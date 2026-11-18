#!/usr/bin/env python3
"""Tests for correct-matches endpoint with composite brush logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add the webui directory to the Python path
webui_dir = Path(__file__).parent.parent
if str(webui_dir) not in sys.path:
    sys.path.insert(0, str(webui_dir))

from webui.api.analysis import get_correct_matches  # noqa: E402


class TestCorrectMatchesCompositeBrush:
    """Test cases for correct-matches endpoint with composite brush logic."""

    @patch("yaml.safe_load")
    def test_get_correct_matches_brush_combines_all_sections(self, mock_yaml_load):
        """Test that get_correct_matches for brush field combines data from brush, handle, and knot sections."""

        # Mock project_root - it's a module-level variable, not a function
        # We need to patch it as a property/attribute
        import webui.api.analysis

        original_project_root = webui.api.analysis.project_root
        webui.api.analysis.project_root = Path("/mock/project")

        # Initialize before try block to avoid unbound variable in finally
        original_exists = Path.exists
        original_open = Path.open

        try:
            # Track which file handle corresponds to which file path
            file_handles = {}
            file_open_order = []

            # Mock Path.exists() to return True for directory and section files
            def mock_exists(self):
                path_str = str(self)
                return path_str.endswith("correct_matches") or path_str.endswith(
                    ("brush.yaml", "handle.yaml", "knot.yaml")
                )

            # Mock Path.open() to track which file is opened and create a unique file handle
            def mock_open(self, *args, **kwargs):
                file_path = str(self)
                file_open_order.append(file_path)
                mock_file_context = MagicMock()
                mock_file_handle = MagicMock()
                # Store the file path as the name attribute so yaml.safe_load can access it
                mock_file_handle.name = file_path
                # Also store in our mapping
                file_handles[file_path] = mock_file_handle
                mock_file_context.__enter__ = MagicMock(return_value=mock_file_handle)
                mock_file_context.__exit__ = MagicMock(return_value=None)
                return mock_file_context

            # Apply the patches
            Path.exists = mock_exists
            Path.open = mock_open

            # Mock yaml.safe_load to return section-specific data based on call order
            call_count = [0]  # Use list to allow modification in nested function

            def yaml_load_side_effect(file_handle):
                # Return data based on call order (brush, handle, knot)
                call_count[0] += 1
                if call_count[0] == 1:  # First call - brush.yaml
                    return {"AP Shave Co": {"G5C": ["ap shave co g5c 24mm"]}}
                elif call_count[0] == 2:  # Second call - handle.yaml
                    return {
                        "AP Shave Co": {"Unspecified": ["ap shave co. - lemon drop 26mm tgn boar"]}
                    }
                elif call_count[0] == 3:  # Third call - knot.yaml
                    return {"The Golden Nib": {"Boar": ["ap shave co. - lemon drop 26mm tgn boar"]}}
                return {}

            mock_yaml_load.side_effect = yaml_load_side_effect

            # Call the async function
            import asyncio

            result = asyncio.run(get_correct_matches("brush"))

            # Verify the result combines all sections
            assert result.field == "brush"
            assert result.total_entries == 3  # 1 from brush + 1 from handle + 1 from knot

            # Verify the entries contain data from all sections
            entries = result.entries
            assert entries is not None

            # Should have brush section
            assert "brush" in entries
            assert "AP Shave Co" in entries["brush"]
            assert "G5C" in entries["brush"]["AP Shave Co"]
            assert "ap shave co g5c 24mm" in entries["brush"]["AP Shave Co"]["G5C"]

            # Should have handle section
            assert "handle" in entries
            assert "AP Shave Co" in entries["handle"]
            assert "Unspecified" in entries["handle"]["AP Shave Co"]
            handle_text = "ap shave co. - lemon drop 26mm tgn boar"
            assert handle_text in entries["handle"]["AP Shave Co"]["Unspecified"]

            # Should have knot section
            assert "knot" in entries
            assert "The Golden Nib" in entries["knot"]
            assert "Boar" in entries["knot"]["The Golden Nib"]
            knot_text = "ap shave co. - lemon drop 26mm tgn boar"
            assert knot_text in entries["knot"]["The Golden Nib"]["Boar"]

        finally:
            # Restore original project_root and Path methods
            webui.api.analysis.project_root = original_project_root
            Path.exists = original_exists
            Path.open = original_open

    @patch("yaml.safe_load")
    def test_get_correct_matches_brush_preserves_existing_brush_logic(self, mock_yaml_load):
        """Test that existing brush section logic is preserved when combining sections."""
        # Mock project_root
        import webui.api.analysis

        original_project_root = webui.api.analysis.project_root
        webui.api.analysis.project_root = Path("/mock/project")

        # Initialize before try block to avoid unbound variable in finally
        original_exists = Path.exists
        original_open = Path.open

        try:

            # Mock Path.exists() to return True only for brush.yaml (not handle/knot)
            def mock_exists(self):
                path_str = str(self)
                return path_str.endswith("correct_matches") or path_str.endswith("brush.yaml")

            # Mock Path.open() to create file handle
            def mock_open(self, *args, **kwargs):
                mock_file_context = MagicMock()
                mock_file_handle = MagicMock()
                mock_file_context.__enter__ = MagicMock(return_value=mock_file_handle)
                mock_file_context.__exit__ = MagicMock(return_value=None)
                return mock_file_context

            Path.exists = mock_exists
            Path.open = mock_open

            # Mock YAML data - brush.yaml contains data directly (not wrapped in "brush" key)
            mock_yaml_data = {
                "AP Shave Co": {"G5C": ["ap shave co g5c 24mm", "ap shave co g5c 26mm"]}
            }
            mock_yaml_load.return_value = mock_yaml_data

            # Call the async function
            import asyncio

            result = asyncio.run(get_correct_matches("brush"))

            # Verify the result works as before for brush-only data
            assert result.field == "brush"
            assert result.total_entries == 2  # 2 entries in the brush section

            # Verify the entries contain all three sections for composite brush logic
            # The UI expects all sections to be present even when empty
            entries = result.entries
            assert entries is not None
            assert "brush" in entries
            assert "AP Shave Co" in entries["brush"]
            assert "G5C" in entries["brush"]["AP Shave Co"]
            assert len(entries["brush"]["AP Shave Co"]["G5C"]) == 2

            # Handle and knot sections should be empty
            assert "handle" in entries
            assert "knot" in entries
            assert entries["handle"] == {}
            assert entries["knot"] == {}

        finally:
            # Restore original project_root and Path methods
            webui.api.analysis.project_root = original_project_root
            Path.exists = original_exists
            Path.open = original_open

    @patch("webui.api.analysis.project_root")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    def test_get_correct_matches_brush_handles_empty_sections(
        self, mock_yaml_load, mock_open, mock_project_root
    ):
        """Test that empty sections are handled gracefully."""
        # Mock YAML data with empty sections
        mock_yaml_data = {"brush": {}, "handle": {}, "knot": {}}

        mock_yaml_load.return_value = mock_yaml_data

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock file exists check
        with patch("pathlib.Path.exists", return_value=True):
            # Call the async function
            import asyncio

            result = asyncio.run(get_correct_matches("brush"))

            # Verify the result handles empty sections
            assert result.field == "brush"
            assert result.total_entries == 0

            # Verify the entries contain all sections even when empty
            entries = result.entries
            assert entries is not None
            assert "brush" in entries
            assert "handle" in entries
            assert "knot" in entries

    @patch("yaml.safe_load")
    def test_get_correct_matches_brush_handles_missing_sections(self, mock_yaml_load):
        """Test that missing sections are handled gracefully."""
        # Mock project_root
        import webui.api.analysis

        original_project_root = webui.api.analysis.project_root
        webui.api.analysis.project_root = Path("/mock/project")

        # Initialize before try block to avoid unbound variable in finally
        original_exists = Path.exists
        original_open = Path.open

        try:

            # Mock Path.exists() to return True only for brush.yaml (not handle/knot)
            def mock_exists(self):
                path_str = str(self)
                return path_str.endswith("correct_matches") or path_str.endswith("brush.yaml")

            # Mock Path.open() to create file handle
            def mock_open(self, *args, **kwargs):
                mock_file_context = MagicMock()
                mock_file_handle = MagicMock()
                mock_file_context.__enter__ = MagicMock(return_value=mock_file_handle)
                mock_file_context.__exit__ = MagicMock(return_value=None)
                return mock_file_context

            Path.exists = mock_exists
            Path.open = mock_open

            # Mock YAML data - brush.yaml contains data directly (not wrapped in "brush" key)
            mock_yaml_data = {"AP Shave Co": {"G5C": ["ap shave co g5c 24mm"]}}
            mock_yaml_load.return_value = mock_yaml_data

            # Call the async function
            import asyncio

            result = asyncio.run(get_correct_matches("brush"))

            # Verify the result handles missing sections
            assert result.field == "brush"
            assert result.total_entries == 1  # Only brush section entries

            # Verify the entries contain all three sections for composite brush logic
            # The UI expects all sections to be present even when empty
            entries = result.entries
            assert entries is not None
            assert "brush" in entries
            assert "AP Shave Co" in entries["brush"]
            assert "G5C" in entries["brush"]["AP Shave Co"]
            assert len(entries["brush"]["AP Shave Co"]["G5C"]) == 1

            # Handle and knot sections should be empty
            assert "handle" in entries
            assert "knot" in entries
            assert entries["handle"] == {}
            assert entries["knot"] == {}

        finally:
            # Restore original project_root and Path methods
            webui.api.analysis.project_root = original_project_root
            Path.exists = original_exists
            Path.open = original_open

    @patch("yaml.safe_load")
    def test_get_correct_matches_non_brush_fields_unaffected(self, mock_yaml_load):
        """Test that non-brush fields are not affected by the composite brush logic."""
        # Mock project_root
        import webui.api.analysis

        original_project_root = webui.api.analysis.project_root
        webui.api.analysis.project_root = Path("/mock/project")

        # Initialize before try block to avoid unbound variable in finally
        original_exists = Path.exists
        original_open = Path.open

        try:

            # Mock Path.exists() to return True for directory and razor.yaml only
            def mock_exists(self):
                path_str = str(self)
                return path_str.endswith("correct_matches") or path_str.endswith("razor.yaml")

            # Mock Path.open() to create file handle
            def mock_open(self, *args, **kwargs):
                mock_file_context = MagicMock()
                mock_file_handle = MagicMock()
                mock_file_context.__enter__ = MagicMock(return_value=mock_file_handle)
                mock_file_context.__exit__ = MagicMock(return_value=None)
                return mock_file_context

            Path.exists = mock_exists
            Path.open = mock_open

            # Mock YAML data - razor.yaml contains data directly (not wrapped in "razor" key)
            mock_yaml_data = {"Koraat": {"Moarteen": ["koraat moarteen"]}}
            mock_yaml_load.return_value = mock_yaml_data

            # Test razor field (should not be affected)
            import asyncio

            result = asyncio.run(get_correct_matches("razor"))

            # Verify razor field is not affected
            assert result.field == "razor"
            assert result.total_entries == 1  # Only razor section entries

            # Verify the entries contain only razor section data
            # Non-brush fields return data directly without field name wrapper
            entries = result.entries
            assert entries is not None
            assert "Koraat" in entries
            assert "brush" not in entries
            assert "handle" not in entries
            assert "knot" not in entries

        finally:
            # Restore original project_root and Path methods
            webui.api.analysis.project_root = original_project_root
            Path.exists = original_exists
            Path.open = original_open

    @patch("yaml.safe_load")
    def test_get_correct_matches_brush_composite_brush_confirmation_logic(self, mock_yaml_load):
        """Test that the combined data enables composite brush confirmation logic."""
        # Mock project_root
        import webui.api.analysis

        original_project_root = webui.api.analysis.project_root
        webui.api.analysis.project_root = Path("/mock/project")

        # Initialize before try block to avoid unbound variable in finally
        original_exists = Path.exists
        original_open = Path.open

        try:
            file_open_order = []

            # Mock Path.exists() to return True for all three section files
            def mock_exists(self):
                path_str = str(self)
                return path_str.endswith("correct_matches") or path_str.endswith(
                    ("brush.yaml", "handle.yaml", "knot.yaml")
                )

            # Mock Path.open() to track which file is opened
            def mock_open(self, *args, **kwargs):
                file_path = str(self)
                file_open_order.append(file_path)
                mock_file_context = MagicMock()
                mock_file_handle = MagicMock()
                mock_file_handle.name = file_path
                mock_file_context.__enter__ = MagicMock(return_value=mock_file_handle)
                mock_file_context.__exit__ = MagicMock(return_value=None)
                return mock_file_context

            Path.exists = mock_exists
            Path.open = mock_open

            # Mock yaml.safe_load to return different data based on call order
            call_count = [0]

            def yaml_load_side_effect(file_handle):
                call_count[0] += 1
                if call_count[0] == 1:  # brush.yaml
                    return {"AP Shave Co": {"G5C": ["ap shave co g5c 24mm"]}}
                elif call_count[0] == 2:  # handle.yaml
                    return {
                        "AP Shave Co": {"Unspecified": ["ap shave co. - lemon drop 26mm tgn boar"]}
                    }
                elif call_count[0] == 3:  # knot.yaml
                    return {"The Golden Nib": {"Boar": ["ap shave co. - lemon drop 26mm tgn boar"]}}
                return {}

            mock_yaml_load.side_effect = yaml_load_side_effect

            # Call the async function
            import asyncio

            result = asyncio.run(get_correct_matches("brush"))

            # Verify the result provides data needed for composite brush confirmation
            assert result.field == "brush"

            # The frontend should now be able to determine that:
            # "ap shave co. - lemon drop 26mm tgn boar" is confirmed because:
            # 1. Its handle component "AP Shave Co - Unspecified" exists in handle section
            # 2. Its knot component "The Golden Nib - Boar" exists in knot section

            entries = result.entries
            assert entries is not None

            # Verify handle component data is available
            assert "handle" in entries
            assert "AP Shave Co" in entries["handle"]
            assert "Unspecified" in entries["handle"]["AP Shave Co"]
            handle_entries = entries["handle"]["AP Shave Co"]["Unspecified"]
            assert "ap shave co. - lemon drop 26mm tgn boar" in handle_entries

            # Verify knot component data is available
            assert "knot" in entries
            assert "The Golden Nib" in entries["knot"]
            assert "Boar" in entries["knot"]["The Golden Nib"]
            knot_entries = entries["knot"]["The Golden Nib"]["Boar"]
            assert "ap shave co. - lemon drop 26mm tgn boar" in knot_entries

            # This enables the frontend to implement the logic:
            # is_confirmed = handle_confirmed AND knot_confirmed
            # where handle_confirmed = handle_source_text in handle_section
            # and knot_confirmed = knot_source_text in knot_section

        finally:
            # Restore original project_root and Path methods
            webui.api.analysis.project_root = original_project_root
            Path.exists = original_exists
            Path.open = original_open
