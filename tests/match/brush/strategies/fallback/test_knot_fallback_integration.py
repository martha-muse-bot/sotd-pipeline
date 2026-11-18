# pylint: disable=redefined-outer-name
import pytest

from sotd.match.brush.knot_matcher import KnotMatcher
from sotd.match.brush.strategies.fallback.fiber_fallback_strategy import FiberFallbackStrategy
from sotd.match.brush.strategies.fallback.knot_size_fallback_strategy import (
    KnotSizeFallbackStrategy,
)
from sotd.match.brush.strategies.known.known_knot_strategy import KnownKnotMatchingStrategy
from sotd.match.brush.strategies.other_knot_strategy import OtherKnotMatchingStrategy


@pytest.fixture
def knot_matcher_with_fallbacks():
    """Create a KnotMatcher with both fallback strategies added."""
    # Sample catalog data for known knots
    known_knots = {
        "Simpson": {
            "Chubby 2": {
                "fiber": "Badger",
                "knot_size_mm": 27,
                "patterns": ["simp.*chubby\\s*2\\b", "simp.*ch2\\b"],
            },
        },
        "Omega": {
            "10048": {
                "fiber": "Boar",
                "knot_size_mm": 24,
                "patterns": ["omega.*10048"],
            },
        },
    }

    # Sample catalog data for other knots
    other_knots = {
        "AP Shave Co": {
            "G5C": {
                "fiber": "Synthetic",
                "knot_size_mm": 24,
                "patterns": ["(?:\\ba ?p\\b.*)?g5c"],
            },
        },
    }

    # Create strategies in the correct order
    strategies = [
        KnownKnotMatchingStrategy(known_knots),
        OtherKnotMatchingStrategy(other_knots),
        FiberFallbackStrategy(),  # After existing strategies
        KnotSizeFallbackStrategy(),  # After FiberFallbackStrategy
    ]

    return KnotMatcher(strategies)


def test_fiber_fallback_strategy_runs_before_knot_size_fallback(knot_matcher_with_fallbacks):
    """Test that FiberFallbackStrategy runs before KnotSizeFallbackStrategy."""
    # "Timberwolf 24mm" should match via FiberFallbackStrategy (not KnotSizeFallbackStrategy)
    result = knot_matcher_with_fallbacks.match("Timberwolf 24mm")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["fiber"] == "Synthetic"
    assert result.matched["model"] == "Synthetic"
    assert result.match_type == "fiber_fallback"


def test_knot_size_fallback_strategy_runs_after_fiber_fallback(knot_matcher_with_fallbacks):
    """Test that KnotSizeFallbackStrategy runs after FiberFallbackStrategy returns None."""
    # "Custom 26mm" should match via KnotSizeFallbackStrategy
    # (after FiberFallbackStrategy returns None)
    result = knot_matcher_with_fallbacks.match("Custom 26mm")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["fiber"] is None
    assert result.matched["model"] == "26mm"
    assert result.match_type == "size_fallback"


def test_existing_known_knots_still_match_correctly(knot_matcher_with_fallbacks):
    """Test that existing known knots still match correctly (no regression)."""
    # Known knot should still match via KnownKnotMatchingStrategy
    result = knot_matcher_with_fallbacks.match("Simpson Chubby 2")

    assert result is not None
    assert result.matched is not None
    # Existing strategies don't set _matched_by_strategy field
    assert result.matched["brand"] == "Simpson"
    assert result.matched["model"] == "Chubby 2"
    assert result.matched["fiber"] == "Badger"


def test_existing_other_knots_still_match_correctly(knot_matcher_with_fallbacks):
    """Test that existing other knots still match correctly (no regression)."""
    # Test with a truly unknown fiber to exercise FiberFallbackStrategy
    # "Unknown Boar" should be matched by FiberFallbackStrategy since it's not in any catalog
    result = knot_matcher_with_fallbacks.match("Unknown Boar")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["brand"] is None
    assert result.matched["model"] == "Boar"
    assert result.matched["fiber"] == "Boar"


def test_completely_unmatched_knots_return_none(knot_matcher_with_fallbacks):
    """Test that completely unmatched knots return None."""
    # This should not match any strategy
    result = knot_matcher_with_fallbacks.match("Completely Unknown Knot")

    assert result is None


def test_fiber_fallback_with_mixed_fiber_types(knot_matcher_with_fallbacks):
    """Test that FiberFallbackStrategy handles mixed fiber types correctly."""
    result = knot_matcher_with_fallbacks.match("Mixed Badger/Boar")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"
    assert result.matched["fiber"] == "Mixed Badger/Boar"
    assert result.matched["model"] == "Mixed Badger/Boar"
    assert result.match_type == "fiber_fallback"


def test_knot_size_fallback_with_decimal_sizes(knot_matcher_with_fallbacks):
    """Test that KnotSizeFallbackStrategy handles decimal sizes correctly."""
    result = knot_matcher_with_fallbacks.match("Custom 27.5mm")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["fiber"] is None
    assert result.matched["model"] == "27.5mm"
    assert result.match_type == "size_fallback"


def test_knot_size_fallback_with_nx_patterns(knot_matcher_with_fallbacks):
    """Test that KnotSizeFallbackStrategy handles NxM patterns correctly."""
    result = knot_matcher_with_fallbacks.match("Unknown 28x50")

    assert result is not None
    assert result.matched is not None
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"
    assert result.matched["fiber"] is None
    assert result.matched["model"] == "28mm"  # First number in NxM pattern
    assert result.match_type == "size_fallback"


def test_strategy_execution_order_verification(knot_matcher_with_fallbacks):
    """Test that strategies execute in the correct order."""
    # Test that known knots are matched first
    result = knot_matcher_with_fallbacks.match("Simpson Chubby 2")
    # Existing strategies don't set _matched_by_strategy field
    assert result.matched["brand"] == "Simpson"

    # Test that fiber fallback is matched when fiber is detected
    result = knot_matcher_with_fallbacks.match("Timberwolf 24mm")
    assert result.matched["_matched_by_strategy"] == "FiberFallbackStrategy"

    # Test that size fallback is matched last
    result = knot_matcher_with_fallbacks.match("Custom 26mm")
    assert result.matched["_matched_by_strategy"] == "KnotSizeFallbackStrategy"


def test_empty_and_whitespace_inputs(knot_matcher_with_fallbacks):
    """Test that empty and whitespace inputs are handled correctly."""
    # Empty string
    result = knot_matcher_with_fallbacks.match("")
    assert result is None

    # Whitespace only
    result = knot_matcher_with_fallbacks.match("   ")
    assert result is None

    # None input
    result = knot_matcher_with_fallbacks.match(None)  # type: ignore
    assert result is None
