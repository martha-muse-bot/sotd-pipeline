#!/usr/bin/env python3
"""Tests for the public-bundle verifier."""

import json

# Import via the repo-root `scripts/` namespace package, like the sibling tests in
# this directory (run with PYTHONPATH=. — the Makefile/CI convention). No sys.path
# hack here: inserting tests/ on sys.path would shadow `scripts` with tests/scripts/.
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
    assert d.is_dir()
    assert check_bundle(tmp_path) == []


def test_missing_slice_month_fails(tmp_path):
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
    # annual/ absent is fine; a stray enriched dir inside the bundle tree is NOT
    (tmp_path / "aggregated" / "enriched").mkdir(parents=True)
    problems = check_bundle(tmp_path)
    assert any("enriched" in p for p in problems)


def test_top_level_enriched_sibling_does_not_block(tmp_path):
    # The pipeline data root legitimately keeps enriched/ next to aggregated/;
    # the rsync selection never publishes it, so it must not fail the check.
    (tmp_path / "enriched").mkdir()
    _mk(tmp_path, "aggregated/2026-09.json", {"meta": {}, "data": {}})
    _mk(tmp_path, "aggregated/user_analysis/2026-09.json", {"users": {}})
    _mk(tmp_path, "aggregated/product_usage/2026-09.json", {"meta": {}})
    assert check_bundle(tmp_path) == []
