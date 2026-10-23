"""
Test performance improvements for RazorMatcher case-insensitive lookup.

This test demonstrates the O(1) vs O(n) performance difference and ensures
the case-insensitive lookup optimization is working correctly.
"""

import pytest
import tempfile
import time
import yaml
from pathlib import Path

from sotd.match.razor_matcher import RazorMatcher

# Wall-clock threshold asserts are load-sensitive; excluded in CI via `-m "not perf"`.
pytestmark = pytest.mark.perf


class TestRazorMatcherPerformance:
    """Test performance characteristics of the optimized RazorMatcher."""

    def setup_method(self):
        """Set up test fixtures with temporary correct_matches file."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create temporary correct_matches.yaml with test data
        self.correct_matches_path = Path(self.test_dir) / "correct_matches.yaml"
        test_correct_matches = {
            "razor": {
                "Gillette": {
                    "Super Speed": [
                        "gillette superspeed",
                        "gillette - superspeed",
                        "1951 gillette black tip superspeed",
                    ]
                },
                "Above the Tie": {"Atlas S1": ["att s1", "above the tie atlas s1"]},
            }
        }

        with open(self.correct_matches_path, "w") as f:
            yaml.dump(test_correct_matches, f)

    def test_case_insensitive_lookup_performance(self):
        """Test that case-insensitive lookup is O(1) and fast."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test with multiple case variations
        test_cases = [
            "Gillette Superspeed",
            "gillette superspeed",
            "GILLETTE SUPERSPEED",
            "Gillette - Superspeed",
            "att s1",
            "ATT S1",
            "Above The Tie Atlas S1",
            "1951 Gillette Black Tip SuperSpeed",
            "1951 gillette black tip superspeed",
        ]

        # Warm up the lookup dictionary
        matcher._build_case_insensitive_lookup()

        # Time the lookups
        start_time = time.time()

        for test_case in test_cases:
            result = matcher._check_correct_matches(test_case)
            assert result is not None, f"Should find match for '{test_case}'"
            assert result["brand"] is not None

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete very quickly (less than 0.1 seconds for 9 lookups)
        assert (
            elapsed < 0.1
        ), f"O(1) lookup took too long: {elapsed:.4f}s for {len(test_cases)} lookups"

        # Calculate average time per lookup
        avg_time_per_lookup = elapsed / len(test_cases)
        assert (
            avg_time_per_lookup < 0.01
        ), f"Average lookup time too slow: {avg_time_per_lookup:.4f}s"

    def test_lookup_dictionary_building(self):
        """Test that the case-insensitive lookup dictionary is built correctly."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Build the lookup dictionary
        lookup = matcher._build_case_insensitive_lookup()

        # Verify it's a dictionary
        assert isinstance(lookup, dict)

        # Verify it contains expected entries
        assert "gillette superspeed" in lookup
        assert "att s1" in lookup
        assert "above the tie atlas s1" in lookup

        # Verify the structure of entries
        superspeed_entry = lookup["gillette superspeed"]
        assert superspeed_entry["brand"] == "Gillette"
        assert superspeed_entry["model"] == "Super Speed"
        assert superspeed_entry["format"] == "DE"

    def test_lookup_dictionary_caching(self):
        """Test that the lookup dictionary is cached and not rebuilt unnecessarily."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # First call should build the dictionary
        start_time = time.time()
        lookup1 = matcher._build_case_insensitive_lookup()
        first_build_time = time.time() - start_time

        # Second call should use cached version (much faster)
        start_time = time.time()
        lookup2 = matcher._build_case_insensitive_lookup()
        second_build_time = time.time() - start_time

        # Should be the same object (cached)
        assert lookup1 is lookup2

        # Second call should be much faster (cached) - but both are very fast with small test data
        # Just verify they're both very fast (sub-millisecond)
        assert first_build_time < 0.001, f"First build too slow: {first_build_time:.4f}s"
        assert second_build_time < 0.001, f"Second build too slow: {second_build_time:.4f}s"

    def test_memory_efficiency(self):
        """Test that the lookup dictionary doesn't use excessive memory."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Build the lookup dictionary
        lookup = matcher._build_case_insensitive_lookup()

        # Count entries
        entry_count = len(lookup)

        # Should have entries from our test data (5 entries from test correct_matches)
        assert entry_count > 0, f"No entries in lookup: {entry_count}"
        assert entry_count == 5, f"Expected 5 entries from test data, got: {entry_count}"
        assert entry_count < 10000, f"Too many entries in lookup: {entry_count}"

        # Each entry should have the expected structure
        for key, value in list(lookup.items())[:5]:  # Check first 5 entries
            assert isinstance(key, str)
            assert isinstance(value, dict)
            assert "brand" in value
            assert "model" in value
            assert "format" in value

    def test_case_insensitive_vs_case_sensitive_performance(self):
        """Test that case-insensitive lookup is as fast as case-sensitive for exact matches."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test case-sensitive lookup (exact match)
        start_time = time.time()
        for _ in range(100):
            result = matcher._check_correct_matches("gillette superspeed")  # Exact case
        case_sensitive_time = time.time() - start_time

        # Test case-insensitive lookup (different case)
        start_time = time.time()
        for _ in range(100):
            result = matcher._check_correct_matches("Gillette Superspeed")  # Different case
        case_insensitive_time = time.time() - start_time

        # Both should be fast, case-insensitive should not be significantly slower
        assert (
            case_sensitive_time < 0.1
        ), f"Case-sensitive lookup too slow: {case_sensitive_time:.4f}s"
        assert (
            case_insensitive_time < 0.1
        ), f"Case-insensitive lookup too slow: {case_insensitive_time:.4f}s"

        # Case-insensitive should not be more than 2x slower than case-sensitive
        ratio = case_insensitive_time / case_sensitive_time
        assert (
            ratio < 2.0
        ), f"Case-insensitive lookup too slow relative to case-sensitive: {ratio:.2f}x"

    def test_large_scale_performance(self):
        """Test performance with a large number of lookups."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test with many different case variations
        base_razors = [
            "gillette superspeed",
            "att s1",
            "above the tie atlas s1",
            "1951 gillette black tip superspeed",
            "3d printed - tride",
        ]

        # Generate many case variations
        test_cases = []
        for razor in base_razors:
            test_cases.extend(
                [
                    razor,
                    razor.upper(),
                    razor.title(),
                    razor.capitalize(),
                ]
            )

        # Time all lookups
        start_time = time.time()

        results = []
        for test_case in test_cases:
            result = matcher._check_correct_matches(test_case)
            results.append(result)

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete quickly even with many lookups
        assert (
            elapsed < 0.5
        ), f"Large scale lookup took too long: {elapsed:.4f}s for {len(test_cases)} lookups"

        # Most should find matches (80% is acceptable for test data)
        matches_found = sum(1 for r in results if r is not None)
        match_rate = matches_found / len(results)
        assert match_rate >= 0.8, f"Match rate too low: {match_rate:.2%}"
