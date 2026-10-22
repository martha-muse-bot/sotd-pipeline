# WebUI Containerization + Public/Admin Split — Design

**Date:** 2026-10-22
**Status:** Approved in conversation (brainstorming); pending spec review.

## Goal

Run the sotd-pipeline WebUI as containers on the Synology NAS with two
separate applications:

- **Admin app** — the existing full WebUI (all 16 routers, all 13 pages,
  mutating endpoints). LAN-only by topology; no authentication code.
- **Public app** — a new curated build exposing only read-only analytics:
  Product Usage, Monthly User Posts, Report Placement Over Time. Deployed
  behind Nginx Proxy Manager / Cloudflare tunnel on the NAS.

Permissions live in deployment topology rather than application code:
the public container physically contains no mutating code paths, and the
admin container is never given an outward exposure.

## Non-Goals

- No authentication/login anywhere in v1 (admin is LAN-only; public is
  read-only by construction).
- No public access to analyzers, catalog editing, or any mutating endpoint.
- No changes to the admin app's behavior or pages.
- Data is not served from git; no dataset snapshots in the repo or images.

## Approach

**One codebase, two builds** (chosen over fork/middleware-allowlist):

- A single FastAPI router set; the public backend is a slim app that
  imports only the three read-only routers. Mutating routers are never
  imported into the public process.
- A single frontend codebase with two Vite builds: the admin build is the
  existing app untouched; the public build is a new entry point that
  mounts only the shared analytics pages plus a new public Home page.

Rationale: the isolation guarantee is structural (public image cannot
mutate data) rather than dependent on an allowlist staying current. All
three public-candidate routers are already 100% GET endpoints, so no
endpoint classification or read-by-POST wrangling is needed.

## Public Backend Surface

`webui/api/public_main.py` — slim FastAPI app mounting exactly:

| Router | Prefix | Endpoints |
|---|---|---|
| `product_usage` | `/api/product-usage` | 4 GET (products, analysis, yearly-summary, health) |
| `monthly_user_posts` | `/api/monthly-user-posts` | 4 GET (months, users/{month}, analysis/{month}/{user}, health) |
| `report_rankings` | `/api/report-rankings` | 5 GET (months, tables, items, series, pivoted) |

- CORS locked to the public origin.
- Guard test: asserts `public_main`'s OpenAPI schema contains **no
  non-GET operations**. A future mutating endpoint added to a shared
  router fails CI instead of shipping silently.
- Admin `main.py` unchanged.

## Public Frontend

- `webui/src/public/` — new entry: `main.tsx`, `App.tsx` with public nav
  (Home, Product Usage, Monthly User Posts, Placement Over Time), and
  thin page wrappers around the existing shared components.
- New public Home page (curated landing; admin Dashboard stays as-is).
- `vite.config.public.ts` — separate build config, own outDir
  (`dist-public`).

## Data Publishing (slim public bundle)

The three public routers read pre-computed aggregates as their primary
path; `data/enriched/` is only an on-demand fallback used when an
aggregated file is missing. The public data bundle therefore ships only
aggregates — a **selective copy**, no new derivation code:

- `scripts/publish-public-data.sh` — rsync to the NAS share
  (e.g. `/volume1/docker/sotd-public/data/`):
  - `data/aggregated/product_usage/` (~274 MB)
  - `data/aggregated/user_analysis/` (~125 MB)
  - `data/aggregated/{YYYY-MM}.json` (~84 MB total)
  - `data/aggregated/annual/` (~20 MB)
  - Total ~500 MB initial, then tens of MB of deltas monthly.
  - **`data/enriched/` (966 MB, comment-level records) never leaves the
    Mac.**
- Run manually after pipeline runs in v1; post-run hook as fast-follow.
- **Completeness invariant**: the aggregate phase must produce every
  file the public routers' primary paths read — for each month with
  enriched data, a `product_usage/{month}.json`, a
  `user_analysis/{month}.json`, and an `aggregated/{month}.json`. The
  publish script verifies this before rsyncing (every month present in
  one slice must be present in the others) and fails loudly rather than
  shipping a hole. This keeps the routers' enriched fallbacks from ever
  firing in production; no router-mode flag is needed.
- Containers mount the share read-only and resolve it via
  `SOTD_DATA_DIR`.
- `report_rankings.py` and `utils/non_matches.py` already honor
  `SOTD_DATA_DIR`; add the same env-var lookup to `product_usage.py` and
  `monthly_user_posts.py` (small change, unit-tested).
- `monthly_user_posts` `/months` scans `data/enriched/` for the month
  list — change it to scan `aggregated/user_analysis/` first (enriched
  stays the fallback), so the public container needs no enriched data.
- Privacy note: leak prevention comes from the bundle itself —
  `data/enriched/` (966 MB, comment-level records) never leaves the
  Mac, so no fallback path in the public container can ever read it.
  The pages expose usernames by design (monthly user posts, per-product
  user lists); the bundle bounds what else ships (no comment text, no
  raw records). Comment-level data stays in the admin deployment's data
  only.

## Containers & Deployment (GitHub CI, myacuright pattern)

The `myacuright` project's loop, applied here: GitHub Actions builds and
pushes images, a Portainer webhook redeploys, Portainer pulls fresh
`ghcr.io/nmrs/...:latest`. No Mac builds, no `docker save | ssh`, no
manual pulls.

**CI (`.github/workflows/build.yml`)** — modeled on
`myacuright/.github/workflows/build.yml`:

- Triggers: push to `master` (paths affecting webui/docker), manual
  `workflow_dispatch`.
- Gates: `make test`, `make test-react`, lint before building; broken
  images never land.
- buildx multi-stage builds, tags
  `ghcr.io/nmrs/sotd-pipeline-{admin,public}:{latest,sha}`, login with
  `secrets.GITHUB_TOKEN`, GHA build cache.
- After push: curl the Portainer webhook(s) for the public stack (and
  admin stack when it runs on the NAS) — skip with a notice if
  `PORTAINER_WEBHOOK` is unset.

**Images:**

- `public-api` — python:3.14-slim, installs backend deps, runs uvicorn
  with `SOTD_DATA_DIR` pointing at the mounted share.
- `public-frontend` — node build stage → static assets served by nginx.
- `admin` — one image: FastAPI serves the built frontend via
  StaticFiles plus the full API on a single port. (v1 keeps the admin
  container simple; separate nginx added later only if needed.)

**Stack compose in this repo (`deploy/`)** — deployed via Portainer
gitops source, following `myacuright/deploy/compose-myacuright.yml`:

- `pull_policy: always`, `mem_limit` only (never `cpus:` — Synology's
  cgroup v1 rejects it), healthcheck via python stdlib, `TZ` set.
- **Public stack** joins `npm-bridge` (NPM routes the public hostname →
  public-frontend, `/api` → public-api) and `cf_tunnel_net` (tunnel
  routes it).
- **Admin stack** LAN-only: reachable on the LAN (macvlan static IP or
  published LAN port), no `npm-bridge`/`cf_tunnel_net` membership —
  no route can reach it from outside.
- NAS pulls from GHCR. The repo is public, so the GHCR packages are
  public and need no registry credential on the NAS (unlike
  myacuright's private image + `ghcr-nmrs` PAT).

## Repo Safety (public repo)

- Data stays out of git (already the case).
- No secrets in images; the public API uses no external credentials.
- Public frontend/API contain no operator tooling.

## Testing

- pytest: `public_main` route guard (no non-GET ops in OpenAPI schema);
  existing router tests unchanged; unit tests for the new
  `SOTD_DATA_DIR` lookups.
- Playwright: public-build smoke test (home loads; one usage page renders
  against test data) alongside existing admin e2e.
- Makefile targets: `build-public`, `build-images`, `publish-data`.

## Future (out of scope for v1)

- App-level auth (password/session) if the admin app is ever exposed
  beyond LAN.
- Post-pipeline-hook automation of `publish-data.sh`.
- Public access to rendered monthly report archives.
