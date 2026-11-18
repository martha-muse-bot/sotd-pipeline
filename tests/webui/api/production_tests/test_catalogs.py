#!/usr/bin/env python3
"""Tests for catalog endpoints."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from webui.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def temp_catalog_dir():
    with tempfile.TemporaryDirectory() as temp_dir:
        catalog_dir = Path(temp_dir)
        # Create minimal test YAML files
        (catalog_dir / "razors.yaml").write_text("brand1:\n  model1:\n    - pattern1\n")
        (catalog_dir / "blades.yaml").write_text("brand2:\n  model2:\n    - pattern2\n")
        yield catalog_dir


class TestCatalogEndpoints:
    def test_list_catalogs(self, client, temp_catalog_dir):
        with patch("webui.api.catalogs.CATALOG_DIR", temp_catalog_dir):
            response = client.get("/api/catalogs/")
            assert response.status_code == 200
            data = response.json()
            # API returns nested structure with 'catalogs' array
            assert "catalogs" in data
            catalog_names = [cat["name"] for cat in data["catalogs"]]
            assert "razor" in catalog_names
            assert "blade" in catalog_names

    def test_get_catalog_success(self, client, temp_catalog_dir):
        with patch("webui.api.catalogs.CATALOG_DIR", temp_catalog_dir):
            response = client.get("/api/catalogs/razor")
            assert response.status_code == 200
            data = response.json()
            assert "brand1" in data

    def test_get_catalog_not_found(self, client, temp_catalog_dir):
        with patch("webui.api.catalogs.CATALOG_DIR", temp_catalog_dir):
            response = client.get("/api/catalogs/soap")
            assert response.status_code == 404 or response.status_code == 500

    def test_get_catalog_invalid_field(self, client):
        response = client.get("/api/catalogs/invalidfield")
        assert response.status_code == 404
        data = response.json()
        assert "Unknown catalog field" in data["detail"]
