#!/usr/bin/env python3
"""Guard tests: the public app exposes ONLY read-only routes."""

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.public_main import app  # noqa: E402

client = TestClient(app)


def test_only_get_routes_exposed():
    schema = client.get("/openapi.json").json()
    for path, ops in schema["paths"].items():
        for method in ops:
            assert (
                method.lower() == "get"
            ), f"public app exposes non-GET route: {method.upper()} {path}"


def test_expected_router_prefixes_present():
    schema = client.get("/openapi.json").json()
    paths = list(schema["paths"])
    for prefix in ("/api/product-usage", "/api/monthly-user-posts", "/api/report-rankings", "/api/home"):
        assert any(p.startswith(prefix) for p in paths), f"missing {prefix}"


def test_no_admin_router_prefixes():
    schema = client.get("/openapi.json").json()
    banned = (
        "/api/analysis",
        "/api/catalogs",
        "/api/files",
        "/api/extract-overrides",
        "/api/filtered",
        "/api/brushes",
        "/api/soaps",
        "/api/validation",
        "/api/wsdb-alignment",
        "/api/format-compatibility",
    )
    for path in schema["paths"]:
        assert not path.startswith(banned), f"admin route leaked: {path}"


def test_health_endpoint():
    resp = client.get("/api/product-usage/health")
    assert resp.status_code == 200


def test_metrics_endpoint_exposed():
    # Not publicly routed (only the frontend container is), so no Host guard here.
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")
    assert "http_requests_total" in resp.text


def test_metrics_not_in_openapi_schema():
    schema = client.get("/openapi.json").json()
    assert "/metrics" not in schema["paths"]
