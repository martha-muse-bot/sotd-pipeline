"""
Tests for Brush ChatGPT Analyzer.

This module tests the ChatGPT integration system for brush learning analysis
that generates structured prompts and processes ChatGPT responses for suggestions.
"""

from unittest.mock import patch

import pytest

from sotd.learning.brush_chatgpt_analyzer import BrushChatGPTAnalyzer


class TestBrushChatGPTAnalyzer:
    """Test the brush ChatGPT analyzer."""

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        assert analyzer.api_key == api_key
        assert analyzer.api_key is not None

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        analyzer = BrushChatGPTAnalyzer(None)

        assert analyzer.api_key is None

    def test_analyze_strategy_selection_basic(self):
        """Test basic strategy selection analysis."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Mock learning report data
        strategy_report = {
            "status": "success",
            "report_type": "strategy_analysis",
            "system_info": {"system_type": "brush_scoring"},
            "strategy_performance": {
                "known_brush": {
                    "total_selections": 10,
                    "validated_selections": 8,
                    "overridden_selections": 2,
                },
                "unified": {
                    "total_selections": 20,
                    "validated_selections": 12,
                    "overridden_selections": 8,
                },
            },
            "win_loss_rates": {
                "known_brush": {"win_rate": 80.0, "loss_rate": 20.0},
                "unified": {"win_rate": 60.0, "loss_rate": 40.0},
            },
        }

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "weight_adjustments": {
                    "known_brush": 85.0,  # Increase from 80.0
                    "unified": 45.0,  # Decrease from 50.0
                },
                "reasoning": "known_brush shows higher validation rate, should be boosted",
            }

            result = analyzer.analyze_strategy_selection(strategy_report)

            assert isinstance(result, dict)
            assert "weight_adjustments" in result
            assert "reasoning" in result
            assert result["weight_adjustments"]["known_brush"] == 85.0
            assert result["weight_adjustments"]["unified"] == 45.0

            # Verify ChatGPT was called with proper prompt
            mock_call.assert_called_once()
            prompt_arg = mock_call.call_args[0][0]
            assert "strategy selection performance" in prompt_arg.lower()
            assert "brush scoring system" in prompt_arg.lower()

    def test_analyze_modifier_performance_basic(self):
        """Test basic modifier performance analysis."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Mock modifier performance report
        modifier_report = {
            "status": "success",
            "report_type": "modifier_performance",
            "system_info": {"system_type": "brush_scoring"},
            "modifier_effectiveness": {
                "multiple_brands": {
                    "validated_count": 5,
                    "overridden_count": 15,
                    "total_count": 20,
                },
                "fiber_words": {"validated_count": 12, "overridden_count": 3, "total_count": 15},
            },
        }

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "modifier_adjustments": {
                    "multiple_brands": -5.0,  # Decrease weight
                    "fiber_words": 5.0,  # Increase weight
                },
                "reasoning": "multiple_brands has low validation rate, fiber_words performs well",
            }

            result = analyzer.analyze_modifier_performance(modifier_report)

            assert isinstance(result, dict)
            assert "modifier_adjustments" in result
            assert "reasoning" in result
            assert result["modifier_adjustments"]["multiple_brands"] == -5.0
            assert result["modifier_adjustments"]["fiber_words"] == 5.0

            # Verify ChatGPT was called with proper prompt
            mock_call.assert_called_once()
            prompt_arg = mock_call.call_args[0][0]
            assert "modifier performance" in prompt_arg.lower()

    def test_analyze_pattern_discovery_basic(self):
        """Test basic pattern discovery analysis."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Mock pattern discovery report
        pattern_report = {
            "status": "success",
            "report_type": "pattern_discovery",
            "system_info": {"system_type": "brush_scoring"},
            "common_override_patterns": {
                "keyword_frequency": {"custom": 5, "artisan": 3, "handmade": 2}
            },
        }

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "suggested_new_modifiers": [
                    {
                        "name": "custom_handle",
                        "function_name": "_modifier_custom_handle",
                        "pattern": "custom|artisan|handmade",
                        "suggested_weights": {"unified": 15, "automated_split": 10},
                    }
                ],
                "reasoning": "Custom handle patterns appear frequently in override cases",
            }

            result = analyzer.analyze_pattern_discovery(pattern_report)

            assert isinstance(result, dict)
            assert "suggested_new_modifiers" in result
            assert "reasoning" in result
            assert len(result["suggested_new_modifiers"]) == 1
            assert result["suggested_new_modifiers"][0]["name"] == "custom_handle"

            # Verify ChatGPT was called with proper prompt
            mock_call.assert_called_once()
            prompt_arg = mock_call.call_args[0][0]
            assert "pattern discovery" in prompt_arg.lower()

    def test_generate_comprehensive_analysis(self):
        """Test comprehensive analysis combining all analysis types."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Test that we can generate comprehensive analysis - this will fail initially
        strategy_report = {"status": "success", "report_type": "strategy_analysis"}

        with pytest.raises(AttributeError):
            # This method doesn't exist yet
            # Type ignore for test - we're testing that the method doesn't exist
            analyzer.generate_comprehensive_analysis(strategy_report)  # type: ignore

    def test_chatgpt_call_with_system_identification(self):
        """Test that ChatGPT calls include proper system identification."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        report = {
            "system_info": {"system_type": "brush_scoring", "version": "1.0"},
            "strategy_performance": {},
        }

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {"weight_adjustments": {}}

            analyzer.analyze_strategy_selection(report)

            # Verify system info is included in prompt
            prompt_arg = mock_call.call_args[0][0]
            assert "brush_scoring" in prompt_arg.lower()
            assert "system type" in prompt_arg.lower()

    def test_chatgpt_api_error_handling(self):
        """Test handling of ChatGPT API errors."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        report = {"strategy_performance": {}}

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.side_effect = Exception("API Error")

            # Should handle API errors gracefully
            result = analyzer.analyze_strategy_selection(report)

            assert isinstance(result, dict)
            assert "error" in result
            assert "API Error" in result["error"]

    def test_invalid_chatgpt_response_handling(self):
        """Test handling of invalid ChatGPT responses."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        report = {"strategy_performance": {}}

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = "invalid json response"

            # Should handle invalid responses gracefully
            result = analyzer.analyze_strategy_selection(report)

            assert isinstance(result, dict)
            assert "error" in result
            assert "invalid response" in result["error"].lower()

    def test_empty_report_handling(self):
        """Test handling of empty or invalid reports."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Test with empty report
        result = analyzer.analyze_strategy_selection({})

        assert isinstance(result, dict)
        assert "error" in result or "warning" in result

    def test_prompt_generation_methods(self):
        """Test that prompt generation methods exist and work."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        report = {"strategy_performance": {}, "system_info": {"system_type": "brush_scoring"}}

        # These methods should exist and generate prompts
        strategy_prompt = analyzer._generate_strategy_analysis_prompt(report)
        assert isinstance(strategy_prompt, str)
        assert "strategy" in strategy_prompt.lower()
        assert "brush_scoring" in strategy_prompt.lower()

        modifier_prompt = analyzer._generate_modifier_performance_prompt(report)
        assert isinstance(modifier_prompt, str)
        assert "modifier" in modifier_prompt.lower()

        pattern_prompt = analyzer._generate_pattern_discovery_prompt(report)
        assert isinstance(pattern_prompt, str)
        assert "pattern" in pattern_prompt.lower()

    def test_response_parsing_methods(self):
        """Test that response parsing methods exist and work."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # These methods should exist and parse responses
        valid_json = '{"weight_adjustments": {"known_brush": 85.0}, "reasoning": "test"}'
        strategy_result = analyzer._parse_strategy_analysis_response(valid_json)
        assert isinstance(strategy_result, dict)
        assert "analysis_type" in strategy_result
        assert strategy_result["analysis_type"] == "strategy_selection"

        modifier_result = analyzer._parse_modifier_performance_response(valid_json)
        assert isinstance(modifier_result, dict)
        assert "analysis_type" in modifier_result
        assert modifier_result["analysis_type"] == "modifier_performance"

        pattern_result = analyzer._parse_pattern_discovery_response(valid_json)
        assert isinstance(pattern_result, dict)
        assert "analysis_type" in pattern_result
        assert pattern_result["analysis_type"] == "pattern_discovery"

    def test_api_key_validation(self):
        """Test API key validation."""
        # Should work with valid API key
        analyzer = BrushChatGPTAnalyzer("sk-test123")
        assert analyzer.api_key == "sk-test123"

        # Should handle None API key gracefully
        analyzer_no_key = BrushChatGPTAnalyzer(None)
        report = {"strategy_performance": {}}

        result = analyzer_no_key.analyze_strategy_selection(report)
        assert isinstance(result, dict)
        assert "error" in result or "warning" in result


class TestBrushChatGPTAnalyzerIntegration:
    """Integration tests for brush ChatGPT analyzer."""

    def test_integration_with_learning_reports(self):
        """Test integration with actual learning reports from BrushLearningReportGenerator."""
        # This will help ensure compatibility with the learning report generator
        from sotd.learning.brush_learning_report_generator import BrushLearningReportGenerator

        validation_data = [
            {
                "input_text": "Omega 10098 Boar",
                "action": "validated",
                "system_choice": {"strategy": "known_brush", "score": 80.0},
                "all_strategies": [{"strategy": "known_brush", "score": 80.0}],
            }
        ]

        # Generate reports using the learning report generator
        generator = BrushLearningReportGenerator(validation_data)
        strategy_report = generator.generate_strategy_analysis_report()
        modifier_report = generator.generate_modifier_performance_report()
        pattern_report = generator.generate_pattern_discovery_report()

        # Test ChatGPT analyzer with real reports
        analyzer = BrushChatGPTAnalyzer("test-api-key")

        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {"weight_adjustments": {"known_brush": 85.0}}

            result = analyzer.analyze_strategy_selection(strategy_report)
            assert isinstance(result, dict)

            # Verify the analyzer can work with real report structure
            assert mock_call.called

    def test_yaml_output_format_compatibility(self):
        """Test that output format is compatible with YAML configuration."""
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        # Mock a response that should be YAML-compatible
        with patch.object(analyzer, "_call_chatgpt") as mock_call:
            mock_call.return_value = {
                "weight_adjustments": {
                    "high_priority_automated_split": {"multiple_brands": 25, "fiber_words": 18}
                },
                "suggested_new_modifiers": [
                    {
                        "name": "custom_handle",
                        "function_name": "_modifier_custom_handle",
                        "pattern": "custom|artisan|handmade",
                        "suggested_weights": {
                            "high_priority_automated_split": 15,
                            "dual_component": 20,
                        },
                    }
                ],
            }

            report = {"strategy_performance": {}}
            result = analyzer.analyze_strategy_selection(report)

            # Result should be YAML-serializable
            import yaml

            yaml_output = yaml.dump(result)
            assert isinstance(yaml_output, str)
            assert "weight_adjustments" in yaml_output

    def test_configuration_update_workflow_integration(self):
        """Test integration with configuration update workflow."""
        # This test will fail initially - we need to implement this
        api_key = "test-api-key"
        analyzer = BrushChatGPTAnalyzer(api_key)

        with pytest.raises(AttributeError):
            # This method doesn't exist yet
            # Type ignore for test - we're testing that the method doesn't exist
            analyzer.generate_configuration_update_suggestions({"strategy_performance": {}})  # type: ignore
