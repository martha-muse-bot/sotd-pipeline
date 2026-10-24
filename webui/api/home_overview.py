#!/usr/bin/env python3
"""Home overview endpoint for the public site's dashboard home page.

One read-only GET that returns everything the home dashboard needs in a single
fetch: the community-pulse series (monthly SOTD post counts), this-month stat
tiles, and top-5 movers (rank deltas vs the prior month). Serves only the
published bundle slices under SOTD_DATA_DIR/aggregated.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .utils.data_dir import get_data_dir  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home", tags=["home-overview"])

MONTH_RE_PAIR = None  # months validated by shape (YYYY-MM) on read


class PulsePoint(BaseModel):
    month: str
    posts: int


class Tiles(BaseModel):
    posts: int
    shavers: int
    top_razor: Optional[str] = None
    top_blade: Optional[str] = None
    top_soap: Optional[str] = None
    top_brush: Optional[str] = None


class Mover(BaseModel):
    name: str
    count: int
    delta: int  # usage delta vs prior month; 0 for new entries stays 0 + is_new flag below
    is_new: bool = False


class Movers(BaseModel):
    razors: List[Mover]
    soaps: List[Mover]
    blades: List[Mover]


class Overview(BaseModel):
    latest_month: Optional[str] = None
    pulse: List[PulsePoint]
    tiles: Optional[Tiles] = None
    movers: Movers


def _month_dir(data_dir: Path, sub: str) -> Path:
    return data_dir / "aggregated" / sub


def _month_jsons(dir_path: Path) -> List[str]:
    if not dir_path.is_dir():
        return []
    return sorted(p.stem for p in dir_path.glob("????-??.json"))


def _load(path: Path) -> Optional[dict]:
    try:
        with path.open() as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("home_overview: unreadable %s: %s", path, exc)
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


def _movers_for(current: dict, prior: dict, field: str) -> List[Mover]:
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
    return [Mover(name=n, count=c, delta=d, is_new=new) for c, d, new, n in scored[:5]]


@router.get("/overview", response_model=Overview)
async def get_overview(month: Optional[str] = None) -> Overview:
    data_dir = Path(get_data_dir())
    ua_dir = _month_dir(data_dir, "user_analysis")
    pu_dir = _month_dir(data_dir, "product_usage")

    months = _month_jsons(ua_dir)
    if not months:
        return Overview(pulse=[], movers=Movers(razors=[], soaps=[], blades=[]))

    pulse = []
    for m in months:
        ua = _load(ua_dir / f"{m}.json")
        if ua is None:
            continue
        posts = sum(int(u.get("posted_days", 0)) for u in (ua.get("users") or {}).values())
        pulse.append(PulsePoint(month=m, posts=posts))

    # Selected month: default latest; an explicit ?month= must exist in the
    # bundle (404 otherwise) so the dashboard never shows an empty selection.
    latest = month if month else months[-1]
    if month and month not in months:
        raise HTTPException(status_code=404, detail=f"no data for month {month}")

    pu = _load(pu_dir / f"{latest}.json")
    ua = _load(ua_dir / f"{latest}.json")
    if pu is None or ua is None:
        return Overview(
            latest_month=latest,
            pulse=pulse,
            movers=Movers(razors=[], soaps=[], blades=[]),
        )

    posts_for_latest = next((p.posts for p in pulse if p.month == latest), 0)
    tiles = Tiles(
        posts=posts_for_latest,
        shavers=len((ua.get("users") or {})),
        **_top_products(pu),
    )

    prior_month = months[months.index(latest) - 1] if months.index(latest) >= 1 else None
    prior = _load(pu_dir / f"{prior_month}.json") if prior_month else None
    prior = prior or {}

    movers = Movers(
        razors=_movers_for(pu, prior, "razors"),
        soaps=_movers_for(pu, prior, "soaps"),
        blades=_movers_for(pu, prior, "blades"),
    )

    return Overview(latest_month=latest, pulse=pulse, tiles=tiles, movers=movers)
