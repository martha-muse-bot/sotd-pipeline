#!/usr/bin/env python3
"""Tests for refactored brush_splits module using YAML utilities."""

from unittest.mock import patch

import pytest


class TestBrushSplitsYAMLRefactor:
    """Test that brush_splits module uses YAML utilities correctly."""

    def test_load_validated_splits_uses_yaml_utils(self, tmp_path):
        """Test that load_validated_splits loads data correctly."""
        from webui.api.brush_splits import BrushSplitValidator

        yaml_file = tmp_path / "brush_splits.yaml"

        # Mock the file operations to avoid touching filesystem
        with (
            patch("builtins.open") as mock_open,
            patch("yaml.safe_load") as mock_yaml_load,
            patch("pathlib.Path.exists") as mock_exists,
        ):

            # Mock file exists check
            mock_exists.return_value = True

            # Mock file content
            mock_yaml_load.return_value = {
                "Test Brush": {
                    "handle": "Test Handle",
                    "knot": "Test Knot",
                    "validated_at": "2025-08-28",
                    "should_not_split": False,
                }
            }

            validator = BrushSplitValidator()
            validator.yaml_path = yaml_file

            # Call the method
            validator.load_validated_splits()

            # Verify the file was opened and YAML was loaded
            mock_open.assert_called_once_with(yaml_file, "r", encoding="utf-8")
            mock_yaml_load.assert_called_once()

            # Verify data was loaded into validator
            assert "Test Brush" in validator.validated_splits

    def test_save_validated_splits_uses_yaml_utils(self, tmp_path):
        """Test that save_validated_splits saves data correctly."""
        from webui.api.brush_splits import BrushSplit, BrushSplitValidator

        # Create test splits
        test_splits = [
            BrushSplit(
                original="Test Brush",
                handle="Test Handle",
                knot="Test Knot",
                validated_at="2025-08-28",
                should_not_split=False,
            )
        ]

        yaml_file = tmp_path / "brush_splits.yaml"

        # Mock the file operations to avoid touching filesystem
        with (
            patch("builtins.open") as mock_open,
            patch("yaml.dump") as mock_yaml_dump,
            patch("pathlib.Path.exists") as mock_exists,
            patch("shutil.copy2") as mock_copy,
        ):

            # Mock file exists check
            mock_exists.return_value = True

            validator = BrushSplitValidator()
            validator.yaml_path = yaml_file

            # Call the method
            result = validator.save_validated_splits(test_splits)

            # Verify the method succeeded
            assert result is True

            # Verify file operations were called
            mock_open.assert_called_once_with(yaml_file, "w", encoding="utf-8")
            mock_yaml_dump.assert_called_once()

            # Verify backup was created
            mock_copy.assert_called_once()

    def test_load_validated_splits_handles_missing_file(self, tmp_path):
        """Test that load_validated_splits handles missing file gracefully."""
        yaml_file = tmp_path / "nonexistent.yaml"

        # Mock the file operations to avoid touching filesystem
        with patch("pathlib.Path.exists") as mock_exists:
            # Mock file doesn't exist
            mock_exists.return_value = False

            from webui.api.brush_splits import BrushSplitValidator

            validator = BrushSplitValidator()
            validator.yaml_path = yaml_file

            # Should handle missing file gracefully (no exception)
            validator.load_validated_splits()

            # Verify the method completed without error
            assert len(validator.validated_splits) == 0

    def test_load_validated_splits_handles_corrupted_data(self, tmp_path):
        """Test that load_validated_splits handles corrupted YAML data."""
        yaml_file = tmp_path / "corrupted.yaml"

        # Mock the file operations to avoid touching filesystem
        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open"),
            patch("yaml.safe_load") as mock_yaml_load,
        ):
            # Mock file exists
            mock_exists.return_value = True

            # Mock corrupted data (not a dict)
            mock_yaml_load.return_value = "not a dict"

            from webui.api.brush_splits import BrushSplitValidator, DataCorruptionError

            validator = BrushSplitValidator()
            validator.yaml_path = yaml_file

            # Should raise DataCorruptionError
            with pytest.raises(DataCorruptionError):
                validator.load_validated_splits()

    def test_save_validated_splits_handles_io_error(self, tmp_path):
        """Test that save_validated_splits handles I/O errors gracefully."""
        from webui.api.brush_splits import BrushSplit, BrushSplitValidator

        test_splits = [
            BrushSplit(
                original="Test Brush",
                handle="Test Handle",
                knot="Test Knot",
                validated_at="2025-08-28",
            )
        ]

        yaml_file = tmp_path / "brush_splits.yaml"

        # Mock the file operations to avoid touching filesystem
        with (
            patch("pathlib.Path.exists") as mock_exists,
            patch("builtins.open") as mock_open,
        ):
            # Mock file exists
            mock_exists.return_value = True

            # Mock I/O error when opening file
            mock_open.side_effect = OSError("I/O error")

            validator = BrushSplitValidator()
            validator.yaml_path = yaml_file

            # Should return False on error
            result = validator.save_validated_splits(test_splits)
            assert result is False

    def test_yaml_utils_integration(self, tmp_path):
        """Test full integration with YAML utilities."""
        from webui.api.brush_splits import BrushSplit, BrushSplitValidator

        # Create test data
        test_splits = [
            BrushSplit(
                original="Test Brush 1",
                handle="Test Handle",
                knot="Test Knot",
                validated_at="2025-08-28",
                should_not_split=False,
            ),
            BrushSplit(
                original="Test Brush 2",
                handle=None,
                knot="Test Brush 2",
                validated_at="2025-08-28",
                should_not_split=True,
            ),
        ]

        yaml_file = tmp_path / "brush_splits.yaml"

        # Test save
        validator = BrushSplitValidator()
        validator.yaml_path = yaml_file

        result = validator.save_validated_splits(test_splits)
        assert result is True
        assert yaml_file.exists()

        # Test load
        validator.validated_splits.clear()
        validator.load_validated_splits()

        assert len(validator.validated_splits) == 2
        assert "Test Brush 1" in validator.validated_splits
        assert "Test Brush 2" in validator.validated_splits
