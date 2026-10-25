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


def build_overview(data_dir: Path, month: Optional[str] = None) -> Dict[str, Any]:
    """Compute the home-overview payload. Same data semantics as the
    home_overview endpoint (pulse over all months, tiles+movers for `month`
    or the latest). Returns a JSON-ready dict."""
    agg = data_dir / "aggregated"
    ua_dir = agg / "user_analysis"
    pu_dir = agg / "product_usage"

    months = sorted(p.stem for p in ua_dir.glob("????-??.json"))
    if not months:
        return {"pulse": [], "movers": {"razors": [], "soaps": [], "blades": []}}

    pulse = []
    for m in months:
        ua = _load(ua_dir / f"{m}.json")
        if ua is None:
            continue
        posts = sum(int(u.get("posted_days", 0)) for u in (ua.get("users") or {}).values())
        pulse.append({"month": m, "posts": posts})

    latest = month if month else months[-1]
    if month and month not in months:
        raise ValueError(f"no data for month {month}")

    pu = _load(pu_dir / f"{latest}.json")
    ua = _load(ua_dir / f"{latest}.json")
    if pu is None or ua is None:
        return {
            "latest_month": latest,
            "pulse": pulse,
            "movers": {"razors": [], "soaps": [], "blades": []},
        }

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

    return {"latest_month": latest, "pulse": pulse, "tiles": tiles, "movers": movers}


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
