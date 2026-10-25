"""Tests for the public /api/home/overview endpoint (tmp_path-based, data-independent)."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def bundle(tmp_path: Path) -> Path:
    """Three-month tmp bundle (2026-08/09/10) shared by the client fixtures."""
    (tmp_path / "aggregated" / "user_analysis").mkdir(parents=True)
    (tmp_path / "aggregated" / "product_usage").mkdir(parents=True)

    # 2026-08: 3 users, posted_days 5/3/1 → 9 posts; 2026-09: 12; 2026-10: 3/2/2 → 7
    posted = {"2026-08": [5, 3, 1], "2026-09": [5, 4, 3], "2026-10": [3, 2, 2]}
    for m in ("2026-08", "2026-09", "2026-10"):
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
    return tmp_path


@pytest.fixture()
def client(bundle: Path, tmp_path: Path, monkeypatch):
    """Public app with SOTD_DATA_DIR pointed at the tmp bundle."""
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
    for month, usage in (
        ("2026-09", {"A": 90, "B": 60, "C": 30}),
        ("2026-10", {"B": 80, "C": 40, "A": 10}),
    ):
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


def test_month_param_overrides_tiles_and_movers(client):
    body = client.get("/api/home/overview?month=2026-08").json()
    assert body["latest_month"] == "2026-08"
    assert body["tiles"]["posts"] == 9
    # movers for 2026-08 vs 2026-07 (no July slice → prior empty → all is_new)
    assert all(m["is_new"] for m in body["movers"]["razors"])


def test_month_param_unknown_month_404(client):
    r = client.get("/api/home/overview?month=2001-01")
    assert r.status_code == 404


def test_movers_vs_prior_of_selected_month(client, tmp_path):
    # 2026-09 movers must compare vs 2026-08 (not the latest month's prior)
    body = client.get("/api/home/overview?month=2026-09").json()
    mover = next(m for m in body["movers"]["razors"] if m["name"] == "Gillette NEW")
    # Sept usage 3 vs Aug usage 3 → held rank → delta 0
    assert mover["delta"] == 0


# --- precomputed-payload fast path -------------------------------------------


@pytest.fixture()
def fresh_client(bundle: Path, tmp_path: Path, monkeypatch):
    """Client over a fresh app instance (empty in-memory cache)."""
    monkeypatch.setenv("SOTD_DATA_DIR", str(tmp_path))
    from fastapi import FastAPI

    import webui.api.home_overview as ho

    ho._cache["mtime"] = None
    ho._cache["payload"] = None
    app = FastAPI()
    app.include_router(ho.router)
    return TestClient(app)


def test_serves_precomputed_file(fresh_client, tmp_path):
    # A stale-but-present precomputed payload with distinctive values proves
    # the endpoint serves the file instead of recomputing.
    (tmp_path / "aggregated" / "home_overview.json").write_text(
        json.dumps(
            {
                "latest_month": "2020-01",
                "pulse": [{"month": "2020-01", "posts": 123}],
                "tiles": {
                    "posts": 123,
                    "shavers": 42,
                    "top_razor": "PRECOMPUTED",
                    "top_blade": None,
                    "top_soap": None,
                    "top_brush": None,
                },
                "movers": {"razors": [], "soaps": [], "blades": []},
            }
        )
    )
    body = fresh_client.get("/api/home/overview").json()
    assert body["tiles"]["top_razor"] == "PRECOMPUTED"
    assert body["latest_month"] == "2020-01"


def test_recomputes_when_bundle_changes(fresh_client, tmp_path):
    body = fresh_client.get("/api/home/overview").json()
    assert body["tiles"]["top_razor"] == "Gillette NEW"  # computed

    # Cache is now warm; mutate the bundle (publish replaces slices).
    pu_path = tmp_path / "aggregated" / "product_usage" / "2026-10.json"
    pu = json.loads(pu_path.read_text())
    pu["razors"] = {
        "Weber|PH": {
            "product": {"type": "razor", "brand": "Weber", "model": "PH"},
            "total_usage": 9,
            "unique_users": 2,
            "users": [],
        }
    }
    pu_path.write_text(json.dumps(pu))
    body = fresh_client.get("/api/home/overview").json()
    assert body["tiles"]["top_razor"] == "Weber PH"  # cache invalidated


def test_falls_back_to_compute_when_no_precomputed_file(fresh_client, tmp_path):
    body = fresh_client.get("/api/home/overview").json()
    assert body["latest_month"] == "2026-10"
    assert body["tiles"]["shavers"] == 3
    assert [p["month"] for p in body["pulse"]] == ["2026-08", "2026-09", "2026-10"]


# --- precompute writer --------------------------------------------------------


def test_write_precomputed_round_trips(bundle: Path, tmp_path):
    from webui.api.home_overview_builder import build_overview, write_precomputed

    write_precomputed(tmp_path)
    written = json.loads((tmp_path / "aggregated" / "home_overview.json").read_text())
    assert written == build_overview(tmp_path)
    assert written["latest_month"] == "2026-10"
    assert written["tiles"]["top_blade"] == "Personna GEM"


def test_verifier_accepts_home_overview_json(tmp_path):
    from scripts.publish_public_data import check_bundle

    # Same fixture shape as the endpoint tests: full three-month bundle.
    agg = tmp_path / "aggregated"
    for sub in ("user_analysis", "product_usage"):
        (agg / sub).mkdir(parents=True)
    for m in ("2026-08", "2026-09", "2026-10"):
        (agg / f"{m}.json").write_text("{}")
        (agg / "user_analysis" / f"{m}.json").write_text(json.dumps({"meta": {}, "users": {}}))
        (agg / "product_usage" / f"{m}.json").write_text(
            json.dumps({"meta": {}, "razors": {}, "blades": {}, "brushes": {}, "soaps": {}})
        )
    (agg / "home_overview.json").write_text("{}")
    assert check_bundle(tmp_path) == []


# --- months-list + rankings precompute ---------------------------------------


@pytest.fixture()
def rankings_bundle(tmp_path: Path) -> Path:
    """Bundle with top-level aggregated month files (rank tables), which
    build_rankings_rows / load_aggregated_data read."""
    agg = tmp_path / "aggregated"
    agg.mkdir(parents=True)
    for m in ("2026-08", "2026-09", "2026-10"):
        (agg / f"{m}.json").write_text(
            json.dumps(
                {
                    "meta": {"month": m, "total_shaves": 1000, "unique_shavers": 50},
                    "data": {
                        "razors": [
                            {"name": "Razor A", "shaves": 100, "unique_users": 10, "rank": 1},
                            {"name": "Razor B", "shaves": 80, "unique_users": 8, "rank": 2},
                        ]
                    },
                }
            )
        )
    return tmp_path


def test_build_months_list_counts_users(bundle: Path):
    from webui.api.home_overview_builder import build_months_list

    rows = build_months_list(bundle)
    assert [r["month"] for r in rows] == ["2026-08", "2026-09", "2026-10"]
    assert all(r["has_data"] for r in rows)
    assert all(r["user_count"] == 3 for r in rows)  # fixture: 3 users every month


def test_write_months_list_round_trips(bundle: Path):
    from webui.api.home_overview_builder import build_months_list, write_months_list

    out = write_months_list(bundle)
    written = json.loads(out.read_text())
    assert written == build_months_list(bundle)
    assert written[0]["month"] == "2026-08"


def test_build_rankings_rows_matches_table_rows(rankings_bundle: Path):
    """Precomputed rows carry the same name/rank/shaves/users as the endpoint's
    compute path (TableGenerator) for the same (table, month)."""
    from sotd.report.load import load_aggregated_data
    from sotd.report.table_generators.table_generator import TableGenerator
    from webui.api.home_overview_builder import build_rankings_rows

    rows_by_table = build_rankings_rows(rankings_bundle, table_ids=["razors"])
    months = rows_by_table["razors"]
    assert [m["month"] for m in months] == ["2026-08", "2026-09", "2026-10"]

    # Cross-check one month against the direct compute path.
    _, data = load_aggregated_data(rankings_bundle / "aggregated" / "2026-10.json", debug=False)
    gen = TableGenerator(data, comparison_data={}, current_month="2026-10")
    direct = gen.get_structured_table_data("razors", deltas=False, format_column_names=False)
    pre_rows = months[-1]["rows"]
    direct_pairs = sorted((r["name"], r["rank"]) for r in direct)
    pre_pairs = sorted((r["name"], r["rank"]) for r in pre_rows)
    assert pre_pairs == direct_pairs


def test_write_rankings_rows_one_file_per_table(rankings_bundle: Path):
    from webui.api.home_overview_builder import write_rankings_rows

    out_dir = write_rankings_rows(rankings_bundle)
    files = sorted(p.stem for p in out_dir.glob("*.json"))
    assert files == ["razors"]  # fixture data has only the razors list
    payload = json.loads((out_dir / "razors.json").read_text())
    assert payload["table"] == "razors"
    assert [m["month"] for m in payload["months"]] == ["2026-08", "2026-09", "2026-10"]


# --- endpoint fast paths for precomputed files --------------------------------


def test_mup_months_serves_precomputed(rankings_bundle: Path, monkeypatch):
    """monthly-user-posts/months serves the precomputed file when fresh."""
    from webui.api.home_overview_builder import write_months_list

    monkeypatch.setenv("SOTD_DATA_DIR", str(rankings_bundle))
    # The precompute derives from user_analysis/, absent in this minimal
    # fixture — build it so the freshness check (month-set equality) passes.
    ua = rankings_bundle / "aggregated" / "user_analysis"
    ua.mkdir()
    for m in ("2026-08", "2026-09", "2026-10"):
        (ua / f"{m}.json").write_text(json.dumps({"meta": {}, "users": {"u": {"posted_days": 1}}}))
    write_months_list(rankings_bundle)

    from fastapi import FastAPI

    from webui.api.monthly_user_posts import router as mup_router

    app = FastAPI()
    app.include_router(mup_router)
    client = TestClient(app)
    body = client.get("/api/monthly-user-posts/months").json()
    assert [m["month"] for m in body] == ["2026-08", "2026-09", "2026-10"]
    assert all(m["user_count"] == 1 for m in body)


def test_mup_months_falls_back_when_precomputed_stale(bundle: Path, monkeypatch):
    """Precomputed file missing a month present on disk → compute path used."""
    (bundle / "aggregated" / "monthly_user_posts_months.json").write_text(
        json.dumps(
            [{"month": "2026-08", "has_data": True, "user_count": 1}]
        )  # stale: missing 09/10
    )
    monkeypatch.setenv("SOTD_DATA_DIR", str(bundle))
    from fastapi import FastAPI

    from webui.api.monthly_user_posts import router as mup_router

    app = FastAPI()
    app.include_router(mup_router)
    client = TestClient(app)
    body = client.get("/api/monthly-user-posts/months").json()
    assert [m["month"] for m in body] == ["2026-10", "2026-09", "2026-08"]  # computed, newest first
