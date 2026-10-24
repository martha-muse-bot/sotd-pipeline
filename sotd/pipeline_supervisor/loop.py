"""Nightly supervisor loop: pull, hash, run phases, publish, catch-up."""

from __future__ import annotations

import argparse
import logging
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
    set_last_run_timestamp,
)
from sotd.pipeline_supervisor.publish import publish_bundle

logger = logging.getLogger(__name__)

SCHEDULE_HOUR = 2
TZ = ZoneInfo("America/Chicago")
HASH_FILE = ".catalog_hash"


@dataclass
class RunResult:
    phases: dict = field(default_factory=dict)
    months_processed: int = 0
    catchup_ran: bool = False
    catchup_ok: bool = False
    published: bool = False


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
    pull = _subprocess(runner, ["git", "-C", str(repo_dir), "pull", "--ff-only"], repo_dir)
    if pull is None or pull.returncode != 0:
        logger.error("git pull failed: %s", "crashed" if pull is None else pull.stderr)
        last_run_status.labels(phase="pull").set(0)
        result.phases["pull"] = False
        return result
    last_run_status.labels(phase="pull").set(1)
    result.phases["pull"] = True

    stored = _read_hash(data_dir)
    new_hash = catalog_hash(data_dir)
    hash_changed = stored is None or stored != new_hash

    ok = True
    for month in months:
        for phase_range in ("fetch:extract", "match:aggregate"):
            ok &= _run_phase(runner, repo_dir, month, phase_range, result)

    if ok:
        result.published = publish_bundle(data_dir, bundle_dir)

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
        if result.catchup_ok:
            if publish_bundle(data_dir, bundle_dir):
                (data_dir / HASH_FILE).write_text(new_hash)
                catalog_catchup_success.set(time.time())
            else:
                result.catchup_ok = False  # publish failed: retry hash next night
    months_processed.set(result.months_processed)
    return result


def _run_phase(runner, repo_dir: Path, month: str, phase_range: str, result: RunResult) -> bool:
    phase = phase_range.split(":")[0]
    proc = _subprocess(
        runner,
        ["python", "run.py", "--month", month, "--force", phase_range],
        repo_dir,
    )
    ok = proc is not None and proc.returncode == 0
    if proc is None:
        logger.exception("%s crashed for %s", phase_range, month)
    elif not ok:
        logger.error("%s failed for %s: %s", phase_range, month, proc.stderr)
    result.phases[phase] = ok
    last_run_status.labels(phase=phase).set(1 if ok else 0)
    if ok:
        result.months_processed += 1
    return ok


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
