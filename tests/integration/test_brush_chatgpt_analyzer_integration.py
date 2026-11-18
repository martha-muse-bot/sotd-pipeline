"""
Integration tests for Brush ChatGPT Analyzer.

This module tests the ChatGPT integration system with real learning reports
and validates the complete workflow from report generation to ChatGPT analysis.
"""

from unittest.mock import patch

import yaml

from sotd.learning.brush_chatgpt_analyzer import BrushChatGPTAnalyzer
from sotd.learning.brush_learning_report_generator import BrushLearningReportGenerator


class TestBrushChatGPTAnalyzerIntegration:
    """Integration tests for brush ChatGPT analyzer."""

    def test_complete_learning_workflow(self):
        """Test complete workflow from learning reports to ChatGPT analysis."""
        # Step 1: Generate learning reports using real validation data
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
            {
                "input_text": "Custom handle with badger knot",
                "action": "overridden",
                "system_choice": {"strategy": "unified", "score": 50.0},
                "user_choice": {"strategy": "automated_split"},
                "all_strategies": [
                    {"strategy": "unified", "score": 50.0},
                    {"strategy": "automated_split", "score": 60.0},
                ],
            },
        ]

        generator = BrushLearningReportGenerator(validation_data)
        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # Step 2: Analyze reports with ChatGPT integration
        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            # Mock realistic ChatGPT responses
            mock_call.side_effect = [
                # Strategy analysis response
                {
                    "weight_adjustments": {
                        "known_brush": 85.0,  # Increase due to good performance
                        "unified": 45.0,  # Decrease due to overrides
                        "automated_split": 65.0,  # Increase due to user preference
                    },
                    "reasoning": "known_brush shows high validation rate but unified has override issues",
                },
                # Modifier analysis response
                {
                    "modifier_adjustments": {
                        "multiple_brands": -5.0,
                        "fiber_words": 5.0,
                    },
                    "reasoning": "Adjust modifiers based on effectiveness patterns",
                },
                # Pattern discovery response
                {
                    "suggested_new_modifiers": [
                        {
                            "name": "custom_handle",
                            "function_name": "_modifier_custom_handle",
                            "pattern": "custom|artisan|handmade",
                            "suggested_weights": {
                                "automated_split": 15,
                                "unified": 10,
                            },
                            "test_cases": [
                                "custom handle with Omega knot",
                                "artisan turned handle",
                            ],
                        }
                    ],
                    "reasoning": "Custom handle patterns appear in override cases",
                },
            ]

            # Run all analyses
            strategy_analysis = analyzer.analyze_strategy_selection(strategy_report)
            modifier_analysis = analyzer.analyze_modifier_performance(modifier_report)
            pattern_analysis = analyzer.analyze_pattern_discovery(pattern_report)

            # Verify all analyses completed successfully
            assert strategy_analysis["analysis_type"] == "strategy_selection"
            assert modifier_analysis["analysis_type"] == "modifier_performance"
            assert pattern_analysis["analysis_type"] == "pattern_discovery"

            # Verify ChatGPT was called for each analysis
            assert mock_call.call_count == 3

            # Verify structured suggestions were returned
            assert "weight_adjustments" in strategy_analysis
            assert "modifier_adjustments" in modifier_analysis
            assert "suggested_new_modifiers" in pattern_analysis

    def test_yaml_serialization_compatibility(self):
        """Test that all analysis results can be serialized to YAML."""
        validation_data = [
            {
                "input_text": "Test brush input",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        reports = {
            "strategy": generator.generate_strategy_analysis_report(),
            "modifier": generator.generate_modifier_performance_report(),
            "pattern": generator.generate_pattern_discovery_report(),
        }

        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "weight_adjustments": {"known_brush": 85.0},
                "reasoning": "Test reasoning",
            }

            # Analyze all reports
            results = {}
            for report_type, report in reports.items():
                if report_type == "strategy":
                    results[report_type] = analyzer.analyze_strategy_selection(report)
                elif report_type == "modifier":
                    results[report_type] = analyzer.analyze_modifier_performance(report)
                elif report_type == "pattern":
                    results[report_type] = analyzer.analyze_pattern_discovery(report)

            # Test YAML serialization for all results
            for result in results.values():
                yaml_output = yaml.dump(result, default_flow_style=False)
                assert isinstance(yaml_output, str)
                assert len(yaml_output) > 0

                # Test round-trip serialization
                parsed_back = yaml.safe_load(yaml_output)
                assert isinstance(parsed_back, dict)
                assert parsed_back["analysis_type"] in [
                    "strategy_selection",
                    "modifier_performance",
                    "pattern_discovery",
                ]

    def test_error_handling_in_workflow(self):
        """Test error handling throughout the complete workflow."""
        # Test with malformed validation data
        malformed_data = [{"invalid": "structure"}]

        generator = BrushLearningReportGenerator(malformed_data)
        strategy_report = generator.generate_strategy_analysis_report()

        analyzer = BrushChatGPTAnalyzer("test-api-key")

        # Test with API error
        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.side_effect = Exception("API Error")

            result = analyzer.analyze_strategy_selection(strategy_report)

            assert "error" in result
            assert "API Error" in result["error"]
            assert result["analysis_type"] == "strategy_selection"

        # Test with invalid response
        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = "invalid json response"

            result = analyzer.analyze_strategy_selection(strategy_report)

            assert "error" in result
            assert "invalid response" in result["error"].lower()

    def test_system_identification_throughout_workflow(self):
        """Test that system identification is preserved throughout the workflow."""
        validation_data = [
            {
                "input_text": "Test brush",
                "action": "validated",
                "system": "scoring",  # System identification
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        strategy_report = generator.generate_strategy_analysis_report()

        # Verify system info is in the report
        assert "system_info" in strategy_report
        assert strategy_report["system_info"]["system_type"] == "brush_scoring"

        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {"weight_adjustments": {}, "reasoning": "test"}

            result = analyzer.analyze_strategy_selection(strategy_report)

            # Verify system identification was included in the prompt
            prompt_arg = mock_call.call_args[0][0]
            assert "brush_scoring" in prompt_arg.lower()
            assert "system type" in prompt_arg.lower()

            # Verify result maintains analysis type
            assert result["analysis_type"] == "strategy_selection"

    def test_performance_with_large_datasets(self):
        """Test performance with larger validation datasets."""
        # Create larger dataset
        large_validation_data = []
        strategies = ["known_brush", "unified", "automated_split", "omega_semogue"]
        actions = ["validated", "overridden"]

        for i in range(50):  # 50 records for performance test
            record = {
                "input_text": f"Test brush input {i}",
                "action": actions[i % 2],
                "system_choice": {
                    "strategy": strategies[i % len(strategies)],
                    "score": 70.0 + (i % 30),
                },
                "all_strategies": [
                    {"strategy": strategies[j % len(strategies)], "score": 60.0 + j}
                    for j in range(3)
                ],
            }
            large_validation_data.append(record)

        generator = BrushLearningReportGenerator(large_validation_data)
        strategy_report = generator.generate_strategy_analysis_report()

        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "weight_adjustments": {"known_brush": 85.0},
                "reasoning": "Performance test",
            }

            # Should handle large datasets efficiently
            result = analyzer.analyze_strategy_selection(strategy_report)

            assert result["analysis_type"] == "strategy_selection"
            assert "weight_adjustments" in result

            # Verify prompt was generated efficiently (should not take too long)
            assert mock_call.called

    def test_no_api_key_handling(self):
        """Test workflow when no API key is provided."""
        validation_data = [
            {
                "input_text": "Test brush",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        generator = BrushLearningReportGenerator(validation_data)
        strategy_report = generator.generate_strategy_analysis_report()

        # Test with no API key
        analyzer = BrushChatGPTAnalyzer(None)

        result = analyzer.analyze_strategy_selection(strategy_report)

        # Should handle gracefully in mock mode
        assert "warning" in result
        assert "mock mode" in result["warning"].lower()
        assert result["analysis_type"] == "strategy_selection"
        assert "weight_adjustments" in result
