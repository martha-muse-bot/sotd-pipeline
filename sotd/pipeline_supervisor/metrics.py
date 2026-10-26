"""Prometheus metrics for the nightly supervisor (scraped on metrics-net)."""

from __future__ import annotations

import logging
import re

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


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
