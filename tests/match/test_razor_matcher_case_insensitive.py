"""
Test case-insensitive correct matches for RazorMatcher.

This test ensures that the RazorMatcher properly handles case-insensitive
lookups for correct matches, which was a critical bug fix.
"""

import tempfile
from pathlib import Path

import yaml

from sotd.match.razor_matcher import RazorMatcher


class TestRazorMatcherCaseInsensitive:
    """Test case-insensitive correct matches functionality."""

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
                        "1956 gillette red tip superspeed",
                        "1957 gillette flare tip superspeed",
                        "1967 vintage gillette superspeed",
                        "gillette 40's-style superspeed",
                        "gillette black-handled superspeed",
                        "gillette flair-tip superspeed",
                        "gillette superspeed 40s ndc",
                        "gillette superspeed red tip",
                    ]
                },
                "Above the Tie": {"Atlas S1": ["att s1", "above the tie atlas s1"]},
            }
        }

        with open(self.correct_matches_path, "w") as f:
            yaml.dump(test_correct_matches, f)

    def test_superspeed_case_variations(self):
        """Test that Superspeed matches work with different case variations."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test cases with different case variations
        test_cases = [
            "Gillette Superspeed",  # Title case
            "gillette superspeed",  # Lowercase
            "GILLETTE SUPERSPEED",  # Uppercase
            "Gillette - Superspeed",  # With dash
            "gillette - superspeed",  # With dash, lowercase
        ]

        for test_case in test_cases:
            result = matcher.match(test_case)

            # All should match as exact
            assert result.match_type == "exact", f"Failed for '{test_case}': {result.match_type}"
            assert result.matched is not None, f"No match for '{test_case}'"
            assert (
                result.matched["brand"] == "Gillette"
            ), f"Wrong brand for '{test_case}': {result.matched['brand']}"
            assert (
                result.matched["model"] == "Super Speed"
            ), f"Wrong model for '{test_case}': {result.matched['model']}"
            assert (
                result.matched["format"] == "DE"
            ), f"Wrong format for '{test_case}': {result.matched['format']}"

    def test_black_tip_superspeed_variations(self):
        """Test that Black Tip Superspeed matches work with different case variations."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        test_cases = [
            "1951 Gillette Black Tip SuperSpeed",
            "1951 gillette black tip superspeed",
            "1951 GILLETTE BLACK TIP SUPERSPEED",
        ]

        for test_case in test_cases:
            result = matcher.match(test_case)

            # All should match as exact
            assert result.match_type == "exact", f"Failed for '{test_case}': {result.match_type}"
            assert result.matched is not None, f"No match for '{test_case}'"
            assert (
                result.matched["brand"] == "Gillette"
            ), f"Wrong brand for '{test_case}': {result.matched['brand']}"
            assert (
                result.matched["model"] == "Super Speed"
            ), f"Wrong model for '{test_case}': {result.matched['model']}"

    def test_att_razor_variations(self):
        """Test that Above the Tie razor matches work with different case variations."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        test_cases = [
            "ATT S1",
            "att s1",
            "Att S1",
            "above the tie atlas s1",
            "Above The Tie Atlas S1",
        ]

        for test_case in test_cases:
            result = matcher.match(test_case)

            # All should match as exact
            assert result.match_type == "exact", f"Failed for '{test_case}': {result.match_type}"
            assert result.matched is not None, f"No match for '{test_case}'"
            assert (
                result.matched["brand"] == "Above the Tie"
            ), f"Wrong brand for '{test_case}': {result.matched['brand']}"

    def test_case_sensitive_exact_match_priority(self):
        """Test that exact case matches are found first before case-insensitive fallback."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test with exact case match (should be found first)
        result = matcher.match("gillette superspeed")
        assert result is not None
        assert result.match_type == "exact"
        assert result.matched is not None
        assert result.matched["brand"] == "Gillette"
        assert result.matched["model"] == "Super Speed"

    def test_no_match_for_unknown_razor(self):
        """Test that unknown razors don't match in correct matches."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test with a razor that's not in correct_matches.yaml
        result = matcher.match("Unknown Brand Unknown Model")

        # Should fall back to regex matching or be unmatched
        assert result.match_type != "exact", "Unknown razor should not match as exact"

    def test_bypass_correct_matches(self):
        """Test that bypass_correct_matches parameter works correctly."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test with bypass_correct_matches=True
        result = matcher.match("gillette superspeed", bypass_correct_matches=True)

        # Should not match as exact when bypassed
        assert result.match_type != "exact", "Should not match as exact when bypassed"

    def test_check_correct_matches_method(self):
        """Test the _check_correct_matches method directly."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test case-insensitive lookup
        result = matcher._check_correct_matches("Gillette Superspeed")
        assert result is not None
        assert result["brand"] == "Gillette"
        assert result["model"] == "Super Speed"
        assert result["format"] == "DE"

        # Test lowercase lookup
        result = matcher._check_correct_matches("gillette superspeed")
        assert result is not None
        assert result["brand"] == "Gillette"
        assert result["model"] == "Super Speed"

        # Test no match
        result = matcher._check_correct_matches("nonexistent razor")
        assert result is None

    def test_performance_with_case_variations(self):
        """Test that case-insensitive lookup doesn't significantly impact performance."""
        matcher = RazorMatcher(correct_matches_path=self.correct_matches_path)

        # Test multiple case variations to ensure performance is reasonable
        test_cases = [
            "Gillette Superspeed",
            "gillette superspeed",
            "GILLETTE SUPERSPEED",
            "Gillette - Superspeed",
            "att s1",
            "ATT S1",
            "Above The Tie Atlas S1",
        ]

        import time

        start_time = time.time()

        for test_case in test_cases:
            result = matcher.match(test_case)
            assert result.match_type == "exact"

        end_time = time.time()
        elapsed = end_time - start_time

        # Should complete quickly (less than 1 second for 7 lookups)
        assert elapsed < 1.0, f"Case-insensitive lookup took too long: {elapsed:.3f}s"
