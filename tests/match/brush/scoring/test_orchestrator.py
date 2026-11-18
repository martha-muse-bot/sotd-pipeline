#!/usr/bin/env python3
"""Tests for StrategyOrchestrator."""

from unittest.mock import Mock

import pytest

from sotd.match.brush.scoring.orchestrator import StrategyOrchestrator
from sotd.match.brush.strategies.base_brush_matching_strategy import (
    BaseBrushMatchingStrategy,
    BaseMultiResultBrushMatchingStrategy,
)
from sotd.match.types import MatchResult


class TestStrategyOrchestrator:
    """Test StrategyOrchestrator functionality."""

    @pytest.fixture
    def mock_single_result_strategy(self):
        """Mock single result strategy for testing."""
        strategy = Mock(spec=BaseBrushMatchingStrategy)
        strategy.match.return_value = MatchResult(
            original="test brush",
            normalized="test brush",
            matched={"brand": "TestBrand", "model": "TestModel"},
            match_type="test",
            pattern="test_pattern",
            strategy="mock_single_strategy",
        )
        return strategy

    @pytest.fixture
    def mock_multi_result_strategy(self):
        """Mock multi result strategy for testing."""
        strategy = Mock(spec=BaseMultiResultBrushMatchingStrategy)
        strategy.match_all.return_value = [
            MatchResult(
                original="test brush",
                normalized="test brush",
                matched={"handle_text": "handle1", "knot_text": "knot1"},
                match_type="split_brush",
                pattern="split_pattern_1",
                strategy="mock_multi_strategy",
            ),
            MatchResult(
                original="test brush",
                normalized="test brush",
                matched={"handle_text": "handle2", "knot_text": "knot2"},
                match_type="split_brush",
                pattern="split_pattern_2",
                strategy="mock_multi_strategy",
            ),
        ]
        return strategy

    @pytest.fixture
    def mock_strategy_with_cached_results(self):
        """Mock strategy that accepts cached results."""
        strategy = Mock(spec=BaseBrushMatchingStrategy)
        strategy.match.return_value = MatchResult(
            original="test brush",
            normalized="test brush",
            matched={"brand": "CachedBrand", "model": "CachedModel"},
            match_type="cached",
            pattern="cached_pattern",
            strategy="mock_cached_strategy",
        )
        return strategy

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization."""
        strategies = [Mock(), Mock()]
        orchestrator = StrategyOrchestrator(strategies)
        assert orchestrator.strategies == strategies
        assert orchestrator.get_strategy_count() == 2

    def test_run_all_strategies_single_result(self, mock_single_result_strategy):
        """Test running single result strategies."""
        orchestrator = StrategyOrchestrator([mock_single_result_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 1
        result = results[0]
        assert result.matched is not None
        assert result.matched["brand"] == "TestBrand"
        assert result.matched["model"] == "TestModel"
        assert result.strategy == "mock_single_strategy"

        # Verify the strategy was called correctly
        mock_single_result_strategy.match.assert_called_once_with("test brush")

    def test_run_all_strategies_multi_result(self, mock_multi_result_strategy):
        """Test running multi result strategies."""
        orchestrator = StrategyOrchestrator([mock_multi_result_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 2

        # First result
        result1 = results[0]
        assert result1.matched is not None
        assert result1.matched["handle_text"] == "handle1"
        assert result1.matched["knot_text"] == "knot1"
        assert result1.strategy == "mock_multi_strategy"

        # Second result
        result2 = results[1]
        assert result2.matched is not None
        assert result2.matched["handle_text"] == "handle2"
        assert result2.matched["knot_text"] == "knot2"
        assert result2.strategy == "mock_multi_strategy"

        # Verify the strategy was called correctly
        mock_multi_result_strategy.match_all.assert_called_once_with("test brush")
        # Should not call match() for multi-result strategies
        mock_multi_result_strategy.match.assert_not_called()

    def test_run_all_strategies_mixed_strategies(
        self, mock_single_result_strategy, mock_multi_result_strategy
    ):
        """Test running mixed single and multi result strategies."""
        orchestrator = StrategyOrchestrator(
            [mock_single_result_strategy, mock_multi_result_strategy]
        )
        results = orchestrator.run_all_strategies("test brush")

        # Should have 1 result from single strategy + 2 results from multi strategy = 3 total
        assert len(results) == 3

        # Verify both strategies were called
        mock_single_result_strategy.match.assert_called_once_with("test brush")
        mock_multi_result_strategy.match_all.assert_called_once_with("test brush")

    def test_run_all_strategies_with_cached_results(self, mock_strategy_with_cached_results):
        """Test running strategies with cached results."""
        orchestrator = StrategyOrchestrator([mock_strategy_with_cached_results])
        cached_results = {"some": "cached data"}
        results = orchestrator.run_all_strategies("test brush", cached_results)

        assert len(results) == 1
        result = results[0]
        assert result.matched is not None
        assert result.matched["brand"] == "CachedBrand"
        assert result.matched["model"] == "CachedModel"

        # Verify the strategy was called with cached results
        mock_strategy_with_cached_results.match.assert_called_once_with(
            "test brush", cached_results
        )

    def test_run_all_strategies_no_results(self):
        """Test running strategies that return no results."""
        mock_strategy = Mock(spec=BaseBrushMatchingStrategy)
        mock_strategy.match.return_value = None

        orchestrator = StrategyOrchestrator([mock_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 0
        mock_strategy.match.assert_called_once_with("test brush")

    def test_run_all_strategies_multi_result_no_results(self):
        """Test running multi result strategies that return no results."""
        mock_strategy = Mock(spec=BaseMultiResultBrushMatchingStrategy)
        mock_strategy.match_all.return_value = []

        orchestrator = StrategyOrchestrator([mock_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 0
        mock_strategy.match_all.assert_called_once_with("test brush")

    def test_run_all_strategies_dict_result_conversion(self):
        """Test conversion of dict results to MatchResult objects."""
        mock_strategy = Mock(spec=BaseBrushMatchingStrategy)
        mock_strategy.match.return_value = {
            "matched": {"brand": "DictBrand", "model": "DictModel"},
            "match_type": "dict_test",
            "pattern": "dict_pattern",
        }

        orchestrator = StrategyOrchestrator([mock_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 1
        result = results[0]
        assert isinstance(result, MatchResult)
        assert result.matched is not None
        assert result.matched["brand"] == "DictBrand"
        assert result.matched["model"] == "DictModel"
        assert result.match_type == "dict_test"
        assert result.pattern == "dict_pattern"
        assert result.strategy == "BaseBrushMatchingStrategy"  # Mock spec class name

    def test_run_all_strategies_invalid_result_skipped(self):
        """Test that invalid results are skipped."""
        mock_strategy = Mock(spec=BaseBrushMatchingStrategy)
        mock_strategy.match.return_value = "invalid_result"  # Not MatchResult or dict

        orchestrator = StrategyOrchestrator([mock_strategy])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 0
        mock_strategy.match.assert_called_once_with("test brush")

    def test_get_strategy_count(self):
        """Test getting strategy count."""
        strategies = [Mock(), Mock(), Mock()]
        orchestrator = StrategyOrchestrator(strategies)
        assert orchestrator.get_strategy_count() == 3

    def test_get_strategy_names(self):
        """Test getting strategy names."""

        class TestStrategy1:
            pass

        class TestStrategy2:
            pass

        strategy1 = TestStrategy1()
        strategy2 = TestStrategy2()
        orchestrator = StrategyOrchestrator([strategy1, strategy2])

        names = orchestrator.get_strategy_names()
        assert len(names) == 2
        assert "TestStrategy1" in names
        assert "TestStrategy2" in names

    def test_strategy_without_cached_results_parameter(self):
        """Test strategy that doesn't accept cached_results parameter."""

        # Create a custom strategy class that only accepts 'value' parameter
        class NoCachedStrategy(BaseBrushMatchingStrategy):
            def match(self, value: str, full_string=None):
                return MatchResult(
                    original=value,
                    normalized=value,
                    matched={"brand": "NoCachedBrand"},
                    match_type="no_cached",
                    pattern="no_cached_pattern",
                    strategy="no_cached_strategy",
                )

        strategy = NoCachedStrategy()
        orchestrator = StrategyOrchestrator([strategy])
        cached_results = {"some": "cached data"}
        results = orchestrator.run_all_strategies("test brush", cached_results)

        assert len(results) == 1
        result = results[0]
        assert result.matched is not None
        assert result.matched["brand"] == "NoCachedBrand"
        assert result.strategy == "no_cached_strategy"

    def test_empty_strategies_list(self):
        """Test orchestrator with empty strategies list."""
        orchestrator = StrategyOrchestrator([])
        results = orchestrator.run_all_strategies("test brush")

        assert len(results) == 0
        assert orchestrator.get_strategy_count() == 0
        assert orchestrator.get_strategy_names() == []
