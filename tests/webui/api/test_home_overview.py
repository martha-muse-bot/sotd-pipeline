"""Tests for the public /api/home/overview endpoint (tmp_path-based, data-independent)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def client(tmp_path: Path, monkeypatch):
    """Public app with SOTD_DATA_DIR pointed at a tmp bundle."""
    (tmp_path / "aggregated" / "user_analysis").mkdir(parents=True)
    (tmp_path / "aggregated" / "product_usage").mkdir(parents=True)

    # 2026-08: 3 users, posted_days 5/3/1 → 9 posts; 2026-09: 12; 2026-10: 3/2/2 → 7
    posted = {"2026-08": [5, 3, 1], "2026-09": [5, 4, 3], "2026-10": [3, 2, 2]}
    for m, users in (("2026-08", 9), ("2026-09", 12), ("2026-10", 7)):
        ua_dir = tmp_path / "aggregated" / "user_analysis"
        (ua_dir / f"{m}.json").write_text(
            json.dumps(
                {
                    "meta": {},
                    "users": {
                        f"user{i}": {
                            "user": f"user{i}",
                            "posted_days": posted[m][i],
                            "missed_days": 0,
                            "posted_dates": [],
                            "comment_ids": [],
                            "comments_by_date": {},
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        }
                        for i in range(3)
                    },
                }
            )
        )
        pu_dir = tmp_path / "aggregated" / "product_usage"
        (pu_dir / f"{m}.json").write_text(
            json.dumps(
                {
                    "meta": {},
                    "razors": {
                        "Gillette|NEW": {
                            "product": {"type": "razor", "brand": "Gillette", "model": "NEW"},
                            "total_usage": 5 if m == "2026-10" else 3,
                            "unique_users": 2,
                            "users": [],
                        }
                    },
                    "blades": {
                        "Personna|GEM": {
                            "product": {"type": "blade", "brand": "Personna", "model": "GEM"},
                            "total_usage": 6,
                            "unique_users": 2,
                            "users": [],
                        }
                    },
                    "brushes": {},
                    "soaps": {},
                }
            )
        )

    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))
    from fastapi import FastAPI

    from webui.api.home_overview import router as home_router

    app = FastAPI()
    app.include_router(home_router)
    return TestClient(app)


def test_overview_returns_pulse_series(client):
    r = client.get("/api/home/overview")
    assert r.status_code == 200
    body = r.json()
    assert [p["month"] for p in body["pulse"]] == ["2026-08", "2026-09", "2026-10"]
    posts = {p["month"]: p["posts"] for p in body["pulse"]}
    assert posts["2026-08"] == 9  # 5+3+1
    assert body["latest_month"] == "2026-10"


def test_tiles_from_latest_month(client):
    body = client.get("/api/home/overview").json()
    assert body["tiles"]["posts"] == 7
    assert body["tiles"]["shavers"] == 3
    assert body["tiles"]["top_razor"] == "Gillette NEW"
    assert body["tiles"]["top_blade"] == "Personna GEM"


def test_movers_compare_with_prior_month(client):
    body = client.get("/api/home/overview").json()
    mover = next(m for m in body["movers"]["razors"] if m["name"] == "Gillette NEW")
    # Rank delta, not usage delta: Gillette NEW is the only razor in both
    # months → rank 1 in Sept, rank 1 in Oct → delta 0 (held #1).
    assert mover["count"] == 5
    assert mover["delta"] == 0
    assert mover["is_new"] is False


def test_rank_delta_climbs_and_drops(client, tmp_path):
    # Sept: A(90) B(60) C(30). Oct: B(80) C(40) A(10) — B climbs 2→1,
    # C climbs 3→2, A drops 1→3. Deltas must reflect position swaps.
    for month, usage in (("2026-09", {"A": 90, "B": 60, "C": 30}), ("2026-10", {"B": 80, "C": 40, "A": 10})):
        pu_path = tmp_path / "aggregated" / "product_usage" / f"{month}.json"
        pu = json.loads(pu_path.read_text())
        pu["razors"] = {
            f"Acme|{k}": {
                "product": {"type": "razor", "brand": "Acme", "model": k},
                "total_usage": v,
                "unique_users": 2,
                "users": [],
            }
            for k, v in usage.items()
        }
        pu_path.write_text(json.dumps(pu))
    body = client.get("/api/home/overview").json()
    deltas = {m["name"].split()[-1]: m["delta"] for m in body["movers"]["razors"]}
    assert deltas == {"B": 1, "C": 1, "A": -2}


def test_unknown_products_skipped(client, tmp_path):
    # "Unknown Smush" outsells everything — the public home must not headline it.
    pu_path = tmp_path / "aggregated" / "product_usage" / "2026-10.json"
    pu = json.loads(pu_path.read_text())
    pu["soaps"] = {
        "Unknown|Smush": {
            "product": {"type": "soap", "brand": "Unknown", "model": "Smush"},
            "total_usage": 99,
            "unique_users": 3,
            "users": [],
        },
        "Noble Otter|Halloween": {
            "product": {"type": "soap", "brand": "Noble Otter", "model": "Halloween"},
            "total_usage": 8,
            "unique_users": 2,
            "users": [],
        },
    }
    pu_path.write_text(json.dumps(pu))
    body = client.get("/api/home/overview").json()
    assert body["tiles"]["top_soap"] == "Noble Otter Halloween"
    assert all(m["name"] != "Unknown Smush" for m in body["movers"]["soaps"])


def test_empty_bundle_never_500s(tmp_path, monkeypatch):
    (tmp_path / "aggregated").mkdir(parents=True)
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))
    from fastapi import FastAPI

    from webui.api.home_overview import router as home_router

    app = FastAPI()
    app.include_router(home_router)
    client = TestClient(app)
    r = client.get("/api/home/overview")
    assert r.status_code == 200
    body = r.json()
    assert body["pulse"] == []
    assert body["latest_month"] is None
    assert body["tiles"] is None
    assert body["movers"] == {"razors": [], "soaps": [], "blades": []}
