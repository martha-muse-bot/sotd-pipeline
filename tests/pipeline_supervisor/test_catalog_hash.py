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
    (tmp_path / "e1").mkdir()
    (tmp_path / "e2").mkdir()
    assert catalog_hash(tmp_path / "e1") == catalog_hash(tmp_path / "e2")
