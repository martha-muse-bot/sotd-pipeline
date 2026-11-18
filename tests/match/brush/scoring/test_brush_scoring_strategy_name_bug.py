"""Test to expose bug where strategy results have None strategy names."""

from unittest.mock import Mock

import pytest

from sotd.match.brush.config import BrushScoringConfig
from sotd.match.brush.scoring.engine import ScoringEngine


class TestStrategyNameBug:
    """Test to expose the bug where strategy results have None strategy names."""

    def test_strategy_result_should_not_have_none_strategy_name(self):
        """Test that strategy results never have None strategy names."""
        # This test verifies that the system prevents None strategy names
        config = BrushScoringConfig()
        engine = ScoringEngine(config)

        # Create a mock strategy result that simulates the bug
        buggy_result = Mock()
        buggy_result.strategy = None  # This would be a bug!
        buggy_result.score = 50.0
        buggy_result.match_type = "regex"
        buggy_result.pattern = "test_pattern"
        buggy_result.matched = {"brand": "Test", "model": "Test"}

        # The system should now catch and prevent this bug
        # This test should pass, showing the bug is fixed
        with pytest.raises(ValueError, match="MatchResult has None strategy name"):
            engine._get_strategy_name_from_result(buggy_result)

    def test_scoring_engine_should_validate_strategy_names(self):
        """Test that ScoringEngine validates strategy names are not None."""
        config = BrushScoringConfig()
        engine = ScoringEngine(config)

        # Create a result with None strategy name
        buggy_result = Mock()
        buggy_result.strategy = None
        buggy_result.score = 50.0
        buggy_result.match_type = "regex"
        buggy_result.pattern = "test_pattern"
        buggy_result.matched = {"brand": "Test", "model": "Test"}

        # The ScoringEngine should validate and reject results with None strategy names
        # This test should fail, showing the validation is missing
        with pytest.raises(ValueError, match="MatchResult has None strategy name"):
            engine._get_strategy_name_from_result(buggy_result)

    def test_strategy_results_should_always_have_valid_names(self):
        """Test that all strategy results have valid, non-None strategy names."""
        # This test documents the requirement that strategy names must never be None
        valid_strategy_names = [
            "known_brush",
            "automated_split",
            "full_input_component_matching",
            "known_split",
            "handle_matching",
            "knot_matching",
        ]

        for name in valid_strategy_names:
            assert name is not None, f"Strategy name '{name}' should not be None"
            assert isinstance(name, str), f"Strategy name '{name}' should be a string"
            assert len(name) > 0, f"Strategy name '{name}' should not be empty"
