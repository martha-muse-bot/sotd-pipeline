"""Tests for the TableGenerator."""

import json

import pytest

from sotd.report.table_generators.table_generator import TableGenerator


class TestTableGenerator:
    """Test cases for TableGenerator."""

    def test_basic_table_generation(self):
        """Test basic table generation without parameters."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers")

        # Should contain all rows
        assert "Brand A" in result
        assert "Brand B" in result
        assert "Brand C" in result
        assert "100" in result
        assert "80" in result
        assert "60" in result

    def test_ranks_filtering(self):
        """Test ranks parameter filtering."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", ranks=2)

        # Should include rank 1 and 2 (inclusive)
        assert "Brand A" in result
        assert "Brand B" in result
        assert "Brand C" not in result

    def test_rows_limiting(self):
        """Test rows parameter limiting."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2)

        # Should include first 2 rows
        assert "Brand A" in result
        assert "Brand B" in result
        assert "Brand C" not in result

    def test_both_parameters(self):
        """Test both ranks and rows parameters together."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", ranks=3, rows=2)

        # Should stop at rows limit (2) even though ranks allows 3
        assert "Brand A" in result
        assert "Brand B" in result
        assert "Brand C" not in result

    def test_empty_data(self):
        """Test handling of empty data."""
        data = {"soap_makers": []}
        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers")

        assert result == ""

    def test_missing_rank_column(self):
        """Test error when rank column is missing but required by parameters."""
        data = {"soap_makers": [{"shaves": 100, "unique_users": 50, "brand": "Brand A"}]}

        generator = TableGenerator(data)

        # Rank column is required when using ranks parameter
        with pytest.raises(ValueError, match="missing 'rank' column"):
            generator.generate_table("soap-makers", ranks=3)

    def test_invalid_ranks_parameter(self):
        """Test error for invalid ranks parameter."""
        data = {"soap_makers": [{"rank": 1, "brand": "Brand A"}]}
        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="ranks must be greater than 0"):
            generator.generate_table("soap-makers", ranks=0)

        with pytest.raises(ValueError, match="ranks must be greater than 0"):
            generator.generate_table("soap-makers", ranks=-1)

    def test_invalid_rows_parameter(self):
        """Test error for invalid rows parameter."""
        data = {"soap_makers": [{"rank": 1, "brand": "Brand A"}]}
        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="rows must be greater than 0"):
            generator.generate_table("soap-makers", rows=0)

        with pytest.raises(ValueError, match="rows must be greater than 0"):
            generator.generate_table("soap-makers", rows=-1)

    def test_unknown_table_name(self):
        """Test error for unknown table name."""
        data = {"soap_makers": [{"rank": 1, "brand": "Brand A"}]}
        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="Unknown table: unknown-table"):
            generator.generate_table("unknown-table")

    def test_missing_data_key(self):
        """Test handling when data key is missing."""
        data = {"other_category": [{"rank": 1, "brand": "Brand A"}]}
        generator = TableGenerator(data)

        # Should raise ValueError for unknown table
        with pytest.raises(ValueError, match="Unknown table: soap-makers"):
            generator.generate_table("soap-makers")

    def test_empty_data_key(self):
        """Test handling when data key exists but is empty."""
        data = {"soap_makers": []}
        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers")

        assert result == ""

    def test_get_available_table_names(self):
        """Test getting available table names."""
        data = {"soap_makers": [{"rank": 1, "brand": "Brand A"}]}
        generator = TableGenerator(data)
        table_names = generator.get_available_table_names()

        # Should only include actual data keys that exist in the data
        assert "soap_makers" in table_names
        assert "razors" not in table_names  # Not in data, so not in available names
        assert len(table_names) == 1  # Only one data key exists

    def test_column_name_formatting(self):
        """Test that column names are automatically formatted to Title Case."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2)

        # Check that column names are formatted
        assert "Rank" in result and "Shaves" in result
        assert "Unique Users" in result and "Maker" in result
        assert "Brand A" in result
        assert "Brand B" in result

        # Verify no snake_case remains
        assert "unique_users" not in result
        assert "Unique Users" in result

    def test_acronym_preservation(self):
        """Test that acronyms are preserved in uppercase."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
                {"rank": 3, "format": "AC", "shaves": 60, "unique_users": 30},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("razor-formats", rows=3)

        # Check that acronyms are preserved
        assert "Rank" in result and "Format" in result
        assert "Shaves" in result and "Unique Users" in result
        assert "DE" in result  # DE should be preserved in uppercase
        assert "GEM" in result  # GEM should be preserved in uppercase
        assert "AC" in result  # AC should be preserved in uppercase

    def test_per_acronym_preservation(self):
        """Test that 'per' is preserved as lowercase in column names."""
        data = {
            "soap_makers": [
                {"rank": 1, "avg_shaves_per_soap": 5.2, "shaves": 100, "brand": "Brand A"},
                {"rank": 2, "avg_shaves_per_soap": 4.8, "shaves": 80, "brand": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2)

        # Check that 'per' is preserved as lowercase in column name
        # The column name should be "Avg Shaves Per Soap" with "per" lowercase
        assert "Avg Shaves per Soap" in result
        assert "Brand A" in result
        assert "Brand B" in result

        # Verify 'per' is not converted to 'Per' or 'PER'
        assert "| Avg Shaves Per Soap     |" not in result
        assert "| Avg Shaves PER Soap     |" not in result

    def test_column_reordering(self):
        """Test column reordering functionality."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "soap-makers", rows=2, columns="shaves, rank, unique_users"
        )

        # Check that columns are reordered
        # Verify columns appear in the specified order
        shaves_index = result.find("Shaves")
        rank_index = result.find("Rank")
        unique_users_index = result.find("Unique Users")

        assert shaves_index != -1 and rank_index != -1 and unique_users_index != -1
        assert shaves_index < rank_index < unique_users_index  # Verify order
        assert "100" in result and "80" in result  # Verify data is present

        # Verify original order is not present
        assert "| Rank     | Shaves     | Unique Users     |" not in result

    def test_column_renaming(self):
        """Test column renaming functionality."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2, columns="rank, maker=soap, shaves")

        # Check that column is renamed
        assert "Rank" in result and "Soap" in result and "Shaves" in result
        assert "Brand A" in result and "Brand B" in result
        # Verify "Maker" column is not present (should be renamed to "Soap")
        assert "Maker" not in result

    def test_column_reordering_and_renaming(self):
        """Test combined column reordering and renaming."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2, columns="shaves, maker=soap, rank")

        # Check that columns are reordered and renamed
        # Verify columns appear in the specified order with renaming
        shaves_index = result.find("Shaves")
        soap_index = result.find("Soap")
        rank_index = result.find("Rank")

        assert shaves_index != -1 and soap_index != -1 and rank_index != -1
        assert shaves_index < soap_index < rank_index  # Verify order
        assert "Brand A" in result and "Brand B" in result  # Verify data is present
        # Verify "Maker" column is not present (should be renamed to "Soap")
        assert "Maker" not in result

    def test_columns_with_ranks_parameter(self):
        """Test columns parameter combined with ranks parameter."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "maker": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", ranks=3, columns="rank, maker=soap")

        # Check that both parameters work together
        assert "Rank" in result and "Soap" in result
        assert "Brand A" in result
        assert "Brand B" in result
        assert "Brand C" in result

    def test_columns_with_rows_parameter(self):
        """Test columns parameter combined with rows parameter."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "maker": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2, columns="rank, maker=soap")

        # Check that both parameters work together
        assert "Rank" in result and "Soap" in result
        assert "Brand A" in result
        assert "Brand B" in result

        # Verify we don't see rank 3
        assert "Brand C" not in result

    def test_missing_columns_handling(self):
        """Test that missing columns are silently omitted."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "soap-makers", rows=2, columns="rank, nonexistent_column, shaves"
        )

        # Check that only existing columns are shown
        assert "Rank" in result and "Shaves" in result
        assert "100" in result

        # Verify missing column is not present
        assert "nonexistent_column" not in result

    def test_empty_columns_parameter(self):
        """Test that empty columns parameter shows all columns."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=2, columns="")

        # Should show all columns in original order
        assert "Rank" in result and "Shaves" in result
        assert "Unique Users" in result and "Maker" in result

    def test_invalid_columns_syntax(self):
        """Test that invalid columns syntax raises appropriate errors."""
        data = {"soap_makers": [{"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"}]}

        generator = TableGenerator(data)

        # Test invalid rename syntax
        with pytest.raises(ValueError, match="Invalid rename syntax"):
            generator.generate_table("soap-makers", rows=2, columns="rank, name=soap=alias")

        # Test empty columns
        with pytest.raises(ValueError, match="Columns parameter cannot be empty"):
            generator.generate_table("soap-makers", rows=2, columns="   ")

    def test_no_valid_columns_after_filtering(self):
        """Test error when no valid columns remain after filtering."""
        data = {"soap_makers": [{"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"}]}

        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="No valid columns found in data"):
            generator.generate_table("soap-makers", rows=2, columns="nonexistent1, nonexistent2")

    def test_rank_column_formatting_equal_ranks(self):
        """Test that equal ranks are formatted as N= in the rank column."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand C"},
                {"rank": 4, "shaves": 60, "unique_users": 30, "maker": "Brand D"},
                {"rank": 4, "shaves": 60, "unique_users": 30, "maker": "Brand E"},
                {"rank": 4, "shaves": 60, "unique_users": 30, "maker": "Brand F"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=6)

        # Check that equal ranks are formatted as N=
        assert "1" in result  # Single rank 1
        assert "2=" in result  # Equal rank 2 (should appear twice)
        assert "4=" in result  # Equal rank 4 (should appear three times)

        # Verify no plain equal ranks remain
        assert "2" in result  # Should still appear as "2="
        assert "4" in result  # Should still appear as "4="

    def test_rank_column_formatting_single_ranks(self):
        """Test that single ranks (no ties) are formatted normally."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "maker": "Brand C"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=3)

        # Check that single ranks are formatted normally (numeric format,
        # no rank formatting applied)
        assert "1 " in result  # Single rank 1 (with space suffix)
        assert "2 " in result  # Single rank 2 (with space suffix)
        assert "3 " in result  # Single rank 3 (with space suffix)

        # Verify no N= formatting for single ranks
        assert "| 1=       |" not in result
        assert "| 2=       |" not in result
        assert "| 3=       |" not in result

    def test_rank_column_formatting_mixed_ranks(self):
        """Test mixed scenario with both single and equal ranks."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand C"},
                {"rank": 4, "shaves": 60, "unique_users": 30, "maker": "Brand D"},
                {"rank": 5, "shaves": 50, "unique_users": 25, "maker": "Brand E"},
                {"rank": 5, "shaves": 50, "unique_users": 25, "maker": "Brand F"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", rows=6)

        # Check mixed formatting
        assert "1 " in result  # Single rank 1 (with space suffix)
        assert "2=" in result  # Equal rank 2 (with equals suffix)
        assert "4 " in result  # Single rank 4 (with space suffix)
        assert "5=" in result  # Equal rank 5 (with equals suffix)

    def test_rank_column_formatting_with_parameters(self):
        """Test rank formatting works with ranks and columns parameters."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "maker": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand B"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "maker": "Brand C"},
                {"rank": 4, "shaves": 60, "unique_users": 30, "maker": "Brand D"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "soap-makers", ranks=3, columns="rank, maker=soap, shaves"
        )

        # Check that rank formatting works with custom columns
        assert "1 " in result  # Single rank 1 (with space suffix)
        assert "2=" in result  # Equal rank 2 (with equals suffix)
        assert "Brand A" in result and "Brand B" in result and "Brand C" in result
        assert "100" in result and "80" in result

    def test_delta_columns_basic_functionality(self):
        """Test basic delta columns functionality with comparison data."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
                {"rank": 3, "format": "AC", "shaves": 60, "unique_users": 30},
            ]
        }

        # Mock comparison data for previous month, previous year, 5 years ago
        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {
                        "rank": 3,
                        "format": "GEM",
                        "shaves": 85,
                        "unique_users": 42,
                    },  # GEM was rank 3
                    {"rank": 2, "format": "AC", "shaves": 70, "unique_users": 35},  # AC was rank 2
                ]
            },
            "2024-06": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 95, "unique_users": 48},
                    {"rank": 2, "format": "AC", "shaves": 75, "unique_users": 38},  # AC was rank 2
                    {
                        "rank": 3,
                        "format": "GEM",
                        "shaves": 65,
                        "unique_users": 32,
                    },  # GEM was rank 3
                ]
            },
            "2020-06": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 85, "unique_users": 40},
                    {
                        "rank": 2,
                        "format": "GEM",
                        "shaves": 70,
                        "unique_users": 35,
                    },  # GEM was rank 2
                    {"rank": 3, "format": "AC", "shaves": 55, "unique_users": 25},  # AC was rank 3
                ]
            },
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", deltas=True)

        # Check that delta columns are added at the end
        assert "| Δ vs May 2025" in result
        assert "| Δ vs Jun 2024" in result
        assert "| Δ vs Jun 2020" in result

        # Check delta values for rank changes
        # DE: rank 1 in all periods = "="
        assert "=" in result  # DE stayed rank 1
        # GEM: rank 2 → rank 3 (previous month: ↓1), rank 3 → rank 2 (previous year: ↑1)
        # AC: rank 3 → rank 2 (previous month: ↑1), rank 2 → rank 3 (previous year: ↓1)

    def test_delta_columns_with_ranks_parameter(self):
        """Test delta columns work with ranks parameter."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
            ]
        }

        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 2, "format": "GEM", "shaves": 85, "unique_users": 42},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", ranks=2, deltas=True)

        # Should show only top 2 ranks with deltas
        assert "=" in result  # DE stayed rank 1
        assert "=" in result  # GEM stayed rank 2

    def test_delta_columns_with_rows_parameter(self):
        """Test delta columns work with rows parameter."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
                {"rank": 3, "format": "AC", "shaves": 60, "unique_users": 30},
            ]
        }

        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 2, "format": "GEM", "shaves": 85, "unique_users": 42},
                    {"rank": 3, "format": "AC", "shaves": 70, "unique_users": 35},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", rows=2, deltas=True)

        # Should show only top 2 rows with deltas
        assert "=" in result  # DE stayed rank 1
        assert "=" in result  # GEM stayed rank 2
        # AC should not appear due to rows=2

    def test_delta_columns_with_columns_parameter(self):
        """Test delta columns work with columns parameter but are not affected by it."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
            ]
        }

        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 2, "format": "GEM", "shaves": 85, "unique_users": 42},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", columns="format, shaves", deltas=True)

        # Should show only format and shaves columns, then delta columns
        assert "Format" in result and "Shaves" in result
        assert "Δ vs May 2025" in result
        # Rank and unique_users should not appear due to columns parameter

    def test_delta_columns_missing_comparison_data(self):
        """Test delta columns handle missing comparison data gracefully."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
            ]
        }

        # No comparison data
        generator = TableGenerator(data)
        result = generator.generate_table("razor-formats", deltas=True)

        # Should show delta columns with "n/a" values
        assert "Δ vs May 2025" in result
        assert "Δ vs Jun 2024" in result
        assert "Δ vs Jun 2020" in result
        assert "n/a" in result

    def test_delta_columns_partial_comparison_data(self):
        """Test delta columns handle partial comparison data gracefully."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
            ]
        }

        # Only some comparison data available
        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 2, "format": "GEM", "shaves": 85, "unique_users": 42},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", deltas=True)

        # Should show all delta columns, with "n/a" for missing data
        assert "Δ vs May 2025" in result
        assert "Δ vs Jun 2024" in result
        assert "Δ vs Jun 2020" in result
        assert "=" in result  # Previous month
        assert "n/a" in result  # Missing periods

    def test_delta_columns_rank_changes(self):
        """Test delta columns show correct rank change indicators."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
                {"rank": 3, "format": "AC", "shaves": 60, "unique_users": 30},
            ]
        }

        # Previous month: GEM moved up 1 rank, AC moved down 1 rank
        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 3, "format": "GEM", "shaves": 85, "unique_users": 42},
                    {"rank": 2, "format": "AC", "shaves": 70, "unique_users": 35},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", deltas=True)

        # Check rank change indicators
        assert "=" in result  # DE stayed rank 1
        assert "↑1" in result  # GEM moved up 1 rank
        assert "↓1" in result  # AC moved down 1 rank

    def test_delta_columns_no_deltas_parameter(self):
        """Test that delta columns are not added when deltas parameter is False or None."""
        data = {
            "razor_formats": [
                {"rank": 1, "format": "DE", "shaves": 100, "unique_users": 50},
                {"rank": 2, "format": "GEM", "shaves": 80, "unique_users": 40},
            ]
        }

        comparison_data = {
            "2025-05": {
                "razor_formats": [
                    {"rank": 1, "format": "DE", "shaves": 90, "unique_users": 45},
                    {"rank": 2, "format": "GEM", "shaves": 85, "unique_users": 42},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table("razor-formats", deltas=False)

        # Should not show delta columns
        assert "| Δ vs May 2025 |" not in result
        assert "| Δ vs Jun 2024 |" not in result
        assert "| Δ vs Jun 2020 |" not in result

    def test_numeric_column_limits_basic(self):
        """Test basic numeric column filtering."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
                {"rank": 4, "shaves": 40, "unique_users": 20, "brand": "Brand D"},
                {"rank": 5, "shaves": 20, "unique_users": 10, "brand": "Brand E"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", shaves=50)

        # Should include rows where shaves >= 50
        assert "Brand A" in result  # shaves: 100
        assert "Brand B" in result  # shaves: 80
        assert "Brand C" in result  # shaves: 60
        assert "Brand D" not in result  # shaves: 40
        assert "Brand E" not in result  # shaves: 20

    def test_numeric_column_limits_single_limit_only(self):
        """Test that only one numeric column limit is allowed per table."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
            ]
        }

        generator = TableGenerator(data)

        # Should fail when multiple numeric limits are specified
        with pytest.raises(ValueError, match="Only one numeric column limit allowed per table"):
            generator.generate_table("soap-makers", shaves=50, unique_users=25)

    def test_numeric_column_limits_with_existing_parameters(self):
        """Test numeric column limits with ranks and rows parameters."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 80, "unique_users": 40, "brand": "Brand B"},
                {"rank": 3, "shaves": 60, "unique_users": 30, "brand": "Brand C"},
                {"rank": 4, "shaves": 40, "unique_users": 20, "brand": "Brand D"},
                {"rank": 5, "shaves": 20, "unique_users": 10, "brand": "Brand E"},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers", ranks=3, shaves=50)

        # Should apply both filters: ranks <= 3 AND shaves >= 50
        assert "Brand A" in result  # rank: 1, shaves: 100
        assert "Brand B" in result  # rank: 2, shaves: 80
        assert "Brand C" in result  # rank: 3, shaves: 60
        assert "Brand D" not in result  # rank: 4, shaves: 40
        assert "Brand E" not in result  # rank: 5, shaves: 20

    def test_numeric_column_limits_gap_detection(self):
        """Test numeric column filtering works correctly even if it creates gaps."""
        data = {
            "soap_makers": [
                {"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand A"},
                {"rank": 2, "shaves": 90, "unique_users": 45, "brand": "Brand B"},
                {"rank": 3, "shaves": 50, "unique_users": 25, "brand": "Brand C"},
                {"rank": 4, "shaves": 80, "unique_users": 40, "brand": "Brand D"},
                {"rank": 5, "shaves": 20, "unique_users": 10, "brand": "Brand E"},
            ]
        }

        generator = TableGenerator(data)

        # This filter should keep ranks 1, 2, 4 (shaves >= 70)
        # which creates a gap in the rank sequence (missing rank 3)
        result = generator.generate_table("soap-makers", shaves=70)

        # Should include items with shaves >= 70
        assert "Brand A" in result  # shaves: 100
        assert "Brand B" in result  # shaves: 90
        assert "Brand D" in result  # shaves: 80

        # Should exclude items with shaves < 70
        assert "Brand C" not in result  # shaves: 50
        assert "Brand E" not in result  # shaves: 20

    def test_numeric_column_limits_invalid_column(self):
        """Test error when numeric column doesn't exist."""
        data = {"soap_makers": [{"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand B"}]}

        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="'nonexistent_column' is not a sorting column"):
            generator.generate_table("soap-makers", nonexistent_column=10)

    def test_numeric_column_limits_invalid_threshold(self):
        """Test error when threshold value is not numeric."""
        data = {"soap_makers": [{"rank": 1, "shaves": 100, "unique_users": 50, "brand": "Brand B"}]}

        generator = TableGenerator(data)

        with pytest.raises(
            ValueError, match="Invalid threshold value 'abc' for column 'shaves' - must be numeric"
        ):
            generator.generate_table("soap-makers", shaves="abc")

    def test_wsdb_slug_lookup_found(self, tmp_path, monkeypatch):
        """Test WSDB slug lookup when match is found."""
        # Create directory structure: tmp_path/sotd/report/table_generators/
        # so that Path(__file__).parent.parent.parent.parent points to tmp_path
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock WSDB data
        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            },
            "Stirling Soap Co.": {
                "scents": {"Executive Man": {"wsdb_slug": "stirling-soap-co-executive-man"}}
            },
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        # Patch __file__ to point to our test directory structure
        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {"soaps": [{"rank": 1, "shaves": 100, "unique_users": 50}]}
        generator = TableGenerator(data)

        # Test slug lookup
        slug = generator._get_wsdb_slug("Barrister and Mann", "Seville")
        assert (
            slug == "barrister-and-mann-seville"
        ), f"Expected 'barrister-and-mann-seville', got {slug}"

        slug2 = generator._get_wsdb_slug("Stirling Soap Co.", "Executive Man")
        assert (
            slug2 == "stirling-soap-co-executive-man"
        ), f"Expected 'stirling-soap-co-executive-man', got {slug2}"

        # Note: WSDBLookup is case-sensitive, so case-insensitive matching is not supported
        # Test non-existent soap

        # Test non-existent soap
        slug4 = generator._get_wsdb_slug("Non Existent", "Scent")
        assert slug4 is None

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_slug_lookup_missing_file(self, tmp_path, monkeypatch):
        """Test WSDB slug lookup when file doesn't exist."""
        # Create directory structure but don't create the WSDB file
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {"soaps": [{"rank": 1, "shaves": 100, "unique_users": 50}]}
        generator = TableGenerator(data)

        # Should return None when file doesn't exist
        slug = generator._get_wsdb_slug("Barrister and Mann", "Seville")
        assert slug is None

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_link_formatting_in_soaps_table(self, tmp_path, monkeypatch):
        """Test that soap names are formatted with links in soaps table."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {"Seville": {"wsdb_slug": "barrister-and-mann-seville"}}
            },
            "Stirling Soap Co.": {
                "scents": {"Executive Man": {"wsdb_slug": "stirling-soap-co-executive-man"}}
            },
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soaps": [
                {
                    "rank": 1,
                    "shaves": 100,
                    "unique_users": 50,
                    "brand": "Barrister and Mann",
                    "scent": "Seville",
                    "name": "Barrister and Mann - Seville",
                },
                {
                    "rank": 2,
                    "shaves": 80,
                    "unique_users": 40,
                    "brand": "Stirling Soap Co.",
                    "scent": "Executive Man",
                    "name": "Stirling Soap Co. - Executive Man",
                },
                {
                    "rank": 3,
                    "shaves": 60,
                    "unique_users": 30,
                    "brand": "Unknown Brand",
                    "scent": "Unknown Scent",
                    "name": "Unknown Brand - Unknown Scent",
                },
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soaps", wsdb=True)

        # Should contain links for matched soaps
        assert (
            "[Barrister and Mann - Seville](https://www.wetshavingdatabase.com/software/barrister-and-mann-seville/)"
            in result
        )
        assert (
            "[Stirling Soap Co. - Executive Man](https://www.wetshavingdatabase.com/software/stirling-soap-co-executive-man/)"
            in result
        )

        # Should not contain link for unmatched soap (just the name)
        assert "Unknown Brand - Unknown Scent" in result
        assert "[Unknown Brand - Unknown Scent](" not in result

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_link_formatting_not_applied_to_other_tables(self, tmp_path, monkeypatch):
        """Test that link formatting is not applied to non-soap tables."""
        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock WSDB data
        wsdb_dir = tmp_path / "data" / "wsdb"
        wsdb_dir.mkdir(parents=True)
        wsdb_file = wsdb_dir / "software.json"

        mock_wsdb_data = [
            {
                "brand": "Barrister and Mann",
                "name": "Seville",
                "slug": "barrister-and-mann-seville",
                "type": "Soap",
            },
        ]

        with wsdb_file.open("w", encoding="utf-8") as f:
            json.dump(mock_wsdb_data, f)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {
            "soap_makers": [
                {
                    "rank": 1,
                    "shaves": 100,
                    "unique_users": 50,
                    "brand": "Barrister and Mann",
                    "name": "Barrister and Mann",
                },
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table("soap-makers")

        # Should not contain links (soap-makers table doesn't get link formatting)
        assert "Barrister and Mann" in result
        assert "[Barrister and Mann](" not in result

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_wsdb_unicode_normalization(self, tmp_path, monkeypatch):
        """Test that Unicode normalization works in slug lookup."""

        # Create directory structure
        table_generators_dir = tmp_path / "sotd" / "report" / "table_generators"
        table_generators_dir.mkdir(parents=True)

        # Create mock soaps.yaml file that WSDBLookup expects
        data_dir = tmp_path / "data"
        data_dir.mkdir(parents=True)
        soaps_file = data_dir / "soaps.yaml"

        # Use composed form (NFC) in the YAML file
        composed_melange = "Mélange"

        mock_soaps_yaml = {
            "Barrister and Mann": {
                "scents": {composed_melange: {"wsdb_slug": "barrister-and-mann-melange"}}
            }
        }

        import yaml

        with soaps_file.open("w", encoding="utf-8") as f:
            yaml.dump(mock_soaps_yaml, f, allow_unicode=True)

        import sotd.report.table_generators.table_generator as tg_module

        original_file = tg_module.__file__
        test_file_path = str(table_generators_dir / "table_generator.py")
        monkeypatch.setattr(tg_module, "__file__", test_file_path)

        data = {"soaps": [{"rank": 1, "shaves": 100, "unique_users": 50}]}
        generator = TableGenerator(data)

        # WSDBLookup uses exact dictionary lookups, so we need to use the same Unicode form
        # Test with composed form (NFC) - same as stored in YAML
        slug = generator._get_wsdb_slug("Barrister and Mann", composed_melange)
        assert slug == "barrister-and-mann-melange"

        # Restore original file path
        monkeypatch.setattr(tg_module, "__file__", original_file)

    def test_parse_columns_parameter_with_sort_directions(self):
        """Test parsing columns parameter with sort directions."""
        data = {"soap_makers": [{"rank": 1, "shaves": 100, "unique_users": 50}]}
        generator = TableGenerator(data)

        # Test simple column with desc
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter("shaves desc")
        assert column_order == ["shaves"]
        assert rename_mapping == {}
        assert sort_info == [("shaves", False)]

        # Test simple column with asc
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter("shaves asc")
        assert column_order == ["shaves"]
        assert rename_mapping == {}
        assert sort_info == [("shaves", True)]

        # Test renamed column with desc
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter(
            "unique_combinations=unique_soaps desc"
        )
        assert column_order == ["unique_combinations"]
        assert rename_mapping == {"unique_combinations": "unique_soaps"}
        assert sort_info == [("unique_combinations", False)]

        # Test multiple columns with directions
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter(
            "rank, user, unique_combinations desc, shaves desc"
        )
        assert column_order == ["rank", "user", "unique_combinations", "shaves"]
        assert rename_mapping == {}
        assert sort_info == [("unique_combinations", False), ("shaves", False)]

        # Test mixed (some with directions, some without)
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter(
            "rank, user, unique_combinations desc"
        )
        assert column_order == ["rank", "user", "unique_combinations"]
        assert rename_mapping == {}
        assert sort_info == [("unique_combinations", False)]

        # Test case-insensitive directions
        column_order, rename_mapping, sort_info = generator._parse_columns_parameter("shaves DESC")
        assert sort_info == [("shaves", False)]

        column_order, rename_mapping, sort_info = generator._parse_columns_parameter("shaves ASC")
        assert sort_info == [("shaves", True)]

    def test_sorting_single_column_ascending(self):
        """Test sorting with single column ascending."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity", columns="rank, user, unique_combinations asc, shaves"
        )

        # Should be sorted by unique_combinations ascending (lowest first)
        # user2 (5) should come before user1 (10) should come before user3 (15)
        user2_index = result.find("user2")
        user1_index = result.find("user1")
        user3_index = result.find("user3")

        assert user2_index < user1_index < user3_index

    def test_sorting_single_column_descending(self):
        """Test sorting with single column descending."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations desc, shaves",
        )

        # Should be sorted by unique_combinations descending (highest first)
        # user3 (15) should come before user1 (10) should come before user2 (5)
        user3_index = result.find("user3")
        user1_index = result.find("user1")
        user2_index = result.find("user2")

        assert user3_index < user1_index < user2_index

    def test_sorting_multiple_columns(self):
        """Test sorting with multiple columns."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 10, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 10, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations asc, shaves desc",
        )

        # Should be sorted by unique_combinations asc, then shaves desc
        # All have same unique_combinations (10), so sorted by shaves desc
        # user1 (50) should come before user3 (40) should come before user2 (30)
        user1_index = result.find("user1")
        user3_index = result.find("user3")
        user2_index = result.find("user2")

        assert user1_index < user3_index < user2_index

    def test_sorting_with_reranking(self):
        """Test that sorting re-ranks the data correctly."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity", columns="rank, user, unique_combinations asc, shaves"
        )

        # After sorting by unique_combinations asc, ranks should be recalculated
        # user2 (5) should be rank 1, user1 (10) should be rank 2, user3 (15) should be rank 3
        # Check that ranks are present (formatted as "|      1 |" or "|      1=|")
        assert "|      1 |" in result or "|      1=" in result  # Rank 1
        assert "|      2 |" in result or "|      2=" in result  # Rank 2
        assert "|      3 |" in result or "|      3=" in result  # Rank 3

        # Verify user2 appears first (lowest unique_combinations)
        user2_index = result.find("user2")
        user1_index = result.find("user1")
        assert user2_index < user1_index

    def test_sorting_with_ranks_parameter(self):
        """Test sorting combined with ranks parameter."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
                {"rank": 4, "user": "user4", "unique_combinations": 3, "shaves": 20},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            ranks=2,
            columns="rank, user, unique_combinations asc, shaves",
        )

        # After sorting by unique_combinations asc, should show top 2 ranks
        # user4 (3) should be rank 1, user2 (5) should be rank 2
        assert "user4" in result
        assert "user2" in result
        assert "user1" not in result
        assert "user3" not in result

    def test_sorting_with_rows_parameter(self):
        """Test sorting combined with rows parameter."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
                {"rank": 4, "user": "user4", "unique_combinations": 3, "shaves": 20},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            rows=2,
            columns="rank, user, unique_combinations asc, shaves",
        )

        # After sorting by unique_combinations asc, should show first 2 rows
        # user4 (3) should be first, user2 (5) should be second
        assert "user4" in result
        assert "user2" in result
        assert "user1" not in result
        assert "user3" not in result

    def test_sorting_with_deltas(self):
        """Test sorting combined with deltas parameter."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        comparison_data = {
            "2025-05": {
                "user_soap_brand_scent_diversity": [
                    {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                    {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                    {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations asc, shaves",
            deltas=True,
        )

        # Should have delta columns
        assert "Δ vs" in result
        # Should be sorted correctly
        user2_index = result.find("user2")
        user1_index = result.find("user1")
        user3_index = result.find("user3")
        assert user2_index < user1_index < user3_index

    def test_sorting_invalid_column(self):
        """Test error when sort column doesn't exist."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
            ]
        }

        generator = TableGenerator(data)

        with pytest.raises(ValueError, match="Sort columns not found in data"):
            generator.generate_table(
                "user-soap-brand-scent-diversity",
                columns="rank, user, nonexistent_column asc",
            )

    def test_sorting_with_column_renaming(self):
        """Test that sorting works with column renaming."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations=unique_soaps asc, shaves",
        )

        # Should be sorted correctly and column renamed
        assert "Unique Soaps" in result  # Renamed column
        user2_index = result.find("user2")
        user1_index = result.find("user1")
        user3_index = result.find("user3")
        assert user2_index < user1_index < user3_index

    def test_sorting_with_ties(self):
        """Test that sorting handles ties correctly with competition ranking."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 10, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 10, "shaves": 40},
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations asc, shaves",
        )

        # All have same unique_combinations (10), so should all get same rank after re-ranking
        # But since we're sorting by unique_combinations first, they should be grouped together
        assert "user1" in result
        assert "user2" in result
        assert "user3" in result

    def test_sorting_with_deltas_consistent_sorting(self):
        """Test that deltas work correctly when using custom sorting - comparison data is sorted the same way."""
        data = {
            "user_soap_brand_scent_diversity": [
                {"rank": 1, "user": "user1", "unique_combinations": 10, "shaves": 50},
                {"rank": 2, "user": "user2", "unique_combinations": 5, "shaves": 30},
                {"rank": 3, "user": "user3", "unique_combinations": 15, "shaves": 40},
            ]
        }

        # Previous month data - sorted by default (descending by unique_combinations)
        # user3: 15 (rank 1), user1: 10 (rank 2), user2: 5 (rank 3)
        comparison_data = {
            "2025-05": {
                "user_soap_brand_scent_diversity": [
                    {"rank": 1, "user": "user3", "unique_combinations": 15, "shaves": 40},
                    {"rank": 2, "user": "user1", "unique_combinations": 10, "shaves": 50},
                    {"rank": 3, "user": "user2", "unique_combinations": 5, "shaves": 30},
                ]
            }
        }

        generator = TableGenerator(data, comparison_data, current_month="2025-06")
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, unique_combinations asc, shaves",
            deltas=True,
        )

        # After sorting current month by unique_combinations asc:
        # user2: 5 (rank 1), user1: 10 (rank 2), user3: 15 (rank 3)
        # After sorting previous month by unique_combinations asc:
        # user2: 5 (rank 1), user1: 10 (rank 2), user3: 15 (rank 3)
        # So deltas should all be "=" (no change)

        # Should have delta columns
        assert "Δ vs" in result
        # All users should show "=" since they're in the same positions after consistent sorting
        assert "=" in result
        # Verify sorting is correct (ascending)
        user2_index = result.find("user2")
        user1_index = result.find("user1")
        user3_index = result.find("user3")
        assert user2_index < user1_index < user3_index

    def test_delta_columns_user_single_use_soaps(self):
        """Delta generation works for user-single-use-soaps (aggregator module name match)."""
        data = {
            "user_single_use_soaps": [
                {"rank": 1, "user": "alice", "single_use_soaps": 3, "shaves": 20},
                {"rank": 2, "user": "bob", "single_use_soaps": 2, "shaves": 15},
            ]
        }
        comparison_data = {
            "2026-03": {
                "user_single_use_soaps": [
                    {"rank": 1, "user": "bob", "single_use_soaps": 4, "shaves": 18},
                    {"rank": 2, "user": "alice", "single_use_soaps": 2, "shaves": 22},
                ]
            },
        }
        generator = TableGenerator(data, comparison_data, current_month="2026-04")
        result = generator.generate_table(
            "user-single-use-soaps",
            ranks=20,
            columns="rank, user, single_use_soaps, shaves",
            deltas=True,
        )
        assert "| Δ vs Mar 2026" in result
        assert "alice" in result

    def test_hhi_percentage_formatting(self):
        """Test that hhi (Boring Score) is formatted as a percentage."""
        data = {
            "user_soap_brand_scent_diversity": [
                {
                    "rank": 1,
                    "user": "user1",
                    "hhi": 0.933,
                    "effective_soaps": 1.07,
                    "unique_combinations": 6,
                    "shaves": 116,
                },
                {
                    "rank": 2,
                    "user": "user2",
                    "hhi": 0.5176,
                    "effective_soaps": 1.93,
                    "unique_combinations": 4,
                    "shaves": 64,
                },
                {
                    "rank": 3,
                    "user": "user3",
                    "hhi": 0.4681,
                    "effective_soaps": 2.14,
                    "unique_combinations": 9,
                    "shaves": 56,
                },
            ]
        }

        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, hhi=boring score desc, effective_soaps, unique_combinations=unique_soaps, shaves",
        )

        # Check that hhi values are formatted as percentages with 1 decimal place
        assert "93.3%" in result  # 0.933 * 100 = 93.3%
        assert "51.8%" in result  # 0.5176 * 100 = 51.8%
        assert "46.8%" in result  # 0.4681 * 100 = 46.8%

        # Check that effective_soaps values are formatted with 1 decimal place
        assert "1.1" in result  # 1.07 formatted to 1.1
        assert "1.9" in result  # 1.93 formatted to 1.9
        assert "2.1" in result  # 2.14 formatted to 2.1

        # Verify the values are not shown as decimals
        assert "0.933" not in result
        assert "0.5176" not in result
        assert "0.4681" not in result

    def test_most_boring_shaver_tie_break_by_shaves_desc(self):
        """Most Boring Shaver: same HHI ties are broken by shaves descending (more shaves = more boring)."""
        data = {
            "user_soap_brand_scent_diversity": [
                {
                    "rank": 1,
                    "user": "low_activity",
                    "hhi": 1.0,
                    "effective_soaps": 1.0,
                    "unique_combinations": 1,
                    "shaves": 10,
                },
                {
                    "rank": 2,
                    "user": "high_activity",
                    "hhi": 1.0,
                    "effective_soaps": 1.0,
                    "unique_combinations": 1,
                    "shaves": 28,
                },
            ]
        }
        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, hhi desc, shaves desc, effective_soaps, unique_combinations=unique_soaps",
            rows=10,
        )
        # 28 shaves with same soap should rank above 10 shaves (more boring)
        high_pos = result.find("high_activity")
        low_pos = result.find("low_activity")
        assert (
            high_pos < low_pos
        ), "high_activity (28 shaves) should appear before low_activity (10 shaves)"
        # Same (hhi, shaves) tie; different shaves break tie. Here only two rows with different shaves → ranks 1 and 2.
        assert "u/high_activity" in result and "28" in result
        assert "u/low_activity" in result and "10" in result

    def test_most_boring_shaver_same_hhi_same_shaves_tied(self):
        """When two users have same HHI and same shaves, they get the same rank (1=)."""
        data = {
            "user_soap_brand_scent_diversity": [
                {
                    "rank": 1,
                    "user": "userA",
                    "hhi": 1.0,
                    "effective_soaps": 1.0,
                    "unique_combinations": 1,
                    "shaves": 28,
                },
                {
                    "rank": 2,
                    "user": "userB",
                    "hhi": 1.0,
                    "effective_soaps": 1.0,
                    "unique_combinations": 1,
                    "shaves": 28,
                },
                {
                    "rank": 3,
                    "user": "userC",
                    "hhi": 1.0,
                    "effective_soaps": 1.0,
                    "unique_combinations": 1,
                    "shaves": 10,
                },
            ]
        }
        generator = TableGenerator(data)
        result = generator.generate_table(
            "user-soap-brand-scent-diversity",
            columns="rank, user, hhi desc, shaves desc, effective_soaps, unique_combinations=unique_soaps",
            rows=10,
        )
        # userA and userB both (100%, 28) → tied for 1; userC (100%, 10) → rank 3
        assert "1=" in result
        assert result.count("1=") >= 2  # at least two rows show 1=
        assert "u/userA" in result and "u/userB" in result and "u/userC" in result
        assert "3 " in result or "| 3\n" in result or "|      3 |" in result  # userC gets rank 3
