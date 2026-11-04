"""Deduplicate records by *id*, keeping newest ``created_utc`` (last write wins ties)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List


def _iso_to_dt(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(timezone.utc)


_MIN_TS = datetime.min.replace(tzinfo=timezone.utc)


def _safe_ts(record: dict) -> datetime:
    """Parse ``created_utc`` defensively.

    Missing or malformed timestamps sort as oldest instead of raising, so one
    bad record cannot abort the whole month merge.
    """
    try:
        return _iso_to_dt(record["created_utc"])
    except (KeyError, TypeError, ValueError, AttributeError):
        return _MIN_TS


def merge_records(existing: List[dict], new: List[dict]) -> List[dict]:
    """
    Merge *new* onto *existing* by ``id``.

    • For duplicates, the new record wins on equal or later ``created_utc``
      (last write wins — Reddit's ``created_utc`` never changes, so this is
      how re-fetches pick up edited titles/bodies/authors).
    • Records with missing or malformed ``created_utc`` are quarantined, not
      fatal: they sort as oldest and never raise.
    • Return list sorted by ``created_utc`` ascending.
    """
    bucket: Dict[str, dict[str, Any]] = {r["id"]: r for r in existing}
    for rec in new:
        rid = rec["id"]
        if rid not in bucket or _safe_ts(rec) >= _safe_ts(bucket[rid]):
            bucket[rid] = rec
    return sorted(bucket.values(), key=lambda r: str(r.get("created_utc") or ""))
