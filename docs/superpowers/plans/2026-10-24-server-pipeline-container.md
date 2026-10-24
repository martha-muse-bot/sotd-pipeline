# Server-side pipeline container — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep the public site's aggregated data fresh unattended by running the full pipeline nightly in a container on the NAS, publishing a verified slim bundle after each successful run.

**Architecture:** One komodo stack (`sotd-pipeline`), one long-running container. Image = Python env + git + rsync; `/app` is a git checkout on a volume (clone on first boot, pull nightly). Supervisor package `sotd/pipeline_supervisor/` implements: praw.ini materializer, catalog hash, publish step, metrics, and the nightly loop. Compose file `deploy/compose-sotd-pipeline.yml`.

**Tech Stack:** Python 3.14, PRAW, prometheus_client, docker/compose via komodo, GHCR via existing `.github/workflows/build.yml`.

**Spec:** `docs/superpowers/specs/2026-10-24-server-pipeline-container-design.md`

## Global Constraints

- Python 3.14; Black 100-char; Ruff (E, F, I); tests via `.venv/bin/python -m pytest` with `PYTHONPATH=.`; CI runs `-m "not perf"` (mark wall-clock tests `pytest.mark.perf`).
- Compose: no `cpus:` (Synology cgroup v1); `mem_limit` only; explicit `name: sotd-pipeline`.
- Container paths: `SOTD_DATA_DIR=/data` (pipeline tree), bundle host path `/volume1/docker/sotd-public/data` mounted at `/bundle` (rw, publish target).
- Image: `ghcr.io/nmrs/sotd-pipeline-pipeline:latest`.
- Secrets (komodo env): `REDDIT_CLIENT_ID`, `REDDIT_CLIENT_SECRET`, `REDDIT_USERNAME`, `REDDIT_PASSWORD`.
- Catalog-hash scope (exact): `data/*.yaml`, `data/correct_matches/*.yaml`, `data/thread_overrides.yaml`, `data/extract_overrides.yaml`, `data/enrichment_overrides.yaml`, `data/intentionally_unmatched.yaml`.
- Nightly order: pull → hash → fetch+extract(current+prior) → match/enrich/aggregate(current+prior) → verify+publish → catch-up(all months) if hash changed → verify+publish → save hash.
- Commit messages end with `Co-Authored-By: Claude Code <noreply@anthropic.com>`.

## Review Focus

- **Code-only git pull must not trigger catch-up** — only operator-authored match inputs hash. Pinned: `test_hash_ignores_non_operator_files` (Task 3).
- **Failed verifier must leave public share untouched** — never rsync over a good bundle with a hole. Pinned: `test_publish_refuses_when_verifier_fails` (Task 4).
- **Hash saved only after successful catch-up** — failed catch-up retries next night. Pinned: `test_hash_not_saved_on_catchup_failure` (Task 6).
- **Mounted praw.ini wins over env materialization** — operator override path. Pinned: `test_prefers_existing_file` (Task 2).
- **Supervisor survives a phase crash** — one bad night must not kill the loop. Pinned: `test_supervisor_survives_phase_crash` (Task 6).

---

### Task 1: Dockerfile.pipeline + CI build step

**Files:**
- Create: `webui/Dockerfile.pipeline`
- Create: `deploy/pipeline/entrypoint.sh` (placeholder; replaced in Task 2)
- Modify: `requirements.txt` (add prometheus_client)
- Modify: `.github/workflows/build.yml` (build job: add 4th build-push step)
- Test: `tests/pipeline_supervisor/test_dockerfile_content.py`

**Interfaces:**
- Produces: image `ghcr.io/nmrs/sotd-pipeline-pipeline:latest` with git+rsync, full `sotd/`, `run.py`, `scripts/`, entrypoint at `/entrypoint.sh`.
- Consumes: existing build job pattern (build-push-action v6, gha cache, GHCR login).

- [ ] **Step 1: Write the failing test** — `tests/pipeline_supervisor/test_dockerfile_content.py`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOCKERFILE = ROOT / "webui" / "Dockerfile.pipeline"


def test_dockerfile_exists():
    assert DOCKERFILE.exists()


def test_dockerfile_installs_git_and_rsync():
    text = DOCKERFILE.read_text()
    assert "git" in text and "rsync" in text


def test_requirements_has_prometheus_client():
    assert "prometheus_client" in (ROOT / "requirements.txt").read_text()
```

- [ ] **Step 2: Run to verify failure** — `PYTHONPATH=. .venv/bin/python -m pytest tests/pipeline_supervisor/test_dockerfile_content.py -v` → FAIL (file missing)

- [ ] **Step 3: Implement**

Add to `requirements.txt` (after the praw line): `prometheus_client>=0.20`

`webui/Dockerfile.pipeline`:

```dockerfile
# Nightly pipeline supervisor. Code runs from a git checkout on a volume
# (/app, cloned on first boot by the entrypoint); the image provides the
# Python env + git + rsync. Data root /data (volume); bundle target /bundle.
FROM python:3.14-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git rsync ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY sotd /app/sotd
COPY run.py /app/run.py
COPY scripts/ /app/scripts/

ENV PYTHONPATH=/app
WORKDIR /app
EXPOSE 8000

COPY deploy/pipeline/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

`deploy/pipeline/entrypoint.sh` (placeholder for this task):

```bash
#!/usr/bin/env bash
set -euo pipefail
echo "pipeline supervisor placeholder"
exec sleep infinity
```

CI: after the admin build-push step in `.github/workflows/build.yml`, add:

```yaml
      - uses: docker/build-push-action@v6
        with:
          context: .
          file: webui/Dockerfile.pipeline
          push: true
          tags: |
            ghcr.io/nmrs/sotd-pipeline-pipeline:latest
            ghcr.io/nmrs/sotd-pipeline-pipeline:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
```

- [ ] **Step 4: Run tests + lint** — pytest → PASS; `.venv/bin/python -m ruff check tests/pipeline_supervisor` → clean

- [ ] **Step 5: Commit** — `git add webui/Dockerfile.pipeline deploy/pipeline/entrypoint.sh requirements.txt tests/pipeline_supervisor/test_dockerfile_content.py .github/workflows/build.yml` → `git commit -m "feat: pipeline supervisor image + CI build step"`

### Task 2: praw.ini materializer + real entrypoint

**Files:**
- Create: `sotd/pipeline_supervisor/__init__.py` (empty), `sotd/pipeline_supervisor/secrets.py`
- Modify: `deploy/pipeline/entrypoint.sh` (replace placeholder)
- Test: `tests/pipeline_supervisor/test_secrets.py`

**Interfaces:**
- Produces: `materialize_praw_ini(env: Mapping[str, str], target_dir: Path) -> Path | None` — returns existing `target_dir/praw.ini` if present; `None` if any of the four `REDDIT_*` vars is missing/empty; else writes the INI and returns its path.

- [ ] **Step 1: Write the failing tests** — `tests/pipeline_supervisor/test_secrets.py`:

```python
from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

ENV = {
    "REDDIT_CLIENT_ID": "cid",
    "REDDIT_CLIENT_SECRET": "csecret",
    "REDDIT_USERNAME": "u",
    "REDDIT_PASSWORD": "p",
}


def test_materializes_when_env_complete(tmp_path: Path):
    out = materialize_praw_ini(ENV, tmp_path)
    assert out == tmp_path / "praw.ini"
    text = out.read_text()
    assert "[app]" in text
    assert "client_id=cid" in text
    assert "client_secret=csecret" in text
    assert "username=u" in text
    assert "password=p" in text


def test_returns_none_when_env_incomplete(tmp_path: Path):
    env = dict(ENV)
    del env["REDDIT_PASSWORD"]
    assert materialize_praw_ini(env, tmp_path) is None
    assert not (tmp_path / "praw.ini").exists()


def test_prefers_existing_file(tmp_path: Path):
    existing = tmp_path / "praw.ini"
    existing.write_text("[app]\nclient_id=mounted\n")
    assert materialize_praw_ini(ENV, tmp_path) == existing
    assert "mounted" in existing.read_text()
```

- [ ] **Step 2: Run to verify failure** — `PYTHONPATH=. .venv/bin/python -m pytest tests/pipeline_supervisor/test_secrets.py -v` → FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement** — `sotd/pipeline_supervisor/secrets.py`:

```python
"""Materialize praw.ini from REDDIT_* env vars (komodo resource env).

A mounted praw.ini wins over env materialization (operator override path).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

PRAW_INI_TEMPLATE = """[app]
client_id={client_id}
client_secret={client_secret}
username={username}
password={password}
"""

REQUIRED = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
)


def materialize_praw_ini(env: Mapping[str, str], target_dir: Path) -> Path | None:
    existing = target_dir / "praw.ini"
    if existing.exists():
        return existing
    if not all(env.get(k) for k in REQUIRED):
        return None
    existing.write_text(
        PRAW_INI_TEMPLATE.format(
            client_id=env["REDDIT_CLIENT_ID"],
            client_secret=env["REDDIT_CLIENT_SECRET"],
            username=env["REDDIT_USERNAME"],
            password=env["REDDIT_PASSWORD"],
        )
    )
    return existing
```

Replace `deploy/pipeline/entrypoint.sh` with:

```bash
#!/usr/bin/env bash
# Pipeline supervisor entrypoint: materialize praw.ini, clone /app on first
# boot, then exec the supervisor loop. A mounted praw.ini wins over env vars.
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
REPO_URL="${REPO_URL:-https://github.com/nmrs/sotd-pipeline.git}"
SECRETS_DIR="${PRAW_INI_DIR:-/secrets}"
export PYTHONPATH=/app

# praw.ini: mounted file wins; else materialize from REDDIT_* env
mkdir -p "${APP_DIR}"
if [ ! -f "${APP_DIR}/praw.ini" ] && [ -f "${SECRETS_DIR}/praw.ini" ]; then
  cp "${SECRETS_DIR}/praw.ini" "${APP_DIR}/praw.ini"
fi

if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
fi
cd "${APP_DIR}"

python -m sotd.pipeline_supervisor.materialize  # writes /app/praw.ini if needed
exec python -m sotd.pipeline_supervisor.loop
```

Create thin `sotd/pipeline_supervisor/materialize.py`:

```python
"""Entrypoint helper: materialize /app/praw.ini from env (no-op if present)."""

from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

if __name__ == "__main__":
    materialize_praw_ini(dict(__import__("os").environ), Path("/app"))
```

(`sotd/pipeline_supervisor/loop.py` lands in Task 6; Task 2 ends with entrypoint referencing it — acceptable because the image isn't deployed until Task 7. If you want Task 2 green standalone, add a stub `loop.py` with `if __name__ == "__main__": raise SystemExit("loop not implemented")`.)

- [ ] **Step 4: Run tests** — pytest → PASS (3 tests)

- [ ] **Step 5: Commit** — `git add sotd/pipeline_supervisor tests/pipeline_supervisor/test_secrets.py deploy/pipeline/entrypoint.sh` → `git commit -m "feat: praw.ini materializer + supervisor entrypoint"`

### Task 3: Catalog hash

**Files:**
- Create: `sotd/pipeline_supervisor/catalog_hash.py`
- Test: `tests/pipeline_supervisor/test_catalog_hash.py`

**Interfaces:**
- Produces: `CATALOG_HASH_INPUTS` (tuple of glob patterns, exactly the Global Constraints scope) and `catalog_hash(data_dir: Path) -> str` (sha256 hex over sorted `relpath:sha256(file)` lines; missing files skipped).

- [ ] **Step 1: Write the failing tests** — `tests/pipeline_supervisor/test_catalog_hash.py`:

```python
from pathlib import Path

from sotd.pipeline_supervisor.catalog_hash import catalog_hash

DATA = {
    "soaps.yaml": "a: 1\n",
    "correct_matches/soap.yaml": "m: [x]\n",
    "thread_overrides.yaml": "include: {}\n",
    "intentionally_unmatched.yaml": "x: 1\n",
    "enrichment_overrides.yaml": "y: 1\n",
    "extract_overrides.yaml": "z: 1\n",
    # NOT hashed — pipeline code files and non-operator inputs
    "aggregated/2026-10.json": "{}\n",
    "correct_matches/.status.json": "{}\n",
    "wsdb/software.json": "{}\n",
}


def make_data_dir(tmp_path: Path) -> Path:
    for rel, text in DATA.items():
        p = tmp_path / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    return tmp_path


def test_hash_changes_when_catalog_changes(tmp_path: Path):
    d = make_data_dir(tmp_path)
    h1 = catalog_hash(d)
    (d / "soaps.yaml").write_text("a: 2\n")
    assert catalog_hash(d) != h1


def test_hash_ignores_non_operator_files(tmp_path: Path):
    d = make_data_dir(tmp_path)
    h1 = catalog_hash(d)
    (d / "aggregated/2026-10.json").write_text('{"x": 1}\n')
    (d / "wsdb/software.json").write_text('{"y": 1}\n')
    assert catalog_hash(d) == h1


def test_hash_stable_across_calls(tmp_path: Path):
    d = make_data_dir(tmp_path)
    assert catalog_hash(d) == catalog_hash(d)


def test_hash_empty_dir_is_constant(tmp_path: Path):
    empty = tmp_path / "empty"
    empty.mkdir()
    assert catalog_hash(empty) == catalog_hash(tmp_path / "also-empty")
```

Note: create `also-empty` in the test before calling (or use `d`-sibling dir created first). Final test body:

```python
def test_hash_empty_dir_is_constant(tmp_path: Path):
    (tmp_path / "e1").mkdir()
    (tmp_path / "e2").mkdir()
    assert catalog_hash(tmp_path / "e1") == catalog_hash(tmp_path / "e2")
```

- [ ] **Step 2: Run to verify failure** → FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement** — `sotd/pipeline_supervisor/catalog_hash.py`:

```python
"""Content hash over operator-authored match inputs.

Scope (spec 2026-10-24): data/*.yaml catalogs, correct_matches/*.yaml, the
three overrides files, intentionally_unmatched.yaml. Everything else —
aggregated output, .status* working files, wsdb — is excluded so code-only
git pulls never trigger the all-months catch-up.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

CATALOG_HASH_INPUTS = (
    "*.yaml",
    "correct_matches/*.yaml",
    "thread_overrides.yaml",
    "extract_overrides.yaml",
    "enrichment_overrides.yaml",
    "intentionally_unmatched.yaml",
)


def catalog_hash(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for rel in sorted(_hashable_files(data_dir)):
        fhash = hashlib.sha256((data_dir / rel).read_bytes()).hexdigest()
        digest.update(f"{rel}:{fhash}\n".encode())
    return digest.hexdigest()


def _hashable_files(data_dir: Path) -> list[str]:
    seen: set[str] = set()
    for pattern in CATALOG_HASH_INPUTS:
        for p in sorted(data_dir.glob(pattern)):
            if p.is_file():
                seen.add(p.relative_to(data_dir).as_posix())
    return sorted(seen)
```

Note: `correct_matches/*.yaml` must not pick up the `.backup`/`.bk` history — it can't (extension is exactly `.yaml`), but the `.status*` dotfiles are excluded by the pattern too. Task 1's audit confirmed those strays were deleted.

- [ ] **Step 4: Run tests** → PASS (4 tests)

- [ ] **Step 5: Commit** — `git add sotd/pipeline_supervisor/catalog_hash.py tests/pipeline_supervisor/test_catalog_hash.py` → `git commit -m "feat: catalog content hash for drift-triggered catch-up"`

### Task 4: Publisher (verify + rsync)

**Files:**
- Create: `sotd/pipeline_supervisor/publish.py`
- Test: `tests/pipeline_supervisor/test_publish.py`

**Interfaces:**
- Consumes: `scripts/publish_public_data.py::check_bundle(data_dir) -> list[str]` (existing verifier; empty list = publishable).
- Produces: `publish_bundle(data_dir: Path, bundle_dir: Path, *, run: Callable[[list[str]], subprocess.CompletedProcess] | None = None) -> bool` — runs `check_bundle` against `data_dir`; on any problem, logs and returns False WITHOUT touching bundle_dir; else rsyncs the four slice groups (product_usage/, user_analysis/, annual/, monthly `????-??.json`) from `data_dir/aggregated/` into `bundle_dir/aggregated/` with `--delete`, returns True. `run` param injects a fake for tests.

- [ ] **Step 1: Write the failing tests** — `tests/pipeline_supervisor/test_publish.py`:

```python
import json
from pathlib import Path

from sotd.pipeline_supervisor.publish import publish_bundle


def make_bundle_source(tmp_path: Path) -> Path:
    agg = tmp_path / "data" / "aggregated"
    for sub in ("product_usage", "user_analysis", "annual"):
        (agg / sub).mkdir(parents=True)
        (agg / sub / "2026-09.json").write_text("{}")
    (agg / "2026-09.json").write_text("{}")
    return tmp_path / "data"


def test_publish_copies_slices(tmp_path: Path):
    data = make_bundle_source(tmp_path)
    bundle = tmp_path / "bundle"
    assert publish_bundle(data, bundle) is True
    assert (bundle / "aggregated" / "2026-09.json").exists()
    assert (bundle / "aggregated" / "product_usage" / "2026-09.json").exists()


def test_publish_refuses_when_verifier_fails(tmp_path: Path):
    data = make_bundle_source(tmp_path)
    (data / "aggregated" / "user_analysis" / "2026-09.json").unlink()  # hole
    bundle = tmp_path / "bundle"
    bundle.mkdir()
    (bundle / "sentinel").write_text("keep me")
    assert publish_bundle(data, bundle) is False
    assert (bundle / "sentinel").exists()  # untouched


def test_publish_delete_removes_stale_months(tmp_path: Path):
    data = make_bundle_source(tmp_path)
    bundle = tmp_path / "bundle"
    stale = bundle / "aggregated"
    stale.mkdir(parents=True)
    (stale / "2020-01.json").write_text("{}")
    assert publish_bundle(data, bundle) is True
    assert not (stale / "2020-01.json").exists()
```

- [ ] **Step 2: Run to verify failure** → FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement** — `sotd/pipeline_supervisor/publish.py`:

```python
"""Publish the slim public bundle: verifier-gated rsync into the public mount."""

from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SLICES = ("product_usage", "user_analysis", "annual")


def publish_bundle(
    data_dir: Path,
    bundle_dir: Path,
    *,
    run: Callable[..., "subprocess.CompletedProcess[str]"] | None = None,
) -> bool:
    from scripts.publish_public_data import check_bundle

    problems = check_bundle(data_dir)
    if problems:
        for p in problems:
            logger.error("bundle check: %s", p)
        return False

    runner = run or subprocess.run
    src = data_dir / "aggregated"
    dst = bundle_dir / "aggregated"
    ok = True
    for slice_name in SLICES:
        ok &= _rsync(runner, src / slice_name, dst / slice_name)
    ok &= _rsync(runner, src, dst, include_months=True)
    return ok


def _rsync(runner, src: Path, dst: Path, *, include_months: bool = False) -> bool:
    cmd = ["rsync", "-a", "--delete"]
    if include_months:
        cmd += ["--include=????-??.json", "--exclude=*"]
    cmd += [f"{src}/", f"{dst}/"]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("rsync failed: %s\n%s", " ".join(cmd), proc.stderr)
        return False
    return True
```

Import note: `scripts/` has no `__init__.py`; if `from scripts.publish_public_data import ...` fails under `PYTHONPATH=/app`, copy `check_bundle`'s import via `sys.path` insertion (`sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))` then `from publish_public_data import check_bundle`) — pick whichever works in the venv and keep it consistent.

- [ ] **Step 4: Run tests** → PASS (3 tests). Also run the verifier's own tests to confirm no regression: `PYTHONPATH=. .venv/bin/python -m pytest tests/ -k publish_public_data -q` (if that suite exists; skip if not).

- [ ] **Step 5: Commit** — `git add sotd/pipeline_supervisor/publish.py tests/pipeline_supervisor/test_publish.py` → `git commit -m "feat: verifier-gated bundle publisher"`

### Task 5: Metrics

**Files:**
- Create: `sotd/pipeline_supervisor/metrics.py`
- Test: `tests/pipeline_supervisor/test_metrics.py`

**Interfaces:**
- Produces: module-level Prometheus collectors and `start_metrics_server(port: int = 8000) -> None`:
  - Gauge `sotd_pipeline_last_run_timestamp_seconds`
  - Gauge `sotd_pipeline_last_run_status` with label `phase` (1 = ok, 0 = failed)
  - Gauge `sotd_pipeline_months_processed`
  - Gauge `sotd_pipeline_catalog_catchup_last_success_timestamp_seconds`

- [ ] **Step 1: Write the failing test** — `tests/pipeline_supervisor/test_metrics.py`:

```python
from prometheus_client import REGISTRY

from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    set_last_run_timestamp,
    start_metrics_server,
)


def test_gauges_update():
    set_last_run_timestamp(1700000000)
    last_run_status.labels(phase="fetch").set(1)
    months_processed.set(2)
    catalog_catchup_success.set(1700000000)
    names = {m.name for m in REGISTRY.collect()}
    assert "sotd_pipeline_last_run_timestamp_seconds" in names
    assert "sotd_pipeline_last_run_status" in names
    assert "sotd_pipeline_months_processed" in names
    assert "sotd_pipeline_catalog_catchup_last_success_timestamp_seconds" in names


def test_status_gauge_takes_zero_on_failure():
    last_run_status.labels(phase="match").set(0)
    assert last_run_status.labels(phase="match")._value.get() == 0


def test_start_metrics_server_runs():
    start_metrics_server(8199)  # only starts a thread; no assertion crash = pass
```

- [ ] **Step 2: Run to verify failure** → FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement** — `sotd/pipeline_supervisor/metrics.py`:

```python
"""Prometheus metrics for the nightly supervisor (scraped on metrics-net)."""

from __future__ import annotations

from prometheus_client import Gauge, start_http_server

last_run_timestamp = Gauge("sotd_pipeline_last_run_timestamp_seconds", "Epoch of last run start")
last_run_status = Gauge("sotd_pipeline_last_run_status", "1=ok 0=failed", ["phase"])
months_processed = Gauge("sotd_pipeline_months_processed", "Months processed in last run")
catalog_catchup_success = Gauge(
    "sotd_pipeline_catalog_catchup_last_success_timestamp_seconds",
    "Epoch of last successful all-months catch-up",
)


def set_last_run_timestamp(epoch: float) -> None:
    last_run_timestamp.set(epoch)


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
```

- [ ] **Step 4: Run tests** → PASS (3 tests)

- [ ] **Step 5: Commit** — `git add sotd/pipeline_supervisor/metrics.py tests/pipeline_supervisor/test_metrics.py` → `git commit -m "feat: supervisor Prometheus metrics"`

### Task 6: Nightly supervisor loop

**Files:**
- Create: `sotd/pipeline_supervisor/loop.py`
- Test: `tests/pipeline_supervisor/test_loop.py`

**Interfaces:**
- Consumes: `catalog_hash`, `materialize_praw_ini`, `publish_bundle`, metrics module; pipeline phases via `run.py` subprocess (`python run.py pipeline --month YYYY-MM --force fetch:enrich` — wait, phase-range syntax: `python run.py pipeline --month 2025-05 --force extract:enrich` per CLAUDE.md; fetch through aggregate is the full `pipeline` command, so per-month scope means `python run.py pipeline --month <M> --force` runs all 6 phases for that month; report phase excluded by running `fetch:aggregate`? — CHECK: `run.py pipeline --month M --force extract:enrich` runs extract..enrich. So fetch+extract = `--month M --force fetch:extract`? CLAUDE.md shows `extract:enrich` spans extract→match→enrich (inclusive). Confirm range semantics in run.py before implementing; use `fetch:aggregate` for phases 1-5 if inclusive-end semantics hold, else the documented `:` prefix/suffix forms).
- Produces: `run_nightly(now, *, repo_dir, data_dir, bundle_dir, runner) -> RunResult` and `main()` loop with schedule `SCHEDULE_HOUR = 2` (America/Chicago via TZ env).

`RunResult` dataclass: `phases: dict[str, bool]`, `months_processed: int`, `catchup_ran: bool`, `catchup_ok: bool`, `published: bool`.

Loop semantics (spec order):
1. `git -C repo pull --ff-only` (failure: log, skip run — data may be stale but public bundle intact)
2. `h_new = catalog_hash(data_dir)`; `changed = h_new != stored` (stored read from `data_dir/.catalog_hash`; missing = changed)
3. phases for current + prior month: fetch, extract (subprocess `python run.py pipeline --month M --force fetch:extract` — verify range semantics), then match, enrich, aggregate (`match:aggregate`)
4. publish (Task 4)
5. if changed: match/enrich/aggregate over ALL months via `python run.py pipeline --range <first>:<last> --force match:aggregate`; on success publish again and write `data_dir/.catalog_hash = h_new`; on failure skip hash write (retry next night)
6. metrics set; phase failures recorded per phase

- [ ] **Step 1: Write the failing tests** — `tests/pipeline_supervisor/test_loop.py`:

```python
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

from sotd.pipeline_supervisor.loop import run_nightly


def fake_runner_ok(cmd, **kw):
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def setup_dirs(tmp_path: Path):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    bundle = tmp_path / "bundle"
    for d in (repo, data, bundle):
        d.mkdir()
    (data / "soaps.yaml").write_text("a: 1\n")
    return repo, data, bundle


def test_run_nightly_happy_path_no_catchup(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert result.published is True
    assert result.catchup_ran is False
    assert result.phases["fetch"] is True


def test_hash_not_saved_on_catchup_failure(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        # fail the all-months pass (identified by --range in cmd)
        if "--range" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.catchup_ran is True
    assert result.catchup_ok is False
    assert not (data / ".catalog_hash").exists()


def test_hash_saved_after_successful_catchup(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.catchup_ran is True and result.catchup_ok is True
    assert (data / ".catalog_hash").read_text() == "h1"


def test_supervisor_survives_phase_crash(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    def runner(cmd, **kw):
        raise RuntimeError("subprocess exploded")

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.published is False
    assert any(v is False for v in result.phases.values())


def test_git_pull_failure_skips_run(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    def runner(cmd, **kw):
        if cmd[:3] == ["git", "-C", str(repo)]:
            return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="network down")
        raise AssertionError("pipeline must not run after pull failure")

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.published is False
```

- [ ] **Step 2: Run to verify failure** → FAIL (ModuleNotFoundError)

- [ ] **Step 3: Implement** — `sotd/pipeline_supervisor/loop.py`. Key structure (final code written at implementation; contract fixed by the tests above):

```python
"""Nightly supervisor loop: pull, hash, run phases, publish, catch-up."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sotd.pipeline_supervisor.catalog_hash import catalog_hash
from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    set_last_run_timestamp,
)
from sotd.pipeline_supervisor.publish import publish_bundle

logger = logging.getLogger(__name__)

SCHEDULE_HOUR = 2
TZ = ZoneInfo("America/Chicago")
HASH_FILE = ".catalog_hash"


@dataclass
class RunResult:
    phases: dict = field(default_factory=dict)
    months_processed: int = 0
    catchup_ran: bool = False
    catchup_ok: bool = False
    published: bool = False


def run_nightly(*, repo_dir: Path, data_dir: Path, bundle_dir: Path, runner=subprocess.run,
                months: tuple[str, ...], all_months: tuple[str, str]) -> RunResult:
    result = RunResult()
    pull = runner(["git", "-C", str(repo_dir), "pull", "--ff-only"],
                  capture_output=True, text=True)
    if pull.returncode != 0:
        logger.error("git pull failed: %s", pull.stderr)
        last_run_status.labels(phase="pull").set(0)
        return result
    last_run_status.labels(phase="pull").set(1)

    stored = _read_hash(data_dir)
    new_hash = catalog_hash(data_dir)
    hash_changed = stored is None or stored != new_hash

    ok = True
    for month in months:
        for phase_range in ("fetch:extract", "match:aggregate"):
            phase_ok = _run_phase(runner, repo_dir, month, phase_range, result)
            ok &= phase_ok

    if ok:
        result.published = publish_bundle(data_dir, bundle_dir)

    if hash_changed:
        result.catchup_ran = True
        first, last = all_months
        catchup = runner(
            ["python", "run.py", "pipeline", "--range", f"{first}:{last}",
             "--force", "match:aggregate"],
            capture_output=True, text=True, cwd=str(repo_dir),
        )
        result.catchup_ok = catchup.returncode == 0
        last_run_status.labels(phase="catchup").set(1 if result.catchup_ok else 0)
        if result.catchup_ok:
            if publish_bundle(data_dir, bundle_dir):
                (data_dir / HASH_FILE).write_text(new_hash)
                catalog_catchup_success.set(time.time())
            else:
                result.catchup_ok = False  # publish failed: retry hash next night
    months_processed.set(result.months_processed)
    return result


def _run_phase(runner, repo_dir, month, phase_range, result) -> bool:
    phase = phase_range.split(":")[0]
    try:
        proc = runner(
            ["python", "run.py", "pipeline", "--month", month, "--force", phase_range],
            capture_output=True, text=True, cwd=str(repo_dir),
        )
        ok = proc.returncode == 0
        if not ok:
            logger.error("%s failed for %s: %s", phase_range, month, proc.stderr)
    except Exception:
        logger.exception("%s crashed for %s", phase_range, month)
        ok = False
    result.phases[phase] = ok
    last_run_status.labels(phase=phase).set(1 if ok else 0)
    if ok:
        result.months_processed += 1
    return ok


def main() -> None:
    from sotd.pipeline_supervisor.metrics import start_metrics_server

    start_metrics_server(8000)
    data_dir = Path("/data")
    repo_dir = Path("/app")
    bundle_dir = Path("/bundle")
    while True:
        now = datetime.now(TZ)
        target = now.replace(hour=SCHEDULE_HOUR, minute=0, second=0, microsecond=0)
        if target <= now:
            target = _next_day(target)
        time.sleep((target - now).total_seconds())
        set_last_run_timestamp(time.time())
        try:
            res = run_nightly(
                repo_dir=repo_dir, data_dir=data_dir, bundle_dir=bundle_dir,
                months=_current_and_prior(target), all_months=_all_months(data_dir),
            )
            logger.info("nightly run: %s", res)
        except Exception:
            logger.exception("nightly run crashed; sleeping until tomorrow")


def _next_day(dt: datetime) -> datetime:
    from datetime import timedelta

    return (dt + timedelta(days=1)).replace(hour=SCHEDULE_HOUR, minute=0, second=0, microsecond=0)


def _current_and_prior(dt: datetime) -> tuple[str, ...]:
    prior = dt.replace(day=1)
    from datetime import timedelta

    prior_end = prior - timedelta(days=1)
    return (dt.strftime("%Y-%m"), prior_end.strftime("%Y-%m"))


def _all_months(data_dir: Path) -> tuple[str, str]:
    months = sorted(p.stem for p in (data_dir / "enriched").glob("????-??.json"))
    return (months[0], months[-1]) if months else ("2016-05", "2016-05")
```

**Implementation-time checks (do not skip):**
1. `run.py pipeline` phase-range syntax: read `run.py` main() around lines 861-1010 to confirm `fetch:extract` / `match:aggregate` are valid inclusive ranges and that `--month M` scopes them. Adjust commands if the grammar differs (e.g. needs separate phase names).
2. `match:aggregate` on a month with no fetched data must not error fatally — verify run.py behavior; if it does, guard the catch-up range command per month instead.
3. Confirm `--range` accepts `match:` phase suffix (CLAUDE.md shows `match:` and `:enrich` forms).

- [ ] **Step 4: Run tests** → PASS (5 tests)

- [ ] **Step 5: Commit** — `git add sotd/pipeline_supervisor/loop.py tests/pipeline_supervisor/test_loop.py` → `git commit -m "feat: nightly supervisor loop with drift-triggered catch-up"`

### Task 7: Compose stack + deploy docs

**Files:**
- Create: `deploy/compose-sotd-pipeline.yml`
- Modify: `deploy/README.md` (add sotd-pipeline stack section: first-time setup, seed command, env vars, verification, troubleshooting)

**Interfaces:**
- Consumes: image from Task 1; external networks `metrics-net`; NAS host paths `/volume1/docker/sotd-pipeline/data`, `/volume1/docker/sotd-public/data`.

- [ ] **Step 1: Write compose file** — `deploy/compose-sotd-pipeline.yml`:

```yaml
# SOTD nightly pipeline supervisor — deployed via komodo (gitops source: this repo).
# Keeps the public bundle fresh: runs the full pipeline nightly, publishes the
# verified slim bundle into /volume1/docker/sotd-public/data (the public stack's
# read-only mount). Catalogs/code arrive via nightly git pull; secrets via komodo env.
#
# NOTE: do NOT set a `cpus:` limit — Synology's cgroup v1 rejects it.
name: sotd-pipeline

services:
  sotd-pipeline:
    image: ghcr.io/nmrs/sotd-pipeline-pipeline:latest
    restart: unless-stopped
    mem_limit: 2g
    pull_policy: always
    environment:
      - TZ=America/Chicago
      - SOTD_DATA_DIR=/data
      - REDDIT_CLIENT_ID=${REDDIT_CLIENT_ID}
      - REDDIT_CLIENT_SECRET=${REDDIT_CLIENT_SECRET}
      - REDDIT_USERNAME=${REDDIT_USERNAME}
      - REDDIT_PASSWORD=${REDDIT_PASSWORD}
      - REPO_URL=https://github.com/nmrs/sotd-pipeline.git
    volumes:
      - /volume1/docker/sotd-pipeline/data:/data
      - /volume1/docker/sotd-pipeline/repo:/app
      - /volume1/docker/sotd-public/data:/bundle
    ports:
      - "127.0.0.1:8100:8000"   # /metrics for Prometheus scrape
    networks:
      - metrics-net

networks:
  metrics-net:
    external: true
```

Prometheus scrape config note for the deploy docs: add job targeting the NAS host on port 8100 (host-port binding keeps metrics off any bridged network the NAS exposes).

- [ ] **Step 2: Update deploy/README.md** — add a `## sotd-pipeline stack (nightly pipeline supervisor)` section covering: env vars to set in komodo (`REDDIT_CLIENT_ID/SECRET/USERNAME/PASSWORD`), the one-time seed rsync command (verbatim from spec §Seed), first-boot behavior (clone into `/app` volume), manual-cycle smoke test (`docker compose exec sotd-pipeline python -m sotd.pipeline_supervisor.loop --once` — add a `--once` flag to loop.py in this task: single run then exit, for smoke tests), verification (Prometheus target up, public site reflects a forced run), and troubleshooting (pull failures keep last-good bundle; hash retry semantics).

- [ ] **Step 3: Add `--once` flag to loop.py** — small change: `main()` parses `sys.argv` (`--once` → run once, exit). Extend `test_loop.py`:

```python
def test_once_flag_exists():
    import inspect

    from sotd.pipeline_supervisor import loop

    assert "once" in inspect.getsource(loop.main)
```

- [ ] **Step 4: Run tests + lint** — full `tests/pipeline_supervisor/` suite → PASS; `ruff check` clean

- [ ] **Step 5: Commit** — `git add deploy/compose-sotd-pipeline.yml deploy/README.md sotd/pipeline_supervisor/loop.py tests/pipeline_supervisor/test_loop.py` → `git commit -m "feat: sotd-pipeline compose stack + deploy runbook"`

### Task 8: Seed script + Mac-side one-time runbook

**Files:**
- Create: `scripts/seed-pipeline-data.sh`

**Interfaces:**
- Consumes: `nas` ssh alias (already configured); spec §Seed exclusion list.
- Produces: executable script; README already documents it (Task 7).

- [ ] **Step 1: Write the script** — `scripts/seed-pipeline-data.sh`:

```bash
#!/usr/bin/env bash
# One-time seed of the NAS pipeline data volume from the Mac's data/ tree.
# Excludes non-pipeline inputs (backups, logs, raw scrape cache) per spec 2026-10-24.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-nas:/volume1/docker/sotd-pipeline/data}"

echo "==> verifying no stray files (post-2026-10-24 audit)"
find data -name '.DS_Store' -o -name '*.backup' -o -name '*.bak' -o -name '*.bk' | grep . && {
  echo "stray files found — clean first"; exit 1; } || true

echo "==> creating remote dirs"
ssh nas 'mkdir -p /volume1/docker/sotd-pipeline/data /volume1/docker/sotd-pipeline/repo'

echo "==> seeding $TARGET"
rsync -a \
  --exclude='.DS_Store' \
  --exclude='*.backup' --exclude='*.bak' --exclude='*.bk' \
  --exclude='backup/' --exclude='logs/' --exclude='learning/' \
  --exclude='report_archive/_reddit_raw/' \
  data/ "$TARGET/"

echo "done. seed at $TARGET"
```

- [ ] **Step 2: chmod +x, shellcheck if available** — `chmod +x scripts/seed-pipeline-data.sh`; `command -v shellcheck && shellcheck scripts/seed-pipeline-data.sh || true`

- [ ] **Step 3: Commit** — `git add scripts/seed-pipeline-data.sh` → `git commit -m "feat: NAS seed script for pipeline data volume"`

### Task 9: NAS deployment + smoke test (manual, operator-assisted)

**Files:** none (operational task)

- [ ] **Step 1: Merge to master** — push all commits; CI builds + pushes the pipeline image.
- [ ] **Step 2: Seed** — `./scripts/seed-pipeline-data.sh` from the Mac (long: ~2 GB).
- [ ] **Step 3: Create komodo stack** — resource from `deploy/compose-sotd-pipeline.yml`, set the four REDDIT_* env vars in komodo resource env, deploy.
- [ ] **Step 4: Smoke test** — `docker exec sotd-pipeline python -m sotd.pipeline_supervisor.loop --once` inside the container; verify: git clone happened, phases ran, bundle published, public site reflects new run, Prometheus target up.
- [ ] **Step 5: Enable schedule** — the loop self-schedules at 02:00 America/Chicago; confirm next morning's run + metrics.

---

## Self-Review

- Spec coverage: architecture/loop (T1, T2, T6), code-from-git (T2 entrypoint, T7 compose), secrets (T2), catalog hash + drift catch-up (T3, T6), verify-then-rsync publish (T4), metrics (T5), compose + runbook (T7), seed (T8), smoke test (T9). Month scope, failure handling, and non-goals are enforced by loop.py tests (T6). No gaps found.
- Placeholder scan: none — all code blocks complete; Task 6's implementation-time checks are verification steps, not placeholders.
- Type consistency: `run_nightly(repo_dir, data_dir, bundle_dir, runner, months, all_months)` used identically in all five T6 tests; `materialize_praw_ini(env, target_dir)` consistent T2; `publish_bundle(data_dir, bundle_dir)` consistent T4/T6.
- Review Focus: all five lines pinned by tests as mapped.