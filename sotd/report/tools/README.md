# Report-phase operator tools

Point-query CLIs under `python -m sotd.report.tools.*`. They exist so agents and
shell debugging never load whole month files into context: month/window arguments
are explicit (structurally enforcing "never see future months") and output is
bounded. Global flags (`--json`, `--data-dir`) precede the subcommand; each CLI's
`--help` has full usage. Tests: `tests/report/tools/`.

Before hand-coding a python/jq query, check here — the tool may already exist.
When an agent hand-codes something reusable, promote it (see "Adding a tool"
below).

## aggregate_query

Point queries over `data/aggregated/` (monthly + annual): meta block, top tables
per category, rank history for one item, row counts under field conditions, the
sort-key registry behind every rendered rank, dict-shaped metric blocks, and
cross-month meta comparisons — plus a `schema` subcommand so nobody has to probe
the JSON for valid categories or field names.

```bash
.venv/bin/python -m sotd.report.tools.aggregate_query meta --month 2026-08
.venv/bin/python -m sotd.report.tools.aggregate_query schema --month 2026-08
.venv/bin/python -m sotd.report.tools.aggregate_query top --month 2026-08 --category razors --top 10 --min-shaves 5
.venv/bin/python -m sotd.report.tools.aggregate_query top --month 2026-08 --category user_soap_brand_scent_diversity --sort hhi --min-shaves 5
.venv/bin/python -m sotd.report.tools.aggregate_query count --month 2026-08 --category users --where "missed_days=0" --where "shaves>=31"
.venv/bin/python -m sotd.report.tools.aggregate_query history --category razors --name "Blackland Blackbird" --last 6 --end 2026-08
.venv/bin/python -m sotd.report.tools.aggregate_query history --category razors --name "Schick Injector" --name "Merkur 37C" --last 3 --end 2026-08
.venv/bin/python -m sotd.report.tools.aggregate_query ranking
.venv/bin/python -m sotd.report.tools.aggregate_query metrics --month 2026-07
.venv/bin/python -m sotd.report.tools.aggregate_query metrics --months 2026-05:2026-07
```

Always pass `--end <report month>` to history — months after the report month are
already aggregated on disk, and a bare `--last N` silently returns them. Repeat
`--name` for a side-by-side rank matrix (one row per month, one column per item).

**Row counts.** `count` answers "how many rows …" without pulling the whole
table: repeatable `--where` conditions are AND-ed — `FIELD=VALUE`,
`FIELD>=VALUE`, `FIELD<=VALUE`, `FIELD>VALUE`, `FIELD<VALUE`. Numeric values
compare numerically; strings match case-insensitively on `=` only; rows missing
the field (or carrying the wrong type) simply don't match. Unknown fields fail
loudly with the category's field list. Quote each `--where` argument
(`--where "shaves>=31"`) — unquoted `>=` is a zsh expansion error. The
perfect-attendance probe (`missed_days=0` + `shaves>=31`) and the 100%-HHI club
size (`hhi=1.0`, optionally `shaves>=31`) are one-liners now.

**Key fields.** Each category's rows are matched and rendered by their natural
identity field, derived from the rows themselves: `name` for razors/blades/
brushes/soaps, but `brand` for `soap_makers`/`brand_diversity`/`razor_manufacturers`/
`blade_manufacturers`/`brush_knot_makers`, `user` for `users` and the `user_*`/
`*_users` tables, `format`/`fiber`/`handle_maker`/`knot_size_mm`/`plate`/`gap`/
`grind`/`point`/`width`/`super_speed_variant`/`use_count` for the hardware
breakdown tables. Annual files re-key most maker tables to `name` (`brand_diversity`
and user tables keep theirs) — history resolves both shapes. Unknown shapes fail
loudly (exit 1) instead of showing blank names or silent misses. Composite
categories whose key repeats across rows (e.g. `highest_use_count_per_blade`,
keyed user+blade) reject `history` as ambiguous — use `top`/`schema` for those.
`--min-shaves` matches the report tables' `shaves:N` thresholds and errors on
categories without a `shaves` field (`brand_diversity` thresholds on
`unique_soaps` — use `--json` + jq for that filter). `--sort hhi` re-sorts the
result as the report's **Most Boring Shaver** table — `hhi` desc then `shaves`
desc, competition ranks recomputed on equal `(hhi, shaves)` — instead of the
canonical `unique_combinations` order; the rank column is the boring-view rank,
not the file's. It errors on categories without an `hhi` field (only
`user_soap_brand_scent_diversity` has one today), and pairs with
`--min-shaves 5` monthly / `50` annual to match the rendered table. A production-marked sweep
(`tests/integration/test_aggregate_query_real_data.py`, `make test-production`)
verifies every real category renders and resolves.

**Ranking semantics.** Table order is deterministic — read ranks as data. The
canonical, per-category map is `aggregate_query ranking` (period-independent):
product tables sort `shaves` desc then `unique_users` desc (equal shaves is
**not** a tie — 29/19 ranks above 29/1), diversity tables sort by their metric
desc then shaves, Top Shaver sorts `missed_days` asc then shaves desc, and
`brand_diversity` breaks its ties alphabetically rather than by shaves. Ties on
the full sort key share a competition rank (1, 2, 2, 4), alphabetical within the
shared rank; several user tables rank sequentially instead. The registry lives
in `aggregate_query.py` (`_CATEGORY_RANKING`) and the production sweep
(`make test-production`) verifies real file row order against it, so the map
cannot drift from the aggregate phase in either direction.

When drafting: any tie-shaped claim ("N-way photo finish", dead heat) must quote
the tied rows' `shaves` **and** `unique_users` from a query output — equal
shaves alone does not make a tie, and a row whose numbers don't match the
claimed tie is excluded from it.

**Dict metrics.** `metrics --month`/`--year` prints the dict-shaped categories
the list-based subcommands can't reach (`sample_usage_metrics`,
`mashup_usage_metrics`); `metrics --months YYYY-MM:YYYY-MM` builds the
cross-month meta inventory table — the June-anomaly query in one line:

```bash
.venv/bin/python -m sotd.report.tools.aggregate_query metrics --months 2026-05:2026-07
```

## community_query

Queries over `data/community/` month files (all posts + full comment trees):
`meta`, `threads` (filterable/sortable listings), `thread` (one thread + its
reconstructed comment tree, with `--top-level` and `--tail N` slice views),
`bodies` (bounded body slices for chosen post or comment ids — "body reads"),
`search` (keyword/author across a bounded window), `gaps` (census of
deleted/removed/authorless records), and `schema` (meta keys, counts,
post/comment record keys).

```bash
.venv/bin/python -m sotd.report.tools.community_query meta --month 2026-08
.venv/bin/python -m sotd.report.tools.community_query schema --month 2026-08
.venv/bin/python -m sotd.report.tools.community_query threads --month 2026-08 --filter non-sotd --sort comments --top 20
.venv/bin/python -m sotd.report.tools.community_query thread --month 2026-08 --id t3_1sbgn5g --max-comments 50
.venv/bin/python -m sotd.report.tools.community_query thread --month 2026-08 --id t3_1sbgn5g --top-level
.venv/bin/python -m sotd.report.tools.community_query thread --month 2026-08 --id t3_1sbgn5g --tail 10
.venv/bin/python -m sotd.report.tools.community_query bodies --month 2026-08 --ids t3_id1,t3_id2 --max-chars 1000
.venv/bin/python -m sotd.report.tools.community_query bodies --month 2026-08 --id t1_ovchl1k,t1_ovhanvs --max-chars 1200
.venv/bin/python -m sotd.report.tools.community_query search --months 2026-03:2026-04 --query "group buy"
.venv/bin/python -m sotd.report.tools.community_query gaps --month 2026-08
```

Ids in `bodies`/`thread` accept the `t3_`/`t1_` prefix or the bare id (`--id` is
an alias for `--ids`); unknown ids are listed in the output rather than failing
the whole call (all-unknown exits 1). Comment bodies carry thread context
(`in t3_<thread>: <title>`).

**Thread slices and gaps.** `--top-level` renders only direct replies to the
post, each with its direct-reply count (`(+N replies)`) — the shape of a busy
fixture without a full drill. `--tail N` renders the last N comments by time
instead of the first `--max-comments` (the two slice flags are mutually
exclusive; `--top-level` composes with either view). `gaps` lists
deleted/removed/authorless posts and comments with their ids and thread titles
— the Open-questions census in one call.

Record shape (also shown by `schema`): `{"meta": {...}, "data": {"posts": [...],
"comments": [...]}}` — posts carry `id/title/selftext/author/created_utc/...`
plus the `in_pipeline` flag; comments are a flattened list with
`id/thread_id/thread_title/parent_id/author/created_utc/body/...`.

**Recipe — daily challenge target calendar** (when a month's community summary
reveals a daily challenge thread — one-off community events come and go; search
for whatever the month's recurring marker is): read the matched comment bodies;
each day's `Today's target` / `Tomorrow's target` sections carry the
`Soap:`/`Brush:`/`Razor:` lines with difficulty tags. Worked example from
2026-07 (Join Us July):

```bash
.venv/bin/python -m sotd.report.tools.community_query search --months 2026-07:2026-07 --query "Join Us July - July"
.venv/bin/python -m sotd.report.tools.community_query bodies --month 2026-07 --id t1_ovchl1k,t1_ovhanvs --max-chars 1500
```

## enriched_query

Per-shave records from `data/enriched/` — aggregates anonymize users, this CLI
doesn't: `user` (one user's shaves with matched products), `usage` (who used a
product, per-shave rows or `--by-user` counts), `timeline` (adoption timing
across a month window), and `schema` (record + category subobject shapes).

```bash
.venv/bin/python -m sotd.report.tools.enriched_query user --month 2026-08 --name scribe__
.venv/bin/python -m sotd.report.tools.enriched_query usage --month 2026-08 --category soap --name "Catie's Bubbles - Tonsorium" --by-user
.venv/bin/python -m sotd.report.tools.enriched_query timeline --months 2026-06:2026-07 --category razor --name "Schick Injector" --by-day --by-user
.venv/bin/python -m sotd.report.tools.enriched_query schema --month 2026-08
```

`timeline` scans the lookback months (all on disk before the window start,
bounded by `--since`) to classify each user as `new` (first-ever visible use in
the window) or `returning` — the contest-surge attribution question ("who
adopted, and when"). `--by-day` adds per-day counts (spike detection); `--by-user`
adds per-user rows spanning lookback + window (shaves, first/last dates, status).

## extract_observations

Extracts Observations sections from `data/report_archive/` reports as the voice
track for drafting. Voice/storyline context only — never a numeric source.

```bash
.venv/bin/python -m sotd.report.tools.extract_observations --last 12 --end 2026-08 --type hardware
```

## Adding a tool

Promotion follows the "Agent tool promotion" section in the root `CLAUDE.md`:
new subcommand or module here, pytest coverage in `tests/report/tools/`,
lint/typecheck clean, and this README plus the relevant agent `.md` updated in
the same change.
