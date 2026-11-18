#!/usr/bin/env python3
"""Tests for EnhancedTableGenerator."""

from unittest.mock import patch

import pytest

from sotd.report.enhanced_table_generator import EnhancedTableGenerator


class TestEnhancedTableGenerator:
    """Test cases for EnhancedTableGenerator."""

    def test_generate_table_without_parameters(self):
        """Test generating table without enhanced parameters."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
            {"rank": 3, "name": "Item 3", "shaves": 3},
        ]

        result = generator.generate_table("test_table", data, {})

        assert result == data

    def test_generate_table_with_data_field_limits(self):
        """Test generating table with data field limits."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10, "unique_users": 5},
            {"rank": 2, "name": "Item 2", "shaves": 5, "unique_users": 3},
            {"rank": 3, "name": "Item 3", "shaves": 3, "unique_users": 2},
        ]

        result = generator.generate_table("test_table", data, {"shaves": 5})

        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_generate_table_with_size_limits(self):
        """Test generating table with size limits."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
            {"rank": 3, "name": "Item 3", "shaves": 3},
            {"rank": 4, "name": "Item 4", "shaves": 2},
        ]

        result = generator.generate_table("test_table", data, {"rows": 2})

        assert len(result) == 2
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2

    def test_generate_table_with_both_limits(self):
        """Test generating table with both data field and size limits."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10, "unique_users": 5},
            {"rank": 2, "name": "Item 2", "shaves": 5, "unique_users": 3},
            {"rank": 3, "name": "Item 3", "shaves": 3, "unique_users": 2},
            {"rank": 4, "name": "Item 4", "shaves": 2, "unique_users": 1},
        ]

        result = generator.generate_table("test_table", data, {"shaves": 5, "rows": 2})

        # Should apply data field limit first, then size limit
        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_generate_table_parameter_validation(self):
        """Test that invalid parameters are caught during validation."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
        ]

        # Invalid column for this table
        with pytest.raises(ValueError, match="not a sorting column"):
            generator.generate_table("test_table", data, {"invalid_column": 5})

    def test_generate_table_unknown_table(self):
        """Test that unknown table names are caught."""
        generator = EnhancedTableGenerator()
        data = [{"rank": 1, "name": "Item 1", "shaves": 10}]

        with pytest.raises(ValueError, match="Unknown table"):
            generator.generate_table("unknown_table", data, {"shaves": 5})

    def test_generate_table_preserves_order(self):
        """Test that table generation preserves original order."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
            {"rank": 3, "name": "Item 3", "shaves": 3},
        ]

        result = generator.generate_table("test_table", data, {"shaves": 5, "rows": 2})

        # Order should be preserved
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2

    def test_generate_table_empty_data(self):
        """Test generating table with empty data."""
        generator = EnhancedTableGenerator()
        data = []

        result = generator.generate_table("test_table", data, {"shaves": 5})

        assert result == []

    def test_generate_table_none_data(self):
        """Test generating table with None data."""
        generator = EnhancedTableGenerator()

        with pytest.raises(ValueError, match="Data cannot be None"):
            # Type ignore for test - we're testing None handling
            generator.generate_table("test_table", None, {"shaves": 5})  # type: ignore

    def test_generate_table_complex_scenario(self):
        """Test complex scenario with multiple limits and ties."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10, "unique_users": 5},
            {"rank": 2, "name": "Item 2", "shaves": 5, "unique_users": 3},
            {"rank": 2, "name": "Item 3", "shaves": 5, "unique_users": 2},  # Tied
            {"rank": 4, "name": "Item 4", "shaves": 3, "unique_users": 1},
        ]

        result = generator.generate_table(
            "test_table", data, {"shaves": 5, "unique_users": 2, "rows": 3}
        )

        # Should apply data field limits first, then size limit
        # Data field limits: shaves >= 5, unique_users >= 2
        # This gives us items 1, 2, 3 (tied at rank 2)
        # Size limit: max 3 rows, but including the tie gives us 3 rows, which fits
        assert len(result) == 3
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 2

    def test_generate_table_parameter_parser_integration(self):
        """Test integration with parameter parser."""
        generator = EnhancedTableGenerator()

        # Mock the parameter parser
        with patch.object(generator, "parameter_parser") as mock_parser:
            mock_parser.parse_placeholder.return_value = ("test_table", {"shaves": 5})

            data = [
                {"rank": 1, "name": "Item 1", "shaves": 10},
                {"rank": 2, "name": "Item 2", "shaves": 5},
                {"rank": 3, "name": "Item 3", "shaves": 3},
            ]

            result = generator.generate_table_from_placeholder(
                "{{tables.test_table|shaves:5}}", data
            )

            mock_parser.parse_placeholder.assert_called_once_with("{{tables.test_table|shaves:5}}")
            assert len(result) == 2

    def test_generate_table_from_placeholder_basic(self):
        """Test generating table from basic placeholder."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
        ]

        result = generator.generate_table_from_placeholder("{{tables.test_table}}", data)

        assert result == data

    def test_generate_table_from_placeholder_with_parameters(self):
        """Test generating table from placeholder with parameters."""
        generator = EnhancedTableGenerator()
        data = [
            {"rank": 1, "name": "Item 1", "shaves": 10},
            {"rank": 2, "name": "Item 2", "shaves": 5},
            {"rank": 3, "name": "Item 3", "shaves": 3},
        ]

        result = generator.generate_table_from_placeholder(
            "{{tables.test_table|shaves:5|rows:2}}", data
        )

        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_generate_table_from_placeholder_invalid_format(self):
        """Test generating table from invalid placeholder format."""
        generator = EnhancedTableGenerator()
        data = [{"rank": 1, "name": "Item 1", "shaves": 10}]

        with pytest.raises(ValueError, match="Invalid placeholder format"):
            generator.generate_table_from_placeholder("invalid_format", data)
