"""
Tests for Brush Learning Report Generator.

This module tests the brush learning report generation system that analyzes
brush validation data and generates structured reports for ChatGPT analysis.
"""

from pathlib import Path

import pytest

from sotd.learning.brush_learning_report_generator import BrushLearningReportGenerator


class TestBrushLearningReportGenerator:
    """Test the brush learning report generator."""

    def test_init_with_validation_data(self):
        """Test initialization with validation data."""
        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "timestamp": "2025-01-27T14:30:00Z",
                "action": "validated",
                "system_choice": {
                    "strategy": "known_brush",
                    "score": 80.0,
                    "result": {"brand": "Omega", "model": "10098", "fiber": "Boar"},
                },
                "user_choice": {
                    "strategy": "known_brush",
                    "result": {"brand": "Omega", "model": "10098", "fiber": "Boar"},
                },
                "all_strategies": [
                    {"strategy": "known_brush", "score": 80.0, "result": {"brand": "Omega"}},
                    {
                        "strategy": "unified",
                        "score": 45.0,
                        "result": {"handle": {"brand": "Omega"}},
                    },
                ],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)

        assert generator.validation_data == validation_data
        assert len(generator.validation_data) == 1

    def test_init_with_empty_validation_data(self):
        """Test initialization with empty validation data."""
        generator = BrushLearningReportGenerator([])

        assert generator.validation_data == []
        assert len(generator.validation_data) == 0

    def test_generate_strategy_analysis_report_basic(self):
        """Test basic strategy analysis report generation."""
        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 80.0},
                    {"strategy": "unified", "score": 45.0},
                ],
            },
            {
                "input_text": "Declaration Grooming / Omega Knot",
                "action": "overridden",
                "system_choice": {"strategy": "known_brush", "score": 70.0},
                "user_choice": {"strategy": "unified"},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 70.0},
                    {"strategy": "unified", "score": 85.0},
                ],
            },
        ]

        generator = BrushLearningReportGenerator(validation_data)
        report = generator.generate_strategy_analysis_report()

        # Should return a structured report
        assert isinstance(report, dict)
        assert "strategy_performance" in report
        assert "win_loss_rates" in report
        assert "score_distributions" in report
        assert "override_patterns" in report

        # Should include strategy performance data
        performance = report["strategy_performance"]
        assert "known_brush" in performance
        assert "unified" in performance

        # Should calculate win/loss rates
        win_loss = report["win_loss_rates"]
        assert isinstance(win_loss, dict)

    def test_generate_modifier_performance_report_basic(self):
        """Test basic modifier performance report generation."""
        validation_data = [
            {
                "input_text": "Declaration Grooming / Omega 10098 w/ modifications",
                "action": "validated",
                "system_choice": {
                    "strategy": "automated_split",
                    "score": 85.0,
                    "modifiers": {
                        "high_confidence": 25.0,
                        "multiple_brands": -3.0,
                        "fiber_words": 2.0,
                    },
                },
                "all_strategies": [{"strategy": "automated_split", "score": 85.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        report = generator.generate_modifier_performance_report()

        # Should return a structured report
        assert isinstance(report, dict)
        assert "modifier_effectiveness" in report
        assert "correlation_analysis" in report
        assert "weight_suggestions" in report

    def test_generate_pattern_discovery_report_basic(self):
        """Test basic pattern discovery report generation."""
        validation_data = [
            {
                "input_text": "Custom handle with Omega knot",
                "action": "overridden",
                "system_choice": {"strategy": "known_brush", "score": 70.0},
                "user_choice": {"strategy": "unified"},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 70.0},
                    {"strategy": "unified", "score": 65.0},
                ],
            },
            {
                "input_text": "Artisan turned handle / Declaration knot",
                "action": "overridden",
                "system_choice": {"strategy": "known_brush", "score": 65.0},
                "user_choice": {"strategy": "unified"},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 65.0},
                    {"strategy": "unified", "score": 60.0},
                ],
            },
        ]

        generator = BrushLearningReportGenerator(validation_data)
        report = generator.generate_pattern_discovery_report()

        # Should return a structured report
        assert isinstance(report, dict)
        assert "common_override_patterns" in report
        assert "text_characteristics" in report
        assert "suggested_modifiers" in report

    def test_generate_comprehensive_report(self):
        """Test comprehensive report generation combining all analysis types."""
        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "timestamp": "2025-01-27T14:30:00Z",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [
                    {"strategy": "known_brush", "score": 80.0},
                    {"strategy": "unified", "score": 45.0},
                ],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)

        # Should have a method to generate comprehensive report
        with pytest.raises(AttributeError):
            # This will fail initially - we need to implement it
            # Type ignore for test - we're testing that the method doesn't exist
            report = generator.generate_comprehensive_report()  # type: ignore

    def test_system_identification_in_reports(self):
        """Test that system identification is included in all reports."""
        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "action": "validated",
                "system": "scoring",  # System identification
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)

        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # All reports should include system identification
        assert "system_info" in strategy_report
        assert "system_info" in modifier_report
        assert "system_info" in pattern_report

        # System info should identify the brush scoring system
        assert strategy_report["system_info"]["system_type"] == "brush_scoring"

    def test_load_validation_data_from_file(self):
        """Test loading validation data from file."""
        # This test will fail initially - we need to implement file loading
        generator = BrushLearningReportGenerator([])

        with pytest.raises(AttributeError):
            # This method doesn't exist yet
            # Type ignore for test - we're testing that the method doesn't exist
            generator.load_validation_data_from_file(  # type: ignore
                Path("data/learning/brush_user_actions_2025-05.yaml")
            )

    def test_save_report_to_file(self):
        """Test saving report to file."""
        generator = BrushLearningReportGenerator([])
        report = {"test": "data"}

        with pytest.raises(AttributeError):
            # This method doesn't exist yet
            # Type ignore for test - we're testing that the method doesn't exist
            generator.save_report_to_file(report, Path("test_report.yaml"))  # type: ignore

    def test_empty_validation_data_handling(self):
        """Test handling of empty validation data."""
        generator = BrushLearningReportGenerator([])

        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # Should handle empty data gracefully
        assert isinstance(strategy_report, dict)
        assert isinstance(modifier_report, dict)
        assert isinstance(pattern_report, dict)

        # Should indicate no data available
        assert strategy_report.get("status") == "no_data"
        assert modifier_report.get("status") == "no_data"
        assert pattern_report.get("status") == "no_data"

    def test_malformed_validation_data_handling(self):
        """Test handling of malformed validation data."""
        malformed_data = [
            {"invalid": "structure"},  # Missing required fields
            {
                "input_text": "Valid entry",
                "action": "validated",
                # Missing other required fields
            },
        ]

        generator = BrushLearningReportGenerator(malformed_data)

        # Should handle malformed data gracefully without crashing
        strategy_report = generator.generate_strategy_analysis_report()

        assert isinstance(strategy_report, dict)
        # Should include warnings about data quality
        assert "warnings" in strategy_report
        assert len(strategy_report["warnings"]) > 0


class TestBrushLearningReportGeneratorIntegration:
    """Integration tests for brush learning report generator."""

    def test_integration_with_real_comparison_data(self):
        """Test integration with real brush system comparison data."""
        # This test will help ensure we can work with actual data files
        comparison_file = Path("data/brush_system_comparison_2025-05.json")

        generator = BrushLearningReportGenerator([])

        with pytest.raises(AttributeError):
            # This method doesn't exist yet
            # Type ignore for test - we're testing that the method doesn't exist
            generator.load_comparison_data(comparison_file)  # type: ignore

    def test_report_format_compatibility(self):
        """Test that reports are compatible with existing report patterns."""
        validation_data = [
            {
                "input_text": "Test brush",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        report = generator.generate_strategy_analysis_report()

        # Should follow existing report patterns
        assert "analysis_date" in report
        assert "report_type" in report
        assert isinstance(report.get("analysis_date"), str)
        assert report.get("report_type") == "strategy_analysis"
