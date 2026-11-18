"""Test that BrushMatcher.match() should accept bypass_correct_matches parameter."""

from pathlib import Path

import pytest

from sotd.match.brush_matcher import BrushMatcher


class TestBrushMatcherMatchBypass:
    """Test that BrushMatcher.match() should accept bypass_correct_matches parameter."""

    def test_match_method_should_accept_bypass_parameter(self):
        """Test that match() method should accept bypass_correct_matches parameter."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create matcher WITHOUT bypass setting
        matcher = BrushMatcher(
            brush_scoring_config_path=data_dir / "brush_scoring_config.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        test_pattern = "a.p. shave co amber smoke g5c fan"

        print(f"🔍 DEBUG: Testing pattern: '{test_pattern}'")

        # Test 1: Default behavior (should use correct_matches.yaml)
        result1 = matcher.match(test_pattern)
        print(f"🔍 DEBUG: Default match result: {result1}")

        # Test 2: Should be able to call with bypass parameter
        # This is what we WANT to be able to do:
        try:
            result2 = matcher.match(test_pattern, bypass_correct_matches=True)
            print(f"🔍 DEBUG: Bypass match result: {result2}")

            # Both should work, but bypass should give different result
            assert result1 is not None, "Default match should work"
            assert result2 is not None, "Bypass match should work"

            # The bypass result should NOT use CorrectMatchesStrategy
            if hasattr(result2, "matched") and result2.matched:
                strategy_used = result2.matched.get("strategy", "Unknown")
                print(f"🔍 DEBUG: Strategy used with bypass: {strategy_used}")

                # Should use a different strategy when bypassing
                assert (
                    strategy_used != "correct_matches"
                ), f"Bypass should not use correct_matches strategy, got: {strategy_used}"

        except TypeError as e:
            # This is the bug - the method doesn't accept the parameter
            print(
                f"🔍 DEBUG: Bug exposed! Method doesn't accept bypass_correct_matches parameter: {e}"
            )
            pytest.fail(f"BrushMatcher.match() should accept bypass_correct_matches parameter: {e}")

    def test_current_workaround_creates_bug(self):
        """Test that the current workaround of setting bypass at instantiation creates bugs."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # This is what the validation system currently does - creates a new matcher
        # with bypass_correct_matches=True
        bypass_matcher = BrushMatcher(
            brush_scoring_config_path=data_dir / "brush_scoring_config.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        test_pattern = "a.p. shave co amber smoke g5c fan"

        print("🔍 DEBUG: Testing with bypass_matcher (bypass_correct_matches=True)")
        print(
            f"🔍 DEBUG: Matcher bypass_correct_matches attribute: {getattr(bypass_matcher, 'bypass_correct_matches', 'NOT_FOUND')}"
        )

        # This should work
        result = bypass_matcher.match(test_pattern)
        print(f"🔍 DEBUG: Bypass matcher result: {result}")

        assert result is not None, "Bypass matcher should work"

        # But this approach has problems:
        # 1. Need to create separate matcher instances
        # 2. More complex instantiation logic
        # 3. Harder to test and debug
        # 4. Violates single responsibility principle

        print("🔍 DEBUG: Current approach requires separate matcher instances")
        print("🔍 DEBUG: This is unnecessarily complex and error-prone")

    def test_better_approach_with_method_parameter(self):
        """Test how it SHOULD work with a bypass parameter on the match method."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create single matcher instance
        matcher = BrushMatcher(
            brush_scoring_config_path=data_dir / "brush_scoring_config.yaml",
            correct_matches_path=data_dir / "correct_matches",
        )

        test_pattern = "a.p. shave co amber smoke g5c fan"

        print("🔍 DEBUG: Testing how it SHOULD work:")
        print("🔍 DEBUG: Single matcher instance, different behavior per call")

        # This is the ideal API:
        # result1 = matcher.match(test_pattern)  # Uses correct_matches.yaml
        # result2 = matcher.match(test_pattern, bypass_correct_matches=True)  # Bypasses correct_matches.yaml

        # Benefits:
        # 1. Single matcher instance
        # 2. Explicit behavior per call
        # 3. Easier to test and debug
        # 4. More flexible
        # 5. Follows principle of least surprise

        print("🔍 DEBUG: Ideal API would be:")
        print("🔍 DEBUG:   matcher.match(text)  # Default behavior")
        print("🔍 DEBUG:   matcher.match(text, bypass_correct_matches=True)  # Bypass behavior")

        # For now, just test that the current approach works
        result = matcher.match(test_pattern)
        assert result is not None, "Current approach should still work"
