# pylint: disable=redefined-outer-name
from unittest.mock import patch

import pytest

from sotd.match.brush.strategies.fallback.fiber_fallback_strategy import FiberFallbackStrategy


@pytest.fixture
def strategy():
    """Create a test strategy instance."""
    return FiberFallbackStrategy()


def test_fiber_fallback_timberwolf_match(strategy):
    """Test that 'Timberwolf 24mm' matches as 'Synthetic' (from 'timber' pattern)."""
    result = strategy.match("Timberwolf 24mm")

    assert result is not None
    assert result.original == "Timberwolf 24mm"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Synthetic"
    assert result.matched["fiber"] == "Synthetic"
    assert result.matched["fiber_strategy"] == "fiber_fallback"
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["_pattern_used"] == "fiber_detection"
    assert result.match_type == "fiber_fallback"


def test_fiber_fallback_custom_badger_match(strategy):
    """Test that 'Custom Badger' matches as 'Badger'."""
    result = strategy.match("Custom Badger")

    assert result is not None
    assert result.original == "Custom Badger"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Badger"
    assert result.matched["fiber"] == "Badger"
    assert result.matched["fiber_strategy"] == "fiber_fallback"
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["_pattern_used"] == "fiber_detection"
    assert result.match_type == "fiber_fallback"


def test_fiber_fallback_unknown_boar_match(strategy):
    """Test that 'Unknown Boar' matches as 'Boar'."""
    result = strategy.match("Unknown Boar")

    assert result is not None
    assert result.original == "Unknown Boar"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Boar"
    assert result.matched["fiber"] == "Boar"
    assert result.matched["fiber_strategy"] == "fiber_fallback"
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["_pattern_used"] == "fiber_detection"
    assert result.match_type == "fiber_fallback"


def test_fiber_fallback_custom_26mm_no_match(strategy):
    """Test that 'Custom 26mm' returns None (no fiber detected)."""
    result = strategy.match("Custom 26mm")

    assert result is None


def test_fiber_fallback_unknown_no_match(strategy):
    """Test that 'Unknown' returns None (no fiber detected)."""
    result = strategy.match("Unknown")

    assert result is None


def test_fiber_fallback_mixed_badger_boar_match(strategy):
    """Test that 'Mixed Badger/Boar' matches as 'Mixed Badger/Boar'."""
    result = strategy.match("Mixed Badger/Boar")

    assert result is not None
    assert result.original == "Mixed Badger/Boar"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Mixed Badger/Boar"
    assert result.matched["fiber"] == "Mixed Badger/Boar"
    assert result.matched["fiber_strategy"] == "fiber_fallback"
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["_pattern_used"] == "fiber_detection"
    assert result.match_type == "fiber_fallback"


def test_fiber_fallback_horse_hair_match(strategy):
    """Test that 'Horse Hair' matches as 'Horse'."""
    result = strategy.match("Horse Hair")

    assert result is not None
    assert result.original == "Horse Hair"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Horse"
    assert result.matched["fiber"] == "Horse"
    assert result.matched["fiber_strategy"] == "fiber_fallback"
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["_pattern_used"] == "fiber_detection"
    assert result.match_type == "fiber_fallback"


def test_fiber_fallback_case_insensitive_match(strategy):
    """Test that fiber detection is case insensitive."""
    result = strategy.match("TIMBERWOLF 24MM")

    assert result is not None
    assert result.matched is not None
    assert result.matched["fiber"] == "Synthetic"


def test_fiber_fallback_empty_string_no_match(strategy):
    """Test that empty string returns None."""
    result = strategy.match("")

    assert result is None


def test_fiber_fallback_whitespace_only_no_match(strategy):
    """Test that whitespace-only string returns None."""
    result = strategy.match("   ")

    assert result is None


@patch("sotd.match.brush.strategies.fallback.fiber_fallback_strategy.match_fiber")
def test_fiber_fallback_uses_fiber_utils(mock_match_fiber, strategy):
    """Test that the strategy uses fiber_utils.match_fiber()."""
    mock_match_fiber.return_value = "Synthetic"

    result = strategy.match("test input")

    mock_match_fiber.assert_called_once_with("test input")
    assert result is not None
    assert result.matched["fiber"] == "Synthetic"


@patch("sotd.match.brush.strategies.fallback.fiber_fallback_strategy.match_fiber")
def test_fiber_fallback_returns_none_when_fiber_utils_returns_none(mock_match_fiber, strategy):
    """Test that strategy returns None when fiber_utils returns None."""
    mock_match_fiber.return_value = None

    result = strategy.match("test input")

    mock_match_fiber.assert_called_once_with("test input")
    assert result is None
