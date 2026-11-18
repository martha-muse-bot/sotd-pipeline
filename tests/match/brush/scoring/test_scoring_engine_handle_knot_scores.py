"""Tests for scoring engine handle/knot score modifiers using actual matcher scores."""

from unittest.mock import Mock

from sotd.match.brush.config import BrushScoringConfig
from sotd.match.brush.scoring.engine import ScoringEngine
from sotd.match.types import MatchResult


class TestScoringEngineHandleKnotScores:
    """Test that scoring engine uses actual matcher scores, not hardcoded base scores."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = BrushScoringConfig()
        self.engine = ScoringEngine(self.config)

    def test_handle_weight_modifier_calculates_handle_score_externally(self):
        """Test that handle_weight modifier calculates handle score externally."""
        # Create a mock result with handle data (no pre-calculated score)
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "handle": {
                "brand": "Test Brand",
                "model": "Test Model",
                "priority": 1,
                "_matched_by": "HandleMatcher",
                "_pattern_used": "test_pattern",
            }
        }

        # Calculate the handle weight modifier
        result = self.engine._modifier_handle_weight("test input", mock_result, "automated_split")

        # Should calculate score externally: brand(5) + model(5) + priority1(2) = 12
        expected_score = 12.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"

    def test_knot_weight_modifier_calculates_knot_score_externally(self):
        """Test that knot_weight modifier calculates knot score externally."""
        # Create a mock result with knot data (no pre-calculated score)
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "knot": {
                "brand": "Test Brand",
                "model": "Test Model",
                "fiber": "Badger",
                "priority": 2,
                "_matched_by": "KnotMatcher",
                "_pattern_used": "test_pattern",
            }
        }

        # Calculate the knot weight modifier
        result = self.engine._modifier_knot_weight("test input", mock_result, "automated_split")

        # Should calculate score externally: brand(5) + model(5) + fiber(5) + priority2(1) = 16
        expected_score = 16.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"

    def test_handle_weight_modifier_with_zero_score(self):
        """Test that handle_weight modifier correctly handles zero score from matcher."""
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "handle": {
                "brand": None,
                "model": None,
                "score": 0.0,  # Zero score from handle matcher
                "priority": None,
                "_matched_by": "HandleMatcher",
                "_pattern_used": "no_match",
            }
        }

        result = self.engine._modifier_handle_weight("test input", mock_result, "automated_split")

        # Should return raw score (0.0)
        # Scoring engine will apply weight: 0.0 * 0.5 = 0.0
        expected_score = 0.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"

    def test_knot_weight_modifier_with_zero_score(self):
        """Test that knot_weight modifier correctly handles zero score from matcher."""
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "knot": {
                "brand": None,
                "model": None,
                "fiber": None,
                "score": 0.0,  # Zero score from knot matcher
                "priority": None,
                "_matched_by": "KnotMatcher",
                "_pattern_used": "no_match",
            }
        }

        result = self.engine._modifier_knot_weight("test input", mock_result, "automated_split")

        # Should return raw score (0.0)
        # Scoring engine will apply weight: 0.0 * 0.5 = 0.0
        expected_score = 0.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"

    def test_handle_weight_modifier_calculates_score_without_score_field(self):
        """Test that handle_weight modifier calculates score even without pre-calculated score field."""
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "handle": {
                "brand": "Test Brand",
                "model": "Test Model",
                # No score field - should calculate externally
                "priority": 1,
                "_matched_by": "HandleMatcher",
                "_pattern_used": "test_pattern",
            }
        }

        # Should calculate score externally: brand(5) + model(5) + priority1(2) = 12
        result = self.engine._modifier_handle_weight("test input", mock_result, "automated_split")
        expected_score = 12.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"

    def test_knot_weight_modifier_calculates_score_without_score_field(self):
        """Test that knot_weight modifier calculates score even without pre-calculated score field."""
        mock_result = Mock(spec=MatchResult)
        mock_result.matched = {
            "knot": {
                "brand": "Test Brand",
                "model": "Test Model",
                "fiber": "Badger",
                # No score field - should calculate externally
                "priority": 2,
                "_matched_by": "KnotMatcher",
                "_pattern_used": "test_pattern",
            }
        }

        # Should calculate score externally: brand(5) + model(5) + fiber(5) + priority2(1) = 16
        result = self.engine._modifier_knot_weight("test input", mock_result, "automated_split")
        expected_score = 16.0
        assert result == expected_score, f"Expected {expected_score}, got {result}"
