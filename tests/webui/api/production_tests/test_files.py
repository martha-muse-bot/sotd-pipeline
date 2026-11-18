#!/usr/bin/env python3
"""Tests for file system integration endpoints."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from webui.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory with test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        data_dir = Path(temp_dir) / "data" / "matched"
        data_dir.mkdir(parents=True)

        # Create test month files
        test_data_2025_01 = {
            "data": [
                {"razor": {"original": "Test Razor 1", "matched": {"brand": "Test"}}},
                {"razor": {"original": "Test Razor 2", "matched": None}},
            ]
        }

        test_data_2025_02 = {
            "data": [
                {"blade": {"original": "Test Blade", "matched": {"brand": "Test"}}},
            ]
        }

        (data_dir / "2025-01.json").write_text(json.dumps(test_data_2025_01))
        (data_dir / "2025-02.json").write_text(json.dumps(test_data_2025_02))

        yield data_dir


class TestFileSystemIntegration:
    """Test file system integration endpoints."""

    def test_get_available_months_success(self, client, temp_data_dir):
        """Test successful retrieval of available months."""
        with patch("webui.api.files.get_data_directory", return_value=temp_data_dir):
            response = client.get("/api/files/available-months")

            assert response.status_code == 200
            data = response.json()
            assert "months" in data
            assert "total_months" in data
            assert data["total_months"] == 2
            assert "2025-01" in data["months"]
            assert "2025-02" in data["months"]

    def test_get_available_months_empty_directory(self, client):
        """Test handling of empty data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            empty_data_dir = Path(temp_dir) / "data" / "matched"
            empty_data_dir.mkdir(parents=True)

            with patch("webui.api.files.get_data_directory", return_value=empty_data_dir):
                response = client.get("/api/files/available-months")

                assert response.status_code == 200
                data = response.json()
                assert data["months"] == []
                assert data["total_months"] == 0

    def test_get_available_months_nonexistent_directory(self, client):
        """Test handling of nonexistent data directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_dir = Path(temp_dir) / "nonexistent"

            with patch("webui.api.files.get_data_directory", return_value=nonexistent_dir):
                response = client.get("/api/files/available-months")

                assert response.status_code == 200
                data = response.json()
                assert data["months"] == []
                assert data["total_months"] == 0

    def test_get_month_data_success(self, client, temp_data_dir):
        """Test successful retrieval of month data."""
        with patch("webui.api.files.get_data_directory", return_value=temp_data_dir):
            response = client.get("/api/files/2025-01")

            assert response.status_code == 200
            data = response.json()
            assert data["month"] == "2025-01"
            assert data["total_records"] == 2
            assert len(data["data"]) == 2
            assert data["data"][0]["razor"]["original"] == "Test Razor 1"

    def test_get_month_data_not_found(self, client, temp_data_dir):
        """Test handling of nonexistent month."""
        with patch("webui.api.files.get_data_directory", return_value=temp_data_dir):
            response = client.get("/api/files/2025-03")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "2025-03" in data["detail"]

    def test_get_month_data_invalid_json(self, client):
        """Test handling of invalid JSON file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            data_dir = Path(temp_dir) / "data" / "matched"
            data_dir.mkdir(parents=True)

            # Create invalid JSON file
            (data_dir / "2025-01.json").write_text("invalid json content")

            with patch("webui.api.files.get_data_directory", return_value=data_dir):
                response = client.get("/api/files/2025-01")

                assert response.status_code == 500
                data = response.json()
                assert "detail" in data
                assert "Invalid JSON" in data["detail"]

    def test_get_month_summary_success(self, client, temp_data_dir):
        """Test successful retrieval of month summary."""
        with patch("webui.api.files.get_data_directory", return_value=temp_data_dir):
            response = client.get("/api/files/2025-01/summary")

            assert response.status_code == 200
            data = response.json()
            assert data["month"] == "2025-01"
            assert data["total_records"] == 2
            assert "file_size_bytes" in data
            assert "fields_present" in data
            assert "match_stats" in data
            assert data["fields_present"]["razor"] == 2
            assert data["match_stats"]["total_matched"] == 1
            assert data["match_stats"]["total_unmatched"] == 1

    def test_get_month_summary_not_found(self, client, temp_data_dir):
        """Test handling of nonexistent month for summary."""
        with patch("webui.api.files.get_data_directory", return_value=temp_data_dir):
            response = client.get("/api/files/2025-03/summary")

            assert response.status_code == 404
            data = response.json()
            assert "detail" in data
            assert "2025-03" in data["detail"]

    def test_validate_json_file_valid(self, temp_data_dir):
        """Test JSON validation with valid file."""
        from webui.api.files import validate_json_file

        test_file = temp_data_dir / "2025-01.json"
        assert validate_json_file(test_file) is True

    def test_validate_json_file_invalid(self, temp_data_dir):
        """Test JSON validation with invalid file."""
        from webui.api.files import validate_json_file

        # Create invalid JSON file
        invalid_file = temp_data_dir / "invalid.json"
        invalid_file.write_text("invalid json content")

        assert validate_json_file(invalid_file) is False

    def test_get_data_directory(self):
        """Test data directory path resolution."""
        from webui.api.files import get_data_directory

        data_dir = get_data_directory()
        assert isinstance(data_dir, Path)
        assert data_dir.name == "matched"
        assert data_dir.parent.name == "data"
