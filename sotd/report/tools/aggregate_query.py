"""Point-query CLI for aggregated SOTD data.

Answers the deterministic questions the observations-drafter agent (and shell
debugging) need without loading whole 500-700 KB JSON files: month meta,
top-N rows of a category, rank history for a single item across months
or years, and row counts under field conditions. All numbers come from
``data/aggregated/`` — the machine truth.

Monthly files (``data/aggregated/YYYY-MM.json``) wrap categories in a
``data`` key with a ``meta`` block; annual files
(``data/aggregated/annual/YYYY.json``) put categories at the top level with
``metadata``. Both shapes are normalized on load.

Each category's rows are matched and rendered by their identity field —
name, brand, user, plate, format, ... — derived from the rows themselves,
so every report table works without a per-category lookup table. Unknown
shapes fail loudly instead of silently rendering blanks or missing matches.

Exit codes: 0 success, 1 on query errors (unknown category, ambiguous name,
missing month).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

HUMAN_DEFAULT_TOP = 10

# A category's identity field is the first of these present across its rows.
KEY_FIELD_PRIORITY = (
    "name",
    "brand",
    "user",
    "format",
    "fiber",
    "handle_maker",
    "knot_size_mm",
    "plate",
    "gap",
    "grind",
    "point",
    "width",
    "super_speed_variant",
    "use_count",
)

# Numeric columns rendered first, in this order; the rest follow sorted.
CANONICAL_NUMERICS = ("shaves", "unique_users", "unique_soaps")

# Meta keys rendered first, in this order, for cross-month inventory tables.
META_CANONICAL = (
    "total_shaves",
    "unique_shavers",
    "unique_soaps",
    "unique_brands",
    "unique_razors",
    "unique_blades",
    "unique_brushes",
    "total_samples",
)

# The sort keys behind every rendered rank, audited from the aggregate phase
# (base ``tie_columns``, per-aggregator ``tie_columns``/``_sort_and_rank``
# overrides, and the standalone aggregators that never touch the base class).
# Style ``competition`` shares a rank across full ties (1, 2, 2, 4) and orders
# them alphabetically; ``sequential`` numbers rows 1..N with no tie sharing.
# The production sweep (tests/integration/test_aggregate_query_real_data.py)
# verifies real file row order against this registry, so editing one side
# without the other fails a test.
SortSpec = tuple[tuple[str, str], ...]

_CATEGORY_RANKING: dict[str, tuple[str, tuple[tuple[str, str], ...]]] = {
    # Core product tables + makers/plates/straights/formats: the base sort.
    "razors": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "blades": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "brushes": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "soaps": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "soap_sample_brands": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "soap_sample_brand_scents": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "razor_manufacturers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "blade_manufacturers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "soap_makers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "razor_formats": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "brush_handle_makers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "brush_knot_makers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "brush_fibers": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "brush_knot_sizes": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "blackbird_plates": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "christopher_bradley_plates": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "game_changer_plates": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "super_speed_variants": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "straight_widths": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "straight_grinds": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "straight_points": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "razor_blade_combinations": ("competition", (("shaves", "desc"), ("unique_users", "desc"))),
    "highest_use_count_per_blade": ("competition", (("uses", "desc"),)),
    # brand_diversity ties are broken alphabetically, not by shaves.
    "brand_diversity": ("competition", (("unique_soaps", "desc"), ("brand", "asc"))),
    "user_soap_brand_diversity": ("competition", (("unique_brands", "desc"), ("shaves", "desc"))),
    "user_soap_brand_scent_diversity": (
        "competition",
        (("unique_combinations", "desc"), ("shaves", "desc")),
    ),
    "user_single_use_soaps": ("competition", (("single_use_soaps", "desc"), ("shaves", "desc"))),
    "users": ("competition", (("missed_days", "asc"), ("shaves", "desc"))),
    # Sequential ranks (1, 2, 3 — no sharing).
    "user_blade_diversity": ("sequential", (("unique_blades", "desc"), ("shaves", "desc"))),
    "user_brush_diversity": ("sequential", (("unique_brushes", "desc"), ("shaves", "desc"))),
    "user_razor_diversity": ("sequential", (("unique_razors", "desc"), ("shaves", "desc"))),
    "soap_mashup_users": ("sequential", (("shaves", "desc"), ("unique_users", "desc"))),
    "soap_sample_users": ("sequential", (("shaves", "desc"), ("unique_users", "desc"))),
    "brush_fiber_users": (
        "sequential within fiber",
        (("fiber", "asc"), ("shaves", "desc"), ("unique_users", "desc")),
    ),
    "razor_format_users": (
        "sequential within format",
        (("format", "asc"), ("shaves", "desc"), ("unique_users", "desc")),
    ),
    "blade_usage_distribution": ("sequential", (("use_count", "asc"),)),
    # Dict-shaped metric blocks, not ranked lists.
    "sample_usage_metrics": ("dict", ()),
    "mashup_usage_metrics": ("dict", ()),
}


class QueryError(Exception):
    """Raised for deterministic, user-facing query failures."""


def default_data_dir() -> str:
    """Return the artifact root from the environment or the repo default."""
    return os.environ.get("SOTD_DATA_DIR", "data")


def build_parser() -> argparse.ArgumentParser:
    """Build the aggregate_query argument parser."""
    parser = argparse.ArgumentParser(
        prog="aggregate_query",
        description="Query data/aggregated JSON files (meta, top-N, rank history, counts).",
    )
    parser.add_argument("--data-dir", default=default_data_dir(), help="Artifact root directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of aligned text")
    sub = parser.add_subparsers(dest="command", required=True)

    meta = sub.add_parser("meta", help="Print the meta/metadata block for a month or year")
    _add_period_args(meta)

    schema = sub.add_parser("schema", help="List categories with row counts and entry fields")
    _add_period_args(schema)

    top = sub.add_parser("top", help="Print the top N rows of a category")
    _add_period_args(top)
    top.add_argument("--category", required=True, help="Category key (e.g. razors, soaps)")
    top.add_argument(
        "--top", type=int, default=HUMAN_DEFAULT_TOP, help="Number of rows (default 10)"
    )
    top.add_argument(
        "--min-shaves",
        type=int,
        default=0,
        help="Exclude entries with fewer shaves (use to match report-table thresholds)",
    )
    top.add_argument(
        "--sort",
        choices=("hhi",),
        help=(
            "Re-sort as the Most Boring Shaver view (hhi desc, shaves desc, competition "
            "ranks recomputed); the category must carry an hhi field"
        ),
    )

    count = sub.add_parser(
        "count", help="Count rows in a category, optionally matching field conditions"
    )
    _add_period_args(count)
    count.add_argument("--category", required=True, help="Category key (e.g. razors, soaps)")
    count.add_argument(
        "--where",
        action="append",
        default=None,
        metavar="FIELD=VALUE",
        help=(
            "Row condition (repeatable, AND-ed): FIELD=VALUE, FIELD>=VALUE, "
            "FIELD<=VALUE, FIELD>VALUE, or FIELD<VALUE. Numeric values compare "
            "numerically; strings match case-insensitively on = only"
        ),
    )

    history = sub.add_parser(
        "history", help="Rank history for one item (or a multi-item matrix) across months or years"
    )
    history.add_argument("--category", required=True, help="Category key (e.g. razors, soaps)")
    history.add_argument(
        "--name",
        required=True,
        action="append",
        help=(
            "Item identity — the category's key field (name, brand, user, ...); "
            "case-insensitive exact match. Repeat for a side-by-side matrix"
        ),
    )
    history.add_argument(
        "--contains", action="store_true", help="Match by case-insensitive substring"
    )
    history.add_argument("--last", type=int, help="Most recent N monthly files")
    history.add_argument("--start", help="Range start month (YYYY-MM)")
    history.add_argument("--end", help="Range end month (YYYY-MM, inclusive)")
    history.add_argument("--year", help="Single annual file (YYYY)")
    history.add_argument(
        "--min-shaves",
        type=int,
        default=0,
        help="Only count months where the item clears this threshold",
    )

    ranking = sub.add_parser(
        "ranking", help="Per-category sort keys behind every rendered rank (period-independent)"
    )
    ranking.add_argument("--category", help="Only this category (e.g. razors, users)")

    metrics = sub.add_parser(
        "metrics",
        help="Dict-shaped metric categories for a period, or a cross-month meta comparison",
    )
    period = metrics.add_mutually_exclusive_group(required=True)
    period.add_argument("--month", help="Monthly file (YYYY-MM): print its dict metric categories")
    period.add_argument("--year", help="Annual file (YYYY): print its dict metric categories")
    period.add_argument(
        "--months", help="Range YYYY-MM:YYYY-MM — meta inventory table (the June-anomaly query)"
    )

    return parser


def _add_period_args(parser: argparse.ArgumentParser) -> None:
    """Add the --month / --year period selectors shared by meta and top."""
    period = parser.add_mutually_exclusive_group(required=True)
    period.add_argument("--month", help="Monthly file (YYYY-MM)")
    period.add_argument("--year", help="Annual file (YYYY)")


def _monthly_paths(data_dir: Path) -> list[Path]:
    """Return sorted monthly aggregated file paths."""
    return sorted((data_dir / "aggregated").glob("????-??.json"))


def _annual_path(data_dir: Path, year: str) -> Path:
    """Return the annual aggregated file path for a year."""
    return data_dir / "aggregated" / "annual" / f"{year}.json"


def _load(path: Path) -> dict[str, Any]:
    """Load a JSON document, raising QueryError if missing."""
    try:
        with path.open(encoding="utf-8") as handle:
            doc = json.load(handle)
    except FileNotFoundError as exc:
        raise QueryError(f"file not found: {path}") from exc
    except json.JSONDecodeError as exc:
        raise QueryError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(doc, dict):
        raise QueryError(f"unexpected structure in {path}")
    return doc


def _category_container(doc: dict[str, Any]) -> dict[str, Any]:
    """Return the dict holding category keys for either file shape."""
    data = doc.get("data")
    return data if isinstance(data, dict) else doc


def _category_list(doc: dict[str, Any], category: str) -> list[dict[str, Any]]:
    """Return the ranked list for a category, or raise QueryError."""
    container = _category_container(doc)
    if category not in container:
        valid = sorted(k for k, v in container.items() if isinstance(v, list))
        raise QueryError(f"unknown category {category!r}; valid categories: {', '.join(valid)}")
    value = container[category]
    if not isinstance(value, list):
        raise QueryError(f"category {category!r} is not a ranked list")
    return [entry for entry in value if isinstance(entry, dict)]


def _resolve_period(args: argparse.Namespace, data_dir: Path) -> tuple[Path, bool]:
    """Return (path, is_annual) for the selected period."""
    if args.month:
        return data_dir / "aggregated" / f"{args.month}.json", False
    return _annual_path(data_dir, args.year), True


def _select_history_files(
    args: argparse.Namespace, data_dir: Path
) -> tuple[list[tuple[str, Path]], bool, list[str]]:
    """Return (labelled paths, is_annual, missing labels) for a history query.

    Range mode enumerates calendar months between --start and --end so gaps
    surface as skipped labels instead of silently compressing the history.
    """
    if args.year:
        if args.last is not None or args.start or args.end:
            raise QueryError("--year cannot be combined with --last/--start/--end")
        return [(args.year, _annual_path(data_dir, args.year))], True, []
    if args.last is None and not (args.start or args.end):
        raise QueryError("history needs --last N (optionally with --start/--end), or --year")
    if args.last is not None and args.last < 1:
        raise QueryError("--last must be a positive integer")
    for value in (args.start, args.end):
        if value is not None and not re.match(r"^\d{4}-\d{2}$", value):
            raise QueryError(f"invalid month {value!r}; expected YYYY-MM")
    if args.start and args.end and args.start > args.end:
        raise QueryError("--start must not be after --end")
    if args.start and args.end:
        labels = _month_range_labels(args.start, args.end)
    else:
        existing = _monthly_paths(data_dir)
        if args.end:
            existing = [p for p in existing if p.stem <= args.end]
        if args.start:
            existing = [p for p in existing if p.stem >= args.start]
        if args.last is not None:
            existing = existing[-args.last :]
        labels = [p.stem for p in existing]
    month_dir = data_dir / "aggregated"
    paths = [(label, month_dir / f"{label}.json") for label in labels]
    missing = [label for label, path in paths if not path.exists()]
    return paths, False, missing


def _month_range_labels(start: str, end: str) -> list[str]:
    """Return every YYYY-MM label between start and end inclusive."""
    start_year, start_month = int(start[:4]), int(start[5:7])
    end_year, end_month = int(end[:4]), int(end[5:7])
    labels: list[str] = []
    year, month = start_year, start_month
    while (year, month) <= (end_year, end_month):
        labels.append(f"{year:04d}-{month:02d}")
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    return labels


def _find_entry(
    entries: list[dict[str, Any]], name: str, contains: bool, key_field: str, category: str
) -> dict[str, Any] | None:
    """Match one entry by its key field; raise QueryError on ambiguous matches."""
    if contains:
        matches = [e for e in entries if name.casefold() in str(e.get(key_field, "")).casefold()]
        if len(matches) > 1:
            values = ", ".join(sorted(str(e.get(key_field, "")) for e in matches))
            raise QueryError(f"ambiguous name {name!r} with --contains; candidates: {values}")
        return matches[0] if matches else None
    target = name.casefold()
    matches = [e for e in entries if str(e.get(key_field, "")).casefold() == target]
    if len(matches) > 1:
        raise QueryError(
            f"ambiguous name {name!r} in {category!r}: {len(matches)} rows share "
            f"{key_field} {name!r}; history needs a unique key"
        )
    return matches[0] if matches else None


def query_schema(args: argparse.Namespace) -> dict[str, Any]:
    """Return per-category row counts and entry-field unions for the period."""
    data_dir = Path(args.data_dir)
    path, _ = _resolve_period(args, data_dir)
    doc = _load(path)
    container = _category_container(doc)
    categories: dict[str, Any] = {}
    for key in sorted(container):
        value = container[key]
        if isinstance(value, list):
            dicts = [entry for entry in value if isinstance(entry, dict)]
            fields = sorted({field for entry in dicts for field in entry})
            categories[key] = {"type": "list", "rows": len(value), "fields": fields}
        elif isinstance(value, dict):
            categories[key] = {"type": "dict", "keys": sorted(value)}
        else:
            categories[key] = {"type": type(value).__name__}
    return {"file": str(path), "period": args.month or args.year, "categories": categories}


def query_meta(args: argparse.Namespace) -> dict[str, Any]:
    """Return the meta/metadata block for the selected period."""
    data_dir = Path(args.data_dir)
    path, is_annual = _resolve_period(args, data_dir)
    doc = _load(path)
    key = "metadata" if is_annual else "meta"
    block = doc.get(key)
    if not isinstance(block, dict):
        raise QueryError(f"{key} block missing in {path}")
    return {k: block[k] for k in sorted(block)}


def query_top(args: argparse.Namespace) -> list[dict[str, Any]]:
    """Return the top rows of a category for the selected period."""
    data_dir = Path(args.data_dir)
    path, _ = _resolve_period(args, data_dir)
    doc = _load(path)
    entries = _category_list(doc, args.category)
    if args.min_shaves > 0:
        numerics = _numeric_fields(entries)
        if entries and "shaves" not in numerics:
            raise QueryError(
                f"category {args.category!r} has no shaves field to filter on; "
                f"numeric fields: {', '.join(numerics) or '(none)'}"
            )
        entries = [e for e in entries if _entry_int(e, "shaves") >= args.min_shaves]
    if args.sort == "hhi":
        entries = _sort_by_hhi(entries, args.category)
    return entries[: max(args.top, 0)]


def _entry_float(entry: dict[str, Any], key: str) -> float:
    """Return an entry's float field, tolerating missing or non-numeric values."""
    value = entry.get(key, 0.0)
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else 0.0


def _sort_by_hhi(entries: list[dict[str, Any]], category: str) -> list[dict[str, Any]]:
    """Re-sort entries as the report's Most Boring Shaver table and recompute ranks.

    Mirrors table_generator's user-soap-brand-scent-diversity hhi view: filter
    first (done by --min-shaves), sort hhi desc then shaves desc (file order —
    the canonical unique_combinations ranking — breaks residual ties, matching
    the report's stable sort), then competition-rank on the full sort key so
    equal (hhi, shaves) rows share a rank.
    """
    if entries and not any(
        isinstance(e.get("hhi"), (int, float)) and not isinstance(e.get("hhi"), bool)
        for e in entries
    ):
        raise QueryError(
            f"category {category!r} has no hhi field to sort on; "
            f"numeric fields: {', '.join(_numeric_fields(entries)) or '(none)'}"
        )
    ordered = sorted(
        entries,
        key=lambda e: (-_entry_float(e, "hhi"), -_entry_int(e, "shaves")),
    )
    previous: tuple[float, int] | None = None
    rank = 0
    for position, entry in enumerate(ordered, start=1):
        key = (_entry_float(entry, "hhi"), _entry_int(entry, "shaves"))
        if key != previous:
            rank = position
            previous = key
        entry["rank"] = rank
    return ordered


def query_ranking(args: argparse.Namespace) -> dict[str, Any]:
    """Return the sort-key registry, optionally narrowed to one category."""
    if args.category:
        if args.category not in _CATEGORY_RANKING:
            valid = ", ".join(sorted(_CATEGORY_RANKING))
            raise QueryError(f"unknown category {args.category!r}; valid categories: {valid}")
        selected = {args.category: _CATEGORY_RANKING[args.category]}
    else:
        selected = _CATEGORY_RANKING
    categories = {
        key: {"ranks": style, "sort": [list(field_dir) for field_dir in spec]}
        for key, (style, spec) in selected.items()
    }
    return {"categories": categories}


def query_metrics(args: argparse.Namespace) -> dict[str, Any]:
    """Return dict metric categories for a period, or a cross-month meta table."""
    data_dir = Path(args.data_dir)
    if args.months:
        return _query_metrics_range(args, data_dir)
    path, _ = _resolve_period(args, data_dir)
    doc = _load(path)
    metrics = {
        key: value for key, value in _category_container(doc).items() if isinstance(value, dict)
    }
    if not metrics:
        raise QueryError(f"no dict-shaped metric categories in {path}")
    return {"file": str(path), "period": args.month or args.year, "metrics": metrics}


def _query_metrics_range(args: argparse.Namespace, data_dir: Path) -> dict[str, Any]:
    """Compare numeric meta blocks across a calendar month range."""
    if not re.match(r"^\d{4}-\d{2}:\d{4}-\d{2}$", args.months):
        raise QueryError(f"invalid range {args.months!r}; expected YYYY-MM:YYYY-MM")
    start, end = args.months.split(":")
    if start > end:
        raise QueryError("--months start must not be after end")
    rows: list[dict[str, Any]] = []
    skipped: list[str] = []
    for label in _month_range_labels(start, end):
        path = data_dir / "aggregated" / f"{label}.json"
        if not path.exists():
            skipped.append(label)
            continue
        doc = _load(path)
        meta = doc.get("meta")
        if not isinstance(meta, dict):
            raise QueryError(f"meta block missing in {path}")
        rows.append(
            {
                "period": label,
                **{
                    k: v
                    for k, v in meta.items()
                    if isinstance(v, (int, float)) and not isinstance(v, bool)
                },
            }
        )
    if not rows:
        raise QueryError("no aggregated files match the selected period")
    return {"rows": rows, "skipped": skipped}


# Two-character operators must be checked before their one-character prefixes.
_WHERE_OPERATORS = (">=", "<=", ">", "<", "=")


def _parse_where(spec: str, fields: set[str]) -> tuple[str, str, int | float | str]:
    """Parse one --where condition into (field, operator, value); raise QueryError
    on missing operators, unknown fields, or comparisons on non-numeric values."""
    for op in _WHERE_OPERATORS:
        if op in spec:
            field, raw = spec.split(op, 1)
            break
    else:
        raise QueryError(
            f'invalid --where "{spec}"; expected FIELD=VALUE, FIELD>=VALUE, '
            "FIELD<=VALUE, FIELD>VALUE, or FIELD<VALUE"
        )
    field, raw = field.strip(), raw.strip()
    if not field or not raw:
        raise QueryError(f'invalid --where "{spec}"; field and value must both be non-empty')
    if field not in fields:
        raise QueryError(
            f"unknown field {field!r} in --where; fields: {', '.join(sorted(fields)) or '(none)'}"
        )
    try:
        value: int | float | str = int(raw)
    except ValueError:
        try:
            value = float(raw)
        except ValueError:
            value = raw
            if op != "=":
                raise QueryError(
                    f'invalid --where "{spec}"; comparison operators need a numeric value'
                ) from None
    return field, op, value


def _row_matches(entry: dict[str, Any], field: str, op: str, value: int | float | str) -> bool:
    """Return whether one row satisfies one --where condition.

    Rows missing the field, or carrying a value of the wrong type, simply do
    not match — unlike the tolerant _entry_int/_entry_float readers, a missing
    value must never compare equal to zero.
    """
    actual = entry.get(field)
    if isinstance(value, (int, float)):
        if not isinstance(actual, (int, float)) or isinstance(actual, bool):
            return False
        if op == "=":
            return actual == value
        if op == ">=":
            return actual >= value
        if op == "<=":
            return actual <= value
        if op == ">":
            return actual > value
        return actual < value
    return isinstance(actual, str) and actual.casefold() == value.casefold()


def query_count(args: argparse.Namespace) -> dict[str, Any]:
    """Return row counts for a category, optionally restricted by --where conditions."""
    data_dir = Path(args.data_dir)
    path, _ = _resolve_period(args, data_dir)
    doc = _load(path)
    entries = _category_list(doc, args.category)
    fields = {field for entry in entries for field in entry}
    conditions = [_parse_where(spec, fields) for spec in (args.where or [])]
    matched = [
        entry
        for entry in entries
        if all(_row_matches(entry, field, op, value) for field, op, value in conditions)
    ]
    return {
        "file": str(path),
        "period": args.month or args.year,
        "category": args.category,
        "where": [f"{field}{op}{value}" for field, op, value in conditions],
        "count": len(matched),
        "total": len(entries),
    }


def _entry_int(entry: dict[str, Any], key: str) -> int:
    """Return an entry's integer field, tolerating missing or non-int values."""
    value = entry.get(key, 0)
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _key_field(entries: list[dict[str, Any]], category: str) -> str:
    """Return a category's identity field (name, brand, user, ...)."""
    if not entries:
        return "name"
    present: set[str] = set()
    for entry in entries:
        present.update(entry)
    for candidate in KEY_FIELD_PRIORITY:
        if candidate in present:
            return candidate
    raise QueryError(
        f"category {category!r} has no recognizable key field; "
        f"entry fields: {', '.join(sorted(present))}"
    )


def _numeric_fields(entries: list[dict[str, Any]]) -> list[str]:
    """Return numeric fields present across entries (rank excluded), canonical first."""
    union: set[str] = set()
    for entry in entries:
        union.update(
            field
            for field, value in entry.items()
            if isinstance(value, (int, float)) and not isinstance(value, bool)
        )
    union.discard("rank")
    ordered = [field for field in CANONICAL_NUMERICS if field in union]
    ordered += sorted(union - set(ordered))
    return ordered


def _format_cell(value: Any) -> str:
    """Format a numeric cell: '-' when missing, thousands separators for ints."""
    if value is None:
        return "-"
    if isinstance(value, int) and not isinstance(value, bool):
        return f"{value:,}"
    return str(value)


def query_history(args: argparse.Namespace) -> dict[str, Any]:
    """Return per-month (or annual) rank rows for one item, or a multi-item matrix."""
    data_dir = Path(args.data_dir)
    labelled, _is_annual, missing = _select_history_files(args, data_dir)
    if not labelled:
        raise QueryError("no aggregated files match the selected period")
    names: list[str] = args.name
    rows: list[dict[str, Any]] = []
    skipped: list[str] = list(missing)
    for label, path in labelled:
        if not path.exists():
            continue
        doc = _load(path)
        entries = _category_list(doc, args.category)
        key_field = _key_field(entries, args.category)
        numerics = _numeric_fields(entries)
        if args.min_shaves > 0 and entries and "shaves" not in numerics:
            raise QueryError(
                f"category {args.category!r} has no shaves field to filter on; "
                f"numeric fields: {', '.join(numerics) or '(none)'}"
            )
        row: dict[str, Any] = {"period": label}
        for name in names:
            entry = _find_entry(entries, name, args.contains, key_field, args.category)
            info = None
            if entry is not None and (
                args.min_shaves <= 0 or _entry_int(entry, "shaves") >= args.min_shaves
            ):
                info = {"rank": entry.get("rank"), **{f: entry.get(f) for f in numerics}}
            if len(names) == 1:
                row.update(info or {"rank": None, **{f: None for f in numerics}})
            else:
                row[name] = info
        rows.append(row)
    if len(names) == 1:
        return {"category": args.category, "name": names[0], "rows": rows, "skipped": skipped}
    return {"category": args.category, "names": names, "rows": rows, "skipped": skipped}


def _render_meta(block: dict[str, Any]) -> str:
    """Render a meta block as aligned key: value lines."""
    width = max((len(k) for k in block), default=0)
    return "\n".join(f"{k:<{width}}  {json.dumps(v)}" for k, v in block.items())


def _render_schema(result: dict[str, Any]) -> str:
    """Render the schema result as aligned per-category lines."""
    lines = [f"{result['period']}  {result['file']}"]
    for key, info in result["categories"].items():
        if info["type"] == "list":
            fields = ", ".join(info["fields"]) or "(no dict rows)"
            lines.append(f"  {key:<24} list  rows={info['rows']}  fields: {fields}")
        elif info["type"] == "dict":
            keys = ", ".join(info["keys"])
            lines.append(f"  {key:<24} dict           keys: {keys}")
        else:
            lines.append(f"  {key:<24} {info['type']}")
    return "\n".join(lines)


def _render_rows(
    rows: list[dict[str, Any]],
    show_rank: bool = True,
    canonical: tuple[str, ...] = CANONICAL_NUMERICS,
) -> str:
    """Render period/rank/numeric rows as an aligned table."""
    field_set = {key for row in rows for key in row if key not in ("period", "rank")}
    numerics = [f for f in canonical if f in field_set] + sorted(field_set - set(canonical))
    headers = ["period", *(["rank"] if show_rank else []), *numerics]
    table: list[list[str]] = []
    for row in rows:
        cells = [str(row["period"])]
        if show_rank:
            cells.append(str(row["rank"]) if row["rank"] is not None else "-")
        cells.extend(_format_cell(row.get(field)) for field in numerics)
        table.append(cells)
    widths = [max(len(headers[i]), *(len(r[i]) for r in table)) for i in range(len(headers))]
    header_line = "  ".join(h.rjust(widths[i]) for i, h in enumerate(headers))
    body = "\n".join("  ".join(c.rjust(widths[i]) for i, c in enumerate(r)) for r in table)
    return f"{header_line}\n{body}" if table else "(no rows)"


def _render_ranking(result: dict[str, Any]) -> str:
    """Render the sort-key registry as aligned category/spec/style lines."""
    lines = [
        "Table sort keys — the encoding of rendered rank order (production sweep verifies",
        "real files against this registry). competition: ties share a rank (1, 2, 2, 4),",
        "alphabetical within a shared rank; sequential: 1, 2, 3 with no sharing. Annual",
        "files follow the same rules; maker tables are re-keyed to name.",
    ]
    for key, info in result["categories"].items():
        style = info["ranks"]
        spec = ", ".join(f"{field} {direction}" for field, direction in info["sort"])
        lines.append(f"{key:<32} {spec:<48} {style}" if spec else f"{key:<32} dict — not ranked")
    return "\n".join(lines)


def _render_metrics_month(result: dict[str, Any]) -> str:
    """Render a period's dict metric categories as aligned key: value blocks."""
    lines = [f"{result['period']}  {result['file']}"]
    for key, block in result["metrics"].items():
        lines.append(key)
        lines.extend("  " + line for line in _render_meta(block).splitlines())
    return "\n".join(lines)


def _render_top(entries: list[dict[str, Any]], category: str) -> str:
    """Render top-N entries as aligned rank/key-field/numeric rows."""
    key_field = _key_field(entries, category)
    numerics = _numeric_fields(entries)
    headers = ["rank", key_field, *numerics]
    table = [
        [
            str(e.get("rank", "")),
            str(e.get(key_field, "")),
            *(_format_cell(e.get(field)) for field in numerics),
        ]
        for e in entries
    ]
    widths = [max(len(headers[i]), *(len(r[i]) for r in table)) for i in range(len(headers))]
    header_line = "  ".join(h.rjust(widths[i]) for i, h in enumerate(headers))
    body = "\n".join("  ".join(c.rjust(widths[i]) for i, c in enumerate(r)) for r in table)
    return f"{header_line}\n{body}" if table else "(no rows)"


def _render_count(result: dict[str, Any]) -> str:
    """Render a count result as one summary line."""
    line = f"{result['period']}  {result['category']}: {result['count']} of {result['total']} rows"
    if result["where"]:
        line += f" match ({', '.join(result['where'])})"
    return line


def _matrix_cell(entry: dict[str, Any]) -> str:
    """Render one matrix cell: #rank shaves/users plus any extra numeric fields."""
    parts = [f"#{entry.get('rank')}"]
    shaves = entry.get("shaves")
    users = entry.get("unique_users")
    if shaves is not None and users is not None:
        parts.append(f"{shaves:,}/{users}")
    elif shaves is not None:
        parts.append(f"{shaves:,}")
    for field in sorted(k for k in entry if k not in ("rank", "shaves", "unique_users")):
        if entry[field] is not None:
            parts.append(f"{field}={_format_cell(entry[field])}")
    return " ".join(parts)


def _render_matrix(result: dict[str, Any]) -> str:
    """Render a multi-item history as a period x item matrix of rank shaves/users cells."""
    names = result["names"]
    headers = ["period"] + names
    table: list[list[str]] = []
    for row in result["rows"]:
        cells = [str(row["period"])]
        for name in names:
            entry = row.get(name)
            cells.append("-" if entry is None else _matrix_cell(entry))
        table.append(cells)
    widths = [max(len(headers[i]), *(len(r[i]) for r in table)) for i in range(len(headers))]
    header_line = "  ".join(h.ljust(widths[i]) for i, h in enumerate(headers))
    body = "\n".join("  ".join(c.ljust(widths[i]) for i, c in enumerate(r)) for r in table)
    return f"{header_line}\n{body}" if table else "(no rows)"


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point returning a process exit code."""
    args = build_parser().parse_args(argv)
    try:
        if args.command == "meta":
            block = query_meta(args)
            output = json.dumps(block, indent=2) if args.json else _render_meta(block)
        elif args.command == "schema":
            result = query_schema(args)
            output = json.dumps(result, indent=2) if args.json else _render_schema(result)
        elif args.command == "top":
            entries = query_top(args)
            output = (
                json.dumps(entries, indent=2) if args.json else _render_top(entries, args.category)
            )
        elif args.command == "ranking":
            result = query_ranking(args)
            output = json.dumps(result, indent=2) if args.json else _render_ranking(result)
        elif args.command == "count":
            result = query_count(args)
            output = json.dumps(result, indent=2) if args.json else _render_count(result)
        elif args.command == "metrics":
            result = query_metrics(args)
            if args.json:
                output = json.dumps(result, indent=2)
            elif "metrics" in result:
                output = _render_metrics_month(result)
            else:
                output = _render_rows(result["rows"], show_rank=False, canonical=META_CANONICAL)
                if result["skipped"]:
                    output += f"\n(skipped missing files: {', '.join(result['skipped'])})"
        else:
            result = query_history(args)
            if args.json:
                output = json.dumps(result, indent=2)
            else:
                output = (
                    _render_matrix(result) if "names" in result else _render_rows(result["rows"])
                )
            if result["skipped"]:
                output += f"\n(skipped missing files: {', '.join(result['skipped'])})"
    except QueryError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
