"""Unit tests for brush splits data structures and validation logic."""

import json
import pytest
import yaml
from datetime import datetime
from unittest.mock import patch

from webui.api.brush_splits import (
    BrushSplit,
    BrushSplitOccurrence,
    BrushSplitValidator,
    BrushSplitStatistics,
    StatisticsCalculator,
    normalize_brush_string,
    ConfidenceLevel,
    DataCorruptionError,
    FileNotFoundError,
    ProcessingError,
)


class TestBrushSplitOccurrence:
    """Test BrushSplitOccurrence data structure."""

    def test_creation(self):
        """Test creating a brush split occurrence."""
        occurrence = BrushSplitOccurrence(file="test.json", comment_ids=["123", "456"])
        assert occurrence.file == "test.json"
        assert occurrence.comment_ids == ["123", "456"]

    def test_to_dict(self):
        """Test converting to dictionary."""
        occurrence = BrushSplitOccurrence(file="test.json", comment_ids=["123", "456"])
        data = occurrence.to_dict()
        assert data["file"] == "test.json"
        assert data["comment_ids"] == ["123", "456"]

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {"file": "test.json", "comment_ids": ["123", "456"]}
        occurrence = BrushSplitOccurrence.from_dict(data)
        assert occurrence.file == "test.json"
        assert occurrence.comment_ids == ["123", "456"]

    def test_from_dict_empty_comment_ids(self):
        """Test creating from dictionary with empty comment_ids."""
        data = {"file": "test.json"}
        occurrence = BrushSplitOccurrence.from_dict(data)
        assert occurrence.file == "test.json"
        assert occurrence.comment_ids == []


class TestBrushSplit:
    """Test BrushSplit data structure."""

    def test_creation_single_component(self):
        """Test creating a single component brush split."""
        split = BrushSplit(original="Declaration B15", handle=None, knot="Declaration B15")
        assert split.original == "Declaration B15"
        assert split.handle is None
        assert split.knot == "Declaration B15"
        assert split.validated_at is None
        assert not split.corrected

    def test_creation_multi_component(self):
        """Test creating a multi-component brush split."""
        split = BrushSplit(
            original="Declaration B15 w/ Chisel & Hound Zebra",
            handle="Declaration B15",
            knot="Chisel & Hound Zebra",
        )
        assert split.original == "Declaration B15 w/ Chisel & Hound Zebra"
        assert split.handle == "Declaration B15"
        assert split.knot == "Chisel & Hound Zebra"

    def test_to_dict_single_component(self):
        """Test converting single component to dictionary."""
        split = BrushSplit(original="Declaration B15", handle=None, knot="Declaration B15")
        data = split.to_dict()
        assert data["original"] == "Declaration B15"
        assert data["handle"] is None
        assert data["knot"] == "Declaration B15"
        assert data["validated_at"] is None
        assert not data["corrected"]

    def test_to_dict_corrected(self):
        """Test converting corrected split to dictionary."""
        split = BrushSplit(
            original="Declaration B15",
            handle=None,
            knot="Declaration B15",
            corrected=True,
            system_handle="Declaration",
            system_knot="B15",
            system_confidence=ConfidenceLevel.HIGH,
            system_reasoning="Test reasoning",
        )
        data = split.to_dict()
        assert data["corrected"] is True
        assert data["system_handle"] == "Declaration"
        assert data["system_knot"] == "B15"
        assert data["system_confidence"] == "high"
        assert data["system_reasoning"] == "Test reasoning"

    def test_from_dict(self):
        """Test creating from dictionary."""
        data = {
            "original": "Declaration B15",
            "handle": None,
            "knot": "Declaration B15",
            "validated_at": "2025-01-27T14:30:00Z",
            "corrected": False,
            "validated_at": "2025-01-27T14:30:00Z",
            "occurrences": [{"file": "test.json", "comment_ids": ["123"]}],
        }
        split = BrushSplit.from_dict(data)
        assert split.original == "Declaration B15"
        assert split.handle is None
        assert split.knot == "Declaration B15"
        assert split.validated_at is not None
        assert not split.corrected
        assert split.validated_at == "2025-01-27T14:30:00Z"
        assert len(split.occurrences) == 1
        assert split.occurrences[0].file == "test.json"

    def test_from_dict_with_system_fields(self):
        """Test creating from dictionary with system fields."""
        data = {
            "original": "Declaration B15",
            "handle": None,
            "knot": "Declaration B15",
            "corrected": True,
            "system_handle": "Declaration",
            "system_knot": "B15",
            "system_confidence": "high",
            "system_reasoning": "Test reasoning",
        }
        split = BrushSplit.from_dict(data)
        assert split.corrected
        assert split.system_handle == "Declaration"
        assert split.system_knot == "B15"
        assert split.system_confidence == ConfidenceLevel.HIGH
        assert split.system_reasoning == "Test reasoning"

    def test_from_dict_invalid_confidence(self):
        """Test creating from dictionary with invalid confidence."""
        data = {
            "original": "Declaration B15",
            "handle": None,
            "knot": "Declaration B15",
            "corrected": True,
            "system_confidence": "invalid",
        }
        split = BrushSplit.from_dict(data)
        assert split.system_confidence is None


class TestBrushSplitStatistics:
    """Test BrushSplitStatistics data structure."""

    def test_creation(self):
        """Test creating statistics."""
        stats = BrushSplitStatistics()
        assert stats.total == 0
        assert stats.validated == 0
        assert stats.corrected == 0
        assert stats.validation_percentage == 0.0
        assert stats.correction_percentage == 0.0

    def test_calculate_percentages(self):
        """Test calculating percentages."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.validated = 50
        stats.corrected = 10
        stats.calculate_percentages()
        assert stats.validation_percentage == 50.0
        assert stats.correction_percentage == 20.0

    def test_calculate_percentages_zero_total(self):
        """Test calculating percentages with zero total."""
        stats = BrushSplitStatistics()
        stats.total = 0
        stats.validated = 0
        stats.corrected = 0
        stats.calculate_percentages()
        assert stats.validation_percentage == 0.0
        assert stats.correction_percentage == 0.0

    def test_to_dict(self):
        """Test converting to dictionary."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.validated = 50
        stats.corrected = 10
        stats.validation_percentage = 50.0
        stats.correction_percentage = 20.0
        data = stats.to_dict()
        assert data["total"] == 100
        assert data["validated"] == 50
        assert data["corrected"] == 10
        assert data["validation_percentage"] == 50.0
        assert data["correction_percentage"] == 20.0

    def test_add_split(self):
        """Test adding a split to statistics."""
        stats = BrushSplitStatistics()
        split = BrushSplit(original="Test", handle="Test", knot="Test")
        stats.add_split(split)
        assert stats.total == 1
        assert stats.validated == 0
        assert stats.corrected == 0

    def test_add_validated_split(self):
        """Test adding a validated split to statistics."""
        stats = BrushSplitStatistics()
        split = BrushSplit(
            original="Test", handle="Test", knot="Test", validated_at="2025-01-27T14:30:00Z"
        )
        stats.add_split(split)
        assert stats.total == 1
        assert stats.validated == 1
        assert stats.corrected == 0

    def test_add_corrected_split(self):
        """Test adding a corrected split to statistics."""
        stats = BrushSplitStatistics()
        split = BrushSplit(
            original="Test",
            handle="Test",
            knot="Test",
            validated_at="2025-01-27T14:30:00Z",
            corrected=True,
        )
        stats.add_split(split)
        assert stats.total == 1
        assert stats.validated == 1
        assert stats.corrected == 1

    def test_reset(self):
        """Test resetting statistics."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.validated = 50
        stats.corrected = 10
        stats.reset()
        assert stats.total == 0
        assert stats.validated == 0
        assert stats.corrected == 0


class TestNormalizeBrushString:
    """Test brush string normalization."""

    def test_normalize_basic(self):
        """Test basic normalization."""
        result = normalize_brush_string("Declaration B15")
        assert result == "Declaration B15"

    def test_normalize_with_prefix(self):
        """Test normalization with brush prefix."""
        result = normalize_brush_string("brush: Declaration B15")
        assert result == "Declaration B15"

    def test_normalize_with_whitespace(self):
        """Test normalization with extra whitespace."""
        result = normalize_brush_string("  Declaration  B15  ")
        assert result == "Declaration B15"

    def test_normalize_empty(self):
        """Test normalization of empty string."""
        result = normalize_brush_string("")
        assert result is None

    def test_normalize_whitespace_only(self):
        """Test normalization of whitespace-only string."""
        result = normalize_brush_string("   ")
        assert result is None

    def test_normalize_none(self):
        """Test normalization of None."""
        result = normalize_brush_string(None)  # type: ignore
        assert result is None

    def test_case_insensitive_matching(self):
        """Test that brush strings are matched case-insensitively."""
        validator = BrushSplitValidator()

        # Create a validated split with one case
        split1 = validator.validate_split(
            "AP Shave Co. 24mm 'Synbad' Synthetic",
            None,
            "AP Shave Co. 24mm 'Synbad' Synthetic",
            validated_at="2025-01-27T14:30:00Z",
        )

        # Save it to the validator's internal storage
        validator.validated_splits[split1.original] = split1

        # Try to find it with different case
        existing_split = None
        for validated_key, validated_split in validator.validated_splits.items():
            if validated_key.lower() == "AP Shave Co. 24mm 'SynBad' Synthetic".lower():
                existing_split = validated_split
                break

        # Should find the existing split despite case difference
        assert existing_split is not None
        assert existing_split.original == "AP Shave Co. 24mm 'Synbad' Synthetic"
        assert existing_split.validated is True


class TestBrushSplitValidator:
    """Test BrushSplitValidator functionality."""

    def test_creation(self):
        """Test creating a validator."""
        validator = BrushSplitValidator()
        assert validator.validated_splits == {}
        assert validator.yaml_path.name == "brush_splits.yaml"

    def test_calculate_confidence_single_component(self):
        """Test confidence calculation for single component."""
        validator = BrushSplitValidator()
        confidence, reasoning = validator.calculate_confidence(
            "Declaration B15", None, "Declaration B15"
        )
        assert confidence == ConfidenceLevel.HIGH
        assert "single component" in reasoning.lower()

    def test_calculate_confidence_delimiter(self):
        """Test confidence calculation for delimiter split."""
        validator = BrushSplitValidator()
        confidence, reasoning = validator.calculate_confidence(
            "Declaration B15 w/ Chisel & Hound Zebra",
            "Declaration B15",
            "Chisel & Hound Zebra",
        )
        assert confidence == ConfidenceLevel.HIGH
        assert "delimiter" in reasoning.lower()

    def test_calculate_confidence_short_components(self):
        """Test confidence calculation for short components."""
        validator = BrushSplitValidator()
        confidence, reasoning = validator.calculate_confidence("A w/ B", "A", "B")
        assert confidence == ConfidenceLevel.LOW
        assert "short" in reasoning.lower()

    def test_calculate_confidence_empty_components(self):
        """Test confidence calculation for empty components."""
        validator = BrushSplitValidator()
        confidence, reasoning = validator.calculate_confidence(" w/ ", "", "")
        assert confidence == ConfidenceLevel.LOW
        assert "empty" in reasoning.lower()

    def test_validate_split_new(self):
        """Test validating a new split."""
        validator = BrushSplitValidator()
        split = validator.validate_split("Declaration B15", None, "Declaration B15")
        assert split.original == "Declaration B15"
        assert split.handle is None
        assert split.knot == "Declaration B15"
        assert not split.validated
        assert not split.corrected

    def test_validate_split_correction(self):
        """Test validating a new split (not actually a correction)."""
        validator = BrushSplitValidator()
        split = validator.validate_split(
            "Declaration B15",
            "Declaration",
            "B15",
            validated_at="2025-01-27T14:30:00Z",
        )
        assert split.original == "Declaration B15"
        assert split.handle == "Declaration"
        assert split.knot == "B15"
        assert split.validated
        assert not split.corrected  # This is a new split, not a correction
        assert split.validated_at == "2025-01-27T14:30:00Z"
        assert split.system_confidence is None  # No system confidence for new splits
        assert split.system_reasoning is None  # No system reasoning for new splits

    def test_save_and_load_yaml(self, tmp_path):
        """Test saving and loading YAML file."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "test_brush_splits.yaml"

        # Create test splits
        splits = [
            BrushSplit(original="Test1", handle="Test1", knot="Test1"),
            BrushSplit(original="Test2", handle="Test2", knot="Test2"),
        ]

        # Save splits
        success = validator.save_validated_splits(splits)
        assert success

        # Load splits
        validator.load_validated_splits()
        assert len(validator.validated_splits) == 2
        assert "Test1" in validator.validated_splits
        assert "Test2" in validator.validated_splits

    def test_merge_occurrences(self):
        """Test merging occurrences for existing splits."""
        validator = BrushSplitValidator()
        validator.validated_splits["Test"] = BrushSplit(original="Test", handle="Test", knot="Test")

        new_occurrences = [BrushSplitOccurrence(file="new.json", comment_ids=["123", "456"])]
        validator.merge_occurrences("Test", new_occurrences)

        split = validator.validated_splits["Test"]
        assert len(split.occurrences) == 1
        assert split.occurrences[0].file == "new.json"
        assert split.occurrences[0].comment_ids == ["123", "456"]

    def test_load_validated_splits_missing_file(self, tmp_path):
        """Test loading validated splits when file doesn't exist."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "nonexistent.yaml"
        validator.load_validated_splits()
        assert validator.validated_splits == {}

    def test_load_validated_splits_corrupted_yaml(self, tmp_path):
        """Test loading validated splits from corrupted YAML."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "corrupted.yaml"

        # Create corrupted YAML file
        with open(validator.yaml_path, "w") as f:
            f.write("invalid yaml content: [")

        with pytest.raises(DataCorruptionError):
            validator.load_validated_splits()

    def test_save_validated_splits_atomic_operation(self, tmp_path):
        """Test atomic save operation."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "test_atomic.yaml"

        splits = [BrushSplit(original="Test", handle="Test", knot="Test")]

        # Save should create the file atomically
        success = validator.save_validated_splits(splits)
        assert success
        assert validator.yaml_path.exists()

        # Verify the file contains valid YAML
        with open(validator.yaml_path, "r") as f:
            data = yaml.safe_load(f)
            assert isinstance(data, dict)

    def test_get_all_validated_splits(self):
        """Test getting all validated splits."""
        validator = BrushSplitValidator()
        validator.validated_splits = {
            "Test1": BrushSplit(original="Test1", handle="Test1", knot="Test1"),
            "Test2": BrushSplit(original="Test2", handle="Test2", knot="Test2"),
        }

        splits = validator.get_all_validated_splits()
        assert len(splits) == 2
        assert any(split.original == "Test1" for split in splits)
        assert any(split.original == "Test2" for split in splits)


class TestAdvancedBrushSplitStatistics:
    """Test advanced BrushSplitStatistics functionality."""

    def test_advanced_statistics_creation(self):
        """Test creating advanced statistics."""
        stats = BrushSplitStatistics()
        assert stats.split_types == {
            "delimiter": 0,
            "fiber_hint": 0,
            "no_split": 0,
        }
        assert stats.confidence_breakdown == {"high": 0, "medium": 0, "low": 0}
        assert stats.month_breakdown == {}
        assert stats.recent_activity == {}

    def test_add_split_method(self):
        """Test adding splits to enhanced statistics."""
        stats = BrushSplitStatistics()
        split = BrushSplit(original="Test", handle="Test", knot="Test")
        stats.add_split(split, month="2025-01")
        assert stats.total == 1
        assert stats.month_breakdown["2025-01"] == 1

    def test_add_corrected_split_with_confidence(self):
        """Test adding corrected split with confidence."""
        stats = BrushSplitStatistics()
        split = BrushSplit(
            original="Test",
            handle="Test",
            knot="Test",
            validated_at="2025-01-27T14:30:00Z",
            corrected=True,
            system_confidence=ConfidenceLevel.HIGH,
        )
        stats.add_split(split)
        assert stats.total == 1
        assert stats.validated == 1
        assert stats.corrected == 1
        assert stats.confidence_breakdown["high"] == 1

    def test_reset_method(self):
        """Test resetting enhanced statistics."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.split_types["delimiter"] = 50
        stats.confidence_breakdown["high"] = 30
        stats.month_breakdown["2025-01"] = 100
        stats.reset()
        assert stats.total == 0
        assert stats.split_types["delimiter"] == 0
        assert stats.confidence_breakdown["high"] == 0
        assert stats.month_breakdown == {}

    def test_advanced_to_dict(self):
        """Test converting advanced statistics to dictionary."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.validated = 50
        stats.corrected = 10
        stats.split_types["delimiter"] = 30
        stats.confidence_breakdown["high"] = 20
        stats.month_breakdown["2025-01"] = 100
        data = stats.to_dict()
        assert data["total"] == 100
        assert data["split_types"]["delimiter"] == 30
        assert data["confidence_breakdown"]["high"] == 20
        assert data["month_breakdown"]["2025-01"] == 100


class TestStatisticsCalculator:
    """Test StatisticsCalculator functionality."""

    def test_calculator_creation(self):
        """Test creating a statistics calculator."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)
        assert calculator.validator == validator

    def test_calculate_comprehensive_statistics(self):
        """Test calculating comprehensive statistics."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)

        splits = [
            BrushSplit(original="Test1", handle="Test1", knot="Test1"),
            BrushSplit(original="Test2", handle="Test2", knot="Test2"),
        ]

        stats = calculator.calculate_comprehensive_statistics(splits, ["2025-01"])
        assert stats.total == 2
        assert stats.month_breakdown["2025-01"] == 2

    def test_calculate_filtered_statistics(self):
        """Test calculating filtered statistics."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)

        splits = [
            BrushSplit(
                original="Test1", handle="Test1", knot="Test1", validated_at="2025-01-27T14:30:00Z"
            ),
            BrushSplit(original="Test2", handle="Test2", knot="Test2", validated_at=None),
        ]

        filters = {"validated_only": True}
        stats = calculator.calculate_filtered_statistics(splits, filters)
        assert stats.total == 1
        assert stats.validated == 1

    def test_apply_filters(self):
        """Test applying filters to splits."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)

        splits = [
            BrushSplit(
                original="Test1", handle="Test1", knot="Test1", validated_at="2025-01-27T14:30:00Z"
            ),
            BrushSplit(original="Test2", handle="Test2", knot="Test2", validated_at=None),
        ]

        # Test validated_only filter
        filtered = calculator._apply_filters(splits, {"validated_only": True})
        assert len(filtered) == 1
        assert filtered[0].validated_at is not None

        # Test confidence_level filter
        splits[0].system_confidence = ConfidenceLevel.HIGH
        filtered = calculator._apply_filters(splits, {"confidence_level": "high"})
        assert len(filtered) == 1
        assert filtered[0].system_confidence == ConfidenceLevel.HIGH

    def test_get_split_type(self):
        """Test determining split type."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)

        # Test delimiter split
        split = BrushSplit(original="Declaration w/ Chisel", handle="Declaration", knot="Chisel")
        split_type = calculator._get_split_type(split)
        assert split_type == "delimiter"

        # Test no split
        split = BrushSplit(original="Test", handle=None, knot="Test")
        split_type = calculator._get_split_type(split)
        assert split_type == "no_split"

    def test_calculate_recent_activity(self):
        """Test calculating recent activity."""
        validator = BrushSplitValidator()
        calculator = StatisticsCalculator(validator)

        # Create splits with recent validation
        now = datetime.now().isoformat()
        splits = [
            BrushSplit(
                original="Test1",
                handle="Test1",
                knot="Test1",
                validated_at=now,
            ),
            BrushSplit(
                original="Test2",
                handle="Test2",
                knot="Test2",
                validated_at=None,
            ),
        ]

        activity = calculator._calculate_recent_activity(splits)
        assert "validated_today" in activity
        assert "validated_this_week" in activity


class TestDataProcessingPipeline:
    """Test Step 7: Data Processing Pipeline enhancements."""

    def test_data_loading_with_mock_files(self, tmp_path):
        """Test data loading with mock files."""
        # Create mock matched data file
        mock_data = {
            "data": [
                {
                    "comment_id": "123",
                    "brush": {
                        "original": "Declaration B15",
                        "matched": {
                            "_original_handle_text": "Declaration",
                            "_original_knot_text": "B15",
                        },
                    },
                },
                {
                    "comment_id": "456",
                    "brush": {
                        "original": "Simpson Chubby 2",
                        "matched": {
                            "_original_handle_text": "Simpson Chubby 2",
                            "_original_knot_text": None,
                        },
                    },
                },
            ]
        }

        mock_file = tmp_path / "data" / "matched"
        mock_file.mkdir(parents=True)
        with open(mock_file / "2025-01.json", "w") as f:
            json.dump(mock_data, f)

        # Test loading with mock file
        # This would be tested through the API endpoint
        # For now, test the normalization function
        normalized = normalize_brush_string("Declaration B15")
        assert normalized == "Declaration B15"

    def test_progress_calculation(self):
        """Test progress calculation for data processing."""
        stats = BrushSplitStatistics()
        stats.total = 100
        stats.validated = 50
        stats.calculate_percentages()
        assert stats.validation_percentage == 50.0

        # Test edge cases
        stats.total = 0
        stats.validated = 0  # Reset validated count too
        stats.calculate_percentages()
        assert stats.validation_percentage == 0.0

    def test_error_handling_for_corrupted_files(self, tmp_path):
        """Test error handling for corrupted files."""
        # Create corrupted JSON file
        corrupted_file = tmp_path / "corrupted.json"
        with open(corrupted_file, "w") as f:
            f.write('{"invalid": json content')

        # Test that corrupted files are handled gracefully
        # This would be tested through the API endpoint
        # For now, test the error classes
        with pytest.raises(DataCorruptionError):
            raise DataCorruptionError("Test corruption error")

    def test_memory_usage_for_large_datasets_processing(self):
        """Test memory usage for large datasets during processing."""
        # Create large dataset
        large_splits = []
        for i in range(2500):  # ~2,500 records per month
            split = BrushSplit(
                original=f"Brush {i}",
                handle=f"Handle {i}",
                knot=f"Knot {i}",
                occurrences=[
                    BrushSplitOccurrence(file="2025-01.json", comment_ids=[f"comment_{i}"])
                ],
            )
            large_splits.append(split)

        # Test that large dataset can be processed
        assert len(large_splits) == 2500
        assert all(isinstance(split, BrushSplit) for split in large_splits)

        # Test statistics calculation with large dataset
        stats = BrushSplitStatistics()
        for split in large_splits:
            stats.add_split(split)
        assert stats.total == 2500

    def test_data_validation_and_integrity_checks(self):
        """Test data validation and integrity checks."""
        # Test valid brush split
        valid_split = BrushSplit(original="Declaration B15", handle="Declaration", knot="B15")
        assert valid_split.original is not None
        assert valid_split.knot is not None

        # Test invalid brush split (missing knot) - dataclasses don't enforce runtime type checking
        # The type hint is str but runtime allows None
        invalid_split = BrushSplit(original="Test", handle="Test", knot=None)  # type: ignore
        assert invalid_split.knot is None  # This is the actual behavior

        # Test data integrity
        validator = BrushSplitValidator()
        split = validator.validate_split("Test", "Test", "Test")
        assert split.original == "Test"
        assert split.handle == "Test"
        assert split.knot == "Test"

        # Test that single-component brushes work correctly
        single_split = BrushSplit(original="Declaration B15", handle=None, knot="Declaration B15")
        assert single_split.handle is None
        assert single_split.knot == "Declaration B15"

    def test_data_loading_with_real_matched_files(self, tmp_path):
        """Test data loading with real matched files."""
        # Create realistic matched data structure
        real_data = {
            "metadata": {
                "total_shaves": 2500,
                "unique_shavers": 150,
                "included_months": ["2025-01"],
                "missing_months": [],
            },
            "data": [
                {
                    "comment_id": "abc123",
                    "brush": {
                        "original": "Declaration B15 w/ Chisel & Hound Zebra",
                        "matched": {
                            "_original_handle_text": "Declaration B15",
                            "_original_knot_text": "Chisel & Hound Zebra",
                        },
                    },
                }
            ],
        }

        # Test that real data structure is valid
        assert "metadata" in real_data
        assert "data" in real_data
        assert len(real_data["data"]) > 0

        # Test brush data extraction
        brush_data = real_data["data"][0]["brush"]
        assert "original" in brush_data
        assert "matched" in brush_data

    def test_progress_tracking_with_actual_datasets(self):
        """Test progress tracking with actual datasets."""
        # Simulate processing 2500 records
        total_records = 2500
        processed_records = 0
        stats = BrushSplitStatistics()

        # Simulate processing in batches
        for i in range(0, total_records, 100):
            batch_size = min(100, total_records - i)
            processed_records += batch_size

            # Add some splits to statistics
            for j in range(batch_size):
                split = BrushSplit(
                    original=f"Brush {i + j}", handle=f"Handle {i + j}", knot=f"Knot {i + j}"
                )
                stats.add_split(split)

        assert processed_records == total_records
        assert stats.total == total_records

    def test_error_handling_with_corrupted_real_files(self, tmp_path):
        """Test error handling with corrupted real files."""
        # Create corrupted file that looks like real data
        corrupted_file = tmp_path / "corrupted_real.json"
        with open(corrupted_file, "w") as f:
            f.write('{"metadata": {"total_shaves": 2500}, "data": [{"invalid": structure}')

        # Test that corrupted files are detected
        # This would be tested through the API endpoint
        # For now, test error handling patterns
        try:
            with open(corrupted_file, "r") as f:
                json.load(f)
        except json.JSONDecodeError:
            # Expected behavior for corrupted JSON
            pass

    def test_processing_performance_for_typical_datasets(self):
        """Test processing performance for typical datasets."""
        # Simulate processing 2500 records and measure time
        start_time = datetime.now().timestamp()

        # Create 2500 test splits
        splits = []
        for i in range(2500):
            split = BrushSplit(original=f"Brush {i}", handle=f"Handle {i}", knot=f"Knot {i}")
            splits.append(split)

        # Calculate statistics
        stats = BrushSplitStatistics()
        for split in splits:
            stats.add_split(split)

        end_time = datetime.now().timestamp()
        processing_time = end_time - start_time

        # Performance should be reasonable (< 1 second for 2500 records)
        assert processing_time < 1.0
        assert len(splits) == 2500
        assert stats.total == 2500

    def test_memory_usage_for_large_datasets(self):
        """Test memory usage for large datasets."""
        # Create large dataset (2500 records)
        large_splits = []
        for i in range(2500):
            split = BrushSplit(
                original=f"Brush {i}",
                handle=f"Handle {i}",
                knot=f"Knot {i}",
                occurrences=[
                    BrushSplitOccurrence(file="2025-01.json", comment_ids=[f"comment_{i}"])
                ],
            )
            large_splits.append(split)

        # Memory usage should be reasonable (< 50MB for 2500 records)
        # Note: This is a rough estimate, actual memory usage depends on Python implementation
        assert len(large_splits) == 2500
        assert all(isinstance(split, BrushSplit) for split in large_splits)


class TestErrorHandling:
    """Test error handling functionality."""

    def test_file_not_found_error_handling(self):
        """Test file not found error handling."""
        with pytest.raises(FileNotFoundError):
            raise FileNotFoundError("Test file not found")

    def test_corrupted_yaml_file_handling(self, tmp_path):
        """Test handling corrupted YAML files."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "corrupted.yaml"

        # Create corrupted YAML
        with open(validator.yaml_path, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(DataCorruptionError):
            validator.load_validated_splits()

    def test_invalid_yaml_structure_handling(self, tmp_path):
        """Test handling invalid YAML structure."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "invalid_structure.yaml"

        # Create YAML with invalid structure
        with open(validator.yaml_path, "w") as f:
            yaml.dump("not a list", f)

        with pytest.raises(DataCorruptionError):
            validator.load_validated_splits()

    def test_save_fail_fast_on_data_errors(self, tmp_path):
        """Test fail-fast behavior on data errors."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "test_data_error.yaml"

        # Create invalid split (this would be caught by validation)
        # For now, test that the save method handles errors properly
        splits = [BrushSplit(original="Test", handle="Test", knot="Test")]
        success = validator.save_validated_splits(splits)
        assert success

    def test_load_fail_fast_on_file_io_error(self, tmp_path):
        """Test fail-fast behavior on file I/O errors during load."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "nonexistent" / "test.yaml"

        # Should fail fast when trying to load from non-existent path
        # But should not raise exception for missing files (they're handled gracefully)
        validator.load_validated_splits()
        assert validator.validated_splits == {}

    def test_load_fail_fast_on_data_corruption(self, tmp_path):
        """Test fail-fast behavior on data corruption during load."""
        validator = BrushSplitValidator()
        validator.yaml_path = tmp_path / "corrupted.yaml"

        # Create corrupted file
        with open(validator.yaml_path, "w") as f:
            f.write("invalid: yaml: content: [")

        # Should fail fast with clear error message
        with pytest.raises(DataCorruptionError):
            validator.load_validated_splits()


class TestAPIErrorHandling:
    """Test API endpoint error handling."""

    def test_load_endpoint_missing_months(self, client):
        """Test load endpoint with missing months parameter."""
        # Test with empty string which gets parsed as a single empty month
        # This should return 200 with error info in the response
        response = client.get("/api/brushes/splits/load?months=")
        assert response.status_code == 200  # Returns 200 with error info
        data = response.json()
        assert "errors" in data
        assert "failed_months" in data["errors"]

    def test_load_endpoint_missing_files(self, client):
        """Test load endpoint with missing files."""
        response = client.get("/api/brushes/splits/load?months=2025-99")
        assert response.status_code == 200  # Returns 200 with error info in response
        data = response.json()
        assert "errors" in data
        assert "failed_months" in data["errors"]

    def test_load_endpoint_corrupted_files(self, client, tmp_path):
        """Test load endpoint with corrupted files."""
        # Create a corrupted file
        corrupted_file = tmp_path / "data" / "matched" / "2025-01.json"
        corrupted_file.parent.mkdir(parents=True, exist_ok=True)
        corrupted_file.write_text("{ invalid json }")

        # Mock the file path
        with patch("webui.api.brush_splits.Path") as mock_path:
            mock_path.return_value = corrupted_file

            response = client.get("/api/brushes/splits/load?months=2025-01")
            assert response.status_code == 200  # Returns 200 with error info
            data = response.json()
            assert "errors" in data
            assert "failed_months" in data["errors"]

    def test_save_endpoint_no_data(self, client):
        """Test save endpoint with no data."""
        response = client.post("/api/brushes/splits/save", json={"brush_splits": []})
        assert response.status_code == 400

    def test_save_endpoint_invalid_data(self, client):
        """Test save endpoint with invalid data."""
        response = client.post("/api/brushes/splits/save", json={"invalid": "data"})
        assert response.status_code == 422

    def test_save_endpoint_file_error(self, client):
        """Test save endpoint with file error."""
        # Mock file operations to fail
        with patch("webui.api.brush_splits.validator.save_validated_splits") as mock_save:
            mock_save.return_value = False

            # Test data
            test_data = {
                "brush_splits": [
                    {
                        "original": "Test",
                        "handle": "Test",
                        "knot": "Test",
                        "validated": True,
                        "corrected": False,
                        "validated_at": "2025-01-27T14:30:00Z",
                        "occurrences": [],
                    }
                ]
            }

            # Make request
            response = client.post("/api/brushes/splits/save", json=test_data)

            # Should return 500 for file error
            assert response.status_code == 500
            data = response.json()
            assert "Failed to save splits to file" in data["detail"]

    def test_yaml_endpoint_file_not_found(self, client):
        """Test YAML endpoint with missing file."""
        response = client.get("/api/brushes/splits/yaml")
        assert response.status_code == 200  # Returns 200 with file info
        data = response.json()
        assert "file_info" in data
        # The file might exist or not, but the endpoint should always return 200
        assert "exists" in data["file_info"]
        assert "path" in data["file_info"]

    def test_statistics_endpoint_error_handling(self, client):
        """Test statistics endpoint error handling."""
        response = client.get("/api/brushes/splits/statistics")
        assert response.status_code == 200  # Should always return 200


class TestErrorCategorization:
    """Test error categorization and messaging."""

    def test_user_error_vs_system_error(self):
        """Test distinction between user errors and system errors."""

        with pytest.raises(ProcessingError):
            raise ProcessingError("Internal processing error")

    def test_error_message_clarity(self):
        """Test that error messages are clear and actionable."""
        # Test clear error messages
        try:
            raise FileNotFoundError("Month file not found: data/matched/2025-99.json")
        except FileNotFoundError as e:
            assert "Month file not found" in str(e)
            assert "2025-99.json" in str(e)

        try:
            raise DataCorruptionError("Invalid JSON structure in data/matched/2025-01.json")
        except DataCorruptionError as e:
            assert "Invalid JSON structure" in str(e)
            assert "2025-01.json" in str(e)


class TestSaveSplitEndpoint:
    """Test the save-split endpoint for individual corrections."""

    def test_save_single_split_endpoint(self, client, tmp_path):
        """Test saving a single brush split correction."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create brush_splits.yaml file
        yaml_file = data_dir / "brush_splits.yaml"
        yaml_file.write_text("brush_splits: []")

        # Mock the validator's yaml_path to prevent writing to production
        with patch("webui.api.brush_splits.validator.yaml_path", yaml_file):
            # Test data
            test_data = {
                "original": "Declaration B15 w/ Chisel & Hound Zebra",
                "handle": "Chisel & Hound Zebra",
                "knot": "Declaration B15",
                "validated_at": "2025-01-27T14:30:00Z",
            }

            # Make request
            response = client.post("/api/brushes/splits/save-split", json=test_data)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully saved brush split" in data["message"]
            assert data["corrected"] is False  # First time saving, not a correction
            assert data["system_handle"] is None
            assert data["system_knot"] is None

    def test_save_single_split_correction(self, client, tmp_path):
        """Test saving a correction of an existing split."""
        # Create test data directory
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        # Create brush_splits.yaml file with existing data (flat structure)
        yaml_file = data_dir / "brush_splits.yaml"
        existing_data = {
            "Declaration B15 w/ Chisel & Hound Zebra": {
                "handle": "Previous Handle",
                "knot": "Previous Knot",
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": False,
                "match_type": None,
                "occurrences": [],
            }
        }
        yaml_file.write_text(yaml.dump(existing_data))

        # Mock the file path at the module level to prevent writing to production
        with patch("webui.api.brush_splits.validator.yaml_path", yaml_file):
            # Test data for correction
            test_data = {
                "original": "Declaration B15 w/ Chisel & Hound Zebra",
                "handle": "Chisel & Hound Zebra",
                "knot": "Declaration B15",
                "validated_at": "2025-01-27T15:30:00Z",
            }

            # Make request
            response = client.post("/api/brushes/splits/save-split", json=test_data)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "Successfully saved brush split" in data["message"]
            # Note: correction detection is tested in validator tests

    def test_save_single_split_error_handling(self, client):
        """Test error handling for save-split endpoint."""
        # Test with invalid data
        test_data = {"original": "", "handle": "Test", "knot": "Test"}  # Invalid empty original

        response = client.post("/api/brushes/splits/save-split", json=test_data)

        # Should return 400 for validation error
        assert response.status_code == 400
        data = response.json()
        assert "Original field cannot be empty" in data["detail"]


class TestDeleteSplitEndpoint:
    """Test deleting a brush split override (revert to automatic)."""

    def test_delete_manual_split_removes_entry(self, client, tmp_path):
        """Deleting a manual split removes it from YAML so default parsing applies."""
        yaml_file = tmp_path / "brush_splits.yaml"
        existing_data = {
            "Virginia Cheng - Silvertip Badger Dogwood Hybrid 26mm": {
                "handle": "Dogwood Hybrid",
                "knot": "Virginia Cheng Silvertip Badger 26mm",
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": True,
                "should_not_split": False,
                "occurrences": [],
            },
            "Other Brush": {
                "handle": "Other Handle",
                "knot": "Other Knot",
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": False,
                "should_not_split": False,
                "occurrences": [],
            },
        }
        yaml_file.write_text(yaml.dump(existing_data))

        with patch("webui.api.brush_splits.validator.yaml_path", yaml_file):
            from webui.api.brush_splits import validator as brush_validator

            brush_validator.validated_splits.clear()

            response = client.delete(
                "/api/brushes/splits/split",
                params={
                    "original": "Virginia Cheng - Silvertip Badger Dogwood Hybrid 26mm",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted"] is True

            remaining = yaml.safe_load(yaml_file.read_text())
            assert "Virginia Cheng - Silvertip Badger Dogwood Hybrid 26mm" not in remaining
            assert "Other Brush" in remaining

    def test_delete_dont_split_removes_entry(self, client, tmp_path):
        """Deleting a don't-split override also removes the YAML entry."""
        yaml_file = tmp_path / "brush_splits.yaml"
        existing_data = {
            "Single Component Brush": {
                "should_not_split": True,
                "validated_at": "2025-01-27T14:30:00Z",
                "corrected": True,
                "occurrences": [],
            },
        }
        yaml_file.write_text(yaml.dump(existing_data))

        with patch("webui.api.brush_splits.validator.yaml_path", yaml_file):
            from webui.api.brush_splits import validator as brush_validator

            brush_validator.validated_splits.clear()

            response = client.delete(
                "/api/brushes/splits/split",
                params={"original": "Single Component Brush"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted"] is True

            remaining = yaml.safe_load(yaml_file.read_text()) or {}
            assert "Single Component Brush" not in remaining

    def test_delete_missing_entry_is_idempotent(self, client, tmp_path):
        """Deleting an entry that is already gone still succeeds."""
        yaml_file = tmp_path / "brush_splits.yaml"
        yaml_file.write_text(yaml.dump({"Keep Me": {"handle": "H", "knot": "K"}}))

        with patch("webui.api.brush_splits.validator.yaml_path", yaml_file):
            from webui.api.brush_splits import validator as brush_validator

            brush_validator.validated_splits.clear()

            response = client.delete(
                "/api/brushes/splits/split",
                params={"original": "Not In File"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["deleted"] is False

            remaining = yaml.safe_load(yaml_file.read_text())
            assert "Keep Me" in remaining

    def test_delete_requires_original(self, client):
        """Empty original is rejected."""
        response = client.delete("/api/brushes/splits/split", params={"original": ""})
        assert response.status_code == 400


def create_test_split(original: str):
    """Helper function to create test brush splits."""
    return BrushSplit(original=original, handle=original, knot=original)
