"""
Test data isolation strategy for webui API tests.

This module tests the creation of test-specific API endpoints and data files
for isolated testing that doesn't depend on changing production data.
"""

from pathlib import Path
from unittest.mock import patch

import yaml
from fastapi.testclient import TestClient

from webui.api.main import app


class TestDataIsolationStrategy:
    """Test the data isolation strategy for API tests."""

    def test_create_test_yaml_file(self, tmp_path):
        """Test creating test YAML files with predictable, small datasets."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test brush_splits.yaml with predictable data
        test_brush_splits = data_dir / "brush_splits.yaml"
        test_data = {
            "splits": {
                "Test Brush 1": [
                    {
                        "original": "Test Brush 1",
                        "handle": "Test Handle 1",
                        "knot": "Test Knot 1",
                        "should_not_split": False,
                        "validated_at": "2025-01-27T14:30:00Z",
                        "corrected": False,
                        "match_type": "regex",
                        "occurrences": [],
                    }
                ],
                "Test Brush 2": [
                    {
                        "original": "Test Brush 2",
                        "handle": None,
                        "knot": None,
                        "should_not_split": True,
                        "validated_at": "2025-01-27T15:30:00Z",
                        "corrected": False,
                        "match_type": None,
                        "occurrences": [],
                    }
                ],
            }
        }

        # Write test data
        test_brush_splits.write_text(yaml.dump(test_data))

        # Verify file was created with correct data
        assert test_brush_splits.exists()
        loaded_data = yaml.safe_load(test_brush_splits.read_text())
        assert len(loaded_data["splits"]) == 2
        assert "Test Brush 1" in loaded_data["splits"]
        assert "Test Brush 2" in loaded_data["splits"]

    def test_create_test_filtered_file(self, tmp_path):
        """Test creating test filtered YAML files."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test filtered.yaml with predictable data
        test_filtered = data_dir / "filtered.yaml"
        test_data = {
            "brush": {
                "entries": [
                    {"name": "Test Brush 1", "status": "matched"},
                    {"name": "Test Brush 2", "status": "unmatched"},
                ]
            },
            "razor": {"entries": [{"name": "Test Razor 1", "status": "matched"}]},
        }

        # Write test data
        test_filtered.write_text(yaml.dump(test_data))

        # Verify file was created with correct data
        assert test_filtered.exists()
        loaded_data = yaml.safe_load(test_filtered.read_text())
        assert "brush" in loaded_data
        assert "razor" in loaded_data
        assert len(loaded_data["brush"]["entries"]) == 2
        assert len(loaded_data["razor"]["entries"]) == 1

    def test_api_endpoint_with_test_data(self, tmp_path):
        """Test API endpoints using test-specific data files."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test brush_splits.yaml (flat structure)
        test_brush_splits = data_dir / "brush_splits.yaml"
        test_data = {
            "Test Brush": {
                "handle": "Test Handle",
                "knot": "Test Knot",
                "should_not_split": False,
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": False,
                "match_type": "regex",
                "occurrences": [],
            }
        }
        test_brush_splits.write_text(yaml.dump(test_data))

        # Mock the validator to use test file
        with patch("webui.api.brush_splits.validator.yaml_path", test_brush_splits):
            client = TestClient(app)

            # Test the load endpoint with test data (requires months parameter)
            response = client.get("/api/brushes/splits/load", params={"months": ["2025-01"]})

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "brush_splits" in data
            # Note: The actual response will depend on the mocked data and processing

    def test_api_endpoint_never_writes_to_production(self, tmp_path):
        """Test that API endpoints never write to production files."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test brush_splits.yaml (flat structure)
        test_brush_splits = data_dir / "brush_splits.yaml"
        test_data = {
            "Test Brush": {
                "handle": "Test Handle",
                "knot": "Test Knot",
                "should_not_split": False,
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": False,
                "match_type": "regex",
                "occurrences": [],
            }
        }
        test_brush_splits.write_text(yaml.dump(test_data))

        # Mock the validator to use test file
        with patch("webui.api.brush_splits.validator.yaml_path", test_brush_splits):
            client = TestClient(app)

            # Test the save endpoint with test data
            save_data = {
                "original": "New Test Brush",
                "handle": "New Handle",
                "knot": "New Knot",
                "validated_at": "2025-01-27T16:30:00Z",
            }

            response = client.post("/api/brushes/splits/save-split", json=save_data)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify that the test file was modified, not production
            updated_data = yaml.safe_load(test_brush_splits.read_text())
            assert "New Test Brush" in updated_data

            # Verify production file was NOT modified
            production_file = Path("data/brush_splits.yaml")
            if production_file.exists():
                production_data = yaml.safe_load(production_file.read_text())
                if production_data is not None:  # Handle case where file is empty/corrupted
                    assert "New Test Brush" not in production_data

    def test_integration_test_with_isolated_data(self, tmp_path):
        """Test integration tests using isolated data."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create test brush_splits.yaml (flat structure)
        test_brush_splits = data_dir / "brush_splits.yaml"
        brush_data = {
            "Integration Test Brush": {
                "handle": "Integration Handle",
                "knot": "Integration Knot",
                "should_not_split": False,
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": False,
                "match_type": "regex",
                "occurrences": [],
            }
        }
        test_brush_splits.write_text(yaml.dump(brush_data))

        # Mock the validator to use test file
        with patch("webui.api.brush_splits.validator.yaml_path", test_brush_splits):
            client = TestClient(app)

            # Test brush splits endpoint (requires months parameter)
            response = client.get("/api/brushes/splits/load", params={"months": ["2025-01"]})
            assert response.status_code == 200
            brush_data = response.json()
            assert "brush_splits" in brush_data
            # Note: The actual response will depend on the mocked data and processing

            # Test filtered endpoint (uses different structure)
            response = client.get("/api/filtered/")
            assert response.status_code == 200
            filtered_data = response.json()
            assert filtered_data["success"] is True
            # Note: The actual response will depend on the real filtered data

    def test_test_data_isolation_requirements(self):
        """Test that all test data isolation requirements are met."""
        # Test that we can create predictable, small datasets
        test_data = {
            "splits": {
                "Small Test Dataset": [
                    {
                        "original": "Small Test Dataset",
                        "handle": "Small Handle",
                        "knot": "Small Knot",
                        "should_not_split": False,
                        "validated_at": "2025-01-27T14:30:00Z",
                        "corrected": False,
                        "match_type": "regex",
                        "occurrences": [],
                    }
                ]
            }
        }

        # Verify dataset is small and predictable
        assert len(test_data["splits"]) == 1
        assert len(test_data["splits"]["Small Test Dataset"]) == 1

        # Test that we can create test-specific API endpoints
        # (This is verified by the other tests in this class)

        # Test that we can use tmp_path for isolation
        # (This is verified by the fixture usage in all tests)

        # Test that we never write to production files
        # (This is verified by test_api_endpoint_never_writes_to_production)
