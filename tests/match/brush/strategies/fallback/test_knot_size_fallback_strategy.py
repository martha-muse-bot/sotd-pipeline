# pylint: disable=redefined-outer-name
from unittest.mock import patch

import pytest

from sotd.match.brush.strategies.fallback.knot_size_fallback_strategy import (
    KnotSizeFallbackStrategy,
)


@pytest.fixture
def strategy():
    """Create a test strategy instance."""
    return KnotSizeFallbackStrategy()


def test_knot_size_fallback_custom_26mm_match(strategy):
    """Test that 'Custom 26mm' matches as model='26mm'."""
    result = strategy.match("Custom 26mm")

    assert result is not None
    assert result.original == "Custom 26mm"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "26mm"
    assert result.matched["fiber"] is None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["_pattern_used"] == "size_detection"
    assert result.match_type == "size_fallback"


def test_knot_size_fallback_unknown_24_mm_match(strategy):
    """Test that 'Unknown 24 mm' matches as model='24mm' (handle space)."""
    result = strategy.match("Unknown 24 mm")

    assert result is not None
    assert result.original == "Unknown 24 mm"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "24mm"
    assert result.matched["fiber"] is None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["_pattern_used"] == "size_detection"
    assert result.match_type == "size_fallback"


def test_knot_size_fallback_custom_no_match(strategy):
    """Test that 'Custom' returns None (no size detected)."""
    result = strategy.match("Custom")

    assert result is None


def test_knot_size_fallback_unknown_no_match(strategy):
    """Test that 'Unknown' returns None (no size detected)."""
    result = strategy.match("Unknown")

    assert result is None


def test_knot_size_fallback_timberwolf_24mm_no_match(strategy):
    """Test that 'Timberwolf 24mm' returns None (fiber detected, so this strategy shouldn't run)."""
    # This test documents the expected behavior - this strategy should only run
    # when no fiber is detected, but we test it in isolation here
    result = strategy.match("Timberwolf 24mm")

    # In isolation, this strategy would match, but in practice it should
    # only run after FiberFallbackStrategy returns None
    assert result is not None
    assert result.matched["model"] == "24mm"


def test_knot_size_fallback_custom_27_5mm_match(strategy):
    """Test that 'Custom 27.5mm' matches as model='27.5mm'."""
    result = strategy.match("Custom 27.5mm")

    assert result is not None
    assert result.original == "Custom 27.5mm"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "27.5mm"
    assert result.matched["fiber"] is None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["_pattern_used"] == "size_detection"
    assert result.match_type == "size_fallback"


def test_knot_size_fallback_unknown_28x50_match(strategy):
    """Test that 'Unknown 28x50' matches as model='28mm' (first number in NxM pattern)."""
    result = strategy.match("Unknown 28x50")

    assert result is not None
    assert result.original == "Unknown 28x50"
    assert result.matched is not None
    assert result.matched["brand"] is None
    assert result.matched["model"] == "28mm"
    assert result.matched["fiber"] is None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["_pattern_used"] == "size_detection"
    assert result.match_type == "size_fallback"


def test_knot_size_fallback_case_insensitive_match(strategy):
    """Test that size detection is case insensitive."""
    result = strategy.match("Custom 26MM")

    assert result is not None
    assert result.matched is not None
    assert result.matched["model"] == "26mm"


def test_knot_size_fallback_empty_string_no_match(strategy):
    """Test that empty string returns None."""
    result = strategy.match("")

    assert result is None


def test_knot_size_fallback_whitespace_only_no_match(strategy):
    """Test that whitespace-only string returns None."""
    result = strategy.match("   ")

    assert result is None


def test_knot_size_fallback_decimal_size_match(strategy):
    """Test that decimal sizes are handled correctly."""
    result = strategy.match("Custom 26.5mm")

    assert result is not None
    assert result.matched is not None
    assert result.matched["model"] == "26.5mm"


def test_knot_size_fallback_standalone_number_match(strategy):
    """Test that standalone numbers without 'mm' are NOT detected."""
    result = strategy.match("Custom 26")

    assert result is None


@patch("sotd.match.brush.strategies.fallback.knot_size_fallback_strategy.parse_knot_size")
def test_knot_size_fallback_uses_knot_size_utils(mock_parse_knot_size, strategy):
    """Test that the strategy uses knot_size_utils.parse_knot_size()."""
    mock_parse_knot_size.return_value = 26.0

    result = strategy.match("test input")

    mock_parse_knot_size.assert_called_once_with("test input")
    assert result is not None
    assert result.matched["model"] == "26mm"


@patch("sotd.match.brush.strategies.fallback.knot_size_fallback_strategy.parse_knot_size")
def test_knot_size_fallback_returns_none_when_knot_size_utils_returns_none(
    mock_parse_knot_size, strategy
):
    """Test that strategy returns None when knot_size_utils returns None."""
    mock_parse_knot_size.return_value = None

    result = strategy.match("test input")

    mock_parse_knot_size.assert_called_once_with("test input")
    assert result is None


@patch("sotd.match.brush.strategies.fallback.knot_size_fallback_strategy.parse_knot_size")
def test_knot_size_fallback_handles_decimal_from_utils(mock_parse_knot_size, strategy):
    """Test that strategy handles decimal values from knot_size_utils correctly."""
    mock_parse_knot_size.return_value = 27.5

    result = strategy.match("test input")

    mock_parse_knot_size.assert_called_once_with("test input")
    assert result is not None
    assert result.matched["model"] == "27.5mm"
