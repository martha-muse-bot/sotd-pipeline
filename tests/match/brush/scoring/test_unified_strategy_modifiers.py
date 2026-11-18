#!/usr/bin/env python3
"""Tests for full input component matching strategy modifiers."""

import tempfile
from pathlib import Path

import yaml

from sotd.match.brush.config import BrushScoringConfig
from sotd.match.brush.scoring.engine import ScoringEngine
from sotd.match.types import MatchResult


class TestFullInputComponentMatchingStrategyModifiers:
    """Test that full input component matching strategy modifiers work correctly."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a temporary config file for testing to insulate from production data changes
        test_config = {
            "brush_scoring_weights": {
                "base_strategies": {
                    "full_input_component_matching": 50.0,  # Test-specific base score
                    "dual_component": 60.0,
                },
                "strategy_modifiers": {
                    "full_input_component_matching": {
                        "dual_component": 15.0,
                        "multiple_brands": 20.0,
                        "fiber_mismatch": -15.0,
                        "size_specification": 0.0,
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

    def test_dual_component_modifier_returns_1_0_when_both_handle_and_knot_match(self):
        """Test that dual_component modifier returns 1.0 when both handle and knot match."""
        # Create a result with both handle and knot sections
        result = MatchResult(
            original="Declaration Grooming Washington B2",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": "Washington"},
                "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "Badger"},
            },
            match_type="composite",
            pattern="dual_component",
            strategy="full_input_component_matching",
        )

        # Test the modifier directly
        modifier_value = self.scoring_engine._modifier_dual_component(
            "Declaration Grooming Washington B2",
            result.matched or {},
            "full_input_component_matching",
        )

        assert modifier_value == 1.0

    def test_dual_component_modifier_returns_0_0_when_only_handle_matches(self):
        """Test that dual_component modifier returns 0.0 when only handle matches."""
        # Create a result with only handle section
        result = MatchResult(
            original="Declaration Grooming Washington",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": "Washington"},
                "knot": {"brand": None, "model": None},
            },
            match_type="single_component",
            pattern="handle_only",
            strategy="full_input_component_matching",
        )

        # Test the modifier directly
        modifier_value = self.scoring_engine._modifier_dual_component(
            "Declaration Grooming Washington", result.matched or {}, "full_input_component_matching"
        )

        assert modifier_value == 0.0

    def test_dual_component_modifier_returns_0_0_for_non_unified_strategy(self):
        """Test that dual_component modifier returns 0.0 for non-unified strategies."""
        result = MatchResult(
            original="Declaration Grooming Washington B2",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": "Washington"},
                "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "Badger"},
            },
            match_type="composite",
            pattern="dual_component",
            strategy="dual_component",  # Not unified
        )

        # Test the modifier directly
        modifier_value = self.scoring_engine._modifier_dual_component(
            "Declaration Grooming Washington B2", result.matched or {}, "dual_component"
        )

        assert modifier_value == 0.0

    def test_unified_strategy_scoring_with_dual_component_modifier(self):
        """Test that unified strategy gets correct score with dual component modifier."""
        # Create a result with both handle and knot sections
        result = MatchResult(
            original="Declaration Grooming Washington B2",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": "Washington"},
                "knot": {"brand": "Declaration Grooming", "model": "B2", "fiber": "Badger"},
            },
            match_type="composite",
            pattern="dual_component",
            strategy="full_input_component_matching",
        )

        # Score the result
        input_text = "Declaration Grooming Washington B2"
        scored_results = self.scoring_engine.score_results([result], input_text)
        scored_result = scored_results[0]

        # Base score 50 + dual_component modifier 15 = 65
        assert scored_result.score == 65.0

    def test_unified_strategy_scoring_without_dual_component_modifier(self):
        """Test that unified strategy gets correct score without dual component modifier."""
        # Create a result with only handle section
        result = MatchResult(
            original="Declaration Grooming Washington",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": "Washington"},
                "knot": {"brand": None, "model": None},
            },
            match_type="single_component",
            pattern="handle_only",
            strategy="full_input_component_matching",
        )

        # Score the result
        input_text = "Declaration Grooming Washington"
        scored_results = self.scoring_engine.score_results([result], input_text)
        scored_result = scored_results[0]

        # Base score 50 (no modifier)
        assert scored_result.score == 50.0
