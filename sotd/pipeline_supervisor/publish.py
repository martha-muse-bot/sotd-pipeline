"""Publish the slim public bundle: verifier-gated rsync into the public mount."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

SLICES = ("product_usage", "user_analysis", "annual", "rankings")


def publish_bundle(
    data_dir: Path,
    bundle_dir: Path,
    *,
    run: Callable[..., "subprocess.CompletedProcess[str]"] | None = None,
) -> bool:
    from scripts.publish_public_data import check_bundle

    # Precompute the public home-overview payload into the bundle before the
    # verifier and rsync so the dashboard serves one small file instead of
    # parsing ~100MB of monthly slices per request.
    try:
        from webui.api.home_overview_builder import write_precomputed

        out = write_precomputed(data_dir)
        logger.info("precomputed home overview: %s", out)
    except Exception:
        # Non-fatal: the endpoint falls back to computing in-process.
        logger.exception("home-overview precompute failed; endpoint will fall back")

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
        slice_src = src / slice_name
        if not slice_src.is_dir():
            # e.g. rankings/ absent when the precompute didn't run — the
            # endpoints fall back to compute, so this is not a publish failure.
            logger.debug("slice %s missing at source; skipping", slice_name)
            continue
        ok &= _rsync(runner, slice_src, dst / slice_name)
    ok &= _rsync(runner, src, dst, include_months=True)
    return ok


def _rsync(runner, src: Path, dst: Path, *, include_months: bool = False) -> bool:
    dst.mkdir(parents=True, exist_ok=True)
    cmd = ["rsync", "-a", "--delete"]
    if include_months:
        cmd += [
            "--include=????-??.json",
            # Precomputed home-overview payload rides with the month slices.
            "--include=home_overview.json",
            "--include=monthly_user_posts_months.json",
            "--exclude=*",
        ]
    cmd += [f"{src}/", f"{dst}/"]
    proc = runner(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("rsync failed: %s\n%s", " ".join(cmd), proc.stderr)
        return False
    return True
