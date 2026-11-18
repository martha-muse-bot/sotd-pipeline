#!/usr/bin/env python3
"""Tests for base brush matching strategy classes."""

from abc import ABC
from typing import Optional

import pytest

from sotd.match.brush.strategies.base_brush_matching_strategy import (
    BaseBrushMatchingStrategy,
    BaseMultiResultBrushMatchingStrategy,
)
from sotd.match.types import MatchResult


class TestBaseBrushMatchingStrategy:
    """Test BaseBrushMatchingStrategy abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseBrushMatchingStrategy cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # Type ignore for test - we're testing that instantiation fails
            BaseBrushMatchingStrategy()  # type: ignore

    def test_has_required_abstract_method(self):
        """Test that BaseBrushMatchingStrategy has the required abstract method."""
        assert hasattr(BaseBrushMatchingStrategy, "match")
        # Check that the method is abstract by trying to instantiate the class
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # Type ignore for test - we're testing that instantiation fails
            BaseBrushMatchingStrategy()  # type: ignore

    def test_concrete_implementation_works(self):
        """Test that a concrete implementation of BaseBrushMatchingStrategy works."""

        class ConcreteStrategy(BaseBrushMatchingStrategy):
            def match(self, value: str, full_string: Optional[str] = None):
                return MatchResult(
                    original=value,
                    normalized=value.lower(),
                    matched={"brand": "Test"},
                    match_type="test",
                    pattern="test_pattern",
                    strategy="concrete_test",
                )

        strategy = ConcreteStrategy()
        result = strategy.match("test brush")

        assert result is not None
        assert result.original == "test brush"
        assert result.matched is not None
        assert result.matched["brand"] == "Test"
        assert result.strategy == "concrete_test"


class TestBaseMultiResultBrushMatchingStrategy:
    """Test BaseMultiResultBrushMatchingStrategy abstract base class."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseMultiResultBrushMatchingStrategy cannot be instantiated."""
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # Type ignore for test - we're testing that instantiation fails
            BaseMultiResultBrushMatchingStrategy()  # type: ignore

    def test_has_required_abstract_methods(self):
        """Test that BaseMultiResultBrushMatchingStrategy has the required abstract methods."""
        assert hasattr(BaseMultiResultBrushMatchingStrategy, "match")
        assert hasattr(BaseMultiResultBrushMatchingStrategy, "match_all")
        # Check that the methods are abstract by trying to instantiate the class
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            # Type ignore for test - we're testing that instantiation fails
            BaseMultiResultBrushMatchingStrategy()  # type: ignore

    def test_concrete_implementation_works(self):
        """Test that a concrete implementation of BaseMultiResultBrushMatchingStrategy works."""

        class ConcreteMultiStrategy(BaseMultiResultBrushMatchingStrategy):
            def match(self, value: str, full_string: Optional[str] = None):
                # Return the first result for backward compatibility
                results = self.match_all(value)
                return results[0] if results else None

            def match_all(self, value: str):
                # Return multiple results for testing
                return [
                    MatchResult(
                        original=value,
                        normalized=value.lower(),
                        matched={"brand": "Test1"},
                        match_type="test1",
                        pattern="test_pattern1",
                        strategy="concrete_multi_test",
                    ),
                    MatchResult(
                        original=value,
                        normalized=value.lower(),
                        matched={"brand": "Test2"},
                        match_type="test2",
                        pattern="test_pattern2",
                        strategy="concrete_multi_test",
                    ),
                ]

        strategy = ConcreteMultiStrategy()

        # Test match_all method
        results = strategy.match_all("test brush")
        assert len(results) == 2
        assert results[0].matched is not None
        assert results[0].matched["brand"] == "Test1"
        assert results[1].matched is not None
        assert results[1].matched["brand"] == "Test2"

        # Test match method (backward compatibility)
        single_result = strategy.match("test brush")
        assert single_result is not None
        assert single_result.matched is not None
        assert single_result.matched["brand"] == "Test1"  # Should return first result

    def test_concrete_implementation_with_no_results(self):
        """Test concrete implementation when no results are found."""

        class ConcreteMultiStrategy(BaseMultiResultBrushMatchingStrategy):
            def match(self, value: str, full_string: Optional[str] = None):
                results = self.match_all(value)
                return results[0] if results else None

            def match_all(self, value: str):
                return []  # No results

        strategy = ConcreteMultiStrategy()

        # Test match_all method with no results
        results = strategy.match_all("no match")
        assert results == []

        # Test match method with no results
        single_result = strategy.match("no match")
        assert single_result is None


class TestBaseClassInheritance:
    """Test inheritance relationships between base classes."""

    def test_base_classes_are_abc(self):
        """Test that both base classes inherit from ABC."""
        assert issubclass(BaseBrushMatchingStrategy, ABC)
        assert issubclass(BaseMultiResultBrushMatchingStrategy, ABC)

    def test_multi_result_is_separate_from_single_result(self):
        """Test that multi-result strategy is not a subclass of single-result strategy."""
        # This ensures they are separate hierarchies
        assert not issubclass(BaseMultiResultBrushMatchingStrategy, BaseBrushMatchingStrategy)
        assert not issubclass(BaseBrushMatchingStrategy, BaseMultiResultBrushMatchingStrategy)
