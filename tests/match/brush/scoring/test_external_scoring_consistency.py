"""
Tests for external scoring consistency across all strategy types.

This test file validates that all strategies follow the same external scoring pattern:
1. Strategies return basic matched data (no internal scoring)
2. Scoring engine handles ALL scoring logic consistently
3. No ComponentScoreCalculator usage in strategies
"""

from pathlib import Path

from sotd.match.brush.config import BrushScoringConfig
from sotd.match.brush.scoring.engine import ScoringEngine
from sotd.match.types import MatchResult


class TestExternalScoringConsistency:
    """Test that all strategies use external scoring consistently."""

    def setup_method(self):
        """Set up test fixtures."""
        # Use test-specific config file instead of production data
        test_config_path = Path(__file__).parent / "test_brush_scoring_config.yaml"
        self.config = BrushScoringConfig(config_path=test_config_path)
        self.engine = ScoringEngine(self.config)

    def test_complete_brush_strategy_external_scoring(self):
        """Test that complete brush strategies use external scoring only."""
        # Create a complete brush result (no component scores)
        result = MatchResult(
            original="Simpson Chubby 2",
            matched={
                "brand": "Simpson",
                "model": "Chubby 2",
                "fiber": "badger",
                "knot_size_mm": 26.0,
            },
            match_type="regex",
            pattern="simpson.*chubby",
            strategy="known_brush",
        )

        # Score the result
        scored_results = self.engine.score_results([result], "Simpson Chubby 2")
        scored_result = scored_results[0]

        # Complete brush strategies should only get base score (no modifiers)
        # Base score for known_brush is 90.0 (updated from 80.0)
        expected_score = 90.0
        assert (
            scored_result.score == expected_score
        ), f"Complete brush strategy should get base score {expected_score}, got {scored_result.score}"

    def test_composite_brush_strategy_external_scoring(self):
        """Test that composite brush strategies use external scoring only."""
        # Create a composite brush result with component data but no component scores
        result = MatchResult(
            original="Declaration Washington w/ Zenith Boar",
            matched={
                "handle": {
                    "brand": "Declaration",
                    "model": "Washington",
                    "source_text": "Declaration Washington",
                    "priority": 1,
                    # NO score field - should be calculated externally
                },
                "knot": {
                    "brand": "Zenith",
                    "model": "Boar",
                    "fiber": "Boar",
                    "source_text": "Zenith Boar",
                    "priority": 2,
                    # NO score field - should be calculated externally
                },
            },
            match_type="split_brush",
            pattern="split_on_medium_priority_delimiter",
            strategy="automated_split",
        )

        # Score the result
        scored_results = self.engine.score_results(
            [result], "Declaration Washington w/ Zenith Boar"
        )
        scored_result = scored_results[0]

        # Composite brush strategies should get base score + modifiers
        # Base score for automated_split is 50.0
        # Modifiers should be calculated externally by scoring engine
        base_score = 50.0
        assert scored_result.score is not None
        assert (
            scored_result.score >= base_score
        ), f"Composite brush strategy should get at least base score {base_score}, got {scored_result.score}"

    def test_component_strategy_external_scoring(self):
        """Test that component strategies use external scoring only."""
        # Create a component strategy result (no internal scoring)
        result = MatchResult(
            original="Zenith Boar",
            matched={
                "brand": "Zenith",
                "model": "Boar",
                "fiber": "Boar",
                "priority": 2,
                # NO score field - should be calculated externally
            },
            match_type="knot",
            pattern="zenith.*boar",
            strategy="knot_matching",
        )

        # Score the result
        scored_results = self.engine.score_results([result], "Zenith Boar")
        scored_result = scored_results[0]

        # Component strategies should get base score + modifiers
        # Base score for knot_matching should be defined in config
        assert scored_result.score is not None
        assert (
            scored_result.score > 0
        ), f"Component strategy should get positive score, got {scored_result.score}"

    def test_no_component_score_calculator_usage(self):
        """Test that strategies don't use ComponentScoreCalculator internally."""
        # This test ensures that strategies return raw data without pre-calculated scores
        # The scoring engine should handle all score calculations

        # Create a result that would have component scores in the old system
        result = MatchResult(
            original="Test brush",
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
            pattern="test.*brush",
            strategy="automated_split",
        )

        # Verify that the result doesn't have pre-calculated scores
        assert result.matched is not None
        assert "handle" in result.matched
        assert isinstance(result.matched["handle"], dict)
        assert (
            "score" not in result.matched["handle"]
        ), "Handle component should not have pre-calculated score"
        assert "knot" in result.matched
        assert isinstance(result.matched["knot"], dict)
        assert (
            "score" not in result.matched["knot"]
        ), "Knot component should not have pre-calculated score"

        # Score the result externally
        scored_results = self.engine.score_results([result], "Test brush")
        scored_result = scored_results[0]

        # The scoring engine should calculate scores externally
        assert scored_result.score is not None
        assert scored_result.score > 0, "Scoring engine should calculate score externally"

    def test_scoring_engine_handles_all_component_scoring(self):
        """Test that scoring engine handles all component scoring via modifiers."""
        # Create a result with component data
        result = MatchResult(
            original="Declaration Washington w/ Zenith Boar",
            matched={
                "handle": {
                    "brand": "Declaration",
                    "model": "Washington",
                    "priority": 1,
                },
                "knot": {
                    "brand": "Zenith",
                    "model": "Boar",
                    "fiber": "Boar",
                    "priority": 2,
                },
            },
            match_type="split_brush",
            pattern="split_on_medium_priority_delimiter",
            strategy="automated_split",
        )

        # Score the result
        scored_results = self.engine.score_results(
            [result], "Declaration Washington w/ Zenith Boar"
        )
        scored_result = scored_results[0]

        # The scoring engine should apply modifiers for component scoring
        # This includes handle_weight, knot_weight, and other modifiers
        base_score = 50.0  # automated_split base score
        assert scored_result.score is not None
        modifier_score = scored_result.score - base_score

        # With test config modifiers set to 0.0, modifier_score should be 0.0
        assert (
            modifier_score == 0.0
        ), f"With test config modifiers set to 0.0, modifier_score should be 0.0, got {modifier_score}"

    def test_strategy_consistency_across_types(self):
        """Test that all strategy types follow the same external scoring pattern."""
        # Create results for different strategy types
        complete_brush_result = MatchResult(
            original="Simpson Chubby 2",
            matched={"brand": "Simpson", "model": "Chubby 2"},
            match_type="regex",
            pattern="simpson.*chubby",
            strategy="known_brush",
        )

        composite_brush_result = MatchResult(
            original="Declaration w/ Zenith",
            matched={
                "handle": {"brand": "Declaration", "priority": 1},
                "knot": {"brand": "Zenith", "priority": 2},
            },
            match_type="split_brush",
            pattern="split_on_medium_priority_delimiter",
            strategy="automated_split",
        )

        component_result = MatchResult(
            original="Zenith Boar",
            matched={"brand": "Zenith", "model": "Boar", "priority": 2},
            match_type="knot",
            pattern="zenith.*boar",
            strategy="knot_matching",
        )

        # Score all results
        all_results = [complete_brush_result, composite_brush_result, component_result]
        scored_results = self.engine.score_results(all_results, "Test input")

        # All results should have scores calculated externally
        for result in scored_results:
            assert hasattr(
                result, "score"
            ), f"Result from strategy {result.strategy} should have score attribute"
            assert result.score is not None
            assert (
                result.score > 0
            ), f"Result from strategy {result.strategy} should have positive score, got {result.score}"

        # Verify that all strategies get positive scores
        complete_result = next(r for r in scored_results if r.strategy == "known_brush")
        composite_result = next(r for r in scored_results if r.strategy == "automated_split")
        component_result = next(r for r in scored_results if r.strategy == "knot_matching")

        assert complete_result.score is not None
        assert composite_result.score is not None
        assert component_result.score is not None

        complete_score = complete_result.score
        composite_score = composite_result.score
        component_score = component_result.score

        # All strategies should have positive scores
        assert (
            complete_score > 0
        ), f"Complete brush should have positive score, got {complete_score}"
        assert (
            composite_score > 0
        ), f"Composite brush should have positive score, got {composite_score}"
        assert (
            component_score > 0
        ), f"Component strategy should have positive score, got {component_score}"

        # Complete brush should have highest base score (80.0 vs 50.0 vs 30.0)
        # But composite brush may have higher total score due to modifiers
        assert (
            complete_score >= 80.0
        ), f"Complete brush should have base score >= 80.0, got {complete_score}"
        assert (
            composite_score >= 50.0
        ), f"Composite brush should have base score >= 50.0, got {composite_score}"
        assert (
            component_score >= 30.0
        ), f"Component strategy should have base score >= 30.0, got {component_score}"

    def test_external_scoring_preserves_behavior(self):
        """Test that external scoring preserves the same behavior as hybrid approach."""
        # This test ensures that moving to external-only scoring doesn't change
        # the final scores that users see

        # Create a result that would have been scored by ComponentScoreCalculator
        result = MatchResult(
            original="Declaration Washington w/ Zenith Boar",
            matched={
                "handle": {
                    "brand": "Declaration",
                    "model": "Washington",
                    "priority": 1,
                },
                "knot": {
                    "brand": "Zenith",
                    "model": "Boar",
                    "fiber": "Boar",
                    "priority": 2,
                },
            },
            match_type="split_brush",
            pattern="split_on_medium_priority_delimiter",
            strategy="automated_split",
        )

        # Score the result
        scored_results = self.engine.score_results(
            [result], "Declaration Washington w/ Zenith Boar"
        )
        scored_result = scored_results[0]

        # The final score should be reasonable and consistent
        # Base score (50.0) + modifiers should give a meaningful total
        assert scored_result.score is not None
        assert (
            50.0 <= scored_result.score <= 200.0
        ), f"External scoring should produce reasonable score (50-200), got {scored_result.score}"

    def test_modifier_functions_handle_component_scoring(self):
        """Test that modifier functions handle component scoring externally."""
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

        # Test that modifier functions can calculate component scores
        handle_weight = self.engine._modifier_handle_weight("Test input", result, "automated_split")
        knot_weight = self.engine._modifier_knot_weight("Test input", result, "automated_split")

        # Modifier functions should return raw component scores
        # Handle: brand(5) + model(5) + priority1(2) = 12
        # Knot: brand(5) + model(5) + fiber(5) + priority2(1) = 16
        expected_handle_score = 12.0
        expected_knot_score = 16.0

        assert (
            handle_weight == expected_handle_score
        ), f"Handle weight modifier should return {expected_handle_score}, got {handle_weight}"
        assert (
            knot_weight == expected_knot_score
        ), f"Knot weight modifier should return {expected_knot_score}, got {knot_weight}"
