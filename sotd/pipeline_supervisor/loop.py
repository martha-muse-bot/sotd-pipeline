"""Nightly supervisor loop: pull, sync catalogs, hash, run phases, publish, catch-up."""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from sotd.pipeline_supervisor.catalog_hash import catalog_hash
from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    parse_phase_durations,
    record_phase_durations,
    run_duration_seconds,
    set_last_run_timestamp,
)
from sotd.pipeline_supervisor.publish import publish_bundle

logger = logging.getLogger(__name__)

SCHEDULE_HOUR = 2
TZ = ZoneInfo("America/Chicago")
HASH_FILE = ".catalog_hash"

# Operator-authored match inputs synced from the repo checkout (/app/data)
# into the data volume (/data) after each successful git pull. This is the
# set match actually consumes: the catalogs its loaders open, correct_matches
# (pre-validated matches, checked first), and the operator override files
# (thread_overrides feeds fetch; extract/enrichment_overrides and
# intentionally_unmatched feed extract/match). Anything else in the checkout
# (aggregated output, wsdb, non-match yamls) never reaches /data via the
# supervisor — it arrives only through the one-time seed.
MATCH_INPUT_PATTERNS = (
    "blades.yaml",
    "razors.yaml",
    "soaps.yaml",
    "brushes.yaml",
    "handles.yaml",
    "knots.yaml",
    "brush_scoring_config.yaml",
    "correct_matches/*.yaml",
    "thread_overrides.yaml",
    "extract_overrides.yaml",
    "enrichment_overrides.yaml",
    "intentionally_unmatched.yaml",
)


@dataclass
class RunResult:
    phases: dict = field(default_factory=dict)
    months_processed: int = 0
    catchup_ran: bool = False
    catchup_ok: bool = False
    published: bool = False


def sync_match_inputs(src_dir: Path, data_dir: Path) -> int:
    """Copy operator-authored match inputs from the checkout into the data volume.

    Only files present in the source are copied (the volume may hold more);
    target directories are created as needed. Returns the number of files
    copied. A copy failure raises and aborts the night before the hash is
    computed — a half-synced volume must never look converged.
    """
    copied = 0
    for pattern in MATCH_INPUT_PATTERNS:
        for src in sorted(src_dir.glob(pattern)):
            if not src.is_file():
                continue
            dst = data_dir / src.relative_to(src_dir)
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
    return copied


def run_nightly(
    *,
    repo_dir: Path,
    data_dir: Path,
    bundle_dir: Path,
    runner=subprocess.run,
    months: tuple[str, ...],
    all_months: tuple[str, str],
) -> RunResult:
    result = RunResult()
    run_start = time.monotonic()
    pull = _subprocess(runner, ["git", "-C", str(repo_dir), "pull", "--ff-only"], repo_dir)
    if pull is None or pull.returncode != 0:
        logger.error("git pull failed: %s", "crashed" if pull is None else pull.stderr)
        last_run_status.labels(phase="pull").set(0)
        result.phases["pull"] = False
        return result
    last_run_status.labels(phase="pull").set(1)
    result.phases["pull"] = True

    # Catalog delivery: the pull updated /app/data only; match reads /data.
    # Sync the operator-authored match inputs, THEN hash the volume.
    sync_match_inputs(repo_dir / "data", data_dir)

    stored = _read_hash(data_dir)
    new_hash = catalog_hash(data_dir)
    hash_changed = stored is None or stored != new_hash

    # One command per month: fetch through aggregate. A failed fetch fails
    # the whole month before match ever runs on stale data (user ruling
    # 2026-10-24) — intra-month ordering is delegated to run.py.
    monthly: dict[str, bool] = {}
    for month in months:
        monthly[month] = _run_monthly(runner, repo_dir, month)
    _set_phase_status(result, "fetch", monthly)
    ok = bool(monthly) and all(monthly.values())
    if ok:
        result.months_processed = len(monthly)
        # Phase failure aborts before publish — the public data keeps the
        # last good bundle, never a hole.
        result.published = publish_bundle(data_dir, bundle_dir)
    _set_phase_status(result, "publish", {"daily": result.published})

    if hash_changed:
        result.catchup_ran = True
        first, last = all_months
        catchup = _subprocess(
            runner,
            [
                "python",
                "run.py",
                "--range",
                f"{first}:{last}",
                "--force",
                "match:aggregate",
            ],
            repo_dir,
        )
        result.catchup_ok = catchup is not None and catchup.returncode == 0
        last_run_status.labels(phase="catchup").set(1 if result.catchup_ok else 0)
        if catchup is not None and catchup.stdout:
            _record_phases(catchup.stdout, "catchup", result.catchup_ok)
        if result.catchup_ok:
            if publish_bundle(data_dir, bundle_dir):
                (data_dir / HASH_FILE).write_text(new_hash)
                catalog_catchup_success.set(time.time())
            else:
                result.catchup_ok = False  # publish failed: retry hash next night
                _set_phase_status(result, "publish", {"daily": result.published, "catchup": False})
    months_processed.set(result.months_processed)
    run_duration_seconds.set(time.monotonic() - run_start)
    return result


def _run_monthly(runner, repo_dir: Path, month: str) -> bool:
    proc = _subprocess(
        runner,
        ["python", "run.py", "--month", month, "--force", "fetch:aggregate"],
        repo_dir,
    )
    ok = proc is not None and proc.returncode == 0
    if proc is None:
        logger.exception("fetch:aggregate crashed for %s", month)
    elif not ok:
        logger.error("fetch:aggregate failed for %s: %s", month, proc.stderr)
    if proc is not None and proc.stdout:
        _record_phases(proc.stdout, "monthly", ok)
    return ok


def _record_phases(stdout: str, context: str, ok: bool) -> None:
    """Parse phase durations from run.py stdout and set the gauges.

    OK phases from a failed run are emitted too (real completed work). No
    parseable phase lines — warn and emit nothing; metrics must never crash
    or perturb the run itself.
    """
    durations = parse_phase_durations(stdout)
    if not durations:
        logger.warning(
            "no phase durations parsed from %s run.py output (ok=%s) — "
            "run.py summary format may have drifted",
            context,
            ok,
        )
        return
    record_phase_durations(durations, context=context)


def _set_phase_status(result: RunResult, phase: str, outcomes: dict) -> None:
    """Any-failure semantics: a phase label ends 0 if ANY month failed, else 1."""
    if not outcomes:
        return
    ok = all(outcomes.values())
    result.phases[phase] = ok
    last_run_status.labels(phase=phase).set(1 if ok else 0)


def _read_hash(data_dir: Path) -> str | None:
    hash_path = data_dir / HASH_FILE
    if not hash_path.is_file():
        return None
    try:
        return hash_path.read_text().strip()
    except OSError:
        logger.exception("could not read %s", hash_path)
        return None


def _subprocess(runner, cmd: list[str], repo_dir: Path):
    """Run one subprocess with the injected runner, crashing calls become None."""
    try:
        return runner(cmd, capture_output=True, text=True, cwd=str(repo_dir))
    except Exception:
        logger.exception("subprocess crashed: %s", cmd)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Nightly pipeline supervisor loop")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one nightly cycle immediately, then exit (smoke testing)",
    )
    args = parser.parse_args(sys.argv[1:])

    if not args.once:
        # The metrics port belongs to the long-running loop process; a --once
        # smoke run inside the same container must not try to take it.
        from sotd.pipeline_supervisor.metrics import start_metrics_server

        start_metrics_server(8000)
    data_dir = Path("/data")
    repo_dir = Path("/app")
    bundle_dir = Path("/bundle")
    while True:
        now = datetime.now(TZ)
        target = now.replace(hour=SCHEDULE_HOUR, minute=0, second=0, microsecond=0)
        if target <= now:
            target = _next_day(target)
        if args.once:
            # Smoke mode: skip the wait, run one cycle now, exit.
            target = now
        time.sleep((target - now).total_seconds())
        set_last_run_timestamp(time.time())
        try:
            res = run_nightly(
                repo_dir=repo_dir,
                data_dir=data_dir,
                bundle_dir=bundle_dir,
                months=_current_and_prior(target),
                all_months=_all_months(data_dir),
            )
            logger.info("nightly run: %s", res)
        except Exception:
            logger.exception("nightly run crashed; sleeping until tomorrow")
        if args.once:
            break


def _next_day(dt: datetime) -> datetime:
    return (dt + timedelta(days=1)).replace(hour=SCHEDULE_HOUR, minute=0, second=0, microsecond=0)


def _current_and_prior(dt: datetime) -> tuple[str, ...]:
    prior = dt.replace(day=1)
    prior_end = prior - timedelta(days=1)
    return (dt.strftime("%Y-%m"), prior_end.strftime("%Y-%m"))


def _all_months(data_dir: Path) -> tuple[str, str]:
    months = sorted(p.stem for p in (data_dir / "enriched").glob("????-??.json"))
    return (months[0], months[-1]) if months else ("2016-05", "2016-05")


if __name__ == "__main__":
    main()
