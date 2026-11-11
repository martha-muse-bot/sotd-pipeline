#!/usr/bin/env python3
"""Tests for metrics utility functions."""

from sotd.aggregate.utils.metrics import (
    calculate_avg_shaves_per_user,
    calculate_median_shaves_per_user,
    calculate_shaves,
    calculate_unique_users,
    calculate_unique_soaps,
    calculate_unique_brands,
    calculate_total_samples,
    calculate_sample_users,
    calculate_sample_brands,
    calculate_unique_sample_soaps,
    calculate_total_mashup_shaves,
    calculate_mashup_users,
    calculate_unique_razors,
    calculate_unique_blades,
    calculate_unique_brushes,
    add_rank_field,
    calculate_metadata,
)


class TestBasicMetrics:
    """Test basic metric calculations."""

    def test_calculate_shaves_empty(self):
        """Test shave calculation with empty records."""
        result = calculate_shaves([])
        assert result == 0

    def test_calculate_shaves_with_records(self):
        """Test shave calculation with records."""
        records = [{"author": "user1"}, {"author": "user2"}, {"author": "user3"}]
        result = calculate_shaves(records)
        assert result == 3

    def test_calculate_unique_users_empty(self):
        """Test unique users calculation with empty records."""
        result = calculate_unique_users([])
        assert result == 0

    def test_calculate_unique_users_with_records(self):
        """Test unique users calculation with records."""
        records = [
            {"author": "user1"},
            {"author": "user2"},
            {"author": "user1"},  # Duplicate
            {"author": "user3"},
        ]
        result = calculate_unique_users(records)
        assert result == 3

    def test_calculate_unique_users_ignores_empty_authors(self):
        """Test unique users calculation ignores empty authors."""
        records = [
            {"author": "user1"},
            {"author": ""},  # Empty author
            {"author": None},  # None author
            {"author": "user2"},
            {"author": "   "},  # Whitespace-only author
        ]
        result = calculate_unique_users(records)
        assert result == 2


class TestSoapMetrics:
    """Test soap-related metric calculations."""

    def test_calculate_unique_soaps_empty(self):
        """Test unique soaps calculation with empty records."""
        result = calculate_unique_soaps([])
        assert result == 0

    def test_calculate_unique_soaps_with_valid_data(self):
        """Test unique soaps calculation with valid soap data."""
        records = [
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},
            {"soap": {"matched": {"brand": "Brand2", "scent": "Scent2"}}},
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},  # Duplicate
        ]
        result = calculate_unique_soaps(records)
        assert result == 2

    def test_calculate_unique_soaps_ignores_invalid_data(self):
        """Test unique soaps calculation ignores invalid soap data."""
        records = [
            {"soap": None},  # No soap
            {"soap": {}},  # Empty soap
            {"soap": {"matched": {}}},  # No matched data
            {"soap": {"matched": {"brand": "Brand1"}}},  # No scent
            {"soap": {"matched": {"scent": "Scent1"}}},  # No brand
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},
        ]
        result = calculate_unique_soaps(records)
        assert result == 1

    def test_calculate_unique_soaps_excludes_non_countable(self):
        """Test that non-countable scents are excluded from unique soap counts."""
        records = [
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},  # Countable (default)
            {
                "soap": {"matched": {"brand": "Brand1", "scent": "Tri-Mix", "countable": False}}
            },  # Non-countable
            {"soap": {"matched": {"brand": "Brand2", "scent": "Scent2"}}},  # Countable (default)
            {
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Sample Mashup", "countable": False}
                }
            },  # Non-countable
        ]
        result = calculate_unique_soaps(records)
        # Should only count Brand1-Scent1 and Brand2-Scent2 (2 unique)
        assert result == 2

    def test_calculate_unique_soaps_includes_countable_explicit(self):
        """Test that explicitly countable scents are included."""
        records = [
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1", "countable": True}}},
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent2", "countable": True}}},
        ]
        result = calculate_unique_soaps(records)
        assert result == 2

    def test_calculate_unique_soaps_defaults_to_countable(self):
        """Test that scents without countable flag default to countable (True)."""
        records = [
            {
                "soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}
            },  # No flag, should be countable
            {
                "soap": {"matched": {"brand": "Brand1", "scent": "Scent2"}}
            },  # No flag, should be countable
        ]
        result = calculate_unique_soaps(records)
        # Both should be counted
        assert result == 2

    def test_calculate_unique_soaps_excludes_mashups(self):
        """Test that mashups are excluded from unique soap counts."""
        records = [
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}, "enriched": {}}},
            {
                "soap": {
                    "matched": {"brand": "Stirling Soap Co.", "scent": "Sample Mash Up"},
                    "enriched": {"is_mashup": True},
                }
            },
            {
                "soap": {
                    "matched": {"brand": "Brand2", "scent": "Scent2"},
                    "enriched": {"is_mashup": False},
                }
            },
        ]
        result = calculate_unique_soaps(records)
        assert result == 2

    def test_calculate_unique_brands_empty(self):
        """Test unique brands calculation with empty records."""
        result = calculate_unique_brands([])
        assert result == 0

    def test_calculate_unique_brands_with_valid_data(self):
        """Test unique brands calculation with valid soap data."""
        records = [
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},
            {"soap": {"matched": {"brand": "Brand2", "scent": "Scent2"}}},
            {
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent3"}  # Same brand, different scent
                }
            },
        ]
        result = calculate_unique_brands(records)
        assert result == 2

    def test_calculate_unique_brands_ignores_invalid_data(self):
        """Test unique brands calculation ignores invalid soap data."""
        records = [
            {"soap": None},  # No soap
            {"soap": {}},  # Empty soap
            {"soap": {"matched": {}}},  # No matched data
            {"soap": {"matched": {"scent": "Scent1"}}},  # No brand
            {"soap": {"matched": {"brand": "Brand1", "scent": "Scent1"}}},
        ]
        result = calculate_unique_brands(records)
        assert result == 1


class TestSampleMetrics:
    """Test sample-related metric calculations."""

    def test_calculate_total_samples_empty(self):
        """Test total samples calculation with empty records."""
        result = calculate_total_samples([])
        assert result == 0

    def test_calculate_total_samples_with_valid_data(self):
        """Test total samples calculation with valid sample data."""
        records = [
            {"soap": {"enriched": {"sample_type": "sample"}}},
            {"soap": {"enriched": {"sample_type": "travel"}}},
            {"soap": {"enriched": {"sample_type": "sample"}}},
            {"soap": {"enriched": {}}},  # No sample type
            {"soap": None},  # No soap
        ]
        result = calculate_total_samples(records)
        assert result == 3

    def test_calculate_sample_users_empty(self):
        """Test sample users calculation with empty records."""
        result = calculate_sample_users([])
        assert result == 0

    def test_calculate_sample_users_with_valid_data(self):
        """Test sample users calculation with valid sample data."""
        records = [
            {"author": "user1", "soap": {"enriched": {"sample_type": "sample"}}},
            {"author": "user2", "soap": {"enriched": {"sample_type": "travel"}}},
            {
                "author": "user1",  # Same user, different sample
                "soap": {"enriched": {"sample_type": "sample"}},
            },
            {"author": "user3", "soap": {"enriched": {}}},  # No sample type
        ]
        result = calculate_sample_users(records)
        assert result == 2

    def test_calculate_sample_brands_empty(self):
        """Test sample brands calculation with empty records."""
        result = calculate_sample_brands([])
        assert result == 0

    def test_calculate_sample_brands_with_valid_data(self):
        """Test sample brands calculation with valid sample data."""
        records = [
            {"soap": {"matched": {"brand": "Brand1"}, "enriched": {"sample_type": "sample"}}},
            {"soap": {"matched": {"brand": "Brand2"}, "enriched": {"sample_type": "travel"}}},
            {
                "soap": {
                    "matched": {"brand": "Brand1"},  # Same brand, different sample
                    "enriched": {"sample_type": "sample"},
                }
            },
            {"soap": {"matched": {"brand": "Brand3"}, "enriched": {"sample_type": "sample"}}},
        ]
        result = calculate_sample_brands(records)
        assert result == 3  # All brands are counted, function doesn't check sample_type

    def test_calculate_unique_sample_soaps_empty(self):
        """Test unique sample soaps calculation with empty records."""
        result = calculate_unique_sample_soaps([])
        assert result == 0

    def test_calculate_unique_sample_soaps_with_valid_data(self):
        """Test unique sample soaps calculation with valid sample data."""
        records = [
            {
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent1"},
                    "enriched": {"sample_type": "sample"},
                }
            },
            {
                "soap": {
                    "matched": {"brand": "Brand2", "scent": "Scent2"},
                    "enriched": {"sample_type": "travel"},
                }
            },
            {
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent1"},  # Duplicate
                    "enriched": {"sample_type": "sample"},
                }
            },
            {
                "soap": {
                    "matched": {"brand": "Brand3", "scent": "Scent3"},
                    "enriched": {},  # No sample type
                }
            },
        ]
        result = calculate_unique_sample_soaps(records)
        assert result == 2


class TestMashupMetrics:
    """Test mashup-related metric calculations (soap.enriched.is_mashup)."""

    def test_calculate_total_mashup_shaves_empty(self):
        """Test total mashup shaves with empty records."""
        result = calculate_total_mashup_shaves([])
        assert result == 0

    def test_calculate_total_mashup_shaves_with_valid_data(self):
        """Test total mashup shaves with is_mashup in enriched."""
        records = [
            {
                "soap": {
                    "matched": {"brand": "Mama Bear", "scent": "Sample Mashup", "countable": False},
                    "enriched": {"is_mashup": True},
                },
            },
            {"soap": {"matched": {"brand": "B&M", "scent": "Seville"}, "enriched": {}}},
            {
                "soap": {
                    "original": "soap mashup",
                    "normalized": "soap mashup",
                    "enriched": {"is_mashup": True},
                }
            },
        ]
        result = calculate_total_mashup_shaves(records)
        assert result == 2

    def test_calculate_mashup_users_empty(self):
        """Test mashup users with empty records."""
        result = calculate_mashup_users([])
        assert result == 0

    def test_calculate_mashup_users_with_valid_data(self):
        """Test mashup users with is_mashup in enriched."""
        records = [
            {"author": "user1", "soap": {"enriched": {"is_mashup": True}}},
            {"author": "user2", "soap": {"enriched": {"is_mashup": True}}},
            {"author": "user1", "soap": {"enriched": {"is_mashup": True}}},
        ]
        result = calculate_mashup_users(records)
        assert result == 2


class TestHardwareMetrics:
    """Test hardware-related metric calculations."""

    def test_calculate_unique_razors_empty(self):
        """Test unique razors calculation with empty records."""
        result = calculate_unique_razors([])
        assert result == 0

    def test_calculate_unique_razors_with_valid_data(self):
        """Test unique razors calculation with valid razor data."""
        records = [
            {"razor": {"matched": {"brand": "Brand1", "model": "Model1"}}},
            {"razor": {"matched": {"brand": "Brand2", "model": "Model2"}}},
            {"razor": {"matched": {"brand": "Brand1", "model": "Model1"}}},  # Duplicate
        ]
        result = calculate_unique_razors(records)
        assert result == 2

    def test_calculate_unique_razors_ignores_invalid_data(self):
        """Test unique razors calculation ignores invalid razor data."""
        records = [
            {"razor": None},  # No razor
            {"razor": {}},  # Empty razor
            {"razor": {"matched": {}}},  # No matched data
            {"razor": {"matched": {"brand": "Brand1"}}},  # No model
            {"razor": {"matched": {"model": "Model1"}}},  # No brand
            {"razor": {"matched": {"brand": "Brand1", "model": "Model1"}}},
        ]
        result = calculate_unique_razors(records)
        assert result == 1

    def test_calculate_unique_blades_empty(self):
        """Test unique blades calculation with empty records."""
        result = calculate_unique_blades([])
        assert result == 0

    def test_calculate_unique_blades_with_valid_data(self):
        """Test unique blades calculation with valid blade data."""
        records = [
            {"blade": {"matched": {"brand": "Brand1", "model": "Model1"}}},
            {"blade": {"matched": {"brand": "Brand2", "model": "Model2"}}},
            {"blade": {"matched": {"brand": "Brand1", "model": "Model1"}}},  # Duplicate
        ]
        result = calculate_unique_blades(records)
        assert result == 2

    def test_calculate_unique_brushes_empty(self):
        """Test unique brushes calculation with empty records."""
        result = calculate_unique_brushes([])
        assert result == 0

    def test_calculate_unique_brushes_with_valid_data(self):
        """Test unique brushes calculation with valid brush data."""
        records = [
            {"brush": {"matched": {"brand": "Brand1", "model": "Model1"}}},
            {"brush": {"matched": {"brand": "Brand2", "model": "Model2"}}},
            {"brush": {"matched": {"brand": "Brand1", "model": "Model1"}}},  # Duplicate
        ]
        result = calculate_unique_brushes(records)
        assert result == 2


class TestUtilityFunctions:
    """Test utility functions."""

    def test_add_rank_field_empty(self):
        """Test adding rank field to empty list."""
        result = add_rank_field([])
        assert result == []

    def test_add_rank_field_with_items(self):
        """Test adding rank field to items."""
        items = [{"name": "Item1"}, {"name": "Item2"}, {"name": "Item3"}]
        result = add_rank_field(items)
        assert len(result) == 3
        assert result[0]["rank"] == 1
        assert result[1]["rank"] == 2
        assert result[2]["rank"] == 3

    def test_add_rank_field_modifies_original(self):
        """Test that add_rank_field modifies the original items."""
        items = [{"name": "Item1"}, {"name": "Item2"}]
        result = add_rank_field(items)
        assert result is items  # Same object reference
        assert items[0]["rank"] == 1
        assert items[1]["rank"] == 2


class TestMetadataCalculation:
    """Test metadata calculation."""

    def test_calculate_metadata_empty(self):
        """Test metadata calculation with empty records."""
        result = calculate_metadata([], "2025-01")
        assert result["month"] == "2025-01"
        assert result["total_shaves"] == 0
        assert result["unique_shavers"] == 0
        assert result["avg_shaves_per_user"] == 0.0
        assert result["median_shaves_per_user"] == 0.0
        assert result["unique_soaps"] == 0
        assert result["unique_brands"] == 0
        assert result["total_samples"] == 0
        assert result["sample_users"] == 0
        assert result["sample_brands"] == 0
        assert result["unique_sample_soaps"] == 0
        assert result["total_mashup_shaves"] == 0
        assert result["mashup_users"] == 0
        assert result["mashup_percentage"] == 0.0
        assert result["unique_razors"] == 0
        assert result["unique_blades"] == 0
        assert result["unique_brushes"] == 0

    def test_calculate_metadata_with_records(self):
        """Test metadata calculation with sample records."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent1"},
                    "enriched": {"sample_type": "sample"},
                },
                "razor": {"matched": {"brand": "Razor1", "model": "Model1"}},
                "blade": {"matched": {"brand": "Blade1", "model": "Model1"}},
                "brush": {"matched": {"brand": "Brush1", "model": "Model1"}},
            },
            {
                "author": "user2",
                "soap": {"matched": {"brand": "Brand2", "scent": "Scent2"}},
                "razor": {"matched": {"brand": "Razor2", "model": "Model2"}},
                "blade": {"matched": {"brand": "Blade2", "model": "Model2"}},
                "brush": {"matched": {"brand": "Brush2", "model": "Model2"}},
            },
        ]
        result = calculate_metadata(records, "2025-01")
        assert result["month"] == "2025-01"
        assert result["total_shaves"] == 2
        assert result["unique_shavers"] == 2
        assert result["avg_shaves_per_user"] == 1.0
        assert result["median_shaves_per_user"] == 1.0
        assert result["unique_soaps"] == 2
        assert result["unique_brands"] == 2
        assert result["total_samples"] == 1
        assert result["sample_users"] == 1
        assert result["sample_brands"] == 1
        assert result["unique_sample_soaps"] == 1
        assert result["total_mashup_shaves"] == 0
        assert result["mashup_users"] == 0
        assert result["mashup_percentage"] == 0.0
        assert result["unique_razors"] == 2
        assert result["unique_blades"] == 2
        assert result["unique_brushes"] == 2


class TestUserMetrics:
    """Test user-related metric calculations."""

    def test_calculate_avg_shaves_per_user_empty(self):
        """Test average calculation with empty records."""
        result = calculate_avg_shaves_per_user([])
        assert result == 0.0

    def test_calculate_avg_shaves_per_user_single_user(self):
        """Test average calculation with single user."""
        records = [
            {"author": "user1"},
            {"author": "user1"},
            {"author": "user1"},
        ]
        result = calculate_avg_shaves_per_user(records)
        assert result == 3.0

    def test_calculate_avg_shaves_per_user_multiple_users(self):
        """Test average calculation with multiple users."""
        records = [
            {"author": "user1"},
            {"author": "user1"},
            {"author": "user2"},
            {"author": "user3"},
        ]
        result = calculate_avg_shaves_per_user(records)
        assert result == 1.33  # 4 shaves / 3 users

    def test_calculate_median_shaves_per_user_empty(self):
        """Test median calculation with empty records."""
        result = calculate_median_shaves_per_user([])
        assert result == 0.0

    def test_calculate_median_shaves_per_user_single_user(self):
        """Test median calculation with single user."""
        records = [
            {"author": "user1"},
            {"author": "user1"},
            {"author": "user1"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 3.0

    def test_calculate_median_shaves_per_user_odd_users(self):
        """Test median calculation with odd number of users."""
        records = [
            {"author": "user1"},  # 1 shave
            {"author": "user2"},  # 1 shave
            {"author": "user3"},  # 1 shave
            {"author": "user4"},  # 2 shaves
            {"author": "user4"},
            {"author": "user5"},  # 3 shaves
            {"author": "user5"},
            {"author": "user5"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 1.0  # Median of [1, 1, 1, 2, 3] is 1

    def test_calculate_median_shaves_per_user_even_users(self):
        """Test median calculation with even number of users."""
        records = [
            {"author": "user1"},  # 1 shave
            {"author": "user2"},  # 1 shave
            {"author": "user3"},  # 2 shaves
            {"author": "user3"},
            {"author": "user4"},  # 3 shaves
            {"author": "user4"},
            {"author": "user4"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 1.5  # Median of [1, 1, 2, 3] is (1+2)/2 = 1.5

    def test_calculate_median_shaves_per_user_mixed_shaves(self):
        """Test median calculation with mixed shave counts."""
        records = [
            {"author": "user1"},  # 1 shave
            {"author": "user2"},  # 2 shaves
            {"author": "user2"},
            {"author": "user3"},  # 3 shaves
            {"author": "user3"},
            {"author": "user3"},
            {"author": "user4"},  # 4 shaves
            {"author": "user4"},
            {"author": "user4"},
            {"author": "user4"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 2.5  # Median of [1, 2, 3, 4] is (2+3)/2 = 2.5

    def test_calculate_median_shaves_per_user_ignores_empty_authors(self):
        """Test median calculation ignores records with empty authors."""
        records = [
            {"author": "user1"},
            {"author": ""},  # Empty author
            {"author": None},  # None author
            {"author": "user2"},
            {"author": "user2"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 1.5  # Median of [1, 2] is (1+2)/2 = 1.5

    def test_calculate_median_shaves_per_user_rounds_to_two_decimals(self):
        """Test median calculation rounds to two decimal places."""
        records = [
            {"author": "user1"},  # 1 shave
            {"author": "user2"},  # 2 shaves
            {"author": "user2"},
            {"author": "user3"},  # 3 shaves
            {"author": "user3"},
            {"author": "user3"},
        ]
        result = calculate_median_shaves_per_user(records)
        assert result == 2.0  # Median of [1, 2, 3] is 2.0


class TestMetadataNoDataFrame:
    """Metadata calculation must not build pandas DataFrames.

    The helpers used to construct a full pd.DataFrame(records) per metric
    and iterrows() it (9 builds per calculate_metadata call); on a 25k-record
    month that cost ~7.2s, dominated by iterrows. They now iterate the
    records directly and dedupe with sets (~0.2s on the same month).
    """

    def test_calculate_metadata_builds_no_dataframes(self, monkeypatch):
        import pandas as pd

        def _no_dataframe(*args, **kwargs):
            raise AssertionError("calculate_metadata must not construct a DataFrame")

        monkeypatch.setattr(pd, "DataFrame", _no_dataframe)
        records = [
            {
                "author": "user1",
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent1"},
                    "enriched": {"sample_type": "sample"},
                },
                "razor": {"matched": {"brand": "Razor1", "model": "Model1"}},
                "blade": {"matched": {"brand": "Blade1", "model": "Model1"}},
                "brush": {"matched": {"brand": "Brush1", "model": "Model1"}},
            },
            {
                "author": "user2",
                "soap": {
                    "matched": {"brand": "Brand1", "scent": "Scent1"},
                    "enriched": {"is_mashup": True},
                },
                "razor": {"matched": {"brand": "Razor1", "model": "Model1"}},
                "blade": {"matched": {"brand": "Blade1", "model": "Model1"}},
                "brush": {"matched": {"brand": "Brush1", "model": "Model1"}},
            },
        ]
        result = calculate_metadata(records, "2025-01")
        assert result["total_shaves"] == 2
        assert result["unique_shavers"] == 2
        assert result["unique_soaps"] == 1
        assert result["unique_brands"] == 1
        assert result["total_samples"] == 1
        assert result["sample_users"] == 1
        assert result["sample_brands"] == 1
        assert result["unique_sample_soaps"] == 1
        assert result["total_mashup_shaves"] == 1
        assert result["mashup_users"] == 1
        assert result["unique_razors"] == 1
        assert result["unique_blades"] == 1
        assert result["unique_brushes"] == 1
