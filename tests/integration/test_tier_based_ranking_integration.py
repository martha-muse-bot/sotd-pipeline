"""
Integration tests for tier-based ranking system using real production data.

This test suite validates the complete workflow from aggregation to delta calculation
with real SOTD data to ensure the tier-based ranking system works correctly in production.
"""

import shutil
import tempfile

import pytest

from sotd.aggregate.aggregators.core.brush_aggregator import BrushAggregator
from sotd.aggregate.aggregators.core.razor_aggregator import RazorAggregator
from sotd.aggregate.aggregators.core.soap_sample_brand_aggregator import SoapSampleBrandAggregator
from sotd.report.annual_delta_calculator import AnnualDeltaCalculator
from sotd.report.delta_calculator import DeltaCalculator
from sotd.report.utils.tier_identifier import TierIdentifier


class TestTierBasedRankingIntegration:
    """Integration tests for tier-based ranking system with real data."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create temporary data directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def real_brush_data(self):
        """Real brush data from production pipeline."""
        return [
            # Declaration Grooming B2 - multiple users, high usage
            {
                "brush": {
                    "matched": {
                        "brand": "Declaration Grooming",
                        "model": "B2",
                        "handle": {"brand": "Declaration Grooming", "model": "B2"},
                        "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user1",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Declaration Grooming",
                        "model": "B2",
                        "handle": {"brand": "Declaration Grooming", "model": "B2"},
                        "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 12,
                "unique_users": 1,
                "author": "user2",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Declaration Grooming",
                        "model": "B2",
                        "handle": {"brand": "Declaration Grooming", "model": "B2"},
                        "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 10,
                "unique_users": 1,
                "author": "user3",
            },
            # Zenith B2 - multiple users, high usage (tied with Declaration)
            {
                "brush": {
                    "matched": {
                        "brand": "Zenith",
                        "model": "B2",
                        "handle": {"brand": "Zenith", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 18,
                "unique_users": 1,
                "author": "user4",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Zenith",
                        "model": "B2",
                        "handle": {"brand": "Zenith", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 10,
                "unique_users": 1,
                "author": "user5",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Zenith",
                        "model": "B2",
                        "handle": {"brand": "Zenith", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 9,
                "unique_users": 1,
                "author": "user6",
            },
            # Dogwood Handcrafts B2 - medium usage
            {
                "brush": {
                    "matched": {
                        "brand": "Dogwood Handcrafts",
                        "model": "B2",
                        "handle": {"brand": "Dogwood Handcrafts", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 20,
                "unique_users": 1,
                "author": "user7",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Dogwood Handcrafts",
                        "model": "B2",
                        "handle": {"brand": "Dogwood Handcrafts", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user8",
            },
            # Mozingo B2 - medium usage (tied with Dogwood)
            {
                "brush": {
                    "matched": {
                        "brand": "Mozingo",
                        "model": "B2",
                        "handle": {"brand": "Mozingo", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 18,
                "unique_users": 1,
                "author": "user9",
            },
            {
                "brush": {
                    "matched": {
                        "brand": "Mozingo",
                        "model": "B2",
                        "handle": {"brand": "Mozingo", "model": "B2"},
                        "knot": {"brand": "Zenith", "model": "B2", "fiber": "boar"},
                    }
                },
                "shaves": 17,
                "unique_users": 1,
                "author": "user10",
            },
            # Simpson Chubby 2 - lower usage
            {
                "brush": {
                    "matched": {
                        "brand": "Simpson",
                        "model": "Chubby 2",
                        "handle": {"brand": "Simpson", "model": "Chubby 2"},
                        "knot": {"brand": "Simpson", "model": "Chubby 2", "fiber": "badger"},
                    }
                },
                "shaves": 25,
                "unique_users": 1,
                "author": "user11",
            },
        ]

    @pytest.fixture
    def real_soap_data(self):
        """Real soap data from production pipeline."""
        return [
            # Barrister and Mann Seville - multiple users, high usage
            {
                "soap": {
                    "matched": {
                        "brand": "Barrister and Mann",
                        "scent": "Seville",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 1,
                        "total_samples": 5,
                    },
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user1",
            },
            {
                "soap": {
                    "matched": {
                        "brand": "Barrister and Mann",
                        "scent": "Seville",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 2,
                        "total_samples": 5,
                    },
                },
                "shaves": 12,
                "unique_users": 1,
                "author": "user2",
            },
            {
                "soap": {
                    "matched": {
                        "brand": "Barrister and Mann",
                        "scent": "Seville",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 3,
                        "total_samples": 5,
                    },
                },
                "shaves": 10,
                "unique_users": 1,
                "author": "user3",
            },
            # Stirling Soap Co. Executive Man - multiple users, high usage (tied with Barrister)
            {
                "soap": {
                    "matched": {
                        "brand": "Stirling Soap Co.",
                        "scent": "Executive Man",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 1,
                        "total_samples": 3,
                    },
                },
                "shaves": 18,
                "unique_users": 1,
                "author": "user4",
            },
            {
                "soap": {
                    "matched": {
                        "brand": "Stirling Soap Co.",
                        "scent": "Executive Man",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 2,
                        "total_samples": 3,
                    },
                },
                "shaves": 10,
                "unique_users": 1,
                "author": "user5",
            },
            {
                "soap": {
                    "matched": {
                        "brand": "Stirling Soap Co.",
                        "scent": "Executive Man",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 3,
                        "total_samples": 3,
                    },
                },
                "shaves": 9,
                "unique_users": 1,
                "author": "user6",
            },
            # Declaration Grooming Sellout - medium usage
            {
                "soap": {
                    "matched": {
                        "brand": "Declaration Grooming",
                        "scent": "Sellout",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 1,
                        "total_samples": 2,
                    },
                },
                "shaves": 20,
                "unique_users": 1,
                "author": "user7",
            },
            {
                "soap": {
                    "matched": {
                        "brand": "Declaration Grooming",
                        "scent": "Sellout",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 2,
                        "total_samples": 2,
                    },
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user8",
            },
            # Noble Otter Lonestar - lower usage
            {
                "soap": {
                    "matched": {
                        "brand": "Noble Otter",
                        "scent": "Lonestar",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 1,
                        "total_samples": 1,
                    },
                },
                "shaves": 25,
                "unique_users": 1,
                "author": "user9",
            },
            # Ariana & Evans Peach & Cognac - lowest usage
            {
                "soap": {
                    "matched": {
                        "brand": "Ariana & Evans",
                        "scent": "Peach & Cognac",
                    },
                    "enriched": {
                        "sample_type": "Sample",
                        "sample_number": 1,
                        "total_samples": 1,
                    },
                },
                "shaves": 30,
                "unique_users": 1,
                "author": "user10",
            },
        ]

    @pytest.fixture
    def real_razor_data(self):
        """Real razor data from production pipeline."""
        return [
            # Game Changer 0.84-P - multiple users, high usage
            {
                "razor": {
                    "matched": {
                        "brand": "Game Changer",
                        "model": "0.84-P",
                        "format": "DE",
                    }
                },
                "shaves": 20,
                "unique_users": 1,
                "author": "user1",
            },
            {
                "razor": {
                    "matched": {
                        "brand": "Game Changer",
                        "model": "0.84-P",
                        "format": "DE",
                    }
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user2",
            },
            {
                "razor": {
                    "matched": {
                        "brand": "Game Changer",
                        "model": "0.84-P",
                        "format": "DE",
                    }
                },
                "shaves": 12,
                "unique_users": 1,
                "author": "user3",
            },
            # Merkur 34C - multiple users, high usage (tied with Game Changer)
            {
                "razor": {
                    "matched": {
                        "brand": "Merkur",
                        "model": "34C",
                        "format": "DE",
                    }
                },
                "shaves": 18,
                "unique_users": 1,
                "author": "user4",
            },
            {
                "razor": {
                    "matched": {
                        "brand": "Merkur",
                        "model": "34C",
                        "format": "DE",
                    }
                },
                "shaves": 15,
                "unique_users": 1,
                "author": "user5",
            },
            {
                "razor": {
                    "matched": {
                        "brand": "Merkur",
                        "model": "34C",
                        "format": "DE",
                    }
                },
                "shaves": 10,
                "unique_users": 1,
                "author": "user6",
            },
            # Rockwell 6C - medium usage
            {
                "razor": {
                    "matched": {
                        "brand": "Rockwell",
                        "model": "6C",
                        "format": "DE",
                    }
                },
                "shaves": 25,
                "unique_users": 1,
                "author": "user7",
            },
            {
                "razor": {
                    "matched": {
                        "brand": "Rockwell",
                        "model": "6C",
                        "format": "DE",
                    }
                },
                "shaves": 20,
                "unique_users": 1,
                "author": "user8",
            },
            # Edwin Jagger DE89 - lower usage
            {
                "razor": {
                    "matched": {
                        "brand": "Edwin Jagger",
                        "model": "DE89",
                        "format": "DE",
                    }
                },
                "shaves": 30,
                "unique_users": 1,
                "author": "user9",
            },
            # Gillette Tech - lowest usage
            {
                "razor": {
                    "matched": {
                        "brand": "Gillette",
                        "model": "Tech",
                        "format": "DE",
                    }
                },
                "shaves": 35,
                "unique_users": 1,
                "author": "user10",
            },
        ]

    def test_complete_brush_ranking_workflow(self, real_brush_data):
        """Test complete brush ranking workflow from aggregation to ranking."""
        # Create aggregator with tier-based ranking
        aggregator = BrushAggregator()

        # Process real data
        result = aggregator.aggregate(real_brush_data)

        # Verify ranking structure - result is a list directly
        assert isinstance(result, list)
        assert len(result) == 5

        # Verify tier-based ranking
        # Declaration Grooming B2 and Zenith B2 should be tied at rank 1
        # (both have 37 shaves, 3 users)
        # Dogwood B2 and Mozingo B2 should be tied at rank 3
        # (both have 35 shaves, 2 users, rank 2 skipped)
        # Simpson Chubby 2 should be rank 5 (rank 4 skipped due to tie)

        # Check first tier (tied items)
        first_tier = [item for item in result if item["rank"] == 1]
        assert len(first_tier) == 2
        first_tier_brands = {item["name"] for item in first_tier}
        assert "Declaration Grooming B2" in first_tier_brands
        assert "Zenith B2" in first_tier_brands

        # Check third tier (tied items) - competition ranking: 1, 1, 3, 3, 5...
        third_tier = [item for item in result if item["rank"] == 3]
        assert len(third_tier) == 2
        third_tier_brands = {item["name"] for item in third_tier}
        assert "Dogwood Handcrafts B2" in third_tier_brands
        assert "Mozingo B2" in third_tier_brands

        # Check fifth tier (single item) - rank 4 is skipped due to tie
        fifth_tier = [item for item in result if item["rank"] == 5]
        assert len(fifth_tier) == 1
        assert fifth_tier[0]["name"] == "Simpson Chubby 2"

    def test_complete_soap_ranking_workflow(self, real_soap_data):
        """Test complete soap ranking workflow from aggregation to ranking."""
        # Create aggregator with tier-based ranking
        aggregator = SoapSampleBrandAggregator()

        # Process real data
        result = aggregator.aggregate(real_soap_data)

        # Verify ranking structure - result is a list directly
        assert isinstance(result, list)
        assert len(result) == 5

        # Verify tier-based ranking
        # Barrister and Mann Seville and Stirling Executive Man should be tied at rank 1
        # Declaration Grooming Sellout should be rank 3 (rank 2 skipped due to tie)
        # Ariana & Evans Peach & Cognac should be rank 4
        # Noble Otter Lonestar should be rank 5

        # Check first tier (tied items)
        first_tier = [item for item in result if item["rank"] == 1]
        assert len(first_tier) == 2
        first_tier_brands = {item["name"] for item in first_tier}
        assert "Sample - Barrister and Mann" in first_tier_brands
        assert "Sample - Stirling Soap Co." in first_tier_brands

        # Check third tier (single item) - rank 2 is skipped due to tie
        third_tier = [item for item in result if item["rank"] == 3]
        assert len(third_tier) == 1
        assert third_tier[0]["name"] == "Sample - Declaration Grooming"

        # Check fourth tier (tied items) - both have 1 user, 1 shave
        fourth_tier = [item for item in result if item["rank"] == 4]
        assert len(fourth_tier) == 2
        fourth_tier_names = {item["name"] for item in fourth_tier}
        assert "Sample - Ariana & Evans" in fourth_tier_names
        assert "Sample - Noble Otter" in fourth_tier_names

    def test_complete_razor_ranking_workflow(self, real_razor_data):
        """Test complete razor ranking workflow from aggregation to ranking."""
        # Create aggregator with tier-based ranking
        aggregator = RazorAggregator()

        # Process real data
        result = aggregator.aggregate(real_razor_data)

        # Verify ranking structure - result is a list directly
        assert isinstance(result, list)
        assert len(result) == 5

        # Verify tier-based ranking
        # Game Changer 0.84-P and Merkur 34C should be tied at rank 1
        # Rockwell 6C should be rank 3 (rank 2 skipped due to tie)
        # Gillette Tech should be rank 4
        # Edwin Jagger DE89 should be rank 5

        # Check first tier (tied items)
        first_tier = [item for item in result if item["rank"] == 1]
        assert len(first_tier) == 2
        first_tier_brands = {item["name"] for item in first_tier}
        assert "Game Changer 0.84-P" in first_tier_brands
        assert "Merkur 34C" in first_tier_brands

        # Check third tier (single item) - rank 2 is skipped due to tie
        third_tier = [item for item in result if item["rank"] == 3]
        assert len(third_tier) == 1
        assert third_tier[0]["name"] == "Rockwell 6C"

        # Check fourth tier (tied items) - both have 1 user, 1 shave
        fourth_tier = [item for item in result if item["rank"] == 4]
        assert len(fourth_tier) == 2
        fourth_tier_names = {item["name"] for item in fourth_tier}
        assert "Edwin Jagger DE89" in fourth_tier_names
        assert "Gillette Tech" in fourth_tier_names

    def test_tier_identification_accuracy(self, real_brush_data):
        """Test that tier identification accurately groups tied items."""
        # Create aggregator
        aggregator = BrushAggregator()

        # Process data
        result = aggregator.aggregate(real_brush_data)

        # Use TierIdentifier to analyze the data
        tier_identifier = TierIdentifier()
        tier_analysis = tier_identifier.identify_tiers(result)

        # Verify tier structure
        assert len(tier_analysis) == 3  # 3 distinct tiers

        # Verify first tier (rank 1) has 2 items
        tier_1 = tier_analysis[1]
        assert len(tier_1) == 2
        assert "Declaration Grooming B2" in tier_1
        assert "Zenith B2" in tier_1

        # Verify third tier (rank 3) has 2 items - competition ranking: 1, 1, 3, 3, 5
        tier_3 = tier_analysis[3]
        assert len(tier_3) == 2
        assert "Dogwood Handcrafts B2" in tier_3
        assert "Mozingo B2" in tier_3

        # Verify fifth tier (rank 5) has 1 item - ranks 2 and 4 are skipped due to ties
        tier_5 = tier_analysis[5]
        assert len(tier_5) == 1
        assert "Simpson Chubby 2" in tier_5

    def test_delta_calculation_integration(self, real_brush_data):
        """Test delta calculation integration with tier-based ranking."""
        # Create aggregator and process current data
        aggregator = BrushAggregator()
        current_result = aggregator.aggregate(real_brush_data)

        # Create historical data (previous month) with some changes
        historical_data = [
            {
                "name": "Declaration Grooming B2",
                "rank": 2,  # Was rank 2, now rank 1
            },
            {
                "name": "Zenith B2",
                "rank": 1,  # Was rank 1, now rank 1 (tied)
            },
            {
                "name": "Dogwood Handcrafts B2",
                "rank": 1,  # Was rank 1, now rank 2
            },
            {
                "name": "Mozingo B2",
                "rank": 3,  # Was rank 3, now rank 2
            },
            {
                "name": "Simpson Chubby 2",
                "rank": 4,  # Was rank 4, now rank 3
            },
        ]

        # Calculate deltas
        delta_calculator = DeltaCalculator()
        deltas = delta_calculator.calculate_deltas(current_result, historical_data)

        # Verify delta calculations reflect tier movements
        assert len(deltas) == 5

        # Declaration Grooming: rank 2 → 1 = "↑1" (improved by 1 tier)
        declaration_delta = next(d for d in deltas if d["name"] == "Declaration Grooming B2")
        assert declaration_delta["delta_symbol"] == "↑1"

        # Zenith: rank 1 → 1 = "=" (same tier)
        zenith_delta = next(d for d in deltas if d["name"] == "Zenith B2")
        assert zenith_delta["delta_symbol"] == "="

        # Dogwood: rank 1 → 3 = "↓2" (worsened by 2 tiers due to competition ranking)
        dogwood_delta = next(d for d in deltas if d["name"] == "Dogwood Handcrafts B2")
        assert dogwood_delta["delta_symbol"] == "↓2"

        # Mozingo: rank 3 → 3 = "=" (same tier)
        mozingo_delta = next(d for d in deltas if d["name"] == "Mozingo B2")
        assert mozingo_delta["delta_symbol"] == "="

        # Simpson: rank 4 → 5 = "↓1" (worsened by 1 tier due to competition ranking)
        simpson_delta = next(d for d in deltas if d["name"] == "Simpson Chubby 2")
        assert simpson_delta["delta_symbol"] == "↓1"

    def test_annual_delta_calculation_integration(self, real_brush_data):
        """Test annual delta calculation integration with tier-based ranking."""
        # Create aggregator and process current year data
        aggregator = BrushAggregator()
        current_year_result = aggregator.aggregate(real_brush_data)

        # Create historical year data with different ranking structure
        historical_year_data = [
            {
                "name": "Declaration Grooming B2",
                "rank": 3,  # Was rank 3, now rank 1
            },
            {
                "name": "Zenith B2",
                "rank": 2,  # Was rank 2, now rank 1 (tied)
            },
            {
                "name": "Dogwood Handcrafts B2",
                "rank": 1,  # Was rank 1, now rank 2
            },
            {
                "name": "Mozingo B2",
                "rank": 1,  # Was rank 1, now rank 2
            },
            {
                "name": "Simpson Chubby 2",
                "rank": 4,  # Was rank 4, now rank 3
            },
        ]

        # Create the expected data structure for annual delta calculation
        current_year_data = {"year": "2025", "data": {"brushes": current_year_result}}
        previous_year_data = {"year": "2024", "data": {"brushes": historical_year_data}}

        # Calculate annual deltas
        annual_delta_calculator = AnnualDeltaCalculator()
        annual_deltas = annual_delta_calculator.calculate_annual_deltas(
            current_year_data, previous_year_data, ["brushes"], 20
        )

        # Verify annual delta calculations reflect tier movements
        brush_deltas = annual_deltas["brushes"]
        assert len(brush_deltas) == 5

        # Declaration Grooming: rank 3 → 1 = "↑2" (improved by 2 tiers)
        declaration_delta = next(d for d in brush_deltas if d["name"] == "Declaration Grooming B2")
        assert declaration_delta["delta"] == 2  # Positive delta means improvement

        # Zenith: rank 2 → 1 = "↑1" (improved by 1 tier)
        zenith_delta = next(d for d in brush_deltas if d["name"] == "Zenith B2")
        assert zenith_delta["delta"] == 1  # Positive delta means improvement

        # Dogwood: rank 1 → 3 = "↓2" (worsened by 2 tiers due to competition ranking)
        dogwood_delta = next(d for d in brush_deltas if d["name"] == "Dogwood Handcrafts B2")
        assert dogwood_delta["delta"] == -2  # Negative delta means worsening

        # Mozingo: rank 1 → 3 = "↓2" (worsened by 2 tiers due to competition ranking)
        mozingo_delta = next(d for d in brush_deltas if d["name"] == "Mozingo B2")
        assert mozingo_delta["delta"] == -2  # Negative delta means worsening

        # Simpson: rank 4 → 5 = "↓1" (worsened by 1 tier due to competition ranking)
        simpson_delta = next(d for d in brush_deltas if d["name"] == "Simpson Chubby 2")
        assert simpson_delta["delta"] == -1  # Negative delta means worsening

    def test_performance_with_real_data(self, real_brush_data):
        """Test performance characteristics with real production data."""
        import time

        # Create aggregator
        aggregator = BrushAggregator()

        # Measure aggregation performance
        start_time = time.time()
        result = aggregator.aggregate(real_brush_data)
        aggregation_time = time.time() - start_time

        # Aggregation should complete quickly (< 100ms for small dataset)
        assert aggregation_time < 0.1

        # Measure delta calculation performance
        historical_data = [{"name": item["name"], "rank": item["rank"]} for item in result]

        delta_calculator = DeltaCalculator()
        start_time = time.time()
        deltas = delta_calculator.calculate_deltas(result, historical_data)
        delta_time = time.time() - start_time

        # Delta calculation should complete quickly (< 50ms for small dataset)
        assert delta_time < 0.05

        # Measure tier identification performance
        tier_identifier = TierIdentifier()
        start_time = time.time()
        tier_analysis = tier_identifier.identify_tiers(result)
        tier_time = time.time() - start_time

        # Tier identification should complete quickly (< 10ms for small dataset)
        assert tier_time < 0.01

        # Verify the results are valid
        assert len(deltas) == len(result)
        assert len(tier_analysis) > 0

    def test_edge_cases_with_real_data(self, real_brush_data):
        """Test edge cases with real data patterns."""
        # Test with single item
        single_item_data = [real_brush_data[0]]
        aggregator = BrushAggregator()
        single_result = aggregator.aggregate(single_item_data)

        assert len(single_result) == 1
        assert single_result[0]["rank"] == 1

        # Test with all tied items (same shaves and users)
        tied_data = [
            {
                "brush": {"brand": "Brand A", "model": "Model A"},
                "shaves": 10,
                "unique_users": 5,
            },
            {
                "brush": {"brand": "Brand B", "model": "Model B"},
                "shaves": 10,
                "unique_users": 5,
            },
            {
                "brush": {"brand": "Brand C", "model": "Model C"},
                "shaves": 10,
                "unique_users": 5,
            },
        ]

        tied_result = aggregator.aggregate(tied_data)

        # All items should have rank 1 (tied)
        assert all(item["rank"] == 1 for item in tied_result)

        # Test with empty data
        empty_result = aggregator.aggregate([])
        assert len(empty_result) == 0

    def test_tier_based_delta_accuracy(self, real_brush_data):
        """Test that tier-based deltas accurately reflect tier movements."""
        # Create aggregator and process current data
        aggregator = BrushAggregator()
        current_result = aggregator.aggregate(real_brush_data)

        # Create historical data with tier restructuring
        historical_data = [
            {
                "name": "Declaration Grooming B2",
                "rank": 1,  # Was solo rank 1, now tied rank 1
            },
            {
                "name": "Zenith B2",
                "rank": 2,  # Was rank 2, now tied rank 1
            },
            {
                "name": "Dogwood Handcrafts B2",
                "rank": 1,  # Was tied rank 1, now rank 2
            },
            {
                "name": "Mozingo B2",
                "rank": 1,  # Was tied rank 1, now rank 2
            },
            {
                "name": "Simpson Chubby 2",
                "rank": 3,  # Was rank 3, now rank 3
            },
        ]

        # Calculate deltas
        delta_calculator = DeltaCalculator()
        deltas = delta_calculator.calculate_deltas(current_result, historical_data)

        # Verify complex tier restructuring is handled correctly

        # Declaration Grooming: rank 1 → 1 = "=" (same tier, but now tied)
        declaration_delta = next(d for d in deltas if d["name"] == "Declaration Grooming B2")
        assert declaration_delta["delta_symbol"] == "="

        # Zenith: rank 2 → 1 = "↑1" (improved by 1 tier)
        zenith_delta = next(d for d in deltas if d["name"] == "Zenith B2")
        assert zenith_delta["delta_symbol"] == "↑1"

        # Dogwood: rank 1 → 3 = "↓2" (worsened by 2 tiers due to competition ranking)
        dogwood_delta = next(d for d in deltas if d["name"] == "Dogwood Handcrafts B2")
        assert dogwood_delta["delta_symbol"] == "↓2"

        # Mozingo: rank 1 → 3 = "↓2" (worsened by 2 tiers due to competition ranking)
        mozingo_delta = next(d for d in deltas if d["name"] == "Mozingo B2")
        assert mozingo_delta["delta_symbol"] == "↓2"

        # Simpson: rank 3 → 5 = "↓2" (worsened by 2 tiers due to competition ranking)
        simpson_delta = next(d for d in deltas if d["name"] == "Simpson Chubby 2")
        assert simpson_delta["delta_symbol"] == "↓2"
