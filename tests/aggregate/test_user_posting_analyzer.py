#!/usr/bin/env python3
"""Tests for UserPostingAnalyzer class."""

from datetime import date
from unittest.mock import Mock, patch

import pytest

from sotd.aggregate.aggregators.users.user_posting_analyzer import UserPostingAnalyzer


class TestUserPostingAnalyzer:
    """Test cases for UserPostingAnalyzer class."""

    def test_init(self):
        """Test UserPostingAnalyzer initialization."""
        analyzer = UserPostingAnalyzer()
        assert analyzer is not None

    def test_load_enriched_data_success(self):
        """Test successful loading of enriched data."""
        # Mock enriched data
        mock_data = {
            "data": [
                {
                    "author": "test_user",
                    "thread_title": "Monday SOTD Thread - Jun 01, 2025",
                    "id": "comment1",
                    "created_utc": "2025-06-01T06:08:36Z",
                }
            ]
        }

        with patch("pathlib.Path.exists", Mock(return_value=True)):
            mock_file = Mock()
            mock_file.__enter__ = Mock(return_value=mock_file)
            mock_file.__exit__ = Mock(return_value=None)

            with patch("builtins.open", Mock(return_value=mock_file)):
                with patch("json.load", Mock(return_value=mock_data)):
                    analyzer = UserPostingAnalyzer()
                    result = analyzer.load_enriched_data("2025-06")

                    assert result is not None
                    assert len(result) == 1
                    assert result[0]["author"] == "test_user"

    def test_load_enriched_data_file_not_found(self):
        """Test handling of missing enriched data file."""
        analyzer = UserPostingAnalyzer()

        with patch("pathlib.Path.exists", Mock(return_value=False)):
            result = analyzer.load_enriched_data("2025-06")
            assert result == []

    def test_extract_date_from_thread_title_success(self):
        """Test successful date extraction from thread title."""
        analyzer = UserPostingAnalyzer()

        thread_title = "Monday SOTD Thread - Jun 01, 2025"
        result = analyzer._extract_date_from_thread_title(thread_title)

        assert result == date(2025, 6, 1)

    def test_extract_date_from_thread_title_invalid_format(self):
        """Test handling of invalid thread title format."""
        analyzer = UserPostingAnalyzer()

        thread_title = "Invalid Thread Title"
        with pytest.raises(ValueError):
            analyzer._extract_date_from_thread_title(thread_title)

    def test_analyze_user_posting_basic(self):
        """Test basic user posting analysis."""
        # Mock enriched data
        mock_data = [
            {
                "author": "test_user",
                "thread_title": "Monday SOTD Thread - Jun 01, 2025",
                "id": "comment1",
                "created_utc": "2025-06-01T06:08:36Z",
            },
            {
                "author": "test_user",
                "thread_title": "Tuesday SOTD Thread - Jun 02, 2025",
                "id": "comment2",
                "created_utc": "2025-06-02T06:08:36Z",
            },
        ]

        analyzer = UserPostingAnalyzer()
        result = analyzer.analyze_user_posting("test_user", mock_data)

        assert result is not None
        assert result["user"] == "test_user"
        assert result["posted_days"] == 2
        assert result["missed_days"] == 28  # June has 30 days, 2 posted = 28 missed
        assert len(result["posted_dates"]) == 2
        assert len(result["comment_ids"]) == 2

    def test_analyze_user_posting_no_posts(self):
        """Test user posting analysis for user with no posts."""
        mock_data = []

        analyzer = UserPostingAnalyzer()
        result = analyzer.analyze_user_posting("test_user", mock_data)

        assert result is not None
        assert result["user"] == "test_user"
        assert result["posted_days"] == 0
        assert result["missed_days"] == 30  # June has 30 days
        assert len(result["posted_dates"]) == 0
        assert len(result["comment_ids"]) == 0

    def test_get_all_dates_in_month(self):
        """Test getting all dates in a month."""
        analyzer = UserPostingAnalyzer()

        # Test June 2025 (30 days)
        result = analyzer._get_all_dates_in_month(2025, 6)

        assert len(result) == 30
        assert result[0] == date(2025, 6, 1)
        assert result[29] == date(2025, 6, 30)

    def test_get_all_dates_in_month_february_leap_year(self):
        """Test getting all dates in February during leap year."""
        analyzer = UserPostingAnalyzer()

        # Test February 2024 (leap year, 29 days)
        result = analyzer._get_all_dates_in_month(2024, 2)

        assert len(result) == 29
        assert result[0] == date(2024, 2, 1)
        assert result[28] == date(2024, 2, 29)

    def test_get_all_dates_in_month_february_non_leap_year(self):
        """Test getting all dates in February during non-leap year."""
        analyzer = UserPostingAnalyzer()

        # Test February 2025 (non-leap year, 28 days)
        result = analyzer._get_all_dates_in_month(2025, 2)

        assert len(result) == 28
        assert result[0] == date(2025, 2, 1)
        assert result[27] == date(2025, 2, 28)
