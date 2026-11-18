"""
Integration tests for BrushScoringConfig.

Tests the configuration system with real YAML files and pipeline integration.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.match.brush.config import BrushScoringConfig


class TestBrushScoringConfigIntegration:
    """Integration tests for BrushScoringConfig."""

    def test_config_with_real_yaml_file(self):
        """Test configuration with real YAML file."""
        # Create a temporary YAML file
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 95.0,
                    "correct_split_brush": 90.0,
                    "known_split": 85.0,
                    "high_priority_automated_split": 80.0,
                    "complete_brush": 75.0,
                    "dual_component": 70.0,
                    "medium_priority_automated_split": 65.0,
                    "single_component_fallback": 60.0,
                },
                "strategy_modifiers": {
                    "high_priority_automated_split": {
                        "multiple_brands": 5.0,
                        "fiber_words": 3.0,
                        "size_specification": 2.0,
                        "handle_confidence": 10.0,
                        "knot_confidence": 15.0,
                        "word_count_balance": 25.0,
                    }
                },
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_config, f)
            config_path = Path(f.name)

        try:
            config = BrushScoringConfig(config_path=config_path)

            # Test base strategy scores
            assert config.get_base_strategy_score("correct_complete_brush") == 95.0
            assert config.get_base_strategy_score("correct_split_brush") == 90.0
            assert config.get_base_strategy_score("known_split") == 85.0

            # Test strategy modifiers
            assert (
                config.get_strategy_modifier("high_priority_automated_split", "multiple_brands")
                == 5.0
            )
            assert (
                config.get_strategy_modifier("high_priority_automated_split", "fiber_words") == 3.0
            )
            assert (
                config.get_strategy_modifier("high_priority_automated_split", "handle_confidence")
                == 10.0
            )

        finally:
            config_path.unlink()

    def test_config_with_default_file(self):
        """Test configuration with default file path."""
        # Create test-specific config instead of using production config
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

        # Create temporary config file for testing
        import tempfile
        from pathlib import Path

        import yaml

        temp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(test_config, temp_config_file)
        temp_config_file.close()

        try:
            test_config_path = Path(temp_config_file.name)
            config = BrushScoringConfig(config_path=test_config_path)

            # Verify default structure
            assert "base_strategies" in config.weights
            assert "strategy_modifiers" in config.weights

            # Verify all expected strategies are present (updated for current config)
            expected_strategies = [
                "correct_complete_brush",
                "correct_split_brush",
                "known_split",
                "known_brush",
                "omega_semogue",
                "zenith",
                "other_brush",
                "automated_split",
                "unified",
            ]

            for strategy in expected_strategies:
                assert strategy in config.weights["base_strategies"]
                score = config.get_base_strategy_score(strategy)
                assert isinstance(score, float)
                assert score > 0
        finally:
            # Clean up temporary file
            import os

            os.unlink(temp_config_file.name)

    def test_config_hot_reload(self):
        """Test hot-reloading configuration."""
        # Create initial config
        initial_config = {
            "brush_scoring_weights": {
                "base_strategies": {"correct_complete_brush": 90.0},
                "strategy_modifiers": {},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(initial_config, f)
            config_path = Path(f.name)

        try:
            config = BrushScoringConfig(config_path=config_path)
            assert config.get_base_strategy_score("correct_complete_brush") == 90.0

            # Update config file
            updated_config = {
                "brush_scoring_weights": {
                    "base_strategies": {"correct_complete_brush": 95.0},
                    "strategy_modifiers": {},
                }
            }

            with open(config_path, "w") as f:
                yaml.dump(updated_config, f)

            # Reload config
            config.reload_config()
            assert config.get_base_strategy_score("correct_complete_brush") == 95.0

        finally:
            config_path.unlink()

    def test_config_validation_integration(self):
        """Test configuration validation in integration."""
        # Test valid config
        valid_config = {
            "brush_scoring_weights": {
                "base_strategies": {"correct_complete_brush": 90.0},
                "strategy_modifiers": {"high_priority_automated_split": {"multiple_brands": 5.0}},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(valid_config, f)
            config_path = Path(f.name)

        try:
            config = BrushScoringConfig(config_path=config_path)
            config.validate_config_structure()
            config.validate_config_values()
        finally:
            config_path.unlink()

        # Test invalid config structure
        invalid_config = {"invalid_section": {}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(invalid_config, f)
            config_path = Path(f.name)

        try:
            with pytest.raises(ValueError, match="Configuration must contain"):
                BrushScoringConfig(config_path=config_path)
        finally:
            config_path.unlink()

    def test_config_with_pipeline_integration(self):
        """Test configuration integration with pipeline components."""
        config = BrushScoringConfig()

        # Test that config can be used by scoring components
        strategy_names = config.get_all_strategy_names()
        assert len(strategy_names) > 0

        # Test that all strategies have valid scores
        for strategy_name in strategy_names:
            score = config.get_base_strategy_score(strategy_name)
            assert score > 0
            assert isinstance(score, float)

        # Test that modifiers can be retrieved for strategies
        for strategy_name in strategy_names:
            modifier_names = config.get_all_modifier_names(strategy_name)
            for modifier_name in modifier_names:
                modifier_value = config.get_strategy_modifier(strategy_name, modifier_name)
                assert isinstance(modifier_value, (int, float))

    def test_config_performance(self):
        """Test configuration performance with repeated access."""
        config = BrushScoringConfig()

        # Test repeated access to same values using actual strategies from config
        for _ in range(100):
            # Use a strategy that actually exists in the config
            score = config.get_base_strategy_score("known_brush")
            assert score > 0

            # Use a modifier that actually exists in the config
            modifier = config.get_strategy_modifier("knot_matching", "brand_match")
            assert isinstance(modifier, float)

    def test_config_error_recovery(self):
        """Test configuration error recovery."""
        # Test with missing file
        config = BrushScoringConfig(config_path=Path("/nonexistent/config.yaml"))

        # Should fall back to default weights
        assert config.weights is not None
        assert "base_strategies" in config.weights
        assert "strategy_modifiers" in config.weights

        # Should still provide valid scores
        score = config.get_base_strategy_score("correct_complete_brush")
        assert score > 0
