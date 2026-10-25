"""Guard: the public-api image's selective COPY set must satisfy public_main.

Dockerfile.public-api copies only a hand-picked subset of webui/api into the
image. If public_main gains an import (direct or transitive) whose file is not
copied, the image crash-loops at deploy time while repo tests stay green —
which is exactly how the live API went down on 2026-10-24 (home_overview).

This test reconstructs the image's api/ tree from the Dockerfile's COPY list
and imports api.public_main from it, so the closure is validated in CI.
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOCKERFILE = ROOT / "webui" / "Dockerfile.public-api"


def _copied_api_files(dockerfile_text: str) -> list:
    """webui/api file/dir COPY targets, in order, from the Dockerfile."""
    copied = []
    for m in re.finditer(r"^COPY\s+(\S+)\s+\S+$", dockerfile_text, re.MULTILINE):
        src = m.group(1)
        if src.startswith("webui/api/"):
            copied.append(src[len("webui/api/") :])
    return copied


def _purge_imported_modules():
    """Drop api.* / sotd.* from sys.modules so a fresh tree imports cleanly."""
    stale = [
        m for m in list(sys.modules) if m == "api" or m.startswith("api.") or m.startswith("sotd.")
    ]
    for m in stale:
        del sys.modules[m]


def test_dockerfile_copies_exist():
    """Every COPY source in the Dockerfile must exist in the repo."""
    text = DOCKERFILE.read_text()
    for src in _copied_api_files(text):
        assert (ROOT / "webui" / "api" / src).exists(), f"Dockerfile copies missing file: {src}"


def test_public_main_imports_from_image_like_tree(tmp_path, monkeypatch):
    """Import api.public_main from a tree containing ONLY the copied files."""
    text = DOCKERFILE.read_text()
    copied = _copied_api_files(text)
    assert copied, "no webui/api COPY lines found in Dockerfile.public-api"
    for src in copied:
        dst = tmp_path / "webui" / "api" / src
        dst.parent.mkdir(parents=True, exist_ok=True)
        src_path = ROOT / "webui" / "api" / src
        if src_path.is_dir():
            shutil.copytree(src_path, dst)
        else:
            shutil.copy2(src_path, dst)
    # sotd/ ships whole (needed by public_main's import closure)
    shutil.copytree(ROOT / "sotd", tmp_path / "sotd")

    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.syspath_prepend(str(tmp_path / "webui"))
    _purge_imported_modules()
    try:
        import api.public_main  # noqa: F401

        # openapi() resolves through the wrapped routers; if a module were
        # missing this import would already have raised ModuleNotFoundError.
        schema = api.public_main.app.openapi()
        paths = set(schema.get("paths", {}))
        assert "/api/product-usage/health" in paths, f"public api routes missing: {sorted(paths)}"
    finally:
        _purge_imported_modules()
