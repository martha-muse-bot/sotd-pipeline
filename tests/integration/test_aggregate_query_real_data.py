# pylint: disable=redefined-outer-name

"""
Production-data sweep for the aggregate_query CLI.

Guards the key-field derivation against report-table drift: hardware and
software report tables span name/brand/user/format/plate/... identity fields,
and monthly files differ from annual ones (the annual engine re-keys maker
tables to name). Every category present in the real aggregated data must
render through ``top`` with a non-empty key column, and drafter-relevant
categories must resolve their current top item through ``history``.

Skipped when no local aggregated data exists (``data/aggregated/*.json`` is
gitignored); runs on machines with data via ``make test`` or
``make test-production``.
"""

import io
import json
from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from sotd.report.tools.aggregate_query import KEY_FIELD_PRIORITY, _CATEGORY_RANKING, main

DATA_DIR = Path(__file__).resolve().parents[2] / "data"

_monthly_files = sorted((DATA_DIR / "aggregated").glob("????-??.json"))
_annual_files = sorted((DATA_DIR / "aggregated" / "annual").glob("????.json"))

pytestmark = [
    pytest.mark.production,
    pytest.mark.skipif(not _monthly_files, reason="no local aggregated data"),
]

month_label = _monthly_files[-1].stem if _monthly_files else None
month_categories = (
    _categories := (
        sorted(
            key
            for key, value in json.loads(_monthly_files[-1].read_text(encoding="utf-8"))[
                "data"
            ].items()
            if isinstance(value, list) and value and isinstance(value[0], dict)
        )
        if _monthly_files
        else []
    )
)

annual_path = _annual_files[-1] if _annual_files else None
year_label = annual_path.stem if annual_path else None
annual_categories = (
    sorted(
        key
        for key, value in json.loads(annual_path.read_text(encoding="utf-8")).items()
        if isinstance(value, list) and value and isinstance(value[0], dict)
    )
    if annual_path
    else []
)

# Categories the observations-drafter resolves through history; all unique-keyed.
HISTORY_CATEGORIES = (
    "razors",
    "soaps",
    "soap_makers",
    "brand_diversity",
    "users",
    "razor_formats",
    "brush_fibers",
    "brush_knot_sizes",
    "super_speed_variants",
)


def _run(argv):
    """Run the CLI in-process, capturing stdout/stderr, and return (code, out, err)."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class TestRealDataTop:
    """Every list category renders through text mode with a real key column."""

    @pytest.mark.parametrize("category", month_categories)
    def test_monthly_top_renders_key_column(self, category, capsys):
        code, out, _ = _run(["top", "--month", month_label, "--category", category, "--top", "3"])
        assert code == 0
        for line in out.splitlines()[1:]:
            assert line.split()[1], f"empty key cell in {category}: {line!r}"

    @pytest.mark.parametrize("category", annual_categories)
    def test_annual_top_renders_key_column(self, category, capsys):
        code, out, _ = _run(["top", "--year", year_label, "--category", category, "--top", "3"])
        assert code == 0
        for line in out.splitlines()[1:]:
            assert line.split()[1], f"empty key cell in {category}: {line!r}"


class TestRealDataHistory:
    """History resolves the current top item by its derived key field."""

    @pytest.mark.parametrize("category", [c for c in month_categories if c in HISTORY_CATEGORIES])
    def test_history_resolves_month_top_item(self, category, capsys):
        _, jout, _ = _run(
            ["--json", "top", "--month", month_label, "--category", category, "--top", "1"]
        )
        entry = json.loads(jout)[0]
        key = next(f for f in KEY_FIELD_PRIORITY if f in entry)
        _, jout, _ = _run(
            [
                "--json",
                "history",
                "--category",
                category,
                "--name",
                str(entry[key]),
                "--last",
                "1",
                "--end",
                month_label,
            ]
        )
        row = json.loads(jout)["rows"][0]
        for field, value in entry.items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                assert row.get(field) == value, f"{category} {field}: {row.get(field)} != {value}"


class TestRealDataCompositeKeys:
    """Composite categories refuse history loudly instead of picking an arbitrary row."""

    def test_highest_use_count_per_blade_errors_loudly(self, capsys):
        doc = json.loads(_monthly_files[-1].read_text(encoding="utf-8"))
        entries = doc["data"]["highest_use_count_per_blade"]
        counts = Counter(str(e["user"]) for e in entries)
        duplicated = next(user for user, n in counts.items() if n > 1)
        code, _, err = _run(
            [
                "history",
                "--category",
                "highest_use_count_per_blade",
                "--name",
                duplicated,
                "--last",
                "1",
                "--end",
                month_label,
            ]
        )
        assert code == 1
        assert "ambiguous" in err


def _respects_spec(rows, spec):
    """True when consecutive rows never improve along the first differing spec field."""
    for a, b in zip(rows, rows[1:]):
        for field, direction in spec:
            va, vb = a.get(field), b.get(field)
            if va is None:
                va = 0
            if vb is None:
                vb = 0
            if va == vb:
                continue
            if direction == "desc":
                return va >= vb
            return va <= vb
    return True


class TestRealDataRankingOrder:
    """Real row order must satisfy the CLI's sort-key registry (drift guard).

    The aggregate phase encodes table order across several sites (base
    tie_columns, per-class overrides, standalone aggregators); this pins the
    ``ranking`` registry to the actual outcome so the map cannot drift from
    the code in either direction.
    """

    @staticmethod
    def _rows(path, container_key, category):
        doc = json.loads(path.read_text(encoding="utf-8"))
        container = doc.get(container_key, doc)
        return container.get(category)

    def test_monthly_categories_covered(self):
        unregistered = [c for c in month_categories if c not in _CATEGORY_RANKING]
        assert (
            not unregistered
        ), f"categories missing from aggregate_query _CATEGORY_RANKING: {unregistered}"

    def test_annual_categories_covered(self):
        unregistered = [c for c in annual_categories if c not in _CATEGORY_RANKING]
        assert (
            not unregistered
        ), f"categories missing from aggregate_query _CATEGORY_RANKING: {unregistered}"

    @pytest.mark.parametrize("category", [c for c in month_categories if c in _CATEGORY_RANKING])
    def test_monthly_order_matches_registry(self, category):
        rows = self._rows(_monthly_files[-1], "data", category)
        if rows is None:
            pytest.skip(f"{category} absent from {month_label}")
        assert _respects_spec(rows, _CATEGORY_RANKING[category][1]), (
            f"{month_label} {category}: row order violates the registered sort "
            f"{_CATEGORY_RANKING[category]}"
        )

    @pytest.mark.parametrize("category", [c for c in annual_categories if c in _CATEGORY_RANKING])
    def test_annual_order_matches_registry(self, category):
        rows = self._rows(annual_path, "data", category)
        if rows is None:
            pytest.skip(f"{category} absent from {year_label}")
        assert _respects_spec(rows, _CATEGORY_RANKING[category][1]), (
            f"{year_label} {category}: row order violates the registered sort "
            f"{_CATEGORY_RANKING[category]}"
        )
