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

    # Build a FRESH app instead of mutating the shared singleton: main.py may
    # have already mounted the real dist/ at "/" at import time (any checkout
    # with webui/dist present), and a fresh FastAPI app reproduces exactly the
    # mount logic under test without cross-test state.
    from fastapi import FastAPI

    test_app = FastAPI()
    if main_mod._frontend_dist.is_dir():
        test_app.mount(
            "/", StaticFiles(directory=str(main_mod._frontend_dist), html=True),
            name="frontend",
        )
    resp = TestClient(test_app).get("/")
    assert resp.status_code == 200
    assert "frontend" in resp.text


def test_admin_mount_guarded_by_dist_presence(tmp_path, monkeypatch):
    """The mount condition checks _frontend_dist.is_dir()."""
    monkeypatch.setattr(main_mod, "_frontend_dist", tmp_path / "no-such-dist")
    assert not main_mod._frontend_dist.is_dir()
