#!/usr/bin/env python3
"""Tests for ParameterValidator."""

from sotd.report.parameter_validator import ParameterValidator


class TestParameterValidator:
    """Test cases for ParameterValidator."""

    def test_validate_parameters_valid_sorting_column(self):
        """Test validation of valid sorting column parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {"shaves": 5})

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_parameters_multiple_valid_parameters(self):
        """Test validation of multiple valid parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {"shaves": 5, "unique_users": 3})

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_parameters_invalid_sorting_column(self):
        """Test validation of invalid sorting column parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {"invalid_column": 5})

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "invalid_column" in result.errors[0]
        assert "not a sorting column" in result.errors[0]

    def test_validate_parameters_mixed_valid_invalid(self):
        """Test validation of mixed valid and invalid parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {"shaves": 5, "invalid_column": 3})

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "invalid_column" in result.errors[0]

    def test_validate_parameters_table_size_parameters(self):
        """Test validation of table size parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {"rows": 20, "ranks": 15})

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_parameters_unknown_table(self):
        """Test validation with unknown table name."""
        validator = ParameterValidator()
        result = validator.validate_parameters("unknown_table", {"shaves": 5})

        assert result.is_valid is False
        assert len(result.errors) == 1
        assert "Unknown table" in result.errors[0]

    def test_get_available_columns_razors(self):
        """Test getting available columns for razors table."""
        validator = ParameterValidator()
        columns = validator.get_available_columns("razors")

        assert "shaves" in columns
        assert "unique_users" in columns
        assert "rows" in columns
        assert "ranks" in columns

    def test_get_available_columns_top_shavers(self):
        """Test getting available columns for top-shavers table."""
        validator = ParameterValidator()
        columns = validator.get_available_columns("top-shavers")

        assert "shaves" in columns
        assert "missed_days" in columns
        assert "rows" in columns
        assert "ranks" in columns

    def test_get_available_columns_unknown_table(self):
        """Test getting available columns for unknown table."""
        validator = ParameterValidator()
        columns = validator.get_available_columns("unknown_table")

        assert columns == []

    def test_is_sorting_column_valid(self):
        """Test checking if column is a sorting column."""
        validator = ParameterValidator()

        assert validator.is_sorting_column("razors", "shaves") is True
        assert validator.is_sorting_column("razors", "unique_users") is True
        assert validator.is_sorting_column("top-shavers", "missed_days") is True

    def test_is_sorting_column_invalid(self):
        """Test checking if column is not a sorting column."""
        validator = ParameterValidator()

        assert validator.is_sorting_column("razors", "invalid_column") is False
        assert validator.is_sorting_column("razors", "brand") is False

    def test_is_sorting_column_unknown_table(self):
        """Test checking sorting column for unknown table."""
        validator = ParameterValidator()

        assert validator.is_sorting_column("unknown_table", "shaves") is False

    def test_validate_parameters_empty_parameters(self):
        """Test validation of empty parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", {})

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_parameters_none_parameters(self):
        """Test validation of None parameters."""
        validator = ParameterValidator()
        result = validator.validate_parameters("razors", None)

        assert result.is_valid is True
        assert result.errors == []

    def test_validate_parameters_specialized_tables(self):
        """Test validation of specialized table parameters."""
        validator = ParameterValidator()

        # Test diversity tables
        result = validator.validate_parameters("brush-diversity", {"unique_brushes": 5})
        assert result.is_valid is True

        # Test cross-product tables
        result = validator.validate_parameters("highest-use-count-per-blade", {"uses": 10})
        assert result.is_valid is True

    def test_validate_parameters_parameter_value_validation(self):
        """Test validation of parameter values."""
        validator = ParameterValidator()

        # Test negative values (should be allowed for now)
        result = validator.validate_parameters("razors", {"shaves": -5})
        assert result.is_valid is True

        # Test zero values
        result = validator.validate_parameters("razors", {"shaves": 0})
        assert result.is_valid is True

        # Test very large values
        result = validator.validate_parameters("razors", {"shaves": 999999})
        assert result.is_valid is True
