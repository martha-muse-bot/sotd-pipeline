#!/usr/bin/env python3
"""Shared data-directory resolution honoring SOTD_DATA_DIR.

Containers mount the pipeline data dir (or the public bundle subset) and
point SOTD_DATA_DIR at it; local dev defaults to the project root's data/.
"""

import os
from pathlib import Path

_project_root = Path(__file__).parent.parent.parent.parent


def get_data_dir() -> Path:
    """Return the pipeline data directory (SOTD_DATA_DIR or project data/)."""
    env_dir = os.environ.get("SOTD_DATA_DIR")
    return Path(env_dir) if env_dir else _project_root / "data"


def get_enriched_dir() -> Path:
    return get_data_dir() / "enriched"


def get_aggregated_dir() -> Path:
    return get_data_dir() / "aggregated"


def get_matched_dir() -> Path:
    return get_data_dir() / "matched"


def get_overrides_dir() -> Path:
    return get_data_dir() / "overrides"


def get_user_analysis_dir() -> Path:
    return get_aggregated_dir() / "user_analysis"
