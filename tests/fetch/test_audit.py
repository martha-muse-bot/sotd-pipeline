from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from sotd.fetch.audit import _audit_months


def make_threads_file(data_dir: Path, year: int, month: int, missing_days):
    threads_dir = data_dir / "threads"
    threads_dir.mkdir(parents=True, exist_ok=True)
    yyyymm = f"{year:04d}-{month:02d}"
    data = {
        "data": [],
        "meta": {
            "month": yyyymm,
            "missing_days": missing_days,
        },
    }
    (threads_dir / f"{yyyymm}.json").write_text(json.dumps(data))


def make_comments_file(data_dir: Path, year: int, month: int):
    comments_dir = data_dir / "comments"
    comments_dir.mkdir(parents=True, exist_ok=True)
    yyyymm = f"{year:04d}-{month:02d}"
    data = {
        "data": [],
        "meta": {
            "month": yyyymm,
        },
    }
    (comments_dir / f"{yyyymm}.json").write_text(json.dumps(data))


def test_audit_months_missing(tmp_path: Path):
    # Setup: 3 months
    # 2024-04: both files, no missing days
    # 2024-05: threads file with missing days, comments file missing
    # 2024-06: both files missing

    make_threads_file(tmp_path, 2024, 4, [])
    make_comments_file(tmp_path, 2024, 4)
    make_threads_file(tmp_path, 2024, 5, ["2024-05-07"])
    # 2024-05 comments file not created
    # 2024-06 neither file created

    months = [(2024, 4), (2024, 5), (2024, 6)]
    result = _audit_months(months, str(tmp_path))
    # Check missing files
    assert sorted(result["missing_files"]) == [
        "comments/2024-05.json",
        "comments/2024-06.json",
        "threads/2024-06.json",
    ]
    # Check missing days
    assert result["missing_days"]["2024-04"] == []
    assert result["missing_days"]["2024-05"] == ["2024-05-07"]
    # 2024-06 not present, as no threads file
    assert "2024-06" not in result["missing_days"]
    # Checked months count
    assert result["checked_months"] == 2


def test_audit_months_json_error(tmp_path: Path):
    # Corrupt a threads file
    threads_dir = tmp_path / "threads"
    threads_dir.mkdir()
    file = threads_dir / "2025-01.json"
    file.write_text("{invalid json")
    months = [(2025, 1)]
    result = _audit_months(months, str(tmp_path))
    # Should show all days missing for missing_days (Jan has 31 days)
    expected_days = [f"2025-01-{day:02d}" for day in range(1, 32)]
    assert result["missing_days"]["2025-01"] == expected_days
    assert result["missing_files"] == ["comments/2025-01.json"]
    assert result["checked_months"] == 1


# --- CLI tests for --list-months ---


def run_cli_with_list_months(tmp_path, extra_files=None):
    """Helper to run CLI in a temp dir with optional files, returns (stdout, code)."""
    data_dir = tmp_path / "data"
    threads_dir = data_dir / "threads"
    comments_dir = data_dir / "comments"
    threads_dir.mkdir(parents=True)
    comments_dir.mkdir(parents=True)
    if extra_files:
        for f in extra_files:
            (data_dir / f).parent.mkdir(parents=True, exist_ok=True)
            (data_dir / f).write_text("{}")
    print("DEBUG: JSON files written to data_dir:")
    for file in data_dir.rglob("*.json"):
        print("  ", file.relative_to(data_dir))
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parent.parent.parent)
    cli = [sys.executable, "-m", "sotd.fetch.run", "--data-dir", str(data_dir), "--list-months"]
    result = subprocess.run(cli, capture_output=True, text=True, env=env, check=True)
    return result.stdout, result.returncode


def test_cli_list_months_empty(tmp_path):
    """If no files exist, --list-months prints nothing and exits 0."""
    out, code = run_cli_with_list_months(tmp_path)
    assert out.strip() == ""
    assert code == 0


def test_cli_list_months_some(tmp_path):
    """If files exist in threads/comments, --list-months prints all unique months sorted."""
    files = [
        "threads/2025-04.json",
        "threads/2025-06.json",
        "comments/2025-05.json",
        "comments/2025-04.json",
        "threads/2024-12.json",
    ]
    out, code = run_cli_with_list_months(tmp_path, files)
    months = out.strip().splitlines()
    assert months == sorted(set(["2024-12", "2025-04", "2025-05", "2025-06"]))
    assert code == 0
