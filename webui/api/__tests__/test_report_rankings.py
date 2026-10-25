#!/usr/bin/env python3
"""Tests for report rankings API endpoints."""

import json
import sys
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.main import app

client = TestClient(app)


def _mock_aggregated_content():
    """Minimal aggregated file content with meta and data (one table with rank/name)."""
    return {
        "meta": {
            "month": "2025-06",
            "total_shaves": 1000,
            "unique_shavers": 50,
        },
        "data": {
            "razors": [
                {"name": "Razor A", "shaves": 100, "unique_users": 10, "rank": 1},
                {"name": "Razor B", "shaves": 80, "unique_users": 8, "rank": 2},
                {"name": "Razor C", "shaves": 60, "unique_users": 6, "rank": 3},
            ],
            "blades": [
                {"name": "Blade X", "shaves": 200, "unique_users": 20, "rank": 1},
            ],
        },
    }


def test_report_rankings_months_empty(tmp_path):
    """GET /api/report-rankings/months returns empty when no aggregated data."""
    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        resp = client.get("/api/report-rankings/months")
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert data["months"] == []


def test_report_rankings_months_returns_sorted_stems(tmp_path):
    """GET /api/report-rankings/months returns sorted YYYY-MM stems from JSON files."""
    (tmp_path / "2025-07.json").write_text("{}")
    (tmp_path / "2025-06.json").write_text("{}")
    (tmp_path / "2025-08.json").write_text("{}")
    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        resp = client.get("/api/report-rankings/months")
    assert resp.status_code == 200
    data = resp.json()
    assert data["months"] == ["2025-06", "2025-07", "2025-08"]


def test_report_rankings_tables_empty_when_no_months(tmp_path):
    """GET /api/report-rankings/tables returns empty when no months available."""
    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        resp = client.get("/api/report-rankings/tables")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tables"] == []


def test_report_rankings_tables_from_aggregated_data(tmp_path):
    """GET /api/report-rankings/tables returns table list from one aggregated file."""
    agg_file = tmp_path / "2025-06.json"
    agg_file.write_text(json.dumps(_mock_aggregated_content(), indent=2), encoding="utf-8")

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data") as load_mock:
            metadata = {"month": "2025-06", "total_shaves": 1000, "unique_shavers": 50}
            content = _mock_aggregated_content()
            load_mock.return_value = (metadata, content["data"])
            resp = client.get("/api/report-rankings/tables")
    assert resp.status_code == 200
    data = resp.json()
    tables = data["tables"]
    ids = [t["id"] for t in tables]
    assert "razors" in ids
    assert "blades" in ids
    labels = [t["label"] for t in tables]
    assert "Razors" in labels
    assert "Blades" in labels


def test_report_rankings_items_from_name_columns(tmp_path):
    """GET /api/report-rankings/items returns item names when rows have name/string columns."""
    content = _mock_aggregated_content()
    (tmp_path / "2025-06.json").write_text(json.dumps(content, indent=2), encoding="utf-8")

    def load_side_effect(file_path, debug=False):
        c = json.loads(file_path.read_text(encoding="utf-8"))
        return c["meta"], c["data"]

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data", side_effect=load_side_effect):
            with patch("api.report_rankings.TableGenerator") as tg_mock:
                gen = tg_mock.return_value
                gen.get_structured_table_data.return_value = [
                    {"name": "Razor A", "rank": 1, "shaves": 100, "unique_users": 10},
                    {"name": "Razor B", "rank": 2, "shaves": 80, "unique_users": 8},
                ]
                resp = client.get("/api/report-rankings/items", params={"table": "razors"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == ["Razor A", "Razor B"]


def test_report_rankings_items_from_use_count_only(tmp_path):
    """GET /api/report-rankings/items returns use_count as labels when no name column (e.g. blade_usage_distribution)."""
    content = {"meta": {"month": "2025-06"}, "data": {"blade_usage_distribution": []}}
    (tmp_path / "2025-06.json").write_text(json.dumps(content, indent=2), encoding="utf-8")

    def load_side_effect(file_path, debug=False):
        c = json.loads(file_path.read_text(encoding="utf-8"))
        return c["meta"], c["data"]

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data", side_effect=load_side_effect):
            with patch("api.report_rankings.TableGenerator") as tg_mock:
                gen = tg_mock.return_value
                # Rows with only rank, use_count, shaves, unique_users (no name/string column)
                gen.get_structured_table_data.return_value = [
                    {"rank": 1, "use_count": 1, "shaves": 500, "unique_users": 200},
                    {"rank": 2, "use_count": 2, "shaves": 300, "unique_users": 150},
                    {"rank": 3, "use_count": 3, "shaves": 100, "unique_users": 80},
                ]
                resp = client.get(
                    "/api/report-rankings/items",
                    params={"table": "blade_usage_distribution"},
                )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == ["1", "2", "3"]


def test_report_rankings_items_union_across_months(tmp_path):
    """GET /api/report-rankings/items without month returns union of items from all months."""
    (tmp_path / "2025-06.json").write_text("{}", encoding="utf-8")
    (tmp_path / "2025-07.json").write_text("{}", encoding="utf-8")

    def load_side_effect(file_path, debug=False):
        return {"month": file_path.stem}, {}

    rows_2025_06 = [
        {"name": "DE", "rank": 1, "shaves": 100, "unique_users": 50},
        {"name": "AC", "rank": 2, "shaves": 30, "unique_users": 20},
    ]
    rows_2025_07 = [
        {"name": "DE", "rank": 1, "shaves": 90, "unique_users": 48},
        {"name": "Straight", "rank": 2, "shaves": 80, "unique_users": 40},
    ]

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data", side_effect=load_side_effect):
            with patch("api.report_rankings.TableGenerator") as tg_mock:
                gen = tg_mock.return_value
                # First call (2025-06): DE, AC. Second call (2025-07): DE, Straight
                gen.get_structured_table_data.side_effect = [rows_2025_06, rows_2025_07]
                resp = client.get("/api/report-rankings/items", params={"table": "razor_formats"})
    assert resp.status_code == 200
    data = resp.json()
    # All three formats appear (AC from month 1, Straight from month 2), sorted
    assert set(data["items"]) == {"AC", "DE", "Straight"}
    assert data["items"] == sorted(data["items"], key=str.lower)


def test_report_rankings_series_requires_items():
    """GET /api/report-rankings/series returns 400 when items missing."""
    resp = client.get("/api/report-rankings/series", params={"table": "razors", "items": ""})
    assert resp.status_code == 400


def test_report_rankings_series_returns_shape(tmp_path):
    """GET /api/report-rankings/series returns months and series for requested items."""
    agg1 = _mock_aggregated_content()
    agg1["meta"]["month"] = "2025-06"
    (tmp_path / "2025-06.json").write_text(json.dumps(agg1, indent=2), encoding="utf-8")
    agg2 = _mock_aggregated_content()
    agg2["meta"]["month"] = "2025-07"
    agg2["data"]["razors"][0]["rank"] = 2
    agg2["data"]["razors"][1]["rank"] = 1
    (tmp_path / "2025-07.json").write_text(json.dumps(agg2, indent=2), encoding="utf-8")

    def load_side_effect(file_path, debug=False):
        content = json.loads(file_path.read_text(encoding="utf-8"))
        return content["meta"], content["data"]

    return_2025_06 = [
        {"name": "Razor A", "rank": 1, "shaves": 100, "unique_users": 10},
        {"name": "Razor B", "rank": 2, "shaves": 80, "unique_users": 8},
    ]
    return_2025_07 = [
        {"name": "Razor B", "rank": 1, "shaves": 90, "unique_users": 9},
        {"name": "Razor A", "rank": 2, "shaves": 70, "unique_users": 7},
    ]

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data", side_effect=load_side_effect):
            with patch("api.report_rankings.TableGenerator") as tg_mock:
                gen = tg_mock.return_value
                gen.get_structured_table_data.side_effect = [return_2025_06, return_2025_07]

                resp = client.get(
                    "/api/report-rankings/series",
                    params={"table": "razors", "items": "Razor A,Razor B"},
                )
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert "series" in data
    assert len(data["series"]) == 2
    items = {s["item"]: s["data"] for s in data["series"]}
    assert "Razor A" in items
    assert "Razor B" in items
    assert len(items["Razor A"]) == len(data["months"])
    assert len(items["Razor B"]) == len(data["months"])
    assert items["Razor A"][0].get("unique_users") == 10
    assert items["Razor A"][1].get("unique_users") == 7
    assert items["Razor B"][0].get("unique_users") == 8
    assert items["Razor B"][1].get("unique_users") == 9


def test_report_rankings_pivoted_empty_when_no_months(tmp_path):
    """GET /api/report-rankings/pivoted returns empty months and lanes when no data."""
    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        resp = client.get("/api/report-rankings/pivoted", params={"table": "razors"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["months"] == []
    assert data["lanes"] == []


def test_report_rankings_pivoted_returns_20_lanes_and_prev_rank(tmp_path):
    """GET /api/report-rankings/pivoted returns 20 lanes, months align, prev_rank set when applicable."""
    # Month 1: Razor A=1, Razor B=2, Razor C=3. Month 2: Razor B=1, Razor A=2, Razor C=3.
    return_2025_06 = [
        {"name": "Razor A", "rank": 1, "shaves": 100, "unique_users": 10},
        {"name": "Razor B", "rank": 2, "shaves": 80, "unique_users": 8},
        {"name": "Razor C", "rank": 3, "shaves": 60, "unique_users": 6},
    ]
    return_2025_07 = [
        {"name": "Razor B", "rank": 1, "shaves": 90, "unique_users": 9},
        {"name": "Razor A", "rank": 2, "shaves": 70, "unique_users": 7},
        {"name": "Razor C", "rank": 3, "shaves": 50, "unique_users": 5},
    ]

    def load_side_effect(file_path, debug=False):
        content = json.loads(file_path.read_text(encoding="utf-8"))
        return content["meta"], content["data"]

    (tmp_path / "2025-06.json").write_text(
        json.dumps(_mock_aggregated_content(), indent=2), encoding="utf-8"
    )
    (tmp_path / "2025-07.json").write_text(
        json.dumps(_mock_aggregated_content(), indent=2), encoding="utf-8"
    )

    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        with patch("api.report_rankings.load_aggregated_data", side_effect=load_side_effect):
            with patch("api.report_rankings.TableGenerator") as tg_mock:
                gen = tg_mock.return_value
                gen.get_structured_table_data.side_effect = [
                    return_2025_06,
                    return_2025_07,
                ]
                resp = client.get("/api/report-rankings/pivoted", params={"table": "razors"})
    assert resp.status_code == 200
    data = resp.json()
    assert "months" in data
    assert "lanes" in data
    assert data["months"] == ["2025-06", "2025-07"]
    assert len(data["lanes"]) == 20
    for i, lane in enumerate(data["lanes"]):
        assert lane["rank"] == i + 1
        assert len(lane["points"]) == 2
        for pt in lane["points"]:
            assert "month" in pt
            assert "item" in pt
            assert "prev_rank" in pt
            assert "unique_users" in pt
    # Lane 1 (rank 1): month 1 = Razor A (prev_rank null), month 2 = Razor B (prev_rank 2)
    lane1 = data["lanes"][0]
    assert lane1["points"][0]["item"] == "Razor A"
    assert lane1["points"][0]["prev_rank"] is None
    assert lane1["points"][0]["unique_users"] == 10
    assert lane1["points"][1]["item"] == "Razor B"
    assert lane1["points"][1]["prev_rank"] == 2
    assert lane1["points"][1]["unique_users"] == 9
    # Lane 2 (rank 2): month 1 = Razor B (prev_rank null), month 2 = Razor A (prev_rank 1)
    lane2 = data["lanes"][1]
    assert lane2["points"][0]["item"] == "Razor B"
    assert lane2["points"][1]["item"] == "Razor A"
    assert lane2["points"][1]["prev_rank"] == 1


def test_month_cache_invalidates_on_file_change(tmp_path):
    """A replaced month file (publish) must serve fresh data, not the cache."""
    from api.report_rankings import _month_cache, _table_rows_cache

    _month_cache.clear()
    _table_rows_cache.clear()
    agg_file = tmp_path / "2025-06.json"
    agg_file.write_text(json.dumps(_mock_aggregated_content()))
    with patch("api.report_rankings._get_aggregated_dir", return_value=tmp_path):
        r1 = client.get("/api/report-rankings/series?table=razors&items=Razor%20A").json()
        rank1 = r1["series"][0]["data"][0]["rank"]

        # Publish replaces the file: same month, different content + mtime.
        import os, time as _time

        content2 = _mock_aggregated_content()
        content2["data"]["razors"] = [
            {"name": "Razor A", "shaves": 42, "unique_users": 4, "rank": 7}
        ]
        agg_file.write_text(json.dumps(content2))
        st = agg_file.stat()
        os.utime(agg_file, (st.st_atime, st.st_mtime + 2))  # force mtime change

        r2 = client.get("/api/report-rankings/series?table=razors&items=Razor%20A").json()
        rank2 = r2["series"][0]["data"][0]["rank"]

    assert rank1 == 1
    assert rank2 == 7  # cache invalidated: fresh read, not the stale rank
    _month_cache.clear()
    _table_rows_cache.clear()
