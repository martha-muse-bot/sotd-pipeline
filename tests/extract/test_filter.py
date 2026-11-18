"""
Tests for the extract phase filtering module.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sotd.extract.filter import ExtractFilter, filter_extracted_data, should_skip_field


class TestExtractFilter:
    """Test cases for the ExtractFilter class."""

    def test_init_with_default_path(self):
        """Test initialization with default filter path."""
        filter_obj = ExtractFilter()
        assert filter_obj.filter_path == Path("data/extract_filters.yaml")

    def test_init_with_custom_path(self):
        """Test initialization with custom filter path."""
        custom_path = Path("/custom/path/filters.yaml")
        filter_obj = ExtractFilter(custom_path)
        assert filter_obj.filter_path == custom_path

    def test_load_filters_missing_file(self):
        """Test loading filters when file doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            filter_path = Path(temp_dir) / "nonexistent.yaml"
            filter_obj = ExtractFilter(filter_path)

            expected_default = {
                "razor": {"patterns": []},
                "blade": {"patterns": []},
                "brush": {"patterns": []},
                "soap": {"patterns": []},
                "global": [],
            }
            assert filter_obj.filters == expected_default

    def test_load_filters_valid_file(self):
        """Test loading filters from valid YAML file."""
        filter_config = {
            "razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]},
            "global": [".*\\$PLASTIC.* # plastic marker"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)
            assert filter_obj.filters == filter_config
        finally:
            filter_path.unlink()

    def test_load_filters_invalid_yaml(self):
        """Test loading filters from invalid YAML file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)
            # Should handle error gracefully and return default
            expected_default = {
                "razor": {"patterns": []},
                "blade": {"patterns": []},
                "brush": {"patterns": []},
                "soap": {"patterns": []},
                "global": [],
            }
            assert filter_obj.filters == expected_default
        finally:
            filter_path.unlink()

    def test_enhanced_regex_error_reporting(self):
        """Test that malformed regex patterns produce detailed error messages."""
        filter_config = {
            "razor": {
                "patterns": ["invalid[regex # malformed pattern"]
            },  # Malformed regex - missing closing bracket
            "global": ["valid.*pattern # valid pattern"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                ExtractFilter(filter_path)

            error_message = str(exc_info.value)
            assert "Invalid regex pattern" in error_message
            assert "invalid[regex" in error_message
            assert "File:" in error_message  # The actual file path will be the temp file
            assert "Field: razor" in error_message
            assert "unterminated character set" in error_message  # The actual regex error
        finally:
            filter_path.unlink()

    def test_compile_patterns_valid(self):
        """Test compiling valid regex patterns."""
        filter_config = {
            "razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]},
            "global": [".*\\$PLASTIC.* # plastic marker"],
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            # Check that patterns were compiled
            assert "razor" in filter_obj.compiled_patterns["filters"]
            assert len(filter_obj.compiled_patterns["filters"]["razor"]) == 1
            assert len(filter_obj.compiled_patterns["global_filters"]) == 1

            # Check pattern objects
            razor_pattern = filter_obj.compiled_patterns["filters"]["razor"][0]
            assert hasattr(razor_pattern["pattern"], "search")
            assert razor_pattern["reason"] == "toy/joke entry"
        finally:
            filter_path.unlink()

    def test_compile_patterns_invalid_regex(self):
        """Test handling of invalid regex patterns with enhanced error reporting."""
        filter_config = {"razor": {"patterns": ["[invalid # invalid pattern"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            with pytest.raises(ValueError) as exc_info:
                ExtractFilter(filter_path)

            error_message = str(exc_info.value)
            assert "Invalid regex pattern" in error_message
            assert "[invalid" in error_message
            assert "File:" in error_message
            assert "Field: razor" in error_message
            assert "unterminated character set" in error_message
        finally:
            filter_path.unlink()

    def test_should_skip_field_matches(self):
        """Test field filtering when pattern matches."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            should_skip, reason = filter_obj.should_skip_field("razor", "Hot Wheels Play Razor")
            assert should_skip is True
            assert reason == "toy/joke entry"
        finally:
            filter_path.unlink()

    def test_should_skip_field_no_match(self):
        """Test field filtering when pattern doesn't match."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            should_skip, reason = filter_obj.should_skip_field("razor", "Schick Injector Type I")
            assert should_skip is False
            assert reason is None
        finally:
            filter_path.unlink()

    def test_should_skip_field_global_filter(self):
        """Test global filtering."""
        filter_config = {"global": [".*\\$PLASTIC.* # plastic marker"]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            should_skip, reason = filter_obj.should_skip_field(
                "razor", "Some Razor $PLASTIC $RAINBOW"
            )
            assert should_skip is True
            assert reason == "plastic marker"
        finally:
            filter_path.unlink()

    def test_should_skip_field_case_insensitive(self):
        """Test that filtering is case insensitive."""
        filter_config = {"razor": {"patterns": ["hot wheels.*play.*razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            should_skip, reason = filter_obj.should_skip_field("razor", "HOT WHEELS PLAY RAZOR")
            assert should_skip is True
            assert reason == "toy/joke entry"
        finally:
            filter_path.unlink()

    def test_filter_extracted_data_valid_entries(self):
        """Test filtering with all valid entries."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            extracted_data = [
                {"razor": "Schick Injector Type I", "author": "user1"},
                {"blade": "Feather", "author": "user2"},
                {"brush": "Simpson", "author": "user3"},
            ]

            valid_entries, filtered_entries = filter_obj.filter_extracted_data(extracted_data)

            assert len(valid_entries) == 3
            assert len(filtered_entries) == 0
        finally:
            filter_path.unlink()

    def test_filter_extracted_data_filtered_entries(self):
        """Test filtering with some filtered entries."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            extracted_data = [
                {"razor": "Hot Wheels Play Razor", "author": "user1"},
                {"razor": "Schick Injector Type I", "author": "user2"},
                {"blade": "Feather", "author": "user3"},
            ]

            valid_entries, filtered_entries = filter_obj.filter_extracted_data(extracted_data)

            assert len(valid_entries) == 2
            assert len(filtered_entries) == 1
            assert filtered_entries[0]["razor"] == "Hot Wheels Play Razor"
            assert filtered_entries[0]["_filtered"] is True
            assert filtered_entries[0]["_filter_reasons"] == ["razor: toy/joke entry"]
        finally:
            filter_path.unlink()


class TestFilterFunctions:
    """Test cases for the convenience functions."""

    @patch("sotd.extract.filter._filter_instance")
    def test_should_skip_field_function(self, mock_instance):
        """Test the should_skip_field convenience function."""
        mock_instance.should_skip_field.return_value = (True, "Test reason")

        result = should_skip_field("razor", "test value")

        mock_instance.should_skip_field.assert_called_once_with("razor", "test value")
        assert result == (True, "Test reason")

    @patch("sotd.extract.filter._filter_instance")
    def test_filter_extracted_data_function(self, mock_instance):
        """Test the filter_extracted_data convenience function."""
        test_data = [{"test": "data"}]
        mock_instance.filter_extracted_data.return_value = ([], test_data)

        result = filter_extracted_data(test_data)

        mock_instance.filter_extracted_data.assert_called_once_with(test_data)
        assert result == ([], test_data)

    def test_convenience_functions_with_reset(self):
        """Test that convenience functions work with reset_filter for isolation."""
        from sotd.extract.filter import reset_filter

        # Reset to ensure clean state
        reset_filter()

        # Create a temporary filter file with a unique pattern
        filter_config = {"razor": {"patterns": ["UNIQUE_TEST_PATTERN.* # test pattern"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            # Create a custom filter instance and patch the global instance
            custom_filter = ExtractFilter(filter_path)

            with patch("sotd.extract.filter._filter_instance", custom_filter):
                # Test convenience function with unique pattern
                should_skip, reason = should_skip_field("razor", "UNIQUE_TEST_PATTERN test")
                assert should_skip is True
                assert reason == "test pattern"

                # Test that real entries pass
                should_skip, reason = should_skip_field("razor", "Schick Injector Type I")
                assert should_skip is False
                assert reason is None
        finally:
            filter_path.unlink()
            # Reset again to clean up
            reset_filter()


class TestRealWorldExamples:
    """Test cases with real-world examples from the user."""

    def test_hot_wheels_example(self):
        """Test the specific Hot Wheels example from the user."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor # toy/joke entry"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            # Test the exact example from the user
            should_skip, reason = filter_obj.should_skip_field(
                "razor", "Hot Wheels Play Razor $PLASTIC $RAINBOW"
            )
            assert should_skip is True
            assert reason == "toy/joke entry"

            # Test the real entry should pass
            should_skip, reason = filter_obj.should_skip_field("razor", "Schick Injector Type I")
            assert should_skip is False
            assert reason is None
        finally:
            filter_path.unlink()

    def test_plastic_rainbow_markers(self):
        """Test filtering with plastic/rainbow markers."""
        filter_config = {
            "razor": {
                "patterns": [".*\\$PLASTIC.*\\$RAINBOW # joke entry with plastic/rainbow markers"]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            # Test various combinations
            test_cases = [
                ("Some Razor $PLASTIC $RAINBOW", True),
                ("Another Razor $PLASTIC $RAINBOW extra", True),
                ("Real Razor", False),
                ("$PLASTIC Razor $RAINBOW", True),
            ]

            for value, expected_skip in test_cases:
                should_skip, reason = filter_obj.should_skip_field("razor", value)
                assert should_skip == expected_skip, f"Failed for: {value}"
        finally:
            filter_path.unlink()

    def test_pattern_without_comment(self):
        """Test pattern without inline comment."""
        filter_config = {"razor": {"patterns": ["Hot Wheels.*Play.*Razor"]}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(filter_config, f)
            filter_path = Path(f.name)

        try:
            filter_obj = ExtractFilter(filter_path)

            should_skip, reason = filter_obj.should_skip_field("razor", "Hot Wheels Play Razor")
            assert should_skip is True
            assert reason == "Matches pattern: Hot Wheels.*Play.*Razor"
        finally:
            filter_path.unlink()
