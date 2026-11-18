"""Test that component-level scoring is properly integrated with strategy-level scoring."""

from sotd.match.brush.scoring.calculator import ComponentScoreCalculator


class TestComponentScoringIntegration:
    """Test that component scoring integrates properly with strategy scoring."""

    def test_scoring_engine_modifier_calculation_matches_expected_values(self):
        """Test that ScoringEngine modifier calculations produce expected values."""
        # This test should FAIL if the double weight application bug returns
        # It validates that modifier functions return raw scores, not weighted scores

        from unittest.mock import MagicMock, Mock

        from sotd.match.brush.scoring.engine import ScoringEngine

        # Arrange - Create a mock config with known values for testing
        mock_config = MagicMock()
        mock_config.get_all_modifier_names.return_value = ["handle_weight", "knot_weight"]
        mock_config.get_strategy_modifier.side_effect = lambda strategy, modifier: {
            "handle_weight": 0.5,
            "knot_weight": 0.5,
        }.get(modifier, 0.0)

        engine = ScoringEngine(mock_config)

        # Create a mock result that matches what the automated_split strategy produces
        mock_result = Mock()
        mock_result.matched = {
            "handle": {
                "brand": None,
                "model": None,
                "source_text": "r",
                "priority": None,
                "score": 0.0,
            },
            "knot": {
                "brand": "Zenith",
                "model": "Boar",
                "fiber": "Boar",
                "source_text": "wetshaving zenith moar boar",
                "priority": 2,
                "score": 16.0,
            },
        }
        mock_result.strategy = "automated_split"

        # Act - Call the modifier functions directly
        knot_weight_value = engine._modifier_knot_weight(
            "test input", mock_result, "automated_split"
        )
        handle_weight_value = engine._modifier_handle_weight(
            "test input", mock_result, "automated_split"
        )

        # Assert - These should return component scores directly (no priority recalculation)
        # Component scores already include priority bonuses - they are the single source of truth

        # Knot: component score 16.0 already includes priority bonus
        expected_knot_raw = 16.0  # Component score as-is
        assert knot_weight_value == expected_knot_raw, (
            f"knot_weight should return component score {expected_knot_raw}, got {knot_weight_value}. "
            "If this is 18.0, the duplicate priority calculation bug has returned!"
        )

        # Handle: component score 0.0 already includes priority bonus
        expected_handle_raw = 0.0  # Component score as-is
        assert handle_weight_value == expected_handle_raw, (
            f"handle_weight should return component score {expected_handle_raw}, got {handle_weight_value}. "
            "If this is 50.0, the hardcoded base score bug has returned!"
        )

        # Now test that the full modifier calculation works correctly
        # This should apply weights to the component scores
        total_modifiers = engine._calculate_modifiers(mock_result, "test input", "automated_split")

        # Expected: handle_weight(0.0 × 0.5) + knot_weight(16.0 × 0.5) = 0.0 + 8.0 = 8.0
        expected_total = (0.0 * 0.5) + (16.0 * 0.5)  # 0.0 + 8.0 = 8.0
        assert abs(total_modifiers - expected_total) < 0.1, (
            f"Total modifiers should be {expected_total}, got {total_modifiers}. "
            "If this is wrong, there's a bug in the weight application!"
        )

    def test_component_score_calculator_utility(self):
        """Test that the component score calculator utility works correctly."""
        # Arrange - Create mock component data that should get scores calculated
        component_data = {
            "handle": {
                "brand": "Declaration",
                "model": "Washington",
                "source_text": "Declaration Washington",
                "priority": 1,
            },
            "knot": {
                "brand": "Zenith",
                "model": "Boar",
                "fiber": "Boar",
                "source_text": "Zenith Boar",
                "priority": 2,
            },
        }

        # Act - Use the utility to calculate scores for both components
        updated_data = ComponentScoreCalculator.calculate_component_scores(component_data)

        # Assert - Both components should have calculated scores
        handle_score = updated_data["handle"]["score"]
        knot_score = updated_data["knot"]["score"]

        assert handle_score is not None, "Handle score should be calculated by utility"
        assert knot_score is not None, "Knot score should be calculated by utility"
        assert handle_score > 0, f"Handle score should be > 0, got {handle_score}"
        assert knot_score > 0, f"Knot score should be > 0, got {knot_score}"

        # Scores should reflect component quality
        # Handle: brand(5) + model(5) + priority1(2) = 12
        assert handle_score == 12.0, f"Handle should get 12 points, got {handle_score}"
        # Knot: brand(5) + model(5) + fiber(5) + priority2(1) = 16
        assert knot_score == 16.0, f"Knot should get 16 points, got {knot_score}"
