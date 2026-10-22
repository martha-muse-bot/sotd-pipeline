# PRD: SOTD Fetch Phase

| Field | Value |
| --- | --- |
| **Status** | Draft for rebuild |
| **Date** | 2026-08-07 |
| **Product** | SOTD Pipeline — Phase 1 (Fetch) |
| **Audience** | Engineers rebuilding fetch as a greenfield component |
| **Fidelity** | Faithful reverse-spec of current production behavior |

This document defines product requirements for rebuilding the **fetch** phase from scratch so a new implementation can match today’s capabilities and contracts without relying on the existing codebase as the source of truth.

---

## 1. Overview

Fetch is the first phase of the Shave of the Day (SOTD) data pipeline. It pulls **r/wetshaving** SOTD threads and their **top-level comments** for one or more calendar months, then writes durable monthly JSON under a configurable data directory (default `data/`).

**Position in the pipeline**

```
Reddit → [fetch] → extract → match → enrich → aggregate → report
```

**What fetch owns**

- Discover SOTD threads for a month
- Harvest top-level (root) comments from those threads
- Persist month-scoped artifacts with completeness metadata
- Support re-runs (merge or force overwrite) and manual include/exclude overrides

**What fetch does not own**

- Parsing product fields from comment bodies (razor, blade, brush, soap, etc.)
- Downstream phases (extract and later)
- Web UI or multi-subreddit collection

Downstream **extract** consumes `comments/YYYY-MM.json` only. Fetch must produce that contract unchanged; it must not parse product fields.

---

## 2. Problem & Goals

### 2.1 Problem

r/wetshaving posts daily SOTD threads. Individual shave write-ups live in **top-level comments**. Reddit search is incomplete in practice (result caps, flair/title variance, joke or non-SOTD threads that still match search). Operators need reliable, month-scoped, re-runnable collection with clear gap reporting and curated corrections—not one-shot scrapes.

### 2.2 Goals

1. Collect all discoverable SOTD threads for a month (title date in that month) plus top-level comments.
2. Persist stable monthly artifacts so extract can run without live Reddit access.
3. Support re-runs: merge by id by default; `--force` for clean overwrite.
4. Surface coverage gaps (`missing_days`, audit mode, threads missing comments).
5. Allow curated include/exclude via `thread_overrides.yaml`.

### 2.3 Success metrics (rebuild)

A rebuild is successful when:

- The same CLI date matrix and operational flags work as specified in §7.
- Output schemas match §6 (field names and meta shape).
- Merge and `--force` semantics match §4 / §6.
- Rate-limit handling does not abort a full month on typical transient Reddit limits (retry/backoff).
- Missing-day and audit reporting work for historical and current months.
- Existing extract can consume rebuilt comments JSON without schema changes.

### 2.4 Non-goals (this phase)

- Product field parsing
- Pushshift or third-party archives (current production fetch is **PRAW-only**)
- Nested reply comments
- WebUI
- Multi-subreddit support
- Changing the override schema or inventing new output fields beyond today’s contract

---

## 3. Users & Use Cases

**Primary user:** Pipeline operator (local CLI or scheduled job).

| ID | Use case | Behavior |
| --- | --- | --- |
| UC1 | Fetch one month | `--month YYYY-MM` → write/merge `threads/` + `comments/` |
| UC2 | Fetch year / range | `--year`, `--range A:B`, or `--start` + `--end` |
| UC3 | Fresh rebuild | `--force` removes existing month files, then writes new |
| UC4 | Incremental refresh | Without `--force`, merge by `id` (newer `created_utc` wins) |
| UC5 | Completeness check | `--audit` reports missing files / `missing_days` (exit `1` if gaps) |
| UC6 | Inventory | `--list-months` prints months with any threads or comments file |
| UC7 | Manual correction | Edit `thread_overrides.yaml`; re-fetch (`--force` required to drop already-saved excludes) |

---

## 4. Functional Requirements

### 4.1 P0 — Must ship

| ID | Requirement |
| --- | --- |
| F1 | Authenticate via PRAW using `praw.ini` in the project root; fail fast if credentials are unusable. |
| F2 | Search r/wetshaving with Lucene queries combining `flair:SOTD`, **month abbreviation only**, and year. Do not include the full month name in broad queries (e.g. use `aug` not `august`) — full names bias relevance toward titles like “Austere August” and can crowd regular SOTD threads out of the 100-result window. |
| F3 | If search hits the ~100-result cap, run day-specific follow-up searches for under-covered days, using an expected threads-per-day of `max(observed_max, 2)` so parallel daily threads (Austere August + regular SOTD, Theme Thursday, etc.) are still hunted when the truncated broad sample shows only one per day. For the **current** calendar month, only check through **today**. Day-specific queries may use both month abbreviation and full month name. |
| F4 | Keep threads whose title date parses to the target `YYYY-MM`. Drop unparsable or wrong-month titles, except **include** overrides that may supply a YAML date fallback when the title is unparsable. |
| F5 | Fetch **top-level (root) comments only**; expand Reddit “more comments” / `MoreComments` objects so the root set is complete. |
| F6 | Fetch comments in parallel with rate-limit-aware retries; on per-thread failure, return empty comments for that thread rather than failing the whole month. |
| F7 | Apply `include` / `exclude` from `data/thread_overrides.yaml`, scoped to the fetched month. |
| F8 | Write `threads/YYYY-MM.json` and `comments/YYYY-MM.json` as `{ "meta": ..., "data": ... }` under the configured data directory. |
| F9 | Default merge by `id` (later `created_utc` wins). `--force` deletes existing month files before rewrite. |
| F10 | Compute `missing_days`: calendar days in the month with no thread whose title (or override) date falls on that day. |
| F11 | Support the date-span CLI: `--month` / `--year` / `--range` / `--start`+`--end`, plus shared flags `--force`, `--debug`, `--verbose`, `--data-dir`. |
| F12 | Support `--audit` and `--list-months` as in UC5 / UC6. |

### 4.2 P1 — Match current behavior; deferrable for a thin MVP cut

| ID | Requirement |
| --- | --- |
| F13 | Verbose completion summary (thread/comment counts, missing days). |
| F14 | Debug logging for search queries, skipped threads/reasons, and override validation. |
| F15 | Optional performance metrics on the parallel comment path. |
| F16 | If zero threads are found for a month, warn and skip file writes. |

### 4.3 Thread discovery details (normative behavior)

**Broad search (example pattern)**

- `flair:SOTD {month_abbr} {year}` (abbreviation only — not full month name)
- Variant including concatenated `yearSOTD` as used in production search strategy

**Cap recovery**

1. Deduplicate submissions by Reddit submission id.
2. Filter to the target year/month via title-date parsing.
3. Group by day; determine max threads-per-day among days that have threads.
4. Set expected threads-per-day to `max(observed_max, 2)` so truncated broad results that only contain one series (e.g. Austere August) still trigger day searches for parallel regular SOTD threads.
5. For days below that expected count (and within the day window for current month), issue day-specific flair+date queries (abbr and full month name) and merge results.

**Validity filter**

- Title date must parse (month-name or numeric day patterns; year optional with year hint).
- Parsed `(year, month)` must equal the requested month.
- Include overrides may attach `_override_date` (`YYYY-MM-DD`) used when title date is missing.
- Sort kept threads by title/override date ascending.

**Coverage vs. created time**

Calendar coverage (`missing_days`, `expected_days`) is based on **title (or override) dates**, not Reddit `created_utc`.

---

## 5. Non-Functional Requirements

| Area | Requirement |
| --- | --- |
| Resilience | On Reddit rate limits, retry using explicit wait from headers/exception when available; otherwise exponential backoff with jitter. Soft-fail individual API calls where returning empty/`None` avoids aborting the whole month. |
| Performance | Parallel comment fetch via thread pool (production run path uses on the order of 10 workers). Sequential fallback if parallel execution fails. |
| Observability | Pipeline logging; `--debug` and `--verbose`; progress indication across months. |
| Security | Credentials only via `praw.ini` / environment—never committed as artifacts. |
| Portability | Configurable `--data-dir` (default `data`, or env-driven data dir conventions used by the pipeline). |
| Idempotency | Re-run without `--force` is merge-safe. Re-run with `--force` is a deterministic overwrite of that month’s files. |

---

## 6. Data Contracts

### 6.1 File layout

```
{data_dir}/
  threads/YYYY-MM.json
  comments/YYYY-MM.json
  thread_overrides.yaml   # operator-maintained input, not phase output
```

Both JSON files use UTF-8, pretty-print indent 2, envelope:

```json
{
  "meta": { },
  "data": [ ]
}
```

Records in `data` are sorted by `created_utc` ascending.

**ID format:** Production uses **bare** Reddit ids (no `t3_` / `t1_` prefix). Rebuilds must match that convention for extract compatibility.

### 6.2 Threads — `threads/YYYY-MM.json`

**Meta**

| Field | Type | Meaning |
| --- | --- | --- |
| `month` | string | `YYYY-MM` |
| `extracted_at` | string | ISO-8601 timestamp of this write |
| `thread_count` | int | `len(data)` after merge |
| `expected_days` | int | Days in the calendar month |
| `missing_days` | string[] | ISO dates `YYYY-MM-DD` with no covering thread |

**Record**

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Submission id |
| `title` | string | Thread title |
| `url` | string | Absolute Reddit permalink URL |
| `author` | string | Username, or `"[deleted]"` if missing |
| `created_utc` | string | ISO-8601 UTC, `Z` suffix preferred |
| `num_comments` | int | Reddit comment count |
| `flair` | string \| null | Link flair text |

**Example**

```json
{
  "meta": {
    "month": "2026-07",
    "extracted_at": "2026-08-05T17:01:07.626776+00:00",
    "thread_count": 31,
    "expected_days": 31,
    "missing_days": []
  },
  "data": [
    {
      "id": "1ukd9m0",
      "title": "Wednesday SOTD Thread - Jul 01, 2026",
      "url": "https://www.reddit.com/r/Wetshaving/comments/1ukd9m0/wednesday_sotd_thread_jul_01_2026/",
      "author": "AutoModerator",
      "created_utc": "2026-07-01T06:00:46Z",
      "num_comments": 64,
      "flair": "SOTD"
    }
  ]
}
```

### 6.3 Comments — `comments/YYYY-MM.json`

**Meta**

| Field | Type | Meaning |
| --- | --- | --- |
| `month` | string | `YYYY-MM` |
| `extracted_at` | string | ISO-8601 timestamp of this write |
| `comment_count` | int | `len(data)` after merge |
| `thread_count_with_comments` | int | Distinct `thread_id` values present in `data` |
| `missing_days` | string[] | Same coverage list as threads meta for the month |
| `threads_missing_comments` | string[] | Thread ids in threads data with no comments in `data` |

**Record**

| Field | Type | Notes |
| --- | --- | --- |
| `id` | string | Comment id |
| `thread_id` | string | Parent submission id |
| `thread_title` | string | Parent title (denormalized) |
| `url` | string | Absolute comment permalink |
| `author` | string | Username, or `"[deleted]"` if missing |
| `created_utc` | string | ISO-8601 UTC |
| `body` | string | Full comment markdown/text |

**Example (truncated)**

```json
{
  "meta": {
    "month": "2026-07",
    "extracted_at": "2026-08-05T17:01:07.626776+00:00",
    "comment_count": 1691,
    "thread_count_with_comments": 31,
    "missing_days": [],
    "threads_missing_comments": []
  },
  "data": [
    {
      "id": "ouuy2or",
      "thread_id": "1ukd9m0",
      "thread_title": "Wednesday SOTD Thread - Jul 01, 2026",
      "url": "https://www.reddit.com/r/Wetshaving/comments/1ukd9m0/wednesday_sotd_thread_jul_01_2026/ouuy2or/",
      "author": "sandstorm99",
      "created_utc": "2026-07-01T06:18:31Z",
      "body": "...shave write-up..."
    }
  ]
}
```

### 6.4 Merge semantics

- Without `--force`: load existing month file if present; merge `new` onto `existing` by `id`; keep the record with the later `created_utc`; sort by `created_utc` ascending; always rewrite file with fresh `extracted_at` metadata.
- With `--force`: delete existing threads and comments files for that month (if present), then write only the newly fetched set.
- Zero threads: warn and **do not** write files (F16).

---

## 7. CLI Contract

### 7.1 Date selection

| Flag | Meaning |
| --- | --- |
| `--month YYYY-MM` | Single month |
| `--year YYYY` | All 12 months |
| `--range A:B` | Inclusive monthly `YYYY-MM:YYYY-MM`, or annual `YYYY:YYYY` (all months in each year) |
| `--start YYYY-MM` + `--end YYYY-MM` | Inclusive span (both required together) |

Invalid / conflicting date combinations must error clearly (argparse / validation errors).

**Default month:** When invoked through the unified pipeline orchestrator (`run.py`) with no date flags, the orchestrator may inject a default (today: **previous calendar month**). The fetch phase itself expects an explicit month span once arguments are resolved; rebuilds should preserve orchestrator-compatible CLI flags even if default injection lives outside fetch.

### 7.2 Operational flags

| Flag | Meaning |
| --- | --- |
| `--force` | Overwrite: delete month outputs then rewrite |
| `--debug` | Debug logging (queries, skips, overrides) |
| `--verbose` | Richer INFO summaries / progress detail |
| `--data-dir PATH` | Data root (default `data`) |
| `--audit` | Completeness audit over selected months; no Reddit fetch |
| `--list-months` | Print months that have threads and/or comments files; exit |

### 7.3 Exit codes

| Code | When |
| --- | --- |
| `0` | Success; clean audit; successful list |
| `1` | Audit found missing files or missing days; interrupt; unhandled failure |

### 7.4 Example invocations

```bash
python run.py fetch --month 2025-05 --force
python run.py fetch --year 2024 --force
python run.py fetch --range 2024-01:2024-06 --force
python run.py fetch --start 2024-01 --end 2024-06 --force
python run.py fetch --month 2025-05 --audit
python run.py fetch --list-months
```

---

## 8. Override Contract

**File:** `data/thread_overrides.yaml` (relative to project / data conventions used by fetch).

```yaml
include:
  2025-06-25:
    - https://www.reddit.com/r/Wetshaving/comments/1lk3ooa/wednesday_sotd_25_june/
exclude:
  2026-06-01:
    # Joke / non-SOTD thread that search still finds
    - https://www.reddit.com/r/Wetshaving/comments/1ttrafo/monday_lather_games_sotd_thread_jun_1_2026/
```

| Section | Behavior |
| --- | --- |
| `include` | Force-fetch threads missed by search. Date key → list of Reddit URLs. Fetch by URL; attach YAML date as fallback when title date cannot be parsed. |
| `exclude` | Drop threads found by search. Match by submission id extracted from URL. |

**Scoping:** Only entries whose date keys start with the fetched `YYYY-MM` apply.

**Persistence note:** Re-fetch with `--force` is required to remove an already-saved excluded thread from monthly JSON.

**Legacy:** Root-level date keys (pre-`include`/`exclude` schema) should be detected and warned; operators should migrate under `include:` / `exclude:`.

---

## 9. Acceptance Criteria

The rebuild is accepted when all of the following are true:

1. **P0 complete:** F1–F12 behave as specified.
2. **Schema parity:** Threads and comments JSON match §6 field-for-field for meta and records.
3. **Merge / force:** Incremental merge and `--force` overwrite match §6.4.
4. **Overrides:** Include and exclude work for a month; force clears stale excludes from disk.
5. **Audit / inventory:** `--audit` and `--list-months` match UC5 / UC6 and exit codes in §7.3.
6. **Resilience:** A typical month completes despite intermittent rate limits (retries succeed or soft-fail per thread).
7. **Downstream smoke:** Extract run against rebuilt `comments/YYYY-MM.json` succeeds without schema adapters.
8. **Coverage signals:** `missing_days` and `threads_missing_comments` are populated consistently with discovery results.

---

## 10. Out of Scope

- Extract, match, enrich, aggregate, report
- Parsing razors/blades/brushes/soaps from comment text
- Pushshift or alternate archives
- Nested / reply comments
- WebUI or API surfaces for fetch
- Multi-subreddit fetching
- Redesigning `thread_overrides.yaml` schema
- Adding new output fields not present in §6

---

## 11. Dependencies & Assumptions

| Dependency | Assumption |
| --- | --- |
| Reddit API via PRAW | Operator provides working `praw.ini` in project root |
| Subreddit | `r/wetshaving` (search target name `wetshaving`) |
| Flair | Primary discovery signal is `flair:SOTD` |
| Title dates | Thread titles contain a parseable calendar date used for month membership and coverage |
| Python tooling | Rebuild may choose stack freely, but must honor CLI and data contracts for pipeline integration |
| Data directory | Default `data/`; must remain compatible with later phases’ expected paths |

---

## 12. Open Risks (known from current product)

| Risk | Mitigation already in product |
| --- | --- |
| Reddit 100-result search cap | Day-specific follow-up searches (F3) |
| Threads missed by search | `include` overrides (F7) |
| Non-SOTD threads matching search | `exclude` overrides (F7) |
| Rate limiting under parallel comment fetch | Retry/backoff; soft-fail per thread (F6, §5) |
| Incomplete months | `missing_days` + `--audit` (F10, F12) |

These are accepted product realities, not rebuild stretch goals—unless a later PRD explicitly expands scope.

---

## Appendix A — Reference architecture (logical modules)

A rebuild may structure code differently, but responsibilities today map cleanly to:

| Concern | Responsibility |
| --- | --- |
| CLI / orchestration | Parse args, iterate months, summary, exit codes |
| Reddit client | Auth, search, submission fetch, root comments, rate-limit wrapper |
| Overrides | Load YAML; include by URL; exclude by id |
| Merge | Deduplicate by id, prefer newer `created_utc` |
| Persistence | Read/write `{meta, data}` month files |
| Audit | Missing files and meta `missing_days` over a month span |

---

## Appendix B — Document history

| Date | Change |
| --- | --- |
| 2026-08-07 | Initial PRD: faithful reverse-spec of fetch for greenfield rebuild |
