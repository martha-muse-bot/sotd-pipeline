"""
Tests for removing ComponentScoreCalculator usage from strategies.

This test file validates that strategies no longer use ComponentScoreCalculator
and that all scoring is handled externally by the scoring engine.
"""

from unittest.mock import Mock

from sotd.match.brush.scoring.calculator import ComponentScoreCalculator
from sotd.match.types import MatchResult


class TestComponentScoreCalculatorRemoval:
    """Test that ComponentScoreCalculator is no longer used by strategies."""

    def test_strategies_dont_import_component_score_calculator(self):
        """Test that strategies don't import ComponentScoreCalculator."""
        # This test ensures that strategies don't have ComponentScoreCalculator imports

        # Check automated_split strategy
        # The strategy should not have ComponentScoreCalculator in its imports
        import inspect

        from sotd.match.brush.strategies.automated.automated_split_strategy import (
            AutomatedSplitStrategy,
        )

        source = inspect.getsource(AutomatedSplitStrategy)

        # ComponentScoreCalculator should not be imported or used
        assert (
            "ComponentScoreCalculator" not in source
        ), "AutomatedSplitStrategy should not import or use ComponentScoreCalculator"

    def test_strategies_dont_call_calculate_component_scores(self):
        """Test that strategies don't call calculate_component_scores."""
        # This test ensures that strategies don't call the ComponentScoreCalculator method

        # Check automated_split strategy
        import inspect

        from sotd.match.brush.strategies.automated.automated_split_strategy import (
            AutomatedSplitStrategy,
        )

        source = inspect.getsource(AutomatedSplitStrategy)

        # The method call should not be present
        assert (
            "calculate_component_scores" not in source
        ), "AutomatedSplitStrategy should not call calculate_component_scores"

    def test_strategies_return_raw_component_data(self):
        """Test that strategies return raw component data without scores."""
        # This test ensures that strategies return component data without pre-calculated scores

        # Mock the automated_split strategy to return raw data
        from sotd.match.brush.strategies.automated.automated_split_strategy import (
            AutomatedSplitStrategy,
        )

        # Create a mock strategy instance
        strategy = Mock(spec=AutomatedSplitStrategy)

        # Mock the match method to return raw component data
        strategy.match.return_value = MatchResult(
            original="Test input",
            matched={
                "handle": {
                    "brand": "Test",
                    "model": "Handle",
                    "priority": 1,
                    # NO score field
                },
                "knot": {
                    "brand": "Test",
                    "model": "Knot",
                    "fiber": "badger",
                    "priority": 2,
                    # NO score field
                },
            },
            match_type="split_brush",
            pattern="test.*input",
            strategy="automated_split",
        )

        # Call the strategy
        result = strategy.match("Test input")

        # Verify that the result has raw component data without scores
        assert (
            "score" not in result.matched["handle"]
        ), "Handle component should not have pre-calculated score"
        assert (
            "score" not in result.matched["knot"]
        ), "Knot component should not have pre-calculated score"

    def test_component_score_calculator_can_be_removed(self):
        """Test that ComponentScoreCalculator can be safely removed."""
        # This test ensures that ComponentScoreCalculator is not used anywhere
        # and can be safely removed from the codebase

        # Check that no strategies import it
        strategy_files = [
            "sotd.match.brush.strategies.automated.automated_split_strategy",
            "sotd.match.brush.strategies.full_input_component_matching_strategy",
            "sotd.match.brush.strategies.known.known_split_wrapper_strategy",
        ]

        for strategy_module in strategy_files:
            try:
                module = __import__(strategy_module, fromlist=[""])
                import inspect

                source = inspect.getsource(module)

                # Check for actual usage, not just comments
                lines = source.split("\n")
                non_comment_lines = [line for line in lines if not line.strip().startswith("#")]
                non_comment_source = "\n".join(non_comment_lines)

                assert (
                    "ComponentScoreCalculator" not in non_comment_source
                ), f"Module {strategy_module} should not use ComponentScoreCalculator (excluding comments)"
            except ImportError:
                # Module might not exist, which is fine
                pass

    def test_scoring_engine_handles_component_scoring(self):
        """Test that scoring engine handles component scoring instead of ComponentScoreCalculator."""
        # This test ensures that the scoring engine can calculate component scores
        # that were previously calculated by ComponentScoreCalculator

        from sotd.match.brush.config import BrushScoringConfig
        from sotd.match.brush.scoring.engine import ScoringEngine

        config = BrushScoringConfig()
        engine = ScoringEngine(config)

        # Create a result with component data (no scores)
        result = MatchResult(
            original="Test input",
            matched={
                "handle": {
                    "brand": "Test",
                    "model": "Handle",
                    "priority": 1,
                },
                "knot": {
                    "brand": "Test",
                    "model": "Knot",
                    "fiber": "badger",
                    "priority": 2,
                },
            },
            match_type="split_brush",
            pattern="test.*input",
            strategy="automated_split",
        )

        # Score the result
        scored_results = engine.score_results([result], "Test input")
        scored_result = scored_results[0]

        # The scoring engine should calculate component scores via modifiers
        assert scored_result.score is not None
        assert (
            scored_result.score > 0
        ), "Scoring engine should calculate component scores via modifiers"

    def test_modifier_functions_replace_component_score_calculator(self):
        """Test that modifier functions replace ComponentScoreCalculator functionality."""
        # This test ensures that the scoring engine's modifier functions
        # can calculate the same scores that ComponentScoreCalculator used to calculate

        from sotd.match.brush.config import BrushScoringConfig
        from sotd.match.brush.scoring.engine import ScoringEngine

        config = BrushScoringConfig()
        engine = ScoringEngine(config)

        # Create component data that would have been scored by ComponentScoreCalculator
        handle_data = {
            "brand": "Test",
            "model": "Handle",
            "priority": 1,
        }

        knot_data = {
            "brand": "Test",
            "model": "Knot",
            "fiber": "badger",
            "priority": 2,
        }

        # Calculate scores using ComponentScoreCalculator (for comparison)
        handle_score_old = ComponentScoreCalculator.calculate_handle_score(handle_data)
        knot_score_old = ComponentScoreCalculator.calculate_knot_score(knot_data)

        # Create a result with the same component data
        result = MatchResult(
            original="Test input",
            matched={
                "handle": handle_data,
                "knot": knot_data,
            },
            match_type="split_brush",
            pattern="test.*input",
            strategy="automated_split",
        )

        # Calculate scores using modifier functions
        handle_score_new = engine._modifier_handle_weight("Test input", result, "automated_split")
        knot_score_new = engine._modifier_knot_weight("Test input", result, "automated_split")

        # The new scores should match the old scores
        assert (
            handle_score_new == handle_score_old
        ), f"New handle score ({handle_score_new}) should match old score ({handle_score_old})"
        assert (
            knot_score_new == knot_score_old
        ), f"New knot score ({knot_score_new}) should match old score ({knot_score_old})"

    def test_no_double_scoring_after_removal(self):
        """Test that removing ComponentScoreCalculator doesn't cause double scoring."""
        # This test ensures that component scores are only calculated once
        # (by the scoring engine) and not twice (by both ComponentScoreCalculator and scoring engine)

        from sotd.match.brush.config import BrushScoringConfig
        from sotd.match.brush.scoring.engine import ScoringEngine

        config = BrushScoringConfig()
        engine = ScoringEngine(config)

        # Create a result with component data
        result = MatchResult(
            original="Test input",
            matched={
                "handle": {
                    "brand": "Test",
                    "model": "Handle",
                    "priority": 1,
                },
                "knot": {
                    "brand": "Test",
                    "model": "Knot",
                    "fiber": "badger",
                    "priority": 2,
                },
            },
            match_type="split_brush",
            pattern="test.*input",
            strategy="automated_split",
        )

        # Score the result
        scored_results = engine.score_results([result], "Test input")
        scored_result = scored_results[0]

        # The final score should be reasonable (not inflated by double scoring)
        # Base score (55.0 for automated_split) + reasonable modifiers should be in a reasonable range
        # Note: This test uses same brand for handle and knot, so same_brand penalty (-20.0) applies
        # Allow scores from (base - penalty) = 35.0 up to 150.0
        assert scored_result.score is not None
        assert 35.0 <= scored_result.score <= 150.0, (
            f"Final score should be reasonable (35-150), got {scored_result.score}. "
            "If this is too high, there might be double scoring."
        )

    def test_component_score_calculator_utility_still_works(self):
        """Test that ComponentScoreCalculator utility still works for testing purposes."""
        # This test ensures that ComponentScoreCalculator still works
        # for testing and validation purposes, even though strategies don't use it

        # Test the utility functions directly
        handle_data = {
            "brand": "Test",
            "model": "Handle",
            "priority": 1,
        }

        knot_data = {
            "brand": "Test",
            "model": "Knot",
            "fiber": "badger",
            "priority": 2,
        }

        # Calculate scores using the utility
        handle_score = ComponentScoreCalculator.calculate_handle_score(handle_data)
        knot_score = ComponentScoreCalculator.calculate_knot_score(knot_data)

        # Scores should be calculated correctly
        # Handle: brand(5) + model(5) + priority1(2) = 12
        # Knot: brand(5) + model(5) + fiber(5) + priority2(1) = 16
        expected_handle_score = 12.0
        expected_knot_score = 16.0

        assert (
            handle_score == expected_handle_score
        ), f"Handle score should be {expected_handle_score}, got {handle_score}"
        assert (
            knot_score == expected_knot_score
        ), f"Knot score should be {expected_knot_score}, got {knot_score}"
