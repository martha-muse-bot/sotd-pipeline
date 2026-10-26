"""Prometheus metrics for the nightly supervisor (scraped on metrics-net)."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from pathlib import Path

from prometheus_client import Counter, Gauge, start_http_server

logger = logging.getLogger(__name__)

last_run_timestamp = Gauge("sotd_pipeline_last_run_timestamp_seconds", "Epoch of last run start")
last_run_status = Gauge("sotd_pipeline_last_run_status", "1=ok 0=failed", ["phase"])
months_processed = Gauge("sotd_pipeline_months_processed", "Months processed in last run")
catalog_catchup_success = Gauge(
    "sotd_pipeline_catalog_catchup_last_success_timestamp_seconds",
    "Epoch of last successful all-months catch-up",
)
phase_duration_seconds = Gauge(
    "sotd_pipeline_phase_duration_seconds",
    "Duration of each pipeline phase parsed from run.py output",
    ["phase", "scope"],
)
run_duration_seconds = Gauge(
    "sotd_pipeline_run_duration_seconds",
    "Whole nightly cycle wall time (pull through final publish)",
)
phase_records = Gauge(
    "sotd_pipeline_phase_records",
    "Record count parsed from run.py's phase lines (last-run semantics)",
    ["phase", "scope"],
)
publish_last_success = Gauge(
    "sotd_pipeline_publish_last_success_timestamp_seconds",
    "Epoch of the last successful verify-gated publish",
)
publish_failures_total = Counter(
    "sotd_pipeline_publish_failures_total",
    "Verify-gated publish attempts that failed",
)
runs_total = Counter("sotd_pipeline_runs_total", "Nightly runs by outcome", ["outcome"])
consecutive_failures = Gauge(
    "sotd_pipeline_consecutive_failures",
    "Consecutive nightly runs that ended in failure (0 after a success)",
)
next_run_timestamp = Gauge(
    "sotd_pipeline_next_run_timestamp_seconds",
    "Epoch of the scheduled next nightly run",
)

# run.py's Phase Breakdown line (run.py:441):
#   "  Phase 1 (fetch):   12.34s ✓ | 1,234 records"
# The status mark and trailing fields are ignored. A FAILED run's summary
# marks the failed phase with ✗ — that line is skipped (no duration metric
# for a phase that failed); earlier OK phases are kept, since that time was
# really spent.
_PHASE_LINE_RE = re.compile(
    r"Phase\s+\d+\s+\((?P<phase>[a-z_]+)\):\s+(?P<dur>[\d.]+)s"
    r"(?:[^|]*\|\s*(?P<records>[\d,]+)\s+records(?=\s*\||\s*$))?"
)
_FAILED_MARKS = ("✗", "✘", "FAILED")


def parse_phase_durations(stdout: str) -> dict[str, float]:
    """Parse per-phase durations from run.py's "Phase Breakdown" stdout.

    Returns {phase_name: duration_seconds} in print order (later duplicates
    overwrite earlier ones — per-phase names are unique within one run).
    Tolerant of whitespace and trailing fields. A phase line marked failed
    (✗/FAILED) is excluded — a failed phase gets NO duration metric; OK
    phases from a FAILED run still parse, as that work really happened.
    Malformed/missing lines simply don't match. An empty dict means nothing
    parseable — the caller logs a warning and emits nothing.
    """
    out: dict[str, float] = {}
    for line in _phase_lines(stdout):
        if m := _PHASE_LINE_RE.search(line):
            try:
                out[m.group("phase")] = float(m.group("dur"))
            except ValueError:
                # pathological duration (e.g. "1.2.3") — skip the line, never
                # let metrics parsing abort the run
                continue
    return out


def _phase_lines(stdout: str) -> list[str]:
    return [ln for ln in (stdout or "").splitlines() if not any(mk in ln for mk in _FAILED_MARKS)]


def parse_phase_records(stdout: str) -> dict[str, int]:
    """Parse per-phase record counts from run.py's "Phase Breakdown" stdout.

    Only phases whose line carries the "| N records" field appear (duration-
    only lines have no count). Same failed-line exclusion as durations. A
    sudden record-count collapse on a passing run is a data problem the
    ok/failed gauges cannot show — this gauge is that tripwire.
    """
    out: dict[str, int] = {}
    for line in _phase_lines(stdout):
        if m := _PHASE_LINE_RE.search(line):
            raw = m.group("records")
            if raw is None:
                continue
            try:
                out[m.group("phase")] = int(raw.replace(",", ""))
            except ValueError:
                continue
    return out


def record_phase_durations(durations: dict[str, float], *, context: str) -> None:
    """Set phase_duration_seconds{phase, scope} for each parsed phase.

    `context` doubles as the scope label: "monthly" for per-month
    fetch:aggregate runs, "catchup" for the all-months match:aggregate run —
    match over 2 months isn't comparable to match over 159+.

    A FAILED subprocess's OK phases are emitted (real completed work); the
    failing phase itself gets no metric — run.py stops at first failure and
    its duration is not printed as a completed phase.
    """
    for phase, dur in durations.items():
        phase_duration_seconds.labels(phase=phase, scope=context).set(dur)
        logger.debug("phase duration (scope=%s): %s=%.2fs", context, phase, dur)


def set_last_run_timestamp(epoch: float) -> None:
    last_run_timestamp.set(epoch)


# --- run-state persistence ----------------------------------------------------
#
# A redeploy recreates the container and resets every gauge to 0 — the
# freshness anchor (publish_last_success) would read as "never published",
# tripping the dashboard's 26h threshold on deploy day. Persist the run-state
# gauges/counters to the /data volume and restore them on boot.

STATE_KEYS = (
    "last_run_timestamp",
    "publish_last_success",
    "catalog_catchup_success",
    "consecutive_failures",
    "runs_ok",
    "runs_failed",
    "publish_failures",
)


def default_state_path() -> str:
    return os.environ.get("SOTD_METRICS_STATE", "/data/.metrics_state.json")


def persist_metrics_state(path: str | None = None) -> None:
    """Write the run-state gauges/counters to the state file (best-effort)."""
    path = path or default_state_path()
    payload = {
        "last_run_timestamp": last_run_timestamp._value.get(),
        "publish_last_success": publish_last_success._value.get(),
        "catalog_catchup_success": catalog_catchup_success._value.get(),
        "consecutive_failures": consecutive_failures._value.get(),
        "runs_ok": (
            runs_total._metrics.get(("ok",), None)._value.get()
            if runs_total._metrics.get(("ok",), None) is not None
            else 0
        ),
        "runs_failed": (
            runs_total._metrics.get(("failed",), None)._value.get()
            if runs_total._metrics.get(("failed",), None) is not None
            else 0
        ),
        "publish_failures": publish_failures_total._value.get(),
    }
    try:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        tmp = Path(str(path) + ".tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, path)  # atomic: the watcher must never read a partial file
    except OSError:
        logger.exception("could not persist metrics state to %s — gauges reset on next boot", path)


def restore_metrics_state(path: str | None = None) -> None:
    """Restore run-state gauges/counters from the state file on boot."""
    path = path or default_state_path()
    p = Path(path)
    if not p.is_file():
        return
    try:
        payload = json.loads(p.read_text())
    except (OSError, ValueError):
        logger.exception("could not read metrics state from %s", path)
        return
    for key in STATE_KEYS:
        value = payload.get(key)
        if value is None:
            continue
        if key == "last_run_timestamp":
            last_run_timestamp.set(value)
        elif key == "publish_last_success":
            publish_last_success.set(value)
        elif key == "catalog_catchup_success":
            catalog_catchup_success.set(value)
        elif key == "consecutive_failures":
            consecutive_failures.set(value)
        elif key == "runs_ok":
            runs_total.labels(outcome="ok").inc(value)
        elif key == "runs_failed":
            runs_total.labels(outcome="failed").inc(value)
        elif key == "publish_failures":
            publish_failures_total.inc(value)
    logger.info("restored metrics state from %s", path)


def check_state_changed(path: str, last_mtime: float | None) -> float | None:
    """Apply the state file if its mtime changed; return the mtime to remember.

    The synchronous core of the watcher: any process that persists state
    (the nightly loop, a --once smoke run) moves the mtime, and the next
    check re-applies it to the live gauges. Unchanged file → returns the
    mtime unchanged, applies nothing. Missing file → None.
    """
    p = Path(path)
    if not p.is_file():
        return None
    mtime = p.stat().st_mtime
    if last_mtime is not None and mtime == last_mtime:
        return last_mtime
    restore_metrics_state(path)
    return mtime


def start_state_watcher(path: str | None = None, interval: float = 30.0) -> None:
    """Poll the state file in a daemon thread, refreshing gauges on change.

    This is what makes manual/--once runs visible to the live /metrics: they
    are separate processes whose gauge updates die with them, but their state
    files persist — the watcher applies those within one interval. The
    nightly loop's own writes also pass through here (idempotent re-apply).
    """
    path = path or default_state_path()
    last_mtime = Path(path).stat().st_mtime if Path(path).is_file() else None

    def _watch() -> None:
        nonlocal last_mtime
        while True:
            time.sleep(interval)
            try:
                last_mtime = check_state_changed(path, last_mtime)
            except Exception:
                logger.exception("state-file watch failed; continuing")

    thread = threading.Thread(target=_watch, name="sotd-metrics-state-watch", daemon=True)
    thread.start()


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
