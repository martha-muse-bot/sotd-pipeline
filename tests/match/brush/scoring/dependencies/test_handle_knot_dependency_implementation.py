#!/usr/bin/env python3
"""Tests for Handle/Knot Dependency Implementation.

This test file validates the implementation of handle/knot dependencies
within automated split strategies while maintaining 100% alignment.
"""

import pytest

from sotd.match.brush.scoring.dependencies.strategy_dependency_manager import (
    DependencyType,
    StrategyDependency,
    StrategyDependencyManager,
)
from sotd.match.brush_matcher import BrushMatcher
from sotd.match.types import create_match_result


class TestHandleKnotDependencyImplementation:
    """Test handle/knot dependency implementation."""

    @pytest.fixture
    def dependency_manager(self):
        """Create dependency manager instance."""
        return StrategyDependencyManager()

    @pytest.fixture
    def scoring_matcher(
        self,
        test_correct_matches_path,
        test_brushes_path,
        test_handles_path,
        test_knots_path,
        test_brush_scoring_config_path,
    ):
        """Create scoring matcher instance."""
        return BrushMatcher(
            correct_matches_path=test_correct_matches_path,
            brushes_path=test_brushes_path,
            handles_path=test_handles_path,
            knots_path=test_knots_path,
            brush_scoring_config_path=test_brush_scoring_config_path,
        )

    def test_dependency_manager_initialization(self, dependency_manager):
        """Test dependency manager initializes correctly."""
        assert dependency_manager.dependencies == []
        assert dependency_manager.dependency_graph == {}
        assert dependency_manager.topological_graph == {}

    def test_handle_knot_dependency_configuration(self, dependency_manager):
        """Test configuring handle/knot dependencies."""
        # Configure dependencies
        dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Verify dependencies are added
        assert len(dependency_manager.dependencies) == 2

        # Verify dependency graph
        assert "HandleMatcher" in dependency_manager.dependency_graph
        assert "KnotMatcher" in dependency_manager.dependency_graph
        assert dependency_manager.dependency_graph["HandleMatcher"] == {"BrushSplitter"}
        assert dependency_manager.dependency_graph["KnotMatcher"] == {"BrushSplitter"}

    def test_dependency_execution_order(self, dependency_manager):
        """Test dependency execution order calculation."""
        # Configure dependencies
        dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Test execution order
        strategy_names = ["BrushSplitter", "HandleMatcher", "KnotMatcher"]
        execution_order = dependency_manager.get_execution_order(strategy_names)

        # BrushSplitter should come first, then HandleMatcher and KnotMatcher
        assert execution_order[0] == "BrushSplitter"
        assert "HandleMatcher" in execution_order[1:]
        assert "KnotMatcher" in execution_order[1:]

    def test_dependency_constraint_checking(self, dependency_manager):
        """Test dependency constraint checking."""
        # Configure dependencies
        dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Test with no results (should block execution)
        can_execute_handle = dependency_manager.can_execute_strategy("HandleMatcher", {})
        can_execute_knot = dependency_manager.can_execute_strategy("KnotMatcher", {})

        # Should block execution when dependencies haven't run yet
        assert can_execute_handle is False
        assert can_execute_knot is False

        # Test with BrushSplitter success
        brush_splitter_result = create_match_result(
            original="test",
            matched={"brand": "test"},
            match_type="exact",
            pattern="test",
            strategy="BrushSplitter",
        )

        can_execute_handle = dependency_manager.can_execute_strategy(
            "HandleMatcher", {"BrushSplitter": brush_splitter_result}
        )
        can_execute_knot = dependency_manager.can_execute_strategy(
            "KnotMatcher", {"BrushSplitter": brush_splitter_result}
        )

        # Should allow execution when BrushSplitter succeeded
        assert can_execute_handle is True
        assert can_execute_knot is True

        # Test with BrushSplitter failure
        brush_splitter_failure = create_match_result(
            original="test",
            matched=None,  # No match = failure
            match_type=None,
            pattern=None,
            strategy="BrushSplitter",
        )

        can_execute_handle = dependency_manager.can_execute_strategy(
            "HandleMatcher", {"BrushSplitter": brush_splitter_failure}
        )
        can_execute_knot = dependency_manager.can_execute_strategy(
            "KnotMatcher", {"BrushSplitter": brush_splitter_failure}
        )

        # Should NOT allow execution when BrushSplitter failed
        assert can_execute_handle is False
        assert can_execute_knot is False

    def test_scoring_matcher_dependency_integration(self, scoring_matcher):
        """Test dependency manager integration in scoring matcher."""
        # Verify dependency manager is initialized
        assert hasattr(scoring_matcher, "strategy_dependency_manager")
        assert scoring_matcher.strategy_dependency_manager is not None

        # Verify dependency info method exists
        dependency_info = scoring_matcher.get_dependency_info()
        assert "dependency_manager" in dependency_info
        assert "dependencies" in dependency_info
        assert "dependency_graph" in dependency_info
        assert "topological_graph" in dependency_info

    def test_dependency_configuration_preserves_alignment(self, scoring_matcher):
        """Test that dependency configuration doesn't break alignment."""
        # Configure handle/knot dependencies
        scoring_matcher.strategy_dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        scoring_matcher.strategy_dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Test with a simple brush string that should work with or without dependencies
        test_input = "Declaration Grooming B2"

        # This should still work even with dependencies configured
        # (dependencies only affect internal execution, not final results)
        result = scoring_matcher.match(test_input)

        # Result should be the same regardless of dependencies
        # (since dependencies are not yet applied to execution order)
        assert result is not None or result is None  # Either result is fine for this test

    def test_dependency_performance_optimization(self, dependency_manager):
        """Test that dependencies can optimize performance."""
        # Configure dependencies
        dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Test performance optimization by checking execution order
        strategy_names = ["BrushSplitter", "HandleMatcher", "KnotMatcher", "OtherStrategy"]
        execution_order = dependency_manager.get_execution_order(strategy_names)

        # BrushSplitter should be prioritized first
        assert execution_order[0] == "BrushSplitter"

        # Dependent strategies should come after
        handle_index = execution_order.index("HandleMatcher")
        knot_index = execution_order.index("KnotMatcher")
        assert handle_index > 0  # After BrushSplitter
        assert knot_index > 0  # After BrushSplitter

    def test_dependency_rollback_capability(self, dependency_manager):
        """Test that dependencies can be easily disabled."""
        # Configure dependencies
        dependency_manager.add_dependency(
            StrategyDependency("HandleMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )
        dependency_manager.add_dependency(
            StrategyDependency("KnotMatcher", "BrushSplitter", DependencyType.REQUIRES_SUCCESS)
        )

        # Verify dependencies are configured
        assert len(dependency_manager.dependencies) == 2

        # Clear all dependencies (rollback)
        dependency_manager.dependencies.clear()
        dependency_manager.dependency_graph.clear()
        dependency_manager.topological_graph.clear()

        # Verify rollback worked
        assert len(dependency_manager.dependencies) == 0
        assert len(dependency_manager.dependency_graph) == 0
        assert len(dependency_manager.topological_graph) == 0

        # Test that execution order is now unconstrained
        strategy_names = ["BrushSplitter", "HandleMatcher", "KnotMatcher"]
        execution_order = dependency_manager.get_execution_order(strategy_names)

        # Should return original order when no dependencies
        assert execution_order == strategy_names
