"""Tests for StrategyAnalyzer."""

from pathlib import Path
from unittest.mock import Mock, patch

from sotd.optimization.strategy_analyzer import StrategyAnalyzer


class TestStrategyAnalyzer:
    """Test cases for StrategyAnalyzer."""

    def test_init(self, tmp_path):
        """Test StrategyAnalyzer initialization."""
        config_path = tmp_path / "config.yaml"
        correct_matches_path = tmp_path / "correct_matches.yaml"

        # Create minimal test files
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
  strategy_modifiers:
    handle_matching: {}
    knot_matching: {}
""")

        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)

        assert analyzer.config_path == config_path
        assert analyzer.correct_matches_path == correct_matches_path
        assert len(analyzer.test_cases) == 1
        assert analyzer.test_cases[0]["input"] == "test brush input"
        assert "known_brush" in analyzer.strategy_names
        assert "automated_split" in analyzer.strategy_names

    def test_extract_test_cases_complete_brush(self, tmp_path):
        """Test extraction of complete brush test cases."""
        # Create a minimal config file
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
""")

        correct_matches_path = tmp_path / "correct_matches.yaml"
        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input 1
      - test brush input 2
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)

        assert len(analyzer.test_cases) == 2
        assert analyzer.test_cases[0]["expected_type"] == "complete"
        assert analyzer.test_cases[0]["category"] == "brush"
        assert analyzer.test_cases[0]["brand"] == "Test Brand"
        assert analyzer.test_cases[0]["model"] == "Test Model"

    def test_extract_test_cases_composite_handle(self, tmp_path):
        """Test extraction of composite handle test cases."""
        # Create a minimal config file
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
""")

        correct_matches_path = tmp_path / "correct_matches.yaml"
        correct_matches_path.write_text("""
handle:
  Test Maker:
    Test Handle:
      - test handle input 1
      - test handle input 2
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)

        assert len(analyzer.test_cases) == 2
        assert analyzer.test_cases[0]["expected_type"] == "composite"
        assert analyzer.test_cases[0]["category"] == "handle"
        assert analyzer.test_cases[0]["maker"] == "Test Maker"
        assert analyzer.test_cases[0]["model"] == "Test Handle"

    def test_extract_test_cases_composite_knot(self, tmp_path):
        """Test extraction of composite knot test cases."""
        # Create a minimal config file
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
""")

        correct_matches_path = tmp_path / "correct_matches.yaml"
        correct_matches_path.write_text("""
knot:
  Test Brand:
    Test Knot:
      - test knot input 1
      - test knot input 2
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)

        assert len(analyzer.test_cases) == 2
        assert analyzer.test_cases[0]["expected_type"] == "composite"
        assert analyzer.test_cases[0]["category"] == "knot"
        assert analyzer.test_cases[0]["brand"] == "Test Brand"
        assert analyzer.test_cases[0]["model"] == "Test Knot"

    def test_get_strategy_names(self, tmp_path):
        """Test extraction of strategy names from config."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
    omega_semogue_brush: 75.0
  strategy_modifiers:
    handle_matching: {}
    knot_matching:
      brand_match: 12.0
""")

        # Create a minimal correct_matches.yaml file
        correct_matches_path = tmp_path / "correct_matches.yaml"
        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)

        expected_strategies = [
            "automated_split",
            "handle_matching",
            "knot_matching",
            "known_brush",
            "omega_semogue_brush",
        ]

        assert set(analyzer.strategy_names) == set(expected_strategies)

    @patch("sotd.optimization.strategy_analyzer.BrushMatcher")
    def test_analyze_strategies_success(self, mock_brush_matcher, tmp_path):
        """Test successful strategy analysis."""
        config_path = tmp_path / "config.yaml"
        correct_matches_path = tmp_path / "correct_matches.yaml"

        # Create test files
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
""")

        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input
""")

        # Mock brush matcher
        mock_result = Mock()
        mock_result.matched = {
            "_matched_by_strategy": "known_brush",
            "_pattern_used": "exact_match",
            "brand": "Test Brand",
            "model": "Test Model",
        }

        mock_matcher = Mock()
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher.return_value = mock_matcher

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)
        results = analyzer.analyze_strategies()

        # Verify results
        assert results["overall_stats"]["total_test_cases"] == 1
        assert results["overall_stats"]["successful_matches"] == 1
        assert results["overall_stats"]["success_rate"] == 1.0
        assert results["strategy_performance"]["wins"]["known_brush"] == 1

    @patch("sotd.optimization.strategy_analyzer.BrushMatcher")
    def test_analyze_strategies_no_match(self, mock_brush_matcher, tmp_path):
        """Test strategy analysis with no match."""
        config_path = tmp_path / "config.yaml"
        correct_matches_path = tmp_path / "correct_matches.yaml"

        # Create test files
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
""")

        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input
""")

        # Mock brush matcher returning no match
        mock_matcher = Mock()
        mock_matcher.match.return_value = None
        mock_brush_matcher.return_value = mock_matcher

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)
        results = analyzer.analyze_strategies()

        # Verify results
        assert results["overall_stats"]["total_test_cases"] == 1
        assert results["overall_stats"]["successful_matches"] == 0
        assert results["overall_stats"]["success_rate"] == 0.0
        assert results["strategy_performance"]["failures"]["no_match"] == 1

    def test_generate_recommendations_no_analysis(self, tmp_path):
        """Test recommendations generation without analysis."""
        # Create minimal test files
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
""")

        correct_matches_path = tmp_path / "correct_matches.yaml"
        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input
""")

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)
        recommendations = analyzer.generate_recommendations()

        assert "error" in recommendations
        assert "No analysis results available" in recommendations["error"]

    @patch("sotd.optimization.strategy_analyzer.BrushMatcher")
    def test_generate_recommendations_with_analysis(self, mock_brush_matcher, tmp_path):
        """Test recommendations generation with analysis results."""
        config_path = tmp_path / "config.yaml"
        correct_matches_path = tmp_path / "correct_matches.yaml"

        # Create test files
        config_path.write_text("""
brush_scoring_weights:
  base_strategies:
    known_brush: 80.0
    automated_split: 60.0
""")

        correct_matches_path.write_text("""
brush:
  Test Brand:
    Test Model:
      - test brush input 1
      - test brush input 2
""")

        # Mock brush matcher
        mock_result = Mock()
        mock_result.matched = {
            "_matched_by_strategy": "known_brush",
            "_pattern_used": "exact_match",
        }

        mock_matcher = Mock()
        mock_matcher.match.return_value = mock_result
        mock_brush_matcher.return_value = mock_matcher

        analyzer = StrategyAnalyzer(config_path, correct_matches_path)
        analyzer.analyze_strategies()
        recommendations = analyzer.generate_recommendations()

        # Verify recommendations
        assert "known_brush" in recommendations["base_strategy_weights"]
        assert recommendations["base_strategy_weights"]["known_brush"] >= 20
        assert "known_brush" in recommendations["rationale"]
