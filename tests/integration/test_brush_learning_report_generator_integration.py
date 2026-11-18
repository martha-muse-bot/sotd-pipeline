"""
Integration tests for Brush Learning Report Generator.

This module tests the brush learning report generator with real data
and validates integration with the actual brush scoring system.
"""

import json
from pathlib import Path

import pytest

from sotd.learning.brush_learning_report_generator import BrushLearningReportGenerator


class TestBrushLearningReportGeneratorIntegration:
    """Integration tests for brush learning report generator."""

    def test_integration_with_real_comparison_data(self):
        """Test integration with real brush system comparison data."""
        comparison_file = Path("data/brush_system_comparison_2025-05.json")

        if not comparison_file.exists():
            pytest.fail(
                f"Test requires comparison file {comparison_file} but it was not found. Create the comparison file or provide a test fixture to run this integration test."
            )

        # Load real comparison data
        with open(comparison_file, "r") as f:
            comparison_data = json.load(f)

        # Transform comparison data into validation data format
        validation_data = self._transform_comparison_to_validation_data(comparison_data)

        # Test report generation with real data
        generator = BrushLearningReportGenerator(validation_data)

        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # Validate reports have expected structure
        assert isinstance(strategy_report, dict)
        assert isinstance(modifier_report, dict)
        assert isinstance(pattern_report, dict)

        # All reports should have system info
        assert "system_info" in strategy_report
        assert "system_info" in modifier_report
        assert "system_info" in pattern_report

    def test_with_empty_comparison_data(self):
        """Test handling of empty comparison data."""
        empty_comparison = {
            "summary": {
                "total_records": 0,
                "matching_results": {"count": 0, "percentage": 0.0},
                "different_results": {"count": 0, "percentage": 0.0},
            },
            "detailed_differences": [],
        }

        validation_data = self._transform_comparison_to_validation_data(empty_comparison)
        generator = BrushLearningReportGenerator(validation_data)

        # Should handle empty data gracefully
        strategy_report = generator.generate_strategy_analysis_report()
        assert strategy_report["status"] == "no_data"

    def test_report_format_compatibility_with_existing_patterns(self):
        """Test that reports follow existing analysis report patterns."""
        # Create minimal validation data for testing
        validation_data = [
            {
                "input_text": "Test brush input",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        report = generator.generate_strategy_analysis_report()

        # Should follow existing report patterns found in analysis/
        required_fields = ["analysis_date", "report_type", "system_info"]
        for field in required_fields:
            assert field in report, f"Report missing required field: {field}"

        # Analysis date should be in ISO format
        assert isinstance(report["analysis_date"], str)
        assert "T" in report["analysis_date"] or "-" in report["analysis_date"]

        # Report type should be descriptive
        assert report["report_type"] == "strategy_analysis"

        # System info should identify brush scoring system
        assert report["system_info"]["system_type"] == "brush_scoring"

    def _transform_comparison_to_validation_data(self, comparison_data: dict) -> list:
        """
        Transform brush system comparison data into validation data format.

        Args:
            comparison_data: Data from brush_system_comparison_*.json

        Returns:
            List of validation records in expected format
        """
        validation_records = []

        # Extract detailed differences if available
        differences = comparison_data.get("detailed_differences", [])

        for diff in differences[:10]:  # Limit to first 10 for testing
            # Create a validation record from the difference
            record = {
                "input_text": diff.get("input_text", "Unknown"),
                "action": "validated" if diff.get("systems_agree", True) else "overridden",
                "system_choice": {
                    "strategy": diff.get("old_strategy", "unknown"),
                    "score": 80.0,  # Default score for testing
                },
                "all_strategies": [
                    {"strategy": diff.get("old_strategy", "unknown"), "score": 80.0},
                    {"strategy": diff.get("new_strategy", "unknown"), "score": 75.0},
                ],
            }

            # Add user choice for override cases
            if record["action"] == "overridden":
                record["user_choice"] = {"strategy": diff.get("new_strategy", "unknown")}

            validation_records.append(record)

        # If no differences, return empty validation data
        # (dummy data creation removed to properly test empty data handling)

        return validation_records

    def test_performance_with_large_dataset(self):
        """Test performance with larger validation datasets."""
        # Create a larger validation dataset for performance testing
        large_validation_data = []

        strategies = ["known_brush", "unified", "automated_split", "omega_semogue"]
        actions = ["validated", "overridden"]

        for i in range(100):  # 100 records for performance test
            record = {
                "input_text": f"Test brush input {i}",
                "action": actions[i % 2],
                "system_choice": {
                    "strategy": strategies[i % len(strategies)],
                    "score": 70.0 + (i % 30),  # Vary scores
                },
                "all_strategies": [
                    {"strategy": strategies[j % len(strategies)], "score": 60.0 + j}
                    for j in range(3)  # 3 strategies per record
                ],
            }
            large_validation_data.append(record)

        generator = BrushLearningReportGenerator(large_validation_data)

        # Should handle large datasets efficiently
        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # All reports should be generated successfully
        assert strategy_report["status"] == "success"
        assert modifier_report["status"] == "success"
        assert pattern_report["status"] == "success"

        # Should have performance data for all strategies
        performance = strategy_report["strategy_performance"]
        assert len(performance) == len(strategies)

        for strategy in strategies:
            assert strategy in performance
            assert performance[strategy]["total_selections"] > 0
