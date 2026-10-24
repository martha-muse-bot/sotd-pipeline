"""Pins the entrypoint contract: clone BEFORE praw.ini copy (I1), APP_DIR honored."""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = ROOT / "deploy" / "pipeline" / "entrypoint.sh"


def _entrypoint_text() -> str:
    return ENTRYPOINT.read_text()


def test_clone_precedes_praw_ini_copy():
    """A file-mounted praw.ini makes APP_DIR non-empty; clone must come first."""
    text = _entrypoint_text()
    clone_idx = text.index("git clone")
    copy_idx = text.index('praw.ini" "${APP_DIR}/praw.ini')
    assert clone_idx < copy_idx


def test_materialize_honors_app_dir():
    """materialize.py must write into APP_DIR (default /app), not a hardcoded path."""
    text = (ROOT / "sotd" / "pipeline_supervisor" / "materialize.py").read_text()
    assert 'os.environ.get("APP_DIR", "/app")' in text


def test_entrypoint_uses_app_dir_variable():
    text = _entrypoint_text()
    assert 'APP_DIR="${APP_DIR:-/app}"' in text
