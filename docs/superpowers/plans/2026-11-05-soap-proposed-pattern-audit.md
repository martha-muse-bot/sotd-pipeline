# Soap Proposed Pattern Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a standalone CLI that audits `soaps_proposed.yaml` patterns against all-time extracted soap normals (missing TPs + same-file hard FPs as the clean gate; contested/ambiguous reported), and wire `/propose-soaps` to run an LLM fix loop until the hard gate is clean.

**Architecture:** Pure Python builds a label index + scans extracted corpus once; classifies each pattern hit; emits a JSON report and exit code. The Claude command invokes the CLI after pattern write and feeds hard/contested rows back to the LLM for pattern edits (capped iterations). No catalog auto-edits.

**Tech Stack:** Python 3.11+, PyYAML, pytest, argparse; `.claude/commands/propose-soaps.md`

**Spec:** `docs/superpowers/specs/2026-11-05-soap-proposed-rebuild-design.md` (Step 2b)

## Global Constraints

- Corpus default: all `data/extracted/YYYY-MM.json` → `soap.normalized` (deduped).
- Clean gate: no missing required TPs; no hard FPs (same `soaps_proposed.yaml` node collisions only).
- Contested = different brand/scent in `soaps.yaml` or `correct_matches/soap.yaml` — report, exit still 0 if hard gate clean.
- Ambiguous = unlabeled history — report only, capped samples.
- Never edit `data/soaps.yaml` or `correct_matches` from audit/LLM accept-as-ours.
- Audit CLI independently runnable; `/propose-soaps` invokes it.
- Work on feature branch / worktree that already has rebuild CLI (`feat/soap-proposed-rebuild` if still active).
- Activate `.venv`; `PYTHONPATH` = checkout root.

## Review Focus

- Entry covered by pattern A but string also hits pattern of another proposed scent → hard FP on both sides (or at least reported as collision).
- Historical string labeled catalog BrandX/ScentX while proposed BrandY/ScentY pattern matches it → contested, not exit 1.
- Same brand+scent in catalog as proposed node → same-product OK, not contested.
- Proposed scent with no `patterns` key (e.g. `unknown`/`unmatched`) → skip pattern scan; still fail if it has patterns that miss entries.
- Empty extracted dir / no months → clear error, non-zero exit (not silent clean).

---

## File map

| Path | Role |
|------|------|
| `sotd/match/tools/audit_soaps_proposed_patterns.py` | Label index, corpus load, classify, report, CLI |
| `tests/match/tools/test_audit_soaps_proposed_patterns.py` | Unit tests |
| `.claude/commands/propose-soaps.md` | Add Step 2b audit + LLM fix loop after patterns |

---

### Task 1: Label index + hit classification (pure functions)

**Files:**
- Create: `sotd/match/tools/audit_soaps_proposed_patterns.py`
- Test: `tests/match/tools/test_audit_soaps_proposed_patterns.py`

**Interfaces:**
- Produces:
  - `normalize_key(brand: str, scent: str) -> tuple[str, str]` — NFC + casefold for comparisons
  - `build_label_index(soaps_catalog: dict, correct_matches: dict, proposed: dict) -> dict[str, set[tuple[str, str]]]`  
    Map `normalized_string_lower` → set of `(brand, scent)` labels from catalog scent patterns’… **No** — labels come from **known string membership**, not from running catalog regexes.  
    **Correct approach:**  
    - From `correct_matches/soap.yaml`: each entry string under Brand→Scent → label `(Brand, Scent)`.  
    - From `soaps.yaml`: do **not** invent strings from patterns; only use correct_matches + proposed entries for string→label. For “same product OK” when a hit equals an entry already under same brand/scent in proposed or appears under that brand/scent in correct_matches.  
    - Catalog brand+scent existence used when classifying contested: if string is labeled in correct_matches as different pair → contested.  
    - Additionally: strings that are **entries** under other proposed nodes → hard collision labels.  
  - `classify_hit(*, hit: str, owner_brand: str, owner_scent: str, label_index: dict, proposed_owners: dict[str, tuple[str, str]]) -> Literal["tp","same_ok","hard_fp","contested","ambiguous"]`  
    - `tp` if hit in owner entries (caller may handle TP separately).  
    - `same_ok` if label_index[hit] contains same normalize_key(owner).  
    - `hard_fp` if proposed_owners[hit] is a different proposed (brand,scent).  
    - `contested` if label_index[hit] has any other brand/scent from correct_matches/catalog entry lists.  
    - else `ambiguous`.

**Pin in tests (tmp structures, no real data files):**

```python
def test_classify_hard_fp_other_proposed_node():
    # hit owned by proposed A/S1 and also matched by B/S2 patterns → hard_fp for B

def test_classify_contested_correct_matches_other_scent():
    # hit in correct_matches under X/Y, owner is A/B → contested

def test_classify_same_ok_correct_matches_same_scent():
    # hit in correct_matches under A/B, owner A/B → same_ok

def test_normalize_key_nfc():
    # Mélange vs Melange NFC variants → equal keys
```

- [ ] **Step 1: Write failing tests** for the classify / index helpers above  
- [ ] **Step 2: Run — expect FAIL**  
  `source .venv/bin/activate && PYTHONPATH=. pytest tests/match/tools/test_audit_soaps_proposed_patterns.py -v -k "classify or normalize_key or label_index"`  
- [ ] **Step 3: Implement helpers in `audit_soaps_proposed_patterns.py`**  
  Build `label_index` only from `correct_matches` entry strings + proposed `entries` (proposed entries also feed `proposed_owners: hit -> (brand,scent)`). Catalog YAML is optional for v1 beyond documenting same brand/scent keys if needed; **primary other-product labels = correct_matches**. If a string appears under two correct_matches scents, keep both labels in the set.  
- [ ] **Step 4: Tests PASS**  
- [ ] **Step 5: Commit** `feat(match): add soap proposed pattern audit classifiers`

---

### Task 2: Corpus load + audit engine + CLI

**Files:**
- Modify: `sotd/match/tools/audit_soaps_proposed_patterns.py`
- Test: `tests/match/tools/test_audit_soaps_proposed_patterns.py`

**Interfaces:**
- `load_extracted_soap_normals(extracted_dir: Path) -> list[str]` — all months’ unique `soap.normalized` (preserve stable sort). Skip missing months silently; if zero files, raise `FileNotFoundError`.
- `audit_proposed(*, proposed: dict, corpus: list[str], correct_matches: dict, ambiguous_cap: int = 5) -> dict`  
  Report shape:

```json
{
  "clean": true,
  "missing_tps": [{"brand": "...", "scent": "...", "entry": "...", "patterns": [...]}],
  "hard_fps": [{"brand": "...", "scent": "...", "pattern": "...", "hit": "...", "other_proposed": ["Brand", "Scent"]}],
  "contested": [{"brand": "...", "scent": "...", "pattern": "...", "hit": "...", "labels": [["X","Y"]]}],
  "ambiguous": [{"brand": "...", "scent": "...", "pattern": "...", "hits_sample": ["..."]}],
  "stats": {"corpus_size": 0, "scents_audited": 0}
}
```

  Logic per proposed brand/scent with non-empty `patterns`:
  1. For each entry: if no pattern matches → `missing_tps`.
  2. For each pattern: scan corpus; for each hit classify; bucket hard_fp / contested / ambiguous (cap ambiguous hits per scent).
  3. Skip `unknown`/`unmatched` if no patterns; if patterns present, audit normally.
  4. `clean = not missing_tps and not hard_fps`.

- `main(argv) -> int` — args: `--proposed` (default `data/soaps_proposed.yaml`), `--extracted-dir` (default `data/extracted`), `--correct-matches` (default `data/correct_matches/soap.yaml`), `--report` optional JSON path, `--ambiguous-cap` default 5. Exit `0` if clean else `1`; `2` on usage/IO errors. Print short summary to stdout; write full JSON to `--report` or stdout if unset (prefer `--report` default `data/soaps_proposed_audit.json` **or** print JSON to stdout only — **builder call: write report to stdout as JSON when `--report -`, else default path `data/soaps_proposed_audit.json`**).

**Tests (tmp_path):**

```python
def test_audit_missing_tp():
    # entry not covered → clean False, missing_tps nonempty, exit path via main

def test_audit_hard_fp_two_proposed_nodes():
    # broad pattern on A also matches B's entry → hard_fps

def test_audit_contested_does_not_unclean():
    # correct_matches other scent; missing/hard empty → clean True, contested nonempty

def test_load_extracted_dedupes(tmp_path):
```

- [ ] **Step 1: Failing tests**  
- [ ] **Step 2: Run FAIL**  
- [ ] **Step 3: Implement load + audit + argparse `main`**  
- [ ] **Step 4: Full test module PASS**  
- [ ] **Step 5: Commit** `feat(match): add audit_soaps_proposed_patterns CLI`

---

### Task 3: Wire `/propose-soaps` audit + LLM fix loop

**Files:**
- Modify: `.claude/commands/propose-soaps.md`

**Interfaces:** After Step C pattern write:

1. Run  
   `python -m sotd.match.tools.audit_soaps_proposed_patterns`  
   (defaults; print summary).
2. If exit `0`: print contested/ambiguous summary counts; continue to wrap-up.
3. If exit `1`: read report JSON; LLM adjusts **only** patterns for scents in `missing_tps` / `hard_fps`; may use `contested` as judgment context (tighten vs note accept-as-ours — **do not** edit catalog files; append a short “human follow-up” note in the chat summary if accepting).
4. Re-write `soaps_proposed.yaml` patterns in place; re-run audit.
5. Max **3** audit→fix iterations; if still exit `1`, stop and show remaining hard failures.
6. Update contrast/wrap-up to mention audit gate.

- [ ] **Step 1: Edit propose-soaps.md** with the loop as explicit steps (Step C2 / Step D renumber as needed)  
- [ ] **Step 2: Read back — confirm standalone CLI documented for humans**  
- [ ] **Step 3: Commit** `docs(commands): add pattern audit fix loop to propose-soaps`

---

### Task 4: Quality gate

- [ ] **Step 1:** `make format` + `PYTHONPATH=. pytest tests/match/tools/test_audit_soaps_proposed_patterns.py -v`  
- [ ] **Step 2:** Fix only issues from this work  
- [ ] **Step 3:** Optional smoke: audit current `data/soaps_proposed.yaml` against real `data/extracted` with `--report /tmp/audit.json`; confirm exits and report shape (do not commit report)  
- [ ] **Step 4:** Commit only if fixes needed  

---

## Spec coverage

| Spec item | Task |
|-----------|------|
| Required TP missing → hard fail | 1–2 |
| Same-file proposed collision → hard FP | 1–2 |
| Catalog/CM other label → contested | 1–2 |
| Ambiguous report-only + cap | 2 |
| Extracted corpus all-time | 2 |
| Standalone CLI exit 0/1 | 2 |
| propose-soaps loop, max 3, no catalog edits | 3 |
