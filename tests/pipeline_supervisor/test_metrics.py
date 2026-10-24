from prometheus_client import REGISTRY

from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    parse_phase_durations,
    set_last_run_timestamp,
    start_metrics_server,
)

# Shape mirrors run.py's "Phase Breakdown" block (run.py:441): duration is
# %-6.2f padded, followed by the status mark and optional " | ..." fields.
SAMPLE_PHASE_STDOUT = """
Phase Breakdown:
  Phase 1 (fetch):   12.34s ✓ | 1,234 records | 100 records/s
  Phase 2 (extract):   0.56s ✓
  Phase 3 (match):   3.21s ✓
  Phase 4 (enrich):   1.11s ✓ | 900 records
  Phase 5 (aggregate):   2.00s ✓
============================================================
"""


def test_gauges_update():
    set_last_run_timestamp(1700000000)
    last_run_status.labels(phase="fetch").set(1)
    months_processed.set(2)
    catalog_catchup_success.set(1700000000)
    names = {m.name for m in REGISTRY.collect()}
    assert "sotd_pipeline_last_run_timestamp_seconds" in names
    assert "sotd_pipeline_last_run_status" in names
    assert "sotd_pipeline_months_processed" in names
    assert "sotd_pipeline_catalog_catchup_last_success_timestamp_seconds" in names


def test_status_gauge_takes_zero_on_failure():
    last_run_status.labels(phase="match").set(0)
    assert last_run_status.labels(phase="match")._value.get() == 0


def test_start_metrics_server_runs():
    start_metrics_server(8199)  # only starts a thread; no assertion crash = pass


# --- parse_phase_durations ---------------------------------------------------


def test_parse_multi_phase_output():
    d = parse_phase_durations(SAMPLE_PHASE_STDOUT)
    assert d == {
        "fetch": 12.34,
        "extract": 0.56,
        "match": 3.21,
        "enrich": 1.11,
        "aggregate": 2.00,
    }


def test_parse_single_phase():
    d = parse_phase_durations("  Phase 1 (fetch):   12.34s ✓")
    assert d == {"fetch": 12.34}


def test_parse_empty_and_malformed():
    assert parse_phase_durations("") == {}
    assert parse_phase_durations("no phases here\njust logs\n") == {}
    # malformed line variants: missing duration, non-numeric, wrong separator
    assert parse_phase_durations("  Phase 1 (fetch): OK\n") == {}
    assert parse_phase_durations("  Phase 1 (fetch): abc s ✓\n") == {}
    assert parse_phase_durations("Phase fetch: 1.00s ✓\n") == {}


def test_parse_skips_pathological_duration():
    """A multi-dot duration ("1.2.3") must be skipped, not crash the run."""
    out = parse_phase_durations(
        "Phase Breakdown:\n"
        "  Phase 1 (fetch):   12.34s ✓\n"
        "  Phase 2 (extract):   1.2.3s ✓\n"
        "  Phase 3 (match):   3.21s ✓\n"
    )
    assert out == {"fetch": 12.34, "match": 3.21}


def test_parse_failed_run_keeps_ok_phase_durations():
    """run.py stops at first failure; OK lines from a failed run are real work."""
    failed = (
        "Phase Breakdown:\n"
        "  Phase 1 (fetch):   12.34s ✓\n"
        "  Phase 2 (extract):   0.56s ✗\n"
        "\n"
        "Note: Pipeline failed partway through. Summary shows completed phases only.\n"
    )
    d = parse_phase_durations(failed)
    assert d == {"fetch": 12.34}


def test_phase_duration_gauge_exists():
    from sotd.pipeline_supervisor.metrics import phase_duration_seconds

    names = {m.name for m in REGISTRY.collect()}
    assert "sotd_pipeline_phase_duration_seconds" in names
    assert "sotd_pipeline_run_duration_seconds" in names
    phase_duration_seconds.labels(phase="fetch", scope="monthly").set(1.0)
    assert phase_duration_seconds.labels(phase="fetch", scope="monthly")._value.get() == 1.0
    phase_duration_seconds.labels(phase="match", scope="catchup").set(2.0)
    assert phase_duration_seconds.labels(phase="match", scope="catchup")._value.get() == 2.0
