"""Tests for filtered entries API endpoints."""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from fastapi.testclient import TestClient

from webui.api.filtered import router


@pytest.fixture
def client():
    """Create test client."""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory."""
    temp_dir = tempfile.mkdtemp()
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir()

    # Create test filtered entries file
    filtered_file = data_dir / "intentionally_unmatched.yaml"
    test_data = {
        "razor": {
            "Hot Wheels Play Razor": {
                "added_date": "2025-01-27",
                "comment_ids": [{"file": "2025-01.json", "id": "abc123", "source": "user"}],
            }
        },
        "brush": {},
        "blade": {},
        "soap": {},
    }

    with open(filtered_file, "w", encoding="utf-8") as f:
        yaml.dump(test_data, f)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestGetFilteredEntries:
    """Test GET /api/filtered endpoint."""

    def test_get_filtered_entries_success(self, client, temp_data_dir, monkeypatch):
        """Test successful retrieval of filtered entries."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        response = client.get("/api/filtered/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Filtered entries retrieved successfully" in data["message"]
        assert "razor" in data["data"]
        assert "Hot Wheels Play Razor" in data["data"]["razor"]

    def test_get_filtered_entries_file_not_found(self, client, temp_data_dir, monkeypatch):
        """Test handling when filtered file doesn't exist."""
        # Mock the file path to non-existent file
        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "nonexistent.yaml",
        )

        response = client.get("/api/filtered/")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "razor" in data["data"]
        assert "brush" in data["data"]
        assert "blade" in data["data"]
        assert "soap" in data["data"]


class TestUpdateFilteredEntries:
    """Test POST /api/filtered endpoint."""

    def test_add_filtered_entry_success(self, client, temp_data_dir, monkeypatch):
        """Test successful addition of filtered entry."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "category": "razor",
            "entries": [
                {
                    "name": "Test Razor",
                    "action": "add",
                    "comment_id": "def456",
                    "month": "2025-01",
                    "source": "user",
                }
            ],
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Added 1 entries" in data["message"]
        assert data["added_count"] == 1
        assert data["removed_count"] == 0

    def test_remove_filtered_entry_success(self, client, temp_data_dir, monkeypatch):
        """Test successful removal of filtered entry."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "category": "razor",
            "entries": [
                {
                    "name": "Hot Wheels Play Razor",
                    "action": "remove",
                    "comment_id": "abc123",
                    "month": "2025-01",
                }
            ],
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Removed 1 entries" in data["message"]
        assert data["added_count"] == 0
        assert data["removed_count"] == 1

    def test_bulk_operations(self, client, temp_data_dir, monkeypatch):
        """Test bulk add and remove operations."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "category": "razor",
            "entries": [
                {
                    "name": "Test Razor 1",
                    "action": "add",
                    "comment_id": "def456",
                    "month": "2025-01",
                },
                {
                    "name": "Test Razor 2",
                    "action": "add",
                    "comment_id": "ghi789",
                    "month": "2025-01",
                },
                {
                    "name": "Hot Wheels Play Razor",
                    "action": "remove",
                    "comment_id": "abc123",
                    "month": "2025-01",
                },
            ],
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Added 2 entries" in data["message"]
        assert "Removed 1 entries" in data["message"]
        assert data["added_count"] == 2
        assert data["removed_count"] == 1

    def test_missing_category(self, client):
        """Test error handling for missing category."""
        request_data = {
            "entries": [
                {
                    "name": "Test Razor",
                    "action": "add",
                    "comment_id": "def456",
                    "month": "2025-01",
                }
            ]
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "category" in data["detail"][0]["loc"]

    def test_missing_entries(self, client):
        """Test error handling for missing entries."""
        request_data = {"category": "razor"}

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "entries" in data["detail"][0]["loc"]

    def test_invalid_action(self, client, temp_data_dir, monkeypatch):
        """Test error handling for invalid action."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "category": "razor",
            "entries": [
                {
                    "name": "Test Razor",
                    "action": "invalid",
                    "comment_id": "def456",
                    "month": "2025-01",
                }
            ],
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Invalid action: invalid" in data["errors"][0]

    def test_missing_required_fields(self, client, temp_data_dir, monkeypatch):
        """Test error handling for missing required fields."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "category": "razor",
            "entries": [
                {
                    "name": "Test Razor",
                    "action": "add",
                    # Missing comment_id and file_path
                }
            ],
        }

        response = client.post("/api/filtered/", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "Month is required for each entry" in data["errors"][0]


class TestGetFilteredEntriesByCategory:
    """Test GET /api/filtered/{category} endpoint."""

    def test_get_filtered_entries_by_category_success(self, client, temp_data_dir, monkeypatch):
        """Test successful retrieval of filtered entries by category."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        response = client.get("/api/filtered/razor")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Filtered entries for razor retrieved successfully" in data["message"]
        assert "razor" in data["data"]
        assert "Hot Wheels Play Razor" in data["data"]["razor"]

    def test_get_filtered_entries_by_category_empty(self, client, temp_data_dir, monkeypatch):
        """Test retrieval of empty category."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        response = client.get("/api/filtered/brush")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Filtered entries for brush retrieved successfully" in data["message"]
        assert "brush" in data["data"]
        assert data["data"]["brush"] == {}


class TestCheckFilteredStatus:
    """Test POST /api/filtered/check endpoint."""

    def test_check_filtered_status_success(self, client, temp_data_dir, monkeypatch):
        """Test successful checking of filtered status."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "entries": [
                {"category": "razor", "name": "Hot Wheels Play Razor"},
                {"category": "razor", "name": "Test Razor"},
                {"category": "brush", "name": "Test Brush"},
            ]
        }

        response = client.post("/api/filtered/check", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Filtered status checked successfully" in data["message"]
        assert data["data"]["razor:Hot Wheels Play Razor"] is True
        assert data["data"]["razor:Test Razor"] is False
        assert data["data"]["brush:Test Brush"] is False

    def test_check_filtered_status_missing_entries(self, client):
        """Test error handling for missing entries."""
        request_data = {}

        response = client.post("/api/filtered/check", json=request_data)

        assert response.status_code == 422  # FastAPI validation error
        data = response.json()
        assert "entries" in data["detail"][0]["loc"]

    def test_check_filtered_status_empty_entries(self, client):
        """Test error handling for empty entries list."""
        request_data = {"entries": []}

        response = client.post("/api/filtered/check", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "Entries list is required" in data["detail"]

    def test_check_filtered_status_invalid_entries(self, client, temp_data_dir, monkeypatch):
        """Test handling of invalid entries."""
        # Mock the file path

        monkeypatch.setattr(
            "webui.api.filtered.FILTERED_ENTRIES_PATH",
            Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml",
        )

        request_data = {
            "entries": [
                {"category": "razor", "name": "Hot Wheels Play Razor"},
                {
                    "category": "razor"
                    # Missing name
                },
                {
                    "name": "Test Razor"
                    # Missing category
                },
            ]
        }

        response = client.post("/api/filtered/check", json=request_data)

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        # Should only include valid entries in results
        assert "razor:Hot Wheels Play Razor" in data["data"]
        assert len(data["data"]) == 1
