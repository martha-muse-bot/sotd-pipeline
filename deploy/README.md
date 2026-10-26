# SOTD Public + Admin Containers — NAS Deployment Runbook

The SOTD web UI ships as three container images, built by GitHub Actions on
every push to `master` (paths: `webui/`, `sotd/`, `requirements.txt`,
`deploy/`, `.dockerignore`, this workflow) and published to GHCR
(`ghcr.io/nmrs`, public packages — no registry credential needed on the NAS):

> **Prerequisite — `nas` ssh alias**: the publish commands below use
> `nas:<path>` targets, where `nas` is an **ssh alias you must configure**
> in `~/.ssh/config` on the Mac (or pass any rsync target instead —
> `SOTD_PUBLIC_DATA_TARGET` env var or the script's first positional
> argument overrides the default). The remote path is relative to the ssh
> login's home directory: if that home is not `/volume1/docker`, use an
> absolute path such as `nas:/volume1/docker/sotd-public/data`.

| Image | Built from | Runs |
|---|---|---|
| `ghcr.io/nmrs/sotd-pipeline-public-api` | `webui/Dockerfile.public-api` | Read-only public API (`webui/api/public_main.py`) |
| `ghcr.io/nmrs/sotd-pipeline-public-frontend` | `webui/Dockerfile.public-frontend` | nginx serving the public SPA + `/api` proxy |
| `ghcr.io/nmrs/sotd-pipeline-admin` | `webui/Dockerfile.admin` | Full admin app (API + built frontend from `webui/dist`) |

Stack compose files live in this repo and are deployed via Portainer
(gitops source pointing at this repository):

- `deploy/compose-sotd-public.yml` — public stack (API + frontend)
- `deploy/compose-sotd-admin.yml` — admin stack, LAN-only

Both stacks mount their data directory **read-only** and locate it via
`SOTD_DATA_DIR=/data`. Neither sets a `cpus:` limit — Synology's cgroup v1
rejects it (`mem_limit` only).

## First-time NAS setup

**Shipped state (2026-10-22): the public stack IS deployed and live**
(the deployed hostname is in the operator's private notes — the site
itself is the public advertisement) — this section is the record of how
it was done (and what to redo on a new NAS).

0. **rsync prerequisites on the Mac + NAS** (each cost debugging time —
   all required):
   - `nas` ssh alias in `~/.ssh/config` on the Mac
     (`Host nas` / `HostName <nas-host>` / `User <ssh-user>`).
   - **Homebrew rsync** on the Mac — `/usr/bin/rsync` is openrsync
     (protocol 29) and cannot talk to the NAS's rsync 3.1.2; install
     `brew install rsync` (script uses whatever `rsync` resolves to).
   - **DSM: Control Panel → File Services → rsync → Enable rsync
     service** (the "Enable rsync account" checkbox is NOT needed —
     that's only for external unencrypted daemon-mode clients).
   - **Pre-create the nested dirs** — rsync won't `mkdir -p`:
     `ssh nas 'mkdir -p /volume1/docker/sotd-public/data/aggregated/{product_usage,user_analysis,annual}'`
     (without this, publishing fails with "file IO (code 11) on
     Receiver").

1. **Create the data directories** on the NAS:

   ```
   /volume1/docker/sotd-public/data
   /volume1/docker/sotd-admin/data
   ```

2. **Populate them before first deploy** (the containers have no data of
   their own):

   - Public share = the **slim bundle** — from the Mac, run
     `make publish-data` (see [Data updates](#data-updates) below). This
     rsyncs `data/aggregated/` slices only (`product_usage/`,
     `user_analysis/`, annual, and the monthly `YYYY-MM.json` files).
     `data/enriched/` never leaves the Mac.
   - Admin share = a **full copy** of the pipeline `data/` directory
     including `enriched/` (the admin tools read comment-level records).
     E.g. `rsync -a data/ nas:sotd-admin/data/` from the Mac.

3. **Create the Portainer stacks** — in Portainer, create one stack per
   file with the repository as gitops source (build method: none — images
   come from GHCR; `pull_policy: always` handles updates):
   - Stack `sotd-public` ← `deploy/compose-sotd-public.yml`
   - Stack `sotd-admin` ← `deploy/compose-sotd-admin.yml`

   The public stack needs one environment variable:
   `SOTD_PUBLIC_ORIGIN` — the public origin, used for CORS
   (`PUBLIC_ALLOWED_ORIGIN`; placeholder default
   `https://sotd.example.invalid`). Set it to the real public URL.

   The admin stack joins the external `macvlan_lan` network and takes the
   static IP `192.168.2.23`. Make sure that IP is free on your LAN and
   outside your DHCP pool before deploying.

4. **NPM proxy host for the public hostname** — in nginx-proxy-manager,
   create a proxy host for the public domain forwarding to
   `sotd-public-frontend:80` (the frontend container is on `npm-bridge`
   for exactly this). Request a Let's Encrypt certificate as usual. The
   frontend nginx config (`webui/nginx/public.conf`) already proxies
   `/api/` to `sotd-public-api:8000`, so a single proxy host covers
   both. The cloudflared tunnel routes the same hostname via the stack's
   `cf_tunnel_net` membership.

   The admin stack has **no** `npm-bridge`/`cf_tunnel_net` membership —
   no external route exists. Reach it at `http://192.168.2.23:8000` from
   the LAN only.

5. **Create the redeploy webhooks** — in Portainer, per stack:
   Edit stack settings → toggle **Create a Webhook** → save → copy the
   webhook URL from the stack details page. Add to this repo as GitHub
   secrets (`gh secret set`):

   - `PORTAINER_WEBHOOK_PUBLIC` → public stack (**set 2026-10-22**; the
     curl POST returns 204 and redeploys)
   - `PORTAINER_WEBHOOK_ADMIN` → admin stack (not needed while the admin
     stack stays undeployed — see the YAGNI note below)

   CI calls them after pushing images; a secret left unset is skipped
   with a notice in the workflow log.

**Admin image is intentionally idle (YAGNI, 2026-10-22 ruling)**: the
admin app mutates the data tree, which buys nothing without a full
pipeline on/near the NAS. The image builds and sits in GHCR (private);
the compose stack and runbook are here for the day that changes. Do not
deploy the admin stack without an explicit decision.

## Update loop

**Code changes** (frontend or API): push to `master` → GitHub Actions runs
the test job (lint + pytest + React tests), then builds and pushes the
three images and fires both webhooks → Portainer redeploys with the new
images. Nothing to do on the NAS.

**Data changes** (after a pipeline run): from the Mac, run
`make publish-data` (or `scripts/publish-public-data.sh [TARGET]`;
default target `nas:/volume1/docker/sotd-public/data` — absolute path on
purpose, a relative one lands in the ssh login's home dir — override via
`SOTD_PUBLIC_DATA_TARGET` or the first argument). The script first
verifies the bundle (fails on an empty bundle or a month gap across the
three slices), then rsyncs with `--delete`. **No container redeploy is
needed** — the API reads the mounted share on each request. For the admin
stack, rsync the full `data/` copy separately as in first-time setup.

The public API serves only read-only GET routes (guarded by a route test
in `webui/api/__tests__/test_public_main.py`, wired into CI). The admin app serves its built frontend via a StaticFiles mount
when `webui/dist` exists (it does in the container image).

## Verification after deploy

- Public: `curl https://<public-host>/api/product-usage/health` (or open
  the site in a browser — Home, Product Usage, Monthly User Posts, Report
  Placement).
- Admin: from the LAN, open `http://192.168.2.23:8000` and confirm the
  frontend loads and analysis endpoints return data.

## Troubleshooting

- **Stack won't start / 404 on images**: GHCR packages inherit the
  repo's visibility — this repo is public, so the public images are
  pullable without credentials (verified by `docker pull` on the NAS).
  The admin image is kept private deliberately (the NAS pulls it with
  a read:packages registry credential). Also confirm the NAS can reach
  `ghcr.io`.
- **CORS errors in the browser**: `SOTD_PUBLIC_ORIGIN` on the public
  stack doesn't match the actual origin.
- **Publish fails with a bundle error**: run the pipeline's aggregate
  phase for the missing months; the verifier refuses to publish a
  partial bundle rather than shipping a hole.
- **Admin unreachable**: it is LAN-only by design — check you're on the
  LAN and that `192.168.2.23` isn't claimed by another device.

## sotd-pipeline stack (nightly pipeline supervisor)

The pipeline container runs the full 6-phase pipeline **on the NAS,
nightly**, and publishes the verified slim bundle straight into the
public stack's data share — `make publish-data` from the Mac becomes a
fallback, not the update path. Deployed via **komodo** (gitops source
pointing at this repository, resource `deploy/compose-sotd-pipeline.yml`):

- `deploy/compose-sotd-pipeline.yml` — stack `sotd-pipeline`, image
  `ghcr.io/nmrs/sotd-pipeline-pipeline:latest` (built by CI on push)

Design notes (spec 2026-10-24): code runs from a git checkout on a
volume (`/app`, cloned on first boot by the entrypoint — the image
provides only the Python env + git + rsync); data lives on its own
volume (`/data`); catalogs arrive via nightly `git pull` (the supervisor
syncs the operator-authored match inputs from `/app/data` into `/data`,
then a hash over the volume triggers an all-months `match:aggregate`
catch-up when they change); the bundle is verified then rsync'd into the
public share (failure keeps the last good bundle — never a hole). Each
month runs as ONE command (`run.py --month M --force fetch:aggregate`)
so a failed fetch never feeds stale data to match. Like the other
stacks, no `cpus:` limit (Synology cgroup v1), `mem_limit: 2g` only.

### First-time setup

1. **Pre-create the NAS directories** (the entrypoint writes into both):

   ```
   /volume1/docker/sotd-pipeline/data
   /volume1/docker/sotd-pipeline/repo
   ```

2. **Seed the data volume** (one-time, from the Mac — long: ~2 GB;
   excludes non-pipeline inputs such as backups, logs and the raw
   scrape cache). `scripts/seed-pipeline-data.sh` wraps exactly this:

   ```bash
   rsync -a --delete \
     --exclude='.DS_Store' \
     --exclude='*.backup' --exclude='*.bak' --exclude='*.bk' \
     --exclude='backup/' --exclude='logs/' --exclude='learning/' \
     --exclude='report_archive/_reddit_raw/' \
     data/ nas:/volume1/docker/sotd-pipeline/data/
   ```

3. **Create the komodo resource** from `deploy/compose-sotd-pipeline.yml`
   (build method: none — the image comes from GHCR; `pull_policy:
   always` handles updates) and set these **environment variables in
   komodo** (the entrypoint materializes `praw.ini` from them at boot):

   | Env var | Purpose |
   |---|---|
   | `REDDIT_CLIENT_ID` | Reddit API credential (praw, required) |
   | `REDDIT_CLIENT_SECRET` | Reddit API credential (praw, required) |
   | `REDDIT_USER_AGENT` | Optional user-agent string (default `sotd-pipeline-supervisor`) |
   | `REDDIT_USERNAME` | Optional — only if an authenticated account is needed |
   | `REDDIT_PASSWORD` | Optional — only if an authenticated account is needed |

   A mounted `praw.ini` wins over the env vars if you ever need to
   provision it by file instead.

4. **Deploy.** On first boot the entrypoint clones the repo into the
   `/app` volume, then the supervisor loop self-schedules at 02:00
   America/Chicago (nightly scope: current + prior month).

### Smoke test before enabling the schedule

Run one full cycle immediately, then exit:

```
docker compose exec sotd-pipeline python -m sotd.pipeline_supervisor.loop --once
```

(`--once` skips the 02:00 wait, runs one nightly cycle now, and exits —
safe to repeat.) Verify: the `/app` clone exists, the phases ran in the
container logs, `/volume1/docker/sotd-public/data` picked up the
published bundle, and the public site reflects the new run.

### Verification

- **Metrics stack** (`deploy/compose-sotd-metrics.yml`, gitops from this
  repo): Prometheus + Grafana on `metrics-net`, scraping
  `sotd-pipeline:8000` (the `127.0.0.1:8100` host bind is only a curl
  stopgap). Grafana is LAN-only by topology — no tunnel/NPM route exists;
  open `http://<nas>:3000` (admin password via komodo env
  `SOTD_GRAFANA_ADMIN_PASSWORD`). The provisioned **SOTD Pipeline**
  dashboard covers: freshness ("hours since last publish", threshold
  ~26h), consecutive-failure count (>= 2 = systematically broken), run
  and phase-duration trends, records per phase, and publish-failure
  history. Prometheus config and dashboards provision from
  `deploy/metrics/` (bind-mounted read-only); retention 30d.
  Metrics exposed: `sotd_pipeline_last_run_timestamp_seconds`,
  `sotd_pipeline_last_run_status{phase}`,
  `sotd_pipeline_months_processed`,
  `sotd_pipeline_catalog_catchup_last_success_timestamp_seconds`,
  `sotd_pipeline_phase_duration_seconds{phase, scope}`,
  `sotd_pipeline_phase_records{phase, scope}`,
  `sotd_pipeline_publish_last_success_timestamp_seconds`,
  `sotd_pipeline_publish_failures_total`, `sotd_pipeline_runs_total{outcome}`,
  `sotd_pipeline_consecutive_failures`,
  `sotd_pipeline_next_run_timestamp_seconds`, and
  `sotd_pipeline_run_duration_seconds`.
  Phase labels on `last_run_status`: `pull`, `fetch` (the whole
  `fetch:aggregate` monthly run — 0 if ANY month failed), `publish`, and
  `catchup`. Note the `--once` smoke run does not serve metrics (the
  port belongs to the running loop).
- **Phase durations**: `sotd_pipeline_phase_duration_seconds{phase, scope}`
  carries one duration per pipeline phase parsed from run.py's summary —
  `phase` is fetch/extract/match/enrich/aggregate, `scope` is `monthly`
  (per-month `fetch:aggregate` runs) or `catchup` (the all-months
  `match:aggregate` run; match over 2 months isn't comparable to match over
  159+). A failed phase gets no duration; earlier OK phases of a failed run
  still do. In Grafana, trend `phase_duration_seconds{phase}` (split by
  `scope`) to watch fetch vs match vs catch-up timing drift.
  `sotd_pipeline_run_duration_seconds` is the whole nightly cycle wall time
  (git pull through final publish), one label-free series.
- **Public site reflects a forced run**: run the `--once` smoke test,
  then reload the public site — product usage / monthly posts should
  include the newest processed month.

### Troubleshooting

- **A phase fails overnight**: the loop aborts before publish; the
  public data keeps the **last good bundle** (never a hole), the failing
  phase shows in `sotd_pipeline_last_run_status{phase}` and the logs,
  and the next night retries.
- **Image pull failures**: `pull_policy: always` means a GHCR outage
  blocks redeploy, but the running container and the last-good bundle
  are unaffected. Check the NAS can reach `ghcr.io`.
- **Catalog catch-up retries**: a failed all-months catch-up leaves the
  catalog hash unsaved, so it retries the next night automatically; the
  daily bundle is already published by then regardless.
