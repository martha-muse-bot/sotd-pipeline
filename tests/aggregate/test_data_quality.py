"""Data quality tests for the aggregate phase."""

import pytest

from sotd.aggregate.processor import (
    aggregate_all,
    check_data_quality,
    normalize_fields,
    validate_records,
)
from sotd.aggregate.utils.metrics import calculate_metadata


class TestDataQuality:
    """Data quality tests for the aggregate phase."""

    def test_validate_records_valid_data(self):
        """Test validation with valid records."""
        records = [
            {"author": "user1", "razor": {"matched": {"brand": "Test"}}},
            {"author": "user2", "blade": {"matched": {"brand": "Test"}}},
        ]

        validated = validate_records(records)
        assert len(validated) == 2

    def test_validate_records_invalid_input(self):
        """Test validation with invalid input types."""
        # Test non-list input
        with pytest.raises(ValueError, match="Records must be a list"):
            validate_records("not a list")  # type: ignore

        # Test list with non-dict items
        with pytest.raises(ValueError, match="Each record must be a dictionary"):
            validate_records([{"author": "user1"}, "not a dict"])  # type: ignore

        # Test missing author field
        with pytest.raises(ValueError, match="Each record must have an 'author' field"):
            validate_records([{"razor": {"matched": {"brand": "Test"}}}])

    def test_normalize_fields(self):
        """Test field normalization."""
        records = [
            {
                "author": "  user1  ",
                "razor": {"matched": {"brand": "  Test  ", "model": "Test"}},
                "blade": {"matched": {"brand": "Test", "model": "  Test  "}},
            }
        ]

        normalized = normalize_fields(records)
        assert normalized[0]["author"] == "user1"
        assert normalized[0]["razor"]["matched"]["brand"] == "Test"
        assert normalized[0]["blade"]["matched"]["model"] == "Test"

    def test_check_data_quality_valid_data(self):
        """Test data quality checks with valid data."""
        records = [
            {"author": "user1"},
            {"author": "user2"},
        ]

        # Should not raise any exceptions
        check_data_quality(records)

    def test_check_data_quality_empty_data(self):
        """Test data quality checks with empty data."""
        records = []

        # Should not raise for empty data
        check_data_quality(records)

    def test_check_data_quality_no_authors(self):
        """Test data quality checks with no valid authors."""
        records = [
            {"author": ""},
            {"author": "   "},
            {"author": None},  # Test None values as well
        ]

        with pytest.raises(ValueError, match="No valid authors found in records"):
            check_data_quality(records)

    def test_aggregate_all_empty_data(self):
        """Test aggregation with empty data."""
        records = []
        result = aggregate_all(records, "2025-01")

        assert result["meta"]["total_shaves"] == 0
        assert result["meta"]["unique_shavers"] == 0
        assert result["meta"]["avg_shaves_per_user"] == 0.0

    def test_aggregate_all_single_record(self):
        """Test aggregation with single record."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "brush": {
                    "matched": {
                        "brand": "Test",
                        "model": "Test",
                        "handle": {"brand": "Test", "model": "Test"},
                        "knot": {"fiber": "Synthetic"},
                    }
                },
                "soap": {"matched": {"brand": "Test", "scent": "Test"}},
            }
        ]

        result = aggregate_all(records, "2025-01")

        assert result["meta"]["total_shaves"] == 1
        assert result["meta"]["unique_shavers"] == 1
        assert result["meta"]["avg_shaves_per_user"] == 1.0

    def test_aggregate_all_missing_product_data(self):
        """Test aggregation with missing product data."""
        records = [
            {"author": "user1"},  # No product data
            {
                "author": "user2",
                "razor": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                # Missing other products
            },
        ]

        result = aggregate_all(records, "2025-01")

        # Should still process successfully
        assert result["meta"]["total_shaves"] == 2
        assert result["meta"]["unique_shavers"] == 2

    def test_rank_field_correctness(self):
        """Test that rank fields are correctly calculated using tier-based ranking."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "blade": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "brush": {
                    "matched": {
                        "brand": "Test1",
                        "model": "Test1",
                        "handle": {"brand": "Test1", "model": "Test1"},
                        "knot": {"fiber": "Synthetic"},
                    }
                },
                "soap": {"matched": {"brand": "Test1", "scent": "Test1"}},
            },
            {
                "author": "user2",
                "razor": {"matched": {"brand": "Test2", "model": "Test2", "format": "DE"}},
                "blade": {"matched": {"brand": "Test2", "model": "Test2", "format": "DE"}},
                "brush": {
                    "matched": {
                        "brand": "Test2",
                        "model": "Test2",
                        "handle": {"brand": "Test2", "model": "Test2"},
                        "knot": {"fiber": "Synthetic"},
                    }
                },
                "soap": {"matched": {"brand": "Test2", "scent": "Test2"}},
            },
        ]

        result = aggregate_all(records, "2025-01")
        data = result["data"]

        # Check rank/position fields for categories that need ranking
        categories_that_need_ranking = [
            "razors",
            "blades",
            "brushes",
            "soaps",
            "razor_manufacturers",
            "blade_manufacturers",
            "soap_makers",
            "razor_formats",
            "brush_handle_makers",
            "brush_knot_makers",
            "brush_fibers",
            "brush_knot_sizes",
            "users",
        ]

        for category_name, category_data in data.items():
            if category_data and category_name in categories_that_need_ranking:
                # Check that rank or position field exists and is valid
                for item in category_data:
                    if "rank" in item:
                        assert item["rank"] > 0, f"Rank {item['rank']} <= 0 in {category_name}"
                        assert isinstance(
                            item["rank"], int
                        ), f"Rank {item['rank']} is not an integer in {category_name}"
                    elif "position" in item:
                        assert (
                            item["position"] > 0
                        ), f"Position {item['position']} <= 0 in {category_name}"
                        assert isinstance(
                            item["position"], int
                        ), f"Position {item['position']} is not an integer in {category_name}"
                    else:
                        assert False, f"Missing rank or position in {category_name}"

                # Check that items are properly ordered (descending by shaves, then by unique_users)
                for i in range(len(category_data) - 1):
                    current = category_data[i]
                    next_item = category_data[i + 1]
                    assert (
                        current["shaves"] >= next_item["shaves"]
                    ), f"Shaves not in descending order in {category_name}"
                    if current["shaves"] == next_item["shaves"]:
                        assert current["unique_users"] >= next_item["unique_users"], (
                            f"Unique users not in descending order for equal shaves in "
                            f"{category_name}"
                        )

    def test_sort_order_correctness(self):
        """Test that sort orders are correct for different categories."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "blade": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "brush": {
                    "matched": {
                        "brand": "Test1",
                        "model": "Test1",
                        "handle": {"brand": "Test1", "model": "Test1"},
                        "knot": {"fiber": "Synthetic"},
                    }
                },
                "soap": {"matched": {"brand": "Test1", "scent": "Test1"}},
            },
            {
                "author": "user2",
                "razor": {"matched": {"brand": "Test2", "model": "Test2", "format": "DE"}},
                "blade": {"matched": {"brand": "Test2", "model": "Test2", "format": "DE"}},
                "brush": {"matched": {"brand": "Test2", "model": "Test2", "fiber": "Synthetic"}},
                "soap": {"matched": {"brand": "Test2", "scent": "Test2"}},
            },
            {
                "author": "user1",  # Same user as first record
                "razor": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "blade": {"matched": {"brand": "Test1", "model": "Test1", "format": "DE"}},
                "brush": {"matched": {"brand": "Test1", "model": "Test1", "fiber": "Synthetic"}},
                "soap": {"matched": {"brand": "Test1", "scent": "Test1"}},
            },
        ]

        result = aggregate_all(records, "2025-01")
        data = result["data"]

        # Test users sort order (missed_days asc, shaves desc)
        users = data["users"]
        if len(users) >= 2:
            assert users[0]["missed_days"] <= users[1]["missed_days"]
            if users[0]["missed_days"] == users[1]["missed_days"]:
                assert users[0]["shaves"] >= users[1]["shaves"]

        # Test default sort order (shaves desc, unique_users desc)
        for category in ["razors", "blades", "brushes", "soaps"]:
            if len(data[category]) >= 2:
                assert data[category][0]["shaves"] >= data[category][1]["shaves"]

    def test_output_structure_completeness(self):
        """Test that output structure contains all required fields."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "brush": {"matched": {"brand": "Test", "model": "Test", "fiber": "Synthetic"}},
                "soap": {"matched": {"brand": "Test", "scent": "Test"}},
            }
        ]

        result = aggregate_all(records, "2025-01")

        # Check metadata structure
        assert "meta" in result
        meta = result["meta"]
        required_meta_fields = ["month", "total_shaves", "unique_shavers", "avg_shaves_per_user"]
        for field in required_meta_fields:
            assert field in meta, f"Missing metadata field: {field}"

        # Check data structure
        assert "data" in result
        data = result["data"]

        # Check all required categories are present
        required_categories = [
            "razors",
            "blades",
            "brushes",
            "soaps",
            "razor_manufacturers",
            "blade_manufacturers",
            "soap_makers",
            "razor_formats",
            "brush_handle_makers",
            "brush_knot_makers",
            "brush_fibers",
            "brush_knot_sizes",
            "blackbird_plates",
            "christopher_bradley_plates",
            "game_changer_plates",
            "super_speed_variants",
            "straight_widths",
            "straight_grinds",
            "straight_points",
            "users",
            "razor_blade_combinations",
            "highest_use_count_per_blade",
        ]

        for category in required_categories:
            assert category in data, f"Missing category: {category}"
            assert isinstance(data[category], list), f"Category {category} should be a list"

    def test_field_name_consistency(self):
        """Test that field names match the specification exactly."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "brush": {"matched": {"brand": "Test", "model": "Test", "fiber": "Synthetic"}},
                "soap": {"matched": {"brand": "Test", "scent": "Test"}},
            }
        ]

        result = aggregate_all(records, "2025-01")
        data = result["data"]

        # Test users field name (should be "user", not "name")
        if data["users"]:
            assert "user" in data["users"][0], "Users should have 'user' field"
            assert "name" not in data["users"][0], "Users should not have 'name' field"

        # Test highest_use_count_per_blade field names
        if data["highest_use_count_per_blade"]:
            item = data["highest_use_count_per_blade"][0]
            assert "user" in item, "highest_use_count_per_blade should have 'user' field"
            assert "blade" in item, "highest_use_count_per_blade should have 'blade' field"
            assert "format" in item, "highest_use_count_per_blade should have 'format' field"
            assert "uses" in item, "highest_use_count_per_blade should have 'uses' field"

    def test_edge_case_null_values(self):
        """Test handling of null values in data."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": "Test", "format": "DE"}},
                "brush": {"matched": {"brand": "Test", "model": "Test", "fiber": "Synthetic"}},
                "soap": {"matched": {"brand": "Test", "scent": "Test"}},
            },
            {
                "author": "user2",
                "razor": {"matched": {"brand": None, "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": None, "format": "DE"}},
                "brush": {"matched": {"brand": "Test", "model": "Test", "fiber": None}},
                "soap": {"matched": {"brand": None, "scent": "Test"}},
            },
        ]

        # Should not raise exceptions
        result = aggregate_all(records, "2025-01")
        assert result["meta"]["total_shaves"] == 2

    def test_edge_case_empty_strings(self):
        """Test handling of empty strings in data."""
        records = [
            {
                "author": "user1",
                "razor": {"matched": {"brand": "", "model": "Test", "format": "DE"}},
                "blade": {"matched": {"brand": "Test", "model": "", "format": "DE"}},
                "brush": {"matched": {"brand": "Test", "model": "Test", "fiber": ""}},
                "soap": {"matched": {"brand": "", "scent": "Test"}},
            }
        ]

        # Should not raise exceptions
        result = aggregate_all(records, "2025-01")
        assert result["meta"]["total_shaves"] == 1

    def test_metadata_calculation_accuracy(self):
        """Test that metadata calculations are accurate."""
        records = [
            {"author": "user1"},
            {"author": "user2"},
            {"author": "user1"},  # Same user as first record
        ]

        meta = calculate_metadata(records, "2025-01")

        assert meta["total_shaves"] == 3
        assert meta["unique_shavers"] == 2
        assert meta["avg_shaves_per_user"] == 1.5
        assert meta["month"] == "2025-01"
