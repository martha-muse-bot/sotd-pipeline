from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List


def _audit_months(months: list[tuple[int, int]], out_dir: Path) -> dict:
    """
    For each (year, month), check for expected threads/comments files,
    and also parse threads files for missing days in metadata.
    Returns:
        {
            "missing_files": [...],
            "missing_days": {"YYYY-MM": [list of ISO days]},
            "checked_months": int,
        }
    """
    missing_files: List[str] = []
    missing_days: Dict[str, List[str]] = {}
    out = Path(out_dir)
    checked_months = 0

    for year, month in months:
        yyyymm = f"{year:04d}-{month:02d}"
        threads_path = out / "threads" / f"{yyyymm}.json"
        comments_path = out / "comments" / f"{yyyymm}.json"
        # File checks
        found_threads = threads_path.exists()
        found_comments = comments_path.exists()
        if not found_threads:
            missing_files.append(str(threads_path.relative_to(out)))
        if not found_comments:
            missing_files.append(str(comments_path.relative_to(out)))
        # Metadata extraction
        if found_threads:
            checked_months += 1
            try:
                data = json.loads(threads_path.read_text())
                meta = data.get("meta", {})
                m_days = meta.get("missing_days", [])
                if not isinstance(m_days, list):
                    m_days = []
                missing_days[yyyymm] = list(m_days)
            except Exception:
                import calendar

                num_days = calendar.monthrange(year, month)[1]
                missing_days[yyyymm] = [f"{yyyymm}-{day:02d}" for day in range(1, num_days + 1)]
    return {
        "missing_files": missing_files,
        "missing_days": missing_days,
        "checked_months": checked_months,
    }


def list_available_months(out_dir: Path) -> list[str]:
    """
    Scans both threads/ and comments/ subdirectories in out_dir.
    Returns a sorted list of all unique months (YYYY-MM) for which at least one file exists.
    """
    out = Path(out_dir)
    months: set[str] = set()
    for subdir in ["threads", "comments"]:
        dir_path = out / subdir
        if not dir_path.is_dir():
            continue
        for file in dir_path.glob("*.json"):
            # Accept files named 'YYYY-MM.json'
            name = file.stem
            if len(name) == 7 and name[4] == "-" and name[:4].isdigit() and name[5:].isdigit():
                months.add(name)
    return sorted(months)
