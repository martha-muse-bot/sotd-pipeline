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
(gitops source pointing at this repository, same pattern as
`myacuright/deploy/compose-myacuright.yml`):

- `deploy/compose-sotd-public.yml` — public stack (API + frontend)
- `deploy/compose-sotd-admin.yml` — admin stack, LAN-only

Both stacks mount their data directory **read-only** and locate it via
`SOTD_DATA_DIR=/data`. Neither sets a `cpus:` limit — Synology's cgroup v1
rejects it (`mem_limit` only).

## First-time NAS setup

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

5. **Create the redeploy webhooks** — in Portainer, create a webhook for
   each stack (Stack → Webhooks), then add them as GitHub secrets in this
   repo:

   - `PORTAINER_WEBHOOK_PUBLIC` → public stack
   - `PORTAINER_WEBHOOK_ADMIN` → admin stack

   CI calls them after pushing images; a secret left unset is skipped
   with a notice in the workflow log (deploy simply doesn't happen until
   you set it or pull manually).

## Update loop

**Code changes** (frontend or API): push to `master` → GitHub Actions runs
the test job (lint + pytest + React tests), then builds and pushes the
three images and fires both webhooks → Portainer redeploys with the new
images. Nothing to do on the NAS.

**Data changes** (after a pipeline run): from the Mac, run
`make publish-data` (or `scripts/publish-public-data.sh [TARGET]`;
default target `nas:sotd-public/data`, override via
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

- **Stack won't start / 404 on images**: verify GHCR package visibility
  after the first CI run. The two public images
  (`sotd-pipeline-public-api`, `sotd-pipeline-public-frontend`) must be
  **public** — first pushes create packages private; flip them in the
  package settings. The admin image (`sotd-pipeline-admin`) is **private
  by design**: Portainer pulls it with the `ghcr-nmrs` registry
  credential (classic read:packages PAT, the same one myacuright uses)
  — add that credential to the sotd-admin stack in Portainer. Also
  confirm the NAS can reach `ghcr.io`.
- **CORS errors in the browser**: `SOTD_PUBLIC_ORIGIN` on the public
  stack doesn't match the actual origin.
- **Publish fails with a bundle error**: run the pipeline's aggregate
  phase for the missing months; the verifier refuses to publish a
  partial bundle rather than shipping a hole.
- **Admin unreachable**: it is LAN-only by design — check you're on the
  LAN and that `192.168.2.23` isn't claimed by another device.
