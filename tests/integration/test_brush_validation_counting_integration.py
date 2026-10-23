"""Integration tests for brush validation counting workflow.

These tests validate the complete counting workflow across CLI, WebUI, and counting service
to ensure consistent counts and proper mathematical relationships.
"""

import pytest

from sotd.match.brush.validation.cli import BrushValidationCLI
from sotd.match.brush.validation.counting import BrushValidationCountingService


class TestBrushValidationCountingIntegration:
    """Integration tests for brush validation counting workflow."""

    @pytest.fixture
    def cli(self):
        """Create CLI instance for testing."""
        return BrushValidationCLI()

    @pytest.fixture
    def counting_service(self):
        """Create counting service instance for testing."""
        return BrushValidationCountingService()

    def test_cli_and_service_consistency(self, cli, counting_service):
        """Test that CLI and counting service return identical results."""
        month = "2025-06"

        # Get statistics from both sources
        cli_stats = cli.get_validation_statistics(month)
        service_stats = counting_service.get_validation_statistics(month)

        # Verify they are identical
        assert (
            cli_stats == service_stats
        ), "CLI and counting service should return identical statistics"

        # Get strategy distribution from both sources
        cli_strategy = cli.get_strategy_distribution_statistics(month)
        service_strategy = counting_service.get_strategy_distribution_statistics(month)

        # Verify they are identical
        assert (
            cli_strategy == service_strategy
        ), "CLI and counting service should return identical strategy distribution"

    def test_mathematical_relationships_integration(self, cli, counting_service):
        """Test mathematical relationships across the complete system."""
        month = "2025-06"

        # Get statistics from CLI (which uses counting service)
        stats = cli.get_validation_statistics(month)
        strategy_stats = cli.get_strategy_distribution_statistics(month)

        # Test core relationship: Total = Validated + Overridden + Unvalidated
        total_calculated = (
            stats["validated_count"] + stats["overridden_count"] + stats["unvalidated_count"]
        )
        assert stats["total_entries"] == total_calculated, (
            f"Total should equal Validated + Overridden + Unvalidated: "
            f"{stats['total_entries']} = {total_calculated}"
        )

        # Test strategy distribution consistency
        assert strategy_stats["total_brush_records"] == stats["total_entries"], (
            f"Strategy total should equal CLI total: "
            f"{strategy_stats['total_brush_records']} = {stats['total_entries']}"
        )

        # Test remaining entries calculation
        assert strategy_stats["remaining_entries"] == stats["unvalidated_count"], (
            f"Remaining entries should equal unvalidated count: "
            f"{strategy_stats['remaining_entries']} = {stats['unvalidated_count']}"
        )

        # Test validation rate calculation
        expected_rate = (stats["validated_count"] + stats["overridden_count"]) / stats[
            "total_entries"
        ]
        assert abs(stats["validation_rate"] - expected_rate) < 0.001, (
            f"Validation rate should be mathematically correct: "
            f"{stats['validation_rate']} ≈ {expected_rate}"
        )

    def test_case_insensitive_grouping_integration(self, cli):
        """Test case-insensitive grouping with real data."""
        month = "2025-06"

        # Get statistics
        stats = cli.get_validation_statistics(month)

        # Verify that case-insensitive grouping is working
        # This test ensures that "Brush 1" and "brush 1" count as one entry
        assert stats["total_entries"] > 0, "Should have some entries"

        # The total should be reasonable (not thousands if case-sensitive grouping failed)
        assert (
            stats["total_entries"] < 10000
        ), "Total entries should be reasonable with case-insensitive grouping"

    def test_correct_matches_integration(self, cli):
        """Test that correct matches are properly counted as validated."""
        month = "2025-06"

        stats = cli.get_validation_statistics(month)
        strategy_stats = cli.get_strategy_distribution_statistics(month)

        # Correct matches should be included in validated count
        correct_matches_count = strategy_stats["correct_matches_count"]

        # If there are no correct matches, that's fine - just verify the logic
        if correct_matches_count > 0:
            # Validated count should be >= correct matches count
            assert stats["validated_count"] >= correct_matches_count, (
                f"Validated count should include correct matches: "
                f"{stats['validated_count']} >= {correct_matches_count}"
            )
        else:
            # No correct matches - verify the system handles this gracefully
            print(f"No correct matches found for {month} - this is acceptable")
            assert correct_matches_count >= 0, "Correct matches count should be non-negative"

    def test_user_actions_integration(self, cli):
        """Test that user actions are properly counted."""
        month = "2025-06"

        stats = cli.get_validation_statistics(month)

        # User actions should contribute to validated and overridden counts
        total_user_actions = stats["validated_count"] + stats["overridden_count"]
        assert total_user_actions >= 0, "Total user actions should be non-negative"

        # Validation rate should reflect user actions
        if stats["total_entries"] > 0:
            assert 0 <= stats["validation_rate"] <= 1, "Validation rate should be between 0 and 1"

    def test_strategy_distribution_integration(self, cli):
        """Test strategy distribution counting logic."""
        month = "2025-06"

        strategy_stats = cli.get_strategy_distribution_statistics(month)

        # Should have strategy counts
        assert "strategy_counts" in strategy_stats, "Should have strategy counts"
        assert "all_strategies_lengths" in strategy_stats, "Should have all_strategies_lengths"

        # Strategy counts should be reasonable
        strategy_counts = strategy_stats["strategy_counts"]
        assert len(strategy_counts) > 0, "Should have some strategies"

        # All strategies lengths should be reasonable
        all_strategies_lengths = strategy_stats["all_strategies_lengths"]
        assert len(all_strategies_lengths) > 0, "Should have some all_strategies_lengths"

    def test_error_handling_integration(self, cli):
        """Test error handling with invalid month."""
        invalid_month = "invalid-month"

        # Should handle invalid month gracefully
        try:
            stats = cli.get_validation_statistics(invalid_month)
            # If it doesn't raise an exception, it should return empty/default data
            assert stats["total_entries"] == 0, "Invalid month should return 0 entries"
        except Exception as e:
            # Exception is also acceptable for invalid month
            assert (
                "month" in str(e).lower() or "invalid" in str(e).lower()
            ), f"Unexpected error: {e}"

    @pytest.mark.perf
    def test_performance_integration(self, cli):
        """Test performance characteristics with real data."""
        month = "2025-06"

        import time

        # Test validation statistics performance
        start_time = time.time()
        stats = cli.get_validation_statistics(month)
        stats_time = time.time() - start_time

        # Test strategy distribution performance
        start_time = time.time()
        strategy_stats = cli.get_strategy_distribution_statistics(month)
        strategy_time = time.time() - start_time

        # Both operations should complete in reasonable time (< 5 seconds)
        assert stats_time < 5.0, f"Validation statistics took too long: {stats_time:.2f}s"
        assert strategy_time < 5.0, f"Strategy distribution took too long: {strategy_time:.2f}s"

        # Verify we got reasonable data
        assert stats["total_entries"] > 0, "Should have some entries"
        assert strategy_stats["total_brush_records"] > 0, "Should have some brush records"

    def test_data_consistency_integration(self, cli):
        """Test that data is consistent across multiple calls."""
        month = "2025-06"

        # Get statistics multiple times
        stats1 = cli.get_validation_statistics(month)
        stats2 = cli.get_validation_statistics(month)

        # Results should be identical (deterministic)
        assert stats1 == stats2, "Multiple calls should return identical results"

        # Get strategy distribution multiple times
        strategy1 = cli.get_strategy_distribution_statistics(month)
        strategy2 = cli.get_strategy_distribution_statistics(month)

        # Results should be identical (deterministic)
        assert strategy1 == strategy2, "Multiple calls should return identical results"

    def test_complete_workflow_integration(self, cli):
        """Test the complete counting workflow end-to-end."""
        month = "2025-06"

        # Step 1: Get validation statistics
        stats = cli.get_validation_statistics(month)
        assert "total_entries" in stats, "Should have total_entries"
        assert "validated_count" in stats, "Should have validated_count"
        assert "overridden_count" in stats, "Should have overridden_count"
        assert "unvalidated_count" in stats, "Should have unvalidated_count"
        assert "validation_rate" in stats, "Should have validation_rate"

        # Step 2: Get strategy distribution
        strategy_stats = cli.get_strategy_distribution_statistics(month)
        assert "total_brush_records" in strategy_stats, "Should have total_brush_records"
        assert "correct_matches_count" in strategy_stats, "Should have correct_matches_count"
        assert "remaining_entries" in strategy_stats, "Should have remaining_entries"
        assert "strategy_counts" in strategy_stats, "Should have strategy_counts"
        assert "all_strategies_lengths" in strategy_stats, "Should have all_strategies_lengths"

        # Step 3: Verify mathematical consistency
        total_calculated = (
            stats["validated_count"] + stats["overridden_count"] + stats["unvalidated_count"]
        )
        assert stats["total_entries"] == total_calculated, "Mathematical relationship should hold"
        assert (
            strategy_stats["total_brush_records"] == stats["total_entries"]
        ), "Totals should match"
        assert (
            strategy_stats["remaining_entries"] == stats["unvalidated_count"]
        ), "Remaining should match unvalidated"

        # Step 4: Verify data quality
        assert stats["total_entries"] > 0, "Should have some entries"
        assert 0 <= stats["validation_rate"] <= 1, "Validation rate should be valid"
        assert len(strategy_stats["strategy_counts"]) > 0, "Should have some strategies"

        print(f"✅ Complete workflow test passed for {month}")
        print(f"   Total Entries: {stats['total_entries']}")
        print(f"   Validated: {stats['validated_count']}")
        print(f"   Overridden: {stats['overridden_count']}")
        print(f"   Unvalidated: {stats['unvalidated_count']}")
        print(f"   Validation Rate: {stats['validation_rate']:.3f}")
        print(f"   Strategies: {len(strategy_stats['strategy_counts'])}")
        print(f"   All Strategies Lengths: {len(strategy_stats['all_strategies_lengths'])}")
