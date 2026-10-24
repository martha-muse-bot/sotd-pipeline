# Server-side pipeline container — design

**Date:** 2026-10-24
**Status:** Approved design (brainstorming output); implementation plan to follow.
**Goal:** The public site's `data/aggregated/` bundle stays fresh unattended. The NAS
runs the full pipeline nightly; catalogs/overrides/correct-matches stay authored on
the Mac and reach the server via git.

## Context

The public site (deployed 2026-10-22) reads a slim `data/aggregated/` bundle from
`/volume1/docker/sotd-public/data`, refreshed today only when the operator runs
`make publish-data` on the Mac after a local pipeline run. This design moves the
pipeline compute to a NAS container so freshness no longer depends on the Mac.

Key environment facts:
- Deployment is via **komodo** (Portainer retired; signed webhook + explicit compose
  project name — commits 0059ec25c, 2d6e74857).
- Arctic Shift is the primary archive (no auth; ~7h lag verified 2026-10-24). PullPush
  is demoted fallback (~11 days stale as of 2026-10-24).
- Current-month Reddit discovery needs the ~1000-item `/new` listing → requires
  `praw.ini` credentials.
- Synology cgroup v1: no `cpus:` limits in compose (`mem_limit` only).
- Pipeline data: 159 months (2016-05 → 2026-10), `data/enriched/` ~1 GB.
- NAS data dirs: `/volume1/docker/sotd-pipeline/data` (pipeline tree, seeded from Mac)
  and `/volume1/docker/sotd-public/data` (public bundle, already live).

## Architecture

One new komodo stack `sotd-pipeline` with one long-running container, image built by
the existing GitHub Actions build job from a new `Dockerfile.pipeline` and pushed to
GHCR alongside the webui images.

The container's entrypoint is a small supervisor loop (not cron-on-host):

```
nightly at 02:00 America/Chicago:
  1. git pull origin master            (catalogs, overrides, correct_matches, code)
  2. compute catalog-content hash; compare with stored hash
  3. fetch + extract: current + prior month
  4. match → enrich → aggregate: current + prior month
  5. verify bundle → publish slim bundle to public share
  6. if catalog hash changed: match → enrich → aggregate over ALL months (~159)
  7. verify + publish (again, only if step 6 ran and succeeded)
  8. save catalog hash (only after step 7 succeeded); emit metrics; log summary
```

Rationale for the double-publish ordering: the all-months pass is the heaviest,
most failure-prone step; running it *after* the daily publish means a catch-up
failure never blocks daily freshness (next night retries with the hash unsaved).
On catalog-change nights the bundle publishes twice; each publish is a sub-second
local rsync.

### Code runs from a git checkout, not the baked image

The image provides the Python environment; `/app` in the container is a **git
working tree on a volume** (`git clone` on first boot, `git pull` nightly). This
keeps catalog + code changes flowing to the server without image rebuilds. CI-built
images remain the vehicle for dependency/Dockerfile changes.

### Data layout

```
volume: sotd-pipeline-data   →  /volume1/docker/sotd-pipeline/data
  seeded once from the Mac via rsync (see Seed below); owned by the container after.
volume: sotd-pipeline-repo   →  git working tree at /app (cloned on first boot)
/volume1/docker/sotd-public/data   (existing; written ONLY by the publish step)
```

Publish step (inside the container, local rsync — no ssh):
`rsync --delete` of the slim bundle slices (`aggregated/product_usage/`,
`user_analysis/`, `annual/`, monthly `????-??.json`) from the pipeline tree into
`/volume1/docker/sotd-public/data`, gated by the existing bundle verifier
(`scripts/publish_public_data.py --check` logic). The public API mount is untouched
by anything except a verified publish.

Independence of the two trees is deliberate: the public bundle is a verified
*subset*, not the pipeline tree; a failed run never serves partial data; and
`make publish-data` from the Mac keeps working unchanged as a manual override.

### Catalog hash definition

Hash covers exactly the operator-authored match inputs: `data/*.yaml` catalogs,
`data/correct_matches/*.yaml`, `data/thread_overrides.yaml`,
`data/extract_overrides.yaml`, `data/enrichment_overrides.yaml`,
`data/intentionally_unmatched.yaml`. Stored at
`/volume1/docker/sotd-pipeline/data/.catalog_hash` after a successful catch-up.
Any diff vs. the stored hash triggers the all-months catch-up. Code-only changes
(matching logic, pipeline code) do NOT trigger catch-up in v1 — noted as a known
gap; the operator can force one by touching any catalog file or running a manual
cycle.

## Secrets & config

- Komodo resource env: `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`,
  `REDDIT_USERNAME`, `REDDIT_PASSWORD`, `TZ=America/Chicago`.
- Entrypoint materializes `praw.ini` from these env vars at startup unless a
  mounted `praw.ini` exists (file mount wins — both paths supported). ~10-line
  adapter script in the image.
- `SOTD_PUBLIC_ORIGIN` stays on the public stack, untouched.

## Fetch behavior

- Current + prior month sit inside Reddit's ~8-month `/new` listing window →
  discovery via praw listing; comment trees via the archive ladder (Arctic Shift
  ID-only, no auth). Same code paths the Mac runs today — no new fetch logic.
- 429 retry/backoff and INCOMPLETE-month marking behave as today. A failed month
  is logged and metricized and does not block publish of the rest of the bundle
  (matches the Mac pipeline's INCOMPLETE semantics).

## Monitoring

Container exposes `/metrics` on the existing external `metrics-net` network (same
pattern as public-api; the pipeline container stays OFF `cf_tunnel_net` and
`npm-bridge`). Prometheus metrics:

- `sotd_pipeline_last_run_timestamp_seconds`
- `sotd_pipeline_last_run_status{phase}` (fetch/extract/match/enrich/aggregate/
  catchup/publish)
- `sotd_pipeline_months_processed`
- `sotd_pipeline_catalog_catchup_last_success_timestamp_seconds`

Container logs (komodo/ssh viewable) remain the detailed record.

## Seed (one-time, from the Mac)

```bash
rsync -a --delete \
  --exclude='.DS_Store' \
  --exclude='*.backup' --exclude='*.bak' --exclude='*.bk' \
  --exclude='backup/' --exclude='logs/' --exclude='learning/' \
  --exclude='report_archive/_reddit_raw/' \
  data/ nas:/volume1/docker/sotd-pipeline/data/
```

Pre-seed cleanup completed 2026-10-24: removed `handles.yaml.backup`,
`brush_splits.yaml.backup`, `correct_matches/soap.yaml.{backup,bk}`,
`correct_matches/soap_duplicates_report.yaml.bk`, and 8 `.DS_Store` files. Data-tree
audit found no other strays; `correct_matches/.status*` and `.queue.jsonl` are
operational state and stay.

## Failure handling

- Any phase failure in steps 1–5 → abort before publish; public data keeps the last
  good bundle; Prometheus shows the failing phase; next night retries.
- Catch-up (step 6) failure → daily bundle already published; hash not saved, so
  the catch-up retries next night.
- Bundle verifier failure → no publish (never ship a hole).

## Testing

- Unit tests for supervisor-loop logic (catalog hash computation, month-scope
  calculation, praw.ini materializer, publish gating) in `tests/` per repo standard.
- Container smoke test on the NAS before enabling the nightly schedule: one full
  manual cycle with `--force`, verify publish lands and the site reflects it.

## Non-goals

- No admin container on NAS (unchanged 2026-10-22 YAGNI ruling).
- No server-side catalog authoring; the Mac stays the single authoring surface.
- No community sidecar / summarizer / observations-drafter on the server (Mac
  workflows).
- No report generation on the NAS (public bundle needs only aggregated slices).
- No intraday freshness (nightly cadence only).

## Explicitly settled decisions (from brainstorming)

| Decision | Choice |
|---|---|
| Phases on server | Full pipeline through aggregate |
| Trigger | Nightly, 02:00 America/Chicago, container-internal loop |
| Catalog sync | Git pull from GitHub (praw.ini provisioned separately) |
| Initial data | Seed full tree from Mac via rsync |
| Secrets | Komodo env vars + entrypoint materializes praw.ini (file-mount fallback supported) |
| Publish path | Verify-then-rsync into independent public dir (no symlinks/shared volume) |
| Month scope | Drift-triggered catch-up over ALL months; nightly current+prior |
| Monitoring | Prometheus metrics on metrics-net |
| Run ordering | Daily publish first; all-months catch-up after, second publish on success |