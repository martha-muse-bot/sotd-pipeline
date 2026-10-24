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
