import tempfile
from pathlib import Path

import yaml

from webui.api.validators.brush_split_validator import (
    BrushSplit,
    BrushSplitOccurrence,
    BrushSplitValidator,
    ConfidenceLevel,
)


class TestBrushSplitValidator:
    """Unit tests for the BrushSplitValidator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_yaml_path = Path(self.temp_dir) / "brush_splits.yaml"

        # Create test data
        self.test_data = {
            "splits": {
                "Test Brush 1": [
                    {
                        "original": "Test Brush 1",
                        "handle": "Test",
                        "knot": "Brush 1",
                        "validated": True,
                        "should_not_split": False,
                        "occurrences": [],
                    }
                ],
                "Test Brush 2": [
                    {
                        "original": "Test Brush 2",
                        "handle": None,
                        "knot": None,
                        "validated": True,
                        "should_not_split": True,
                        "occurrences": [],
                    }
                ],
            }
        }

        # Write test data to file
        with open(self.test_yaml_path, "w") as f:
            yaml.dump(self.test_data, f)

    def teardown_method(self):
        """Clean up test fixtures."""
        if self.test_yaml_path.exists():
            self.test_yaml_path.unlink()
        if Path(self.temp_dir).exists():
            import shutil

            shutil.rmtree(self.temp_dir)

    def test_brush_split_validator_initialization(self):
        """Test that BrushSplitValidator initializes correctly."""
        validator = BrushSplitValidator(self.test_yaml_path)

        assert validator.yaml_path == self.test_yaml_path
        assert validator.data == {}
        assert validator.is_loaded is False

    def test_normalize_brush_string(self):
        """Test brush string normalization."""
        validator = BrushSplitValidator()

        # Test basic normalization
        assert validator.normalize_brush_string("  Test Brush  ") == "Test Brush"

        # Test prefix removal
        assert validator.normalize_brush_string("brush: Test Brush") == "Test Brush"
        assert validator.normalize_brush_string("b: Test Brush") == "Test Brush"

        # Test whitespace normalization
        assert validator.normalize_brush_string("Test   Brush") == "Test Brush"

        # Test empty/None input
        assert validator.normalize_brush_string("") is None
        # Type ignore for None argument - test is checking None handling
        assert validator.normalize_brush_string(None) is None  # type: ignore

    def test_load_brush_splits_success(self):
        """Test successful brush splits loading."""
        validator = BrushSplitValidator(self.test_yaml_path)
        result = validator.load_brush_splits()

        assert result.success is True
        assert result.data is not None
        assert "brush_splits" in result.data
        assert len(result.data["brush_splits"]) == 2

    def test_load_brush_splits_file_not_found(self):
        """Test brush splits loading when file doesn't exist."""
        non_existent_path = Path("/non/existent/file.yaml")
        validator = BrushSplitValidator(non_existent_path)
        result = validator.load_brush_splits()

        assert result.success is False
        assert result.error_message is not None
        assert "File not found" in result.error_message

    def test_save_brush_splits_success(self):
        """Test successful brush splits saving."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        # Create brush splits
        brush_splits = [
            BrushSplit(
                original="New Brush 1",
                handle="New",
                knot="Brush 1",
                validated=True,
                should_not_split=False,
            ),
            BrushSplit(
                original="New Brush 2",
                handle=None,
                knot=None,
                validated=True,
                should_not_split=True,
            ),
        ]

        result = validator.save_brush_splits(brush_splits)

        assert result.success is True

        # Verify file was written
        with open(self.test_yaml_path, "r") as f:
            saved_data = yaml.safe_load(f)
        assert "splits" in saved_data
        assert len(saved_data["splits"]) == 2

    def test_get_brush_split_by_name_success(self):
        """Test successful brush split retrieval by name."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        brush_split = validator.get_brush_split_by_name("Test Brush 1")

        assert brush_split is not None
        assert brush_split.original == "Test Brush 1"
        assert brush_split.handle == "Test"
        assert brush_split.knot == "Brush 1"

    def test_get_brush_split_by_name_not_found(self):
        """Test brush split retrieval when item doesn't exist."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        brush_split = validator.get_brush_split_by_name("Non Existent Brush")

        assert brush_split is None

    def test_add_brush_split_success(self):
        """Test successful brush split addition."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        new_brush_split = BrushSplit(
            original="New Brush", handle="New", knot="Brush", validated=True, should_not_split=False
        )

        result = validator.add_brush_split(new_brush_split)

        assert result.success is True

        # Verify brush split was added
        added_brush_split = validator.get_brush_split_by_name("New Brush")
        assert added_brush_split is not None
        assert added_brush_split.original == "New Brush"

    def test_add_brush_split_already_exists(self):
        """Test brush split addition when item already exists."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        existing_brush_split = BrushSplit(
            original="Test Brush 1",
            handle="Test",
            knot="Brush 1",
            validated=True,
            should_not_split=False,
        )

        result = validator.add_brush_split(existing_brush_split)

        assert result.success is False
        assert result.error_message is not None
        assert "already exists" in result.error_message

    def test_update_brush_split_success(self):
        """Test successful brush split update."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        updated_brush_split = BrushSplit(
            original="Test Brush 1",
            handle="Updated",
            knot="Brush 1",
            validated=True,
            should_not_split=False,
        )

        result = validator.update_brush_split(updated_brush_split)

        assert result.success is True

        # Verify brush split was updated
        updated = validator.get_brush_split_by_name("Test Brush 1")
        assert updated is not None
        assert updated.handle == "Updated"

    def test_update_brush_split_not_found(self):
        """Test brush split update when item doesn't exist."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        non_existent_brush_split = BrushSplit(
            original="Non Existent Brush",
            handle="Test",
            knot="Brush",
            validated=True,
            should_not_split=False,
        )

        result = validator.update_brush_split(non_existent_brush_split)

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message

    def test_delete_brush_split_success(self):
        """Test successful brush split deletion."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        result = validator.delete_brush_split("Test Brush 1")

        assert result.success is True

        # Verify brush split was deleted
        deleted_brush_split = validator.get_brush_split_by_name("Test Brush 1")
        assert deleted_brush_split is None

    def test_delete_brush_split_not_found(self):
        """Test brush split deletion when item doesn't exist."""
        validator = BrushSplitValidator(self.test_yaml_path)
        validator.load_data()

        result = validator.delete_brush_split("Non Existent Brush")

        assert result.success is False
        assert result.error_message is not None
        assert "not found" in result.error_message

    def test_validate_brush_split_data_success(self):
        """Test successful brush split data validation."""
        validator = BrushSplitValidator()

        valid_brush_split = BrushSplit(
            original="Test Brush",
            handle="Test",
            knot="Brush",
            validated=True,
            should_not_split=False,
        )

        result = validator.validate_brush_split_data(valid_brush_split)

        assert result.success is True
        assert result.validation_errors is not None
        assert len(result.validation_errors) == 0

    def test_validate_brush_split_data_missing_original(self):
        """Test brush split data validation with missing original field."""
        validator = BrushSplitValidator()

        invalid_brush_split = BrushSplit(
            original="",  # Empty original
            handle="Test",
            knot="Brush",
            validated=True,
            should_not_split=False,
        )

        result = validator.validate_brush_split_data(invalid_brush_split)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("original" in error for error in result.validation_errors)

    def test_validate_brush_split_data_should_not_split_with_knot(self):
        """Test validation when should_not_split is true but knot is not null."""
        validator = BrushSplitValidator()

        invalid_brush_split = BrushSplit(
            original="Test Brush",
            handle=None,
            knot="Should be null",  # Should be null when should_not_split is true
            validated=True,
            should_not_split=True,
        )

        result = validator.validate_brush_split_data(invalid_brush_split)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("Knot must be null" in error for error in result.validation_errors)

    def test_validate_brush_split_data_no_split_no_should_not_split(self):
        """Test validation when no split is provided and should_not_split is false."""
        validator = BrushSplitValidator()

        invalid_brush_split = BrushSplit(
            original="Test Brush",
            handle=None,
            knot=None,
            validated=True,
            should_not_split=False,  # Should be true if no split provided
        )

        result = validator.validate_brush_split_data(invalid_brush_split)

        assert result.success is False
        assert result.validation_errors is not None
        assert len(result.validation_errors) > 0
        assert any("handle/knot" in error for error in result.validation_errors)

    def test_calculate_confidence_high(self):
        """Test confidence calculation for high confidence cases."""
        validator = BrushSplitValidator()

        # Test with explicit split indicator
        confidence, reason = validator.calculate_confidence("Test w/ Brush", "Test", "Brush")
        assert confidence == ConfidenceLevel.HIGH
        assert "explicit split indicator" in reason

        # Test with substantial content
        confidence, reason = validator.calculate_confidence("Test Brush", "LongHandle", "LongKnot")
        assert confidence == ConfidenceLevel.HIGH
        assert "substantial content" in reason

    def test_calculate_confidence_medium(self):
        """Test confidence calculation for medium confidence cases."""
        validator = BrushSplitValidator()

        # Test partial split
        confidence, reason = validator.calculate_confidence("Test Brush", "Test", None)
        assert confidence == ConfidenceLevel.MEDIUM
        assert "Partial split" in reason

        # Test standard split
        confidence, reason = validator.calculate_confidence("Test Brush", "Test", "Brush")
        assert confidence == ConfidenceLevel.MEDIUM
        assert "Standard split" in reason

    def test_calculate_confidence_low(self):
        """Test confidence calculation for low confidence cases."""
        validator = BrushSplitValidator()

        # Test no split provided
        confidence, reason = validator.calculate_confidence("Test Brush", None, None)
        assert confidence == ConfidenceLevel.LOW
        assert "No split provided" in reason

    def test_brush_split_to_dict(self):
        """Test BrushSplit to_dict method."""
        brush_split = BrushSplit(
            original="Test Brush",
            handle="Test",
            knot="Brush",
            validated=True,
            corrected=True,
            system_handle="System Test",
            system_knot="System Brush",
            system_confidence=ConfidenceLevel.HIGH,
            system_reasoning="Test reasoning",
            should_not_split=False,
            occurrences=[BrushSplitOccurrence(file="test.txt", comment_ids=["123"])],
        )

        result = brush_split.to_dict()

        assert result["original"] == "Test Brush"
        assert result["handle"] == "Test"
        assert result["knot"] == "Brush"
        assert result["validated"] is True
        assert result["corrected"] is True
        assert result["system_handle"] == "System Test"
        assert result["system_knot"] == "System Brush"
        assert result["system_confidence"] == "high"
        assert result["system_reasoning"] == "Test reasoning"
        assert result["should_not_split"] is False
        assert len(result["occurrences"]) == 1
        assert result["occurrences"][0]["file"] == "test.txt"

    def test_brush_split_from_dict(self):
        """Test BrushSplit from_dict method."""
        data = {
            "original": "Test Brush",
            "handle": "Test",
            "knot": "Brush",
            "validated": True,
            "corrected": True,
            "system_handle": "System Test",
            "system_knot": "System Brush",
            "system_confidence": "high",
            "system_reasoning": "Test reasoning",
            "should_not_split": False,
            "occurrences": [{"file": "test.txt", "comment_ids": ["123"]}],
        }

        brush_split = BrushSplit.from_dict(data)

        assert brush_split.original == "Test Brush"
        assert brush_split.handle == "Test"
        assert brush_split.knot == "Brush"
        assert brush_split.validated is True
        assert brush_split.corrected is True
        assert brush_split.system_handle == "System Test"
        assert brush_split.system_knot == "System Brush"
        assert brush_split.system_confidence == ConfidenceLevel.HIGH
        assert brush_split.system_reasoning == "Test reasoning"
        assert brush_split.should_not_split is False
        assert len(brush_split.occurrences) == 1
        assert brush_split.occurrences[0].file == "test.txt"
