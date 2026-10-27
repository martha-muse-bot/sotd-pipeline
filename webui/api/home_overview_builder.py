#!/usr/bin/env python3
"""Build the public home-overview payload from the aggregated bundle.

Shared by two callers:
  - webui/api/home_overview.py serves it (preferring a precomputed file)
  - the precompute step (publish flow / nightly supervisor) writes it

The bundle only changes when the pipeline re-aggregates and publish runs,
so the payload is safe to precompute. Kept dependency-free (stdlib only)
so both the API and the supervisor can import it.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

OUTPUT_NAME = "home_overview.json"


class _Unsupported(Exception):
    """Payload shape changed; caller should treat as build failure."""


def _pulse_series(ua_dir: Path, months: List[str]) -> List[Dict[str, Any]]:
    """Monthly SOTD post counts. Parses every user_analysis slice (~126 files),
    so callers memoize the result keyed on the directory's mtimes — the pulse
    is identical for every requested month."""
    pulse = []
    for m in months:
        ua = _load(ua_dir / f"{m}.json")
        if ua is None:
            continue
        posts = sum(int(u.get("posted_days", 0)) for u in (ua.get("users") or {}).values())
        pulse.append({"month": m, "posts": posts})
    return pulse


def pulse_series_memo(data_dir: Path, months: List[str]) -> List[Dict[str, Any]]:
    """Memoized pulse series for the endpoint's per-month requests: keyed on
    the user_analysis dir's mtimes, so a click on the pulse chart never
    re-parses history. The precomputed file already embeds the pulse; this
    covers the compute path."""
    ua_dir = data_dir / "aggregated" / "user_analysis"
    key = tuple((p.name, p.stat().st_mtime_ns) for p in sorted(ua_dir.glob("????-??.json")))
    cache = pulse_series_memo._cache  # type: ignore[attr-defined]
    if cache.get("key") == key and cache.get("pulse") is not None:
        return cache["pulse"]
    pulse = _pulse_series(data_dir / "aggregated" / "user_analysis", months)
    cache["key"] = key
    cache["pulse"] = pulse
    return pulse


pulse_series_memo._cache = {"key": None, "pulse": None}  # type: ignore[attr-defined]


def _load(path: Path) -> Optional[dict]:
    try:
        with path.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("home_overview_builder: unreadable %s: %s", path, exc)
        return None


def _is_unknown(product: Dict[str, Any]) -> bool:
    brand = (product.get("brand") or "").strip().lower()
    model = (product.get("model") or "").strip().lower()
    return brand == "unknown" or model == "unknown" or (brand == "" and model == "")


def _display_name(product: Dict[str, Any]) -> str:
    brand = (product.get("brand") or "").strip()
    model = (product.get("model") or "").strip()
    if brand and model:
        return f"{brand} {model}"
    return brand or model or "unknown"


def _top_products(pu: dict) -> Dict[str, Optional[str]]:
    out = {}
    for field, key in (
        ("razors", "top_razor"),
        ("blades", "top_blade"),
        ("soaps", "top_soap"),
        ("brushes", "top_brush"),
    ):
        entries = pu.get(field) or {}
        best = None
        for entry in entries.values():
            if _is_unknown(entry.get("product", {})):
                continue
            usage = entry.get("total_usage", 0)
            if best is None or usage > best[0]:
                best = (usage, entry)
        out[key] = _display_name(best[1]["product"]) if best else None
    return out


def _rank_map(pu: dict, field: str) -> Dict[str, int]:
    """Rank products by the canonical table semantics: shaves desc, then
    unique_users desc (matching aggregate_query ranking; equal shaves are NOT
    a tie for display purposes — position comes from this ordering)."""
    entries = sorted(
        (e for e in (pu.get(field) or {}).values() if not _is_unknown(e.get("product", {}))),
        key=lambda e: (
            -e.get("total_usage", 0),
            -e.get("unique_users", 0),
            _display_name(e.get("product", {})),
        ),
    )
    return {_display_name(e["product"]): i + 1 for i, e in enumerate(entries)}


def _movers_for(current: dict, prior: dict, field: str) -> List[Dict[str, Any]]:
    prior_rank = _rank_map(prior, field)
    current_rank = _rank_map(current, field)

    scored = []
    for entry in (current.get(field) or {}).values():
        if _is_unknown(entry.get("product", {})):
            continue
        name = _display_name(entry.get("product", {}))
        count = entry.get("total_usage", 0)
        if name in prior_rank:
            # rank delta: positive = climbed (prior position - current position)
            scored.append((count, prior_rank[name] - current_rank[name], False, name))
        else:
            scored.append((count, 0, True, name))
    scored.sort(key=lambda t: (-t[0], t[3]))
    return [{"name": n, "count": c, "delta": d, "is_new": new} for c, d, new, n in scored[:5]]


def _utc_now_iso() -> str:
    """Freshness stamp for the payload: when it was computed/published."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_overview(
    data_dir: Path,
    month: Optional[str] = None,
    pulse: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute the home-overview payload. Same data semantics as the
    home_overview endpoint (pulse over all months, tiles+movers for `month`
    or the latest). Returns a JSON-ready dict. Callers that already hold the
    pulse series (it is identical for every month) may pass `pulse` to skip
    re-parsing history."""
    agg = data_dir / "aggregated"
    ua_dir = agg / "user_analysis"
    pu_dir = agg / "product_usage"

    months = sorted(p.stem for p in ua_dir.glob("????-??.json"))
    if not months:
        return {
            "generated_at": _utc_now_iso(),
            "data_through": None,
            "pulse": [],
            "movers": {"razors": [], "soaps": [], "blades": []},
        }

    if pulse is None:
        pulse = _pulse_series(ua_dir, months)

    latest = month if month else months[-1]
    if month and month not in months:
        raise ValueError(f"no data for month {month}")

    pu = _load(pu_dir / f"{latest}.json")
    ua = _load(ua_dir / f"{latest}.json")
    if pu is None or ua is None:
        return {
            "generated_at": _utc_now_iso(),
            "data_through": None,
            "latest_month": latest,
            "pulse": pulse,
            "movers": {"razors": [], "soaps": [], "blades": []},
        }

    # Coverage end = newest SOTD date actually processed (the current month
    # is partial, so the month itself is not "through").
    posted = [d for u in (ua.get("users") or {}).values() for d in (u.get("posted_dates") or [])]
    data_through: Optional[str] = max(posted) if posted else None

    posts_for_latest = next((p["posts"] for p in pulse if p["month"] == latest), 0)
    tiles = {
        "posts": posts_for_latest,
        "shavers": len((ua.get("users") or {})),
        **_top_products(pu),
    }

    prior_month = months[months.index(latest) - 1] if months.index(latest) >= 1 else None
    prior = _load(pu_dir / f"{prior_month}.json") if prior_month else None
    prior = prior or {}

    movers = {field: _movers_for(pu, prior, field) for field in ("razors", "soaps", "blades")}

    return {
        "generated_at": _utc_now_iso(),
        "data_through": data_through,
        "latest_month": latest,
        "pulse": pulse,
        "tiles": tiles,
        "movers": movers,
    }


def write_precomputed(data_dir: Path) -> Path:
    """Build the overview for the latest month and write it into the bundle
    (aggregated/home_overview.json) so publish copies it to the NAS."""
    payload = build_overview(data_dir)
    out = data_dir / "aggregated" / OUTPUT_NAME
    tmp = out.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(payload, f)
    tmp.replace(out)
    return out


# --- monthly-user-posts months list -------------------------------------------


def build_months_list(data_dir: Path) -> List[Dict[str, Any]]:
    """{month, has_data, user_count} rows for /api/monthly-user-posts/months.
    The endpoint's compute path parses every user_analysis file for these
    counts; precomputing makes the page's first request a single-file read."""
    ua_dir = data_dir / "aggregated" / "user_analysis"
    months = []
    for path in sorted(ua_dir.glob("????-??.json")):
        ua = _load(path)
        count = len((ua.get("users") or {})) if ua is not None else 0
        months.append({"month": path.stem, "has_data": ua is not None, "user_count": count})
    return months


def write_months_list(data_dir: Path) -> Path:
    out = data_dir / "aggregated" / "monthly_user_posts_months.json"
    tmp = out.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(build_months_list(data_dir), f)
    tmp.replace(out)
    return out


# --- rankings rows per (table, month) -----------------------------------------


def _table_ids_from_data(data: Dict[str, Any]) -> List[str]:
    return sorted(
        key
        for key, value in data.items()
        if isinstance(value, list) and bool(value) and isinstance(value[0], dict)
    )


def _row_identity(row: Dict[str, Any]) -> Optional[str]:
    """Item display name from a structured table row (shared shape with the
    rankings endpoint's own extraction: name/name/User/user, then any string col)."""
    for key in ("name", "Name", "User", "user"):
        if key in row and isinstance(row[key], str):
            return row[key].strip() or None
    skip = {"rank", "position", "shaves", "unique_users", "unique users"}
    for key, value in row.items():
        k_lower = key.lower().replace(" ", "_")
        if k_lower in skip or (isinstance(value, (int, float)) and k_lower != "rank"):
            continue
        if isinstance(value, str) and value.strip():
            return value.strip()
    if row.get("use_count") is not None:
        return str(row["use_count"])
    return None


def _numeric(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return int(value.replace("=", "").replace(",", "").strip())
        except ValueError:
            return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_rankings_rows(
    data_dir: Path,
    table_ids: Optional[List[str]] = None,
    progress: Optional[Any] = None,
) -> Dict[str, List[Dict[str, Any]]]:
    """Per-table rows across all months: for each (table, month), the list of
    {name, rank, shaves, unique_users}. Stored newest-first per month order
    matching the aggregated dir listing. `progress` gets (table, month) calls."""
    agg = data_dir / "aggregated"
    months = sorted(p.stem for p in agg.glob("????-??.json"))
    # Import here so the builder keeps stdlib-only for the API path.
    from sotd.report.table_generators.table_generator import TableGenerator

    out: Dict[str, List[Dict[str, Any]]] = {}
    for month in months:
        path = agg / f"{month}.json"
        try:
            with path.open() as f:
                content = json.load(f)
            data = content["data"]
        except (OSError, json.JSONDecodeError, KeyError) as exc:
            logger.warning("rankings precompute: skipping %s: %s", path, exc)
            continue
        for table_id in table_ids if table_ids is not None else _table_ids_from_data(data):
            if progress:
                progress(table_id, month)
            table_name = table_id.replace("_", "-") if "_" in table_id else table_id
            generator = TableGenerator(data, comparison_data={}, current_month=month)
            try:
                rows = generator.get_structured_table_data(
                    table_name, deltas=False, format_column_names=False
                )
            except Exception as exc:
                logger.warning("rankings precompute: %s/%s: %s", table_id, month, exc)
                continue
            extracted = []
            for row in rows:
                name = _row_identity(row)
                rank = _numeric(row.get("rank"))
                if name is None and rank is None:
                    continue
                extracted.append(
                    {
                        "name": name,
                        "rank": rank,
                        "shaves": _numeric(row.get("shaves")),
                        "unique_users": _numeric(row.get("unique_users")),
                    }
                )
            out.setdefault(table_id, []).append({"month": month, "rows": extracted})
    return out


def write_rankings_rows(data_dir: Path, progress: Optional[Any] = None) -> Path:
    """Write aggregated/rankings/<table>.json — one file per table, all months."""
    rows_by_table = build_rankings_rows(data_dir, progress=progress)
    out_dir = data_dir / "aggregated" / "rankings"
    out_dir.mkdir(parents=True, exist_ok=True)
    for table_id, months in rows_by_table.items():
        out = out_dir / f"{table_id}.json"
        tmp = out.with_suffix(".json.tmp")
        with tmp.open("w") as f:
            json.dump({"table": table_id, "months": months}, f)
        tmp.replace(out)
    return out_dir
