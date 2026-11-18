"""Tests for brush splits loader."""

from pathlib import Path

import pytest

from sotd.match.brush.comparison.splits_loader import BrushSplit, BrushSplitsLoader


class TestBrushSplitsLoader:
    """Test brush splits loader functionality."""

    @pytest.fixture
    def temp_yaml_path(self, tmp_path):
        """Create a temporary YAML file for testing."""
        yaml_file = tmp_path / "test_brush_splits.yaml"

        # Create test data using current structure: brush names as top-level keys
        test_data = {
            "Rad Dinosaur Creations - Jetson - 25mm Muhle STF": {
                "handle": "Rad Dinosaur Creations Jetson",
                "knot": "25mm Muhle STF",
                "match_type": "regex",
                "validated": True,
                "corrected": False,
                "should_not_split": False,
            },
            "Zenith 506U N (50/50 horse mane/tail) $WOODEN $HORSESASS": {
                "handle": "",
                "knot": "",
                "match_type": "regex",
                "validated": True,
                "corrected": False,
                "should_not_split": True,
            },
        }

        # Write test data to file
        import yaml

        with open(yaml_file, "w", encoding="utf-8") as f:
            yaml.dump(test_data, f, default_flow_style=False)

        return yaml_file

    def test_brush_split_from_dict(self):
        """Test BrushSplit creation from dictionary."""
        data = {
            "original": "Test Brush",
            "handle": "Test Handle",
            "knot": "Test Knot",
            "match_type": "regex",
            "validated": True,
            "corrected": False,
            "should_not_split": False,
        }

        split = BrushSplit.from_dict(data)

        assert split.original == "Test Brush"
        assert split.handle == "Test Handle"
        assert split.knot == "Test Knot"
        assert split.match_type == "regex"
        assert split.validated is True
        assert split.corrected is False
        assert split.should_not_split is False

    def test_brush_splits_loader_initialization(self):
        """Test brush splits loader initialization."""
        loader = BrushSplitsLoader()
        assert loader.brush_splits_path == Path("data/brush_splits.yaml")
        assert loader._splits == {}
        assert loader._loaded is False

    def test_brush_splits_loader_custom_path(self):
        """Test brush splits loader with custom path."""
        custom_path = Path("/custom/path/brush_splits.yaml")
        loader = BrushSplitsLoader(custom_path)
        assert loader.brush_splits_path == custom_path

    def test_load_splits_success(self, temp_yaml_path):
        """Test successful loading of brush splits."""
        loader = BrushSplitsLoader(temp_yaml_path)
        loader.load_splits()

        assert loader._loaded is True
        assert len(loader._splits) == 2

        # Check that splits were loaded correctly
        expected_original = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        assert expected_original in loader._splits

        split = loader._splits[expected_original]
        assert split.handle == "Rad Dinosaur Creations Jetson"
        assert split.knot == "25mm Muhle STF"
        assert split.should_not_split is False

    def test_load_splits_file_not_found(self):
        """Test loading when file doesn't exist."""
        non_existent_path = Path("/non/existent/file.yaml")
        loader = BrushSplitsLoader(non_existent_path)
        loader.load_splits()

        assert loader._loaded is True
        assert len(loader._splits) == 0

    def test_find_split_direct_match(self, temp_yaml_path):
        """Test finding split with direct match."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        split = loader.find_split(original)

        assert split is not None
        assert split.original == original
        assert split.handle == "Rad Dinosaur Creations Jetson"
        assert split.knot == "25mm Muhle STF"

    def test_find_split_case_insensitive(self, temp_yaml_path):
        """Test finding split with case-insensitive match."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original_lower = "rad dinosaur creations - jetson - 25mm muhle stf"
        split = loader.find_split(original_lower)

        assert split is not None
        assert split.original == "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"

    def test_find_split_normalized(self, temp_yaml_path):
        """Test finding split with normalized whitespace."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original_with_extra_spaces = "  Rad Dinosaur Creations - Jetson - 25mm Muhle STF  "
        split = loader.find_split(original_with_extra_spaces)

        assert split is not None
        assert split.original == "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"

    def test_find_split_not_found(self, temp_yaml_path):
        """Test finding split when not found."""
        loader = BrushSplitsLoader(temp_yaml_path)

        non_existent = "Non Existent Brush"
        split = loader.find_split(non_existent)

        assert split is None

    def test_get_handle_and_knot_success(self, temp_yaml_path):
        """Test getting handle and knot components."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        result = loader.get_handle_and_knot(original)

        assert result is not None
        handle, knot = result
        assert handle == "Rad Dinosaur Creations Jetson"
        assert knot == "25mm Muhle STF"

    def test_get_handle_and_knot_should_not_split(self, temp_yaml_path):
        """Test getting handle and knot when should_not_split is True."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original = "Zenith 506U N (50/50 horse mane/tail) $WOODEN $HORSESASS"
        result = loader.get_handle_and_knot(original)

        # Should return None because should_not_split is True
        assert result is None

    def test_get_handle_and_knot_not_found(self, temp_yaml_path):
        """Test getting handle and knot when not found."""
        loader = BrushSplitsLoader(temp_yaml_path)

        non_existent = "Non Existent Brush"
        result = loader.get_handle_and_knot(non_existent)

        assert result is None

    def test_should_not_split_true(self, temp_yaml_path):
        """Test should_not_split when True."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original = "Zenith 506U N (50/50 horse mane/tail) $WOODEN $HORSESASS"
        result = loader.should_not_split(original)

        assert result is True

    def test_should_not_split_false(self, temp_yaml_path):
        """Test should_not_split when False."""
        loader = BrushSplitsLoader(temp_yaml_path)

        original = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        result = loader.should_not_split(original)

        assert result is False

    def test_should_not_split_not_found(self, temp_yaml_path):
        """Test should_not_split when not found."""
        loader = BrushSplitsLoader(temp_yaml_path)

        non_existent = "Non Existent Brush"
        result = loader.should_not_split(non_existent)

        assert result is False

    def test_get_splits_count(self, temp_yaml_path):
        """Test getting splits count."""
        loader = BrushSplitsLoader(temp_yaml_path)

        count = loader.get_splits_count()
        assert count == 2
