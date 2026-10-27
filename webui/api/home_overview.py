#!/usr/bin/env python3
"""Home overview endpoint for the public site's dashboard home page.

One read-only GET that returns everything the home dashboard needs in a single
fetch: the community-pulse series (monthly SOTD post counts), this-month stat
tiles, and top-5 movers (rank deltas vs the prior month).

Fast path: the publish flow precomputes aggregated/home_overview.json (via
home_overview_builder.write_precomputed); this endpoint serves that file when
present and fresh (mtime of the slices unchanged since it was built). Slow
path: compute once via the shared builder and cache in memory until the
bundle changes (slices' mtimes move only when publish replaces them).
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from . import home_overview_builder  # noqa: E402
from .utils.data_dir import get_data_dir  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/home", tags=["home-overview"])

MONTH_RE_PAIR = None  # months validated by shape (YYYY-MM) on read

# In-memory fallback cache, invalidated when the bundle's mtimes change.
_cache: Dict[str, Any] = {"mtime": None, "payload": None}


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
    # UTC ISO stamp of when the payload was computed/published; None for
    # precomputed bundles written before the field existed.
    generated_at: Optional[str] = None
    # True coverage end: the latest posted SOTD date processed (YYYY-MM-DD);
    # the current month is partial, so coverage is not the month itself.
    data_through: Optional[str] = None
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


def _bundle_mtime(data_dir: Path) -> float:
    """Cheap bundle fingerprint: newest mtime among the latest-month slice
    files and the precomputed overview itself."""
    agg = data_dir / "aggregated"
    candidates = [
        agg / "user_analysis",
        agg / "product_usage",
        agg / home_overview_builder.OUTPUT_NAME,
    ]
    newest = 0.0
    for path in candidates:
        if path.is_dir():
            for p in path.glob("????-??.json"):
                newest = max(newest, p.stat().st_mtime)
        elif path.is_file():
            newest = max(newest, path.stat().st_mtime)
    return newest


def _serve_payload(data_dir: Path) -> Dict[str, Any]:
    """Precomputed file if fresh; else compute once and cache in memory."""
    mtime = _bundle_mtime(data_dir)
    if _cache["mtime"] == mtime and _cache["payload"] is not None:
        return _cache["payload"]

    precomputed_path = data_dir / "aggregated" / home_overview_builder.OUTPUT_NAME
    payload: Optional[Dict[str, Any]] = None
    if precomputed_path.is_file():
        payload = _load(precomputed_path)

    if payload is None:
        payload = home_overview_builder.build_overview(data_dir)

    _cache["mtime"] = mtime
    _cache["payload"] = payload
    return payload


@router.get("/overview", response_model=Overview)
async def get_overview(month: Optional[str] = None) -> Overview:
    data_dir = Path(get_data_dir())
    ua_dir = _month_dir(data_dir, "user_analysis")

    months = _month_jsons(ua_dir)
    if not months:
        return Overview(pulse=[], movers=Movers(razors=[], soaps=[], blades=[]))

    # Selected month: default latest; an explicit ?month= must exist in the
    # bundle (404 otherwise) so the dashboard never shows an empty selection.
    if month and month not in months:
        raise HTTPException(status_code=404, detail=f"no data for month {month}")

    # ?month= requests bypass the precomputed/cached payload (which covers the
    # latest month) — the dashboard only ever asks for latest by default.
    if month and month != months[-1]:
        return _overview_from_builder(data_dir, month)

    payload = _serve_payload(data_dir)
    return _overview_from_payload(payload)


def _overview_from_builder(data_dir: Path, month: str) -> Overview:
    """Explicit historical ?month= path: compute tiles+movers for that month,
    reusing the memoized pulse series so a chart click doesn't re-parse the
    whole history (the pulse is identical for every month)."""
    ua_dir = data_dir / "aggregated" / "user_analysis"
    months = _month_jsons(ua_dir)
    pulse = home_overview_builder.pulse_series_memo(data_dir, months)
    raw = home_overview_builder.build_overview(data_dir, month=month, pulse=pulse)
    return _overview_from_payload(raw)


def _overview_from_payload(payload: Dict[str, Any]) -> Overview:
    movers = payload.get("movers") or {}
    pulse = [PulsePoint(**p) for p in (payload.get("pulse") or [])]
    tiles = Tiles(**payload["tiles"]) if payload.get("tiles") else None
    return Overview(
        latest_month=payload.get("latest_month"),
        generated_at=payload.get("generated_at"),
        data_through=payload.get("data_through"),
        pulse=pulse,
        tiles=tiles,
        movers=Movers(
            razors=[Mover(**m) for m in movers.get("razors", [])],
            soaps=[Mover(**m) for m in movers.get("soaps", [])],
            blades=[Mover(**m) for m in movers.get("blades", [])],
        ),
    )
