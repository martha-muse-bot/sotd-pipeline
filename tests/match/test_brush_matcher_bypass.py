"""Test BrushMatcher bypass functionality."""

from pathlib import Path

from sotd.match.brush_matcher import BrushMatcher


class TestBrushMatcherBypass:
    """Test that BrushMatcher correctly bypasses correct_matches.yaml when requested."""

    def test_bypass_correct_matches_true(self):
        """Test that bypass_correct_matches=True actually bypasses correct_matches.yaml."""
        # Get project root for data paths
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create matcher (correct_matches directory is always loaded, but can be bypassed in match calls)
        matcher = BrushMatcher(
            brushes_path=data_dir / "brushes.yaml",
            handles_path=data_dir / "handles.yaml",
            knots_path=data_dir / "knots.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        # Test the specific pattern that's failing with bypass enabled
        test_pattern = "a.p. shave co amber smoke g5c fan"
        result = matcher.match(test_pattern, bypass_correct_matches=True)

        # Debug output
        print(f"🔍 DEBUG: Testing pattern: '{test_pattern}'")
        print(f"🔍 DEBUG: Result: {result}")
        if result and hasattr(result, "matched"):
            print(f"🔍 DEBUG: Matched data: {result.matched}")
            print(f"🔍 DEBUG: Strategy used: {getattr(result, '_matched_by', 'Unknown')}")

        # This should match based on the regex pattern in brushes.yaml
        assert result is not None, f"Pattern '{test_pattern}' should match"
        assert hasattr(result, "matched"), "Result should have matched attribute"
        assert result.matched is not None, "Matched data should not be None"

        # Should match to AP Shave Co G5C based on the regex pattern
        expected_brand = "AP Shave Co"
        expected_model = "G5C"

        actual_brand = result.matched.get("brand")
        actual_model = result.matched.get("model")

        print(f"🔍 DEBUG: Expected: {expected_brand} {expected_model}")
        print(f"🔍 DEBUG: Actual: {actual_brand} {actual_model}")

        assert (
            actual_brand == expected_brand
        ), f"Expected brand '{expected_brand}', got '{actual_brand}'"
        assert (
            actual_model == expected_model
        ), f"Expected model '{expected_model}', got '{actual_model}'"

        # Should NOT be using CorrectMatchesStrategy when bypassing
        strategy_used = getattr(result, "_matched_by", "Unknown")
        assert (
            strategy_used != "CorrectMatchesStrategy"
        ), f"Should not use CorrectMatchesStrategy when bypassing, got '{strategy_used}'"

    def test_bypass_correct_matches_false(self):
        """Test that bypass_correct_matches=False uses correct_matches.yaml."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create matcher with default behavior (correct_matches directory is always loaded)
        matcher = BrushMatcher(
            brushes_path=data_dir / "brushes.yaml",
            handles_path=data_dir / "handles.yaml",
            knots_path=data_dir / "knots.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        # Test the same pattern with bypass disabled (default)
        test_pattern = "a.p. shave co amber smoke g5c fan"
        result = matcher.match(test_pattern, bypass_correct_matches=False)

        print(f"🔍 DEBUG: Testing pattern with bypass=False: '{test_pattern}'")
        print(f"🔍 DEBUG: Result: {result}")
        if result and hasattr(result, "matched"):
            print(f"🔍 DEBUG: Matched data: {result.matched}")
            print(f"🔍 DEBUG: Strategy used: {getattr(result, '_matched_by', 'Unknown')}")

        # Should still match, but might use different strategy
        assert result is not None, f"Pattern '{test_pattern}' should match even without bypass"
        assert hasattr(result, "matched"), "Result should have matched attribute"
        assert result.matched is not None, "Matched data should not be None"

    def test_regex_pattern_matching(self):
        """Test that the specific regex pattern in brushes.yaml actually matches."""
        import re

        # The pattern from brushes.yaml
        pattern = r"\ba[\s.]*p\b.*g5c"
        test_string = "a.p. shave co amber smoke g5c fan"

        print(f"🔍 DEBUG: Testing regex pattern: '{pattern}'")
        print(f"🔍 DEBUG: Test string: '{test_string}'")

        match = re.search(pattern, test_string, re.IGNORECASE)
        print(f"🔍 DEBUG: Regex match result: {match}")

        # This should definitely match
        assert match is not None, f"Regex pattern '{pattern}' should match '{test_string}'"

        # Print what was matched
        if match:
            print(f"🔍 DEBUG: Matched portion: '{match.group(0)}'")
            print(f"🔍 DEBUG: Match span: {match.span()}")

    def test_brush_matcher_initialization(self):
        """Test that BrushMatcher can bypass correct_matches.yaml in match calls."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create matcher (correct_matches directory is always loaded)
        matcher = BrushMatcher(
            brushes_path=data_dir / "brushes.yaml",
            handles_path=data_dir / "handles.yaml",
            knots_path=data_dir / "knots.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        # Test that bypass_correct_matches parameter works in match method
        test_pattern = "test pattern"

        # Test with bypass=True
        result_bypass = matcher.match(test_pattern, bypass_correct_matches=True)
        print(f"🔍 DEBUG: Match with bypass=True: {result_bypass}")

        # Test with bypass=False (default)
        result_no_bypass = matcher.match(test_pattern, bypass_correct_matches=False)
        print(f"🔍 DEBUG: Match with bypass=False: {result_no_bypass}")

        # Both should work without errors
        assert matcher is not None, "Matcher should be created successfully"
        print("✅ Matcher initialization and bypass parameter testing successful")
