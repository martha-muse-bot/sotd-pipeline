"""Tests for the --reverse flag on run.py's orchestrator.

--reverse flips the month span to newest-first (reverse chronological);
run.py must both accept the flag and forward it to the phases it dispatches
(it rebuilds the phase command line rather than passing raw argv through).
"""

import run as run_module


class TestReverseFlag:
    def test_reverse_forwarded_to_phases(self, monkeypatch):
        seen = {}

        def fake_run_pipeline(phases, common_args, debug=False):
            seen["common_args"] = common_args
            return 0

        monkeypatch.setattr(run_module, "run_pipeline", fake_run_pipeline)
        code = run_module.main(["community", "--range", "2025-01:2025-03", "--reverse", "--force"])
        assert code == 0
        assert seen["common_args"].count("--reverse") == 1

    def test_reverse_absent_not_forwarded(self, monkeypatch):
        seen = {}

        def fake_run_pipeline(phases, common_args, debug=False):
            seen["common_args"] = common_args
            return 0

        monkeypatch.setattr(run_module, "run_pipeline", fake_run_pipeline)
        code = run_module.main(["community", "--range", "2025-01:2025-03", "--force"])
        assert code == 0
        assert "--reverse" not in seen["common_args"]
