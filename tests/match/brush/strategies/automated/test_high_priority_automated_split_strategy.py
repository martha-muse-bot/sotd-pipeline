#!/usr/bin/env python3
"""Tests for HighPriorityAutomatedSplitStrategy.

This strategy wraps the legacy system's high_priority_automated_split logic
to integrate with the scoring system architecture.
"""

from unittest.mock import Mock

import pytest

from sotd.match.brush.strategies.automated.high_priority_automated_split_strategy import (
    HighPriorityAutomatedSplitStrategy,
)
from sotd.match.types import create_match_result


class TestHighPriorityAutomatedSplitStrategy:
    """Test HighPriorityAutomatedSplitStrategy functionality."""

    @pytest.fixture
    def mock_legacy_matcher(self):
        """Create mock legacy matcher."""
        mock_matcher = Mock()
        mock_matcher.brush_splits_loader = Mock()
        mock_matcher.brush_splitter = Mock()
        mock_matcher.handle_matcher = Mock()
        mock_matcher.knot_matcher = Mock()
        return mock_matcher

    @pytest.fixture
    def mock_scoring_config(self):
        """Create mock scoring config."""
        mock_config = Mock()
        mock_config.get_component_scoring_weight.return_value = 5.0
        return mock_config

    @pytest.fixture
    def strategy(self, mock_legacy_matcher, mock_scoring_config):
        """Create HighPriorityAutomatedSplitStrategy instance."""
        return HighPriorityAutomatedSplitStrategy(mock_legacy_matcher, mock_scoring_config)

    def test_strategy_initialization(self, strategy):
        """Test strategy initializes correctly."""
        assert strategy.legacy_matcher is not None
        assert strategy.scoring_config is not None
        assert strategy.strategy_name == "high_priority_automated_split"

    def test_match_with_should_not_split_returns_none(self, strategy, mock_legacy_matcher):
        """Test that should_not_split returns None."""
        # Setup
        mock_legacy_matcher._match_high_priority_automated_split.return_value = None
        test_input = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Execute
        result = strategy.match(test_input)

        # Verify
        assert result is None
        mock_legacy_matcher._match_high_priority_automated_split.assert_called_once_with(test_input)

    def test_match_with_curated_split_returns_result(self, strategy, mock_legacy_matcher):
        """Test that curated split returns proper result."""
        # Setup
        mock_result = create_match_result(
            original="Wolf Whiskers RCE 1301 w/ Omega 10049 Boar",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Wolf Whiskers", "model": "RCE 1301"},
                "knot": {"brand": "Omega", "model": "10049", "fiber": "boar"},
            },
            match_type="regex",
            pattern="curated_split",
            strategy="high_priority_automated_split",
        )
        mock_legacy_matcher._match_high_priority_automated_split.return_value = mock_result

        test_input = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Execute
        result = strategy.match(test_input)

        # Verify
        assert result is not None
        assert result.strategy == "high_priority_automated_split"
        assert result.match_type == "regex"
        assert result.matched["handle"]["brand"] == "Wolf Whiskers"
        assert result.matched["knot"]["brand"] == "Omega"

    def test_match_with_automated_split_returns_result(self, strategy, mock_legacy_matcher):
        """Test that automated split returns proper result."""
        # Setup
        mock_result = create_match_result(
            original="Wolf Whiskers RCE 1301 w/ Omega 10049 Boar",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Wolf Whiskers", "model": "RCE 1301"},
                "knot": {"brand": "Omega", "model": "10049", "fiber": "boar"},
            },
            match_type="regex",
            pattern="high_reliability",
            strategy="high_priority_automated_split",
        )
        mock_legacy_matcher._match_high_priority_automated_split.return_value = mock_result

        test_input = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Execute
        result = strategy.match(test_input)

        # Verify
        assert result is not None
        assert result.strategy == "high_priority_automated_split"
        assert result.match_type == "regex"
        assert result.matched["handle"]["brand"] == "Wolf Whiskers"
        assert result.matched["knot"]["brand"] == "Omega"

    def test_match_with_no_split_returns_none(self, strategy, mock_legacy_matcher):
        """Test that no split returns None."""
        # Setup
        mock_legacy_matcher._match_high_priority_automated_split.return_value = None

        test_input = "Simpson Chubby 2"

        # Execute
        result = strategy.match(test_input)

        # Verify
        assert result is None

    def test_match_with_empty_input_returns_none(self, strategy):
        """Test that empty input returns None."""
        # Execute
        result = strategy.match("")
        result2 = strategy.match(None)

        # Verify
        assert result is None
        assert result2 is None

    def test_match_preserves_legacy_behavior(self, strategy, mock_legacy_matcher):
        """Test that strategy preserves legacy system behavior exactly."""
        # Setup - simulate legacy system behavior
        mock_result = create_match_result(
            original="Declaration Grooming w/ B15",
            matched={
                "brand": "Declaration Grooming",  # Same brand for both
                "model": None,  # Legacy system uses None for composite brushes
                "handle": {"brand": "Declaration Grooming", "model": None},
                "knot": {"brand": "Declaration Grooming", "model": "B15", "fiber": "badger"},
            },
            match_type="regex",
            pattern="high_reliability",
            strategy="high_priority_automated_split",
        )
        mock_legacy_matcher._match_high_priority_automated_split.return_value = mock_result

        test_input = "Declaration Grooming w/ B15"

        # Execute
        result = strategy.match(test_input)

        # Verify legacy behavior is preserved
        assert result is not None
        assert result.strategy == "high_priority_automated_split"
        assert result.match_type == "regex"
        assert result.matched["brand"] == "Declaration Grooming"  # Same brand for both
        assert result.matched["model"] is None  # Legacy system uses None for composite brushes
        assert result.matched["handle"]["brand"] == "Declaration Grooming"
        assert result.matched["knot"]["brand"] == "Declaration Grooming"

    def test_match_handles_exceptions_gracefully(self, strategy, mock_legacy_matcher):
        """Test that strategy handles exceptions gracefully."""
        # Setup
        mock_legacy_matcher._match_high_priority_automated_split.side_effect = Exception(
            "Test error"
        )

        test_input = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Execute and verify exception is raised (fail-fast behavior)
        with pytest.raises(Exception, match="Test error"):
            strategy.match(test_input)
