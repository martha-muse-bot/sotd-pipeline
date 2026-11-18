"""Integration tests for the complete tier-based delta calculation system."""

from sotd.report.annual_delta_calculator import AnnualDeltaCalculator
from sotd.report.delta_calculator import DeltaCalculator


class TestTierBasedDeltaSystem:
    """Integration tests for the complete tier-based delta calculation system."""

    def test_complete_delta_workflow(self):
        """Test complete end-to-end delta calculation workflow."""
        # Simulate aggregator output with rank field
        current_data = [
            {"name": "Razor A", "shaves": 100, "unique_users": 50, "rank": 1},
            {"name": "Razor B", "shaves": 80, "unique_users": 40, "rank": 2},
            {"name": "Razor C", "shaves": 80, "unique_users": 40, "rank": 2},  # Tied with Razor B
            {"name": "Razor D", "shaves": 60, "unique_users": 30, "rank": 3},
            {"name": "Razor E", "shaves": 60, "unique_users": 30, "rank": 3},  # Tied with Razor D
        ]

        historical_data = [
            {"name": "Razor A", "shaves": 85, "unique_users": 45, "rank": 2},  # Was in Tier 2
            {"name": "Razor B", "shaves": 90, "unique_users": 45, "rank": 1},  # Was in Tier 1
            {"name": "Razor C", "shaves": 85, "unique_users": 40, "rank": 2},  # Still in Tier 2
            {"name": "Razor D", "shaves": 70, "unique_users": 35, "rank": 2},  # Was in Tier 2
            {"name": "Razor E", "shaves": 65, "unique_users": 30, "rank": 2},  # Was in Tier 2
        ]

        # Test monthly delta calculation workflow
        monthly_calculator = DeltaCalculator()
        monthly_results = monthly_calculator.calculate_tier_based_deltas(
            current_data, historical_data
        )

        # Verify monthly workflow results
        assert len(monthly_results) == 5

        # Razor A: Improved from Tier 2 to Tier 1
        razor_a = next(item for item in monthly_results if item["name"] == "Razor A")
        assert razor_a["delta"] == 1
        assert razor_a["delta_symbol"] == "↑1"
        assert razor_a["tier_movement"] == 1
        assert razor_a["tier_structure_changed"] is True

        # Razor B: Declined from Tier 1 to Tier 2
        razor_b = next(item for item in monthly_results if item["name"] == "Razor B")
        assert razor_b["delta"] == -1
        assert razor_b["delta_symbol"] == "↓1"
        assert razor_b["tier_movement"] == -1

        # Razor C: No change (still in Tier 2)
        razor_c = next(item for item in monthly_results if item["name"] == "Razor C")
        assert razor_c["delta"] == 0
        assert razor_c["delta_symbol"] == "="
        assert razor_c["tier_movement"] == 0

        # Razors D and E: Declined from Tier 2 to Tier 3
        for name in ["Razor D", "Razor E"]:
            razor = next(item for item in monthly_results if item["name"] == name)
            assert razor["delta"] == -1
            assert razor["delta_symbol"] == "↓1"
            assert razor["tier_movement"] == -1

    def test_real_data_scenarios(self):
        """Test various real-world tie and ranking scenarios."""
        # Scenario 1: Complex tier restructuring with multiple ties
        current_data = [
            {"name": "Blade A", "shaves": 200, "rank": 1},
            {"name": "Blade B", "shaves": 150, "rank": 2},
            {"name": "Blade C", "shaves": 150, "rank": 2},  # 2-way tie
            {"name": "Blade D", "shaves": 100, "rank": 3},
            {"name": "Blade E", "shaves": 100, "rank": 3},  # 2-way tie
            {"name": "Blade F", "shaves": 100, "rank": 3},  # 3-way tie
        ]

        historical_data = [
            {"name": "Blade A", "shaves": 180, "rank": 2},  # Was in Tier 2
            {"name": "Blade B", "shaves": 180, "rank": 2},  # Was in Tier 2
            {"name": "Blade C", "shaves": 180, "rank": 2},  # Was in Tier 2
            {"name": "Blade D", "shaves": 120, "rank": 2},  # Was in Tier 2
            {"name": "Blade E", "shaves": 120, "rank": 2},  # Was in Tier 2
            {"name": "Blade F", "shaves": 120, "rank": 2},  # Was in Tier 2
        ]

        calculator = DeltaCalculator()
        results = calculator.calculate_tier_based_deltas(current_data, historical_data)

        # Verify complex tier restructuring
        assert len(results) == 6

        # Blade A: Improved to Tier 1
        blade_a = next(item for item in results if item["name"] == "Blade A")
        assert blade_a["delta"] == 1
        assert blade_a["tier_movement"] == 1

        # Blades B and C: Still in Tier 2
        for name in ["Blade B", "Blade C"]:
            blade = next(item for item in results if item["name"] == name)
            assert blade["delta"] == 0
            assert blade["tier_movement"] == 0

        # Blades D, E, F: Declined to Tier 3
        for name in ["Blade D", "Blade E", "Blade F"]:
            blade = next(item for item in results if item["name"] == name)
            assert blade["delta"] == -1
            assert blade["tier_movement"] == -1

    def test_monthly_annual_consistency(self):
        """Test consistency between monthly and annual delta calculations."""
        # Create monthly data
        current_monthly = [
            {"name": "Soap A", "shaves": 50, "rank": 1},
            {"name": "Soap B", "shaves": 40, "rank": 2},
            {"name": "Soap C", "shaves": 40, "rank": 2},  # Tied with Soap B
        ]

        historical_monthly = [
            {"name": "Soap A", "shaves": 45, "rank": 2},  # Was in Tier 2
            {"name": "Soap B", "shaves": 50, "rank": 1},  # Was in Tier 1
            {"name": "Soap C", "shaves": 45, "rank": 2},  # Still in Tier 2
        ]

        # Create annual data (same structure)
        current_annual = {"year": "2024", "data": {"soaps": current_monthly}}

        historical_annual = {"year": "2023", "data": {"soaps": historical_monthly}}

        # Calculate monthly deltas
        monthly_calculator = DeltaCalculator()
        monthly_results = monthly_calculator.calculate_tier_based_deltas(
            current_monthly, historical_monthly
        )

        # Calculate annual deltas
        annual_calculator = AnnualDeltaCalculator()
        annual_results = annual_calculator.calculate_tier_based_annual_deltas(
            current_annual, historical_annual
        )

        # Verify consistency between monthly and annual calculations
        assert "soaps" in annual_results
        annual_soaps = annual_results["soaps"]

        # Both should have same number of results
        assert len(monthly_results) == len(annual_soaps)

        # Both should show same tier movements
        for monthly_item, annual_item in zip(monthly_results, annual_soaps):
            assert monthly_item["name"] == annual_item["name"]
            assert monthly_item["delta"] == annual_item["delta"]
            assert monthly_item["delta_symbol"] == annual_item["delta_symbol"]
            assert monthly_item["tier_movement"] == annual_item["tier_movement"]
            assert monthly_item["tier_structure_changed"] == annual_item["tier_structure_changed"]

    def test_performance_with_production_data(self):
        """Test performance characteristics with production-scale datasets."""
        # Create production-scale dataset (1000+ items)
        current_data = []
        historical_data = []

        for i in range(1000):
            # Create realistic data with various tie patterns
            shaves = 1000 - (i % 100)  # Varies from 900 to 1000
            rank = (i // 10) + 1  # Creates 100 tiers

            current_data.append({"name": f"Product {i:04d}", "shaves": shaves, "rank": rank})

            # Historical data with some changes
            historical_rank = rank + (1 if i % 7 == 0 else 0)  # Some items change rank
            historical_data.append(
                {
                    "name": f"Product {i:04d}",
                    "shaves": shaves + (10 if i % 5 == 0 else 0),  # Some items change shaves
                    "rank": historical_rank,
                }
            )

        calculator = DeltaCalculator()

        # Measure performance
        import time

        start_time = time.time()

        results = calculator.calculate_tier_based_deltas(
            current_data, historical_data, max_items=1000
        )

        end_time = time.time()
        processing_time = end_time - start_time

        # Verify results
        assert len(results) == 1000

        # Performance requirements: Should complete in under 5 seconds for 1000 items
        assert processing_time < 5.0

        # Verify tier analysis is included
        for item in results[:10]:  # Check first 10 items
            assert "tier_structure_changed" in item
            assert "tier_restructured" in item

    def test_edge_cases_with_real_data(self):
        """Test edge cases using realistic data patterns."""
        # Edge case 1: All items tied
        current_data = [
            {"name": "Product A", "shaves": 100, "rank": 1},
            {"name": "Product B", "shaves": 100, "rank": 1},
            {"name": "Product C", "shaves": 100, "rank": 1},
        ]

        historical_data = [
            {"name": "Product A", "shaves": 100, "rank": 1},
            {"name": "Product B", "shaves": 100, "rank": 1},
            {"name": "Product C", "shaves": 100, "rank": 1},
        ]

        calculator = DeltaCalculator()
        results = calculator.calculate_tier_based_deltas(current_data, historical_data)

        # All items should show no change
        for item in results:
            assert item["delta"] == 0
            assert item["delta_symbol"] == "="
            assert item["tier_movement"] == 0
            assert item["tier_structure_changed"] is False
            assert item["tier_restructured"] is False

        # Edge case 2: Single item
        single_current = [{"name": "Product X", "shaves": 50, "rank": 1}]
        single_historical = [{"name": "Product X", "shaves": 45, "rank": 1}]

        single_results = calculator.calculate_tier_based_deltas(single_current, single_historical)

        assert len(single_results) == 1
        assert single_results[0]["delta"] == 0
        assert single_results[0]["delta_symbol"] == "="

        # Edge case 3: Empty data
        empty_results = calculator.calculate_tier_based_deltas([], [])
        assert empty_results == []

    def test_tier_analysis_accuracy(self):
        """Test that tier analysis accurately identifies complex scenarios."""
        # Create scenario with tier splits and merges
        current_data = [
            {"name": "Item A", "rank": 1},  # Moved up from Tier 2
            {"name": "Item B", "rank": 2},  # Still in Tier 2
            {"name": "Item C", "rank": 2},  # Still in Tier 2
            {"name": "Item D", "rank": 3},  # Moved down from Tier 2
            {"name": "Item E", "rank": 4},  # Moved down from Tier 2
        ]

        historical_data = [
            {"name": "Item A", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Item B", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Item C", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Item D", "rank": 2},  # Was in Tier 2 (tied)
            {"name": "Item E", "rank": 2},  # Was in Tier 2 (tied)
        ]

        calculator = DeltaCalculator()

        # Get tier analysis
        tier_analysis = calculator.get_tier_analysis(current_data, historical_data)

        # Verify tier analysis accuracy
        assert tier_analysis["structure_changed"] is True
        assert tier_analysis["restructured"] is True

        # Should identify tier split
        assert len(tier_analysis["splits"]) == 1
        split = tier_analysis["splits"][0]
        assert split["historical_tier"] == 2
        assert set(split["historical_items"]) == {"Item A", "Item B", "Item C", "Item D", "Item E"}
        assert set(split["current_tiers"]) == {1, 2, 3, 4}

        # Verify movement calculations
        movement = tier_analysis["movement"]
        assert movement["Item A"] == 1  # Improved
        assert movement["Item B"] == 0  # No change
        assert movement["Item C"] == 0  # No change
        assert movement["Item D"] == -1  # Declined
        assert movement["Item E"] == -2  # Declined more
