"""Pytest configuration and fixtures for SOTD Pipeline tests."""

from pathlib import Path

import pytest


@pytest.fixture(scope="session")
def test_data_dir():
    """Provide the test data directory path."""
    return Path(__file__).parent / "test_data"


@pytest.fixture(scope="session")
def test_correct_matches_path(test_data_dir):
    """Provide the test correct_matches.yaml path."""
    return test_data_dir / "correct_matches.yaml"


@pytest.fixture(scope="session")
def test_brushes_path(test_data_dir):
    """Provide the test brushes.yaml path."""
    return test_data_dir / "brushes.yaml"


@pytest.fixture(scope="session")
def test_handles_path(test_data_dir):
    """Provide the test handles.yaml path."""
    return test_data_dir / "handles.yaml"


@pytest.fixture(scope="session")
def test_knots_path(test_data_dir):
    """Provide the test knots.yaml path."""
    return test_data_dir / "knots.yaml"


@pytest.fixture(scope="session")
def test_brush_scoring_config_path(test_data_dir):
    """Provide the test brush_scoring_config.yaml path."""
    return test_data_dir / "brush_scoring_config.yaml"
