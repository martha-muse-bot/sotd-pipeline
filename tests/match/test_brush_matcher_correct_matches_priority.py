"""
Tests for BrushMatcher's correct matches priority rule.

This tests the core behavior that correct matches have highest priority
and return immediately, while other strategies only run when correct matches
find nothing.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.match.brush_matcher import BrushMatcher


class TestBrushMatcherCorrectMatchesPriority:
    """Test that correct matches have highest priority in BrushMatcher."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create temporary directory for test files
        self.test_dir = tempfile.mkdtemp()

        # Create temporary correct_matches.yaml with test data
        self.correct_matches_path = Path(self.test_dir) / "correct_matches.yaml"
        test_correct_matches = {
            "brush": {
                "Test Brand": {"Test Model": ["test brush pattern", "another test pattern"]},
            }
        }

        with open(self.correct_matches_path, "w") as f:
            yaml.dump(test_correct_matches, f)

        # Copy production catalog files to temp directory for testing
        production_brushes = Path("data/brushes.yaml")
        production_handles = Path("data/handles.yaml")
        production_knots = Path("data/knots.yaml")
        production_config = Path("data/brush_scoring_config.yaml")

        self.brushes_path = Path(self.test_dir) / "brushes.yaml"
        self.handles_path = Path(self.test_dir) / "handles.yaml"
        self.knots_path = Path(self.test_dir) / "knots.yaml"
        self.config_path = Path(self.test_dir) / "brush_scoring_config.yaml"

        if production_brushes.exists():
            shutil.copy(production_brushes, self.brushes_path)
        if production_handles.exists():
            shutil.copy(production_handles, self.handles_path)
        if production_knots.exists():
            shutil.copy(production_knots, self.knots_path)
        if production_config.exists():
            shutil.copy(production_config, self.config_path)

        # Use temporary files for BrushMatcher
        self.brush_matcher = BrushMatcher(
            correct_matches_path=self.correct_matches_path,
            brushes_path=self.brushes_path,
            handles_path=self.handles_path,
            knots_path=self.knots_path,
            brush_scoring_config_path=self.config_path,
        )

        # Load test correct_matches for testing
        self.correct_matches = test_correct_matches

    def teardown_method(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)

    def test_correct_matches_have_highest_priority(self):
        """Test that correct matches return immediately and don't run other strategies."""
        # Find a brush entry in correct_matches that has a specific pattern
        brush_entries = self.correct_matches.get("brush", {})
        if not brush_entries:
            pytest.fail(
                "Test setup failed: No brush entries found in correct_matches test data. Test requires brush entries to validate correct matches priority."
            )

        # Look for an entry with specific patterns (not just brand names)
        test_input = None
        expected_match = None

        for brand, models in brush_entries.items():
            for model, patterns in models.items():
                if isinstance(patterns, list) and patterns:
                    # Use the first pattern as test input
                    test_input = patterns[0]
                    expected_match = {"brand": brand, "model": model}
                    break
            if test_input:
                break

        if not test_input:
            pytest.fail(
                "Test setup failed: No brush patterns found in correct_matches test data. Test requires at least one pattern to validate correct matches priority."
            )

        # Test that correct matches returns immediately
        result = self.brush_matcher.match(test_input)

        assert result is not None
        assert result.matched is not None
        assert result.match_type == "exact"  # Should be exact for correct matches
        assert result.matched["strategy"] == "correct_matches"  # Should use correct matches

        # Verify the match data matches what's in correct_matches.yaml
        assert result.matched is not None
        assert expected_match is not None
        assert result.matched["brand"] == expected_match["brand"]
        assert result.matched["model"] == expected_match["model"]

    def test_correct_matches_no_match_runs_other_strategies(self):
        """Test that when correct matches finds nothing, other strategies are run."""
        # Test with a brush that is NOT in correct_matches but should match via other strategies
        test_input = "Simpson Chubby 2"  # This should match via known_brush strategy

        # First verify it's not in correct_matches
        brush_entries = self.correct_matches.get("brush", {})
        assert test_input.lower() not in brush_entries, (
            f"Test input {test_input} is in correct_matches, " f"choose different input"
        )

        # Test that it matches via other strategies
        result = self.brush_matcher.match(test_input)

        assert result is not None
        assert result.matched is not None
        assert result.match_type == "regex"  # Should be regex for known brush strategy
        assert result.matched["strategy"] == "known_brush"  # Should use known brush strategy

    def test_correct_matches_priority_overrides_other_strategies(self):
        """Test that correct matches take precedence even when other strategies could match."""
        # This test verifies that if correct matches finds something,
        # other strategies don't get a chance to run

        # Find a brush entry that could potentially match via other strategies too
        brush_entries = self.correct_matches.get("brush", {})
        if not brush_entries:
            pytest.fail(
                "Test setup failed: No brush entries found in correct_matches test data. Test requires brush entries to validate correct matches priority over other strategies."
            )

        # Look for a simple brand name that might match via other strategies
        test_input = None
        for brand in brush_entries.keys():
            if len(brand.split()) <= 3:  # Simple brand name
                # Check if this brand has a pattern that matches the brand name itself
                for model, patterns in brush_entries[brand].items():
                    for pattern in patterns:
                        if brand.lower() in pattern.lower():
                            test_input = brand
                            break
                    if test_input:
                        break
                if test_input:
                    break
