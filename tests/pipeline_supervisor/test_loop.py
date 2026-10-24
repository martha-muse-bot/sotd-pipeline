import subprocess
from pathlib import Path

from sotd.pipeline_supervisor.loop import run_nightly


def fake_runner_ok(cmd, **kw):
    return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")


def setup_dirs(tmp_path: Path):
    repo = tmp_path / "repo"
    data = tmp_path / "data"
    bundle = tmp_path / "bundle"
    for d in (repo, data, bundle):
        d.mkdir()
    (data / "soaps.yaml").write_text("a: 1\n")
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
    assert result.phases["fetch"] is True


def test_hash_not_saved_on_catchup_failure(tmp_path, monkeypatch):
    repo, data, bundle = setup_dirs(tmp_path)

    calls = []

    def runner(cmd, **kw):
        calls.append(cmd)
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
    assert any(v is False for v in result.phases.values())
    assert result.catchup_ran is True  # drift branch still runs (per-brief order)
    assert result.catchup_ok is False  # catch-up crashes too -> hash not saved
    assert not (data / ".catalog_hash").exists()


def test_once_flag_exists():
    import inspect

    from sotd.pipeline_supervisor import loop

    assert "once" in inspect.getsource(loop.main)


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
