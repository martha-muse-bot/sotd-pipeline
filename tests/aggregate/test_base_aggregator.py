"""Tests for base aggregator functionality."""

import pytest

from sotd.aggregate.aggregators.base_aggregator import BaseAggregator


class MockAggregator(BaseAggregator):
    """Mock implementation of BaseAggregator for testing."""

    @property
    def IDENTIFIER_FIELDS(self) -> list[str]:
        """Fields used for matching/grouping."""
        return ["brand", "model"]

    @property
    def METRIC_FIELDS(self) -> list[str]:
        """Calculated/metric fields."""
        return ["shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> list[str]:
        """Fields used for sorting/ranking."""
        return ["shaves", "unique_users"]

    def _extract_data(self, records):
        """Extract test data from records."""
        extracted_data = []
        for record in records:
            product = record.get("test_product", {})
            matched = product.get("matched", {})

            if not matched or not matched.get("brand") or not matched.get("model"):
                continue

            brand = matched.get("brand", "").strip()
            model = matched.get("model", "").strip()
            author = record.get("author", "").strip()

            if brand and model and author:
                extracted_data.append({"brand": brand, "model": model, "author": author})

        return extracted_data

    def _create_composite_name(self, df):
        """Create composite name from brand and model."""
        return df["brand"] + " " + df["model"]


class MockAggregatorWithGrouping(BaseAggregator):
    """Mock implementation with additional grouping fields."""

    @property
    def IDENTIFIER_FIELDS(self) -> list[str]:
        """Fields used for matching/grouping."""
        return ["brand", "model", "category"]

    @property
    def METRIC_FIELDS(self) -> list[str]:
        """Calculated/metric fields."""
        return ["shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> list[str]:
        """Fields used for sorting/ranking."""
        return ["shaves", "unique_users"]

    def _extract_data(self, records):
        """Extract test data with additional grouping field."""
        extracted_data = []
        for record in records:
            product = record.get("test_product", {})
            matched = product.get("matched", {})

            if not matched or not matched.get("brand") or not matched.get("model"):
                continue

            brand = matched.get("brand", "").strip()
            model = matched.get("model", "").strip()
            category = matched.get("category", "").strip()
            author = record.get("author", "").strip()

            if brand and model and category and author:
                extracted_data.append(
                    {"brand": brand, "model": model, "category": category, "author": author}
                )

        return extracted_data

    def _create_composite_name(self, df):
        """Create composite name from brand and model."""
        return df["brand"] + " " + df["model"]

    def _get_group_columns(self, df):
        """Group by name and category."""
        return ["name", "category"]


@pytest.fixture
def test_aggregator():
    """Fixture for MockAggregator instance."""
    return MockAggregator()


@pytest.fixture
def test_aggregator_with_grouping():
    """Fixture for MockAggregatorWithGrouping instance."""
    return MockAggregatorWithGrouping()


class TestBaseAggregator:
    """Test cases for BaseAggregator functionality."""

    def test_aggregate_empty_records(self, test_aggregator):
        """Test aggregation with empty records."""
        result = test_aggregator.aggregate([])
        assert result == []

    def test_aggregate_no_valid_data(self, test_aggregator):
        """Test aggregation with records but no valid data."""
        records = [
            {"test_product": {"matched": {}}, "author": "user1"},
            {"test_product": {"matched": {"brand": ""}}, "author": "user2"},
        ]
        result = test_aggregator.aggregate(records)
        assert result == []

    def test_aggregate_basic_functionality(self, test_aggregator):
        """Test basic aggregation functionality."""
        records = [
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        assert len(result) == 2

        # Check first item (Brand1 Model1 - 2 shaves, 2 users)
        assert result[0]["rank"] == 1
        assert result[0]["name"] == "Brand1 Model1"
        assert result[0]["shaves"] == 2
        assert result[0]["unique_users"] == 2

        # Check second item (Brand2 Model2 - 1 shave, 1 user)
        assert result[1]["rank"] == 2
        assert result[1]["name"] == "Brand2 Model2"
        assert result[1]["shaves"] == 1
        assert result[1]["unique_users"] == 1

    def test_aggregate_with_grouping(self, test_aggregator_with_grouping):
        """Test aggregation with additional grouping fields."""
        records = [
            {
                "test_product": {
                    "matched": {"brand": "Brand1", "model": "Model1", "category": "Category1"}
                },
                "author": "user1",
            },
            {
                "test_product": {
                    "matched": {"brand": "Brand1", "model": "Model1", "category": "Category2"}
                },
                "author": "user2",
            },
        ]

        result = test_aggregator_with_grouping.aggregate(records)

        assert len(result) == 2

        # Check both items have correct grouping
        assert result[0]["name"] == "Brand1 Model1"
        assert result[0]["category"] == "Category1"
        assert result[1]["name"] == "Brand1 Model1"
        assert result[1]["category"] == "Category2"

    def test_sorting_by_shaves_and_users(self, test_aggregator):
        """Test that results are sorted by shaves desc, unique_users desc."""
        records = [
            # Brand1 Model1: 3 shaves, 1 user
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            # Brand2 Model2: 2 shaves, 2 users
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Brand1 Model1 should be first (more shaves)
        assert result[0]["name"] == "Brand1 Model1"
        assert result[0]["shaves"] == 3
        assert result[0]["unique_users"] == 1

        # Brand2 Model2 should be second (fewer shaves, but more unique users)
        assert result[1]["name"] == "Brand2 Model2"
        assert result[1]["shaves"] == 2
        assert result[1]["unique_users"] == 2

    def test_extract_field_utility(self, test_aggregator):
        """Test the _extract_field utility method."""

        record = {"level1": {"level2": {"level3": "test_value"}}}

        # Test successful extraction
        result = test_aggregator._extract_field(record, ["level1", "level2", "level3"])
        assert result == "test_value"

        # Test with default value
        result = test_aggregator._extract_field(record, ["level1", "missing"], "default")
        assert result == "default"

        # Test with None value
        record["level1"]["level2"]["level3"] = ""  # Use empty string instead of None
        result = test_aggregator._extract_field(record, ["level1", "level2", "level3"], "default")
        assert result == "default"

        # Test with whitespace
        record["level1"]["level2"]["level3"] = "  test  "
        result = test_aggregator._extract_field(record, ["level1", "level2", "level3"])
        assert result == "test"

    def test_validate_required_fields(self, test_aggregator):
        """Test the _validate_required_fields utility method."""

        data = {"field1": "value1", "field2": "value2", "field3": ""}

        # Test with all required fields present and non-empty
        assert test_aggregator._validate_required_fields(data, ["field1", "field2"]) is True

        # Test with missing field
        assert test_aggregator._validate_required_fields(data, ["field1", "field4"]) is False

        # Test with empty field
        assert test_aggregator._validate_required_fields(data, ["field1", "field3"]) is False

        # Test with None field
        data["field4"] = ""  # Use empty string instead of None
        assert test_aggregator._validate_required_fields(data, ["field1", "field4"]) is False

    def test_rank_assignment(self, test_aggregator):
        """Test that rank assignments are correctly assigned."""
        records = [
            # Brand1 Model1: 3 shaves, 1 user (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            # Brand2 Model2: 2 shaves, 1 user (rank 2)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            # Brand3 Model3: 1 shave, 1 user (rank 3)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user3",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Check that ranks are 1-based and sequential
        assert result[0]["rank"] == 1  # Brand1 Model1: 3 shaves
        assert result[1]["rank"] == 2  # Brand2 Model2: 2 shaves
        assert result[2]["rank"] == 3  # Brand3 Model3: 1 shave

    def test_data_types_in_result(self, test_aggregator):
        """Test that result data types are correct."""
        records = [
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        assert len(result) == 1
        item = result[0]

        # Check data types
        assert isinstance(item["rank"], int)
        assert isinstance(item["shaves"], int)
        assert isinstance(item["unique_users"], int)
        assert isinstance(item["name"], str)

    # New tests for tier-based ranking functionality
    def test_tie_columns_property_default(self, test_aggregator):
        """Test that tie_columns property has correct default value."""
        assert test_aggregator.tie_columns == ["shaves", "unique_users"]

    def test_tie_columns_property_override(self, test_aggregator):
        """Test that subclasses can override tie_columns property."""

        class TestAggregatorCustomTies(MockAggregator):
            tie_columns = ["shaves"]  # Only shaves matter for ties

        custom_aggregator = TestAggregatorCustomTies()
        assert custom_aggregator.tie_columns == ["shaves"]

    def test_tier_based_ranking_no_ties(self, test_aggregator):
        """Test tier-based ranking when no items are tied."""
        records = [
            # Brand1 Model1: 3 shaves, 1 user (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            # Brand2 Model2: 2 shaves, 1 user (rank 2)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            # Brand3 Model3: 1 shave, 1 user (rank 3)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user3",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Check that ranks are sequential when no ties
        assert result[0]["rank"] == 1  # Brand1 Model1: 3 shaves
        assert result[1]["rank"] == 2  # Brand2 Model2: 2 shaves
        assert result[2]["rank"] == 3  # Brand3 Model3: 1 shave

    def test_tier_based_ranking_with_ties(self, test_aggregator):
        """Test tier-based ranking when items have identical values."""
        records = [
            # Brand1 Model1: 10 shaves, 3 users (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user3",
            },
            # Brand2 Model2: 8 shaves, 2 users (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            # Brand3 Model3: 8 shaves, 2 users (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user2",
            },
            # Brand4 Model4: 8 shaves, 1 user (rank 3)
            {
                "test_product": {"matched": {"brand": "Brand4", "model": "Model4"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Check competition ranking (1, 2, 2, 4)
        assert result[0]["rank"] == 1  # Brand1 Model1: 10 shaves, 3 users
        assert result[1]["rank"] == 2  # Brand2 Model2: 8 shaves, 2 users (tied)
        assert result[2]["rank"] == 2  # Brand3 Model3: 8 shaves, 2 users (tied)
        assert result[3]["rank"] == 4  # Brand4 Model4: 8 shaves, 1 user (skipping 3)

    def test_tier_based_ranking_all_tied(self, test_aggregator):
        """Test tier-based ranking when all items have identical values."""
        records = [
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user3",
            },
        ]

        result = test_aggregator.aggregate(records)

        # All items have 1 shave, 1 user, so they should all be tied at rank 1
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 1
        assert result[2]["rank"] == 1

    def test_tier_based_ranking_field_name_change(self, test_aggregator):
        """Test that output field changed from 'position' to 'rank'."""
        records = [
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Should have 'rank' field, not 'position'
        assert "rank" in result[0]
        assert "position" not in result[0]
        assert result[0]["rank"] == 1

    def test_tier_based_ranking_custom_tie_columns(self, test_aggregator):
        """Test tier-based ranking with custom tie_columns."""

        class TestAggregatorCustomTies(MockAggregator):
            tie_columns = ["shaves"]  # Only shaves matter for ties

        records = [
            # Brand1 Model1: 1 shave, 1 user (rank 2, tied on shaves only)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            # Brand2 Model2: 1 shave, 1 user (rank 2, tied on shaves only)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            # Brand3 Model3: 3 shaves, 3 users (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user3",
            },
        ]

        custom_aggregator = TestAggregatorCustomTies()
        result = custom_aggregator.aggregate(records)

        # Check that only shaves matter for ties
        # Brand3 should be rank 1 (3 shaves), Brand1 and Brand2 should be tied at rank 2
        assert result[0]["rank"] == 1  # Brand3 Model3: 3 shaves
        assert result[1]["rank"] == 2  # Brand1 Model1: 1 shave (tied)
        assert result[2]["rank"] == 2  # Brand2 Model2: 1 shave (tied)

    def test_competition_ranking_multi_column(self, test_aggregator):
        """Test that competition ranking uses both shaves and unique_users for ranking."""
        records = [
            # Brand1 Model1: 5 shaves, 3 users (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user3",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user2",
            },
            # Brand2 Model2: 3 shaves, 2 users (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            # Brand3 Model3: 3 shaves, 2 users (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user3",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user1",
            },
            # Brand4 Model4: 2 shaves, 1 user (rank 4)
            {
                "test_product": {"matched": {"brand": "Brand4", "model": "Model4"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand4", "model": "Model4"}},
                "author": "user1",
            },
            # Brand5 Model5: 1 shave, 1 user (rank 5)
            {
                "test_product": {"matched": {"brand": "Brand5", "model": "Model5"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Check multi-column competition ranking: 1, 2, 3, 4, 5
        # Brand1 Model1: 5 shaves, 3 users -> rank 1
        assert result[0]["rank"] == 1
        assert result[0]["name"] == "Brand1 Model1"
        assert result[0]["shaves"] == 5

        # Brand3 Model3: 3 shaves, 3 users -> rank 2 (higher because more users)
        assert result[1]["rank"] == 2
        assert result[1]["name"] == "Brand3 Model3"
        assert result[1]["shaves"] == 3
        assert result[1]["unique_users"] == 3

        # Brand2 Model2: 3 shaves, 2 users -> rank 3 (lower because fewer users)
        assert result[2]["rank"] == 3
        assert result[2]["name"] == "Brand2 Model2"
        assert result[2]["shaves"] == 3
        assert result[2]["unique_users"] == 2

        # Brand4 Model4: 2 shaves, 1 user -> rank 4
        assert result[3]["rank"] == 4
        assert result[3]["name"] == "Brand4 Model4"
        assert result[3]["shaves"] == 2

        # Brand5 Model5: 1 shave, 1 user -> rank 5
        assert result[4]["rank"] == 5
        assert result[4]["name"] == "Brand5 Model5"
        assert result[4]["shaves"] == 1

        # Verify that ranks follow competition ranking pattern (no ties in this case)
        ranks = [item["rank"] for item in result]
        assert ranks == [1, 2, 3, 4, 5], f"Expected [1, 2, 3, 4, 5], got {ranks}"

    def test_competition_ranking_with_true_ties(self, test_aggregator):
        """Test competition ranking with true ties (same shaves AND unique_users)."""
        records = [
            # Brand1 Model1: 3 shaves, 2 users (rank 1)
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand1", "model": "Model1"}},
                "author": "user1",
            },
            # Brand2 Model2: 2 shaves, 1 user (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Brand2", "model": "Model2"}},
                "author": "user1",
            },
            # Brand3 Model3: 2 shaves, 1 user (rank 2, tied)
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Brand3", "model": "Model3"}},
                "author": "user2",
            },
            # Brand4 Model4: 1 shave, 1 user (rank 4, skipping 3)
            {
                "test_product": {"matched": {"brand": "Brand4", "model": "Model4"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        # Check true competition ranking with ties: 1, 2, 2, 4
        # Brand1 Model1: 3 shaves, 2 users -> rank 1
        assert result[0]["rank"] == 1
        assert result[0]["name"] == "Brand1 Model1"
        assert result[0]["shaves"] == 3
        assert result[0]["unique_users"] == 2

        # Brand2 Model2: 2 shaves, 1 user -> rank 2 (tied, alphabetically first)
        assert result[1]["rank"] == 2
        assert result[1]["name"] == "Brand2 Model2"
        assert result[1]["shaves"] == 2
        assert result[1]["unique_users"] == 1

        # Brand3 Model3: 2 shaves, 1 user -> rank 2 (tied, alphabetically second)
        assert result[2]["rank"] == 2
        assert result[2]["name"] == "Brand3 Model3"
        assert result[2]["shaves"] == 2
        assert result[2]["unique_users"] == 1

        # Brand4 Model4: 1 shave, 1 user -> rank 4 (skipping 3)
        assert result[3]["rank"] == 4
        assert result[3]["name"] == "Brand4 Model4"
        assert result[3]["shaves"] == 1
        assert result[3]["unique_users"] == 1

        # Verify that ranks follow competition ranking pattern with ties
        ranks = [item["rank"] for item in result]
        assert ranks == [1, 2, 2, 4], f"Expected [1, 2, 2, 4], got {ranks}"

    def test_brand_model_preservation(self, test_aggregator):
        """Test that brand and model fields are preserved in aggregated output."""
        records = [
            {
                "test_product": {"matched": {"brand": "Rockwell", "model": "6S"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Rockwell", "model": "6S"}},
                "author": "user2",
            },
            {
                "test_product": {"matched": {"brand": "Merkur", "model": "34C"}},
                "author": "user1",
            },
        ]

        result = test_aggregator.aggregate(records)

        assert len(result) == 2

        # Check first item (Rockwell 6S)
        assert result[0]["name"] == "Rockwell 6S"
        assert result[0]["brand"] == "Rockwell"
        assert result[0]["model"] == "6S"
        assert result[0]["shaves"] == 2
        assert result[0]["unique_users"] == 2

        # Check second item (Merkur 34C)
        assert result[1]["name"] == "Merkur 34C"
        assert result[1]["brand"] == "Merkur"
        assert result[1]["model"] == "34C"
        assert result[1]["shaves"] == 1
        assert result[1]["unique_users"] == 1

    def test_brand_model_preservation_with_ties(self, test_aggregator):
        """Test that brand and model are preserved even when items are tied."""
        records = [
            # Rockwell 6S: 2 shaves, 2 users
            {
                "test_product": {"matched": {"brand": "Rockwell", "model": "6S"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Rockwell", "model": "6S"}},
                "author": "user2",
            },
            # Merkur 34C: 2 shaves, 2 users (tied)
            {
                "test_product": {"matched": {"brand": "Merkur", "model": "34C"}},
                "author": "user1",
            },
            {
                "test_product": {"matched": {"brand": "Merkur", "model": "34C"}},
                "author": "user2",
            },
        ]

        result = test_aggregator.aggregate(records)

        assert len(result) == 2

        # Both should have brand and model preserved
        assert "brand" in result[0]
        assert "model" in result[0]
        assert "brand" in result[1]
        assert "model" in result[1]

        # Verify values are correct
        assert result[0]["brand"] in ["Rockwell", "Merkur"]
        assert result[1]["brand"] in ["Rockwell", "Merkur"]
        assert result[0]["brand"] != result[1]["brand"]  # Different brands
