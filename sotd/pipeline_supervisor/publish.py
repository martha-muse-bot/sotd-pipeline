"""Publish the slim public bundle: verifier-gated rsync into the public mount."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SLICES = ("product_usage", "user_analysis", "annual")


def publish_bundle(
    data_dir: Path,
    bundle_dir: Path,
    *,
    run: Callable[..., "subprocess.CompletedProcess[str]"] | None = None,
) -> bool:
    from scripts.publish_public_data import check_bundle

    problems = check_bundle(data_dir)
    if problems:
        for p in problems:
            logger.error("bundle check: %s", p)
        return False

    runner = run or subprocess.run
    src = data_dir / "aggregated"
    dst = bundle_dir / "aggregated"
    ok = True
    for slice_name in SLICES:
        ok &= _rsync(runner, src / slice_name, dst / slice_name)
    ok &= _rsync(runner, src, dst, include_months=True)
    return ok


def _rsync(runner, src: Path, dst: Path, *, include_months: bool = False) -> bool:
    dst.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--delete"]
    if include_months:
        cmd += ["--include=????-??.json", "--exclude=*"]
    cmd += [f"{src}/", f"{dst}/"]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("rsync failed: %s\n%s", " ".join(cmd), proc.stderr)
        return False
    return True
