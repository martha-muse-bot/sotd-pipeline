"""
Tests for Brush Configuration Updater.

This module tests the configuration update workflow that applies ChatGPT suggestions
to the brush scoring configuration with validation and rollback capabilities.
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.learning.brush_configuration_updater import BrushConfigurationUpdater


class TestBrushConfigurationUpdater:
    """Test the brush configuration updater."""

    def setup_method(self):
        """Set up test configuration file."""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_brush_scoring_config.yaml"

        # Create test configuration
        self.test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "known_brush": 80.0,
                    "unified": 50.0,
                    "automated_split": 60.0,
                },
                "strategy_modifiers": {
                    "automated_split": {
                        "multiple_brands": -3.0,
                        "fiber_words": 2.0,
                    },
                    "unified": {
                        "dual_component": 15.0,
                        "fiber_words": 0.0,
                    },
                },
            }
        }

        with open(self.config_path, "w") as f:
            yaml.dump(self.test_config, f)

    def teardown_method(self):
        """Clean up test files."""
        shutil.rmtree(self.temp_dir)

    def test_init_with_config_path(self):
        """Test initialization with configuration path."""
        updater = BrushConfigurationUpdater(self.config_path)

        assert updater.config_path == self.config_path
        assert updater.config_path.exists()

    def test_init_with_nonexistent_config(self):
        """Test initialization with non-existent configuration file."""
        nonexistent_path = Path(self.temp_dir) / "nonexistent.yaml"

        with pytest.raises(FileNotFoundError):
            BrushConfigurationUpdater(nonexistent_path)

    def test_load_configuration(self):
        """Test loading configuration from file."""
        updater = BrushConfigurationUpdater(self.config_path)

        config = updater.load_configuration()

        assert isinstance(config, dict)
        assert "brush_scoring_weights" in config
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 80.0

    def test_apply_base_strategy_weight_adjustments(self):
        """Test applying base strategy weight adjustments."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {
            "weight_adjustments": {
                "known_brush": 85.0,  # Increase from 80.0
                "unified": 45.0,  # Decrease from 50.0
            }
        }

        result = updater.apply_weight_adjustments(adjustments)

        assert result is True

        # Verify changes were applied
        updated_config = updater.load_configuration()
        base_strategies = updated_config["brush_scoring_weights"]["base_strategies"]
        assert base_strategies["known_brush"] == 85.0
        assert base_strategies["unified"] == 45.0
        assert base_strategies["automated_split"] == 60.0  # Unchanged

    def test_apply_modifier_weight_adjustments(self):
        """Test applying modifier weight adjustments."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {
            "modifier_adjustments": {
                "multiple_brands": -5.0,  # Decrease from -3.0
                "fiber_words": 5.0,  # Increase from 2.0
            }
        }

        result = updater.apply_modifier_adjustments(adjustments)

        assert result is True

        # Verify changes were applied to automated_split strategy
        updated_config = updater.load_configuration()
        modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"]["automated_split"]
        assert modifiers["multiple_brands"] == -5.0
        assert modifiers["fiber_words"] == 5.0

    def test_apply_new_modifiers(self):
        """Test applying new modifier suggestions."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {
            "suggested_new_modifiers": [
                {
                    "name": "custom_handle",
                    "suggested_weights": {
                        "automated_split": 15.0,
                        "unified": 10.0,
                    },
                },
                {
                    "name": "artisan_indicator",
                    "suggested_weights": {
                        "automated_split": 8.0,
                    },
                },
            ]
        }

        result = updater.apply_new_modifiers(adjustments)

        assert result is True

        # Verify new modifiers were added
        updated_config = updater.load_configuration()
        auto_split_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"][
            "automated_split"
        ]
        unified_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"]["unified"]

        assert auto_split_modifiers["custom_handle"] == 15.0
        assert auto_split_modifiers["artisan_indicator"] == 8.0
        assert unified_modifiers["custom_handle"] == 10.0

    def test_validate_configuration_valid(self):
        """Test configuration validation with valid configuration."""
        updater = BrushConfigurationUpdater(self.config_path)
        config = updater.load_configuration()

        is_valid = updater.validate_configuration(config)

        assert is_valid is True

    def test_validate_configuration_invalid_structure(self):
        """Test configuration validation with invalid structure."""
        updater = BrushConfigurationUpdater(self.config_path)

        invalid_config = {"invalid": "structure"}

        is_valid = updater.validate_configuration(invalid_config)

        assert is_valid is False

    def test_validate_configuration_missing_strategies(self):
        """Test configuration validation with missing required strategies."""
        updater = BrushConfigurationUpdater(self.config_path)

        invalid_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    # Missing required strategies
                },
                "strategy_modifiers": {},
            }
        }

        is_valid = updater.validate_configuration(invalid_config)

        assert is_valid is False

    def test_create_backup_configuration(self):
        """Test creating backup of current configuration."""
        updater = BrushConfigurationUpdater(self.config_path)

        backup_path = updater.create_backup()
        assert backup_path is not None

        assert backup_path.exists()
        assert backup_path.name.startswith("test_brush_scoring_config.yaml.backup")

        # Verify backup content matches original
        with open(backup_path, "r") as f:
            backup_config = yaml.safe_load(f)

        assert backup_config == self.test_config

    def test_rollback_configuration(self):
        """Test rolling back to previous configuration."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Create backup
        backup_path = updater.create_backup()

        # Make changes
        adjustments = {"weight_adjustments": {"known_brush": 90.0}}
        updater.apply_weight_adjustments(adjustments)

        # Verify change was applied
        config = updater.load_configuration()
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 90.0

        # Rollback
        result = updater.rollback_configuration()

        assert result is True

        # Verify rollback worked
        rolled_back_config = updater.load_configuration()
        assert rolled_back_config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 80.0

    def test_rollback_without_backup(self):
        """Test rollback when no backup exists."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Try to rollback without creating backup first
        result = updater.rollback_configuration()

        assert result is False

    def test_apply_comprehensive_chatgpt_suggestions(self):
        """Test applying comprehensive ChatGPT suggestions."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Mock comprehensive ChatGPT response
        chatgpt_suggestions = {
            "weight_adjustments": {
                "known_brush": 85.0,
                "unified": 45.0,
            },
            "modifier_adjustments": {
                "multiple_brands": -5.0,
                "fiber_words": 5.0,
            },
            "suggested_new_modifiers": [
                {
                    "name": "custom_handle",
                    "suggested_weights": {
                        "automated_split": 15.0,
                        "unified": 10.0,
                    },
                }
            ],
        }

        result = updater.apply_chatgpt_suggestions(chatgpt_suggestions)

        assert result is True

        # Verify all changes were applied
        updated_config = updater.load_configuration()
        base_strategies = updated_config["brush_scoring_weights"]["base_strategies"]
        auto_split_modifiers = updated_config["brush_scoring_weights"]["strategy_modifiers"][
            "automated_split"
        ]

        assert base_strategies["known_brush"] == 85.0
        assert base_strategies["unified"] == 45.0
        assert auto_split_modifiers["multiple_brands"] == -5.0
        assert auto_split_modifiers["fiber_words"] == 5.0
        assert auto_split_modifiers["custom_handle"] == 15.0

    def test_system_identification_in_updates(self):
        """Test that system identification is preserved in configuration updates."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {
            "system_info": {"system_type": "brush_scoring", "version": "1.0"},
            "weight_adjustments": {"known_brush": 85.0},
        }

        result = updater.apply_weight_adjustments(adjustments)

        assert result is True

        # Verify system identification is preserved (implementation should handle this)
        updated_config = updater.load_configuration()
        assert updated_config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 85.0

    def test_invalid_weight_values(self):
        """Test handling of invalid weight values."""
        updater = BrushConfigurationUpdater(self.config_path)

        # Test with negative base strategy weights (should be rejected)
        invalid_adjustments = {
            "weight_adjustments": {
                "known_brush": -10.0,  # Invalid negative weight
            }
        }

        result = updater.apply_weight_adjustments(invalid_adjustments)

        assert result is False

        # Configuration should remain unchanged
        config = updater.load_configuration()
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 80.0

    def test_unknown_strategy_handling(self):
        """Test handling of unknown strategies in adjustments."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {
            "weight_adjustments": {
                "unknown_strategy": 75.0,  # Strategy doesn't exist
                "known_brush": 85.0,  # Valid strategy
            }
        }

        result = updater.apply_weight_adjustments(adjustments)

        # Should succeed but only apply valid strategies
        assert result is True

        config = updater.load_configuration()
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 85.0
        assert "unknown_strategy" not in config["brush_scoring_weights"]["base_strategies"]

    def test_dry_run_mode(self):
        """Test dry run mode for configuration changes."""
        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {"weight_adjustments": {"known_brush": 85.0}}

        # Dry run should return what would be changed without applying changes
        changes = updater.preview_changes(adjustments)

        assert isinstance(changes, dict)
        assert "weight_adjustments" in changes
        assert changes["weight_adjustments"]["known_brush"]["old"] == 80.0
        assert changes["weight_adjustments"]["known_brush"]["new"] == 85.0

        # Verify original config is unchanged
        config = updater.load_configuration()
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 80.0

    def test_configuration_metadata_preservation(self):
        """Test that configuration metadata (comments, structure) is preserved."""
        # Add comments to test config
        config_with_comments = """# Brush Scoring Configuration
# Test configuration with comments

brush_scoring_weights:
  # Base strategy scores
  base_strategies:
    known_brush: 80.0
    unified: 50.0
    automated_split: 60.0
  
  # Strategy-specific modifiers  
  strategy_modifiers:
    automated_split:
      multiple_brands: -3.0
      fiber_words: 2.0
    unified:
      dual_component: 15.0
      fiber_words: 0.0
"""

        with open(self.config_path, "w") as f:
            f.write(config_with_comments)

        updater = BrushConfigurationUpdater(self.config_path)

        adjustments = {"weight_adjustments": {"known_brush": 85.0}}
        result = updater.apply_weight_adjustments(adjustments)

        assert result is True

        # Read the file content to check if structure is preserved
        with open(self.config_path, "r") as f:
            updated_content = f.read()

        # Header comments should be preserved
        assert "# Brush Scoring Configuration" in updated_content
        assert "# Test configuration with comments" in updated_content

        # Value should be updated
        config = updater.load_configuration()
        assert config["brush_scoring_weights"]["base_strategies"]["known_brush"] == 85.0


class TestBrushConfigurationUpdaterEdgeCases:
    """Test edge cases and error scenarios for brush configuration updater."""

    def test_concurrent_access_handling(self):
        """Test handling of concurrent access to configuration file."""
        # This test would verify file locking behavior - not implemented yet
        pass

    def test_corrupted_config_file_handling(self):
        """Test handling of corrupted configuration files."""
        temp_dir = tempfile.mkdtemp()
        config_path = Path(temp_dir) / "corrupted.yaml"

        # Create corrupted YAML file
        with open(config_path, "w") as f:
            f.write("invalid: yaml: content: [unclosed")

        try:
            with pytest.raises(yaml.YAMLError):
                BrushConfigurationUpdater(config_path)
        finally:
            shutil.rmtree(temp_dir)

    def test_permission_error_handling(self):
        """Test handling of permission errors."""
        # This would test read-only file scenarios
        # Implementation depends on system permissions
        pass
