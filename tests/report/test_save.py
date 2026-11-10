"""Regression tests for non-atomic report writes (survey item #18).

``save_report`` / ``save_json_report`` (``sotd/report/save.py``) and
``save_annual_report`` / ``save_annual_json_report``
(``sotd/report/annual_run.py``) used to write directly to the target path
with ``open(path, "w")`` — a killed run left a truncated ``.md``/``.json``
that skip-if-exists then treated as complete. They must now write
atomically (temp file + replace), so a failed write leaves any pre-existing
report untouched and no ``.tmp`` file behind.
"""

import builtins
import io
import json
import os
from pathlib import Path

import pytest

from sotd.report import save as save_module
from sotd.report.annual_run import save_annual_json_report, save_annual_report

SENTINEL = "# previous complete report\n"
CONTENT = "# new report\n\nBody text.\n"
JSON_DATA = {"title": "report", "rows": [1, 2, 3]}


def _write_file(path, text):
    """Write a file via os.open, bypassing the sabotaged open() in tests."""
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o644)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)


class _FailingWriter:
    """Wraps a real file object: writes a prefix, then raises OSError.

    Simulates a write interrupted mid-stream (disk full / killed process).
    """

    def __init__(self, fp, fail_after=10):
        self._fp = fp
        self._fail_after = fail_after
        self._written = 0
        self._failed = False

    def write(self, s):
        if self._failed:
            raise OSError("simulated write failure")
        prefix = s[: max(0, self._fail_after - self._written)]
        if prefix:
            self._fp.write(prefix)
            self._written += len(prefix)
        self._failed = True
        raise OSError("simulated write failure")

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self._fp.close()
        return False

    def __getattr__(self, name):
        return getattr(self._fp, name)


@pytest.fixture
def sabotaged_open(monkeypatch, tmp_path):
    """Fail writes to files under tmp_path after a short prefix.

    Patches both ``builtins.open`` (used by the old direct-write code) and
    ``io.open`` (used by ``pathlib.Path.open`` in the atomic helpers), so
    the test fails on the old code and passes on the new code.
    """
    real_open = builtins.open

    def _open(file, *args, **kwargs):
        mode = args[0] if args else kwargs.get("mode", "r")
        fp = real_open(file, *args, **kwargs)
        if "w" not in str(mode):
            return fp
        try:
            path = Path(file)
        except TypeError:
            return fp
        if tmp_path in path.parents or path == tmp_path:
            return _FailingWriter(fp)
        return fp

    monkeypatch.setattr(builtins, "open", _open)
    monkeypatch.setattr(io, "open", _open)
    return tmp_path


def _assert_no_tmp_files(tmp_path):
    assert list(tmp_path.rglob("*.tmp")) == []


@pytest.mark.parametrize(
    "save_fn,args",
    [
        ("save_report", (CONTENT,)),
        ("save_json_report", (JSON_DATA,)),
    ],
)
def test_monthly_save_atomic_on_write_failure(tmp_path, sabotaged_open, save_fn, args):
    """A failed monthly save must leave the previous report intact."""
    target = tmp_path / "2024-01-hardware.md"
    if save_fn == "save_json_report":
        target = tmp_path / "2024-01-hardware.json"
    _write_file(target, SENTINEL if save_fn == "save_report" else json.dumps({"old": True}))
    before = target.read_bytes()

    with pytest.raises(OSError):
        getattr(save_module, save_fn)(*args, target)

    assert target.read_bytes() == before
    _assert_no_tmp_files(tmp_path)


@pytest.mark.parametrize(
    "save_fn,args",
    [
        ("save_annual_report", (CONTENT,)),
        ("save_annual_json_report", (JSON_DATA,)),
    ],
)
def test_annual_save_atomic_on_write_failure(tmp_path, sabotaged_open, save_fn, args):
    """A failed annual save must leave the previous report intact."""
    out_dir = tmp_path / "out"
    reports_dir = out_dir / "report" / "annual"
    reports_dir.mkdir(parents=True)
    suffix = "md" if save_fn == "save_annual_report" else "json"
    target = reports_dir / f"2024-hardware.{suffix}"
    _write_file(target, SENTINEL if suffix == "md" else json.dumps({"old": True}))
    before = target.read_bytes()

    fn = save_annual_report if suffix == "md" else save_annual_json_report
    # force=True: without it the pre-existing file raises FileExistsError
    # before any write, and the test would pass vacuously.
    with pytest.raises(OSError):
        fn(*args, out_dir, "2024", "hardware", force=True)

    assert target.read_bytes() == before
    _assert_no_tmp_files(tmp_path)


def test_save_report_replaces_existing_content(tmp_path):
    """Happy path: atomic save fully replaces the old content, no .tmp left."""
    target = tmp_path / "2024-01-hardware.md"
    target.write_text(SENTINEL)
    save_module.save_report(CONTENT, target, force=True)
    assert target.read_text() == CONTENT
    _assert_no_tmp_files(tmp_path)


def test_save_json_report_round_trip(tmp_path):
    """Happy path: JSON save keeps the established format, no .tmp left."""
    target = tmp_path / "2024-01-hardware.json"
    target.write_text(json.dumps({"old": True}))
    save_module.save_json_report(JSON_DATA, target, force=True)
    assert json.loads(target.read_text()) == JSON_DATA
    assert target.read_text() == json.dumps(JSON_DATA, indent=2, ensure_ascii=False)
    _assert_no_tmp_files(tmp_path)


def test_save_annual_report_replaces_existing_content(tmp_path):
    """Happy path: annual markdown save fully replaces the old content."""
    out_dir = tmp_path / "out"
    target = out_dir / "report" / "annual" / "2024-hardware.md"
    target.parent.mkdir(parents=True)
    target.write_text(SENTINEL)
    saved = save_annual_report(CONTENT, out_dir, "2024", "hardware", force=True)
    assert saved == target
    assert target.read_text() == CONTENT
    _assert_no_tmp_files(tmp_path)


def test_save_annual_json_report_round_trip(tmp_path):
    """Happy path: annual JSON save keeps the established format."""
    out_dir = tmp_path / "out"
    target = out_dir / "report" / "annual" / "2024-hardware.json"
    target.parent.mkdir(parents=True)
    target.write_text(json.dumps({"old": True}))
    saved = save_annual_json_report(JSON_DATA, out_dir, "2024", "hardware", force=True)
    assert saved == target
    assert json.loads(target.read_text()) == JSON_DATA
    assert target.read_text() == json.dumps(JSON_DATA, indent=2, ensure_ascii=False)
    _assert_no_tmp_files(tmp_path)
