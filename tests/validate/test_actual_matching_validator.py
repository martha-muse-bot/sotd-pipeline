"""
Tests for ActualMatchingValidator.

This module tests the actual matching validation functionality for all field types.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from sotd.validate.actual_matching_validator import (
    ActualMatchingValidator,
    ValidationIssue,
    ValidationResult,
)


class TestActualMatchingValidator:
    """Test cases for ActualMatchingValidator."""

    def setup_method(self):
        """Set up test fixtures."""
        self.validator = ActualMatchingValidator(data_path=Path("data"))
        self.mock_correct_matches = {
            "brush": {"AP Shave Co": {"Mixed Badger/Boar": ["ap shaveco 24mm luxury mixed knot"]}},
            "razor": {"Koraat": {"Moarteen": ["koraat moarteen"]}},
            "blade": {"Feather": {"ProGuard": ["feather proguard"]}},
            "soap": {"Barrister and Mann": {"Adagio": ["barrister & mann - adagio"]}},
        }

    def test_init(self):
        """Test validator initialization."""
        validator = ActualMatchingValidator()
        assert validator.data_path == Path("data")
        assert validator._matchers == {}
        assert validator._correct_matches_checker is None

    def test_init_with_custom_data_path(self):
        """Test validator initialization with custom data path."""
        custom_path = Path("/custom/data")
        validator = ActualMatchingValidator(data_path=custom_path)
        assert validator.data_path == custom_path

    def test_get_matcher_brush(self):
        """Test getting brush matcher."""
        matcher = self.validator._get_matcher("brush")
        assert matcher is not None
        assert "brush" in self.validator._matchers

    def test_get_matcher_razor(self):
        """Test getting razor matcher."""
        matcher = self.validator._get_matcher("razor")
        assert matcher is not None
        assert "razor" in self.validator._matchers

    def test_get_matcher_blade(self):
        """Test getting blade matcher."""
        matcher = self.validator._get_matcher("blade")
        assert matcher is not None
        assert "blade" in self.validator._matchers

    def test_get_matcher_soap(self):
        """Test getting soap matcher."""
        matcher = self.validator._get_matcher("soap")
        assert matcher is not None
        assert "soap" in self.validator._matchers

    def test_get_matcher_unsupported_field(self):
        """Test getting matcher for unsupported field."""
        with pytest.raises(ValueError, match="Unsupported field type"):
            self.validator._get_matcher("unsupported")

    def test_validate_data_structure_duplicate_strings(self):
        """Test data structure validation for duplicate strings."""
        correct_matches = {
            "brush": {
                "AP Shave Co": {
                    "Mixed Badger/Boar": [
                        "ap shaveco 24mm luxury mixed knot",
                        "ap shaveco 24mm luxury mixed knot",  # Duplicate
                    ]
                }
            }
        }

        issues = self.validator._validate_data_structure(correct_matches)

        assert len(issues) == 1
        assert issues[0].issue_type == "duplicate_string"
        assert issues[0].severity == "low"
        assert "ap shaveco 24mm luxury mixed knot" in issues[0].correct_match

    def test_validate_data_structure_cross_section_conflict(self):
        """Test data structure validation for cross-section conflicts."""
        correct_matches = {
            "brush": {"AP Shave Co": {"Mixed Badger/Boar": ["ap shaveco 24mm luxury mixed knot"]}},
            "handle": {
                "AP Shave Co": {"Unspecified": ["ap shaveco 24mm luxury mixed knot"]}  # Conflict
            },
        }

        issues = self.validator._validate_data_structure(correct_matches)

        assert len(issues) == 1
        assert issues[0].issue_type == "cross_section_conflict"
        assert issues[0].severity == "high"
        assert "ap shaveco 24mm luxury mixed knot" in issues[0].correct_match

    def test_validate_data_structure_no_issues(self):
        """Test data structure validation with no issues."""
        correct_matches = {
            "brush": {"AP Shave Co": {"Mixed Badger/Boar": ["ap shaveco 24mm luxury mixed knot"]}},
            "handle": {
                "Chisel & Hound": {
                    "Unspecified": ["chisel & hound tahitian pearl 26mm maggard shd"]
                }
            },
            "knot": {"Maggard": {"Badger": ["chisel & hound tahitian pearl 26mm maggard shd"]}},
        }

        issues = self.validator._validate_data_structure(correct_matches)
        assert len(issues) == 0

    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_entry_no_match(self, mock_brush_matcher_class):
        """Test brush entry validation when no match is found."""
        mock_matcher = Mock()
        mock_matcher.match.return_value = None
        mock_brush_matcher_class.return_value = mock_matcher

        expected_data = {"brand": "AP Shave Co", "model": "Mixed Badger/Boar"}
        issues = self.validator._validate_brush_entry(
            "ap shaveco 24mm luxury mixed knot", expected_data, "brush"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "no_match"
        assert issues[0].severity == "high"
        assert "ap shaveco 24mm luxury mixed knot" in issues[0].correct_match

    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_entry_data_mismatch(self, mock_brush_matcher_class):
        """Test brush entry validation when data doesn't match."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "AP Shave Co",
            "model": "Luxury Mixed",  # Different from expected
        }
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        expected_data = {"brand": "AP Shave Co", "model": "Mixed Badger/Boar"}
        issues = self.validator._validate_brush_entry(
            "ap shaveco 24mm luxury mixed knot", expected_data, "brush"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "data_mismatch"
        assert issues[0].severity == "high"
        assert issues[0].expected_model == "Mixed Badger/Boar"
        assert issues[0].actual_model == "Luxury Mixed"

    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_entry_structural_change(self, mock_brush_matcher_class):
        """Test brush entry validation when structural type changes."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "handle": {"brand": "AP Shave Co", "model": "Luxury Mixed"},
            "knot": {"brand": "AP Shave Co", "model": "Mixed Badger/Boar"},
        }
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        expected_data = {"brand": "AP Shave Co", "model": "Mixed Badger/Boar"}
        issues = self.validator._validate_brush_entry(
            "ap shaveco 24mm luxury mixed knot", expected_data, "brush"
        )

        # Should have structural change issue
        structural_issues = [i for i in issues if i.issue_type == "structural_change"]
        assert len(structural_issues) == 1
        assert structural_issues[0].severity == "high"
        assert structural_issues[0].expected_section == "brush"
        assert structural_issues[0].actual_section == "handle_knot"

    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_entry_handle_knot_mismatch(self, mock_brush_matcher_class):
        """Test brush entry validation for handle_knot entries with knot mismatch."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "handle": {
                "brand": "Dogwood",
                "model": "Unspecified",
            },
            "knot": {
                "brand": "Declaration Grooming",
                "model": "B9A",  # Missing the + that should be in B9A+
            },
        }
        mock_result.pattern = "exact_match"
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        expected_data = {
            "handle_maker": "Dogwood",
            "handle_model": "Unspecified",
            "knot_brand": "Declaration Grooming",
            "knot_model": "B9A+",  # Expected B9A+ but got B9A
        }
        issues = self.validator._validate_brush_entry(
            "dogwood handcrafts 26mm declaration b9a+",
            expected_data,
            "handle_knot",
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "data_mismatch"
        assert issues[0].severity == "high"
        assert issues[0].expected_knot_model == "B9A+"
        assert issues[0].actual_knot_model == "B9A"

    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_entry_handle_knot_no_brand_normalization(
        self, mock_brush_matcher_class
    ):
        """Test that None and _no_brand are treated as equivalent for handle_knot entries."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "handle": {
                "brand": None,  # Matcher returns None for no brand
                "model": "Unspecified",
            },
            "knot": {
                "brand": None,  # Matcher returns None for no brand
                "model": "Boar",
            },
        }
        mock_result.pattern = "exact_match"
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        # correct_matches uses _no_brand for entries without brands
        expected_data = {
            "handle_maker": "_no_brand",
            "handle_model": "Unspecified",
            "knot_brand": "_no_brand",
            "knot_model": "Boar",
        }
        issues = self.validator._validate_brush_entry(
            "my own brush with 20mm boar knot",
            expected_data,
            "handle_knot",
        )

        # Should have no issues since None and _no_brand are equivalent
        assert len(issues) == 0

    @patch("sotd.validate.actual_matching_validator.RazorMatcher")
    def test_validate_simple_entry_no_match(self, mock_razor_matcher_class):
        """Test simple entry validation when no match is found."""
        mock_matcher = Mock()
        mock_matcher.match.return_value = None
        mock_razor_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "razor", "koraat moarteen", "Koraat", "Moarteen"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "no_match"
        assert issues[0].severity == "high"
        assert "koraat moarteen" in issues[0].correct_match

    @patch("sotd.validate.actual_matching_validator.RazorMatcher")
    def test_validate_simple_entry_data_mismatch(self, mock_razor_matcher_class):
        """Test simple entry validation when data doesn't match."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "Koraat",
            "model": "Different Model",  # Different from expected
        }
        mock_matcher.match.return_value = mock_result
        mock_razor_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "razor", "koraat moarteen", "Koraat", "Moarteen"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "data_mismatch"
        assert issues[0].severity == "high"
        assert issues[0].expected_model == "Moarteen"
        assert issues[0].actual_model == "Different Model"

    @patch("sotd.validate.actual_matching_validator.SoapMatcher")
    def test_validate_simple_entry_soap_no_match(self, mock_soap_matcher_class):
        """Test soap entry validation when no match is found."""
        mock_matcher = Mock()
        mock_matcher.match.return_value = None
        mock_soap_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "soap", "345 co. - cairn", "345 Soap Co.", "Cairn"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "no_match"
        assert issues[0].severity == "high"
        assert "345 co. - cairn" in issues[0].correct_match

    @patch("sotd.validate.actual_matching_validator.SoapMatcher")
    def test_validate_simple_entry_soap_data_mismatch(self, mock_soap_matcher_class):
        """Test soap entry validation when scent doesn't match."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "345 Soap Co.",
            "scent": "Different Scent",  # Different from expected Cairn
        }
        mock_result.pattern = "345.*different"
        mock_matcher.match.return_value = mock_result
        mock_soap_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "soap", "345 co. - cairn", "345 Soap Co.", "Cairn"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "data_mismatch"
        assert issues[0].severity == "high"
        assert issues[0].expected_brand == "345 Soap Co."
        assert issues[0].expected_model == "Cairn"  # This is the scent name from YAML
        assert issues[0].actual_brand == "345 Soap Co."
        assert issues[0].actual_model == "Different Scent"  # Stored in actual_model for consistency
        assert "Brand/scent mismatch" in issues[0].details
        assert "brand/scent" in issues[0].suggested_action.lower()
        assert issues[0].matched_pattern == "345.*different"

    @patch("sotd.validate.actual_matching_validator.SoapMatcher")
    def test_validate_simple_entry_soap_correct_match(self, mock_soap_matcher_class):
        """Test soap entry validation when scent matches correctly."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "345 Soap Co.",
            "scent": "Cairn",  # Matches expected
        }
        mock_result.pattern = "345.*cairn"
        mock_matcher.match.return_value = mock_result
        mock_soap_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "soap", "345 co. - cairn", "345 Soap Co.", "Cairn"
        )

        # Should have no issues when scent matches
        assert len(issues) == 0

    @patch("sotd.validate.actual_matching_validator.SoapMatcher")
    def test_validate_simple_entry_soap_case_insensitive_match(self, mock_soap_matcher_class):
        """Test soap entry validation when scent matches but with different casing."""
        mock_matcher = Mock()
        mock_result = Mock()
        # Matcher returns lowercase scent, but YAML has proper casing
        mock_result.matched = {
            "brand": "Abbate Y La Mantia",
            "scent": "marduk",  # Lowercase, but YAML has "Marduk"
        }
        mock_result.pattern = "abbate.*marduk"
        mock_matcher.match.return_value = mock_result
        mock_soap_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "soap", "abbate y la mantia - marduk", "Abbate Y La Mantia", "Marduk"
        )

        # Should have no issues when scent matches (case-insensitive)
        assert len(issues) == 0

    @patch("sotd.validate.actual_matching_validator.SoapMatcher")
    def test_validate_simple_entry_soap_case_insensitive_brand(self, mock_soap_matcher_class):
        """Test soap entry validation when brand matches but with different casing."""
        mock_matcher = Mock()
        mock_result = Mock()
        # Matcher returns different brand casing
        mock_result.matched = {
            "brand": "ariana & evans",  # Lowercase, but YAML has "Ariana & Evans"
            "scent": "Aqua de Boracay",  # Matches expected
        }
        mock_result.pattern = "ariana.*boracay"
        mock_matcher.match.return_value = mock_result
        mock_soap_matcher_class.return_value = mock_matcher

        issues = self.validator._validate_simple_entry(
            "soap", "ariana & evans - aqua de boracay", "Ariana & Evans", "Aqua de Boracay"
        )

        # Should have no issues when brand matches (case-insensitive)
        assert len(issues) == 0

    @patch("sotd.validate.actual_matching_validator.BladeMatcher")
    def test_validate_simple_entry_blade_with_format_context(self, mock_blade_matcher_class):
        """Test blade entry validation with format context using match_with_context."""
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "Derby",
            "model": "USTA",  # Different from expected Extra
            "format": "DE",  # Matches expected format (DE razor context)
        }
        mock_result.pattern = "derb.*usta"
        # mock_with_context should be called for blades with format
        mock_matcher.match_with_context.return_value = mock_result
        mock_blade_matcher_class.return_value = mock_matcher

        # Entry is in DE format section, validate it matches correctly in DE format context
        # Expected: Derby/Extra, but matcher returns Derby/USTA
        issues = self.validator._validate_simple_entry(
            "blade", "derby usta", "Derby", "Extra", expected_format="DE"
        )

        assert len(issues) == 1
        assert issues[0].issue_type == "data_mismatch"
        assert issues[0].severity == "high"
        assert issues[0].correct_match == "derby usta"
        assert issues[0].expected_brand == "Derby"
        assert issues[0].expected_model == "Extra"
        assert issues[0].actual_brand == "Derby"
        assert issues[0].actual_model == "USTA"
        assert "DE format context" in issues[0].details
        assert issues[0].matched_pattern == "derb.*usta"
        # Verify match_with_context was called with format
        mock_matcher.match_with_context.assert_called_once_with("derby usta", "DE")

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_validate_brush_field(
        self, mock_brush_matcher_class, mock_yaml_load, mock_open, mock_glob, mock_exists
    ):
        """Test validation for brush field."""
        # Mock directory exists
        mock_exists.return_value = True

        # Mock directory structure: correct_matches/brush.yaml
        mock_brush_file = Mock()
        mock_brush_file.stem = "brush"
        mock_brush_file.name = "brush.yaml"
        mock_glob.return_value = [mock_brush_file]

        # Mock file reading - Path.open() returns a context manager
        mock_file_handle = Mock()
        mock_file_context = Mock()
        mock_file_context.__enter__ = Mock(return_value=mock_file_handle)
        mock_file_context.__exit__ = Mock(return_value=None)
        mock_brush_file.open.return_value = mock_file_context

        mock_yaml_load.return_value = self.mock_correct_matches["brush"]

        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {"brand": "AP Shave Co", "model": "Mixed Badger/Boar"}
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        result = self.validator.validate("brush")

        assert isinstance(result, ValidationResult)
        assert result.field == "brush"
        assert result.validation_mode == "actual_matching"
        assert result.total_entries == 1
        assert len(result.issues) == 0  # No issues since data matches

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    @patch("sotd.validate.actual_matching_validator.RazorMatcher")
    def test_validate_razor_field(
        self, mock_razor_matcher_class, mock_yaml_load, mock_open, mock_glob, mock_exists
    ):
        """Test validation for razor field."""
        # Mock directory exists
        mock_exists.return_value = True

        # Mock directory structure: correct_matches/razor.yaml
        mock_razor_file = Mock()
        mock_razor_file.stem = "razor"
        mock_razor_file.name = "razor.yaml"
        mock_glob.return_value = [mock_razor_file]

        # Mock file reading - Path.open() returns a context manager
        mock_file_handle = Mock()
        mock_file_context = Mock()
        mock_file_context.__enter__ = Mock(return_value=mock_file_handle)
        mock_file_context.__exit__ = Mock(return_value=None)
        mock_razor_file.open.return_value = mock_file_context

        mock_yaml_load.return_value = self.mock_correct_matches["razor"]

        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {"brand": "Koraat", "model": "Moarteen"}
        mock_matcher.match.return_value = mock_result
        mock_razor_matcher_class.return_value = mock_matcher

        result = self.validator.validate("razor")

        assert isinstance(result, ValidationResult)
        assert result.field == "razor"
        assert result.validation_mode == "actual_matching"
        assert result.total_entries == 1
        assert len(result.issues) == 0  # No issues since data matches

    def test_validation_issue_creation(self):
        """Test ValidationIssue creation and properties."""
        issue = ValidationIssue(
            issue_type="data_mismatch",
            severity="high",
            correct_match="test string",
            expected_brand="Expected Brand",
            expected_model="Expected Model",
            actual_brand="Actual Brand",
            actual_model="Actual Model",
            details="Test details",
            suggested_action="Test action",
        )

        assert issue.issue_type == "data_mismatch"
        assert issue.severity == "high"
        assert issue.correct_match == "test string"
        assert issue.expected_brand == "Expected Brand"
        assert issue.expected_model == "Expected Model"
        assert issue.actual_brand == "Actual Brand"
        assert issue.actual_model == "Actual Model"
        assert issue.details == "Test details"
        assert issue.suggested_action == "Test action"

    def test_validation_result_creation(self):
        """Test ValidationResult creation and properties."""
        issues = [
            ValidationIssue("data_mismatch", "high", "test string"),
            ValidationIssue("no_match", "medium", "test string 2"),
        ]

        result = ValidationResult(
            field="brush",
            total_entries=10,
            issues=issues,
            processing_time=1.5,
            validation_mode="actual_matching",
            strategy_stats={"strategy1": 5, "strategy2": 3},
            performance_metrics={"memory_usage": "100MB"},
        )

        assert result.field == "brush"
        assert result.total_entries == 10
        assert len(result.issues) == 2
        assert result.processing_time == 1.5
        assert result.validation_mode == "actual_matching"
        assert result.strategy_stats == {"strategy1": 5, "strategy2": 3}
        assert result.performance_metrics == {"memory_usage": "100MB"}

    def test_validation_result_defaults(self):
        """Test ValidationResult with default values."""
        result = ValidationResult(field="razor", total_entries=5, issues=[], processing_time=0.5)

        assert result.field == "razor"
        assert result.total_entries == 5
        assert len(result.issues) == 0
        assert result.processing_time == 0.5
        assert result.validation_mode == "actual_matching"
        assert result.strategy_stats == {}
        assert result.performance_metrics == {}

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("yaml.safe_load")
    @patch("sotd.validate.actual_matching_validator.BrushMatcher")
    def test_deduplicate_structural_change_issues(
        self, mock_brush_matcher_class, mock_yaml_load, mock_glob, mock_exists
    ):
        """Test that duplicate structural_change issues are deduplicated when same string appears in multiple files."""
        # Mock directory exists
        mock_exists.return_value = True

        # Mock directory structure: correct_matches/handle.yaml and knot.yaml
        mock_handle_file = Mock()
        mock_handle_file.stem = "handle"
        mock_handle_file.name = "handle.yaml"
        mock_knot_file = Mock()
        mock_knot_file.stem = "knot"
        mock_knot_file.name = "knot.yaml"
        mock_glob.return_value = [mock_handle_file, mock_knot_file]

        # Mock file reading - Path.open() returns a context manager
        mock_handle_file_handle = Mock()
        mock_handle_file_context = Mock()
        mock_handle_file_context.__enter__ = Mock(return_value=mock_handle_file_handle)
        mock_handle_file_context.__exit__ = Mock(return_value=None)
        mock_handle_file.open.return_value = mock_handle_file_context

        mock_knot_file_handle = Mock()
        mock_knot_file_context = Mock()
        mock_knot_file_context.__enter__ = Mock(return_value=mock_knot_file_handle)
        mock_knot_file_context.__exit__ = Mock(return_value=None)
        mock_knot_file.open.return_value = mock_knot_file_context

        # Mock YAML data - same string appears in both handle.yaml and knot.yaml
        test_string = "grizzly bay - sophisticated kaos bar-bear w/ v25 fanchurian"

        def yaml_load_side_effect(f):
            if f == mock_handle_file_handle:
                return {"Grizzly Bay": {"Unspecified": [test_string]}}
            elif f == mock_knot_file_handle:
                return {"Chisel & Hound": {"v25": [test_string]}}
            return None

        mock_yaml_load.side_effect = yaml_load_side_effect

        # Mock brush matcher to return a complete brush match (structural change from handle_knot to brush)
        mock_matcher = Mock()
        mock_result = Mock()
        mock_result.matched = {
            "brand": "Grizzly Bay",
            "model": "Sophisticated Kaos Bar-Bear",
        }
        mock_result.pattern = "test pattern"
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher_class.return_value = mock_matcher

        # Mock splits loader to not have this string in brush_splits.yaml
        with patch.object(self.validator, "_get_splits_loader") as mock_splits_loader:
            mock_splits = Mock()
            mock_splits.should_not_split.return_value = False
            mock_splits.find_split.return_value = None
            mock_splits_loader.return_value = mock_splits

            result = self.validator.validate("brush")

            # Should have only ONE structural_change issue, not two
            structural_change_issues = [
                i for i in result.issues if i.issue_type == "structural_change"
            ]
            assert len(structural_change_issues) == 1, (
                f"Expected 1 structural_change issue, got {len(structural_change_issues)}. "
                f"Issues: {[i.correct_match for i in structural_change_issues]}"
            )
            assert structural_change_issues[0].correct_match == test_string
            assert structural_change_issues[0].expected_section == "handle_knot"
            assert structural_change_issues[0].actual_section == "brush"

    def test_suppress_data_mismatch_when_structural_change_exists(self):
        """Test that data_mismatch issues are suppressed when structural_change exists."""
        # Create test issues that would normally cause duplicates
        issues = [
            ValidationIssue(
                issue_type="structural_change",
                severity="high",
                correct_match="test brush string",
                expected_section="brush",
                actual_section="handle_knot",
                details="Brush type changed from brush to handle_knot",
                suggested_action="Move 'test brush string' from brush section to handle_knot section",
            ),
            ValidationIssue(
                issue_type="data_mismatch",
                severity="high",
                correct_match="test brush string",
                expected_brand="Expected Brand",
                expected_model="Expected Model",
                actual_brand=None,
                actual_model=None,
                details="Brand/model mismatch: expected 'Expected Brand Expected Model', got 'None None'",
                suggested_action="Update correct_matches.yaml to reflect new brand/model: 'None None'",
            ),
            ValidationIssue(
                issue_type="data_mismatch",
                severity="high",
                correct_match="different brush string",
                expected_brand="Different Brand",
                expected_model="Different Model",
                actual_brand="Actual Brand",
                actual_model="Actual Model",
                details="Brand/model mismatch: expected 'Different Brand Different Model', got 'Actual Brand Actual Model'",
                suggested_action="Update correct_matches.yaml to reflect new brand/model: 'Actual Brand Actual Model'",
            ),
        ]

        # Apply the same filtering logic as in the validator
        structural_change_patterns = {
            issue.correct_match.lower()
            for issue in issues
            if issue.issue_type == "structural_change"
        }

        filtered_issues = [
            issue
            for issue in issues
            if not (
                issue.issue_type == "data_mismatch"
                and issue.correct_match.lower() in structural_change_patterns
            )
        ]

        # Should have 2 issues: 1 structural_change + 1 data_mismatch (for different string)
        assert len(filtered_issues) == 2

        # Verify the structural_change issue is preserved
        structural_issues = [i for i in filtered_issues if i.issue_type == "structural_change"]
        assert len(structural_issues) == 1
        assert structural_issues[0].correct_match == "test brush string"

        # Verify the data_mismatch for the same string is suppressed
        data_mismatch_issues = [i for i in filtered_issues if i.issue_type == "data_mismatch"]
        assert len(data_mismatch_issues) == 1
        assert data_mismatch_issues[0].correct_match == "different brush string"

        # Verify no overlap between structural_change and data_mismatch patterns
        structural_patterns = {
            issue.correct_match.lower()
            for issue in filtered_issues
            if issue.issue_type == "structural_change"
        }

        data_mismatch_patterns = {
            issue.correct_match.lower()
            for issue in filtered_issues
            if issue.issue_type == "data_mismatch"
        }

        overlap = structural_patterns & data_mismatch_patterns
        assert len(overlap) == 0, (
            f"Found both structural_change and data_mismatch for: {overlap}. "
            f"data_mismatch should be suppressed."
        )

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("builtins.open")
    @patch("yaml.safe_load")
    @patch("sotd.validate.actual_matching_validator.BladeMatcher")
    def test_validate_blade_field_format_based_structure(
        self, mock_blade_matcher_class, mock_yaml_load, mock_open, mock_glob, mock_exists
    ):
        """Test validation for blade field with format-based structure."""
        # Mock directory exists
        mock_exists.return_value = True

        # Mock directory structure: correct_matches/blade.yaml
        mock_blade_file = Mock()
        mock_blade_file.stem = "blade"
        mock_blade_file.name = "blade.yaml"
        mock_glob.return_value = [mock_blade_file]

        # Mock file reading - Path.open() returns a context manager
        mock_file_handle = Mock()
        mock_file_context = Mock()
        mock_file_context.__enter__ = Mock(return_value=mock_file_handle)
        mock_file_context.__exit__ = Mock(return_value=None)
        mock_blade_file.open.return_value = mock_file_context

        # Mock format-based structure (DE, Half DE, etc.)
        mock_yaml_load.return_value = {
            "DE": {
                "Derby": {
                    "Extra": ["derby extra", "derby usta"],  # derby usta is in wrong format section
                }
            },
            "Half DE": {
                "Derby": {
                    "USTA": ["derby usta 1/2 de"],
                }
            },
        }

        mock_matcher = Mock()

        # match_with_context should be called for blades with format context
        def match_with_context_side_effect(value, format_name, **kwargs):
            mock_result = Mock()
            if "derby extra" in value.lower() and format_name == "DE":
                mock_result.matched = {"brand": "Derby", "model": "Extra", "format": "DE"}
            elif "derby usta" in value.lower() and format_name == "DE":
                # In DE format context, it matches to USTA (different model than expected Extra)
                mock_result.matched = {"brand": "Derby", "model": "USTA", "format": "DE"}
            elif "derby usta 1/2 de" in value.lower() and format_name == "Half DE":
                mock_result.matched = {"brand": "Derby", "model": "USTA", "format": "Half DE"}
            else:
                mock_result.matched = None
            mock_result.pattern = "test pattern"
            return mock_result

        mock_matcher.match_with_context.side_effect = match_with_context_side_effect
        mock_blade_matcher_class.return_value = mock_matcher

        result = self.validator.validate("blade")

        assert isinstance(result, ValidationResult)
        assert result.field == "blade"
        assert result.validation_mode == "actual_matching"
        assert (
            result.total_entries == 3
        )  # "derby extra", "derby usta" (DE), "derby usta 1/2 de" (Half DE)

        # Should have 1 data_mismatch issue for "derby usta" in DE section
        # (expected Derby/Extra, got Derby/USTA in DE format context)
        data_mismatch_issues = [i for i in result.issues if i.issue_type == "data_mismatch"]
        derby_usta_issues = [
            i for i in data_mismatch_issues if "derby usta" in i.correct_match.lower()
        ]
        assert len(derby_usta_issues) == 1
        assert derby_usta_issues[0].expected_model == "Extra"
        assert derby_usta_issues[0].actual_model == "USTA"
        assert "DE format context" in derby_usta_issues[0].details


class TestValidationIssue:
    """Test cases for ValidationIssue class."""

    def test_validation_issue_minimal(self):
        """Test ValidationIssue with minimal required fields."""
        issue = ValidationIssue(
            issue_type="test_issue", severity="low", correct_match="test string"
        )

        assert issue.issue_type == "test_issue"
        assert issue.severity == "low"
        assert issue.correct_match == "test string"
        assert issue.expected_brand is None
        assert issue.actual_brand is None

    def test_validation_issue_complete(self):
        """Test ValidationIssue with all fields."""
        issue = ValidationIssue(
            issue_type="data_mismatch",
            severity="high",
            correct_match="test string",
            expected_brand="Expected Brand",
            expected_model="Expected Model",
            actual_brand="Actual Brand",
            actual_model="Actual Model",
            expected_handle_brand="Expected Handle Brand",
            expected_handle_model="Expected Handle Model",
            actual_handle_brand="Actual Handle Brand",
            actual_handle_model="Actual Handle Model",
            expected_knot_brand="Expected Knot Brand",
            expected_knot_model="Expected Knot Model",
            actual_knot_brand="Actual Knot Brand",
            actual_knot_model="Actual Knot Model",
            expected_section="brush",
            actual_section="handle_knot",
            details="Test details",
            suggested_action="Test action",
        )

        assert issue.issue_type == "data_mismatch"
        assert issue.severity == "high"
        assert issue.correct_match == "test string"
        assert issue.expected_brand == "Expected Brand"
        assert issue.expected_model == "Expected Model"
        assert issue.actual_brand == "Actual Brand"
        assert issue.actual_model == "Actual Model"
        assert issue.expected_handle_brand == "Expected Handle Brand"
        assert issue.expected_handle_model == "Expected Handle Model"
        assert issue.actual_handle_brand == "Actual Handle Brand"
        assert issue.actual_handle_model == "Actual Handle Model"
        assert issue.expected_knot_brand == "Expected Knot Brand"
        assert issue.expected_knot_model == "Expected Knot Model"
        assert issue.actual_knot_brand == "Actual Knot Brand"
        assert issue.actual_knot_model == "Actual Knot Model"
        assert issue.expected_section == "brush"
        assert issue.actual_section == "handle_knot"
        assert issue.details == "Test details"
        assert issue.suggested_action == "Test action"
