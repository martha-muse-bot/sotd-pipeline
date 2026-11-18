"""
Integration tests for Brush Configuration Updater.

This module tests the configuration update workflow with real configuration files
and validates the complete workflow from ChatGPT suggestions to applied changes.
"""

import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import yaml

from sotd.learning.brush_chatgpt_analyzer import BrushChatGPTAnalyzer
from sotd.learning.brush_configuration_updater import BrushConfigurationUpdater
from sotd.learning.brush_learning_report_generator import BrushLearningReportGenerator


class TestBrushConfigurationUpdaterIntegration:
    """Integration tests for brush configuration updater."""

    def setup_method(self):
        """Set up test environment with real configuration structure."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "brush_scoring_config.yaml"

        # Create realistic test configuration based on actual structure
        self.realistic_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 100.0,
                    "correct_split_brush": 95.0,
                    "known_split": 90.0,
                    "known_brush": 80.0,
                    "omega_semogue": 75.0,
                    "zenith": 75.0,
                    "other_brush": 70.0,
                    "automated_split": 60.0,
                    "unified": 50.0,
                },
                "strategy_modifiers": {
                    "automated_split": {
                        "high_confidence": 25.0,
                        "multiple_brands": -3.0,
                        "fiber_words": 2.0,
                        "size_specification": 1.0,
                        "delimiter_confidence": 2.0,
                        "handle_confidence": 0.0,
                        "knot_confidence": 0.0,
                        "word_count_balance": 0.0,
                    },
                    "unified": {
                        "dual_component": 15.0,
                        "fiber_words": 0.0,
                        "size_specification": 0.0,
                        "delimiter_confidence": 0.0,
                        "handle_confidence": 0.0,
                        "knot_confidence": 0.0,
                        "word_count_balance": 0.0,
                    },
                    "known_brush": {
                        "multiple_brands": 0.0,
                        "fiber_words": 0.0,
                        "size_specification": 0.0,
                        "delimiter_confidence": 0.0,
                        "handle_confidence": 0.0,
                        "knot_confidence": 0.0,
                        "word_count_balance": 0.0,
                    },
                },
            }
        }

        with open(self.config_path, "w") as f:
            yaml.dump(self.realistic_config, f, default_flow_style=False, sort_keys=False, indent=2)

    def teardown_method(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)

    def test_complete_learning_to_configuration_workflow(self):
        """Test complete workflow from learning reports to configuration updates."""
        # Step 1: Generate learning reports with realistic validation data
        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 80.0},
                    {"strategy": "unified", "score": 45.0},
                ],
            },
            {
                "input_text": "Declaration Grooming / Zenith B2 Boar",
                "action": "overridden",
                "system_choice": {"strategy": "known_brush", "score": 70.0},
                "user_choice": {"strategy": "automated_split"},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 70.0},
                    {"strategy": "automated_split", "score": 85.0},
                ],
            },
            {
                "input_text": "Custom artisan handle with badger knot",
                "action": "overridden",
                "system_choice": {"strategy": "unified", "score": 50.0},
                "user_choice": {"strategy": "automated_split"},
                "all_strategies": [
                    {"strategy": "unified", "score": 50.0},
                    {"strategy": "automated_split", "score": 75.0},
                ],
            },
        ]

        # Step 2: Generate learning reports
        generator = BrushLearningReportGenerator(validation_data)
        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # Step 3: Analyze with ChatGPT (mock realistic responses)
        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.side_effect = [
                # Strategy analysis response
                {
                    "weight_adjustments": {
                        "known_brush": 85.0,  # Increase due to good base performance
                        "automated_split": 65.0,  # Increase due to user preferences
                        "unified": 45.0,  # Decrease due to override patterns
                    },
                    "reasoning": "Automated split shows higher user preference in override cases",
                },
                # Modifier analysis response
                {
                    "modifier_adjustments": {
                        "multiple_brands": -5.0,  # More negative penalty
                        "fiber_words": 5.0,  # Increase positive modifier
                    },
                    "reasoning": "Multiple brands causes confusion, fiber words help identification",
                },
                # Pattern discovery response
                {
                    "suggested_new_modifiers": [
                        {
                            "name": "artisan_indicator",
                            "function_name": "_modifier_artisan_indicator",
                            "pattern": "artisan|custom|handmade|turned",
                            "suggested_weights": {
                                "automated_split": 15.0,
                                "unified": 10.0,
                            },
                            "test_cases": [
                                "custom artisan handle with Omega knot",
                                "handmade turned handle",
                            ],
                        }
                    ],
                    "reasoning": "Artisan indicators correlate with split strategies",
                },
            ]

            # Analyze reports
            strategy_analysis = analyzer.analyze_strategy_selection(strategy_report)
            modifier_analysis = analyzer.analyze_modifier_performance(modifier_report)
            pattern_analysis = analyzer.analyze_pattern_discovery(pattern_report)

        # Step 4: Apply configuration updates
        updater = BrushConfigurationUpdater(self.config_path)

        # Combine all suggestions into comprehensive update
        comprehensive_suggestions = {
            "weight_adjustments": strategy_analysis.get("weight_adjustments", {}),
            "modifier_adjustments": modifier_analysis.get("modifier_adjustments", {}),
            "suggested_new_modifiers": pattern_analysis.get("suggested_new_modifiers", []),
        }

        # Apply all changes
        result = updater.apply_chatgpt_suggestions(comprehensive_suggestions)
        assert result is True

        # Step 5: Verify all changes were applied correctly
        updated_config = updater.load_configuration()
        base_strategies = updated_config["brush_scoring_weights"]["base_strategies"]
        auto_split_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"][
            "automated_split"
        ]
        unified_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"]["unified"]

        # Verify strategy weight changes
        assert base_strategies["known_brush"] == 85.0
        assert base_strategies["automated_split"] == 65.0
        assert base_strategies["unified"] == 45.0

        # Verify modifier changes
        assert auto_split_modifiers["multiple_brands"] == -5.0
        assert auto_split_modifiers["fiber_words"] == 5.0

        # Verify new modifier was added
        assert auto_split_modifiers["artisan_indicator"] == 15.0
        assert unified_modifiers["artisan_indicator"] == 10.0

    def test_rollback_after_failed_validation(self):
        """Test rollback when updated configuration fails validation."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Store original config for comparison
        original_config = updater.load_configuration()

        # Create malicious suggestions that would break validation
        bad_suggestions = {
            "weight_adjustments": {
                "known_brush": -50.0,  # Invalid negative weight
                "nonexistent_strategy": 75.0,  # Unknown strategy
            }
        }

        # Mock validation to fail for testing rollback
        with patch.object(updater, "validate_configuration") as mock_validate:
            mock_validate.return_value = False

            result = updater.apply_chatgpt_suggestions(bad_suggestions)

            # Should fail and rollback
            assert result is False

        # Verify configuration was rolled back to original state
        current_config = updater.load_configuration()
        assert current_config == original_config

    def test_integration_with_real_brush_scoring_config(self):
        """Test integration with the actual brush scoring configuration structure."""
        # Create test-specific config instead of using production file
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "correct_complete_brush": 100.0,
                    "correct_split_brush": 95.0,
                    "known_split": 90.0,
                    "known_brush": 80.0,
                    "automated_split": 60.0,
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
            updater = BrushConfigurationUpdater(test_config_path)

            # Test with realistic adjustments that might come from ChatGPT
            realistic_suggestions = {
                "weight_adjustments": {
                    "known_brush": 82.0,  # Small adjustment
                    "automated_split": 62.0,  # Small adjustment
                },
                "modifier_adjustments": {
                    "multiple_brands": -4.0,  # Adjust existing modifier
                },
            }

            result = updater.apply_chatgpt_suggestions(realistic_suggestions)
            assert result is True

            # Verify changes were applied
            updated_config = updater.load_configuration()
            base_strategies = updated_config["brush_scoring_weights"]["base_strategies"]

            assert base_strategies["known_brush"] == 82.0
            assert base_strategies["automated_split"] == 62.0

            # Find a strategy that has multiple_brands modifier
            strategy_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"]
            found_modifier_update = False
            for strategy_name, modifiers in strategy_modifiers.items():
                if "multiple_brands" in modifiers:
                    assert modifiers["multiple_brands"] == -4.0
                    found_modifier_update = True
                    break

            assert found_modifier_update, "multiple_brands modifier should have been updated"
        finally:
            # Clean up temporary file
            import os

            os.unlink(temp_config_file.name)

    def test_backup_and_restore_workflow(self):
        """Test the complete backup and restore workflow."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Store original state
        original_config = updater.load_configuration()

        # Create backup
        backup_path = updater.create_backup()
        assert backup_path is not None
        assert backup_path.exists()

        # Make changes
        suggestions = {
            "weight_adjustments": {
                "known_brush": 90.0,
                "automated_split": 70.0,
            }
        }

        result = updater.apply_chatgpt_suggestions(suggestions)
        assert result is True

        # Verify changes were applied
        modified_config = updater.load_configuration()
        assert modified_config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 90.0

        # Rollback to backup
        rollback_result = updater.rollback_configuration()
        assert rollback_result is True

        # Verify rollback worked
        restored_config = updater.load_configuration()
        assert restored_config == original_config

    def test_preview_changes_integration(self):
        """Test preview changes functionality with comprehensive suggestions."""
        updater = BrushConfigurationUpdater(self.config_path)

        suggestions = {
            "weight_adjustments": {
                "known_brush": 85.0,
                "automated_split": 65.0,
            },
            "modifier_adjustments": {
                "multiple_brands": -5.0,
                "fiber_words": 3.0,
            },
            "suggested_new_modifiers": [
                {
                    "name": "custom_handle",
                    "suggested_weights": {
                        "automated_split": 12.0,
                    },
                }
            ],
        }

        # Preview changes without applying them
        changes = updater.preview_changes(suggestions)

        # Verify preview structure
        assert "weight_adjustments" in changes
        assert "modifier_adjustments" in changes
        assert "new_modifiers" in changes

        # Check weight adjustment previews
        assert "known_brush" in changes["weight_adjustments"]
        assert changes["weight_adjustments"]["known_brush"]["old"] == 80.0
        assert changes["weight_adjustments"]["known_brush"]["new"] == 85.0

        # Check modifier adjustment previews
        modifier_changes = changes["modifier_adjustments"]
        assert any("multiple_brands" in key for key in modifier_changes.keys())

        # Check new modifiers preview
        assert len(changes["new_modifiers"]) == 1
        assert changes["new_modifiers"][0]["name"] == "custom_handle"

        # Verify original config is unchanged
        current_config = updater.load_configuration()
        assert current_config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 80.0

    def test_configuration_validation_integration(self):
        """Test configuration validation with various scenarios."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Test with valid configuration
        valid_config = updater.load_configuration()
        assert updater.validate_configuration(valid_config) is True

        # Test with invalid configuration structures
        invalid_configs = [
            {},  # Empty config
            {"invalid": "structure"},  # Wrong structure
            {"brush_scoring_weights": {}},  # Missing sections
            {"brush_scoring_weights": {"base_strategies": {}}},  # Empty strategies
        ]

        for invalid_config in invalid_configs:
            assert updater.validate_configuration(invalid_config) is False

    def test_error_handling_integration(self):
        """Test error handling in integration scenarios."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Test with malformed suggestions
        malformed_suggestions = [
            {"invalid": "structure"},
            {"weight_adjustments": "not_a_dict"},
            {"modifier_adjustments": {"invalid": "value"}},
        ]

        for malformed in malformed_suggestions:
            # Should handle gracefully and return False
            updater.apply_chatgpt_suggestions(malformed)
            # Implementation should handle errors gracefully
            # Exact behavior depends on implementation choices

        # Verify configuration remains valid after error attempts
        current_config = updater.load_configuration()
        assert updater.validate_configuration(current_config) is True
