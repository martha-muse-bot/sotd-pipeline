#!/usr/bin/env python3
"""Tests for the shared data-dir resolver (SOTD_DATA_DIR support)."""

import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.utils.data_dir import (  # noqa: E402
    get_aggregated_dir,
    get_data_dir,
    get_enriched_dir,
    get_user_analysis_dir,
)

PROJECT_DATA = Path(__file__).parent.parent.parent.parent / "data"


def test_defaults_to_project_data_dir():
    with patch.dict("os.environ", {}, clear=False):
        assert get_data_dir() == PROJECT_DATA


def test_env_var_overrides():
    with patch.dict("os.environ", {"SOTD_DATA_DIR": "/mnt/public-data"}):
        assert get_data_dir() == Path("/mnt/public-data")
        assert get_enriched_dir() == Path("/mnt/public-data/enriched")
        assert get_aggregated_dir() == Path("/mnt/public-data/aggregated")
        assert get_user_analysis_dir() == Path("/mnt/public-data/aggregated/user_analysis")


def test_subdirs_consistent_between_modes():
    """Env-var mode resolves the same relative layout as project-root mode."""
    with patch.dict("os.environ", {"SOTD_DATA_DIR": str(PROJECT_DATA)}):
        assert get_enriched_dir() == PROJECT_DATA / "enriched"
        assert get_aggregated_dir() == PROJECT_DATA / "aggregated"
