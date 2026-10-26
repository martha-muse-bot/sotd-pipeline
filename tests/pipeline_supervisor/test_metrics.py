import json

from prometheus_client import REGISTRY

from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    parse_phase_durations,
    parse_phase_records,
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


# --- parse_phase_records ------------------------------------------------------


def test_parse_records_with_counts():
    r = parse_phase_records(SAMPLE_PHASE_STDOUT)
    assert r == {"fetch": 1234, "enrich": 900}


def test_parse_records_ignores_records_per_second():
    """'| 100 records/s' must not parse as a record count."""
    line = "  Phase 1 (fetch):   12.34s OK | 1,234 records | 100 records/s\n"
    assert parse_phase_records(line) == {"fetch": 1234}


def test_parse_records_empty_when_no_counts():
    out = "  Phase 1 (fetch):   12.34s OK\n  Phase 2 (extract):   0.56s OK\n"
    assert parse_phase_records(out) == {}


def test_parse_records_skips_failed_lines():
    out = "  Phase 1 (fetch):   12.34s OK | 1,234 records\n  Phase 2 (extract):   0.56s FAILED | 5 records\n"
    assert parse_phase_records(out) == {"fetch": 1234}


def test_new_gauges_registered():
    from sotd.pipeline_supervisor.metrics import (
        consecutive_failures,
        next_run_timestamp,
        phase_records,
        publish_failures_total,
        publish_last_success,
        runs_total,
    )

    phase_records.labels(phase="fetch", scope="monthly").set(100)
    publish_last_success.set(1700000000)
    publish_failures_total.inc()
    runs_total.labels(outcome="ok").inc()
    consecutive_failures.set(2)
    next_run_timestamp.set(1700000100)
    names = {m.name for m in REGISTRY.collect()}
    assert "sotd_pipeline_phase_records" in names
    assert "sotd_pipeline_publish_last_success_timestamp_seconds" in names
    assert "sotd_pipeline_publish_failures" in names  # Counter: _total stripped by the client
    assert "sotd_pipeline_runs" in names  # Counter: _total stripped by the client
    assert "sotd_pipeline_consecutive_failures" in names
    assert "sotd_pipeline_next_run_timestamp_seconds" in names


# --- run-state persistence ----------------------------------------------------


def test_persist_and_restore_roundtrip(tmp_path):
    from sotd.pipeline_supervisor.metrics import (
        catalog_catchup_success,
        consecutive_failures,
        last_run_timestamp,
        persist_metrics_state,
        publish_failures_total,
        publish_last_success,
        restore_metrics_state,
        runs_total,
    )

    state_file = tmp_path / "state" / ".metrics_state.json"
    last_run_timestamp.set(1700000000)
    publish_last_success.set(1700000100)
    catalog_catchup_success.set(1700000200)
    consecutive_failures.set(2)
    runs_total.labels(outcome="ok").inc(5)
    runs_total.labels(outcome="failed").inc(1)
    publish_failures_total.inc(3)

    persist_metrics_state(str(state_file))
    # Counters cannot be reset, so persist captures the RUNNING TOTAL and
    # restore re-adds it. The contract being tested: restore adds exactly the
    # persisted total to whatever the counter holds — across a real redeploy
    # the fresh container's counters start at 0, so the restore lands them at
    # the pre-redeploy total (continuity). Emulate that here by zeroing via a
    # fresh registry: assert against the persisted file's values instead of
    # deltas, with the counter's at-persist-time value as the base.
    after_inc_ok = runs_total._metrics[("ok",)]._value.get()
    after_inc_failed = runs_total._metrics[("failed",)]._value.get()
    after_inc_pf = publish_failures_total._value.get()
    persisted = json.loads(state_file.read_text())

    last_run_timestamp.set(0)
    publish_last_success.set(0)
    catalog_catchup_success.set(0)
    consecutive_failures.set(0)
    restore_metrics_state(str(state_file))

    assert last_run_timestamp._value.get() == 1700000000
    assert publish_last_success._value.get() == 1700000100
    assert catalog_catchup_success._value.get() == 1700000200
    assert consecutive_failures._value.get() == 2
    assert runs_total._metrics[("ok",)]._value.get() == after_inc_ok + persisted["runs_ok"]
    assert (
        runs_total._metrics[("failed",)]._value.get() == after_inc_failed + persisted["runs_failed"]
    )
    assert publish_failures_total._value.get() == after_inc_pf + persisted["publish_failures"]


def test_restore_missing_file_is_noop(tmp_path):
    from sotd.pipeline_supervisor.metrics import restore_metrics_state

    restore_metrics_state(str(tmp_path / "nonexistent.json"))  # no crash, no change


def test_restore_garbage_file_is_noop(tmp_path):
    from sotd.pipeline_supervisor.metrics import restore_metrics_state

    bad = tmp_path / "bad.json"
    bad.write_text("not json{")
    restore_metrics_state(str(bad))  # no crash


# --- state watcher ------------------------------------------------------------


def test_check_state_changed_applies_and_dedupes(tmp_path):
    from sotd.pipeline_supervisor.metrics import (
        check_state_changed,
        last_run_timestamp,
        persist_metrics_state,
    )

    f = tmp_path / "state.json"
    last_run_timestamp.set(1000)
    persist_metrics_state(str(f))
    mtime1 = check_state_changed(str(f), None)
    assert mtime1 is not None
    assert last_run_timestamp._value.get() == 1000  # applied

    # unchanged file: no re-apply — change the gauge, re-check, gauge untouched
    last_run_timestamp.set(0)
    mtime2 = check_state_changed(str(f), mtime1)
    assert mtime2 == mtime1
    assert last_run_timestamp._value.get() == 0  # not re-applied

    # changed file: re-applied
    last_run_timestamp.set(2000)
    persist_metrics_state(str(f))
    last_run_timestamp.set(0)
    check_state_changed(str(f), mtime2)
    assert last_run_timestamp._value.get() == 2000


def test_check_state_changed_missing_file(tmp_path):
    from sotd.pipeline_supervisor.metrics import check_state_changed

    assert check_state_changed(str(tmp_path / "nope.json"), None) is None


def test_persist_is_atomic_no_partial_reads(tmp_path):
    """persist writes via tmp+rename: a concurrent reader (the watcher) never
    sees a partial file."""
    from sotd.pipeline_supervisor.metrics import persist_metrics_state

    f = tmp_path / "state.json"
    persist_metrics_state(str(f))
    import json

    json.loads(f.read_text())  # valid JSON
    assert not f.with_suffix(".json.tmp").exists()  # tmp renamed away
