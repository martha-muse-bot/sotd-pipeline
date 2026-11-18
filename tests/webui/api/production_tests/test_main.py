#!/usr/bin/env python3
"""Tests for the FastAPI main application."""

import pytest
from fastapi.testclient import TestClient

from webui.api.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "SOTD Pipeline Analyzer API"}


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/api/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert data["service"] == "SOTD Pipeline Analyzer API"
