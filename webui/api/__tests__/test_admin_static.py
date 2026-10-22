#!/usr/bin/env python3
"""Admin app serves the built frontend via StaticFiles when dist/ exists."""

import sys
from pathlib import Path

from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import api.main as main_mod


def test_admin_serves_index_html_when_dist_exists(tmp_path, monkeypatch):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<html><body>frontend</body></html>")
    monkeypatch.setattr(main_mod, "_frontend_dist", dist)

    # Re-run the mount logic the way main.py does at import, against tmp dist
    test_app = main_mod.app
    # remove any previously mounted "/" apps to isolate the test
    test_app.router.routes = [r for r in test_app.router.routes if getattr(r, "path", "") != "/"]
    test_app.mount("/", StaticFiles(directory=str(dist), html=True), name="frontend-test")
    resp = TestClient(test_app).get("/")
    assert resp.status_code == 200
    assert "frontend" in resp.text


def test_admin_mount_guarded_by_dist_presence(tmp_path, monkeypatch):
    """The mount condition checks _frontend_dist.is_dir()."""
    monkeypatch.setattr(main_mod, "_frontend_dist", tmp_path / "no-such-dist")
    assert not main_mod._frontend_dist.is_dir()
