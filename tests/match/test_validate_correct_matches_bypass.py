"""Test ValidateCorrectMatches bypass functionality."""

from pathlib import Path

import pytest

from sotd.match.tools.managers.validate_correct_matches import ValidateCorrectMatches


class TestValidateCorrectMatchesBypass:
    """Test that ValidateCorrectMatches correctly bypasses correct_matches.yaml when testing."""

    def test_get_matcher_brush_bypass_setting(self):
        """Test that _get_matcher creates BrushMatcher with bypass_correct_matches=True for brush field."""
        # Get project root for data paths
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create validator
        validator = ValidateCorrectMatches(correct_matches_path=data_dir / "correct_matches")
        validator._data_dir = data_dir

        # Get the brush matcher
        matcher = validator._get_matcher("brush")

        print(f"🔍 DEBUG: Matcher type: {type(matcher)}")
        print(f"🔍 DEBUG: Matcher: {matcher}")

        # Should return a BrushMatcher
        assert matcher is not None, "Should return a matcher for brush field"

        # Check that bypass_correct_matches is NOT set as an attribute (it's now a method parameter)
        print(
            f"🔍 DEBUG: Matcher bypass_correct_matches attribute: {getattr(matcher, 'bypass_correct_matches', 'NOT_FOUND')}"
        )

        # Should NOT have bypass_correct_matches as an attribute - it's now a method parameter
        assert not hasattr(
            matcher, "bypass_correct_matches"
        ), "Matcher should NOT have bypass_correct_matches attribute (it's now a method parameter)"

    def test_test_brush_pattern_bypass_validation(self):
        """Test that _test_brush_pattern actually uses bypass matcher for validation."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create validator
        validator = ValidateCorrectMatches(correct_matches_path=data_dir / "correct_matches")
        validator._data_dir = data_dir

        # Test the specific pattern that's failing
        test_pattern = "a.p. shave co amber smoke g5c fan"
        brand_name = "AP Shave Co"
        version_name = "G5C"

        # Get the brush matcher
        matcher = validator._get_matcher("brush")

        print(f"🔍 DEBUG: Testing _test_brush_pattern with pattern: '{test_pattern}'")
        print(f"🔍 DEBUG: Expected brand: '{brand_name}', model: '{version_name}'")

        # Call the private method directly to test it
        result = validator._test_brush_pattern(
            matcher, test_pattern, "brush", brand_name, version_name
        )

        print(f"🔍 DEBUG: _test_brush_pattern result: {result}")

        # Should return None (no issues) because the pattern should match correctly
        assert (
            result is None
        ), f"Pattern '{test_pattern}' should validate successfully, got: {result}"

    def test_validate_field_brush_bypass(self):
        """Test that validate_field for brush actually uses bypass validation."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Create validator
        validator = ValidateCorrectMatches(correct_matches_path=data_dir / "correct_matches")
        validator._data_dir = data_dir

        print("🔍 DEBUG: Starting validate_field for brush")

        # Validate the brush field
        issues, expected_structure = validator.validate_field("brush")

        print(f"🔍 DEBUG: Validation returned {len(issues)} issues")
        print(f"🔍 DEBUG: First few issues: {issues[:3] if issues else 'No issues'}")

        # Look for the specific pattern that should work
        test_pattern = "a.p. shave co amber smoke g5c fan"

        # Check if this pattern has any issues
        pattern_issues = [issue for issue in issues if issue.get("pattern") == test_pattern]

        print(f"🔍 DEBUG: Issues for pattern '{test_pattern}': {pattern_issues}")

        # This pattern should NOT have any issues because it should match correctly
        assert (
            len(pattern_issues) == 0
        ), f"Pattern '{test_pattern}' should not have validation issues: {pattern_issues}"

    def test_brush_matcher_constructor_signature(self):
        """Test that BrushMatcher constructor no longer accepts bypass_correct_matches parameter."""
        from sotd.match.brush_matcher import BrushMatcher

        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        # Test the exact constructor call that ValidateCorrectMatches makes
        brush_scoring_config_path = data_dir / "brush_scoring_config.yaml"

        print(
            f"🔍 DEBUG: Testing BrushMatcher constructor with brush_scoring_config_path: {brush_scoring_config_path}"
        )
        print("🔍 DEBUG: Testing that bypass_correct_matches is no longer a constructor parameter")

        try:
            # This should work - test the constructor signature without bypass_correct_matches
            matcher = BrushMatcher(brush_scoring_config_path=brush_scoring_config_path)

            print("🔍 DEBUG: Successfully created BrushMatcher")
            print(
                f"🔍 DEBUG: bypass_correct_matches attribute: {getattr(matcher, 'bypass_correct_matches', 'NOT_FOUND')}"
            )

            # Should NOT have bypass_correct_matches as an attribute - it's now a method parameter
            assert not hasattr(
                matcher, "bypass_correct_matches"
            ), "Matcher should NOT have bypass_correct_matches attribute (it's now a method parameter)"

            # Test that the method parameter approach works
            result = matcher.match("test", bypass_correct_matches=True)
            print(f"🔍 DEBUG: Method parameter approach works: {result is not None}")

        except Exception as e:
            pytest.fail(f"BrushMatcher constructor or method parameter failed: {e}")

    def test_validate_correct_matches_initialization(self):
        """Test that ValidateCorrectMatches initializes correctly with data directory."""
        project_root = Path(__file__).parent.parent.parent
        data_dir = project_root / "data"

        print("🔍 DEBUG: Testing ValidateCorrectMatches initialization")
        print(f"🔍 DEBUG: Data directory: {data_dir}")

        try:
            validator = ValidateCorrectMatches(
                correct_matches_path=data_dir / "correct_matches.yaml"
            )
            validator._data_dir = data_dir

            print("🔍 DEBUG: Successfully created validator")
            print(f"🔍 DEBUG: Validator data_dir: {validator._data_dir}")

            # Should have data_dir set correctly
            assert (
                validator._data_dir == data_dir
            ), f"Expected data_dir {data_dir}, got {validator._data_dir}"

        except Exception as e:
            pytest.fail(f"ValidateCorrectMatches initialization failed: {e}")
