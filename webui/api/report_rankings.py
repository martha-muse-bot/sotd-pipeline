#!/usr/bin/env python3
"""Report rankings API: placement over time for aggregation table rows."""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Add project root for sotd imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sotd.report.load import load_aggregated_data  # noqa: E402
from sotd.report.table_generators.table_generator import TableGenerator  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/report-rankings", tags=["report-rankings"])


class MonthsResponse(BaseModel):
    """Available months with aggregated data."""

    months: List[str]


class TableInfo(BaseModel):
    """One aggregation table."""

    id: str
    label: str


class TablesResponse(BaseModel):
    """List of aggregation tables."""

    tables: List[TableInfo]


class ItemsResponse(BaseModel):
    """Item names for a table (row labels)."""

    items: List[str]


class SeriesPoint(BaseModel):
    """One month's rank/shaves/unique_users for an item."""

    month: str
    rank: Optional[int] = None
    shaves: Optional[int] = None
    unique_users: Optional[int] = None


class SeriesEntry(BaseModel):
    """Time series for one item."""

    item: str
    data: List[SeriesPoint]


class SeriesResponse(BaseModel):
    """Rank-over-time series for requested items."""

    months: List[str]
    series: List[SeriesEntry]


class PivotedPoint(BaseModel):
    """One month's item at a rank slot, with previous-month rank for movement."""

    month: str
    item: Optional[str] = None
    shaves: Optional[int] = None
    unique_users: Optional[int] = None
    prev_rank: Optional[int] = None


class PivotedLane(BaseModel):
    """One rank slot (1..20) with points per month."""

    rank: int
    points: List[PivotedPoint]


class PivotedResponse(BaseModel):
    """Top-20-by-month pivoted data for swim lanes."""

    months: List[str]
    lanes: List[PivotedLane]


def _get_aggregated_dir() -> Path:
    """Return path to data/aggregated directory."""
    env_dir = os.environ.get("SOTD_DATA_DIR")
    if env_dir:
        return Path(env_dir) / "aggregated"
    return project_root / "data" / "aggregated"


# Month-file cache: every endpoint below scans all ~126 monthly aggregated
# files (seconds on the NAS), and the bundle only changes when the pipeline
# re-aggregates and publish runs. Cache keyed on each file's (size, mtime_ns)
# so a replaced month invalidates just that entry.
_month_cache: Dict[str, Dict[str, Any]] = {}


def _load_month_cached(file_path: Path) -> Dict[str, Any]:
    """load_aggregated_data for one month, served from an in-memory cache
    keyed on the file's size + mtime."""
    st = file_path.stat()
    key = f"{file_path.stem}"
    fingerprint = (st.st_size, st.st_mtime_ns)
    cached = _month_cache.get(key)
    if cached is not None and cached["fingerprint"] == fingerprint:
        return cached["data"]
    _, data = load_aggregated_data(file_path, debug=False)
    _month_cache[key] = {"fingerprint": fingerprint, "data": data}
    return data


# Derived table rows cache: get_structured_table_data runs the TableGenerator
# over a month's data (~1-5ms/month locally, more on the NAS) on every request.
# Keyed on (table, month) with the same file fingerprint as _load_month_cached.
_table_rows_cache: Dict[tuple, Dict[str, Any]] = {}


def _table_rows_cached(file_path: Path, table_name: str) -> List[Dict[str, Any]]:
    """Structured table rows for one month+table, memoized on file fingerprint."""
    st = file_path.stat()
    key = (table_name, file_path.stem)
    fingerprint = (st.st_size, st.st_mtime_ns)
    cached = _table_rows_cache.get(key)
    if cached is not None and cached["fingerprint"] == fingerprint:
        return cached["rows"]
    data = _load_month_cached(file_path)
    generator = TableGenerator(data, comparison_data={}, current_month=file_path.stem)
    rows = generator.get_structured_table_data(table_name, deltas=False, format_column_names=False)
    _table_rows_cache[key] = {"fingerprint": fingerprint, "rows": rows}
    return rows


# Precomputed rankings rows (aggregated/rankings/<table>.json, written at
# publish time by home_overview_builder.write_rankings_rows). Served when the
# file's month set matches the aggregated dir exactly — first-request-after-
# restart stays fast, and the API never holds all parsed months in memory.
_precomputed_rows_cache: Dict[str, Optional[Dict[str, Any]]] = {}


def _precomputed_rows(table_id: str) -> Optional[Dict[str, Any]]:
    """{months: [{month, rows}], ...} for a table, or None when absent/stale."""
    aggregated_dir = _get_aggregated_dir()
    if not aggregated_dir.exists():
        return None
    file_months = {p.stem for p in aggregated_dir.glob("????-??.json")}
    path = aggregated_dir / "rankings" / f"{table_id}.json"
    if not path.exists():
        _precomputed_rows_cache.pop(table_id, None)
        return None
    cached = _precomputed_rows_cache.get(table_id)
    # Invalidate on the rankings file's own mtime — publish replaces it.
    try:
        mtime = path.stat().st_mtime_ns
    except OSError:
        return None
    if cached is not None and cached.get("mtime") == mtime:
        return cached["payload"]
    try:
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"precomputed rankings unreadable for {table_id}: {e}")
        return None
    precomputed_months = {m["month"] for m in payload.get("months", [])}
    if precomputed_months != file_months:
        return None  # stale: publish hasn't run since a month was added/removed
    _precomputed_rows_cache[table_id] = {"mtime": mtime, "payload": payload}
    return payload


def _humanize(key: str) -> str:
    """Convert snake_case key to title label (e.g. razor_manufacturers -> Razor manufacturers)."""
    return key.replace("_", " ").title()


def _get_available_months(aggregated_dir: Path) -> List[str]:
    """List month stems (YYYY-MM) from aggregated JSON files, sorted."""
    if not aggregated_dir.exists():
        return []
    months = []
    for f in aggregated_dir.glob("*.json"):
        if f.stem and f.stat().st_size > 0:
            # Validate YYYY-MM
            if re.match(r"^\d{4}-\d{2}$", f.stem):
                months.append(f.stem)
    months.sort()
    return months


def _get_tables_from_data(data: Dict[str, Any]) -> List[TableInfo]:
    """Build table list from aggregated data: every key whose value is a list of objects."""
    tables = []
    for key, value in data.items():
        if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
            tables.append(TableInfo(id=key, label=_humanize(key)))
    tables.sort(key=lambda t: t.label)
    return tables


def _identifier_column(row: Dict[str, Any]) -> Optional[str]:
    """Return the key in row that holds the item display name (case-insensitive match)."""
    skip = {"rank", "position", "shaves", "unique_users", "unique users"}
    for k, v in row.items():
        k_lower = k.lower().replace(" ", "_")
        if k_lower in skip or (isinstance(v, (int, float)) and k_lower != "rank"):
            continue
        if isinstance(v, str) and v.strip():
            return k
    return None


def _row_display_name(row: Dict[str, Any]) -> Optional[str]:
    """Get the display name for a row (for matching and items list)."""
    # Prefer "name" (any case)
    for key in ("name", "Name", "User", "user"):
        if key in row and isinstance(row[key], str):
            return row[key].strip() or None
    col = _identifier_column(row)
    if col and col in row:
        return str(row[col]).strip() or None
    # Tables with only numeric columns (e.g. blade_usage_distribution): use use_count as label
    if "use_count" in row and row["use_count"] is not None:
        return str(row["use_count"])
    return None


def _normalize_name(s: str) -> str:
    """Normalize for matching: lowercase, collapse whitespace."""
    return " ".join(s.lower().split())


@router.get("/months", response_model=MonthsResponse)
async def get_months() -> MonthsResponse:
    """List available months with aggregated data."""
    aggregated_dir = _get_aggregated_dir()
    months = _get_available_months(aggregated_dir)
    return MonthsResponse(months=months)


@router.get("/tables", response_model=TablesResponse)
async def get_tables() -> TablesResponse:
    """List all aggregation tables from the latest available month."""
    aggregated_dir = _get_aggregated_dir()
    months = _get_available_months(aggregated_dir)
    if not months:
        return TablesResponse(tables=[])

    latest = months[-1]
    file_path = aggregated_dir / f"{latest}.json"
    if not file_path.exists():
        return TablesResponse(tables=[])

    try:
        data = _load_month_cached(file_path)
        tables = _get_tables_from_data(data)
        return TablesResponse(tables=tables)
    except Exception as e:
        logger.warning(f"Failed to load aggregated data for tables: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/items", response_model=ItemsResponse)
async def get_items(
    table: str = Query(..., description="Table id (snake_case)"),
    month: Optional[str] = Query(
        None, description="Month YYYY-MM; when omitted, items from all months"
    ),
) -> ItemsResponse:
    """List item names (row labels) for a table. When month is omitted, returns the union of
    items across all available months so that formats/categories that appear in some months
    but not others (e.g. AC razors) are still selectable."""
    aggregated_dir = _get_aggregated_dir()
    months = _get_available_months(aggregated_dir)
    if not months:
        return ItemsResponse(items=[])

    table_name = table.replace("_", "-") if "_" in table else table
    # normalized name -> first display name seen (canonical for dropdown)
    by_normalized: Dict[str, str] = {}

    if month and month in months:
        # Single month: use only that month
        months_to_scan = [month]
    else:
        # No month: union across all months so all items ever present are selectable
        months_to_scan = months

    # Fast path: precomputed rows (whole-history unions are the common case).
    pre = None if (month and month in months) else _precomputed_rows(table)
    if pre is not None:
        for month_entry in pre["months"]:
            for row in month_entry["rows"]:
                name = row.get("name")
                if not name:
                    continue
                norm = _normalize_name(name)
                if norm not in by_normalized:
                    by_normalized[norm] = name
        names = sorted(by_normalized.values(), key=lambda s: _normalize_name(s))
        return ItemsResponse(items=names)

    for use_month in months_to_scan:
        file_path = aggregated_dir / f"{use_month}.json"
        if not file_path.exists():
            continue
        try:
            rows = _table_rows_cached(file_path, table_name)
        except Exception as e:
            logger.debug(f"Skip month {use_month} for items: {e}")
            continue
        for row in rows:
            name = _row_display_name(row)
            if not name:
                continue
            norm = _normalize_name(name)
            if norm not in by_normalized:
                by_normalized[norm] = name

    # Preserve a stable order: sort by normalized name so dropdown order is consistent
    names = sorted(by_normalized.values(), key=lambda s: _normalize_name(s))
    return ItemsResponse(items=names)


@router.get("/series", response_model=SeriesResponse)
async def get_series(
    table: str = Query(..., description="Table id (snake_case or kebab-case)"),
    items: str = Query(..., description="Comma-separated item names to track (URL-encoded)"),
) -> SeriesResponse:
    """Get rank and shaves over time for the given table and items."""
    aggregated_dir = _get_aggregated_dir()
    months = _get_available_months(aggregated_dir)
    if not months:
        return SeriesResponse(months=[], series=[])

    item_list = [unquote(s).strip() for s in items.split(",") if s.strip()]
    if not item_list:
        raise HTTPException(status_code=400, detail="At least one item is required")

    table_name = table.replace("_", "-") if "_" in table else table
    wanted = {_normalize_name(i): i for i in item_list}  # normalized -> original

    series_by_item: Dict[str, List[Dict[str, Any]]] = {orig: [] for orig in item_list}
    valid_months: List[str] = []

    # Fast path: precomputed rows — pure filtering, no month parsing.
    pre = _precomputed_rows(table)
    if pre is not None:
        by_month_rows = {m["month"]: m["rows"] for m in pre["months"]}
        for month_str in months:
            rows = by_month_rows.get(month_str)
            if rows is None:
                continue
            valid_months.append(month_str)
            by_name = {}
            for row in rows:
                if row.get("name"):
                    by_name[_normalize_name(row["name"])] = row
            for norm, orig in wanted.items():
                row = by_name.get(norm)
                series_by_item[orig].append(
                    {
                        "month": month_str,
                        "rank": row.get("rank") if row else None,
                        "shaves": row.get("shaves") if row else None,
                        "unique_users": row.get("unique_users") if row else None,
                    }
                )
    else:
        for month_str in months:
            file_path = aggregated_dir / f"{month_str}.json"
            if not file_path.exists():
                continue
            try:
                rows = _table_rows_cached(file_path, table_name)
            except Exception as e:
                logger.debug(f"Skip month {month_str}: {e}")
                continue

            valid_months.append(month_str)
            by_name: Dict[str, Dict[str, Any]] = {}
            for row in rows:
                name = _row_display_name(row)
                if name:
                    by_name[_normalize_name(name)] = row

            for norm, orig in wanted.items():
                row = by_name.get(norm)
                rank = row.get("rank") if row else None
                shaves = row.get("shaves") if row else None
                unique_users = row.get("unique_users") if row else None
                if rank is not None and isinstance(rank, str):
                    try:
                        rank = int(rank.replace("=", "").strip())
                    except ValueError:
                        rank = None
                if unique_users is not None and isinstance(unique_users, str):
                    try:
                        unique_users = int(unique_users.replace(",", "").strip())
                    except ValueError:
                        unique_users = None
                series_by_item[orig].append(
                    {
                        "month": month_str,
                        "rank": rank,
                        "shaves": shaves,
                        "unique_users": unique_users,
                    }
                )

    # Build response: ensure every item has an entry for every valid month (null if missing)
    series_entries = [
        SeriesEntry(
            item=item,
            data=[
                SeriesPoint(
                    month=p["month"],
                    rank=p["rank"],
                    shaves=p.get("shaves"),
                    unique_users=p.get("unique_users"),
                )
                for p in series_by_item[item]
            ],
        )
        for item in item_list
    ]
    return SeriesResponse(months=valid_months, series=series_entries)


def _row_rank(row: Dict[str, Any]) -> Optional[int]:
    """Extract numeric rank from a table row."""
    rank = row.get("rank")
    if rank is None:
        return None
    if isinstance(rank, str):
        try:
            return int(rank.replace("=", "").strip())
        except ValueError:
            return None
    return int(rank) if rank is not None else None


@router.get("/pivoted", response_model=PivotedResponse)
async def get_pivoted(
    table: str = Query(..., description="Table id (snake_case or kebab-case)"),
) -> PivotedResponse:
    """Get top-20-by-month pivoted data for swim lanes (rank per month, with prev_rank for movement)."""
    aggregated_dir = _get_aggregated_dir()
    months = _get_available_months(aggregated_dir)
    if not months:
        return PivotedResponse(months=[], lanes=[])

    table_name = table.replace("_", "-") if "_" in table else table
    TOP_N = 20

    # Build per-month: list of (display_name, shaves, unique_users) for ranks 1..TOP_N
    month_rows: List[List[tuple]] = []  # month_rows[i] = [(name, shaves, unique_users), ...]
    valid_months: List[str] = []

    def _row_slot(row: Dict[str, Any]) -> tuple:
        name = row.get("name")
        shaves = row.get("shaves")
        if isinstance(shaves, str):
            try:
                shaves = int(shaves.replace(",", "").strip())
            except ValueError:
                shaves = None
        unique_users = row.get("unique_users")
        if isinstance(unique_users, str):
            try:
                unique_users = int(unique_users.replace(",", "").strip())
            except ValueError:
                unique_users = None
        return (name or "", shaves, unique_users)

    # Fast path: precomputed rows — top-N per month is a slice of each month's
    # rows (the precompute already ordered by rank).
    pre = _precomputed_rows(table)
    if pre is not None:
        by_month_rows = {m["month"]: m["rows"] for m in pre["months"]}
        for month_str in months:
            rows = by_month_rows.get(month_str)
            if rows is None:
                continue
            valid_months.append(month_str)
            slot_list = [_row_slot(r) for r in rows[:TOP_N]]
            while len(slot_list) < TOP_N:
                slot_list.append(("", None, None))
            month_rows.append(slot_list)
    else:
        for month_str in months:
            file_path = aggregated_dir / f"{month_str}.json"
            if not file_path.exists():
                continue
            try:
                rows = _table_rows_cached(file_path, table_name)
            except Exception as e:
                logger.debug(f"Skip month {month_str}: {e}")
                continue

            valid_months.append(month_str)
            slot_list = [_row_slot(r) for r in rows[:TOP_N]]
            while len(slot_list) < TOP_N:
                slot_list.append(("", None, None))
            month_rows.append(slot_list)

    if not valid_months:
        return PivotedResponse(months=[], lanes=[])

    # For each month i, build item -> rank (1-based) for previous month i-1 (for prev_rank)
    def prev_rank_for(month_index: int, slot_index: int) -> Optional[int]:
        if month_index == 0:
            return None
        name, _, _ = month_rows[month_index][slot_index]
        if not name or not name.strip():
            return None
        norm = _normalize_name(name)
        prev_slots = month_rows[month_index - 1]
        for r, (n, _, _) in enumerate(prev_slots):
            if n and _normalize_name(n) == norm:
                return r + 1
        return None

    lanes: List[PivotedLane] = []
    for rank_one_based in range(1, TOP_N + 1):
        slot_index = rank_one_based - 1
        points: List[PivotedPoint] = []
        for mi, month_str in enumerate(valid_months):
            name, shaves, unique_users = month_rows[mi][slot_index]
            prev_r = prev_rank_for(mi, slot_index)
            points.append(
                PivotedPoint(
                    month=month_str,
                    item=name or None,
                    shaves=shaves,
                    unique_users=unique_users,
                    prev_rank=prev_r,
                )
            )
        lanes.append(PivotedLane(rank=rank_one_based, points=points))

    return PivotedResponse(months=valid_months, lanes=lanes)
