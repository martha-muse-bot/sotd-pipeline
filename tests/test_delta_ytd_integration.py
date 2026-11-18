"""
Test integration of --delta with --ytd flags.

This test file verifies that when both --delta and --ytd are used together,
the pipeline processes the correct number of months for historical comparison.
"""

import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))

from run import calculate_delta_months  # noqa: E402


class TestDeltaYTDIntegration:
    """Test that --delta with --ytd processes the correct months."""

    def test_delta_ytd_should_process_25_months_total(self):
        """
        Test that --delta with --ytd processes 25 months total:
        - Current year (2025): Jan-Aug = 8 months
        - One month ago (Dec 2024-Jul 2025): 1 additional month
        - One year ago (2024): Jan-Aug = 8 months
        - Five years ago (2020): Jan-Aug = 8 months
        """
        # Mock current date to be August 2025
        with (
            patch("datetime.datetime") as mock_datetime,
            patch("run.get_default_month") as mock_get_default_month,
        ):
            mock_datetime.now.return_value = datetime(2025, 8, 15)
            mock_get_default_month.return_value = "2025-07"

            # Create mock args with ytd flag
            mock_args = MagicMock()
            mock_args.month = None
            mock_args.year = None
            mock_args.start = None
            mock_args.end = None
            mock_args.range = None
            mock_args.ytd = True

            # Calculate delta months
            delta_months = calculate_delta_months(mock_args)

            # Should have 25 months total
            assert len(delta_months) == 25, f"Expected 25 months, got {len(delta_months)}"

            # Verify current year months (2025-01 through 2025-08)
            current_year_months = [month for month in delta_months if month.startswith("2025-")]
            assert (
                len(current_year_months) == 8
            ), f"Expected 8 current year months, got {len(current_year_months)}"
            assert "2025-01" in current_year_months
            assert "2025-08" in current_year_months

            # Verify one year ago months (2024-01 through 2024-08) + Dec 2024 (one month ago)
            one_year_ago_months = [month for month in delta_months if month.startswith("2024-")]
            assert (
                len(one_year_ago_months) == 9
            ), f"Expected 9 one year ago months (Jan-Aug + Dec), got {len(one_year_ago_months)}"
            assert "2024-01" in one_year_ago_months
            assert "2024-08" in one_year_ago_months
            assert "2024-12" in one_year_ago_months  # December from one month ago logic

            # Verify five years ago months (2020-01 through 2020-08)
            five_years_ago_months = [month for month in delta_months if month.startswith("2020-")]
            assert (
                len(five_years_ago_months) == 8
            ), f"Expected 8 five years ago months, got {len(five_years_ago_months)}"
            assert "2020-01" in five_years_ago_months
            assert "2020-08" in five_years_ago_months

            # Verify one month ago (2024-12 through 2025-07)
            one_month_ago_months = []
            expected_one_month_ago = [
                "2024-12",
                "2025-01",
                "2025-02",
                "2025-03",
                "2025-04",
                "2025-05",
                "2025-06",
                "2025-07",
            ]
            for month in delta_months:
                if month in expected_one_month_ago:
                    one_month_ago_months.append(month)
            assert (
                len(one_month_ago_months) == 8
            ), f"Expected 8 one month ago months, got {len(one_month_ago_months)}"

    def test_delta_ytd_should_handle_different_current_months(self):
        """Test that the calculation works for different current months."""
        test_cases = [
            (2025, 1, 4),  # January: 4 months (1+1+1+1)
            (2025, 6, 19),  # June: 19 months (6+1+6+6)
            (2025, 12, 36),  # December: 36 months (12+1+11+12)
        ]

        for year, month, expected_total in test_cases:
            with (
                patch("datetime.datetime") as mock_datetime,
                patch("run.get_default_month") as mock_get_default_month,
            ):
                mock_datetime.now.return_value = datetime(year, month, 15)
                mock_get_default_month.return_value = f"{year}-{max(1, month-1):02d}"

                mock_args = MagicMock()
                mock_args.month = None
                mock_args.year = None
                mock_args.start = None
                mock_args.end = None
                mock_args.range = None
                mock_args.ytd = True

                delta_months = calculate_delta_months(mock_args)
                assert len(delta_months) == expected_total, (
                    f"Expected {expected_total} months for {year}-{month:02d}, "
                    f"got {len(delta_months)}"
                )

    def test_delta_ytd_should_handle_year_boundaries(self):
        """Test that the calculation works correctly across year boundaries."""
        # Test December 2024 (previous year)
        with (
            patch("datetime.datetime") as mock_datetime,
            patch("run.get_default_month") as mock_get_default_month,
        ):
            mock_datetime.now.return_value = datetime(2024, 12, 15)
            mock_get_default_month.return_value = "2024-11"

            mock_args = MagicMock()
            mock_args.month = None
            mock_args.year = None
            mock_args.start = None
            mock_args.end = None
            mock_args.range = None
            mock_args.ytd = True

            delta_months = calculate_delta_months(mock_args)

            # Should include months from 2024, 2023, and 2019
            assert "2024-01" in delta_months
            assert "2024-12" in delta_months
            assert "2023-01" in delta_months
            assert "2023-12" in delta_months
            assert "2019-01" in delta_months
            assert "2019-12" in delta_months

    def test_delta_ytd_should_handle_leap_years(self):
        """Test that the calculation works correctly for leap years."""
        # Test February 2024 (leap year)
        with (
            patch("datetime.datetime") as mock_datetime,
            patch("run.get_default_month") as mock_get_default_month,
        ):
            mock_datetime.now.return_value = datetime(2024, 2, 15)
            mock_get_default_month.return_value = "2024-01"

            mock_args = MagicMock()
            mock_args.month = None
            mock_args.year = None
            mock_args.start = None
            mock_args.end = None
            mock_args.range = None
            mock_args.ytd = True

            delta_months = calculate_delta_months(mock_args)

            # Should include February from 2024, 2023, and 2019
            assert "2024-02" in delta_months
            assert "2023-02" in delta_months
            assert "2019-02" in delta_months

    def test_delta_ytd_should_not_duplicate_months(self):
        """Test that no duplicate months are included in the result."""
        with (
            patch("datetime.datetime") as mock_datetime,
            patch("run.get_default_month") as mock_get_default_month,
        ):
            mock_datetime.now.return_value = datetime(2025, 8, 15)
            mock_get_default_month.return_value = "2025-07"

            mock_args = MagicMock()
            mock_args.month = None
            mock_args.year = None
            mock_args.start = None
            mock_args.end = None
            mock_args.range = None
            mock_args.ytd = True

            delta_months = calculate_delta_months(mock_args)

            # Check for duplicates
            assert len(delta_months) == len(set(delta_months)), "Duplicate months found in result"

            # Verify all months are in valid format
            for month in delta_months:
                assert len(month) == 7, f"Invalid month format: {month}"
                assert month[4] == "-", f"Invalid month format: {month}"
                month_num = int(month[5:])
                assert 1 <= month_num <= 12, f"Invalid month number: {month_num}"


if __name__ == "__main__":
    pytest.main([__file__])
