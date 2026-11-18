"""Tests for WSDB lookup utility with slug support."""


import pytest
import yaml

from sotd.utils.wsdb_lookup import WSDBLookup


@pytest.fixture
def temp_project_root(tmp_path):
    """Create a temporary project root with data directories."""
    project_root = tmp_path / "project"
    project_root.mkdir()

    # Create data directories
    (project_root / "data" / "wsdb").mkdir(parents=True)
    (project_root / "data").mkdir(exist_ok=True)

    return project_root


@pytest.fixture
def mock_pipeline_soaps(temp_project_root):
    """Create mock pipeline soaps.yaml with wsdb_slug fields."""
    soaps_file = temp_project_root / "data" / "soaps.yaml"

    soaps_data = {
        "Barrister and Mann": {
            "patterns": ["barrister.*mann"],
            "scents": {
                "Seville": {
                    "patterns": ["seville"],
                    "wsdb_slug": "barrister-and-mann-seville",
                },
            },
        },
        "The Artisan Soap Shoppe": {
            "patterns": ["artisan.*soap.*shoppe"],
            "scents": {
                "Crisp Vetiver": {
                    "patterns": ["crisp.*vetiver"],
                    "wsdb_slug": "artisan-shave-shoppe-crisp-vetiver",
                },
            },
        },
        "Stirling Soap Co.": {
            "patterns": ["stirling"],
            "scents": {
                "Executive Man": {
                    "patterns": ["executive.*man"],
                    "wsdb_slug": "stirling-soap-co-executive-man",
                },
            },
        },
    }

    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(soaps_data, f)

    return soaps_data


def test_slug_lookup_with_slug_in_catalog(temp_project_root, mock_pipeline_soaps):
    """Test slug lookup when wsdb_slug exists in catalog."""
    lookup = WSDBLookup(project_root=temp_project_root)

    slug = lookup.get_wsdb_slug("Barrister and Mann", "Seville")

    assert slug == "barrister-and-mann-seville"


def test_slug_lookup_different_brand(temp_project_root, mock_pipeline_soaps):
    """Test slug lookup for different brand."""
    lookup = WSDBLookup(project_root=temp_project_root)

    slug = lookup.get_wsdb_slug("The Artisan Soap Shoppe", "Crisp Vetiver")

    assert slug == "artisan-shave-shoppe-crisp-vetiver"


def test_slug_lookup_stirling(temp_project_root, mock_pipeline_soaps):
    """Test slug lookup for Stirling."""
    lookup = WSDBLookup(project_root=temp_project_root)

    slug = lookup.get_wsdb_slug("Stirling Soap Co.", "Executive Man")

    assert slug == "stirling-soap-co-executive-man"


def test_no_match_brand_not_in_catalog(temp_project_root, mock_pipeline_soaps):
    """Test when brand is not in catalog."""
    lookup = WSDBLookup(project_root=temp_project_root)

    slug = lookup.get_wsdb_slug("Unknown Brand", "Unknown Scent")

    assert slug is None


def test_no_match_scent_not_in_catalog(temp_project_root, mock_pipeline_soaps):
    """Test when scent is not in catalog."""
    lookup = WSDBLookup(project_root=temp_project_root)

    slug = lookup.get_wsdb_slug("Barrister and Mann", "Unknown Scent")

    assert slug is None


def test_no_match_scent_without_slug(temp_project_root, mock_pipeline_soaps):
    """Test when scent exists but has no wsdb_slug."""
    # Add a scent without wsdb_slug
    soaps_file = temp_project_root / "data" / "soaps.yaml"
    with soaps_file.open("r", encoding="utf-8") as f:
        soaps_data = yaml.safe_load(f)

    soaps_data["Barrister and Mann"]["scents"]["No Slug"] = {
        "patterns": ["no.*slug"],
    }

    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(soaps_data, f)

    lookup = WSDBLookup(project_root=temp_project_root)
    slug = lookup.get_wsdb_slug("Barrister and Mann", "No Slug")

    assert slug is None


def test_empty_brand_or_scent(temp_project_root, mock_pipeline_soaps):
    """Test with empty brand or scent."""
    lookup = WSDBLookup(project_root=temp_project_root)

    assert lookup.get_wsdb_slug("", "Seville") is None
    assert lookup.get_wsdb_slug("Barrister and Mann", "") is None
    assert lookup.get_wsdb_slug("", "") is None


def test_missing_soaps_yaml(temp_project_root):
    """Test when soaps.yaml doesn't exist."""
    lookup = WSDBLookup(project_root=temp_project_root)

    # Should return None when soaps.yaml doesn't exist
    slug = lookup.get_wsdb_slug("Barrister and Mann", "Seville")

    assert slug is None


def test_get_all_assigned_slugs(temp_project_root, mock_pipeline_soaps):
    """Test get_all_assigned_slugs returns exactly the wsdb_slug values from the catalog."""
    lookup = WSDBLookup(project_root=temp_project_root)

    assigned = lookup.get_all_assigned_slugs()

    assert assigned == {
        "barrister-and-mann-seville",
        "artisan-shave-shoppe-crisp-vetiver",
        "stirling-soap-co-executive-man",
    }


def test_get_all_assigned_slugs_excludes_empty_and_missing(temp_project_root, mock_pipeline_soaps):
    """Test get_all_assigned_slugs excludes scents without wsdb_slug."""
    soaps_file = temp_project_root / "data" / "soaps.yaml"
    with soaps_file.open("r", encoding="utf-8") as f:
        soaps_data = yaml.safe_load(f)

    soaps_data["Barrister and Mann"]["scents"]["No Slug"] = {"patterns": ["no"]}
    soaps_data["Barrister and Mann"]["scents"]["Empty Slug"] = {
        "patterns": ["empty"],
        "wsdb_slug": "",
    }

    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(soaps_data, f)

    lookup = WSDBLookup(project_root=temp_project_root)
    assigned = lookup.get_all_assigned_slugs()

    assert "barrister-and-mann-seville" in assigned
    assert "No Slug" not in assigned
    assert "" not in assigned
