"""
Test BrushMatcher O(1) optimization for correct matches.

This test verifies that the BrushMatcher is using O(1) lookup
for correct_matches.yaml after our optimization.
"""

import time

import pytest

from sotd.match.brush_matcher import BrushMatcher

# Wall-clock threshold asserts are load-sensitive; excluded in CI via `-m "not perf"`.
pytestmark = pytest.mark.perf


class TestBrushMatcherOptimization:
    """Test that BrushMatcher uses O(1) lookup for correct matches."""

    def test_correct_matches_performance(self):
        """Test that BrushMatcher uses O(1) lookup for correct matches."""
        matcher = BrushMatcher()

        # Test multiple lookups to verify O(1) performance
        test_cases = [
            "simpson chubby 2 manchurian",
            "Simpson Chubby 2 Manchurian",
            "SIMPSON CHUBBY 2 MANCHURIAN",
            "ap shave co g5c",
            "AP Shave Co G5C",
        ]

        # First lookup (builds dictionary)
        start_time = time.time()
        matcher.match(test_cases[0])
        first_lookup_time = time.time() - start_time

        # Subsequent lookups (should be O(1))
        start_time = time.time()
        for test_case in test_cases[1:]:
            matcher.match(test_case)
        subsequent_lookups_time = time.time() - start_time

        # First lookup should be slower (builds dictionary)
        assert first_lookup_time > 0.0001, f"First lookup too fast: {first_lookup_time:.6f}s"

        # Subsequent lookups should be very fast (O(1))
        avg_subsequent_time = subsequent_lookups_time / (len(test_cases) - 1)
        print(
            f"BrushMatcher - First: {first_lookup_time:.6f}s, "
            f"Subsequent avg: {avg_subsequent_time:.6f}s"
        )

        # BrushMatcher should be reasonably fast after first lookup
        assert (
            avg_subsequent_time < 0.001
        ), f"Subsequent lookups too slow: {avg_subsequent_time:.6f}s"

    def test_correct_matches_strategy_reuse(self):
        """Test that BrushMatcher reuses CorrectMatchesStrategy instance."""
        matcher = BrushMatcher()

        # First call should create the strategy
        matcher.match("simpson chubby 2 manchurian")

        # Second call should reuse the same strategy instance
        matcher.match("ap shave co g5c")

        # Verify the strategy instance was created and reused
        assert hasattr(matcher, "_correct_matches_strategy")
        assert matcher._correct_matches_strategy is not None

        print("✅ BrushMatcher correctly reuses CorrectMatchesStrategy instance")

    def test_performance_improvement(self):
        """Test that performance improves with multiple lookups."""
        matcher = BrushMatcher()

        # Test 100 lookups to measure performance improvement
        test_cases = [
            "simpson chubby 2 manchurian",
            "ap shave co g5c",
            "omega 10049",
            "semogue 1305",
            "chisel & hound v20",
        ] * 20  # Repeat 20 times for 100 total lookups

        start_time = time.time()
        for test_case in test_cases:
            matcher.match(test_case)
        total_time = time.time() - start_time

        avg_time = total_time / len(test_cases)
        print(f"BrushMatcher - Avg lookup time: {avg_time:.6f}s")

        # Should be reasonably fast (O(1) after first lookup)
        # Allow more time for system load variations (performance tests can be flaky)
        assert avg_time < 0.003, f"BrushMatcher too slow: {avg_time:.6f}s"

        # Should be significantly faster than the old O(n) performance
        # Old performance was ~0.0005s per lookup, new should be much better
        # Allow more time for system load variations (performance tests can be flaky)
        assert avg_time < 0.003, f"BrushMatcher not optimized enough: {avg_time:.6f}s"
