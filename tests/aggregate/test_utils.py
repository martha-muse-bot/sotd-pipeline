"""Tests for aggregate utility functions."""

from sotd.aggregate.utils.metrics import (
    calculate_metadata,
    calculate_total_samples,
    calculate_unique_blades,
    calculate_unique_brands,
    calculate_unique_brushes,
    calculate_unique_razors,
    calculate_unique_sample_soaps,
    calculate_unique_soaps,
)


class TestMetrics:
    """Test metric calculation functions."""

    def test_calculate_metadata_basic(self):
        """Test basic metadata calculation."""
        records = [
            {"author": "user1"},
            {"author": "user2"},
            {"author": "user1"},
            {"author": "user3"},
        ]

        meta = calculate_metadata(records, "2025-01")

        assert meta["month"] == "2025-01"
        assert meta["total_shaves"] == 4
        assert meta["unique_shavers"] == 3
        assert meta["avg_shaves_per_user"] == 1.33  # Rounded to 2 decimal places
        assert meta["unique_soaps"] == 0  # No soap data in these records
        assert meta["unique_brands"] == 0  # No soap data in these records
        assert meta["total_samples"] == 0  # No sample data in these records
        assert meta["unique_sample_soaps"] == 0  # No sample data in these records
        assert meta["unique_razors"] == 0  # No razor data in these records
        assert meta["unique_blades"] == 0  # No blade data in these records
        assert meta["unique_brushes"] == 0  # No brush data in these records

    def test_calculate_metadata_empty(self):
        """Test metadata calculation with empty records."""
        meta = calculate_metadata([], "2025-01")

        assert meta["month"] == "2025-01"
        assert meta["total_shaves"] == 0
        assert meta["unique_shavers"] == 0
        assert meta["avg_shaves_per_user"] == 0.0
        assert meta["unique_soaps"] == 0
        assert meta["unique_brands"] == 0
        assert meta["total_samples"] == 0
        assert meta["unique_sample_soaps"] == 0
        assert meta["unique_razors"] == 0
        assert meta["unique_blades"] == 0
        assert meta["unique_brushes"] == 0

    def test_calculate_metadata_single_user(self):
        """Test metadata calculation with single user."""
        records = [
            {"author": "user1"},
            {"author": "user1"},
            {"author": "user1"},
        ]

        meta = calculate_metadata(records, "2025-01")

        assert meta["total_shaves"] == 3
        assert meta["unique_shavers"] == 1
        assert meta["avg_shaves_per_user"] == 3.0
        assert meta["unique_soaps"] == 0
        assert meta["unique_brands"] == 0
        assert meta["total_samples"] == 0
        assert meta["unique_sample_soaps"] == 0
        assert meta["unique_razors"] == 0
        assert meta["unique_blades"] == 0
        assert meta["unique_brushes"] == 0

    def test_calculate_unique_razors_basic(self):
        """Test basic unique razors calculation."""
        records = [
            {
                "author": "user1",
                "razor": {
                    "matched": {"brand": "Gillette", "model": "Super Speed"},
                },
            },
            {
                "author": "user2",
                "razor": {
                    "matched": {"brand": "Gillette", "model": "Super Speed"},
                },
            },
            {
                "author": "user3",
                "razor": {
                    "matched": {"brand": "Merkur", "model": "34C"},
                },
            },
        ]

        unique_razors = calculate_unique_razors(records)
        assert unique_razors == 2  # 2 unique razor combinations

    def test_calculate_unique_razors_no_matches(self):
        """Test unique razors calculation with no matched data."""
        records = [
            {
                "author": "user1",
                "razor": {
                    # No matched section
                },
            },
            {
                "author": "user2",
                "razor": {
                    "matched": {"brand": "Gillette"},  # Missing model
                },
            },
        ]

        unique_razors = calculate_unique_razors(records)
        assert unique_razors == 0

    def test_calculate_unique_blades_basic(self):
        """Test basic unique blades calculation."""
        records = [
            {
                "author": "user1",
                "blade": {
                    "matched": {"brand": "Astra", "model": "Superior Platinum"},
                },
            },
            {
                "author": "user2",
                "blade": {
                    "matched": {"brand": "Astra", "model": "Superior Platinum"},
                },
            },
            {
                "author": "user3",
                "blade": {
                    "matched": {"brand": "Feather", "model": "Hi-Stainless"},
                },
            },
        ]

        unique_blades = calculate_unique_blades(records)
        assert unique_blades == 2  # 2 unique blade combinations

    def test_calculate_unique_blades_no_matches(self):
        """Test unique blades calculation with no matched data."""
        records = [
            {
                "author": "user1",
                "blade": {
                    # No matched section
                },
            },
            {
                "author": "user2",
                "blade": {
                    "matched": {"brand": "Astra"},  # Missing model
                },
            },
        ]

        unique_blades = calculate_unique_blades(records)
        assert unique_blades == 0

    def test_calculate_unique_brushes_basic(self):
        """Test basic unique brushes calculation."""
        records = [
            {
                "author": "user1",
                "brush": {
                    "matched": {"brand": "Simpson", "model": "Chubby 2"},
                },
            },
            {
                "author": "user2",
                "brush": {
                    "matched": {"brand": "Simpson", "model": "Chubby 2"},
                },
            },
            {
                "author": "user3",
                "brush": {
                    "matched": {"brand": "Omega", "model": "10049"},
                },
            },
        ]

        unique_brushes = calculate_unique_brushes(records)
        assert unique_brushes == 2  # 2 unique brush combinations

    def test_calculate_unique_brushes_no_matches(self):
        """Test unique brushes calculation with no matched data."""
        records = [
            {
                "author": "user1",
                "brush": {
                    # No matched section
                },
            },
            {
                "author": "user2",
                "brush": {
                    "matched": {"brand": "Simpson"},  # Missing model
                },
            },
        ]

        unique_brushes = calculate_unique_brushes(records)
        assert unique_brushes == 0

    def test_calculate_unique_soaps_basic(self):
        """Test unique soaps calculation."""
        records = [
            {
                "author": "user1",
                "soap": {"matched": {"brand": "Declaration Grooming", "scent": "Sellout"}},
            },
            {
                "author": "user2",
                "soap": {"matched": {"brand": "Declaration Grooming", "scent": "Sellout"}},
            },
            {
                "author": "user1",
                "soap": {"matched": {"brand": "Stirling", "scent": "Executive Man"}},
            },
        ]

        unique_soaps = calculate_unique_soaps(records)
        assert unique_soaps == 2  # "Declaration Grooming - Sellout" and "Stirling - Executive Man"

    def test_calculate_unique_soaps_no_matches(self):
        """Test unique soaps calculation with no matched soaps."""
        records = [
            {"author": "user1", "soap": {"original": "Unknown Soap"}},
            {
                "author": "user2",
                "soap": {"matched": {"brand": "Declaration Grooming"}},
            },  # Missing scent
        ]

        unique_soaps = calculate_unique_soaps(records)
        assert unique_soaps == 0

    def test_calculate_unique_soaps_empty(self):
        """Test unique soaps calculation with empty records."""
        unique_soaps = calculate_unique_soaps([])
        assert unique_soaps == 0

    def test_calculate_unique_brands_basic(self):
        """Test unique brands calculation."""
        records = [
            {
                "author": "user1",
                "soap": {"matched": {"brand": "Declaration Grooming", "scent": "Sellout"}},
            },
            {
                "author": "user2",
                "soap": {"matched": {"brand": "Declaration Grooming", "scent": "Darkfall"}},
            },
            {
                "author": "user1",
                "soap": {"matched": {"brand": "Stirling", "scent": "Executive Man"}},
            },
        ]

        unique_brands = calculate_unique_brands(records)
        assert unique_brands == 2  # "Declaration Grooming" and "Stirling"

    def test_calculate_unique_brands_no_matches(self):
        """Test unique brands calculation with no matched soaps."""
        records = [
            {"author": "user1", "soap": {"original": "Unknown Soap"}},
            {
                "author": "user2",
                "soap": {"matched": {"scent": "Some Scent"}},
            },  # Missing maker
        ]

        unique_brands = calculate_unique_brands(records)
        assert unique_brands == 0

    def test_calculate_unique_brands_empty(self):
        """Test unique brands calculation with empty records."""
        unique_brands = calculate_unique_brands([])
        assert unique_brands == 0

    def test_calculate_total_samples_basic(self):
        """Test basic total samples calculation."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                },
            },
            {
                "author": "user2",
                "soap": {
                    "enriched": {"sample_type": "tester"},
                },
            },
            {
                "author": "user3",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                },
            },
            {
                "author": "user4",
                "soap": {
                    # No enriched section
                },
            },
        ]

        total_samples = calculate_total_samples(records)
        assert total_samples == 3  # 2 samples + 1 tester

    def test_calculate_total_samples_no_samples(self):
        """Test total samples calculation with no sample data."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "matched": {"brand": "B&M", "scent": "Seville"},
                },
            },
            {
                "author": "user2",
                "soap": {
                    "matched": {"brand": "Declaration Grooming", "scent": "Persephone"},
                },
            },
        ]

        total_samples = calculate_total_samples(records)
        assert total_samples == 0

    def test_calculate_total_samples_empty_records(self):
        """Test total samples calculation with empty records."""
        total_samples = calculate_total_samples([])
        assert total_samples == 0

    def test_calculate_total_samples_missing_soap(self):
        """Test total samples calculation with records missing soap data."""
        records = [
            {"author": "user1"},  # No soap section
            {
                "author": "user2",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                },
            },
        ]

        total_samples = calculate_total_samples(records)
        assert total_samples == 1  # Only the second record has sample data

    def test_calculate_unique_sample_soaps_basic(self):
        """Test basic unique sample soaps calculation."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                    "matched": {"brand": "Declaration Grooming", "scent": "Sellout"},
                },
            },
            {
                "author": "user2",
                "soap": {
                    "enriched": {"sample_type": "tester"},
                    "matched": {"brand": "Stirling", "scent": "Executive Man"},
                },
            },
            {
                "author": "user3",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                    "matched": {"brand": "Declaration Grooming", "scent": "Sellout"},
                },
            },
            {
                "author": "user4",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                    "matched": {"brand": "Declaration Grooming", "scent": "Leviathan"},
                },
            },
        ]

        unique_sample_soaps = calculate_unique_sample_soaps(records)
        assert unique_sample_soaps == 3  # 3 unique brand+scent combinations

    def test_calculate_unique_sample_soaps_no_matches(self):
        """Test unique sample soaps calculation with no matched data."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                    # No matched section
                },
            },
            {
                "author": "user2",
                "soap": {
                    "enriched": {"sample_type": "tester"},
                    "matched": {},  # Empty matched section
                },
            },
        ]

        unique_sample_soaps = calculate_unique_sample_soaps(records)
        assert unique_sample_soaps == 0

    def test_calculate_unique_sample_soaps_empty_records(self):
        """Test unique sample soaps calculation with empty records."""
        unique_sample_soaps = calculate_unique_sample_soaps([])
        assert unique_sample_soaps == 0

    def test_calculate_unique_sample_soaps_missing_soap(self):
        """Test unique sample soaps calculation with records missing soap data."""
        records = [
            {"author": "user1"},  # No soap section
            {
                "author": "user2",
                "soap": {
                    "enriched": {"sample_type": "sample"},
                    "matched": {"brand": "Declaration Grooming", "scent": "Sellout"},
                },
            },
        ]

        unique_sample_soaps = calculate_unique_sample_soaps(records)
        assert unique_sample_soaps == 1  # Only the second record has valid sample data

    def test_calculate_metadata_with_hardware_data(self):
        """Test metadata calculation with hardware data."""
        records = [
            {
                "author": "user1",
                "soap": {
                    "matched": {"brand": "B&M", "scent": "Seville"},
                },
                "razor": {
                    "matched": {"brand": "Gillette", "model": "Super Speed"},
                },
                "blade": {
                    "matched": {"brand": "Astra", "model": "Superior Platinum"},
                },
                "brush": {
                    "matched": {"brand": "Simpson", "model": "Chubby 2"},
                },
            },
            {
                "author": "user2",
                "soap": {
                    "matched": {"brand": "Declaration Grooming", "scent": "B2"},
                },
                "razor": {
                    "matched": {"brand": "Merkur", "model": "34C"},
                },
                "blade": {
                    "matched": {"brand": "Feather", "model": "Hi-Stainless"},
                },
                "brush": {
                    "matched": {"brand": "Omega", "model": "10049"},
                },
            },
        ]

        meta = calculate_metadata(records, "2025-01")

        assert meta["unique_soaps"] == 2  # 2 unique soap combinations
        assert meta["unique_brands"] == 2  # 2 unique soap makers
        assert meta["unique_razors"] == 2  # 2 unique razor combinations
        assert meta["unique_blades"] == 2  # 2 unique blade combinations
        assert meta["unique_brushes"] == 2  # 2 unique brush combinations
