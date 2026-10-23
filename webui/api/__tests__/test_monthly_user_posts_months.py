#!/usr/bin/env python3
"""/months must list months from user_analysis (bundle mode), enriched only as fallback."""

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app

client = TestClient(app)


def test_months_from_user_analysis(tmp_path, monkeypatch):
    ua = tmp_path / "aggregated" / "user_analysis"
    ua.mkdir(parents=True)
    for month, n in (("2026-08", 3), ("2026-09", 5)):
        (ua / f"{month}.json").write_text(json.dumps({"users": {f"u{i}": {} for i in range(n)}}))
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))

    resp = client.get("/api/monthly-user-posts/months")
    assert resp.status_code == 200
    months = resp.json()
    assert [m["month"] for m in months] == ["2026-09", "2026-08"]  # newest first
    assert months[0]["has_data"] is True and months[0]["user_count"] == 5


def test_months_falls_back_to_enriched_when_no_user_analysis(tmp_path, monkeypatch):
    enriched = tmp_path / "enriched"
    enriched.mkdir(parents=True)
    (enriched / "2026-01.json").write_text(json.dumps({"data": [{"author": "a"}, {"author": "b"}]}))
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))

    resp = client.get("/api/monthly-user-posts/months")
    assert resp.status_code == 200
    months = resp.json()
    assert [m["month"] for m in months] == ["2026-01"]
    assert months[0]["user_count"] == 2
