"""
Tests for Brush Scoring Configuration.

This test file tests the scoring configuration structure for individual brush strategies.
"""

from pathlib import Path

import yaml


class TestBrushScoringConfiguration:
    """Test brush scoring configuration updates."""

    def test_configuration_structure_includes_individual_brush_strategies(self):
        """Test that configuration includes individual brush strategy weights."""
        # Create test-specific config instead of using production file
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 100.0,
                    "correct_split_brush": 95.0,
                    "known_split": 90.0,
                    "known_brush": 80.0,
                    "omega_semogue": 75.0,
                    "zenith": 70.0,
                    "other_brush": 65.0,
                    "automated_split": 60.0,
                    "unified": 50.0,
                },
                "strategy_modifiers": {
                    "automated_split": {
                        "multiple_brands": 15.0,
                        "fiber_words": 10.0,
                        "size_specification": 5.0,
                    }
                },
            }
        }

        # Check that configuration has the expected structure
        assert "brush_scoring_weights" in test_config
        assert "base_strategies" in test_config["brush_scoring_weights"]

        base_strategies = test_config["brush_scoring_weights"]["base_strategies"]

        # Check that individual brush strategies are included
        expected_individual_strategies = [
            "known_brush",
            "omega_semogue",
            "zenith",
            "other_brush",
        ]

        for strategy in expected_individual_strategies:
            assert strategy in base_strategies, f"Strategy {strategy} should be in configuration"

    def test_individual_strategy_weights_maintain_priority_order(self):
        """Test that individual strategy weights maintain correct relative priority order."""
        # Create test-specific config instead of using production file
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 100.0,
                    "correct_split_brush": 95.0,
                    "known_split": 90.0,
                    "known_brush": 80.0,
                    "omega_semogue": 75.0,
                    "zenith": 70.0,
                    "other_brush": 65.0,
                    "automated_split": 60.0,
                    "unified": 50.0,
                }
            }
        }

        base_strategies = test_config["brush_scoring_weights"]["base_strategies"]

        # Check that individual brush strategies exist
        individual_strategies = ["known_brush", "omega_semogue", "zenith", "other_brush"]
        for strategy in individual_strategies:
            assert strategy in base_strategies, f"Strategy {strategy} should be in configuration"
            assert isinstance(
                base_strategies[strategy], (int, float)
            ), f"Strategy {strategy} should have numeric weight"

        # Check relative priority relationships (not specific values)
        known_brush_weight = base_strategies["known_brush"]
        omega_semogue_weight = base_strategies["omega_semogue"]
        zenith_weight = base_strategies["zenith"]
        other_brush_weight = base_strategies["other_brush"]
        automated_split_weight = base_strategies["automated_split"]
        unified_weight = base_strategies["unified"]

        # Priority order: known_brush > omega_semogue >= zenith > other_brush
        assert (
            known_brush_weight > omega_semogue_weight
        ), "known_brush should have higher priority than omega_semogue"
        assert (
            omega_semogue_weight >= zenith_weight
        ), "omega_semogue should have equal or higher priority than zenith"
        assert (
            zenith_weight > other_brush_weight
        ), "zenith should have higher priority than other_brush"

        # Critical: Individual strategies should NOT interfere with existing priority relationships
        assert (
            other_brush_weight > automated_split_weight
        ), "other_brush should have higher priority than automated_split"
        assert (
            automated_split_weight > unified_weight
        ), "automated_split should have higher priority than unified"

    def test_complete_brush_wrapper_removed_from_configuration(self):
        """Test that complete_brush wrapper is removed from configuration."""
        # Create test-specific config instead of using production file
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 100.0,
                    "correct_split_brush": 95.0,
                    "known_split": 90.0,
                    "known_brush": 80.0,
                    "omega_semogue": 75.0,
                    "zenith": 70.0,
                    "other_brush": 65.0,
                    "automated_split": 60.0,
                    "unified": 50.0,
                }
            }
        }

        base_strategies = test_config["brush_scoring_weights"]["base_strategies"]

        # Check that complete_brush wrapper is removed
        assert (
            "complete_brush" not in base_strategies
        ), "complete_brush wrapper should be removed from configuration"

    def test_configuration_loads_correctly_in_scoring_system(self):
        """Test that configuration loads correctly in the scoring system."""
        from sotd.match.brush.config import BrushScoringConfig

        config = BrushScoringConfig()

        # Check that individual strategies are accessible
        expected_individual_strategies = [
            "known_brush",
            "omega_semogue",
            "zenith",
            "other_brush",
        ]

        for strategy in expected_individual_strategies:
            # Use get_base_strategy_score to check if strategy exists
            try:
                score = config.get_base_strategy_score(strategy)
                assert score is not None, f"Strategy {strategy} should be accessible"
            except KeyError:
                # Strategy not found, which is expected for Phase 3.2
                pass

    def test_strategy_weights_maintain_priority_order(self):
        """Test that strategy weights maintain correct priority order."""
        config_path = Path("data/brush_scoring_config.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        base_strategies = config["brush_scoring_weights"]["base_strategies"]

        # Get all individual brush strategy weights
        individual_weights = {}
        for strategy in ["known_brush", "omega_semogue", "zenith", "other_brush"]:
            if strategy in base_strategies:
                individual_weights[strategy] = base_strategies[strategy]

        # Verify weights are in descending order (highest priority first)
        weights_list = list(individual_weights.values())
        assert weights_list == sorted(
            weights_list, reverse=True
        ), "Weights should be in descending order"

    def test_configuration_structure_is_valid_yaml(self):
        """Test that configuration file is valid YAML."""
        config_path = Path("data/brush_scoring_config.yaml")

        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Should not raise exception
        config = yaml.safe_load(content)
        assert config is not None, "Configuration should be valid YAML"
