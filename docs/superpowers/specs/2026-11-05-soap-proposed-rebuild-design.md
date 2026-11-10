# Design: Soap Proposed Rebuild (entries → patterns)

**Date:** 2026-11-05  
**Status:** Approved (including Step 2b pattern audit)  
**Scope:** Replace the broken `soaps_proposed.yaml` generation path with: deterministic rebuild from monthly unmatched soap match output → LLM `patterns` (`/propose-soaps`) → optional LLM validation annotate/promote (`/validate-soap-proposals`). Manual paste into `data/soaps.yaml` remains the human step.

---

## Intent

`data/soaps_proposed.yaml` should be a reviewable staging file of soap strings the matcher did **not** fully resolve, grouped for catalog work — not a dump of `correct_matches` scents that already exist in `soaps.yaml`.

Today’s file is mostly duplicates of catalogued scents. The old generator (`generate_soaps_proposed.py`) mined `correct_matches` and did not match how proposals are actually used. The `/propose-soaps` path writes elsewhere (`data/proposed/soaps*.yaml`) and also does not de-dupe against real unmatched rows.

---

## Goals

1. Rebuild `data/soaps_proposed.yaml` from monthly `data/matched/YYYY-MM.json` soap fields that need catalog/pattern work.
2. Keep step 1 fully deterministic (Python CLI).
3. Have an LLM enrich that file with `patterns` that cover each scent’s `entries`.
4. Never edit `data/soaps.yaml` automatically.

## Non-goals

- Auto-merging proposals into `soaps.yaml` or `correct_matches`.
- Proposing razors/blades/brushes.
- Replacing `/validate-matches` verification flow.
- Using `correct_matches` as an input or filter for this rebuild.

## Anti-goals

- Emitting “new scent” proposals for strings that already fully matched (`exact` / `regex`).
- Second rotate when the LLM writes patterns (only rebuild rotates).
- Treating catalog presence of a brand/scent as a reason to skip — missing patterns are in scope.

---

## Output shape

Flat catalog-like YAML (same shape as the current review file, **not** nested under a `scents:` key):

```yaml
Brand Name:
  Scent Name:
    entries:
    - normalized string one
    - normalized string two
    patterns:          # added by LLM step; absent after rebuild
    - brand.*scent
unknown:
  unmatched:
    entries:
    - fully unresolved normalized string
```

- **`entries`**: match-phase `normalized` strings (what the matcher sees). Deduped, sorted.
- **`patterns`**: regexes intended for `soaps.yaml`; must cover the scent’s entries (LLM responsibility + skill validation).

---

## Step 1 — Deterministic rebuild

### Standalone CLI (required)

Step 1 is a **first-class, independently runnable Python CLI**. A human who wants to do the LLM’s job themselves (or skip patterns entirely) must be able to run only this script and get a complete entries-only `soaps_proposed.yaml`.

The Claude skill/command **invokes this CLI**, then optionally runs the LLM pattern pass. The skill must not bury rebuild logic in prompts or agent-only steps — all routing/aggregation/rotate lives in Python.

### CLI

Module under `sotd/match/tools/` (builder chooses exact module name; prefer replacing/repurposing `generate_soaps_proposed.py` / aligning with `proposed_soaps_to_yaml` tooling rather than adding a third parallel path).

Flags (pipeline-consistent):

| Flag | Required | Behavior |
|------|----------|----------|
| `--month YYYY-MM` | one of month/range | Single matched month |
| `--range START:END` | one of month/range | Inclusive merge of months |
| `--data-dir` | no | Default `data` |
| `--out` | no | Default `data/soaps_proposed.yaml` |

Missing month files: report on stderr; merge present months; non-zero exit if any requested month is missing (same spirit as `proposed_soaps_to_yaml` range behavior).

### Sources

For each selected month, read `data/matched/{month}.json` records’ `soap` field.

### Routing by `match_type`

| `match_type` | Action |
|--------------|--------|
| `exact`, `regex` | Ignore (fully matched) |
| `filtered` | Ignore (intentionally unmatched via `intentionally_unmatched.yaml`; already decided not to catalog) |
| `dash_split` | Propose under `matched.brand` / `matched.scent`; append `normalized` to `entries` |
| `brand` | Propose under `matched.brand` / `matched.scent`; append `normalized` to `entries` |
| `None` / missing / other unresolved | Bucket under `unknown` → `unmatched` → `entries` |

**Soap field name:** use `matched.scent` (not `model`) — that is what soap match output uses today.

**Guards (builder call):** skip a row for dash_split/brand if `matched.brand` or `matched.scent` is missing/empty — treat as `unknown`/`unmatched` instead of inventing keys. Skip empty/missing `normalized`.

**Out of scope for filtering:** `correct_matches` and “already in `soaps.yaml`” — do not consult those files in step 1. `filtered` rows are skipped via `match_type` only (no need to re-read `intentionally_unmatched.yaml`).

### Aggregation

- Merge across months **within this CLI invocation** into one structure.
- Each rebuild **replaces** the staging file for the selected month/range only (after rotate). A later `--month 2026-10` run does **not** keep proposals from a prior `--range` unless that range is re-run.
- Deduplicate `entries` per brand/scent (case-sensitive on the normalized string as stored).
- Sort brands, scents, and entries for stable diffs.
- After rebuild, each scent node has **only** `entries` (no `patterns` yet).

### Rotate-on-rebuild

Before writing the new file:

1. If the output path exists, rotate it aside.
2. Write the new current file at the canonical path (`data/soaps_proposed.yaml` by default).

**Rotation naming (builder call):** single previous copy at `{out}.bak` (overwrite prior `.bak`). Git remains the long history; no timestamped stack required unless we later want it.

---

## Step 2 — LLM pattern enrichment (`/propose-soaps`)

### Trigger

**`/propose-soaps` is rewritten** to: run the standalone rebuild CLI, then LLM pattern enrichment on `data/soaps_proposed.yaml`.

It does **not** dispatch validate-matches propose agents and does **not** write `data/proposed/{month}.json` or `data/proposed/soaps*.yaml`.

Operators may skip the skill and run only step 1.

Skill flow:

1. Run step 1 CLI for the requested month/range (unless user asks for patterns-only on an existing file).
2. LLM reads `data/soaps_proposed.yaml`.
3. For each brand/scent (including `unknown`/`unmatched` when useful), propose `patterns` that match **all** of that scent’s `entries` (case-insensitive), without overly broad false positives where practical.
4. Write **in place** to the same file (entries preserved; `patterns` added/updated). **No rotate** on this write.
5. Run **Step 2b** pattern collision audit; on hard failures, LLM adjusts patterns and re-audits until clean (or max iterations).
6. Remind the user to review (and optionally `/validate-soap-proposals`) before manually merging into `data/soaps.yaml`.

### Pattern rules (skill)

- Prefer scent-discriminative patterns; add a maker guard when the scent name is generic (same judgment as existing soap catalog practice).
- Before accepting a pattern, verify with a small Python `re.search(..., re.I)` check against every entry under that scent.
- Do not modify `data/soaps.yaml`.
- May leave `unknown`/`unmatched` without patterns (or with conservative patterns) when brand/scent cannot be inferred — still keep entries for human review.
- **Existence research is not required in `/propose-soaps`** — that is `/validate-soap-proposals`’s job (WebSearch + `source_url`). Propose may invent patterns for matcher-inferred brand/scent keys without confirming the product exists.

### Models / batching (builder call)

Follow existing propose-soaps model flag conventions (`sonnet` default). If the file is large, process by brand chunks; rewrite the full YAML once at the end so the file stays valid.

---

## Step 2b — Pattern collision audit (deterministic + LLM fix loop)

After patterns exist on `data/soaps_proposed.yaml`, a **standalone Python CLI** audits them against **all-time** soap `normalized` strings from extracted (or matched) monthly data. `/propose-soaps` invokes this CLI and, on hard failures, feeds the report back to the LLM to adjust patterns, then re-runs until clean.

### Goals

1. Every proposed `entries` string must match at least one of that scent’s `patterns` (`re.I`).
2. Two live proposals in the same `soaps_proposed.yaml` must not both claim the same historical string (clear conflict).
3. Hits on strings labeled as a different product in catalog/`correct_matches` are **contested**, not automatic fails — the other label may be wrong or too broad; LLM/human decides.
4. Unlabeled historical hits are reported, not used as a clean gate.

### Hit classification (per pattern × historical normalized string)

| Bucket | Definition | Gate |
|--------|------------|------|
| **Required TP** | String is in this scent’s `entries` | Must match — missing → **hard fail** |
| **Same product OK** | Same brand+scent already in `soaps.yaml` and/or `correct_matches/soap.yaml` (NFC/case-normalized key match), or same node’s entries | Not a failure |
| **Hard FP** | String is also matched by **another node in the same `soaps_proposed.yaml`** (different brand/scent) | **Hard fail** — two proposals fighting |
| **Contested** | String is labeled as a **different** brand/scent in `soaps.yaml` or `correct_matches/soap.yaml` | **Not auto-fail** — LLM (+ human) decides: tighten our pattern *or* treat as “should be ours / other label wrong” |
| **Ambiguous** | Hits extracted history but is not in entries and not labeled as another product | **Report only** — does not block clean |

**Clean** = no missing required TPs and no hard FPs (same-file proposal collisions). Contested and ambiguous are reported for the LLM fix loop / human; contested should be explained or resolved in the loop when practical, but does not by itself keep the audit exit non-zero.

Optional later flags (out of scope for v1): `--strict-ambiguous`, `--strict-contested` (treat those buckets as hard fails).

### CLI (standalone, required)

Module under `sotd/match/tools/` (builder names it; e.g. `audit_soaps_proposed_patterns.py`).

- Inputs: `data/soaps_proposed.yaml`; all-time soap normals from **`data/extracted/`** (default corpus; every record has `soap.normalized`). Optional `--matched` later is YAGNI for v1.
- Build label index from `soaps.yaml` + `correct_matches/soap.yaml` + other proposed nodes.
- Output: exit `0` if clean; exit `1` if hard failures; machine-readable report (JSON or YAML) listing missing TPs and hard FPs (and capped ambiguous samples).
- Independently runnable so a human can audit without the LLM loop.

### LLM fix loop (inside `/propose-soaps`)

1. Run audit CLI.
2. If exit `0` (clean on hard gate): optionally still show contested/ambiguous summaries; done for gate purposes.
3. If hard failures: pass those rows to the LLM; adjust `patterns` in place; re-audit.
4. Contested rows: include in the LLM prompt as judgment items (tighten vs accept-as-ours). Accepting “ours” does **not** auto-edit catalog/`correct_matches` — note for human follow-up only.
5. Cap iterations (builder call: default 3). If still dirty on the hard gate, stop and show remaining hard failures — do not infinite-loop.

Does not edit `data/soaps.yaml`. Does not rotate `soaps_proposed.yaml` on audit/fix writes.

---

## Step 3 — Validate proposals (`/validate-soap-proposals`)

Separate command from propose. Reads the current `data/soaps_proposed.yaml` (after patterns exist, or entries-only if the human filled patterns).

**Intent:** Decide whether each proposal is real / catalog-worthy; **annotate in place** with evidence; never silent-drop the whole file; never auto-merge into `soaps.yaml`.

**Annotation (per scent node):**

```yaml
Brand:
  Scent:
    entries: [...]
    patterns: [...]
    validation: validated   # or unable_to_validate
    source_url: https://...  # required when validation: validated — URL used as evidence
    research: ...            # short note of what was checked
```

- Keep failed/uncertain scents in place with `validation: unable_to_validate` (optional `research`; `source_url` only if useful).
- Human uses `validation` (+ URL) when choosing what to paste into `soaps.yaml`.

**Promotion from `unknown`:**

If a string under `unknown` / `unmatched` can be identified as a real brand+scent:

1. Create (or merge into) that brand/scent node with the entry (and patterns if already proposed).
2. Set `validation: validated`, `source_url`, and `research` on the **new** brand/scent node.
3. Remove that entry from the `unknown`/`unmatched` bucket (drop the bucket if empty).

Does **not** edit `data/soaps.yaml`. Does **not** rotate the file (in-place annotate / promote only).

---

## Retirement / cleanup

| Existing artifact | Fate |
|-------------------|------|
| `generate_soaps_proposed.py` (correct_matches miner) | Remove or rewrite into the new CLI; do not leave two generators |
| Current `data/soaps_proposed.yaml` content | Discarded on first successful rebuild (rotated to `.bak`) |
| `/propose-soaps` | Rewrite: rebuild CLI → LLM patterns on `data/soaps_proposed.yaml` (no validate-matches agents) |
| `/validate-soap-proposals` | **New:** annotate proposals (`validation` + `source_url`); promote validated `unknown` rows into brand/scent |
| `/propose-soaps-yaml`, `proposed_soaps_to_yaml.py` | Legacy for validate-matches `data/proposed/*.json` path; document as separate from `soaps_proposed.yaml` |

**Legacy JSON path:** keep `data/proposed/YYYY-MM.json` + `proposed_soaps_to_yaml.py` as the validate-matches propose artifact path (razors/blades/etc. and any remaining agent propose). This design owns **`data/soaps_proposed.yaml`** via `/propose-soaps` + `/validate-soap-proposals`.

---

## Testing (step 1)

**Unit**

- Routing: exact/regex ignored; brand/dash_split grouped; unresolved → `unknown`/`unmatched`.
- Missing brand/scent on brand/dash_split → unknown bucket.
- Entry dedupe across months; stable sort.
- Rotate: existing out → `.bak`, new file written; second rebuild replaces `.bak`.
- Empty month / missing file behavior.

**Integration**

- Run against a real `data/matched/YYYY-MM.json` fixture or checked-in month slice; assert no exact/regex normalized strings appear in output entries.

**Step 2**

- Skill/docs tested by dry-run instructions; optional unit helper later for “patterns cover entries” if extracted to Python. Not required for first landing if skill embeds the check.

---

## Success criteria

- Rebuild from a recent month produces a small file dominated by `brand` / `dash_split` / unmatched rows — not catalog clones.
- After LLM pass, each patterned scent’s patterns match its entries.
- After Step 2b, audit is clean (no missing TPs, no same-file proposal hard FPs); contested/ambiguous may remain as report-only (unless later strict flags).
- `soaps.yaml` untouched by the tools.
- Docs/commands describe the operator path: rebuild → pattern → audit/fix loop (`/propose-soaps`) → optional validate → manual merge.

---

## Left to the builder

- Exact module/CLI name and argparse wiring.
- Whether to delete vs thin-wrap legacy `generate_soaps_proposed.py`.
- Chunking strategy and prompt text for the LLM skill.
- Fixture strategy for tests (synthetic matched records preferred for units).
