from prometheus_client import REGISTRY

from sotd.pipeline_supervisor.metrics import (
    catalog_catchup_success,
    last_run_status,
    months_processed,
    set_last_run_timestamp,
    start_metrics_server,
)


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
