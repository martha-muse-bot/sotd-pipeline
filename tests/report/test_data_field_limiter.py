#!/usr/bin/env python3
"""Tests for DataFieldLimiter."""


from sotd.report.data_field_limiter import DataFieldLimiter


class TestDataFieldLimiter:
    """Test cases for DataFieldLimiter."""

    def test_apply_limits_no_parameters(self):
        """Test applying no limits returns original data."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
        ]

        result = limiter.apply_limits(data, {})

        assert result == data

    def test_apply_limits_single_column(self):
        """Test applying limit to single column."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
        ]

        result = limiter.apply_limits(data, {"shaves": 5})

        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_apply_limits_multiple_columns(self):
        """Test applying limits to multiple columns."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
            {"shaves": 8, "unique_users": 1},
        ]

        result = limiter.apply_limits(data, {"shaves": 5, "unique_users": 2})

        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_apply_limits_all_items_below_threshold(self):
        """Test when all items are below threshold."""
        limiter = DataFieldLimiter()
        data = [{"shaves": 3, "unique_users": 1}, {"shaves": 2, "unique_users": 1}]

        result = limiter.apply_limits(data, {"shaves": 5})

        assert len(result) == 0

    def test_apply_limits_empty_data(self):
        """Test applying limits to empty data."""
        limiter = DataFieldLimiter()
        data = []

        result = limiter.apply_limits(data, {"shaves": 5})

        assert result == []

    def test_apply_limits_missing_column(self):
        """Test applying limits when column is missing from data."""
        limiter = DataFieldLimiter()
        data = [{"shaves": 10, "unique_users": 5}, {"shaves": 5, "unique_users": 3}]

        result = limiter.apply_limits(data, {"missing_column": 5})

        # Should return original data since column doesn't exist
        assert result == data

    def test_apply_limits_tie_at_threshold(self):
        """Test applying limits when items are tied at threshold."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 5, "unique_users": 2},  # Tied at threshold
            {"shaves": 3, "unique_users": 1},
        ]

        result = limiter.apply_limits(data, {"shaves": 5})

        # Should include both items with shaves >= 5
        assert len(result) == 3
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5
        assert result[2]["shaves"] == 5

    def test_apply_limits_string_values(self):
        """Test applying limits to string values."""
        limiter = DataFieldLimiter()
        data = [
            {"format": "DE", "shaves": 10},
            {"format": "SE", "shaves": 5},
            {"format": "SR", "shaves": 3},
        ]

        result = limiter.apply_limits(data, {"format": "SE"})

        # String comparison should work - "SE" >= "SE" and "SR" >= "SE"
        assert len(result) == 2
        assert result[0]["format"] == "SE"
        assert result[1]["format"] == "SR"

    def test_apply_limits_float_values(self):
        """Test applying limits to float values."""
        limiter = DataFieldLimiter()
        data = [
            {"avg_shaves_per_user": 5.5, "shaves": 10},
            {"avg_shaves_per_user": 3.2, "shaves": 5},
            {"avg_shaves_per_user": 2.1, "shaves": 3},
        ]

        result = limiter.apply_limits(data, {"avg_shaves_per_user": 3.0})

        assert len(result) == 2
        assert result[0]["avg_shaves_per_user"] == 5.5
        assert result[1]["avg_shaves_per_user"] == 3.2

    def test_apply_limits_preserve_order(self):
        """Test that applying limits preserves original order."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
        ]

        result = limiter.apply_limits(data, {"shaves": 5})

        # Order should be preserved
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_apply_column_limit_single_column(self):
        """Test applying limit to single column directly."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": 5, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
        ]

        result = limiter.apply_column_limit(data, "shaves", 5)

        assert len(result) == 2
        assert result[0]["shaves"] == 10
        assert result[1]["shaves"] == 5

    def test_apply_column_limit_missing_column(self):
        """Test applying limit to missing column."""
        limiter = DataFieldLimiter()
        data = [{"shaves": 10, "unique_users": 5}, {"shaves": 5, "unique_users": 3}]

        result = limiter.apply_column_limit(data, "missing_column", 5)

        # Should return original data
        assert result == data

    def test_apply_column_limit_none_values(self):
        """Test applying limits when some values are None."""
        limiter = DataFieldLimiter()
        data = [
            {"shaves": 10, "unique_users": 5},
            {"shaves": None, "unique_users": 3},
            {"shaves": 3, "unique_users": 2},
        ]

        result = limiter.apply_column_limit(data, "shaves", 5)

        # None values should be treated as below threshold
        assert len(result) == 1
        assert result[0]["shaves"] == 10
