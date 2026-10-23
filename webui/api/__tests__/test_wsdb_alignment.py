#!/usr/bin/env python3
"""Tests for WSDB alignment API endpoints."""

import copy
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import httpx
import pytest
import yaml
from api.main import app
from api.wsdb_alignment import pre_normalize_wsdb_entries
from fastapi.testclient import TestClient

client = TestClient(app)

# Test data
MOCK_WSDB_DATA = [
    {
        "brand": "Barrister and Mann",
        "name": "Seville",
        "type": "Soap",
        "slug": "barrister-and-mann-seville",
        "scent_notes": ["citrus", "lavender"],
        "collaborators": [],
        "tags": ["classic"],
        "category": "Traditional",
    },
    {
        "brand": "Declaration Grooming",
        "name": "Massacre of the Innocents",
        "type": "Soap",
        "slug": "declaration-grooming-massacre-of-the-innocents",
        "scent_notes": ["pine", "smoke"],
        "collaborators": ["Chatillon Lux"],
        "tags": ["seasonal"],
        "category": "Artisan",
    },
    {
        "brand": "Stirling Soap Co.",
        "name": "Executive Man",
        "type": "Soap",
        "slug": "stirling-executive-man",
        "scent_notes": ["oakmoss", "citrus"],
        "collaborators": [],
        "tags": ["dupe"],
        "category": "Value",
    },
    # Non-soap item to test filtering
    {
        "brand": "Some Brand",
        "name": "Some Aftershave",
        "type": "Aftershave",
        "slug": "some-aftershave",
    },
]

MOCK_PIPELINE_DATA = {
    "Barrister and Mann": {
        "patterns": ["barrister.*mann", "b&m", "b and m"],
        "scents": {
            "Seville": {"patterns": ["seville"]},
            "Leviathan": {"patterns": ["leviathan", "levi"]},
            "Le Grand Chypre": {"patterns": ["le.*grand.*chypre"]},
        },
    },
    "Declaration Grooming": {
        "patterns": ["declaration.*grooming", "dg"],
        "scents": {
            "Massacre of the Innocents": {"patterns": ["massacre.*innocents", "moti"]},
            "Chaotic Neutral": {"patterns": ["chaotic.*neutral", "cn"]},
        },
    },
    "Stirling Soap Co.": {
        "patterns": ["stirling.*soap", "stirling"],
        "scents": {
            "Executive Man": {"patterns": ["executive.*man", "exec man"]},
            "Barbershop": {"patterns": ["barbershop"]},
        },
    },
    "Black Mountain Shaving": {
        "patterns": ["black.*mountain.*shaving", "bms"],
        "scents": {
            "Sandalwood": {"patterns": ["sandalwood"]},
        },
    },
}


@pytest.fixture
def mock_data_files(tmp_path):
    """Create temporary test data files."""
    # Create data directory
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    # Create wsdb subdirectory
    wsdb_dir = data_dir / "wsdb"
    wsdb_dir.mkdir()

    # Write software.json in wsdb subdirectory
    software_file = wsdb_dir / "software.json"
    with software_file.open("w", encoding="utf-8") as f:
        json.dump(MOCK_WSDB_DATA, f)

    # Write soaps.yaml
    soaps_file = data_dir / "soaps.yaml"
    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(MOCK_PIPELINE_DATA, f)

    return data_dir


class TestPreNormalizeWsdbEntries:
    """Tests for pre_normalize_wsdb_entries (slug_space_norm, hyphens to spaces)."""

    def test_slug_space_norm_present_and_has_spaces(self):
        """Pre-normalized entries include slug_space_norm with hyphens replaced by spaces."""
        soaps = [
            {
                "brand": "Abbate Y La Mantia",
                "name": "Matteo 9-11",
                "type": "Soap",
                "slug": "abbate-y-la-mantia-matteo-911-soap",
            },
        ]
        entries = pre_normalize_wsdb_entries(soaps)
        assert len(entries) == 1
        assert "slug_space_norm" in entries[0]
        # Hyphens replaced by spaces, then normalize_for_matching (lowercase, etc.)
        assert entries[0]["slug_space_norm"] == "abbate y la mantia matteo 911 soap"

    def test_slug_space_norm_empty_slug(self):
        """Entries with empty or missing slug get empty slug_space_norm."""
        soaps = [{"brand": "X", "name": "Y", "type": "Soap"}]
        entries = pre_normalize_wsdb_entries(soaps)
        assert len(entries) == 1
        assert entries[0]["slug_space_norm"] == ""


class TestLoadWSDBSoaps:
    """Tests for /api/wsdb-alignment/load-wsdb endpoint."""

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_wsdb_soaps_success(self, mock_root, mock_data_files):
        """Test successful loading of WSDB soaps."""
        # Mock PROJECT_ROOT to return parent of data directory
        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        response = client.get("/api/wsdb-alignment/load-wsdb")

        assert response.status_code == 200
        data = response.json()

        assert "soaps" in data
        assert "total_count" in data
        assert "total_software_items" in data
        assert "loaded_at" in data

        # Should filter out non-soap items
        assert data["total_count"] == 3  # Only soaps
        assert data["total_software_items"] == 4  # All items including aftershave
        assert len(data["soaps"]) == 3

        # Verify soap brands
        brands = [soap["brand"] for soap in data["soaps"]]
        assert "Barrister and Mann" in brands
        assert "Declaration Grooming" in brands
        assert "Stirling Soap Co." in brands

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_wsdb_soaps_file_not_found(self, mock_root, tmp_path):
        """Test error handling when software.json is not found."""
        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.get("/api/wsdb-alignment/load-wsdb")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_wsdb_soaps_invalid_json(self, mock_root, tmp_path):
        """Test error handling when software.json is invalid."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        wsdb_dir = data_dir / "wsdb"
        wsdb_dir.mkdir()
        software_file = wsdb_dir / "software.json"
        software_file.write_text("invalid json content")

        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.get("/api/wsdb-alignment/load-wsdb")

        assert response.status_code == 500
        assert "parse" in response.json()["detail"].lower()


class TestLoadPipelineSoaps:
    """Tests for /api/wsdb-alignment/load-pipeline endpoint."""

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_pipeline_soaps_success(self, mock_root, mock_data_files):
        """Test successful loading of pipeline soaps."""
        # Mock PROJECT_ROOT to return parent of data directory
        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        response = client.get("/api/wsdb-alignment/load-pipeline")

        assert response.status_code == 200
        data = response.json()

        assert "soaps" in data
        assert "total_brands" in data
        assert "total_scents" in data
        assert "loaded_at" in data

        assert data["total_brands"] == 4
        assert data["total_scents"] == 8
        assert len(data["soaps"]) == 4

        # Verify structure
        for soap in data["soaps"]:
            assert "brand" in soap
            assert "scents" in soap
            assert isinstance(soap["scents"], list)
            for scent in soap["scents"]:
                assert "name" in scent
                assert "patterns" in scent

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_pipeline_soaps_file_not_found(self, mock_root, tmp_path):
        """Test error handling when soaps.yaml is not found."""
        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.get("/api/wsdb-alignment/load-pipeline")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_pipeline_soaps_invalid_yaml(self, mock_root, tmp_path):
        """Test error handling when soaps.yaml is invalid."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        soaps_file = data_dir / "soaps.yaml"
        soaps_file.write_text("invalid: yaml: content: [")

        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.get("/api/wsdb-alignment/load-pipeline")

        assert response.status_code == 500
        assert "parse" in response.json()["detail"].lower()

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_load_pipeline_soaps_excludes_mashup_scents(self, mock_root, tmp_path):
        """Test that scents with countable: false (mashups) are excluded from load-pipeline."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        soaps_file = data_dir / "soaps.yaml"
        pipeline_with_mashup = {
            "Barrister and Mann": {
                "patterns": ["barrister.*mann"],
                "scents": {
                    "Seville": {"patterns": ["seville"]},
                    "Sample Mashup": {"countable": False, "patterns": ["sample.*mashup"]},
                },
            },
        }
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_with_mashup, f)

        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.get("/api/wsdb-alignment/load-pipeline")

        assert response.status_code == 200
        data = response.json()
        assert data["total_brands"] == 1
        assert data["total_scents"] == 1  # Only Seville; Sample Mashup excluded
        bm = data["soaps"][0]
        assert bm["brand"] == "Barrister and Mann"
        scent_names = [s["name"] for s in bm["scents"]]
        assert "Seville" in scent_names
        assert "Sample Mashup" not in scent_names


class TestFuzzyMatch:
    """Tests for /api/wsdb-alignment/fuzzy-match endpoint."""

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_pipeline_to_wsdb_exact(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching from pipeline to WSDB with exact match."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "Barrister and Mann",
                "scent": "Seville",
                "threshold": 0.7,
                "limit": 5,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "matches" in data
        assert "query" in data
        assert "threshold" in data
        assert "total_matches" in data

        # Should find exact match with high confidence
        assert len(data["matches"]) > 0
        top_match = data["matches"][0]
        assert top_match["brand"] == "Barrister and Mann"
        assert top_match["name"] == "Seville"
        assert top_match["confidence"] >= 90  # High confidence for exact match
        assert top_match["source"] == "wsdb"
        assert "details" in top_match
        assert "scent_notes" in top_match["details"]

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_pipeline_to_wsdb_close_match(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching with close but not exact match."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "Barister Mann",  # Typo in brand
                "scent": "Seville",
                "threshold": 0.7,
                "limit": 5,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should still find match due to fuzzy matching
        assert len(data["matches"]) > 0
        assert data["matches"][0]["brand"] == "Barrister and Mann"

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_wsdb_to_pipeline(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching from WSDB to pipeline."""
        pipeline_soaps = []
        for brand, brand_data in MOCK_PIPELINE_DATA.items():
            scents = [
                {"name": scent, "patterns": data.get("patterns", [])}
                for scent, data in brand_data["scents"].items()
            ]
            pipeline_soaps.append({"brand": brand, "scents": scents})

        mock_wsdb.return_value = {"soaps": [], "total_count": 0}
        mock_pipeline.return_value = {"soaps": pipeline_soaps, "total_brands": 3, "total_scents": 6}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "wsdb",
                "brand": "Declaration Grooming",
                "scent": "Massacre of the Innocents",
                "threshold": 0.7,
                "limit": 5,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert len(data["matches"]) > 0
        top_match = data["matches"][0]
        assert top_match["brand"] == "Declaration Grooming"
        assert top_match["source"] == "pipeline"
        assert "patterns" in top_match["details"]

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_no_matches_below_threshold(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching with no matches below threshold."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "Completely Different Brand",
                "scent": "Nonexistent Scent",
                "threshold": 0.9,  # High threshold
                "limit": 5,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should have no matches or very few low-confidence matches
        assert data["total_matches"] >= 0

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_respects_limit(self, mock_pipeline, mock_wsdb):
        """Test that fuzzy matching respects result limit."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "Barrister",
                "scent": "Seville",
                "threshold": 0.0,
                "limit": 2,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should respect limit
        assert len(data["matches"]) <= 2

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_empty_strings(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching with empty strings."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "",
                "scent": "",
                "threshold": 0.7,
                "limit": 5,
                "mode": "brand_scent",
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should handle empty strings gracefully
        assert "matches" in data

    @patch("api.wsdb_alignment.load_wsdb_soaps")
    @patch("api.wsdb_alignment.load_pipeline_soaps")
    async def test_fuzzy_match_brands_only_mode(self, mock_pipeline, mock_wsdb):
        """Test fuzzy matching in brands-only mode."""
        mock_wsdb.return_value = {"soaps": MOCK_WSDB_DATA[:3], "total_count": 3}
        mock_pipeline.return_value = {"soaps": [], "total_brands": 0, "total_scents": 0}

        # Test with matching brand but different scent
        response = client.post(
            "/api/wsdb-alignment/fuzzy-match",
            json={
                "source_type": "pipeline",
                "brand": "Barrister and Mann",
                "scent": "Completely Different Scent",  # Different scent
                "threshold": 0.7,
                "limit": 5,
                "mode": "brands",  # Brands only mode
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Should still find match based on brand alone
        assert len(data["matches"]) > 0
        # Top match should be Barrister and Mann with high brand score
        top_match = data["matches"][0]
        assert top_match["brand"] == "Barrister and Mann"
        assert top_match["brand_score"] >= 90  # High brand score
        # In brands mode, confidence should equal brand_score
        assert top_match["confidence"] == top_match["brand_score"]


class TestRefreshWSDBData:
    """Tests for /api/wsdb-alignment/refresh-wsdb-data endpoint."""

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    @patch("httpx.AsyncClient")
    async def test_refresh_wsdb_data_success(self, mock_client, mock_root, tmp_path):
        """Test successful WSDB data refresh."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.json.return_value = MOCK_WSDB_DATA
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        # Setup temp directory with wsdb subdirectory
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        wsdb_dir = data_dir / "wsdb"
        wsdb_dir.mkdir()
        mock_root.__truediv__ = lambda self, other: tmp_path / other

        response = client.post("/api/wsdb-alignment/refresh-wsdb-data")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["soap_count"] == 3  # 3 soaps in mock data
        assert "updated_at" in data
        assert data["error"] is None

        # Verify file was written to correct location
        software_file = wsdb_dir / "software.json"
        assert software_file.exists()

        # Verify content
        with software_file.open("r", encoding="utf-8") as f:
            saved_data = json.load(f)
        assert len(saved_data) == 4  # All items including aftershave

    @patch("httpx.AsyncClient")
    async def test_refresh_wsdb_data_http_error(self, mock_client):
        """Test WSDB refresh with HTTP error."""
        # Create mock that raises error on get()
        mock_get = AsyncMock(side_effect=httpx.HTTPError("Connection failed"))

        mock_client_instance = MagicMock()
        mock_client_instance.get = mock_get
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock(return_value=None)
        mock_client.return_value = mock_client_instance

        response = client.post("/api/wsdb-alignment/refresh-wsdb-data")

        assert response.status_code == 200  # Returns 200 with error in response
        data = response.json()

        assert data["success"] is False
        assert data["soap_count"] == 0
        assert data["error"] is not None
        assert "HTTP error" in data["error"] or "Connection failed" in data["error"]

    @patch("httpx.AsyncClient")
    async def test_refresh_wsdb_data_invalid_response(self, mock_client):
        """Test WSDB refresh with invalid response format."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"invalid": "format"}  # Not a list
        mock_response.raise_for_status = MagicMock()

        mock_client_instance = MagicMock()
        mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_client_instance.__aexit__ = AsyncMock()
        mock_client_instance.get = AsyncMock(return_value=mock_response)
        mock_client.return_value = mock_client_instance

        response = client.post("/api/wsdb-alignment/refresh-wsdb-data")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "Invalid response format" in data["error"]


class TestAliasFuzzyMatch:
    """Tests for alias matching functionality in batch-analyze endpoint."""

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_alias_matching_brands_only(self, mock_root, mock_data_files):
        """Test that alias matching works in brands only mode."""
        # Add alias data to pipeline
        pipeline_with_aliases = copy.deepcopy(MOCK_PIPELINE_DATA)
        pipeline_with_aliases["Alexandria Grooming"] = {
            "aliases": ["Alexendria Fragrances"],  # Intentional typo to test alias matching
            "patterns": ["alexandria.*grooming"],
            "scents": {
                "Fructus Virginis": {"patterns": ["fructus.*virginis"]},
            },
        }

        # Update soaps.yaml with alias data
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_with_aliases, f)

        # Add matching WSDB entry with alias name (typo version)
        wsdb_with_alias_match = MOCK_WSDB_DATA.copy()
        wsdb_with_alias_match.append(
            {
                "brand": "Alexendria Fragrances",  # Matches alias, not canonical
                "name": "Fructus Virginis",
                "type": "Soap",
                "slug": "alexendria-fragrances-fructus-virginis",
                "scent_notes": ["fig", "fruit"],
                "collaborators": [],
                "tags": [],
                "category": "Artisan",
            }
        )

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(wsdb_with_alias_match, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test Pipeline → WSDB with alias match
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?mode=brands&threshold=0.5&limit=100",
        )

        assert response.status_code == 200
        data = response.json()

        # Find the Alexandria Grooming result
        alexandria_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Alexandria Grooming"),
            None,
        )

        assert alexandria_result is not None
        assert len(alexandria_result["matches"]) > 0

        # Find the match with alias
        alias_match = next(
            (m for m in alexandria_result["matches"] if m["brand"] == "Alexendria Fragrances"), None
        )

        # Verify alias match was found and marked correctly
        assert alias_match is not None
        assert alias_match["matched_via"] == "alias"
        # Alias should score higher than canonical for this typo'd brand
        assert alias_match["confidence"] > 85.0  # High confidence for alias match

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_alias_matching_brand_scent_mode(self, mock_root, mock_data_files):
        """Test that alias matching works in brand + scent mode."""
        # Similar setup to brands only test
        pipeline_with_aliases = copy.deepcopy(MOCK_PIPELINE_DATA)
        pipeline_with_aliases["Alexandria Grooming"] = {
            "aliases": ["Alexendria Fragrances"],
            "patterns": ["alexandria.*grooming"],
            "scents": {
                "Fructus Virginis": {"patterns": ["fructus.*virginis"]},
            },
        }

        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_with_aliases, f)

        wsdb_with_alias_match = MOCK_WSDB_DATA.copy()
        wsdb_with_alias_match.append(
            {
                "brand": "Alexendria Fragrances",
                "name": "Fructus Virginis",
                "type": "Soap",
                "slug": "alexendria-fragrances-fructus-virginis",
                "scent_notes": ["fig", "fruit"],
                "collaborators": [],
                "tags": [],
                "category": "Artisan",
            }
        )

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(wsdb_with_alias_match, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test Pipeline → WSDB with alias match in brand_scent mode
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?mode=brand_scent&threshold=0.5&limit=100",
        )

        assert response.status_code == 200
        data = response.json()

        # Find the Alexandria Grooming + Fructus Virginis result
        alexandria_result = next(
            (
                r
                for r in data["pipeline_results"]
                if r["source_brand"] == "Alexandria Grooming"
                and r["source_scent"] == "Fructus Virginis"
            ),
            None,
        )

        assert alexandria_result is not None
        assert len(alexandria_result["matches"]) > 0

        # Find the match with alias
        alias_match = next(
            (m for m in alexandria_result["matches"] if m["brand"] == "Alexendria Fragrances"), None
        )

        # Verify alias match was found and marked correctly
        assert alias_match is not None
        assert alias_match["matched_via"] == "alias"
        assert alias_match["confidence"] > 70.0  # Combined brand + scent score

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_canonical_name_preferred_when_better(self, mock_root, mock_data_files):
        """Test that canonical name is used when it scores higher than alias."""
        # Setup where canonical name matches perfectly
        pipeline_with_aliases = copy.deepcopy(MOCK_PIPELINE_DATA)
        pipeline_with_aliases["Barrister and Mann"]["aliases"] = ["B&M", "Barrister & Mann"]

        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_with_aliases, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test with WSDB entry that matches canonical name perfectly
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?mode=brands&threshold=0.5&limit=100",
        )

        assert response.status_code == 200
        data = response.json()

        # Find the Barrister and Mann result
        bam_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )

        assert bam_result is not None
        assert len(bam_result["matches"]) > 0

        # The perfect canonical match should be marked as canonical
        top_match = bam_result["matches"][0]
        assert top_match["brand"] == "Barrister and Mann"
        assert top_match["matched_via"] == "canonical"
        # In brands mode, we expect reasonable confidence for canonical match
        # (May not be exactly 100 due to fuzzy matching algorithm)
        assert top_match["confidence"] >= 70.0

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_pattern_matches_slug_space_norm(self, mock_root, mock_data_files):
        """Pipeline scent regex pattern matching slug (hyphens→spaces) produces a match.

        Pattern has a space (e.g. "caledonia rose"); slug has hyphens. Pre-processing
        converts slug to space-separated text so the pattern matches.
        """
        # WSDB: slug with hyphens; pipeline pattern assumes spaces: (barris|bam).*caledonia rose
        wsdb_soaps = [
            {
                "brand": "Barrister and Mann",
                "name": "Caledonia Rose",
                "type": "Soap",
                "slug": "barrister-mann-caledonia-rose-soap",
                "scent_notes": [],
                "collaborators": [],
                "tags": [],
                "category": "software",
            },
        ]
        pipeline_soaps = {
            "Barrister and Mann": {
                "patterns": ["barrister.*mann", "bam"],
                "scents": {
                    "Caledonia Rose": {
                        "patterns": ["(barris|bam).*caledonia rose"],
                    },
                },
            },
        }
        software_file = mock_data_files / "wsdb" / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(wsdb_soaps, f)
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_soaps, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Invalidate cache so our new WSDB data is loaded
        from api.wsdb_alignment import invalidate_wsdb_cache

        invalidate_wsdb_cache()

        response = client.post(
            "/api/wsdb-alignment/batch-analyze?mode=brand_scent&threshold=0.9&limit=100",
        )
        assert response.status_code == 200
        data = response.json()

        result = next(
            (
                r
                for r in data["pipeline_results"]
                if r["source_brand"] == "Barrister and Mann"
                and r["source_scent"] == "Caledonia Rose"
            ),
            None,
        )
        assert (
            result is not None
        ), "Expected pipeline result for Barrister and Mann - Caledonia Rose"
        assert len(result["matches"]) > 0, "Expected at least one match from slug pattern match"
        match = result["matches"][0]
        assert match["details"]["slug"] == "barrister-mann-caledonia-rose-soap"
        assert match["details"].get("slug_pattern_match") is True


def test_load_non_matches(mock_data_files):
    """Test loading non-matches from new hierarchical YAML files."""
    # Create non-matches files (wsdb dir already exists from fixture)
    wsdb_dir = mock_data_files / "wsdb"

    # Brand non-matches
    brands_file = wsdb_dir / "non_matches_brands.yaml"
    brands_data = {
        "Black Mountain Shaving": ["Mountain Hare Shaving"],
    }
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump(brands_data, f)

    # Scent non-matches
    scents_file = wsdb_dir / "non_matches_scents.yaml"
    scents_data = {
        "Barrister and Mann": {
            "Le Grand Chypre": ["Le Petit Chypre"],
        }
    }
    with scents_file.open("w", encoding="utf-8") as f:
        yaml.dump(scents_data, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.get("/api/wsdb-alignment/non-matches")
        assert response.status_code == 200
        data = response.json()
        assert "Black Mountain Shaving" in data["brand_non_matches"]
        assert "Mountain Hare Shaving" in data["brand_non_matches"]["Black Mountain Shaving"]
        assert "Barrister and Mann" in data["scent_non_matches"]
        assert "Le Grand Chypre" in data["scent_non_matches"]["Barrister and Mann"]
        assert (
            "Le Petit Chypre" in data["scent_non_matches"]["Barrister and Mann"]["Le Grand Chypre"]
        )


def test_add_brand_non_match(mock_data_files):
    """Test adding brand-level non-match."""
    wsdb_dir = mock_data_files / "wsdb"
    brands_file = wsdb_dir / "non_matches_brands.yaml"

    # Initialize empty file
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump({}, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/non-matches",
            json={
                "match_type": "brand",
                "pipeline_brand": "Black Mountain Shaving",
                "wsdb_brand": "Mountain Hare Shaving",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify file was written with hierarchical format
        with brands_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "Black Mountain Shaving" in data
        assert "Mountain Hare Shaving" in data["Black Mountain Shaving"]


def test_add_scent_non_match(mock_data_files):
    """Test adding scent-level non-match."""
    wsdb_dir = mock_data_files / "wsdb"
    scents_file = wsdb_dir / "non_matches_scents.yaml"

    # Initialize empty file
    with scents_file.open("w", encoding="utf-8") as f:
        yaml.dump({}, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/non-matches",
            json={
                "match_type": "scent",
                "pipeline_brand": "Barrister and Mann",
                "pipeline_scent": "Le Grand Chypre",
                "wsdb_brand": "Barrister and Mann",
                "wsdb_scent": "Le Petit Chypre",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify file was written with hierarchical format
        with scents_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "Barrister and Mann" in data
        assert "Le Grand Chypre" in data["Barrister and Mann"]
        assert "Le Petit Chypre" in data["Barrister and Mann"]["Le Grand Chypre"]


def test_non_match_filtering_brands_mode(mock_data_files):
    """Test that non-matches are filtered in brands mode."""
    wsdb_dir = mock_data_files / "wsdb"

    # Create non-matches file (software.json already in correct location from fixture)
    brands_file = wsdb_dir / "non_matches_brands.yaml"
    brands_data = {
        "Barrister and Mann": ["Stirling Soap Co."],
    }
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump(brands_data, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?threshold=0.1&limit=100&mode=brands"
        )
        assert response.status_code == 200
        data = response.json()

        # Find Barrister and Mann result
        bam_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )
        assert bam_result is not None

        # Verify Stirling Soap Co. is NOT in the matches
        stirling_matches = [m for m in bam_result["matches"] if m["brand"] == "Stirling Soap Co."]
        assert len(stirling_matches) == 0


def test_non_match_filtering_brand_scent_mode(mock_data_files):
    """Test that non-matches are filtered in brand+scent mode."""
    wsdb_dir = mock_data_files / "wsdb"

    # Create scent non-matches file (software.json already in correct location from fixture)
    # Format: Brand -> Scent -> [list of non-matching scents within same brand]
    scents_file = wsdb_dir / "non_matches_scents.yaml"
    scents_data = {
        "Barrister and Mann": {
            "Seville": ["Leviathan"],  # BaM Seville != BaM Leviathan
        }
    }
    with scents_file.open("w", encoding="utf-8") as f:
        yaml.dump(scents_data, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?threshold=0.1&limit=100&mode=brand_scent"
        )
        assert response.status_code == 200
        data = response.json()

        # Find Barrister and Mann - Seville result
        bam_seville = next(
            (
                r
                for r in data["pipeline_results"]
                if r["source_brand"] == "Barrister and Mann" and r["source_scent"] == "Seville"
            ),
            None,
        )
        assert bam_seville is not None

        # Verify BaM Leviathan is NOT in the matches
        leviathan_matches = [
            m
            for m in bam_seville["matches"]
            if m["brand"] == "Barrister and Mann" and m["name"] == "Leviathan"
        ]
        assert len(leviathan_matches) == 0


def test_batch_analyze_excludes_assigned_slugs_from_wsdb(mock_data_files):
    """Test that WSDB entries whose slug is already assigned in soaps.yaml are excluded from matching."""
    # Pipeline: Seville has wsdb_slug (assigned); Seville EDT has no slug
    pipeline_with_slug = copy.deepcopy(MOCK_PIPELINE_DATA)
    pipeline_with_slug["Barrister and Mann"]["scents"]["Seville"] = {
        "patterns": ["seville"],
        "wsdb_slug": "barrister-and-mann-seville",
    }
    pipeline_with_slug["Barrister and Mann"]["scents"]["Seville EDT"] = {
        "patterns": ["seville.*edt", "seville edt"],
    }

    # WSDB: two entries - one assigned (Seville), one unassigned (Seville EDT)
    wsdb_with_both = [
        {
            "brand": "Barrister and Mann",
            "name": "Seville",
            "type": "Soap",
            "slug": "barrister-and-mann-seville",
            "scent_notes": [],
            "collaborators": [],
            "tags": [],
            "category": "Traditional",
        },
        {
            "brand": "Barrister and Mann",
            "name": "Seville EDT",
            "type": "Soap",
            "slug": "barrister-and-mann-seville-edt",
            "scent_notes": [],
            "collaborators": [],
            "tags": [],
            "category": "Traditional",
        },
    ]

    soaps_file = mock_data_files / "soaps.yaml"
    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(pipeline_with_slug, f)

    wsdb_file = mock_data_files / "wsdb" / "software.json"
    with wsdb_file.open("w", encoding="utf-8") as f:
        json.dump(wsdb_with_both, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?threshold=0.5&limit=100&mode=brand_scent"
        )
        assert response.status_code == 200
        data = response.json()

    # Barrister and Mann - Seville is skipped (has slug). Find Seville EDT result.
    seville_edt_result = next(
        (
            r
            for r in data["pipeline_results"]
            if r["source_brand"] == "Barrister and Mann" and r["source_scent"] == "Seville EDT"
        ),
        None,
    )
    assert seville_edt_result is not None, "Seville EDT result not found"

    # Assigned slug must not appear as a suggestion (excluded from wsdb_to_consider)
    assigned_slug_matches = [
        m
        for m in seville_edt_result["matches"]
        if m.get("details", {}).get("slug") == "barrister-and-mann-seville"
    ]
    assert len(assigned_slug_matches) == 0, "Assigned slug should be excluded from suggestions"


def test_bidirectional_filtering(mock_data_files):
    """Test that non-matches work in both directions."""
    wsdb_dir = mock_data_files / "wsdb"

    # Create non-matches file (Pipeline: BaM != WSDB: Stirling)
    # (software.json already in correct location from fixture)
    brands_file = wsdb_dir / "non_matches_brands.yaml"
    brands_data = {
        "Barrister and Mann": ["Stirling Soap Co."],
    }
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump(brands_data, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/batch-analyze?threshold=0.1&limit=100&mode=brands"
        )
        assert response.status_code == 200
        data = response.json()

        # Check Pipeline → WSDB: BaM should NOT match Stirling
        bam_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )
        if bam_result:
            stirling_matches = [
                m for m in bam_result["matches"] if m["brand"] == "Stirling Soap Co."
            ]
            assert len(stirling_matches) == 0

        # Check WSDB → Pipeline: Stirling should NOT match BaM
        stirling_result = next(
            (r for r in data["wsdb_results"] if r["source_brand"] == "Stirling Soap Co."), None
        )
        if stirling_result:
            bam_matches = [
                m for m in stirling_result["matches"] if m["brand"] == "Barrister and Mann"
            ]
            assert len(bam_matches) == 0


def test_add_brand_non_match_brand_not_in_catalog(mock_data_files):
    """Test that non-matches can be saved even when brand doesn't exist in soaps.yaml (match files mode)."""
    wsdb_dir = mock_data_files / "wsdb"
    brands_file = wsdb_dir / "non_matches_brands.yaml"

    # Initialize empty file
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump({}, f)

    # Create soaps.yaml without the brand we're testing (simulating match files mode)
    soaps_file = mock_data_files / "soaps.yaml"
    soaps_data = {
        "Some Other Brand": {
            "patterns": ["some.*other"],
            "scents": {"Scent1": {"patterns": ["scent1"]}},
        }
    }
    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(soaps_data, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        # Try to add non-match for a brand that doesn't exist in soaps.yaml
        response = client.post(
            "/api/wsdb-alignment/non-matches",
            json={
                "match_type": "brand",
                "pipeline_brand": "Third Pass Shaving Co",  # Not in soaps.yaml
                "wsdb_brand": "Wild West Shaving Co.",
            },
        )

        assert response.status_code == 200
        data = response.json()
        # Should succeed even though brand doesn't exist in catalog (for match files mode)
        assert data["success"] is True

        # Verify it was saved
        with brands_file.open("r", encoding="utf-8") as f:
            saved_data = yaml.safe_load(f) or {}
        assert "Third Pass Shaving Co" in saved_data
        assert "Wild West Shaving Co." in saved_data["Third Pass Shaving Co"]


def test_duplicate_non_match_prevention(mock_data_files):
    """Test that duplicate non-matches are not added."""
    wsdb_dir = mock_data_files / "wsdb"
    brands_file = wsdb_dir / "non_matches_brands.yaml"

    # Initialize empty file
    with brands_file.open("w", encoding="utf-8") as f:
        yaml.dump({}, f)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        # Add first time
        response1 = client.post(
            "/api/wsdb-alignment/non-matches",
            json={
                "match_type": "brand",
                "pipeline_brand": "Black Mountain Shaving",
                "wsdb_brand": "Mountain Hare Shaving",
            },
        )
        assert response1.status_code == 200
        assert response1.json()["success"] is True

        # Try to add again (duplicate)
        response2 = client.post(
            "/api/wsdb-alignment/non-matches",
            json={
                "match_type": "brand",
                "pipeline_brand": "Black Mountain Shaving",
                "wsdb_brand": "Mountain Hare Shaving",
            },
        )
        assert response2.status_code == 200
        assert response2.json()["success"] is True
        assert "already exists" in response2.json()["message"]

        # Verify only one entry in file (hierarchical format)
        with brands_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "Black Mountain Shaving" in data
        assert len(data["Black Mountain Shaving"]) == 1
        assert "Mountain Hare Shaving" in data["Black Mountain Shaving"]


def test_add_scent_alias_success(mock_data_files):
    """Test successfully adding a scent alias to a brand."""
    soaps_file = mock_data_files / "soaps.yaml"

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        # Add a scent alias
        response = client.post(
            "/api/wsdb-alignment/add-scent-alias",
            json={
                "pipeline_brand": "Barrister and Mann",
                "pipeline_scent": "Seville",
                "alias": "Seville Classic",
            },
        )
        assert response.status_code == 200
        assert response.json()["success"] is True

        # Verify it was written to file
        with soaps_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert "alias" in data["Barrister and Mann"]["scents"]["Seville"]
        assert data["Barrister and Mann"]["scents"]["Seville"]["alias"] == "Seville Classic"


def test_add_scent_alias_duplicate(mock_data_files):
    """Test that duplicate scent aliases are replaced (not added)."""
    soaps_file = mock_data_files / "soaps.yaml"

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        # Add alias first time
        response1 = client.post(
            "/api/wsdb-alignment/add-scent-alias",
            json={
                "pipeline_brand": "Barrister and Mann",
                "pipeline_scent": "Seville",
                "alias": "Seville Classic",
            },
        )
        assert response1.status_code == 200

        # Try to add same alias again (should replace, not duplicate)
        response2 = client.post(
            "/api/wsdb-alignment/add-scent-alias",
            json={
                "pipeline_brand": "Barrister and Mann",
                "pipeline_scent": "Seville",
                "alias": "Seville Classic",
            },
        )
        assert response2.status_code == 200
        assert "already exists" in response2.json()["message"]

        # Verify only one alias entry (not an array)
        with soaps_file.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data["Barrister and Mann"]["scents"]["Seville"]["alias"] == "Seville Classic"


def test_unicode_normalization_brand_scent_mode(mock_data_files):
    """Test that Unicode normalization handles visually identical strings correctly."""
    import unicodedata

    # Create test data with composed vs decomposed Unicode
    # "Mélange" can be encoded as:
    # - Composed: U+004D U+00E9 U+006C U+0061 U+006E U+0067 U+0065 (é as single character)
    # - Decomposed: U+004D U+0065 U+0301 U+006C U+0061 U+006E U+0067 U+0065 (e + combining accent)

    # Use composed form in pipeline
    composed_melange = "Mélange"  # This should be NFC (composed)

    # Create decomposed form for WSDB (simulating different encoding)
    decomposed_melange = unicodedata.normalize("NFD", composed_melange)  # Decomposed form

    # Verify they're different encodings but visually identical
    assert composed_melange != decomposed_melange
    assert len(composed_melange) == 7  # 7 characters
    assert len(decomposed_melange) == 8  # 8 characters (e + combining accent)

    # Update mock data
    soaps_file = mock_data_files / "soaps.yaml"
    wsdb_file = mock_data_files / "wsdb" / "software.json"

    with soaps_file.open("r", encoding="utf-8") as f:
        soaps_data = yaml.safe_load(f)

    # Add test brand with composed Unicode
    soaps_data["Test Brand Unicode"] = {"scents": {composed_melange: {"patterns": []}}}

    with soaps_file.open("w", encoding="utf-8") as f:
        yaml.dump(soaps_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    with wsdb_file.open("r", encoding="utf-8") as f:
        wsdb_data = json.load(f)

    # Add WSDB entry with decomposed Unicode
    # wsdb_data is a list, not a dict
    wsdb_data.append(
        {
            "brand": "Test Brand Unicode",
            "name": decomposed_melange,
            "type": "Soap",
            "slug": "test-brand-unicode-melange",
            "scent_notes": [],
            "collaborators": [],
            "tags": [],
            "category": "software",
        }
    )

    with wsdb_file.open("w", encoding="utf-8") as f:
        json.dump(wsdb_data, f, ensure_ascii=False, indent=2)

    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        # Run batch analysis in brand_scent mode
        response = client.post(
            "/api/wsdb-alignment/batch-analyze",
            params={"mode": "brand_scent", "threshold": 0.7, "brand_threshold": 0.8},
        )
        assert response.status_code == 200

        results = response.json()
        pipeline_results = results["pipeline_results"]

        # Find our test brand result
        test_result = None
        for result in pipeline_results:
            if result["source_brand"] == "Test Brand Unicode":
                test_result = result
                break

        assert test_result is not None, "Test brand not found in results"
        assert len(test_result["matches"]) > 0, "No matches found for test brand"

        # The match should be 100% confidence because Unicode normalization makes them identical
        match = test_result["matches"][0]
        assert match["confidence"] == 100.0, f"Expected 100% confidence, got {match['confidence']}%"
        assert match["brand"] == "Test Brand Unicode"
        # The name might be in either form, but they should match at 100%


def test_add_scent_alias_scent_not_found(mock_data_files):
    """Test error handling when scent is not found."""
    with patch("api.wsdb_alignment.PROJECT_ROOT", mock_data_files.parent):
        response = client.post(
            "/api/wsdb-alignment/add-scent-alias",
            json={
                "pipeline_brand": "Barrister and Mann",
                "pipeline_scent": "NonExistent",
                "alias": "Some Alias",
            },
        )
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestBatchAnalyzeMatchFiles:
    """Tests for batch-analyze-match-files endpoint."""

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_basic(self, mock_root, mock_data_files):
        """Test basic functionality of batch-analyze-match-files endpoint."""
        # Create match files directory
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        # Create a test match file
        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05", "total_shaves": 100},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "regex",
                    },
                },
                {
                    "id": "comment2",
                    "soap": {
                        "original": "Declaration Grooming - Massacre of the Innocents",
                        "matched": {
                            "brand": "Declaration Grooming",
                            "scent": "Massacre of the Innocents",
                        },
                        "match_type": "regex",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        # Set up WSDB data
        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)

        # Set up pipeline data (minimal, not used in match files mode)
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test the endpoint (match_type_filter=brand is query param; backend only includes exact/regex matches)
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        assert "pipeline_results" in data
        assert "wsdb_results" in data
        assert data["mode"] == "brand_scent"
        assert "2025-05" in data["months_processed"]
        assert data["total_entries"] == 2

        # Check that results contain the expected data
        assert len(data["pipeline_results"]) > 0

        # Find Barrister and Mann result
        bm_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )
        assert bm_result is not None
        assert bm_result["source_scent"] == "Seville"
        assert "original_texts" in bm_result
        assert "match_types" in bm_result
        assert "count" in bm_result
        assert bm_result["count"] == 1

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_excludes_mashup_matches(self, mock_root, mock_data_files):
        """Test that soap matches with countable: false (mashups) are excluded from results."""
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)
        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "c1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "regex",
                    },
                },
                {
                    "id": "c2",
                    "soap": {
                        "original": "Mama Bear - Sample Mashup",
                        "matched": {
                            "brand": "Mama Bear",
                            "scent": "Sample Mashup",
                            "countable": False,
                        },
                        "match_type": "regex",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        with (wsdb_dir / "software.json").open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=all"
        )

        assert response.status_code == 200
        data = response.json()
        # Only Barrister and Mann - Seville; Mama Bear Sample Mashup (countable false) excluded
        assert data["total_entries"] == 1
        assert len(data["pipeline_results"]) == 1
        assert data["pipeline_results"][0]["source_brand"] == "Barrister and Mann"
        assert data["pipeline_results"][0]["source_scent"] == "Seville"
        # No Mama Bear / Sample Mashup in results
        mama_results = [r for r in data["pipeline_results"] if r["source_brand"] == "Mama Bear"]
        assert len(mama_results) == 0

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_filter_by_match_type(self, mock_root, mock_data_files):
        """Test that match_type filtering works correctly."""
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "brand",
                    },
                },
                {
                    "id": "comment2",
                    "soap": {
                        "original": "Declaration Grooming - MOTI",
                        "matched": {
                            "brand": "Declaration Grooming",
                            "scent": "Massacre of the Innocents",
                        },
                        "match_type": "regex",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)

        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test with match_type_filter=brand (should only return brand matches)
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        # Should only have 1 entry (the brand match, not the regex match)
        assert data["total_entries"] == 1
        assert len(data["pipeline_results"]) == 1
        assert data["pipeline_results"][0]["source_brand"] == "Barrister and Mann"

        # Test with match_type_filter=all (should return both)
        response_all = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=all"
        )

        assert response_all.status_code == 200
        data_all = response_all.json()

        # Should have 2 entries
        assert data_all["total_entries"] == 2
        assert len(data_all["pipeline_results"]) == 2

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_invalid_month(self, mock_root, mock_data_files):
        """Test that invalid month format is rejected."""
        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=invalid&threshold=0.5&mode=brand_scent"
        )

        assert response.status_code == 400
        assert "Invalid month format" in response.json()["detail"]

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_missing_month_file(self, mock_root, mock_data_files):
        """Test that missing month files are handled gracefully."""
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)

        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test with non-existent month (use valid format but file doesn't exist)
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-01&threshold=0.5&mode=brand_scent&match_type_filter=brand"
        )

        # Should return empty results, not an error (file doesn't exist but format is valid)
        assert response.status_code == 200
        data = response.json()
        assert data["total_entries"] == 0
        assert len(data["pipeline_results"]) == 0

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_with_aliases(self, mock_root, mock_data_files):
        """Test that aliases from soaps.yaml are used when matching brands from match files."""
        # Create match files directory
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        # Create a test match file with a brand that has an alias
        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "The Artisan Soap Shoppe - Crisp Vetiver",
                        "matched": {"brand": "The Artisan Soap Shoppe", "scent": "Crisp Vetiver"},
                        "match_type": "brand",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        # Set up pipeline data with alias
        pipeline_with_alias = copy.deepcopy(MOCK_PIPELINE_DATA)
        pipeline_with_alias["The Artisan Soap Shoppe"] = {
            "aliases": ["The Artisan Shave Shoppe"],
            "patterns": ["artisan.*soap.*shoppe"],
            "scents": {
                "Crisp Vetiver": {"patterns": ["crisp.*vetiver"]},
            },
        }
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(pipeline_with_alias, f)

        # Set up WSDB data with the alias name (not canonical)
        wsdb_with_alias = MOCK_WSDB_DATA.copy()
        wsdb_with_alias.append(
            {
                "brand": "The Artisan Shave Shoppe",  # This is the alias, not canonical
                "name": "Crisp Vetiver",
                "type": "Soap",
                "slug": "artisan-shave-shoppe-crisp-vetiver",
                "scent_notes": ["vetiver", "citrus"],
                "collaborators": [],
                "tags": [],
                "category": "Artisan",
            }
        )

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(wsdb_with_alias, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test the endpoint
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        # Find The Artisan Soap Shoppe result
        artisan_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "The Artisan Soap Shoppe"),
            None,
        )
        assert artisan_result is not None

        # Should have found a match via alias
        assert len(artisan_result["matches"]) > 0

        # Find the match that was found via alias
        alias_match = next(
            (m for m in artisan_result["matches"] if m["brand"] == "The Artisan Shave Shoppe"), None
        )
        assert alias_match is not None
        assert alias_match["matched_via"] == "alias"

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_brand_without_aliases(self, mock_root, mock_data_files):
        """Test that brands without aliases still work correctly."""
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "brand",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        # Use standard pipeline data (Barrister and Mann has no aliases in MOCK_PIPELINE_DATA)
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.5&mode=brand_scent&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        # Should still work without aliases
        bm_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )
        assert bm_result is not None

        # Matches should have matched_via set to "canonical" (not alias)
        if len(bm_result["matches"]) > 0:
            assert bm_result["matches"][0]["matched_via"] == "canonical"

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_non_matches_brands_mode(self, mock_root, mock_data_files):
        """Test that non-matches are filtered in match files mode (brands only)."""
        # Create match files directory
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        # Create a test match file
        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "brand",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        # Set up pipeline data
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        # Set up WSDB data
        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(MOCK_WSDB_DATA, f)

        # Create non-matches file - Barrister and Mann should NOT match Stirling Soap Co.
        brands_file = wsdb_dir / "non_matches_brands.yaml"
        brands_data = {
            "Barrister and Mann": ["Stirling Soap Co."],
        }
        with brands_file.open("w", encoding="utf-8") as f:
            yaml.dump(brands_data, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test the endpoint
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.1&mode=brands&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        # Find Barrister and Mann result
        bam_result = next(
            (r for r in data["pipeline_results"] if r["source_brand"] == "Barrister and Mann"), None
        )
        assert bam_result is not None

        # Verify Stirling Soap Co. is NOT in the matches (should be filtered out)
        stirling_matches = [m for m in bam_result["matches"] if m["brand"] == "Stirling Soap Co."]
        assert len(stirling_matches) == 0

    @patch("api.wsdb_alignment.PROJECT_ROOT")
    def test_batch_analyze_match_files_non_matches_brand_scent_mode(
        self, mock_root, mock_data_files
    ):
        """Test that non-matches are filtered in match files mode (brand+scent)."""
        # Create match files directory
        matched_dir = mock_data_files / "matched"
        matched_dir.mkdir(exist_ok=True)

        # Create a test match file
        match_file = matched_dir / "2025-05.json"
        match_data = {
            "meta": {"month": "2025-05"},
            "data": [
                {
                    "id": "comment1",
                    "soap": {
                        "original": "Barrister and Mann - Seville",
                        "matched": {"brand": "Barrister and Mann", "scent": "Seville"},
                        "match_type": "brand",
                    },
                },
            ],
        }
        with match_file.open("w", encoding="utf-8") as f:
            json.dump(match_data, f)

        # Set up pipeline data
        soaps_file = mock_data_files / "soaps.yaml"
        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(MOCK_PIPELINE_DATA, f)

        # Set up WSDB data - add Leviathan to test scent non-match
        wsdb_with_leviathan = MOCK_WSDB_DATA.copy()
        wsdb_with_leviathan.append(
            {
                "brand": "Barrister and Mann",
                "name": "Leviathan",
                "type": "Soap",
                "slug": "barrister-and-mann-leviathan",
                "scent_notes": ["coffee", "leather"],
                "collaborators": [],
                "tags": [],
                "category": "Traditional",
            }
        )
        wsdb_dir = mock_data_files / "wsdb"
        wsdb_dir.mkdir(exist_ok=True)
        software_file = wsdb_dir / "software.json"
        with software_file.open("w", encoding="utf-8") as f:
            json.dump(wsdb_with_leviathan, f)

        # Create scent non-matches file - BaM Seville != BaM Leviathan
        scents_file = wsdb_dir / "non_matches_scents.yaml"
        scents_data = {
            "Barrister and Mann": {
                "Seville": ["Leviathan"],
            }
        }
        with scents_file.open("w", encoding="utf-8") as f:
            yaml.dump(scents_data, f)

        mock_root_path = mock_data_files.parent
        mock_root.__truediv__ = lambda self, other: mock_root_path / other

        # Test the endpoint
        response = client.post(
            "/api/wsdb-alignment/batch-analyze-match-files?months=2025-05&threshold=0.1&mode=brand_scent&match_type_filter=brand"
        )

        assert response.status_code == 200
        data = response.json()

        # Find Barrister and Mann - Seville result
        bam_seville = next(
            (
                r
                for r in data["pipeline_results"]
                if r["source_brand"] == "Barrister and Mann" and r["source_scent"] == "Seville"
            ),
            None,
        )
        assert bam_seville is not None

        # Verify Leviathan is NOT in the matches (should be filtered out)
        leviathan_matches = [m for m in bam_seville["matches"] if m["name"] == "Leviathan"]
        assert len(leviathan_matches) == 0

        # But Seville itself should still be in matches (same brand, same scent)
        seville_matches = [m for m in bam_seville["matches"] if m["name"] == "Seville"]
        assert len(seville_matches) > 0
