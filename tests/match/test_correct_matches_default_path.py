"""Regression tests: the match-layer correct_matches default resolves to the
run's data dir, not the process working directory (#23 instance 4).

Previously every matcher defaulted to a bare CWD-relative
``Path("data/correct_matches")``, so constructing a matcher from any
directory but the repo root silently loaded no correct matches and the
matcher fell back to regex-only matching. The default is now
``get_default_correct_matches_path()`` (run's data dir via ``get_data_dir()``,
relative data dirs anchored at the repo root), applied in ``BaseMatcher``,
``CatalogLoader.load_correct_matches`` and ``SoapMatcher``.
"""

from pathlib import Path

import pytest
import yaml

from sotd.match.base_matcher import clear_catalog_cache
from sotd.match.blade_matcher import BladeMatcher
from sotd.match.loaders import CatalogLoader, clear_yaml_cache
from sotd.match.razor_matcher import RazorMatcher
from sotd.utils.data_dir import get_default_correct_matches_path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = REPO_ROOT / "data"


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_catalog_cache()
    clear_yaml_cache()
    yield
    clear_catalog_cache()
    clear_yaml_cache()


@pytest.fixture
def foreign_cwd(monkeypatch, tmp_path):
    """Run the test from a directory with no data/ in it."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SOTD_DATA_DIR", raising=False)
    return tmp_path


def test_default_cm_path_is_run_data_dir(foreign_cwd):
    assert get_default_correct_matches_path() == DATA_DIR / "correct_matches"
    assert get_default_correct_matches_path().is_absolute()


def test_default_cm_path_honours_sotd_data_dir(monkeypatch, tmp_path):
    data_dir = tmp_path / "elsewhere"
    monkeypatch.setenv("SOTD_DATA_DIR", str(data_dir))
    assert get_default_correct_matches_path() == data_dir / "correct_matches"


def test_default_cm_path_anchors_relative_data_dir_at_repo_root(monkeypatch):
    monkeypatch.setenv("SOTD_DATA_DIR", "data")
    assert get_default_correct_matches_path() == DATA_DIR / "correct_matches"


def test_razor_matcher_default_cm_loads_from_foreign_cwd(foreign_cwd):
    matcher = RazorMatcher(catalog_path=DATA_DIR / "razors.yaml")
    assert matcher.correct_matches_path == DATA_DIR / "correct_matches"
    assert len(matcher.correct_matches) > 0
    assert "Above the Tie" in matcher.correct_matches
    result = matcher.match("above the tie - atlas s1")
    assert result.matched is not None
    assert result.matched["brand"] == "Above the Tie"
    assert result.matched["model"] == "S1"
    assert result.match_type == "exact"


def test_blade_matcher_default_cm_loads_from_foreign_cwd(foreign_cwd):
    matcher = BladeMatcher(catalog_path=DATA_DIR / "blades.yaml")
    assert matcher.correct_matches_path == DATA_DIR / "correct_matches"
    assert len(matcher.correct_matches) > 0
    result = matcher.match("feather ac professional")
    assert result.matched is not None
    assert result.matched["brand"] == "Feather"
    assert result.matched["model"] == "Pro"
    assert result.match_type == "exact"


def test_soap_matcher_default_cm_loads_from_foreign_cwd(foreign_cwd):
    pytest.importorskip("rich")
    from sotd.match.soap_matcher import SoapMatcher

    matcher = SoapMatcher(catalog_path=DATA_DIR / "soaps.yaml")
    assert matcher.correct_matches_path == DATA_DIR / "correct_matches"
    assert len(matcher.correct_matches) > 0
    assert "345 Soap Co." in matcher.correct_matches
    result = matcher.match("345 soap co. - cairn")
    assert result.matched is not None
    assert result.matched["brand"] == "345 Soap Co."
    assert result.matched["scent"] == "Cairn"
    assert result.match_type == "exact"


def test_loader_default_cm_loads_from_foreign_cwd(foreign_cwd):
    loader = CatalogLoader()
    razor_cm = loader.load_correct_matches(field_type="razor")
    assert len(razor_cm) > 0
    assert "Above the Tie" in razor_cm
    blade_cm = loader.load_correct_matches(field_type="blade")
    assert len(blade_cm) > 0


def test_sotd_data_dir_cm_is_used(monkeypatch, tmp_path):
    data_dir = tmp_path / "custom_data"
    cm_dir = data_dir / "correct_matches"
    cm_dir.mkdir(parents=True)
    (cm_dir / "razor.yaml").write_text(
        yaml.safe_dump({"MarkerBrand": {"MarkerModel": ["marker razor string"]}}),
        encoding="utf-8",
    )
    catalog_path = tmp_path / "razors.yaml"
    catalog_path.write_text(
        yaml.safe_dump(
            {"MarkerBrand": {"MarkerModel": {"patterns": ["marker"], "format": "DE"}}}
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SOTD_DATA_DIR", str(data_dir))
    monkeypatch.chdir(tmp_path)

    matcher = RazorMatcher(catalog_path=catalog_path)
    assert matcher.correct_matches_path == cm_dir
    assert "MarkerBrand" in matcher.correct_matches
    result = matcher.match("marker razor string")
    assert result.matched is not None
    assert result.matched["brand"] == "MarkerBrand"
    assert result.match_type == "exact"


def test_explicit_cm_path_wins_over_default(monkeypatch, tmp_path):
    empty_cm = tmp_path / "empty_cm"
    empty_cm.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("SOTD_DATA_DIR", raising=False)

    matcher = RazorMatcher(
        catalog_path=DATA_DIR / "razors.yaml", correct_matches_path=empty_cm
    )
    assert matcher.correct_matches_path == empty_cm
    assert matcher.correct_matches == {}
