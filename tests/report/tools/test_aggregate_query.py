"""Tests for the aggregate_query CLI tool."""

import json

import pytest

from sotd.report.tools.aggregate_query import main


def make_month_file(path, month, razors, soaps, meta_extra=None, extra=None):
    meta = {"month": month, "total_shaves": 100, "unique_shavers": 5}
    meta.update(meta_extra or {})
    data = {
        "razors": razors,
        "soaps": soaps,
        "sample_usage_metrics": {"total_samples": 0},
    }
    data.update(extra or {})
    doc = {"meta": meta, "data": data}
    path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def data_dir(tmp_path):
    """Three monthly files plus one annual file under a tmp data dir."""
    agg = tmp_path / "aggregated"
    agg.mkdir()
    razor_sets = {
        "2026-01": [
            {"rank": 1, "name": "Blackland Blackbird", "shaves": 90, "unique_users": 4},
            {"rank": 2, "name": "RazoRock Game Changer", "shaves": 6, "unique_users": 2},
        ],
        "2026-02": [
            {"rank": 1, "name": "RazoRock Game Changer", "shaves": 80, "unique_users": 3},
            {"rank": 2, "name": "Blackland Blackbird", "shaves": 15, "unique_users": 3},
        ],
        "2026-03": [
            {"rank": 1, "name": "Blackland Blackbird", "shaves": 70, "unique_users": 4},
            {"rank": 2, "name": "RazoRock Game Changer", "shaves": 9, "unique_users": 2},
        ],
    }
    soaps = [
        {"rank": 1, "name": "Martin de Candre - Fougere", "shaves": 30, "unique_users": 3},
        {"rank": 2, "name": "Barrister and Mann - Seville", "shaves": 4, "unique_users": 2},
    ]
    # Categories whose rows are keyed by something other than "name", mirroring
    # the real aggregated shape: monthly maker tables are brand-keyed, user
    # tables are user-keyed, composite tables share a user across rows.
    key_field_sets = {
        "soap_makers": {
            "2026-01": [
                {"rank": 1, "brand": "Stirling Soap Co.", "shaves": 200, "unique_users": 62},
                {"rank": 2, "brand": "Stirling East", "shaves": 50, "unique_users": 10},
                {"rank": 3, "brand": "House of Mammoth", "shaves": 41, "unique_users": 22},
            ],
            "2026-02": [
                {"rank": 1, "brand": "Stirling Soap Co.", "shaves": 190, "unique_users": 60},
                {"rank": 2, "brand": "House of Mammoth", "shaves": 130, "unique_users": 40},
            ],
            "2026-03": [
                {"rank": 1, "brand": "Stirling Soap Co.", "shaves": 210, "unique_users": 65},
                {"rank": 2, "brand": "House of Mammoth", "shaves": 150, "unique_users": 45},
            ],
        },
        "brand_diversity": {
            "2026-01": [{"rank": 1, "brand": "Stirling Soap Co.", "unique_soaps": 60}],
            "2026-02": [{"rank": 1, "brand": "Stirling Soap Co.", "unique_soaps": 58}],
            "2026-03": [{"rank": 1, "brand": "Stirling Soap Co.", "unique_soaps": 61}],
        },
        "users": {
            "2026-01": [{"rank": 1, "user": "annuser", "shaves": 31, "missed_days": 0}],
            "2026-02": [{"rank": 1, "user": "annuser", "shaves": 30, "missed_days": 1}],
            "2026-03": [{"rank": 1, "user": "annuser", "shaves": 28, "missed_days": 0}],
        },
        "highest_use_count_per_blade": {
            "2026-01": [
                {"rank": 1, "user": "annuser", "blade": "Feather", "format": "DE", "uses": 5},
                {"rank": 2, "user": "annuser", "blade": "Lord Platinum", "format": "DE", "uses": 4},
            ],
            "2026-02": [
                {"rank": 1, "user": "annuser", "blade": "Feather", "format": "DE", "uses": 6},
                {"rank": 2, "user": "annuser", "blade": "Lord Platinum", "format": "DE", "uses": 5},
            ],
            "2026-03": [
                {"rank": 1, "user": "annuser", "blade": "Feather", "format": "DE", "uses": 7},
                {"rank": 2, "user": "annuser", "blade": "Lord Platinum", "format": "DE", "uses": 6},
            ],
        },
        # hhi rows are in file order = canonical rank (unique_combinations desc, shaves desc)
        "user_soap_brand_scent_diversity": {
            "2026-01": [
                {
                    "rank": 1,
                    "user": "scribe",
                    "shaves": 38,
                    "effective_soaps": 1,
                    "unique_combinations": 38,
                    "hhi": 0.05,
                },
                {
                    "rank": 2,
                    "user": "lowshave",
                    "shaves": 2,
                    "effective_soaps": 2,
                    "unique_combinations": 5,
                    "hhi": 0.99,
                },
                {
                    "rank": 3,
                    "user": "mono",
                    "shaves": 31,
                    "effective_soaps": 10,
                    "unique_combinations": 3,
                    "hhi": 0.9,
                },
                {
                    "rank": 4,
                    "user": "glass",
                    "shaves": 29,
                    "effective_soaps": 10,
                    "unique_combinations": 3,
                    "hhi": 0.877,
                },
                {
                    "rank": 5,
                    "user": "pair_a",
                    "shaves": 6,
                    "effective_soaps": 5,
                    "unique_combinations": 2,
                    "hhi": 0.8,
                },
                {
                    "rank": 6,
                    "user": "pair_b",
                    "shaves": 6,
                    "effective_soaps": 5,
                    "unique_combinations": 2,
                    "hhi": 0.8,
                },
            ],
            "2026-02": [
                {
                    "rank": 1,
                    "user": "annuser",
                    "shaves": 30,
                    "effective_soaps": 2,
                    "unique_combinations": 2,
                    "hhi": 0.85,
                },
            ],
            "2026-03": [
                {
                    "rank": 1,
                    "user": "annuser",
                    "shaves": 28,
                    "effective_soaps": 2,
                    "unique_combinations": 2,
                    "hhi": 0.86,
                },
            ],
        },
        "weird": {
            "2026-01": [{"rank": 1, "widget": "gizmo", "shaves": 5}],
            "2026-02": [],
            "2026-03": [],
        },
    }
    for month, razors in razor_sets.items():
        extra = {key: months[month] for key, months in key_field_sets.items()}
        make_month_file(agg / f"{month}.json", month, razors, soaps, extra=extra)
    annual = {
        "metadata": {"year": 2025, "total_shaves": 12000},
        "razors": [{"rank": 1, "name": "Blackland Blackbird", "shaves": 900, "unique_users": 30}],
        # the annual engine re-keys maker tables to name; these stay brand/user-keyed
        "soap_makers": [
            {"rank": 1, "name": "Stirling Soap Co.", "shaves": 1200, "unique_users": 80}
        ],
        "brand_diversity": [{"rank": 1, "brand": "Stirling Soap Co.", "unique_soaps": 600}],
        "users": [{"rank": 1, "user": "annuser", "shaves": 500, "missed_days": 2}],
        "sample_usage_metrics": {"total_samples": 0},
    }
    (agg / "annual").mkdir()
    (agg / "annual" / "2025.json").write_text(json.dumps(annual), encoding="utf-8")
    return tmp_path


def run(capsys, argv):
    """Run the CLI and return (exit_code, stdout, stderr)."""
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestMeta:
    def test_meta_month(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "meta", "--month", "2026-02"])
        assert code == 0
        assert "total_shaves" in out
        assert "100" in out
        assert '"2026-02"' in out

    def test_meta_annual(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "meta", "--year", "2025"])
        assert code == 0
        assert "total_shaves" in out
        assert "12000" in out

    def test_meta_missing_file(self, data_dir, capsys):
        code, _, err = run(capsys, ["--data-dir", str(data_dir), "meta", "--month", "2025-01"])
        assert code == 1
        assert "file not found" in err


class TestTop:
    def test_top_default(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "top", "--month", "2026-01", "--category", "razors"],
        )
        assert code == 0
        assert "Blackland Blackbird" in out
        assert "90" in out

    def test_top_n_and_min_shaves(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "razors",
                "--top",
                "1",
                "--min-shaves",
                "10",
            ],
        )
        assert code == 0
        assert "Blackland Blackbird" in out
        assert "RazoRock" not in out

    def test_top_unknown_category_lists_valid(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            ["--data-dir", str(data_dir), "top", "--month", "2026-01", "--category", "wands"],
        )
        assert code == 1
        assert "unknown category" in err
        assert "razors" in err

    def test_top_non_list_category(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "sample_usage_metrics",
            ],
        )
        assert code == 1
        assert "not a ranked list" in err

    def test_top_annual(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "top", "--year", "2025", "--category", "razors"]
        )
        assert code == 0
        assert "Blackland Blackbird" in out


class TestHistory:
    def test_history_last_n(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "blackland blackbird",
                "--last",
                "3",
            ],
        )
        assert code == 0
        for period in ("2026-01", "2026-02", "2026-03"):
            assert period in out
        assert "1" in out and "2" in out

    def test_history_absent_rows(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Karve Overlander",
                "--last",
                "2",
            ],
        )
        assert code == 0
        rows = json.loads(out)["rows"]
        assert len(rows) == 2
        for row in rows:
            assert row["rank"] is None
            assert row["shaves"] is None
            assert row["unique_users"] is None

    def test_history_start_end_range(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--start",
                "2026-02",
                "--end",
                "2026-03",
            ],
        )
        assert code == 0
        assert "2026-01" not in out
        assert "2026-02" in out and "2026-03" in out

    def test_history_last_with_end(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--last",
                "2",
                "--end",
                "2026-02",
            ],
        )
        assert code == 0
        assert "2026-03" not in out
        assert "2026-01" in out and "2026-02" in out

    def test_history_contains_ambiguous(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "soaps",
                "--name",
                "-",
                "--contains",
                "--last",
                "1",
            ],
        )
        assert code == 1
        assert "ambiguous name" in err

    def test_history_min_shaves_masks_month(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "RazoRock Game Changer",
                "--last",
                "2",
                "--min-shaves",
                "10",
            ],
        )
        assert code == 0
        rows = json.loads(out)["rows"]
        # --last 2 = 2026-02 (80 shaves, stays) and 2026-03 (9 shaves, masked)
        assert rows[0]["shaves"] == 80
        assert rows[1]["shaves"] is None

    def test_history_year_annual(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--year",
                "2025",
            ],
        )
        assert code == 0
        assert "2025" in out and "900" in out

    def test_history_year_rejects_range(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--year",
                "2025",
                "--last",
                "2",
            ],
        )
        assert code == 1
        assert "cannot be combined" in err

    def test_history_no_mode(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
            ],
        )
        assert code == 1
        assert "needs" in err

    def test_history_last_zero(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--last",
                "0",
            ],
        )
        assert code == 1
        assert "positive integer" in err

    def test_history_skips_missing_month(self, data_dir, capsys):
        (data_dir / "aggregated" / "2026-02.json").unlink()
        code, out, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--start",
                "2026-01",
                "--end",
                "2026-03",
            ],
        )
        assert code == 0
        assert "skipped missing files: 2026-02" in out

    def test_history_json(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--last",
                "1",
            ],
        )
        assert code == 0
        result = json.loads(out)
        assert result["rows"][0]["rank"] == 1
        assert result["rows"][0]["shaves"] == 70


class TestSchema:
    def test_month_schema_lists_categories_with_counts_and_fields(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "schema", "--month", "2026-01"])
        assert code == 0
        assert "razors" in out
        assert "soaps" in out
        assert "rows=2" in out
        assert "unique_users" in out

    def test_schema_marks_non_list_sections(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "schema", "--month", "2026-01"])
        assert code == 0
        assert "sample_usage_metrics" in out
        assert "dict" in out
        assert "total_samples" in out

    def test_annual_schema(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "schema", "--year", "2025"])
        assert code == 0
        assert "razors" in out
        assert "rows=1" in out

    def test_json_output(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--json", "--data-dir", str(data_dir), "schema", "--month", "2026-01"]
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["categories"]["razors"]["rows"] == 2
        assert "shaves" in doc["categories"]["razors"]["fields"]

    def test_missing_month_exits_1(self, tmp_path, capsys):
        code, _, err = run(capsys, ["--data-dir", str(tmp_path), "schema", "--month", "2025-01"])
        assert code == 1
        assert "file not found" in err


class TestHistoryMultiName:
    def test_two_names_render_side_by_side(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--name",
                "RazoRock Game Changer",
                "--last",
                "2",
            ],
        )
        assert code == 0
        header = next(line for line in out.splitlines() if "Blackland Blackbird" in line)
        assert "RazoRock Game Changer" in header
        assert "2026-02" in out and "2026-03" in out
        # 2026-02: Blackbird #1 80/3, Game Changer #2 15/3
        assert "#1 80/3" in out
        assert "#2 15/3" in out

    def test_json_multi_name_rows_carry_per_name_maps(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--name",
                "RazoRock Game Changer",
                "--last",
                "1",
            ],
        )
        assert code == 0
        result = json.loads(out)
        assert result["names"] == ["Blackland Blackbird", "RazoRock Game Changer"]
        row = result["rows"][0]
        assert row["period"] == "2026-03"
        assert row["RazoRock Game Changer"]["shaves"] == 9
        assert row["Blackland Blackbird"]["rank"] == 1

    def test_multi_name_absent_item_renders_dash(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--name",
                "Gillette Tech",
                "--last",
                "1",
            ],
        )
        assert code == 0
        assert "Gillette Tech" in out
        # the absent item's 2026-03 cell is "-"
        row = next(line for line in out.splitlines() if line.startswith("2026-03"))
        assert row.count("-") >= 1

    def test_single_name_json_shape_unchanged(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "razors",
                "--name",
                "Blackland Blackbird",
                "--last",
                "1",
            ],
        )
        assert code == 0
        result = json.loads(out)
        assert result["name"] == "Blackland Blackbird"
        assert result["rows"][0]["rank"] == 1


class TestKeyFieldAwareness:
    """Categories keyed by brand/user/... (not name) render and match correctly."""

    def test_top_renders_brand_key_field(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "top", "--month", "2026-01", "--category", "soap_makers"],
        )
        assert code == 0
        assert "brand" in out
        assert "Stirling Soap Co." in out

    def test_top_renders_user_key_field(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "top", "--month", "2026-01", "--category", "users"],
        )
        assert code == 0
        assert "annuser" in out
        assert "missed_days" in out

    def test_top_renders_unique_soaps_column(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "brand_diversity",
            ],
        )
        assert code == 0
        assert "unique_soaps" in out
        assert "60" in out

    def test_top_json_preserves_raw_fields(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "brand_diversity",
            ],
        )
        assert code == 0
        assert json.loads(out)[0] == {"rank": 1, "brand": "Stirling Soap Co.", "unique_soaps": 60}

    def test_top_json_skips_key_rendering(self, data_dir, capsys):
        # JSON mode dumps raw rows even when no key field can be derived
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "weird",
            ],
        )
        assert code == 0
        assert json.loads(out)[0]["widget"] == "gizmo"

    def test_top_unrecognized_key_field_errors_loudly(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            ["--data-dir", str(data_dir), "top", "--month", "2026-01", "--category", "weird"],
        )
        assert code == 1
        assert "key field" in err
        assert "widget" in err

    def test_top_min_shaves_errors_on_shavesless_category(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "brand_diversity",
                "--min-shaves",
                "5",
            ],
        )
        assert code == 1
        assert "shaves" in err

    def test_top_sort_hhi_matches_boring_table(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "user_soap_brand_scent_diversity",
                "--sort",
                "hhi",
                "--min-shaves",
                "5",
            ],
        )
        assert code == 0
        rows = [line.split() for line in out.splitlines()[1:]]
        # hhi desc, shaves desc — the report's Most Boring Shaver view. The
        # shaves:2 row (highest hhi) is filtered before sorting.
        assert [r[1] for r in rows] == ["mono", "glass", "pair_a", "pair_b", "scribe"]
        # Competition ranks on equal (hhi, shaves): 1, 2, 3, 3, 5.
        assert [r[0] for r in rows] == ["1", "2", "3", "3", "5"]

    def test_top_sort_hhi_json_reranks(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "user_soap_brand_scent_diversity",
                "--sort",
                "hhi",
                "--min-shaves",
                "5",
            ],
        )
        assert code == 0
        entries = json.loads(out)
        assert [(e["user"], e["rank"]) for e in entries] == [
            ("mono", 1),
            ("glass", 2),
            ("pair_a", 3),
            ("pair_b", 3),
            ("scribe", 5),
        ]

    def test_top_sort_hhi_errors_without_hhi(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "top",
                "--month",
                "2026-01",
                "--category",
                "users",
                "--sort",
                "hhi",
            ],
        )
        assert code == 1
        assert "hhi" in err

    def test_history_matches_brand_keyed_item(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "soap_makers",
                "--name",
                "Stirling Soap Co.",
                "--last",
                "2",
            ],
        )
        assert code == 0
        assert "2026-02" in out and "2026-03" in out
        assert "190" in out and "210" in out

    def test_history_matches_user_keyed_item(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "users",
                "--name",
                "annuser",
                "--last",
                "1",
            ],
        )
        assert code == 0
        row = json.loads(out)["rows"][0]
        assert row["rank"] == 1
        assert row["shaves"] == 28
        assert row["missed_days"] == 0

    def test_history_matrix_brand_keyed(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "soap_makers",
                "--name",
                "Stirling Soap Co.",
                "--name",
                "House of Mammoth",
                "--last",
                "1",
            ],
        )
        assert code == 0
        assert "#1 210/65" in out
        assert "#2 150/45" in out

    def test_history_annual_soap_makers_name_keyed(self, data_dir, capsys):
        # the annual engine re-keys maker tables to name; monthly is brand-keyed
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "soap_makers",
                "--name",
                "Stirling Soap Co.",
                "--year",
                "2025",
            ],
        )
        assert code == 0
        assert "1,200" in out

    def test_history_annual_user_keyed(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "users",
                "--name",
                "annuser",
                "--year",
                "2025",
            ],
        )
        assert code == 0
        assert json.loads(out)["rows"][0]["shaves"] == 500

    def test_history_contains_lists_brand_candidates(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "soap_makers",
                "--name",
                "stirling",
                "--contains",
                "--last",
                "3",
            ],
        )
        assert code == 1
        assert "ambiguous name" in err
        assert "Stirling Soap Co." in err
        assert "Stirling East" in err

    def test_history_composite_key_errors_loudly(self, data_dir, capsys):
        # rows sharing a user across blades cannot be resolved to one item
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "highest_use_count_per_blade",
                "--name",
                "annuser",
                "--last",
                "1",
            ],
        )
        assert code == 1
        assert "ambiguous" in err

    def test_history_min_shaves_errors_on_shavesless_category(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "history",
                "--category",
                "brand_diversity",
                "--name",
                "Stirling Soap Co.",
                "--last",
                "1",
                "--min-shaves",
                "5",
            ],
        )
        assert code == 1
        assert "shaves" in err


class TestRanking:
    """ranking: the per-category sort keys behind every rendered rank."""

    def test_ranking_lists_sort_rules_for_known_categories(self, capsys):
        code, out, _ = run(capsys, ["ranking"])
        assert code == 0
        # product tables: shaves desc, then unique_users desc
        assert "shaves desc, unique_users desc" in out
        # top shaver: missed_days asc wins over raw shaves
        assert "missed_days asc, shaves desc" in out
        # brand diversity: unique_soaps first, alphabetical brand within
        assert "unique_soaps desc, brand asc" in out
        # rank styles are stated
        assert "competition" in out
        assert "sequential" in out
        # dict categories are listed but not ranked
        assert "sample_usage_metrics" in out

    def test_ranking_category_filter(self, capsys):
        code, out, _ = run(capsys, ["ranking", "--category", "users"])
        assert code == 0
        assert "missed_days asc, shaves desc" in out
        assert "razors" not in out.split("\n", 1)[0]

    def test_ranking_unknown_category_errors(self, capsys):
        code, _, err = run(capsys, ["ranking", "--category", "nope"])
        assert code == 1
        assert "valid categories" in err

    def test_ranking_json(self, capsys):
        code, out, _ = run(capsys, ["--json", "ranking", "--category", "razors"])
        assert code == 0
        doc = json.loads(out)
        entry = doc["categories"]["razors"]
        assert entry["sort"] == [["shaves", "desc"], ["unique_users", "desc"]]
        assert entry["ranks"] == "competition"


class TestMetrics:
    """metrics: dict-shaped metric categories and cross-month meta comparison."""

    def test_metrics_month_renders_dict_categories(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "metrics", "--month", "2026-01"])
        assert code == 0
        assert "sample_usage_metrics" in out
        assert "total_samples" in out

    def test_metrics_month_json(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "--json", "metrics", "--month", "2026-01"]
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["period"] == "2026-01"
        assert doc["metrics"]["sample_usage_metrics"]["total_samples"] == 0

    def test_metrics_missing_month_errors(self, tmp_path, capsys):
        (tmp_path / "aggregated").mkdir()
        code, _, err = run(capsys, ["--data-dir", str(tmp_path), "metrics", "--month", "2025-01"])
        assert code == 1
        assert "file not found" in err

    def test_metrics_range_compares_meta(self, tmp_path, capsys):
        agg = tmp_path / "aggregated"
        agg.mkdir()
        inventory = (("2026-05", 531, 139), ("2026-06", 856, 215), ("2026-07", 526, 135))
        for month, soaps, brands in inventory:
            make_month_file(
                agg / f"{month}.json",
                month,
                razors=[],
                soaps=[],
                meta_extra={"unique_soaps": soaps, "unique_brands": brands, "total_samples": 3},
            )
        code, out, _ = run(
            capsys, ["--data-dir", str(tmp_path), "metrics", "--months", "2026-05:2026-07"]
        )
        assert code == 0
        for month, _, _ in inventory:
            assert month in out
        assert "unique_soaps" in out
        assert "unique_brands" in out
        assert "total_shaves" in out

    def test_metrics_range_skips_missing_months(self, tmp_path, capsys):
        agg = tmp_path / "aggregated"
        agg.mkdir()
        make_month_file(agg / "2026-05.json", "2026-05", razors=[], soaps=[])
        code, out, _ = run(
            capsys, ["--data-dir", str(tmp_path), "metrics", "--months", "2026-05:2026-07"]
        )
        assert code == 0
        assert "skipped" in out
        assert "2026-06" in out and "2026-07" in out

    def test_metrics_requires_exactly_one_period(self):
        # no period at all -> argparse usage error
        with pytest.raises(SystemExit) as exc:
            main(["metrics"])
        assert exc.value.code == 2
        # conflicting periods -> argparse usage error too
        with pytest.raises(SystemExit) as exc:
            main(["metrics", "--month", "2026-01", "--months", "2026-01:2026-02"])
        assert exc.value.code == 2


@pytest.fixture
def users_month(tmp_path):
    """A month with six user rows spanning missed_days/shaves values."""
    agg = tmp_path / "aggregated"
    agg.mkdir()
    users = [
        {"rank": 1, "user": "bob", "shaves": 40, "missed_days": 0},
        {"rank": 2, "user": "alice", "shaves": 31, "missed_days": 0},
        {"rank": 3, "user": "dave", "shaves": 31, "missed_days": 2},
        {"rank": 4, "user": "carol", "shaves": 28, "missed_days": 1},
        {"rank": 5, "user": "erin", "shaves": 20, "missed_days": 0},
        {"rank": 6, "user": "frank", "shaves": 10, "missed_days": 3},
    ]
    make_month_file(agg / "2026-04.json", "2026-04", razors=[], soaps=[], extra={"users": users})
    return tmp_path


class TestCount:
    """count: rows in a category matching AND-ed --where field conditions."""

    def test_count_where_equality_and_threshold(self, users_month, capsys):
        # the perfect-attendance probe: missed_days=0 AND shaves>=31 -> bob, alice
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(users_month),
                "count",
                "--month",
                "2026-04",
                "--category",
                "users",
                "--where",
                "missed_days=0",
                "--where",
                "shaves>=31",
            ],
        )
        assert code == 0
        assert "2 of 6 rows match" in out
        assert "missed_days=0" in out
        assert "shaves>=31" in out

    def test_count_numeric_equality(self, users_month, capsys):
        # shaves=31 -> alice, dave
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(users_month),
                "count",
                "--month",
                "2026-04",
                "--category",
                "users",
                "--where",
                "shaves=31",
            ],
        )
        assert code == 0
        assert "2 of 6 rows match" in out

    def test_count_inequality(self, users_month, capsys):
        # missed_days>=1 -> carol, dave, frank
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(users_month),
                "count",
                "--month",
                "2026-04",
                "--category",
                "users",
                "--where",
                "missed_days>=1",
            ],
        )
        assert code == 0
        assert "3 of 6 rows match" in out

    def test_count_string_equality_is_case_insensitive(self, data_dir, capsys):
        # both highest_use_count_per_blade rows carry format=DE
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "highest_use_count_per_blade",
                "--where",
                "format=de",
            ],
        )
        assert code == 0
        assert "2 of 2 rows match" in out

    def test_count_float_equality(self, data_dir, capsys):
        # pair_a and pair_b share hhi=0.8 in the 2026-01 diversity rows
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "user_soap_brand_scent_diversity",
                "--where",
                "hhi=0.8",
            ],
        )
        assert code == 0
        assert "2 of 6 rows match" in out

    def test_count_no_where_counts_all_rows(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "count", "--month", "2026-01", "--category", "razors"],
        )
        assert code == 0
        assert "2 of 2 rows" in out
        assert "match" not in out

    def test_count_annual(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "count", "--year", "2025", "--category", "razors"]
        )
        assert code == 0
        assert "1 of 1 rows" in out

    def test_count_json(self, users_month, capsys):
        code, out, _ = run(
            capsys,
            [
                "--json",
                "--data-dir",
                str(users_month),
                "count",
                "--month",
                "2026-04",
                "--category",
                "users",
                "--where",
                "missed_days=0",
                "--where",
                "shaves>=31",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["period"] == "2026-04"
        assert doc["category"] == "users"
        assert doc["where"] == ["missed_days=0", "shaves>=31"]
        assert doc["count"] == 2
        assert doc["total"] == 6

    def test_count_unknown_field_lists_valid_fields(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "users",
                "--where",
                "missed_day=0",
            ],
        )
        assert code == 1
        assert "unknown field" in err
        assert "missed_days" in err

    def test_count_invalid_where_syntax(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "users",
                "--where",
                "missed_days",
            ],
        )
        assert code == 1
        assert "invalid --where" in err

    def test_count_comparison_with_string_value_errors(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "highest_use_count_per_blade",
                "--where",
                "format>=DE",
            ],
        )
        assert code == 1
        assert "numeric" in err

    def test_count_unknown_category(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            ["--data-dir", str(data_dir), "count", "--month", "2026-01", "--category", "wands"],
        )
        assert code == 1
        assert "unknown category" in err

    def test_count_non_list_category(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "count",
                "--month",
                "2026-01",
                "--category",
                "sample_usage_metrics",
            ],
        )
        assert code == 1
        assert "not a ranked list" in err
