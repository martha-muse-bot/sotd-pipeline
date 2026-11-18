#!/usr/bin/env python3
"""Tests for MediumPriorityAutomatedSplitStrategy.

This strategy wraps the legacy system's medium_priority_automated_split logic
to integrate with the scoring system architecture.
"""

from unittest.mock import Mock

import pytest

from sotd.match.brush.strategies.automated.medium_priority_automated_split_strategy import (
    MediumPriorityAutomatedSplitStrategy,
)
from sotd.match.types import create_match_result


class TestMediumPriorityAutomatedSplitStrategy:
    """Test MediumPriorityAutomatedSplitStrategy functionality."""

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
        """Create MediumPriorityAutomatedSplitStrategy instance."""
        return MediumPriorityAutomatedSplitStrategy(mock_legacy_matcher, mock_scoring_config)

    def test_strategy_initialization(self, strategy):
        """Test strategy initializes correctly."""
        assert strategy.legacy_matcher is not None
        assert strategy.scoring_config is not None
        assert strategy.strategy_name == "medium_priority_automated_split"

    def test_match_with_successful_split_returns_result(self, strategy, mock_legacy_matcher):
        """Test that successful split returns proper result."""
        # Setup
        mock_result = create_match_result(
            original="Declaration Grooming - B15",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Declaration Grooming", "model": None},
                "knot": {"brand": "Declaration Grooming", "model": "B15", "fiber": "badger"},
            },
            match_type="regex",
            pattern="smart_analysis",
            strategy="medium_priority_automated_split",
        )
        mock_legacy_matcher._match_medium_priority_automated_split.return_value = mock_result

        test_input = "Declaration Grooming - B15"

        # Execute
        result = strategy.match(test_input)

        # Verify
        assert result is not None
        assert result.strategy == "medium_priority_automated_split"
        assert result.match_type == "regex"
        assert result.matched["handle"]["brand"] == "Declaration Grooming"
        assert result.matched["knot"]["brand"] == "Declaration Grooming"

    def test_match_with_no_split_returns_none(self, strategy, mock_legacy_matcher):
        """Test that no split returns None."""
        # Setup
        mock_legacy_matcher._match_medium_priority_automated_split.return_value = None

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
            original="Wolf Whiskers + Mixed Badger/Boar",
            matched={
                "brand": None,
                "model": None,
                "handle": {"brand": "Wolf Whiskers", "model": None},
                "knot": {"brand": "Wolf Whiskers", "model": "Mixed Badger/Boar", "fiber": "mixed"},
            },
            match_type="regex",
            pattern="smart_analysis",
            strategy="medium_priority_automated_split",
        )
        mock_legacy_matcher._match_medium_priority_automated_split.return_value = mock_result

        test_input = "Wolf Whiskers + Mixed Badger/Boar"

        # Execute
        result = strategy.match(test_input)

        # Verify legacy behavior is preserved
        assert result is not None
        assert result.strategy == "medium_priority_automated_split"
        assert result.match_type == "regex"
        assert result.matched["brand"] is None  # Composite brush
        assert result.matched["model"] is None  # Composite brush
        assert result.matched["handle"]["brand"] == "Wolf Whiskers"
        assert result.matched["knot"]["brand"] == "Wolf Whiskers"

    def test_match_handles_exceptions_gracefully(self, strategy, mock_legacy_matcher):
        """Test that strategy handles exceptions gracefully."""
        # Setup
        mock_legacy_matcher._match_medium_priority_automated_split.side_effect = Exception(
            "Test error"
        )

        test_input = "Declaration Grooming - B15"

        # Execute and verify exception is raised (fail-fast behavior)
        with pytest.raises(Exception, match="Test error"):
            strategy.match(test_input)
