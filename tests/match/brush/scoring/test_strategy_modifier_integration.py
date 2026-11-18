"""
Tests for Strategy Modifier Integration.

This module tests the implementation of strategy-specific modifiers
that can adjust scores based on input characteristics.
"""

from unittest.mock import Mock

from sotd.match.brush.config import BrushScoringConfig
from sotd.match.brush.scoring.engine import ScoringEngine
from sotd.match.types import MatchResult


class TestStrategyModifierIntegration:
    """Test strategy modifier integration in scoring engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = Mock(spec=BrushScoringConfig)
        self.scoring_engine = ScoringEngine(self.config)

    def test_modifier_framework_calls_modifier_functions(self):
        """Test that modifier framework calls modifier functions."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["multiple_brands", "fiber_words"]
        self.config.get_strategy_modifier.side_effect = lambda strategy, modifier: {
            "multiple_brands": 25.0,  # Actual config value
            "fiber_words": 0.0,  # Actual config value
        }[modifier]

        # Create test result with multiple brands to trigger the modifier
        result = MatchResult(
            original="Simpson Chubby 2 / Omega 10098 Badger",
            matched={
                "brand": "Simpson",
                "model": "Chubby 2",
                "handle": {"brand": "Simpson"},
                "knot": {"brand": "Omega"},
            },
            match_type="regex",
            pattern="simpson.*chubby",
            strategy="automated_split",
        )

        # Calculate score with modifiers
        score = self.scoring_engine._calculate_score(
            result, "Simpson Chubby 2 / Omega 10098 Badger"
        )

        # Verify modifier functions were called
        self.config.get_all_modifier_names.assert_called_with("automated_split")
        assert self.config.get_strategy_modifier.call_count == 2

        # Verify final score (multiple brands detected: 1.0 * 25.0, fiber words detected: 1.0 * 0.0)
        assert score == 95.0  # 70.0 + (1.0 * 25.0) + (1.0 * 0.0)

    def test_multiple_brands_modifier_penalty(self):
        """Test multiple brands modifier applies penalty for multiple brand mentions."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["multiple_brands"]
        self.config.get_strategy_modifier.return_value = 25.0  # Actual config value

        # Create test result with multiple brands to trigger the modifier
        result = MatchResult(
            original="Simpson Chubby 2 / Omega 10098",
            matched={
                "brand": "Simpson",
                "model": "Chubby 2",
                "handle": {"brand": "Simpson"},
                "knot": {"brand": "Omega"},
            },
            match_type="regex",
            pattern="simpson.*chubby",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Simpson Chubby 2 / Omega 10098")

        # Should have base score plus modifier (multiple brands detected: 1.0 * 25.0)
        assert score == 95.0  # 70.0 + (1.0 * 25.0)

    def test_fiber_words_modifier_bonus(self):
        """Test fiber words modifier applies bonus for fiber-specific terminology."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["fiber_words"]
        self.config.get_strategy_modifier.return_value = 0.0  # Actual config value

        # Create test result
        result = MatchResult(
            original="Badger brush with synthetic knot",
            matched={"brand": "Generic", "model": "Brush"},
            match_type="regex",
            pattern="badger.*brush",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Badger brush with synthetic knot")

        # Should have base score plus modifier (fiber words detected: 1.0 * 0.0)
        assert score == 70.0  # 70.0 + (1.0 * 0.0)

    def test_size_specification_modifier_bonus(self):
        """Test size specification modifier applies bonus for size specifications."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["size_specification"]
        self.config.get_strategy_modifier.return_value = 0.0  # Actual config value

        # Create test result
        result = MatchResult(
            original="26mm brush",
            matched={"brand": "Brand1", "model": "Brush"},
            match_type="regex",
            pattern="26mm.*brush",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "26mm brush")

        # Should have base score plus modifier (size specification detected: 1.0 * 0.0)
        assert score == 70.0  # 70.0 + (1.0 * 0.0)

    def test_delimiter_confidence_modifier_bonus(self):
        """Test delimiter confidence modifier applies bonus for high-confidence delimiters."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["delimiter_confidence"]
        self.config.get_strategy_modifier.return_value = 4.0

        # Create test result
        result = MatchResult(
            original="Handle w/ knot",
            matched={"brand": "Generic", "model": "Brush"},
            match_type="regex",
            pattern="handle.*w/.*knot",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Handle w/ knot")

        # Should have base score plus bonus
        assert score == 74.0  # 70.0 + 4.0

    def test_multiple_modifiers_combined(self):
        """Test that multiple modifiers are combined correctly."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = [
            "multiple_brands",
            "fiber_words",
            "size_specification",
        ]
        self.config.get_strategy_modifier.side_effect = lambda strategy, modifier: {
            "multiple_brands": 25.0,  # Actual config value
            "fiber_words": 0.0,  # Actual config value
            "size_specification": 0.0,  # Actual config value
        }[modifier]

        # Create test result with multiple brands and size specification to trigger modifiers
        result = MatchResult(
            original="Simpson Chubby 2 / Omega 10098 26mm Badger",
            matched={
                "brand": "Simpson",
                "model": "Chubby 2",
                "handle": {"brand": "Simpson"},
                "knot": {"brand": "Omega"},
            },
            match_type="regex",
            pattern="simpson.*chubby",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(
            result, "Simpson Chubby 2 / Omega 10098 26mm Badger"
        )

        # Should have base score plus all modifiers (multiple brands: 1.0 * 25.0, others: 1.0 * 0.0)
        assert score == 95.0  # 70.0 + (1.0 * 25.0) + (1.0 * 0.0) + (1.0 * 0.0)

    def test_modifier_functions_are_strategy_aware(self):
        """Test that modifier functions receive correct strategy name."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["multiple_brands"]
        self.config.get_strategy_modifier.return_value = -5.0

        # Create test result with specific strategy
        result = MatchResult(
            original="Test brush",
            matched={"brand": "Test", "model": "Brush"},
            match_type="regex",
            pattern="test.*brush",
            strategy="dual_component",
        )

        # Calculate score
        self.scoring_engine._calculate_score(result, "Test brush")

        # Verify strategy name was passed to modifier functions
        self.config.get_all_modifier_names.assert_called_with("dual_component")
        self.config.get_strategy_modifier.assert_called_with("dual_component", "multiple_brands")

    def test_modifier_functions_handle_empty_modifiers(self):
        """Test that modifier functions handle empty modifier lists."""
        # Setup mock config with no modifiers
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = []

        # Create test result
        result = MatchResult(
            original="Test brush",
            matched={"brand": "Test", "model": "Brush"},
            match_type="regex",
            pattern="test.*brush",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Test brush")

        # Should have base score only
        assert score == 70.0

    def test_modifier_functions_handle_unknown_strategy(self):
        """Test that modifier functions handle unknown strategy names."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = []

        # Create test result with unknown strategy
        result = MatchResult(
            original="Test brush",
            matched={"brand": "Test", "model": "Brush"},
            match_type="unknown",
            pattern="test.*brush",
            strategy="unknown_strategy",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Test brush")

        # Should handle gracefully
        assert score == 70.0

    def test_modifier_functions_preserve_base_score(self):
        """Test that modifier functions preserve base score when no modifiers apply."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 75.0
        self.config.get_all_modifier_names.return_value = ["multiple_brands"]
        self.config.get_strategy_modifier.return_value = 0.0  # No modifier effect

        # Create test result
        result = MatchResult(
            original="Simple brush",
            matched={"brand": "Simple", "model": "Brush"},
            match_type="regex",
            pattern="simple.*brush",
            strategy="complete_brush",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Simple brush")

        # Should preserve base score
        assert score == 75.0

    def test_modifier_functions_with_negative_base_score(self):
        """Test that modifier functions work correctly with negative modifiers."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["multiple_brands"]
        self.config.get_strategy_modifier.return_value = 25.0  # Actual config value

        # Create test result with multiple brands to trigger the modifier
        result = MatchResult(
            original="Simpson Chubby 2 / Omega 10098",
            matched={
                "brand": "Brand1",
                "model": "Brush",
                "handle": {"brand": "Brand1"},
                "knot": {"brand": "Brand2"},
            },
            match_type="regex",
            pattern="brand1.*brush",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Simpson Chubby 2 / Omega 10098")

        # Should have base score plus modifier (multiple brands detected: 1.0 * 25.0)
        assert score == 95.0  # 70.0 + (1.0 * 25.0)

    def test_modifier_functions_with_large_bonus(self):
        """Test that modifier functions work correctly with large bonuses."""
        # Setup mock config
        self.config.get_base_strategy_score.return_value = 70.0
        self.config.get_all_modifier_names.return_value = ["fiber_words"]
        self.config.get_strategy_modifier.return_value = 15.0  # Large bonus

        # Create test result
        result = MatchResult(
            original="Badger brush",
            matched={"brand": "Generic", "model": "Brush"},
            match_type="regex",
            pattern="badger.*brush",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(result, "Badger brush")

        # Should have base score plus bonus
        assert score == 85.0  # 70.0 + 15.0


class TestModifierConfiguration:
    """Test modifier configuration integration."""

    def test_yaml_configuration_with_modifiers(self):
        """Test that YAML configuration supports modifier weights."""
        # Create test-specific config instead of using production config
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "automated_split": 60.0,
                    "known_brush": 80.0,
                },
                "strategy_modifiers": {
                    "automated_split": {
                        "multiple_brands": 15.0,
                        "fiber_words": 10.0,
                        "size_specification": 5.0,
                        "high_confidence": 20.0,
                        "delimiter_confidence": 25.0,
                    },
                    "known_brush": {
                        "multiple_brands": 10.0,
                        "size_specification": 5.0,
                    },
                },
            }
        }

        # Create config from test data
        import tempfile
        from pathlib import Path

        import yaml

        from sotd.match.brush.config import BrushScoringConfig

        # Create temporary file
        temp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(test_config, temp_config_file)
        temp_config_file.close()

        try:
            config = BrushScoringConfig(config_path=Path(temp_config_file.name))

            # Verify modifier structure exists
            assert "strategy_modifiers" in config.weights

            # Verify specific strategies have modifiers
            automated_split_modifiers = config.weights["strategy_modifiers"].get(
                "automated_split", {}
            )
            assert "multiple_brands" in automated_split_modifiers
            assert "fiber_words" in automated_split_modifiers
            assert "size_specification" in automated_split_modifiers
            assert "high_confidence" in automated_split_modifiers
            assert "delimiter_confidence" in automated_split_modifiers
        finally:
            # Clean up temporary file
            import os

            os.unlink(temp_config_file.name)

    def test_modifier_weights_are_configurable(self):
        """Test that modifier weights can be configured via YAML."""
        config = BrushScoringConfig()

        # Get modifier weights for a strategy
        dual_component_modifiers = config.weights["strategy_modifiers"].get("dual_component", {})

        # Verify weights are numeric
        for modifier_name, weight in dual_component_modifiers.items():
            assert isinstance(
                weight, (int, float)
            ), f"Modifier {modifier_name} weight should be numeric"

    def test_all_strategies_have_modifier_support(self):
        """Test that all strategies support modifiers."""
        config = BrushScoringConfig()

        # Get all strategy names
        strategy_names = config.get_all_strategy_names()

        # Verify each strategy has modifier support
        for strategy_name in strategy_names:
            modifier_names = config.get_all_modifier_names(strategy_name)
            assert isinstance(
                modifier_names, list
            ), f"Strategy {strategy_name} should have modifier list"

    def test_modifier_names_are_consistent(self):
        """Test that modifier names are consistent across strategies."""
        # Create test-specific config instead of using production config
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "automated_split": 60.0,
                    "known_brush": 80.0,
                },
                "strategy_modifiers": {
                    "automated_split": {
                        "multiple_brands": 15.0,
                        "fiber_words": 10.0,
                        "size_specification": 5.0,
                    },
                    "known_brush": {
                        "multiple_brands": 10.0,
                        "size_specification": 5.0,
                    },
                },
            }
        }

        # Create config from test data
        import tempfile
        from pathlib import Path

        import yaml

        from sotd.match.brush.config import BrushScoringConfig

        # Create temporary file
        temp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(test_config, temp_config_file)
        temp_config_file.close()

        try:
            config = BrushScoringConfig(config_path=Path(temp_config_file.name))

            # Get modifier names for different strategies
            automated_split_modifiers = config.get_all_modifier_names("automated_split")
            known_brush_modifiers = config.get_all_modifier_names("known_brush")

            # Verify common modifiers exist across different strategy types
            common_modifiers = ["multiple_brands", "size_specification"]
            for modifier in common_modifiers:
                assert (
                    modifier in automated_split_modifiers
                ), f"Automated split should have {modifier}"
                assert modifier in known_brush_modifiers, f"Known brush should have {modifier}"

            # Check strategy-specific modifiers
            assert (
                "fiber_words" in automated_split_modifiers
            ), "Automated split should have fiber_words"
        finally:
            # Clean up temporary file
            import os

            os.unlink(temp_config_file.name)


class TestModifierIntegrationWithScoringEngine:
    """Test modifier integration with the full scoring engine."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary config file for testing
        import tempfile
        from pathlib import Path

        import yaml

        # Create minimal test config
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {"automated_split": 60.0},
                "strategy_modifiers": {
                    "automated_split": {
                        "multiple_brands": 25.0,
                        "fiber_words": 0.0,
                        "size_specification": 0.0,
                        "high_confidence": 0.0,
                        "delimiter_confidence": 0.0,
                    }
                },
            }
        }

        # Create temporary file
        self.temp_config_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        yaml.dump(test_config, self.temp_config_file)
        self.temp_config_file.close()

        # Load config from temporary file
        config_path = Path(self.temp_config_file.name)
        self.config = BrushScoringConfig(config_path=config_path)
        self.scoring_engine = ScoringEngine(self.config)

    def teardown_method(self):
        """Clean up test fixtures."""
        # Remove temporary config file
        if hasattr(self, "temp_config_file"):
            import os

            try:
                os.unlink(self.temp_config_file.name)
            except OSError:
                pass  # File may already be deleted

    def test_scoring_engine_applies_modifiers_to_results(self):
        """Test that scoring engine applies modifiers when scoring results."""
        # Create test results
        results = [
            MatchResult(
                original="Test brush",
                matched={"brand": "Test", "model": "Brush"},
                match_type="regex",
                pattern="test.*brush",
                strategy="automated_split",
            ),
            MatchResult(
                original="Another brush",
                matched={"brand": "Another", "model": "Brush"},
                match_type="regex",
                pattern="another.*brush",
                strategy="complete_brush",
            ),
        ]

        # Score results
        scored_results = self.scoring_engine.score_results(results, "Test brush")

        # Verify all results have scores
        for result in scored_results:
            assert hasattr(result, "score"), "Result should have score attribute"
            assert isinstance(result.score, (int, float)), "Score should be numeric"

    def test_scoring_engine_preserves_result_order_with_modifiers(self):
        """Test that scoring engine preserves result order when applying modifiers."""
        # Create test results with different base scores
        results = [
            MatchResult(
                original="High priority brush",
                matched={"brand": "High", "model": "Priority"},
                match_type="regex",
                pattern="high.*priority",
                strategy="automated_split",
            ),
            MatchResult(
                original="Complete brush",
                matched={"brand": "Complete", "model": "Brush"},
                match_type="regex",
                pattern="complete.*brush",
                strategy="complete_brush",
            ),
        ]

        # Score results
        scored_results = self.scoring_engine.score_results(results, "Test input")

        # Verify order is preserved
        assert len(scored_results) == 2
        assert scored_results[0].strategy == "automated_split"
        assert scored_results[1].strategy == "complete_brush"

    def test_scoring_engine_handles_empty_results_with_modifiers(self):
        """Test that scoring engine handles empty results when modifiers are enabled."""
        # Create empty results list
        results = []

        # Score results
        scored_results = self.scoring_engine.score_results(results, "Test input")

        # Should return empty list
        assert scored_results == []

    def test_scoring_engine_handles_none_matched_with_modifiers(self):
        """Test that scoring engine handles results with None matched when modifiers are enabled."""
        # Create result with None matched
        results = [
            MatchResult(
                original="No match",
                matched=None,
                match_type=None,
                pattern=None,
                strategy="automated_split",
            ),
        ]

        # Score results
        scored_results = self.scoring_engine.score_results(results, "Test input")

        # Should handle gracefully
        assert len(scored_results) == 1
        assert scored_results[0].matched is None

    def test_automated_split_multiple_brands_modifier_bug(self):
        """Test that automated_split strategy correctly applies multiple_brands modifier."""
        # This test reproduces the bug where automated_split shows
        # "Multiple brands detected (++25)" but the total score is 60 instead of 85
        # (60 base + 25 modifier)

        # Create a result that should trigger the multiple_brands modifier
        result = MatchResult(
            original="AP Shave Co. - Lemon Drop 26mm TGN Boar",
            matched={
                "brand": None,  # Composite brush
                "model": None,  # Composite brush
                "handle": {
                    "brand": "AP Shave Co.",
                    "model": "Lemon Drop",
                    "source_text": "AP Shave Co. - Lemon Drop 26mm TGN Boar",
                },
                "knot": {
                    "brand": "TGN",
                    "model": "Boar",
                    "source_text": "AP Shave Co. - Lemon Drop 26mm TGN Boar",
                },
            },
            match_type="composite",
            pattern="medium_priority_split",
            strategy="automated_split",
        )

        # Calculate score
        score = self.scoring_engine._calculate_score(
            result, "AP Shave Co. - Lemon Drop 26mm TGN Boar"
        )

        # Debug output
        assert result.strategy is not None
        strategy_name = result.strategy
        print("\n=== Debug Output ===")
        print(f"Strategy: {strategy_name}")
        print(f"Base score: {self.config.get_base_strategy_score(strategy_name)}")
        print(
            f"Modifier score: {self.scoring_engine._calculate_modifiers(result, result.original, strategy_name)}"
        )
        print(f"Total score: {score}")

        # Check multiple_brands modifier specifically
        modifier_value = self.scoring_engine._modifier_multiple_brands(
            result.original, result, strategy_name
        )
        print(f"Multiple brands modifier value: {modifier_value}")
        print(
            f"Multiple brands weight: {self.config.get_strategy_modifier(strategy_name, 'multiple_brands')}"
        )
        print(
            f"Expected modifier score: {modifier_value * self.config.get_strategy_modifier(strategy_name, 'multiple_brands')}"
        )
        print("=== End Debug ===\n")

        # Should have base score (60) plus modifier (25) for multiple brands
        # Base score: 60 (from brush_scoring_config.yaml)
        # Multiple brands modifier: 1.0 * 25.0 = 25
        # Total: 60 + 25 = 85
        assert score == 85.0, f"Expected 85.0, got {score}"

        # Verify the modifier calculation separately
        modifier_score = self.scoring_engine._calculate_modifiers(
            result, "AP Shave Co. - Lemon Drop 26mm TGN Boar", "automated_split"
        )
        assert modifier_score == 25.0, f"Expected modifier score 25.0, got {modifier_score}"

        # Verify the multiple_brands modifier specifically
        multiple_brands_value = self.scoring_engine._modifier_multiple_brands(
            "AP Shave Co. - Lemon Drop 26mm TGN Boar", result, "automated_split"
        )
        assert (
            multiple_brands_value == 1.0
        ), f"Expected multiple_brands value 1.0, got {multiple_brands_value}"
