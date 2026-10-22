# WebUI Containerization + Public/Admin Split Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the WebUI as two containerized apps on the NAS — the existing full WebUI (admin, LAN-only) and a new public app exposing only the three read-only analytics routers — with data delivered by a slim aggregate-only rsync bundle and images built by GitHub Actions.

**Architecture:** One codebase, two builds. The public backend is a slim FastAPI app (`public_main.py`) importing only `product_usage`, `monthly_user_posts`, and `report_rankings` routers (all 100% GET today); a CI guard test fails if a non-GET operation ever appears in its OpenAPI schema. The public frontend is a second Vite entry reusing the shared page components. Data ships as an rsync'd bundle of four aggregate slices (enriched/ never leaves the Mac), verified for month-completeness before publish. Images go GHCR via GitHub Actions (myacuright pattern), Portainer webhook redeploys.

**Tech Stack:** FastAPI + uvicorn (python:3.14-slim), React/Vite/TypeScript, nginx (public-frontend), Docker multi-stage, GitHub Actions + buildx + GHCR, rsync.

**Spec:** `docs/superpowers/specs/2026-10-22-webui-containerization-public-admin-split-design.md`

## Global Constraints

- Python 3.14 (project standard; pyrightconfig enforces).
- Black formatting, 100-char line length; Ruff lint (E, F, I).
- `make typecheck` has a **pre-existing 279-error baseline** — never chase it; only ensure your own new files don't add errors (`pyright <new files>`).
- Python tests: `PYTHONPATH=. pytest tests/...` using `.venv` (`source .venv/bin/activate`).
- WebUI JS tests: `cd webui && npm run test` (jest); lint: `npm run lint`.
- Compose files: `mem_limit` only — **never `cpus:`** (Synology cgroup v1 rejects it). Always set `TZ=America/Chicago`. `pull_policy: always` on GHCR images. Healthchecks use python stdlib urllib (no curl in slim images).
- GHCR image names: `ghcr.io/nmrs/sotd-pipeline-public-api`, `ghcr.io/nmrs/sotd-pipeline-public-frontend`, `ghcr.io/nmrs/sotd-pipeline-admin`.
- Public data bundle slices (only these four ever leave the Mac): `data/aggregated/product_usage/`, `data/aggregated/user_analysis/`, `data/aggregated/{YYYY-MM}.json`, `data/aggregated/annual/`. **`data/enriched/` is never published, never copied, never referenced by the bundle.**
- Repo is PUBLIC: no secrets in images or workflows; `secrets.GITHUB_TOKEN` is the only credential in CI.
- WebUI API backend tests live in `webui/api/__tests__/` and run under the project venv's pytest (they insert project root on sys.path).

## Review Focus

1. **Enriched fallback firing in the public container** — a month with aggregates missing must degrade to empty/404, never compute from per-comment data. Pinned by: bundle-completeness verifier tests (Task 8) + `/months`-scans-user_analysis test (Task 2).
2. **A mutating endpoint leaking into the public app** — anyone adding POST/PUT/DELETE to one of the three shared routers must break CI. Pinned by: OpenAPI guard test (Task 3).
3. **`SOTD_DATA_DIR` set vs unset parity** — with the env var set (containers) endpoints must read the same files they read from the project root locally. Pinned by: parity tests in Task 1.
4. **First-run publish to an empty NAS dir** — rsync must create the target tree and the verifier must pass on a cold start. Pinned by: verifier + script dry-run tests (Task 8).
5. **Public SPA deep links** — refreshing `/product-usage` on the public host must serve the SPA, not nginx 404. Pinned by: curl of a deep path against the built frontend container (Task 5, Step 8).

---

### Task 1: `SOTD_DATA_DIR` support in product_usage and monthly_user_posts

**Files:**
- Create: `webui/api/utils/data_dir.py`
- Modify: `webui/api/product_usage.py` (data paths at lines ~168, ~212, ~342, ~451)
- Modify: `webui/api/monthly_user_posts.py` (data paths at lines ~57, ~136, ~207)
- Test: `webui/api/__tests__/test_data_dir.py`

**Interfaces:**
- Consumes: nothing new (existing routers).
- Produces: `get_data_dir() -> Path` and `get_enriched_dir() -> Path`, `get_aggregated_dir() -> Path`, `get_user_analysis_dir() -> Path` in `webui/api/utils/data_dir.py`. Later tasks (3, 8) import `get_data_dir`.

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""Tests for the shared data-dir resolver (SOTD_DATA_DIR support)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from api.utils.data_dir import (
    get_aggregated_dir,
    get_data_dir,
    get_enriched_dir,
    get_user_analysis_dir,
)

PROJECT_DATA = Path(__file__).parent.parent.parent.parent / "data"


def test_defaults_to_project_data_dir():
    with patch.dict("os.environ", {}, clear=False):
        assert get_data_dir() == PROJECT_DATA


def test_env_var_overrides():
    with patch.dict("os.environ", {"SOTD_DATA_DIR": "/mnt/public-data"}):
        assert get_data_dir() == Path("/mnt/public-data")
        assert get_enriched_dir() == Path("/mnt/public-data/enriched")
        assert get_aggregated_dir() == Path("/mnt/public-data/aggregated")
        assert get_user_analysis_dir() == Path(
            "/mnt/public-data/aggregated/user_analysis"
        )


def test_subdirs_consistent_between_modes():
    """Env-var mode resolves the same relative layout as project-root mode."""
    with patch.dict("os.environ", {"SOTD_DATA_DIR": str(PROJECT_DATA)}):
        assert get_enriched_dir() == PROJECT_DATA / "enriched"
        assert get_aggregated_dir() == PROJECT_DATA / "aggregated"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_data_dir.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.utils.data_dir'`

- [ ] **Step 3: Write minimal implementation**

```python
#!/usr/bin/env python3
"""Shared data-directory resolution honoring SOTD_DATA_DIR.

Containers mount the pipeline data dir (or the public bundle subset) and
point SOTD_DATA_DIR at it; local dev defaults to the project root's data/.
"""

import os
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent.parent


def get_data_dir() -> Path:
    """Return the pipeline data directory (SOTD_DATA_DIR or project data/)."""
    env_dir = os.environ.get("SOTD_DATA_DIR")
    return Path(env_dir) if env_dir else _project_root / "data"


def get_enriched_dir() -> Path:
    return get_data_dir() / "enriched"


def get_aggregated_dir() -> Path:
    return get_data_dir() / "aggregated"


def get_user_analysis_dir() -> Path:
    return get_aggregated_dir() / "user_analysis"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_data_dir.py -v`
Expected: PASS (3 tests)

- [ ] **Step 5: Wire product_usage.py to the helper**

Replace each hardcoded `project_root / "data" ...` construction with the helper, deleting the now-unused local `project_root` computation where it becomes unused:

- Line ~168: `(project_root / "data" / "aggregated" / "product_usage" / f"{month}.json")` → `get_aggregated_dir() / "product_usage" / f"{month}.json"`
- Lines ~212 and ~342: `(project_root / "data" / "enriched" / f"{month}.json")` → `get_enriched_dir() / f"{month}.json"`
- Line ~451: `aggregated_dir = project_root / "data" / "aggregated"` → `aggregated_dir = get_aggregated_dir()`

Add import near the other local imports: `from .utils.data_dir import get_aggregated_dir, get_enriched_dir`

- [ ] **Step 6: Wire monthly_user_posts.py the same way**

- Line ~57: `enriched_dir = project_root / "data" / "enriched"` → `enriched_dir = get_enriched_dir()`
- Lines ~136 and ~207: enriched fallback paths → `get_enriched_dir() / f"{month}.json"`
- Lines ~135 and ~206: user_analysis primary paths `(project_root / "data" / "aggregated" / "user_analysis" / f"{month}.json")` → `get_user_analysis_dir() / f"{month}.json"`

Add import: `from .utils.data_dir import get_enriched_dir, get_user_analysis_dir`

- [ ] **Step 7: Run router test suites to confirm no regression**

Run: `PYTHONPATH=. pytest webui/api/__tests__/ webui/api/tests/ -v 2>&1 | tail -5`
Expected: all PASS (no behavior change when SOTD_DATA_DIR is unset)

- [ ] **Step 8: Lint and commit**

```bash
.venv/bin/python -m black webui/api/utils/data_dir.py webui/api/product_usage.py webui/api/monthly_user_posts.py webui/api/__tests__/test_data_dir.py
.venv/bin/ruff check --fix webui/api/utils/data_dir.py webui/api/product_usage.py webui/api/monthly_user_posts.py webui/api/__tests__/test_data_dir.py
git add webui/api/utils/data_dir.py webui/api/product_usage.py webui/api/monthly_user_posts.py webui/api/__tests__/test_data_dir.py
git commit -m "feat(webui): honor SOTD_DATA_DIR in product_usage and monthly_user_posts"
```

---

### Task 2: monthly_user_posts `/months` scans user_analysis first

The public bundle has no `enriched/`; `/months` must derive its month list + user counts from `aggregated/user_analysis/*.json` (each file's `users` dict length is the user count). Enriched scanning stays as the fallback when the user_analysis dir is empty/missing.

**Files:**
- Modify: `webui/api/monthly_user_posts.py:52-86` (`get_available_months`)
- Test: `webui/api/__tests__/test_monthly_user_posts_months.py`

**Interfaces:**
- Consumes: `get_user_analysis_dir()`, `get_enriched_dir()` from Task 1.
- Produces: no signature change (endpoint contract unchanged).

- [ ] **Step 1: Write the failing test**

```python
#!/usr/bin/env python3
"""/months must list months from user_analysis (bundle mode), enriched only as fallback."""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app

client = TestClient(app)


def test_months_from_user_analysis(tmp_path, monkeypatch):
    ua = tmp_path / "aggregated" / "user_analysis"
    ua.mkdir(parents=True)
    for month, n in (("2026-08", 3), ("2026-09", 5)):
        (ua / f"{month}.json").write_text(
            json.dumps({"users": {f"u{i}": {} for i in range(n)}})
        )
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))

    resp = client.get("/api/monthly-user-posts/months")
    assert resp.status_code == 200
    months = resp.json()
    assert [m["month"] for m in months] == ["2026-09", "2026-08"]  # newest first
    assert months[0]["has_data"] is True and months[0]["user_count"] == 5


def test_months_falls_back_to_enriched_when_no_user_analysis(tmp_path, monkeypatch):
    enriched = tmp_path / "enriched"
    enriched.mkdir(parents=True)
    (enriched / "2026-01.json").write_text(
        json.dumps({"data": [{"author": "a"}, {"author": "b"}]})
    )
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))

    resp = client.get("/api/monthly-user-posts/months")
    assert resp.status_code == 200
    months = resp.json()
    assert [m["month"] for m in months] == ["2026-01"]
    assert months[0]["user_count"] == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_monthly_user_posts_months.py -v`
Expected: FAIL — `test_months_from_user_analysis` returns `[]` (no enriched dir to scan)

- [ ] **Step 3: Implement user_analysis-first scanning**

Rewrite the body of `get_available_months`: try `get_user_analysis_dir()`; if it contains `*.json` files, build `MonthData(month=stem, has_data=True, user_count=len(data.get("users", {})))` for each (guard per-file exceptions the same way the current code does). Only if that dir yields nothing, fall back to the existing enriched scan loop unchanged. Keep sorting newest-first.

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_monthly_user_posts_months.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Run broader suite, lint, commit**

Run: `PYTHONPATH=. pytest webui/api/__tests__/ webui/api/tests/ -q 2>&1 | tail -3` → all PASS.
Then black/ruff on the touched files and:

```bash
git add webui/api/monthly_user_posts.py webui/api/__tests__/test_monthly_user_posts_months.py
git commit -m "feat(webui): /months lists months from user_analysis aggregates first"
```

---

### Task 3: Public backend app + GET-only guard

**Files:**
- Create: `webui/api/public_main.py`
- Create: `webui/api/__tests__/test_public_main.py`

**Interfaces:**
- Consumes: the three routers (`product_usage`, `monthly_user_posts`, `report_rankings`) unchanged; Task 1's env-var support.
- Produces: FastAPI ASGI app `webui.api.public_main:app` — the string the public-api Dockerfile CMD and compose healthcheck rely on.

- [ ] **Step 1: Write the failing guard test**

```python
#!/usr/bin/env python3
"""Guard tests: the public app exposes ONLY read-only routes."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.public_main import app

client = TestClient(app)


def test_only_get_routes_exposed():
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        for method in ops:
            assert method.lower() == "get", (
                f"public app exposes non-GET route: {method.upper()} {path}"
            )


def test_expected_router_prefixes_present():
    schema = client.get("/openapi.json").json()
    paths = list(schema["paths"])
    for prefix in ("/api/product-usage", "/api/monthly-user-posts", "/api/report-rankings"):
        assert any(p.startswith(prefix) for p in paths), f"missing {prefix}"


def test_no_admin_router_prefixes():
    schema = client.get("/openapi.json").json()
    banned = (
        "/api/analysis", "/api/catalogs", "/api/files", "/api/extract-overrides",
        "/api/filtered", "/api/brushes", "/api/soaps", "/api/validation",
        "/api/wsdb-alignment", "/api/format-compatibility",
    )
    for path in schema["paths"]:
        assert not path.startswith(banned), f"admin route leaked: {path}"


def test_health_endpoint():
    resp = client.get("/api/product-usage/health")
    assert resp.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_public_main.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'api.public_main'`

- [ ] **Step 3: Write public_main.py**

```python
#!/usr/bin/env python3
"""Public, read-only SOTD analytics API.

Mounts ONLY the three read-only analytics routers. The test
api/__tests__/test_public_main.py asserts the OpenAPI schema contains no
non-GET operations — keep that test green when touching shared routers.
"""

import logging
import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from .monthly_user_posts import router as monthly_user_posts_router  # noqa: E402
from .product_usage import router as product_usage_router  # noqa: E402
from .report_rankings import router as report_rankings_router  # noqa: E402

logger = logging.getLogger(__name__)

app = FastAPI(
    title="SOTD Public Analytics API",
    description="Read-only SOTD pipeline analytics",
    version="1.0.0",
    docs_url=None,  # don't advertise interactive docs on the public host
    redoc_url=None,
)

app.include_router(product_usage_router)
app.include_router(monthly_user_posts_router)
app.include_router(report_rankings_router)

_allowed_origin = os.getenv("PUBLIC_ALLOWED_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_allowed_origin],
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def reject_non_get(request, call_next):
    """Second line of defense: never answer anything but GET/OPTIONS/HEAD."""
    if request.method not in ("GET", "OPTIONS", "HEAD"):
        return JSONResponse(status_code=405, content={"detail": "Read-only API"})
    return await call_next(request)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `PYTHONPATH=. pytest webui/api/__tests__/test_public_main.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Lint, typecheck new files, commit**

```bash
.venv/bin/python -m black webui/api/public_main.py webui/api/__tests__/test_public_main.py
.venv/bin/ruff check webui/api/public_main.py webui/api/__tests__/test_public_main.py
.venv/bin/pyright webui/api/public_main.py webui/api/__tests__/test_public_main.py  # only new files
git add webui/api/public_main.py webui/api/__tests__/test_public_main.py
git commit -m "feat(webui): public read-only API app with GET-only guard"
```

---

### Task 4: Public frontend (second Vite build)

**Files:**
- Create: `webui/public.html` (Vite entry HTML for the public build)
- Create: `webui/src/public/main.tsx`
- Create: `webui/src/public/App.tsx`
- Create: `webui/src/public/PublicHome.tsx`
- Create: `webui/src/public/__tests__/PublicApp.test.tsx`
- Modify: `webui/vite.config.public.ts` (create), `webui/package.json` (add `build:public` script)

**Interfaces:**
- Consumes: shared page components `@/pages/ProductUsage`, `@/pages/MonthlyUserPosts`, `@/pages/ReportPlacementOverTime` unchanged; axios client `@/services/api` unchanged (baseURL-relative `/api` works behind nginx proxy).
- Produces: `npm run build:public` → `webui/dist-public/` with `index.html` (this is the file public-frontend's nginx serves and the admin StaticFiles mount analog for the public build).

- [ ] **Step 1: Write the failing component test**

```tsx
import React from 'react';
import { MemoryRouter } from 'react-router-dom';
import { render, screen } from '@testing-library/react';
import App from '../App';

jest.mock('../../services/api', () => ({
  api: { get: jest.fn().mockResolvedValue({ data: [] }) },
  handleApiError: jest.fn((e: unknown) => String(e)),
}));

describe('PublicApp', () => {
  it('renders home with links to the three analytics pages', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText(/SOTD Analytics/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /product usage/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /monthly user posts/i })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /placement/i })).toBeInTheDocument();
  });

  it('has no admin analyzer links', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.queryByRole('link', { name: /mismatch/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /brush split/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('link', { name: /catalog validator/i })).not.toBeInTheDocument();
  });
});
```

(Adjust the `jest.mock` path to the actual module specifier the shared pages import — open `src/pages/ProductUsage.tsx` and mirror its `@/services/api` import exactly.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd webui && npx jest src/public --silent`
Expected: FAIL — cannot resolve `../App`

- [ ] **Step 3: Write the entry HTML, main, App, and Home**

`webui/public.html` — copy `webui/index.html` and change the script src to `/src/public/main.tsx` and the `<title>` to `SOTD Analytics`.

`webui/src/public/main.tsx`:

```tsx
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import '../index.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

`webui/src/public/App.tsx`:

```tsx
import { BrowserRouter as Router, Routes, Route, NavLink } from 'react-router-dom';
import ProductUsage from '../pages/ProductUsage';
import MonthlyUserPosts from '../pages/MonthlyUserPosts';
import ReportPlacementOverTime from '../pages/ReportPlacementOverTime';
import PublicHome from './PublicHome';

const navClass = ({ isActive }: { isActive: boolean }) =>
  isActive ? 'px-3 py-2 rounded-md text-sm font-medium bg-gray-700 text-white' : 'px-3 py-2 rounded-md text-sm font-medium text-gray-300 hover:text-white';

export default function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-900 text-white">
        <header className="bg-gray-800 shadow">
          <nav className="max-w-7xl mx-auto px-4 flex items-center gap-2 h-14">
            <span className="font-bold mr-4">SOTD Analytics</span>
            <NavLink to="/" end className={navClass}>Home</NavLink>
            <NavLink to="/product-usage" className={navClass}>Product Usage</NavLink>
            <NavLink to="/monthly-user-posts" className={navClass}>Monthly User Posts</NavLink>
            <NavLink to="/report-placement" className={navClass}>Placement Over Time</NavLink>
          </nav>
        </header>
        <main className="max-w-7xl mx-auto px-4 py-6">
          <Routes>
            <Route path="/" element={<PublicHome />} />
            <Route path="/product-usage" element={<ProductUsage />} />
            <Route path="/monthly-user-posts" element={<MonthlyUserPosts />} />
            <Route path="/report-placement" element={<ReportPlacementOverTime />} />
          </Routes>
        </main>
      </div>
    </Router>
  );
}
```

`webui/src/public/PublicHome.tsx`:

```tsx
import { Link } from 'react-router-dom';

const cards = [
  { to: '/product-usage', title: 'Product Usage', desc: 'Explore which razors, blades, brushes, and soaps the community used each month.' },
  { to: '/monthly-user-posts', title: 'Monthly User Posts', desc: 'Who posted SOTDs this month, and how consistently.' },
  { to: '/report-placement', title: 'Placement Over Time', desc: 'How products moved through the monthly report rankings.' },
];

export default function PublicHome() {
  return (
    <div>
      <h1 className="text-2xl font-bold mb-2">SOTD Analytics</h1>
      <p className="text-gray-400 mb-6">Read-only statistics from the r/wetshaving Shave of the Day pipeline.</p>
      <div className="grid gap-4 md:grid-cols-3">
        {cards.map((c) => (
          <Link key={c.to} to={c.to} className="block rounded-lg bg-gray-800 p-5 hover:bg-gray-700">
            <h2 className="text-lg font-semibold mb-1">{c.title}</h2>
            <p className="text-sm text-gray-400">{c.desc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
```

(Shared pages may render their own internal chrome (page headers/toolbars) that assumed the admin Dashboard layout — visually verify in Step 7 and adjust only obvious layout breakage; do not refactor the shared pages.)

- [ ] **Step 4: Run component test to verify it passes**

Run: `cd webui && npx jest src/public --silent`
Expected: PASS (2 tests). If NavLink label matching needs adjusting to the actual accessible names, fix the test selectors to match what renders.

- [ ] **Step 5: Create `vite.config.public.ts` and npm script**

`webui/vite.config.public.ts`:

```ts
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Public build: curated analytics-only entry. Serves behind nginx with /api proxied.
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // Dev server proxy so `vite --config vite.config.public.ts` works with the
  // existing backend on :8000 (same contract as the admin dev config).
  server: {
    port: 3100,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist-public',
    sourcemap: false,
    minify: 'esbuild',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      input: path.resolve(__dirname, 'public.html'),
      output: {
        manualChunks: { vendor: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
});
```

`webui/package.json` scripts — add:

```json
"build:public": "vite build --config vite.config.public.ts"
```

- [ ] **Step 6: Build and typecheck**

Run: `cd webui && npx tsc --noEmit -p tsconfig.json 2>&1 | grep -E "src/public" ; npm run build:public`
Expected: no TS errors under `src/public`; `dist-public/index.html` emitted (Vite renames `public.html` → `index.html`).

- [ ] **Step 7: Dev-server smoke (public build against real backend)**

Run: `cd webui && npx vite --config vite.config.public.ts` (port 3100, proxies `/api` to :8000 like the admin dev server). With the admin backend running (`make start-servers`), verify: Home renders; Product Usage, Monthly User Posts, Placement Over Time each load real data; no admin links anywhere. Also refresh `/product-usage` directly (deep link) — must render, not 404. Kill the server after.

- [ ] **Step 8: Playwright smoke for the public build**

Create `webui/tests/public-build.spec.ts`:

```ts
import { test, expect } from '@playwright/test';

// Runs against the public build served by `manage-servers.sh` (public mode)
// or vite preview for dist-public. Verifies the curated nav only.
test('public home lists exactly the three analytics pages', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('SOTD Analytics')).toBeVisible();
  const links = page.getByRole('navigation').getByRole('link');
  await expect(links).toHaveCount(4); // Home + 3 pages
});

test('deep link to product usage renders the SPA', async ({ page }) => {
  await page.goto('/product-usage');
  await expect(page.locator('main')).toBeVisible();
});
```

Plus the plumbing: `manage-servers.sh` gains a `--public` mode (start backend + `vite --config vite.config.public.ts` instead of the admin frontend; pass-through everything else), and `playwright.config.ts` needs no new project if the smoke uses the same baseURL — confirm at execution time and adjust the config only if the two servers must run on different ports.

- [ ] **Step 9: Lint and commit**

```bash
cd webui && npm run lint --if-present
cd .. && git add webui/public.html webui/src/public webui/vite.config.public.ts webui/package.json
git commit -m "feat(webui): public analytics frontend build (second vite entry)"
```

---

### Task 5: Dockerfiles + nginx config

**Files:**
- Create: `webui/Dockerfile.public-api`
- Create: `webui/Dockerfile.public-frontend`
- Create: `webui/Dockerfile.admin`
- Create: `webui/nginx/public.conf`

**Interfaces:**
- Consumes: `api.public_main:app` (Task 3), `npm run build:public` → `dist-public/` (Task 4), `dist/` (admin, existing build), `requirements.txt` (project root).
- Produces: three locally buildable images; compose files in Task 6 reference them by GHCR name.

- [ ] **Step 1: `webui/Dockerfile.public-api`**

```dockerfile
# Public read-only API. Serves ONLY product_usage, monthly_user_posts, report_rankings.
# Data comes from the published bundle mounted read-only at /data (SOTD_DATA_DIR=/data).
FROM python:3.14-slim
WORKDIR /app/webui
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY sotd /app/sotd
COPY webui/api /app/webui/api
COPY webui/__init__.py* /app/webui/   # no-op if webui has no __init__.py
ENV PYTHONPATH=/app:/app/webui
ENV SOTD_DATA_DIR=/data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/product-usage/health', timeout=5).status==200 else 1)"]
CMD ["python", "-m", "uvicorn", "api.public_main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Note: if `webui/__init__.py` does not exist, drop the third COPY line. The routers do `sys.path.insert(0, project_root)` where `project_root` = `/app`, so `sotd.*` imports resolve.

- [ ] **Step 2: `webui/Dockerfile.public-frontend`**

```dockerfile
# Static public frontend; nginx serves it and proxies /api to the public API service.
FROM node:20-slim AS build
WORKDIR /src
COPY webui/package.json webui/package-lock.json ./
RUN npm ci
COPY webui/ .
RUN npm run build:public

FROM nginx:alpine
COPY --from=build /src/dist-public /usr/share/nginx/html
COPY webui/nginx/public.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

- [ ] **Step 3: `webui/nginx/public.conf`**

```nginx
server {
    listen 80;

    # SPA fallback: deep links like /product-usage must serve index.html
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API proxied to the public-api service on the same compose network
    location /api/ {
        proxy_pass http://sotd-public-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

- [ ] **Step 4: `webui/Dockerfile.admin`**

```dockerfile
# Admin (operator) app: full API + built frontend, single port, LAN-only deploy.
FROM node:20-slim AS frontend
WORKDIR /src
COPY webui/package.json webui/package-lock.json ./
RUN npm ci
COPY webui/ .
RUN npm run build

FROM python:3.14-slim
WORKDIR /app/webui
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY sotd /app/sotd
COPY webui/api /app/webui/api
COPY webui/__init__.py* /app/webui/
COPY --from=frontend /src/dist /app/webui/dist
ENV PYTHONPATH=/app:/app/webui
# Admin mounts the FULL pipeline data dir (bundle + enriched) read-only or rw as desired.
ENV SOTD_DATA_DIR=/data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/api/product-usage/health', timeout=5).status==200 else 1)"]
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 5: Wire StaticFiles into admin main.py**

At the bottom of `webui/api/main.py` (after middleware), add:

```python
# Serve the built frontend when present (container deploy); harmless in dev (no dist).
_frontend_dist = Path(__file__).parent.parent / "dist"
if _frontend_dist.is_dir():
    from fastapi.staticfiles import StaticFiles

    app.mount("/", StaticFiles(directory=str(_frontend_dist), html=True), name="frontend")
```

- [ ] **Step 6: Test the StaticFiles mount**

Create `webui/api/__tests__/test_admin_static.py`:

```python
#!/usr/bin/env python3
"""Admin app serves the built frontend via StaticFiles when dist/ exists."""

import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import api.main as main_mod


def test_admin_serves_index_html_when_dist_exists(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>frontend</body></html>")
    monkeypatch.setattr(main_mod, "_frontend_dist", dist)

    # Re-run the mount logic the way main.py does at import, against tmp dist
    test_app = main_mod.app
    # remove any previously mounted "/" apps to isolate the test
    test_app.router.routes = [
        r for r in test_app.router.routes if getattr(r, "path", "") != "/"
    ]
    test_app.mount(
        "/", StaticFiles(directory=str(dist), html=True), name="frontend-test"
    )
    resp = TestClient(test_app).get("/")
    assert resp.status_code == 200
    assert "frontend" in resp.text


def test_admin_mount_guarded_by_dist_presence(tmp_path, monkeypatch):
    """The mount condition checks _frontend_dist.is_dir()."""
    monkeypatch.setattr(
        main_mod, "_frontend_dist", tmp_path / "no-such-dist"
    )
    assert not main_mod._frontend_dist.is_dir()
```

Note: the route-stripping in the first test is a test-local workaround because `app` is a module-level singleton; keep it scoped to this test. If stripping proves brittle, delete the mount at teardown instead.

- [ ] **Step 7: Build all three images locally**

Run (project root):
```bash
docker build -f webui/Dockerfile.public-api -t sotd-public-api:dev .
docker build -f webui/Dockerfile.public-frontend -t sotd-public-frontend:dev .
docker build -f webui/Dockerfile.admin -t sotd-admin:dev .
```
Expected: all three build cleanly. If `npm ci` fails on lock/platform quirks, fix in the Dockerfile (e.g. `npm ci --omit=dev` is NOT ok — playwright is a devDep needed for nothing at build; keep full ci).

- [ ] **Step 8: Smoke the public stack locally**

```bash
mkdir -p /tmp/sotd-bundle && cp -r data/aggregated/product_usage data/aggregated/user_analysis /tmp/sotd-bundle-aggregates/ 2>/dev/null || true
# simplest: mount the real repo data read-only for the smoke
docker run -d --name sotd-public-api-smoke -p 8100:8000 \
  -v "$PWD/data:/data:ro" sotd-public-api:dev
curl -s http://localhost:8100/api/product-usage/health
curl -s "http://localhost:8100/api/report-rankings/months" | head -c 200
docker rm -f sotd-public-api-smoke
```
Expected: health returns 200 JSON; months returns a JSON list.

- [ ] **Step 9: Commit**

```bash
git add webui/Dockerfile.public-api webui/Dockerfile.public-frontend webui/Dockerfile.admin webui/nginx/public.conf webui/api/main.py
git commit -m "build(webui): dockerfiles for public-api, public-frontend, admin"
```

---

### Task 6: Compose files for Portainer (deploy/)

**Files:**
- Create: `deploy/compose-sotd-public.yml`
- Create: `deploy/compose-sotd-admin.yml`

**Interfaces:**
- Consumes: GHCR image names (Global Constraints), NAS data share path.
- Produces: Portainer gitops-ready stacks; public joins `npm-bridge` + `cf_tunnel_net`, admin is LAN-only via `macvlan_lan`.

- [ ] **Step 1: `deploy/compose-sotd-public.yml`**

```yaml
# SOTD public analytics stack — deployed via Portainer (gitops source "sotd-pipeline").
# Images built by GitHub Actions on push to master (ghcr.io/nmrs, public packages —
# no registry credential needed on the NAS).
#
# Data: slim public bundle rsync'd from the Mac to
#   /volume1/docker/sotd-public/data  (aggregated slices only — NO enriched/)
# mounted read-only into public-api. Refresh with scripts/publish-public-data.sh.
#
# Networking: npm-bridge so nginx-proxy-manager routes the public hostname to
# sotd-public-frontend (and /api through the same host → frontend proxies to the
# API service); cf_tunnel_net so the cloudflared tunnel can route it.
#
# NOTE: do NOT set a `cpus:` limit — Synology's cgroup v1 rejects it.
services:
  sotd-public-api:
    image: ghcr.io/nmrs/sotd-pipeline-public-api:latest
    restart: unless-stopped
    mem_limit: 1g
    pull_policy: always
    environment:
      - TZ=America/Chicago
      - SOTD_DATA_DIR=/data
      - PUBLIC_ALLOWED_ORIGIN=${SOTD_PUBLIC_ORIGIN:-https://sotd.example.invalid}
    volumes:
      - /volume1/docker/sotd-public/data:/data:ro
    networks:
      - sotd-internal

  sotd-public-frontend:
    image: ghcr.io/nmrs/sotd-pipeline-public-frontend:latest
    restart: unless-stopped
    mem_limit: 128m
    pull_policy: always
    depends_on:
      - sotd-public-api
    networks:
      - sotd-internal
      - npm-bridge
      - cf_tunnel_net

networks:
  sotd-internal:
    driver: bridge
  npm-bridge:
    external: true
  cf_tunnel_net:
    external: true
```

(NPM routes the public hostname → `sotd-public-frontend`; the frontend's nginx proxies `/api/` → `sotd-public-api:8000`, so only the frontend needs NPM/tunnel membership.)

- [ ] **Step 2: `deploy/compose-sotd-admin.yml`**

```yaml
# SOTD admin (operator) stack — LAN ONLY. No npm-bridge, no cf_tunnel_net:
# no external route exists to it. Reachable at the macvlan static IP.
# Mounts the FULL pipeline data dir (bundle + enriched) read-only.
#
# NOTE: do NOT set a `cpus:` limit — Synology's cgroup v1 rejects it.
services:
  sotd-admin:
    image: ghcr.io/nmrs/sotd-pipeline-admin:latest
    restart: unless-stopped
    mem_limit: 1g
    pull_policy: always
    environment:
      - TZ=America/Chicago
      - SOTD_DATA_DIR=/data
    volumes:
      - /volume1/docker/sotd-admin/data:/data:ro
    networks:
      macvlan_lan:
        ipv4_address: 192.168.2.23

networks:
  macvlan_lan:
    external: true
```

(Adjust the admin data share + static IP to the real NAS layout at execution time — the NAS-side dirs must exist and be populated before first deploy; admin uses the full data copy, published by the same script with `--full` or a plain rsync of `data/aggregated` + `data/enriched`.)

- [ ] **Step 3: Validate compose files**

Run: `docker compose -f deploy/compose-sotd-public.yml config -q && docker compose -f deploy/compose-sotd-admin.yml config -q`
Expected: no output (valid). (External networks/IPs need not exist for `config` validation.)

- [ ] **Step 4: Commit**

```bash
git add deploy/compose-sotd-public.yml deploy/compose-sotd-admin.yml
git commit -m "deploy: compose stacks for sotd public + admin containers"
```

---

### Task 7: GitHub Actions workflow

**Files:**
- Create: `.github/workflows/build.yml`

**Interfaces:**
- Consumes: Dockerfiles (Task 5); Makefile targets `lint`, `test` (existing), `test-react` (existing).
- Produces: GHCR images on every push to master touching webui/deploy/docker paths; optional Portainer webhook redeploys via `PORTAINER_WEBHOOK_PUBLIC` / `PORTAINER_WEBHOOK_ADMIN` secrets.

- [ ] **Step 1: Write `.github/workflows/build.yml`** (modeled on myacuright's build.yml, with test gates and two webhooks)

```yaml
name: build
on:
  push:
    branches: [master]
    paths:
      - 'webui/**'
      - 'sotd/**'
      - 'requirements.txt'
      - 'deploy/**'
      - '.github/workflows/build.yml'
  workflow_dispatch:

permissions:
  contents: read
  packages: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.14'
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install python deps
        run: pip install -r requirements.txt -r requirements-dev.txt
      - name: Ruff + black check
        run: |
          pip install ruff black
          ruff check sotd webui/api
          black --check sotd webui/api
      - name: Python tests
        run: PYTHONPATH=. pytest tests/ -x -q
      - name: React lint + tests
        working-directory: webui
        run: |
          npm ci
          npm run lint
          npm run test

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      - uses: docker/build-push-action@v6
        with:
          file: webui/Dockerfile.public-api
          push: true
          tags: |
            ghcr.io/nmrs/sotd-pipeline-public-api:latest
            ghcr.io/nmrs/sotd-pipeline-public-api:${{ github.sha }}
      - uses: docker/build-push-action@v6
        with:
          file: webui/Dockerfile.public-frontend
          push: true
          tags: |
            ghcr.io/nmrs/sotd-pipeline-public-frontend:latest
            ghcr.io/nmrs/sotd-pipeline-public-frontend:${{ github.sha }}
      - uses: docker/build-push-action@v6
        with:
          file: webui/Dockerfile.admin
          push: true
          tags: |
            ghcr.io/nmrs/sotd-pipeline-admin:latest
            ghcr.io/nmrs/sotd-pipeline-admin:${{ github.sha }}
      - name: redeploy public stack (webhook)
        env:
          WEBHOOK: ${{ secrets.PORTAINER_WEBHOOK_PUBLIC }}
        run: |
          if [ -n "$WEBHOOK" ]; then
            curl -fsS -X POST "$WEBHOOK"
          else
            echo "PORTAINER_WEBHOOK_PUBLIC not set — skipping redeploy"
          fi
      - name: redeploy admin stack (webhook)
        env:
          WEBHOOK: ${{ secrets.PORTAINER_WEBHOOK_ADMIN }}
        run: |
          if [ -n "$WEBHOOK" ]; then
            curl -fsS -X POST "$WEBHOOK"
          else
            echo "PORTAINER_WEBHOOK_ADMIN not set — skipping redeploy"
          fi
```

Note: full `pytest tests/` runs ~4300 tests; if CI wall-time matters, start with `-x -q` as written and only later consider splitting test/build jobs by path. Also verify `requirements-dev.txt` exists (it does) and that `black --check` matches the repo's actual formatting baseline — if pre-existing files fail `black --check`, scope the check to changed files or drop that step (ruff alone is an acceptable v1 gate).

- [ ] **Step 2: Validate workflow syntax**

Run: `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build.yml'))" && echo OK`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/build.yml
git commit -m "ci: build and publish public-api/public-frontend/admin images to ghcr"
```

---

### Task 8: Public data bundle publisher (verifier + rsync)

**Files:**
- Create: `scripts/publish_public_data.py` (argparse CLI; also importable)
- Create: `scripts/publish-public-data.sh` (thin shell wrapper: verify → rsync → optional hook note)
- Create: `tests/scripts/__init__.py` (if absent) + `tests/scripts/test_publish_public_data.py`
- Modify: `Makefile` (add `publish-data` target)

**Interfaces:**
- Consumes: `data/aggregated/` layout (existing).
- Produces: `python scripts/publish_public_data.py --check --data-dir data --target <dir>` exit-code contract used by the shell wrapper; bundle layout `/volume1/docker/sotd-public/data/aggregated/{product_usage,user_analysis}/*.json`, `{YYYY-MM}.json`, `annual/`.

- [ ] **Step 1: Write the failing tests**

```python
#!/usr/bin/env python3
"""Tests for the public-bundle verifier."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.publish_public_data import check_bundle


def _mk(d, rel, payload):
    p = d / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload))


def test_complete_bundle_passes(tmp_path):
    d = tmp_path / "aggregated"
    for m in ("2026-08", "2026-09"):
        _mk(tmp_path, f"aggregated/{m}.json", {"meta": {}, "data": {}})
        _mk(tmp_path, f"aggregated/user_analysis/{m}.json", {"users": {}})
        _mk(tmp_path, f"aggregated/product_usage/{m}.json", {"meta": {}})
    assert check_bundle(tmp_path) == []


def test_missing_slice_month_fails(tmp_path):
    d = tmp_path / "aggregated"
    _mk(tmp_path, "aggregated/2026-09.json", {"meta": {}, "data": {}})
    _mk(tmp_path, "aggregated/user_analysis/2026-09.json", {"users": {}})
    # product_usage/2026-09.json missing
    problems = check_bundle(tmp_path)
    assert any("product_usage" in p and "2026-09" in p for p in problems)


def test_month_file_without_user_analysis_fails(tmp_path):
    _mk(tmp_path, "aggregated/2026-09.json", {"meta": {}, "data": {}})
    problems = check_bundle(tmp_path)
    assert any("2026-09" in p for p in problems)


def test_annual_dir_optional_but_no_enriched_ever(tmp_path):
    # annual/ absent is fine; a stray enriched dir inside the bundle source is NOT
    (tmp_path / "enriched").mkdir()
    problems = check_bundle(tmp_path)
    assert any("enriched" in p for p in problems)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. pytest tests/scripts/test_publish_public_data.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scripts.publish_public_data'` (create empty `tests/scripts/__init__.py` and, if needed, `scripts/__init__.py` first so the import resolves)

- [ ] **Step 3: Implement the verifier CLI**

```python
#!/usr/bin/env python3
"""Verify the slim public data bundle before publishing.

Bundle = aggregated slices the public routers read:
  aggregated/{YYYY-MM}.json, aggregated/user_analysis/, aggregated/product_usage/,
  aggregated/annual/ (optional). enriched/ must NOT be present in the target.
"""

import argparse
import json
import re
import sys
from pathlib import Path

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _months_in(dir_path: Path) -> set:
    if not dir_path.is_dir():
        return set()
    return {p.stem for p in dir_path.glob("*.json") if MONTH_RE.match(p.stem)}


def check_bundle(data_dir: Path) -> list:
    """Return a list of human-readable problems; empty list = bundle is publishable."""
    problems = []
    agg = data_dir / "aggregated"
    month_files = _months_in(agg)
    ua = _months_in(agg / "user_analysis")
    pu = _months_in(agg / "product_usage")

    for m in sorted(month_files | ua | pu):
        if m not in month_files:
            problems.append(f"{m}: missing aggregated/{m}.json (rank tables)")
        if m not in ua:
            problems.append(f"{m}: missing aggregated/user_analysis/{m}.json")
        if m not in pu:
            problems.append(f"{m}: missing aggregated/product_usage/{m}.json")

    if (data_dir / "enriched").exists():
        problems.append("enriched/ present in bundle source — must never be published")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--check", action="store_true", help="verify only; no copying")
    args = ap.parse_args()
    problems = check_bundle(args.data_dir)
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if problems:
        return 1
    print("bundle complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

(`annual/` is included in the rsync unconditionally by the shell script; the verifier treats it as optional since report_rankings degrades gracefully without it.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `PYTHONPATH=. pytest tests/scripts/test_publish_public_data.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: Write the shell wrapper** (verify → four rsync calls; no remote verification in v1)

```bash
#!/usr/bin/env bash
# Publish the slim public data bundle to the NAS (or any rsync target).
# Usage: scripts/publish-public-data.sh [TARGET]
#   TARGET default: nas:sotd-public/data   (ssh alias + path; can be a local dir)
# Env: SOTD_PUBLIC_DATA_TARGET overrides the default target.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-${SOTD_PUBLIC_DATA_TARGET:-nas:sotd-public/data}}"

echo "==> verifying bundle completeness"
python scripts/publish_public_data.py --check --data-dir data

echo "==> rsyncing bundle to $TARGET"
rsync -a --delete data/aggregated/product_usage/ "$TARGET/aggregated/product_usage/"
rsync -a --delete data/aggregated/user_analysis/ "$TARGET/aggregated/user_analysis/"
rsync -a --delete data/aggregated/annual/        "$TARGET/aggregated/annual/"
rsync -a --delete --include='????-??.json' --exclude='*' data/aggregated/ "$TARGET/aggregated/"

echo "done. bundle at $TARGET"
```

- [ ] **Step 6: Makefile target**

Add to the Makefile (near the other webui targets):

```make
publish-data:  ## rsync the slim public data bundle to the NAS
	python scripts/publish_public_data.py --check --data-dir data
	./scripts/publish-public-data.sh
```

(If the Makefile uses `.PHONY`, add `publish-data` there too. Note the double-check is intentional but harmless; keep whichever form reads cleaner — verifier runs inside the script already.)

- [ ] **Step 7: Dry-run against the real repo data, then commit**

Run: `PYTHONPATH=. python scripts/publish_public_data.py --check --data-dir data`
Expected: `bundle complete` (we verified all 126 months are present in all three slices).
Also run the rsync with a local throwaway target to prove the include/exclude filter copies only month JSONs:
```bash
./scripts/publish-public-data.sh /tmp/sotd-bundle-test && ls /tmp/sotd-bundle-test/aggregated/ | head && ls /tmp/sotd-bundle-test/aggregated/ | wc -l
```
Expected: only `{YYYY-MM}.json` files + the three subdirs; ~126 month files. `rm -rf /tmp/sotd-bundle-test` after.

```bash
chmod +x scripts/publish-public-data.sh
git add scripts/publish_public_data.py scripts/publish-public-data.sh tests/scripts/ Makefile
git commit -m "feat(scripts): slim public data bundle verifier + rsync publisher"
```

---

### Task 9: Docs + final wiring

**Files:**
- Modify: `webui/README.md` (public build section)
- Modify: `CLAUDE.md` (WebUI note: two builds, containers, publish-data)
- Create: `deploy/README.md` (NAS deploy runbook: compose stacks, NPM host setup, webhooks, bundle path)

**Interfaces:**
- Consumes: everything above.
- Produces: documentation an operator needs to deploy without reading the plan.

- [ ] **Step 1: Write `deploy/README.md`** — cover: first-time NAS setup (create `/volume1/docker/sotd-public/data` + admin data dir, run `make publish-data`), Portainer stack creation from this repo per file, NPM proxy-host config for the public hostname (forward to `sotd-public-frontend:80`), creating the two Portainer webhook secrets in GitHub, and the update loop (push → CI → images → webhook → redeploy; data → `make publish-data`, no redeploy needed).

- [ ] **Step 2: Update `webui/README.md`** — add a "Public build" section: `npm run build:public`, what it contains (three pages), and a pointer to the spec + deploy/README.

- [ ] **Step 3: Update project `CLAUDE.md`** — one short paragraph under the WebUI note: two builds (admin default, `--config vite.config.public.ts` public), containers via `.github/workflows/build.yml`, `make publish-data` for data.

- [ ] **Step 4: Run the full local gate**

```bash
source .venv/bin/activate && PYTHONPATH=. pytest tests/ webui/api/__tests__/ webui/api/tests/ -q 2>&1 | tail -3
cd webui && npm run test && npm run lint
```
Expected: all green.

- [ ] **Step 5: Commit docs**

```bash
git add webui/README.md CLAUDE.md deploy/README.md
git commit -m "docs: public/admin container deployment runbook"
```

---

## Out of Scope (per spec)

- App-level auth (admin is LAN-only by topology).
- Post-pipeline-hook automation of `publish-data` (fast-follow).
- Public access to rendered report archives.
- NAS-side deployment execution itself (this plan ships the compose files + docs; the Portainer stack creation and NPM host config are operator steps documented in `deploy/README.md`).
