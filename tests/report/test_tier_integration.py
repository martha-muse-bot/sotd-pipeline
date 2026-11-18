"""Tests for tier-based delta calculation integration."""

from sotd.report.annual_delta_calculator import AnnualDeltaCalculator
from sotd.report.delta_calculator import DeltaCalculator


class TestTierIntegration:
    """Test integration between TierIdentifier utility and delta calculators."""

    def test_delta_calculator_tier_integration(self):
        """Test that DeltaCalculator integrates with TierIdentifier utility."""
        current_data = [
            {"name": "Razor A", "rank": 1},  # Added rank
            {"name": "Razor B", "rank": 2},
            {"name": "Razor C", "rank": 2},  # Tied with Razor B
        ]

        historical_data = [
            {"name": "Razor A", "rank": 2},  # Was in Tier 2
            {"name": "Razor B", "rank": 1},  # Was in Tier 1
            {"name": "Razor C", "rank": 2},  # Still in Tier 2
        ]

        calculator = DeltaCalculator()

        # Test basic delta calculation
        basic_results = calculator.calculate_deltas(current_data, historical_data)
        assert len(basic_results) == 3

        # Test tier-based delta calculation
        tier_results = calculator.calculate_tier_based_deltas(current_data, historical_data)
        assert len(tier_results) == 3

        # Verify tier information is added
        for item in tier_results:
            assert "tier_structure_changed" in item
            assert "tier_restructured" in item
            if item["name"] in ["Razor A", "Razor B"]:
                assert "tier_change" in item
                assert "tier_movement" in item

    def test_delta_calculator_tier_analysis(self):
        """Test that DeltaCalculator provides tier analysis."""
        current_data = [
            {"name": "Razor A", "rank": 1},  # Added rank
            {"name": "Razor B", "rank": 2},
            {"name": "Razor C", "rank": 2},
        ]

        historical_data = [
            {"name": "Razor A", "rank": 2},
            {"name": "Razor B", "rank": 1},  # Added rank
            {"name": "Razor C", "rank": 2},
        ]

        calculator = DeltaCalculator()
        tier_analysis = calculator.get_tier_analysis(current_data, historical_data)

        # Should include tier movement information
        assert "movement" in tier_analysis
        assert "tier_changes" in tier_analysis
        assert "structure_changed" in tier_analysis
        assert "restructured" in tier_analysis

        # Should show tier structure changed
        assert tier_analysis["structure_changed"] is True
        assert tier_analysis["restructured"] is True

    def test_annual_delta_calculator_tier_integration(self):
        """Test that AnnualDeltaCalculator integrates with TierIdentifier utility."""
        current_year_data = {
            "year": "2024",
            "data": {
                "razors": [
                    {"name": "Razor A", "rank": 1},  # Added rank
                    {"name": "Razor B", "rank": 2},
                    {"name": "Razor C", "rank": 2},
                ]
            },
        }

        previous_year_data = {
            "year": "2023",
            "data": {
                "razors": [
                    {"name": "Razor A", "rank": 2},
                    {"name": "Razor B", "rank": 1},  # Added rank
                    {"name": "Razor C", "rank": 2},
                ]
            },
        }

        calculator = AnnualDeltaCalculator()

        # Test basic annual delta calculation
        basic_results = calculator.calculate_annual_deltas(current_year_data, previous_year_data)
        assert "razors" in basic_results
        assert len(basic_results["razors"]) == 3

        # Test tier-based annual delta calculation
        tier_results = calculator.calculate_tier_based_annual_deltas(
            current_year_data, previous_year_data
        )
        assert "razors" in tier_results
        assert len(tier_results["razors"]) == 3

        # Verify tier information is added
        for item in tier_results["razors"]:
            assert "tier_structure_changed" in item
            assert "tier_restructured" in item
            if item["name"] in ["Razor A", "Razor B"]:
                assert "tier_change" in item
                assert "tier_movement" in item

    def test_annual_delta_calculator_tier_analysis(self):
        """Test that AnnualDeltaCalculator provides tier analysis."""
        current_year_data = {
            "year": "2024",
            "data": {
                "razors": [
                    {"name": "Razor A", "rank": 1},  # Added rank
                    {"name": "Razor B", "rank": 2},
                    {"name": "Razor C", "rank": 2},
                ]
            },
        }

        previous_year_data = {
            "year": "2023",
            "data": {
                "razors": [
                    {"name": "Razor A", "rank": 2},
                    {"name": "Razor B", "rank": 1},  # Added rank
                    {"name": "Razor C", "rank": 2},
                ]
            },
        }

        calculator = AnnualDeltaCalculator()
        tier_analysis = calculator.get_annual_tier_analysis(current_year_data, previous_year_data)

        # Should include tier analysis for razors category
        assert "razors" in tier_analysis

        razors_analysis = tier_analysis["razors"]
        assert "movement" in razors_analysis
        assert "tier_changes" in razors_analysis
        assert "structure_changed" in razors_analysis
        assert "restructured" in razors_analysis

        # Should show tier structure changed
        assert razors_analysis["structure_changed"] is True
        assert razors_analysis["restructured"] is True

    def test_complex_tier_scenarios_integration(self):
        """Test integration handles complex tier scenarios correctly."""
        current_data = [
            {"name": "Razor A", "rank": 1},  # Moved up from Tier 2
            {"name": "Razor B", "rank": 2},  # Still in Tier 2
            {"name": "Razor C", "rank": 2},  # Still in Tier 2
            {"name": "Razor D", "rank": 3},  # Moved down from Tier 2
        ]

        historical_data = [
            {"name": "Razor A", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Razor B", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Razor C", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Razor D", "rank": 2},  # Was in Tier 2 (tied)
        ]

        calculator = DeltaCalculator()
        tier_results = calculator.calculate_tier_based_deltas(current_data, historical_data)

        # Should identify tier split scenario
        assert len(tier_results) == 4

        # Razor A should show improvement
        razor_a = next(item for item in tier_results if item["name"] == "Razor A")
        assert razor_a["delta"] == 1
        assert razor_a["tier_movement"] == 1

        # Razor D should show decline
        razor_d = next(item for item in tier_results if item["name"] == "Razor D")
        assert razor_d["delta"] == -1
        assert razor_d["tier_movement"] == -1

        # All should show tier structure changed
        for item in tier_results:
            assert item["tier_structure_changed"] is True
            assert item["tier_restructured"] is True
