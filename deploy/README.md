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

**Shipped state (2026-10-22): the public stack IS deployed and live at
http://sotd.jmoore.org** — this section is the record of how it was done
(and what to redo on a new NAS).

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
