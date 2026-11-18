# Lint & Typecheck Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Drive the repo's three quality gates to zero — ruff lint (342 test-file errors currently invisible to `make lint`), black (3 files), pyright (303 errors) — with every task ending green on the full test suite.

**Architecture:** Bulk auto-fixes first (safe, mechanical), manual fixes second (need judgment), scope extension third (so the debt can't regrow silently), pyright last (needs investigation per cluster). Each task is independently committable and leaves the suite green.

**Tech Stack:** ruff 0.16.x (E/F/I rules), black 100-char, pyright standard mode (Python 3.14), pytest.

**Spec:** n/a — cleanup task; the "spec" is the current measured debt, reproduced here:
- ruff: `make lint` passes only because pyproject `exclude = ["data", "tests", ...]`; `ruff check tests/` reports 342 errors (173 I001 unsorted imports, 95 F401 unused imports, 46 F541 empty f-strings, 18 F841 unused vars, 7 E402 late imports, 2 F821 undefined names, 1 F601 dup dict key). `sotd/` is clean.
- black: 3 files — `tests/aggregate/test_annual_integration.py`, `tests/integration/test_real_catalog_integration.py`, `tests/extract/test_override_manager.py`.
- pyright: 303 errors / 8 warnings. By rule: reportAttributeAccessIssue 137, reportArgumentType 100, reportOptionalMemberAccess 18, reportGeneralTypeIssues 12, reportCallIssue 11, reportIncompatibleMethodOverride 8, reportOperatorIssue 6, reportUnsupportedDunderAll 6, reportPossiblyUnboundVariable 4, remainder ~1-2 each. Top files: `sotd/aggregate/annual_engine.py` 111 (pandas `df.reset_index` on union-typed values), `tests/fetch/test_community_fetch.py` 20, `sotd/aggregate/aggregators/cross_product/highest_use_count_per_blade_aggregator.py` 17, `sotd/aggregate/aggregators/users/soap_brand_scent_diversity_aggregator.py` 17, `sotd/aggregate/aggregators/formats/razor_format_aggregator.py` 10, `sotd/enrich/brush_enricher.py` 10, `sotd/aggregate/aggregators/core/blade_usage_distribution_aggregator.py` 8, `tests/utils/test_logging_config.py` 8.
- Tests: currently all green (Python 4206 + 415 webui, React 756, Playwright 6 as of 2026-10-22).

## Global Constraints

- Python venv only: `.venv/bin/python`; Makefile targets need `source .venv/bin/activate` (or prefix `PYTHONPATH=.`).
- Black line length 100; ruff line-length 100 with E501 ignored.
- No behavior changes in lint/type tasks: every task must end with the full Python suite green (`PYTHONPATH=. python -m pytest tests/ -q`, ~2 min). React suite green at final task.
- Pyright fix policy: prefer real types/narrowing/annotations. A `# type: ignore[rule]  # <reason>` is allowed only for third-party stub artifacts (pandas) where a real fix would distort the code — each ignore carries its reason. No blanket pyrightconfig downgrades, no loosening `typeCheckingMode`.
- F841 deletion rule: if the assigned call has side effects the test relies on (e.g. `result = matcher.match(...)` exercising the call), keep the call as a bare expression; only the binding is deleted. Never delete a call outright without reading what it does.
- E402 rule: inspect *why* the import is late (sys.path setup? deliberate?). Only `# noqa: E402  # <reason>` if moving it up is genuinely impossible; otherwise move it up.
- Commit style: conventional commits, `Co-Authored-By: Claude Code <noreply@anthropic.com>`.
- Work on a branch (use superpowers:using-git-worktrees at execution start).

## Review Focus

1. **Ruff auto-fix removing a load-bearing import** — imports used only inside `patch("module.attr")` strings look unused to ruff; the fix deletes them and mock still resolves them, but any *other* string-based reference breaks silently. Check: full suite run immediately after `--fix` (Task 1 step 3) is the gate.
2. **F841 deletion weakening a test** — an unused `result =` often still proves "this call doesn't raise". Decision rule in Global Constraints; reviewer checks each of the 18 sites (Task 2).
3. **E402 noqa masking a real path bug** — `tests/match/brush/strategies/automated/test_automated_split_black_eagle_ht2.py` has 4 consecutive late imports; verify the reason before suppressing (Task 2).
4. **Type annotations changing runtime behavior** — pandas fixes in `annual_engine.py` must be annotations/narrowing only, never reordering of operations; suite green after each pyright task is the gate.
5. **tests/webui drift** — the 415 webui API tests were excluded from several past "full suite" runs; the final task runs the complete `tests/` tree (no ignore flags) so nothing hides again.

---

### Task 1: Ruff auto-fixes across tests/

**Files:**
- Modify: ~150+ files under `tests/` (mechanical: import sorting, unused imports, empty f-strings)

**Interfaces:**
- Consumes: current `tests/` tree
- Produces: `ruff check tests/` reduced from 342 to 28 errors (the manual set)

- [ ] **Step 1: Apply auto-fixes**

Run: `python -m ruff check tests/ --fix`
Expected: 314 fixed, 28 remaining (19 unsafe-hidden remain unfixed)

- [ ] **Step 2: Confirm sotd/ untouched**

Run: `git diff --stat -- sotd/ | head -3`
Expected: empty

- [ ] **Step 3: Full Python suite green**

Run: `PYTHONPATH=. python -m pytest tests/ -q` (no ignore flags — include tests/webui)
Expected: 0 failed; count ~4621 passing

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "style(tests): apply ruff auto-fixes (import sorting, unused imports, empty f-strings)"
```

### Task 2: Manual ruff fixes (28 findings)

**Files:**
- Modify: 18 F841 sites — `tests/docker/test_pipeline_container_scripts.py:26`, `tests/fetch_via_json/test_auth_cli.py:56`, `tests/integration/test_brush_configuration_updater_integration.py:420`, `tests/integration/test_split_brush_performance.py:197`, `tests/learning/test_brush_chatgpt_analyzer.py:321-322`, `tests/learning/test_brush_configuration_updater.py:215`, `tests/learning/test_brush_learning_report_generator.py:182`, `tests/match/brush/scoring/dependencies/test_handle_knot_dependency_performance.py:237`, `tests/match/test_brush_splitter_delimiter_with_specifications.py:255`, `tests/match/test_pattern_cache_performance.py:181,186`, `tests/match/test_razor_matcher_performance.py:167`, `tests/webui/api/production_tests/test_brush_splits_refactor.py:39,83,128`, `tests/webui/api/test_catalog_validation.py:810`, `tests/webui/api/test_correct_matches_composite_brush.py:196`
- Modify: `tests/match/brush/strategies/automated/test_automated_split_black_eagle_ht2.py:12-15` (4× E402), `tests/test_brush_matching_api_completeness.py:21`, `tests/test_brush_matching_api_integration.py:17`, `tests/webui/api/production_tests/test_brush_validation.py:22` (1× E402 each)
- Modify: `tests/webui/api/test_catalog_validation.py:518,521` (F821 — latent NameError: the cleanup branch references `correct_matches_dir` which that function never assigns; read the function and fix the cleanup logic so the name exists or the branch is correct)
- Modify: `tests/webui/api/test_brush_splits.py:114` (F601 — drop the duplicated `"validated_at"` key)

**Interfaces:**
- Consumes: F841/E402 decision rules from Global Constraints
- Produces: `ruff check tests/` → 0 errors

- [ ] **Step 1: Fix F601 and F821 first** (the two real bugs) — read each function before touching it; the F821 fix must keep the cleanup semantics the author intended
- [ ] **Step 2: Fix the 18 F841 sites** per the decision rule (delete binding, keep side-effectful calls)
- [ ] **Step 3: Handle the 7 E402 sites** — inspect each; move import up where possible, else `# noqa: E402  # <reason>`
- [ ] **Step 4: Verify zero and suite green**

Run: `python -m ruff check tests/ && PYTHONPATH=. python -m pytest tests/ -q`
Expected: 0 errors; 0 failed

- [ ] **Step 5: Commit**

```bash
git commit -am "style(tests): manual ruff fixes (unused vars, late imports, dup dict key, latent NameError)"
```

### Task 3: Black the 3 remaining files

**Files:**
- Modify: `tests/aggregate/test_annual_integration.py`, `tests/integration/test_real_catalog_integration.py`, `tests/extract/test_override_manager.py`

- [ ] **Step 1: Format** — Run: `python -m black tests/aggregate/test_annual_integration.py tests/integration/test_real_catalog_integration.py tests/extract/test_override_manager.py`
- [ ] **Step 2: Verify** — Run: `python -m black --check .` → expect **0** files would-be-reformatted. Also `PYTHONPATH=. python -m pytest tests/ -q` green.
- [ ] **Step 3: Commit** — `git commit -am "style: black-format remaining test files"`

### Task 4: Extend ruff scope to tests/

**Files:**
- Modify: `pyproject.toml` `[tool.ruff] exclude` — remove `"tests"` (keep `"data"`, venvs)

- [ ] **Step 1: Edit pyproject.toml exclude**
- [ ] **Step 2: Verify the gate now covers tests and stays clean**

Run: `make lint`
Expected: "All checks passed!" — and this now scans tests/ (proof: `python -m ruff check tests/` also passes)

- [ ] **Step 3: Commit** — `git commit -am "build: include tests/ in ruff lint scope"`

### Task 5: Pyright — `annual_engine.py` root cause (111 errors)

**Files:**
- Modify: `sotd/aggregate/annual_engine.py` (annotations/narrowing only)

**Interfaces:**
- Produces: the pattern (likely one union-typed variable feeding `df.reset_index()` around line 370) that other aggregate files may share

- [ ] **Step 1: Investigate** — Run: `python -m pyright sotd/aggregate/annual_engine.py 2>&1 | head -40`; identify the typed-as-union variable(s). One root annotation may clear most of the 111.
- [ ] **Step 2: Fix with real types** — add the narrowest correct annotation(s); `# type: ignore[rule]  # pandas stub artifact` only where genuinely stub-caused
- [ ] **Step 3: Verify** — Run: `python -m pyright sotd/aggregate/annual_engine.py 2>&1 | tail -1` → 0 errors; `PYTHONPATH=. python -m pytest tests/aggregate tests/integration -q` green; full-suite count dropped ≥100 (`python -m pyright --outputjson | python3 -c "import json,sys; print(json.load(sys.stdin)['summary']['errorCount'])"`)
- [ ] **Step 4: Commit** — `git commit -am "fix(aggregate): resolve annual_engine pyright errors (pandas typing)"`

### Task 6: Pyright — aggregators cluster (~64 errors)

**Files:**
- Modify: `sotd/aggregate/aggregators/cross_product/highest_use_count_per_blade_aggregator.py` (17), `sotd/aggregate/aggregators/users/soap_brand_scent_diversity_aggregator.py` (17), `sotd/aggregate/aggregators/formats/razor_format_aggregator.py` (10), `sotd/aggregate/aggregators/core/blade_usage_distribution_aggregator.py` (8), `sotd/aggregate/aggregators/users/soap_mashup_user_aggregator.py` (6), `sotd/aggregate/aggregators/users/soap_sample_user_aggregator.py` (6), plus remaining aggregators by `pyright` output

- [ ] **Step 1: Fix file-by-file**, reusing Task 5's annotation pattern where the same pandas pattern appears
- [ ] **Step 2: Verify** — `python -m pyright sotd/aggregate/aggregators/ 2>&1 | tail -1` → 0 errors; `PYTHONPATH=. python -m pytest tests/aggregate -q` green
- [ ] **Step 3: Commit** — `git commit -am "fix(aggregate): resolve aggregator pyright errors"`

### Task 7: Pyright — tests/ clusters (~40 errors)

**Files:**
- Modify: `tests/fetch/test_community_fetch.py` (20), `tests/utils/test_logging_config.py` (8), `tests/fetch/test_reddit.py` (5), plus remaining test files by output

- [ ] **Step 1: Fix file-by-file** (mock-typed fixtures usually need `cast()` or correct Mock generics — prefer real types)
- [ ] **Step 2: Verify** — `python -m pyright tests/ 2>&1 | tail -1` → 0 errors; affected suites green
- [ ] **Step 3: Commit** — `git commit -am "fix(tests): resolve test-file pyright errors"`

### Task 8: Pyright — remaining stragglers (enrich, match, webui, misc)

**Files:**
- Modify: `sotd/enrich/brush_enricher.py` (10), `sotd/match/brush/strategies/utils/__init__.py` (6, reportUnsupportedDunderAll), and every remaining file listed by pyright until 0
- Note: `reportUnsupportedDunderAll` on `__init__.py` usually means `__all__` contains non-module names — fix the list contents, don't ignore

- [ ] **Step 1: Sweep by file** in descending error order; re-check `python -m pyright --outputjson` count after each batch
- [ ] **Step 2: Verify** — `make typecheck` → **0 errors, 0 warnings** (warnings count too: 8 today)
- [ ] **Step 3: Commit** — `git commit -am "fix: resolve remaining pyright errors repo-wide"`

### Task 9: Final verification + bookkeeping

**Files:**
- Modify: memory note (delete/update the stale `typecheck-baseline-failing` entry outside the repo), `.claude/` if CLAUDE.md mentions the failing baseline

- [ ] **Step 1: All four gates** — Run: `make lint && make typecheck && make test && make test-react`
Expected: all green; pytest ~4621 passed incl. tests/webui
- [ ] **Step 2: Playwright** — Run: `make test-e2e` (servers auto-managed via `webui/scripts/manage-servers.sh`; playwright via `node node_modules/@playwright/test/cli.js`, not npx)
Expected: 6 passed
- [ ] **Step 3: Update the repo doc that documents the baseline** if it mentions the failing typecheck; commit — `git commit -am "docs: typecheck baseline now clean"`
