"""Test that Black Eagle HT2 patterns have higher priority than generic B2 patterns."""

from sotd.match.brush.strategies.known.known_knot_strategy import KnownKnotMatchingStrategy


class TestBlackEagleHT2Priority:
    """Test that Black Eagle HT2 patterns take priority over generic B2 patterns."""

    def setup_method(self):
        """Set up test data."""
        # Create minimal test catalog with the specific patterns we're testing
        self.test_catalog = {
            "Black Eagle": {
                "HT2": {
                    "fiber": "Badger",
                    "patterns": [
                        "black.*eag.*ht2",  # 15 chars
                        "(?:black.*eag)?.*exclusive.*b2",  # 30 chars (without padding)
                    ],
                }
            },
            "Declaration Grooming": {
                "B2": {
                    "fiber": "Badger",
                    "patterns": [
                        "(declaration|\\bdg\\b).*\\bb2\\b",  # 28 chars
                        "\\bb2\\b",  # 6 chars
                    ],
                }
            },
        }

        self.strategy = KnownKnotMatchingStrategy(self.test_catalog)

    def test_patterns_are_sorted_by_length_longest_first(self):
        """Test that patterns are sorted by length, longest first."""
        patterns = self.strategy.patterns

        # Verify sorting order
        assert len(patterns) >= 4, "Should have at least 4 patterns"

        # First pattern should be the longest
        first_pattern = patterns[0]
        assert first_pattern["brand"] == "Black Eagle"
        assert first_pattern["model"] == "HT2"
        assert (
            len(first_pattern["pattern"]) == 30
        ), f"Expected 30 chars, got {len(first_pattern['pattern'])}"

        # Second pattern should be the second longest
        second_pattern = patterns[1]
        assert second_pattern["brand"] == "Declaration Grooming"
        assert second_pattern["model"] == "B2"
        assert (
            len(second_pattern["pattern"]) == 28
        ), f"Expected 28 chars, got {len(second_pattern['pattern'])}"

        # Third pattern should be the third longest
        third_pattern = patterns[2]
        assert third_pattern["brand"] == "Black Eagle"
        assert third_pattern["model"] == "HT2"
        assert (
            len(third_pattern["pattern"]) == 15
        ), f"Expected 15 chars, got {len(third_pattern['pattern'])}"

        # Fourth pattern should be the shortest
        fourth_pattern = patterns[3]
        assert fourth_pattern["brand"] == "Declaration Grooming"
        assert fourth_pattern["model"] == "B2"
        assert (
            len(fourth_pattern["pattern"]) == 6
        ), f"Expected 6 chars, got {len(fourth_pattern['pattern'])}"

    def test_black_eagle_ht2_exclusive_pattern_matches_correctly(self):
        """Test that the Black Eagle HT2 exclusive pattern matches the expected text."""
        test_text = "28 x 49.5 mm EXCLUSIVE BADGER KNOT B2"

        # Find the Black Eagle HT2 exclusive pattern (30 chars)
        ht2_exclusive_pattern = None
        for pattern_data in self.strategy.patterns:
            if (
                pattern_data["brand"] == "Black Eagle"
                and pattern_data["model"] == "HT2"
                and len(pattern_data["pattern"]) == 30
            ):
                ht2_exclusive_pattern = pattern_data
                break

        assert ht2_exclusive_pattern is not None, "Should find Black Eagle HT2 exclusive pattern"

        # Test that it matches
        match = ht2_exclusive_pattern["compiled"].search(test_text)
        assert (
            match is not None
        ), f"Pattern '{ht2_exclusive_pattern['pattern']}' should match '{test_text}'"
        assert (
            "EXCLUSIVE BADGER KNOT B2" in match.group()
        ), f"Should match 'EXCLUSIVE BADGER KNOT B2', got '{match.group()}'"

    def test_generic_b2_pattern_matches_correctly(self):
        """Test that the generic B2 pattern matches the expected text."""
        test_text = "28 x 49.5 mm EXCLUSIVE BADGER KNOT B2"

        # Find the generic B2 pattern (6 chars)
        generic_b2_pattern = None
        for pattern_data in self.strategy.patterns:
            if (
                pattern_data["brand"] == "Declaration Grooming"
                and pattern_data["model"] == "B2"
                and len(pattern_data["pattern"]) == 6
            ):
                generic_b2_pattern = pattern_data
                break

        assert generic_b2_pattern is not None, "Should find generic B2 pattern"

        # Test that it matches
        match = generic_b2_pattern["compiled"].search(test_text)
        assert (
            match is not None
        ), f"Pattern '{generic_b2_pattern['pattern']}' should match '{test_text}'"
        assert match.group() == "B2", f"Should match 'B2', got '{match.group()}'"

    def test_strategy_returns_black_eagle_ht2_for_exclusive_text(self):
        """Test that the strategy returns Black Eagle HT2 for text containing 'EXCLUSIVE B2'."""
        test_text = "28 x 49.5 mm EXCLUSIVE BADGER KNOT B2"

        result = self.strategy.match(test_text)

        assert result is not None, "Should return a match result"
        assert result.matched is not None, "Should have matched data"
        assert (
            result.matched["brand"] == "Black Eagle"
        ), f"Expected Black Eagle, got {result.matched['brand']}"
        assert result.matched["model"] == "HT2", f"Expected HT2, got {result.matched['model']}"
        assert (
            result.pattern == "(?:black.*eag)?.*exclusive.*b2"
        ), f"Expected exclusive pattern, got {result.pattern}"

        # Verify that the longer pattern won (not the generic B2 pattern)
        assert (
            len(result.pattern) > 6
        ), f"Expected pattern longer than 6 chars, got {len(result.pattern)} chars"

    def test_black_eagle_ht2_pattern_priority_over_generic_b2(self):
        """Test that Black Eagle HT2 pattern takes priority over generic B2 pattern."""
        test_text = "28 x 49.5 mm EXCLUSIVE BADGER KNOT B2"

        # Both patterns should match individually
        ht2_matches = []
        b2_matches = []

        for pattern_data in self.strategy.patterns:
            if pattern_data["compiled"].search(test_text):
                if pattern_data["brand"] == "Black Eagle" and pattern_data["model"] == "HT2":
                    ht2_matches.append(pattern_data)
                elif (
                    pattern_data["brand"] == "Declaration Grooming"
                    and pattern_data["model"] == "B2"
                ):
                    b2_matches.append(pattern_data)

        # Both should have matches
        assert len(ht2_matches) > 0, "Should have Black Eagle HT2 matches"
        assert len(b2_matches) > 0, "Should have Declaration Grooming B2 matches"

        # The strategy should return the Black Eagle HT2 match (longer pattern)
        result = self.strategy.match(test_text)
        assert result is not None
        assert result.matched is not None
        assert result.matched["brand"] == "Black Eagle", "Longer pattern should win"
        assert result.matched["model"] == "HT2", "Longer pattern should win"

        # Verify the winning pattern is longer than the generic B2 pattern
        assert result.pattern is not None
        winning_pattern_length = len(result.pattern)
        generic_b2_length = 6
        assert winning_pattern_length > generic_b2_length, (
            f"Winning pattern should be longer than generic B2 pattern. "
            f"Got: {winning_pattern_length} vs {generic_b2_length}"
        )
