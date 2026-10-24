"""Prometheus metrics for the nightly supervisor (scraped on metrics-net)."""

from __future__ import annotations

from prometheus_client import Gauge, start_http_server

last_run_timestamp = Gauge("sotd_pipeline_last_run_timestamp_seconds", "Epoch of last run start")
last_run_status = Gauge("sotd_pipeline_last_run_status", "1=ok 0=failed", ["phase"])
months_processed = Gauge("sotd_pipeline_months_processed", "Months processed in last run")
catalog_catchup_success = Gauge(
    "sotd_pipeline_catalog_catchup_last_success_timestamp_seconds",
    "Epoch of last successful all-months catch-up",
)


def set_last_run_timestamp(epoch: float) -> None:
    last_run_timestamp.set(epoch)


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
