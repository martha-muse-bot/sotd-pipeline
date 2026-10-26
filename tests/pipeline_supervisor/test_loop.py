import subprocess
from pathlib import Path

import pytest

from sotd.pipeline_supervisor.loop import run_nightly, sync_match_inputs
from sotd.pipeline_supervisor.metrics import (
    phase_duration_seconds,
    run_duration_seconds,
)

PHASE_STDOUT = (
    "Phase Breakdown:\n"
    "  Phase 1 (fetch):   12.34s OK\n"
    "  Phase 2 (extract):   0.56s OK\n"
    "  Phase 3 (match):   3.21s OK\n"
    "  Phase 4 (enrich):   1.11s OK\n"
    "  Phase 5 (aggregate):   2.00s OK\n"
)
CATCHUP_STDOUT = (
    "Phase Breakdown:\n"
    "  Phase 1 (match):   9.00s OK\n"
    "  Phase 2 (enrich):   5.00s OK\n"
    "  Phase 3 (aggregate):   4.00s OK\n"
)


def fake_runner_ok(cmd, **kw):
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def setup_dirs(tmp_path: Path):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    bundle = tmp_path / "bundle"
    for d in (repo, data, bundle):
        d.mkdir()
    # Operator-authored match inputs in the checkout (/app/data)
    app_data = repo / "data"
    app_data.mkdir()
    (app_data / "soaps.yaml").write_text("a: 1\n")
    (app_data / "correct_matches").mkdir()
    (app_data / "correct_matches" / "soap.yaml").write_text("m: [x]\n")
    # Bundle source the real publish verifier accepts (happy path + catch-up publish).
    agg = data / "aggregated"
    for sub in ("product_usage", "user_analysis", "annual"):
        (agg / sub).mkdir(parents=True)
        (agg / sub / "2026-10.json").write_text("{}")
    (agg / "2026-10.json").write_text("{}")
    return repo, data, bundle


def test_run_nightly_happy_path_no_catchup(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")  # stored == new -> no drift, no catch-up
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert result.published is True
    assert result.catchup_ran is False
    assert result.phases["pull"] is True
    assert result.phases["fetch"] is True
    assert result.phases["publish"] is True
    # months_processed counts MONTHS (2 on a 2-month night), not phase-runs
    assert result.months_processed == 2


def test_single_monthly_command_per_month(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    pipeline_calls = [c for c in calls if c[:2] == ["python", "run.py"]]
    assert pipeline_calls == [
        ["python", "run.py", "--month", "2026-10", "--force", "fetch:aggregate"],
        ["python", "run.py", "--month", "2026-09", "--force", "fetch:aggregate"],
    ]


def test_sync_copies_catalog_updates_into_data_volume(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("old")
    # Catalog update arrives via git pull: /app/data/soaps.yaml changed
    (repo / "data" / "soaps.yaml").write_text("a: 2\n")
    monkeypatch.setattr(
        "sotd.pipeline_supervisor.loop.catalog_hash",
        lambda d: catalog_hash_of({"soaps.yaml": "a: 2\n"}),
    )
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.catchup_ran is True  # hash differs from stored -> catch-up fires


def catalog_hash_of(files: dict) -> str:
    import hashlib

    digest = hashlib.sha256()
    for rel in sorted(files):
        fhash = hashlib.sha256(files[rel].encode()).hexdigest()
        digest.update(f"{rel}:{fhash}\n".encode())
    return digest.hexdigest()


def test_code_only_pull_yields_identical_hash_no_catchup(tmp_path):
    repo, data, bundle = setup_dirs(tmp_path)
    # First night: sync runs, hash saved over the synced volume
    from sotd.pipeline_supervisor.catalog_hash import catalog_hash

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    stored = (data / ".catalog_hash").read_text()
    # Code-only pull (no catalog change in /app/data): hash is identical
    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert (data / ".catalog_hash").read_text() == stored
    assert catalog_hash(data) == stored


def test_hash_not_saved_on_catchup_failure(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    def runner(cmd, **kw):
        # fail the all-months pass (identified by --range in cmd)
        if "--range" in cmd:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.catchup_ran is True
    assert result.catchup_ok is False
    assert not (data / ".catalog_hash").exists()


def test_hash_saved_after_successful_catchup(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.catchup_ran is True and result.catchup_ok is True
    assert (data / ".catalog_hash").read_text() == "h1"


def test_supervisor_survives_phase_crash(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    def runner(cmd, **kw):
        if cmd[:3] == ["git", "-C", str(repo)]:
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise RuntimeError("subprocess exploded")  # first phase command

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.published is False
    assert result.phases["pull"] is True
    assert result.phases["fetch"] is False
    assert result.months_processed == 0
    assert result.catchup_ran is True  # drift branch still runs (per-brief order)
    assert result.catchup_ok is False  # catch-up crashes too -> hash not saved
    assert not (data / ".catalog_hash").exists()


def test_any_month_failure_masks_fetch_label(tmp_path, monkeypatch):
    """A failed month must not be overwritten by a later successful month."""
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")

    def runner(cmd, **kw):
        if "--month" in cmd and cmd[cmd.index("--month") + 1] == "2026-10":
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert result.phases["fetch"] is False  # any-failure across months
    assert result.months_processed == 0  # not all months succeeded
    assert result.phases["publish"] is False  # nothing published on a failed night


def test_sync_match_inputs_scopes_to_match_consumed_set(tmp_path: Path):
    src = tmp_path / "appdata"
    dst = tmp_path / "data"
    src.mkdir()
    dst.mkdir()
    (src / "soaps.yaml").write_text("a: 1\n")
    (src / "blades.yaml").write_text("b: 1\n")
    (src / "correct_matches").mkdir()
    (src / "correct_matches" / "razor.yaml").write_text("r: [x]\n")
    (src / "thread_overrides.yaml").write_text("include: {}\n")
    # NOT in the sync set: aggregated output, wsdb, backups
    (src / "aggregated").mkdir()
    (src / "aggregated" / "2026-10.json").write_text("{}")
    (src / "wsdb").mkdir()
    (src / "wsdb" / "software.json").write_text("{}")
    (src / "razors.yaml.backup").write_text("junk\n")
    copied = sync_match_inputs(src, dst)
    assert copied == 4
    assert (dst / "soaps.yaml").read_text() == "a: 1\n"
    assert (dst / "correct_matches" / "razor.yaml").exists()
    assert not (dst / "aggregated").exists()
    assert not (dst / "wsdb").exists()
    assert not (dst / "razors.yaml.backup").exists()


def test_sync_match_inputs_creates_dirs_and_skips_absent(tmp_path: Path):
    src = tmp_path / "appdata"
    dst = tmp_path / "data"
    src.mkdir()
    dst.mkdir()
    (src / "correct_matches").mkdir()
    (src / "correct_matches" / "soap.yaml").write_text("m: [x]\n")
    assert sync_match_inputs(src, dst) == 1
    assert (dst / "correct_matches" / "soap.yaml").exists()
    # Patterns with no source file are simply skipped (volume may hold more)
    assert not (dst / "soaps.yaml").exists()


def test_once_flag_exists():
    import inspect

    from sotd.pipeline_supervisor import loop

    assert "once" in inspect.getsource(loop.main)


def test_once_mode_skips_metrics_server(monkeypatch):
    """--once must not bind the metrics port (owned by the running loop)."""
    import inspect

    from sotd.pipeline_supervisor import loop

    src = inspect.getsource(loop.main)
    assert "start_metrics_server" in src
    # the call is guarded by the once check
    assert "if not args.once:" in src


def test_git_pull_failure_skips_run(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    def runner(cmd, **kw):
        if cmd[:3] == ["git", "-C", str(repo)]:
            return subprocess.CompletedProcess(cmd, 128, stdout="", stderr="network down")
        raise AssertionError("pipeline must not run after pull failure")

    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    assert result.published is False
    assert result.phases["pull"] is False


# --- phase-duration metrics ---------------------------------------------------


def _clear_phase_gauges():
    phase_duration_seconds.clear()
    run_duration_seconds._value.set(0.0)


def test_phase_durations_set_from_monthly_and_catchup(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    _clear_phase_gauges()

    def runner(cmd, **kw):
        out = CATCHUP_STDOUT if "--range" in cmd else PHASE_STDOUT
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2016-05"),
    )
    # monthly runs emit scope="monthly"; catch-up run emits scope="catchup"
    monthly_fetch = phase_duration_seconds.labels(phase="fetch", scope="monthly")
    assert monthly_fetch._value.get() == pytest.approx(12.34)
    # catch-up's match overwrites the monthly match value on its own label set
    monthly_match = phase_duration_seconds.labels(phase="match", scope="monthly")
    catchup_match = phase_duration_seconds.labels(phase="match", scope="catchup")
    assert monthly_match._value.get() == pytest.approx(3.21)
    assert catchup_match._value.get() == pytest.approx(9.00)
    assert phase_duration_seconds.labels(phase="enrich", scope="catchup")._value.get() == (
        pytest.approx(5.00)
    )
    assert phase_duration_seconds.labels(phase="aggregate", scope="catchup")._value.get() == (
        pytest.approx(4.00)
    )
    assert run_duration_seconds._value.get() > 0


def test_phase_durations_skipped_when_no_phase_lines(tmp_path, monkeypatch, caplog):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")  # no catch-up branch
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    _clear_phase_gauges()
    phase_duration_seconds.labels(phase="fetch", scope="monthly").set(99.0)  # sentinel

    def runner(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 0, stdout="nothing parseable here", stderr="")

    with caplog.at_level("WARNING", logger="sotd.pipeline_supervisor.loop"):
        run_nightly(
            repo_dir=repo,
            data_dir=data,
            bundle_dir=bundle,
            runner=runner,
            months=("2026-10", "2026-09"),
            all_months=("2026-10", "2016-05"),
        )
    got = phase_duration_seconds.labels(phase="fetch", scope="monthly")._value.get()
    assert got == 99.0
    assert any("phase" in r.message.lower() for r in caplog.records)


# --- run-outcome and publish metrics ------------------------------------------


def test_publish_freshness_gauge_set_on_success(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    from sotd.pipeline_supervisor.metrics import publish_last_success

    before = publish_last_success._value.get()
    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert publish_last_success._value.get() > before


def test_publish_failures_counter_increments_on_publish_failure(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    # Remove a required bundle slice so the verifier fails the publish.
    (data / "aggregated" / "product_usage" / "2026-10.json").unlink()
    from sotd.pipeline_supervisor.metrics import publish_failures_total

    before = publish_failures_total._value.get()
    result = run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert result.published is False
    assert publish_failures_total._value.get() == before + 1


def test_runs_total_and_consecutive_failures(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    from sotd.pipeline_supervisor.metrics import consecutive_failures, runs_total

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    ok_runs = runs_total._metrics.get(("ok",), None)
    assert ok_runs is not None and ok_runs._value.get() >= 1
    assert consecutive_failures._value.get() == 0

    # A failing night (bad git pull) increments consecutive failures.
    def failing_pull(cmd, **kw):
        if cmd[:2] == ["git", "-C"]:
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="boom")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=failing_pull,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert consecutive_failures._value.get() == 1
    failed_runs = runs_total._metrics.get(("failed",), None)
    assert failed_runs is not None and failed_runs._value.get() >= 1


def test_consecutive_failures_reset_by_success(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    from sotd.pipeline_supervisor.metrics import consecutive_failures

    consecutive_failures.set(3)  # simulate prior failures
    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=fake_runner_ok,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    assert consecutive_failures._value.get() == 0


def test_phase_records_set_from_stdout(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)
    (data / ".catalog_hash").write_text("h1")
    monkeypatch.setattr("sotd.pipeline_supervisor.loop.catalog_hash", lambda d: "h1")
    from sotd.pipeline_supervisor.metrics import phase_records

    records = {"fetch": 1234, "enrich": 900}
    lines = [
        f"  Phase {i + 1} ({p}):   1.00s OK" + (f" | {c:,} records" if p in records else "")
        for i, (p, c) in enumerate(records.items())
    ]
    lines.append("  Phase 6 (aggregate):   2.00s OK")
    stdout = "Phase Breakdown:\n" + "\n".join(lines) + "\n"
    (data / "aggregated" / "annual").mkdir(exist_ok=True)

    def runner_with_stdout(cmd, **kw):
        if cmd[:3] == ["python", "run.py", "--month"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    run_nightly(
        repo_dir=repo,
        data_dir=data,
        bundle_dir=bundle,
        runner=runner_with_stdout,
        months=("2026-10", "2026-09"),
        all_months=("2026-10", "2026-05"),
    )
    for phase, count in records.items():
        assert phase_records.labels(phase=phase, scope="monthly")._value.get() == count
