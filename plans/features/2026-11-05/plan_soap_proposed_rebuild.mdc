# Soap Proposed Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace broken `soaps_proposed.yaml` generation with a standalone rebuild CLI from unmatched soap match rows, rewrite `/propose-soaps` to run that CLI then LLM patterns, and add `/validate-soap-proposals` to annotate (and promote from `unknown`) with evidence URLs.

**Architecture:** Deterministic Python owns routing, aggregation, rotate, and write. Claude commands only orchestrate: propose = CLI + pattern LLM; validate = research LLM that annotates/promotes in place. `data/soaps.yaml` is never auto-edited. Legacy `data/proposed/*.json` convert path stays for validate-matches.

**Tech Stack:** Python 3.11+, PyYAML, pytest, argparse; Claude command markdown under `.claude/commands/`

**Spec:** `docs/superpowers/specs/2026-11-05-soap-proposed-rebuild-design.md`

## Global Constraints

- Rebuild CLI must be independently runnable; skills invoke it, they do not reimplement routing.
- Output default path: `data/soaps_proposed.yaml`; rotate to `{out}.bak` only on rebuild (overwrite prior `.bak`).
- Entries are match `normalized` strings; scent key from `matched.scent` (not `model`).
- Ignore `match_type` in `{exact, regex, filtered}`; route `brand` / `dash_split` to brand+scent; else `unknown` → `unmatched`.
- Do not consult `correct_matches` or skip because scent exists in `soaps.yaml`.
- Never write `data/soaps.yaml` from these tools/commands.
- Activate `.venv` before `make` / pytest.

## Review Focus

- Soap row with `match_type: brand` but empty `matched.scent` → treated as `unknown`/`unmatched`, not a blank scent key.
- Empty or missing `normalized` → skipped entirely (not written under unknown).
- Second rebuild with different `--month` → full replace after rotate (prior range content only in `.bak`).
- `filtered` soap strings → absent from output even if they look like real products.
- Validate promote: one `unknown` entry identified → new brand/scent with `validation: validated` + `source_url`; entry removed from `unknown`/`unmatched`.

---

## File map

| Path | Role |
|------|------|
| `sotd/match/tools/rebuild_soaps_proposed.py` | New CLI + pure functions (route, aggregate, rotate, write) |
| `tests/match/tools/test_rebuild_soaps_proposed.py` | Unit/integration tests for rebuild |
| `generate_soaps_proposed.py` | Delete (superseded) |
| `.claude/commands/propose-soaps.md` | Rewrite: rebuild CLI → LLM patterns |
| `.claude/commands/validate-soap-proposals.md` | New: annotate + promote unknown |
| `.claude/commands/propose-soaps-yaml.md` | Update contrast table (legacy JSON path) |
| `docs/superpowers/specs/2026-11-05-soap-proposed-rebuild-design.md` | Already approved; touch only if plan drift |

Reuse `months_for_args` / `parse_month_range` from `sotd.match.tools.proposed_soaps_to_yaml` (do not duplicate month parsing).

---

### Task 1: Rebuild core — route and aggregate

**Files:**
- Create: `sotd/match/tools/rebuild_soaps_proposed.py`
- Test: `tests/match/tools/test_rebuild_soaps_proposed.py`

**Interfaces:**
- Produces:
  - `IGNORE_MATCH_TYPES: frozenset[str]` = `{"exact", "regex", "filtered"}`
  - `route_soap_record(soap: dict[str, Any]) -> tuple[str, str] | None`  
    Returns `(brand, scent)` to accumulate into, or `None` to skip.  
    Uses `matched.brand` / `matched.scent` for `brand`/`dash_split` when both non-empty; otherwise `("unknown", "unmatched")` for unresolved; `None` for ignore types or missing `normalized`.
  - `aggregate_soap_entries(records: list[dict[str, Any]]) -> dict[str, dict[str, dict[str, list[str]]]]`  
    Shape: `{brand: {scent: {"entries": [normalized, ...]}}}` — entries deduped, brands/scents/entries sorted.

- [ ] **Step 1: Write failing tests** for routing and aggregation

```python
def test_ignores_exact_regex_filtered():
    assert route_soap_record({"normalized": "x", "match_type": "exact", "matched": {}}) is None
    assert route_soap_record({"normalized": "x", "match_type": "regex", "matched": {}}) is None
    assert route_soap_record({"normalized": "x", "match_type": "filtered", "matched": None}) is None

def test_brand_and_dash_split_use_matched_scent():
    assert route_soap_record({
        "normalized": "summer break soaps - roty 2025",
        "match_type": "brand",
        "matched": {"brand": "Summer Break Soaps", "scent": "ROTY 2025"},
    }) == ("Summer Break Soaps", "ROTY 2025")

def test_brand_missing_scent_goes_unknown():
    assert route_soap_record({
        "normalized": "orphan",
        "match_type": "brand",
        "matched": {"brand": "Acme", "scent": ""},
    }) == ("unknown", "unmatched")

def test_unresolved_goes_unknown():
    assert route_soap_record({
        "normalized": "mystery mash",
        "match_type": None,
        "matched": None,
    }) == ("unknown", "unmatched")

def test_aggregate_dedupes_and_sorts():
    records = [
        {"soap": {"normalized": "b", "match_type": "brand",
                  "matched": {"brand": "A", "scent": "S"}}},
        {"soap": {"normalized": "a", "match_type": "brand",
                  "matched": {"brand": "A", "scent": "S"}}},
        {"soap": {"normalized": "b", "match_type": "brand",
                  "matched": {"brand": "A", "scent": "S"}}},
    ]
    out = aggregate_soap_entries(records)
    assert out == {"A": {"S": {"entries": ["a", "b"]}}}
```

- [ ] **Step 2: Run tests — expect FAIL** (import / not defined)

Run: `source .venv/bin/activate && PYTHONPATH=. pytest tests/match/tools/test_rebuild_soaps_proposed.py::test_ignores_exact_regex_filtered tests/match/tools/test_rebuild_soaps_proposed.py::test_brand_and_dash_split_use_matched_scent tests/match/tools/test_rebuild_soaps_proposed.py::test_brand_missing_scent_goes_unknown tests/match/tools/test_rebuild_soaps_proposed.py::test_unresolved_goes_unknown tests/match/tools/test_rebuild_soaps_proposed.py::test_aggregate_dedupes_and_sorts -v`

- [ ] **Step 3: Implement `route_soap_record` and `aggregate_soap_entries` in `rebuild_soaps_proposed.py`**

Skip empty/whitespace `normalized`. For each record, read `record["soap"]` if present else skip. Only `entries` keys in scent dicts (no patterns).

- [ ] **Step 4: Run tests — expect PASS**

- [ ] **Step 5: Commit**

```bash
git add sotd/match/tools/rebuild_soaps_proposed.py tests/match/tools/test_rebuild_soaps_proposed.py
git commit -m "$(cat <<'EOF'
feat(match): add soap proposed rebuild routing and aggregation

EOF
)"
```

---

### Task 2: Rebuild CLI — load months, rotate, write

**Files:**
- Modify: `sotd/match/tools/rebuild_soaps_proposed.py`
- Test: `tests/match/tools/test_rebuild_soaps_proposed.py`

**Interfaces:**
- Consumes: `route_soap_record`, `aggregate_soap_entries`; `months_for_args` from `proposed_soaps_to_yaml`
- Produces:
  - `load_matched_records(path: Path) -> list[dict[str, Any]]` — reads JSON; uses top-level `data` list
  - `rotate_out_file(out_path: Path) -> Path | None` — if exists, replace `{out}.bak` with current; return bak path or None
  - `write_proposed_yaml(fragment: dict, out_path: Path) -> None`
  - `rebuild_soaps_proposed(months: list[str], data_dir: Path, out_path: Path) -> dict[str, int]` — rotate, merge months, write; returns stats (`brands`, `scents`, `entries`, `missing_months` count)
  - `main(argv: list[str] | None = None) -> int` — `--month` | `--range`, `--data-dir`, `--out`; exit `1` if any month missing (still write if any data), `0` on full success, `2` on arg errors

- [ ] **Step 1: Write failing tests** (use `tmp_path`)

```python
def test_rotate_writes_bak(tmp_path: Path):
    out = tmp_path / "soaps_proposed.yaml"
    out.write_text("old: true\n", encoding="utf-8")
    rotate_out_file(out)
    assert (tmp_path / "soaps_proposed.yaml.bak").read_text(encoding="utf-8") == "old: true\n"

def test_rebuild_merges_months_and_ignores_exact(tmp_path: Path):
    # Write two matched JSON files under tmp_path/matched/
    # Include exact (ignored) + brand (kept); call rebuild_soaps_proposed
    # Assert YAML shape and stats

def test_main_missing_month_exits_1(tmp_path: Path, capsys):
    # Only one of two range months present; assert returncode == 1 and file still written
```

Pin Review Focus cases in these or adjacent tests: empty normalized skipped; second rebuild replaces content; filtered absent.

- [ ] **Step 2: Run — expect FAIL**

Run: `source .venv/bin/activate && PYTHONPATH=. pytest tests/match/tools/test_rebuild_soaps_proposed.py -v -k "rotate or rebuild or main_missing"`

- [ ] **Step 3: Implement I/O, argparse `main`, `if __name__ == "__main__"`**

YAML dump: `allow_unicode=True`, `default_flow_style=False`, `sort_keys=False` (structure already sorted). Print summary to stdout like other match tools.

- [ ] **Step 4: Run full rebuild test module — expect PASS**

Run: `source .venv/bin/activate && PYTHONPATH=. pytest tests/match/tools/test_rebuild_soaps_proposed.py -v`

- [ ] **Step 5: Commit**

```bash
git add sotd/match/tools/rebuild_soaps_proposed.py tests/match/tools/test_rebuild_soaps_proposed.py
git commit -m "$(cat <<'EOF'
feat(match): add rebuild_soaps_proposed CLI with rotate-on-write

EOF
)"
```

---

### Task 3: Remove legacy generator; smoke real month

**Files:**
- Delete: `generate_soaps_proposed.py`
- Modify: any README / comment that points at it (grep first)

**Interfaces:** Consumes Task 2 CLI.

- [ ] **Step 1: Grep for `generate_soaps_proposed` and `soaps_proposed` references; update or remove stale docs pointing at the correct_matches miner**

- [ ] **Step 2: Delete `generate_soaps_proposed.py`**

- [ ] **Step 3: Smoke against one real month (read-only assert)**

Run: `source .venv/bin/activate && python -m sotd.match.tools.rebuild_soaps_proposed --month 2026-11 --out /tmp/soaps_proposed_smoke.yaml`

Manually confirm: no exact/regex-only noise flooding the file; brand rows present if Nov has them; `unknown.unmatched` only for unresolved.

- [ ] **Step 4: Commit**

```bash
git add -u generate_soaps_proposed.py
git add docs/  # if doc refs changed
git commit -m "$(cat <<'EOF'
chore: remove correct_matches-based soaps_proposed generator

EOF
)"
```

---

### Task 4: Rewrite `/propose-soaps`

**Files:**
- Modify: `.claude/commands/propose-soaps.md`
- Modify: `.claude/commands/propose-soaps-yaml.md` (contrast only)

**Interfaces:** Invokes `python -m sotd.match.tools.rebuild_soaps_proposed` then LLM pattern pass on `data/soaps_proposed.yaml`.

- [ ] **Step 1: Replace `propose-soaps.md` content** to match the approved spec:

  - Args: `--month` | `--range`, optional `--model` (`sonnet` default), optional `--patterns-only` (skip rebuild).
  - Step A: resolve months via `months_for_args` (same helper as today).
  - Confirm `data/matched/{month}.json` exists for each month; stop if any missing **unless** `--patterns-only`.
  - Step B: unless `--patterns-only`, run  
    `python -m sotd.match.tools.rebuild_soaps_proposed --month …` or `--range …`  
    (no separate `--force`; rotate is built-in).
  - Step C: LLM reads `data/soaps_proposed.yaml`, adds `patterns` covering each scent’s `entries` (Python `re.I` check per entry), writes **in place**, no rotate.
  - No validate-matches agents; no `data/proposed/*.json`.
  - Remind: optional `/validate-soap-proposals`; manual merge to `soaps.yaml`.

- [ ] **Step 2: Update contrast tables** in `propose-soaps.md` and `propose-soaps-yaml.md` so legacy JSON convert is clearly separate from `soaps_proposed.yaml`.

- [ ] **Step 3: Read back both commands; confirm no leftover “propose agents / proposed_soaps_to_yaml” as the soap staging path**

- [ ] **Step 4: Commit**

```bash
git add .claude/commands/propose-soaps.md .claude/commands/propose-soaps-yaml.md
git commit -m "$(cat <<'EOF'
docs(commands): retarget propose-soaps to rebuild CLI + pattern LLM

EOF
)"
```

---

### Task 5: Add `/validate-soap-proposals`

**Files:**
- Create: `.claude/commands/validate-soap-proposals.md`

**Interfaces:** Reads/writes `data/soaps_proposed.yaml` only.

- [ ] **Step 1: Create the command** with:

  - Args: optional `--model` (default `sonnet`); operates on current `data/soaps_proposed.yaml` (error if missing).
  - For each brand/scent (including processing `unknown`/`unmatched` entries individually): WebSearch to confirm product; set  
    `validation: validated | unable_to_validate`,  
    `source_url` **required** when validated,  
    `research` short note.
  - **Promote:** if an `unknown`/`unmatched` entry is identified, move it under the real brand/scent node with `validation: validated` + `source_url` + `research`; remove from unknown bucket; drop empty unknown nodes.
  - Do not rotate; do not edit `soaps.yaml`.
  - Print summary counts: validated / unable / promoted.

- [ ] **Step 2: Cross-link from `propose-soaps.md` wrap-up to this command**

- [ ] **Step 3: Commit**

```bash
git add .claude/commands/validate-soap-proposals.md .claude/commands/propose-soaps.md
git commit -m "$(cat <<'EOF'
docs(commands): add validate-soap-proposals annotate/promote flow

EOF
)"
```

---

### Task 6: Quality gate

**Files:** none new

- [ ] **Step 1: Run** `source .venv/bin/activate && make format lint typecheck test`

- [ ] **Step 2: Fix any failures introduced by this work**

- [ ] **Step 3: Commit only if fixes were needed**

```bash
git add -u
git commit -m "$(cat <<'EOF'
fix: clear quality gate after soap proposed rebuild

EOF
)"
```

---

## Spec coverage checklist

| Spec item | Task |
|-----------|------|
| Standalone rebuild CLI | 1–2 |
| Routing table incl. filtered | 1 |
| `matched.scent`, unknown bucket | 1 |
| Rotate `.bak` on rebuild only | 2 |
| Month/range merge + replace | 2 |
| Delete correct_matches generator | 3 |
| `/propose-soaps` = CLI + patterns | 4 |
| No existence research in propose | 4 |
| `/validate-soap-proposals` annotate + URL | 5 |
| Promote from unknown | 5 |
| Legacy proposed JSON path kept/documented | 4 |
| Never edit soaps.yaml | 4–5 |
