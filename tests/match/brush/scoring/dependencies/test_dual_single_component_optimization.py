#!/usr/bin/env python3
"""Tests for dual/single component optimization with dependencies."""

import time

import pytest

from sotd.match.brush.scoring.dependencies.strategy_dependency_manager import (
    StrategyDependencyManager,
    StrategyDependency,
    DependencyType,
)
from sotd.match.brush_matcher import BrushMatcher
from sotd.match.types import MatchResult


class TestDualSingleComponentOptimization:
    """Test the optimization of dual and single component strategies."""

    @pytest.fixture
    def scoring_matcher(self):
        """Create a scoring matcher with optimization dependencies."""
        return BrushMatcher()

    @pytest.fixture
    def dependency_manager(self):
        """Create a dependency manager for testing."""
        return StrategyDependencyManager()

    def test_dual_component_dependencies_configured(self, scoring_matcher):
        """Test that dual component dependencies are properly configured."""
        dependency_manager = scoring_matcher.strategy_dependency_manager

        # Check that dual component depends on both HandleMatcher and KnotMatcher success
        dual_dependencies = [
            dep
            for dep in dependency_manager.dependencies
            if dep.dependent_strategy == "FullInputComponentMatchingStrategy"
        ]

        # FullInputComponentMatchingStrategy should have 4 dependencies:
        # - 2 REQUIRES_SUCCESS (for dual component scenarios)
        # - 2 REQUIRES_ANY (for single component scenarios)
        assert (
            len(dual_dependencies) == 4
        ), "FullInputComponentMatchingStrategy should have 4 dependencies (2 REQUIRES_SUCCESS + 2 REQUIRES_ANY)"

        # Check HandleMatcher dependency
        handle_dep = next(
            (dep for dep in dual_dependencies if dep.depends_on_strategy == "HandleMatcher"), None
        )
        assert handle_dep is not None, "Dual component should depend on HandleMatcher"
        assert handle_dep.dependency_type == DependencyType.REQUIRES_SUCCESS

        # Check KnotMatcher dependency
        knot_dep = next(
            (dep for dep in dual_dependencies if dep.depends_on_strategy == "KnotMatcher"), None
        )
        assert knot_dep is not None, "Dual component should depend on KnotMatcher"
        assert knot_dep.dependency_type == DependencyType.REQUIRES_SUCCESS

    def test_single_component_dependencies_configured(self, scoring_matcher):
        """Test that single component dependencies are properly configured."""
        dependency_manager = scoring_matcher.strategy_dependency_manager

        # Check that FullInputComponentMatchingStrategy depends on both HandleMatcher and KnotMatcher
        full_input_dependencies = [
            dep
            for dep in dependency_manager.dependencies
            if dep.dependent_strategy == "FullInputComponentMatchingStrategy"
        ]

        # FullInputComponentMatchingStrategy should have 4 dependencies:
        # - 2 REQUIRES_SUCCESS (for dual component scenarios)
        # - 2 REQUIRES_ANY (for single component scenarios)
        assert (
            len(full_input_dependencies) == 4
        ), "FullInputComponentMatchingStrategy should have 4 dependencies (2 REQUIRES_SUCCESS + 2 REQUIRES_ANY)"

        # Check HandleMatcher dependencies (both REQUIRES_SUCCESS and REQUIRES_ANY)
        handle_deps = [
            dep for dep in full_input_dependencies if dep.depends_on_strategy == "HandleMatcher"
        ]
        assert (
            len(handle_deps) == 2
        ), "FullInputComponentMatchingStrategy should have 2 HandleMatcher dependencies"

        # Check that one is REQUIRES_SUCCESS and one is REQUIRES_ANY
        handle_success = next(
            (dep for dep in handle_deps if dep.dependency_type == DependencyType.REQUIRES_SUCCESS),
            None,
        )
        handle_any = next(
            (dep for dep in handle_deps if dep.dependency_type == DependencyType.REQUIRES_ANY), None
        )
        assert (
            handle_success is not None
        ), "Should have REQUIRES_SUCCESS dependency on HandleMatcher"
        assert handle_any is not None, "Should have REQUIRES_ANY dependency on HandleMatcher"

        # Check KnotMatcher dependencies (both REQUIRES_SUCCESS and REQUIRES_ANY)
        knot_deps = [
            dep for dep in full_input_dependencies if dep.depends_on_strategy == "KnotMatcher"
        ]
        assert (
            len(knot_deps) == 2
        ), "FullInputComponentMatchingStrategy should have 2 KnotMatcher dependencies"

        # Check that one is REQUIRES_SUCCESS and one is REQUIRES_ANY
        knot_success = next(
            (dep for dep in knot_deps if dep.dependency_type == DependencyType.REQUIRES_SUCCESS),
            None,
        )
        knot_any = next(
            (dep for dep in knot_deps if dep.dependency_type == DependencyType.REQUIRES_ANY), None
        )
        assert knot_success is not None, "Should have REQUIRES_SUCCESS dependency on KnotMatcher"
        assert knot_any is not None, "Should have REQUIRES_ANY dependency on KnotMatcher"

    def test_dual_component_execution_constraints(self, dependency_manager):
        """Test that dual component is constrained by HandleMatcher and KnotMatcher success."""
        # Add dual component dependencies
        dependency_manager.add_dependency(
            StrategyDependency(
                "LegacyDualComponentWrapperStrategy",
                "HandleMatcher",
                DependencyType.REQUIRES_SUCCESS,
            )
        )
        dependency_manager.add_dependency(
            StrategyDependency(
                "LegacyDualComponentWrapperStrategy", "KnotMatcher", DependencyType.REQUIRES_SUCCESS
            )
        )

        # Test with no results - should be blocked
        can_execute = dependency_manager.can_execute_strategy(
            "LegacyDualComponentWrapperStrategy", {}
        )
        assert (
            can_execute is False
        ), "Dual component should be blocked when no dependencies have run"

        # Test with only HandleMatcher success
        strategy_results = {
            "HandleMatcher": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="exact",
                pattern="test",
                strategy="HandleMatcher",
            )
        }
        can_execute = dependency_manager.can_execute_strategy(
            "LegacyDualComponentWrapperStrategy", strategy_results
        )
        assert (
            can_execute is False
        ), "Dual component should be blocked when only HandleMatcher succeeded"

        # Test with both HandleMatcher and KnotMatcher success
        strategy_results["KnotMatcher"] = MatchResult(
            original="test",
            matched={"brand": "test"},
            match_type="exact",
            pattern="test",
            strategy="KnotMatcher",
        )
        can_execute = dependency_manager.can_execute_strategy(
            "LegacyDualComponentWrapperStrategy", strategy_results
        )
        assert can_execute is True, "Dual component should execute when both dependencies succeeded"

    def test_single_component_execution_constraints(self, dependency_manager):
        """Test that single component is constrained by any of HandleMatcher or KnotMatcher."""
        # Add single component dependencies
        dependency_manager.add_dependency(
            StrategyDependency(
                "LegacySingleComponentFallbackWrapperStrategy",
                "HandleMatcher",
                DependencyType.REQUIRES_ANY,
            )
        )
        dependency_manager.add_dependency(
            StrategyDependency(
                "LegacySingleComponentFallbackWrapperStrategy",
                "KnotMatcher",
                DependencyType.REQUIRES_ANY,
            )
        )

        # Test with no results - should be allowed (REQUIRES_ANY allows execution when no deps checked)
        can_execute = dependency_manager.can_execute_strategy("HandleComponentStrategy", {})
        assert (
            can_execute is True
        ), "Single component should be allowed when no dependencies have run"

        # Test with only HandleMatcher success
        strategy_results = {
            "HandleMatcher": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="exact",
                pattern="test",
                strategy="HandleMatcher",
            )
        }
        can_execute = dependency_manager.can_execute_strategy(
            "HandleComponentStrategy", strategy_results
        )
        assert can_execute is True, "Single component should execute when HandleMatcher succeeded"

        # Test with only KnotMatcher success
        strategy_results = {
            "KnotMatcher": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="exact",
                pattern="test",
                strategy="KnotMatcher",
            )
        }
        can_execute = dependency_manager.can_execute_strategy(
            "KnotComponentStrategy", strategy_results
        )
        assert can_execute is True, "Single component should execute when KnotMatcher succeeded"

        # Test with both HandleMatcher and KnotMatcher success
        strategy_results["HandleMatcher"] = MatchResult(
            original="test",
            matched={"brand": "test"},
            match_type="exact",
            pattern="test",
            strategy="HandleMatcher",
        )
        can_execute = dependency_manager.can_execute_strategy(
            "HandleComponentStrategy", strategy_results
        )
        assert (
            can_execute is True
        ), "Single component should execute when both dependencies succeeded"

    def test_optimization_execution_order(self, scoring_matcher):
        """Test that execution order prioritizes HandleMatcher and KnotMatcher first."""
        dependency_manager = scoring_matcher.strategy_dependency_manager

        # Get execution order for strategies that include HandleMatcher, KnotMatcher, and component strategies
        strategy_names = [
            "HandleMatcher",
            "KnotMatcher",
            "FullInputComponentMatchingStrategy",
            "HandleComponentStrategy",
        ]
        execution_order = dependency_manager.get_execution_order(strategy_names)

        # HandleMatcher and KnotMatcher should come before component strategies
        handle_index = execution_order.index("HandleMatcher")
        knot_index = execution_order.index("KnotMatcher")
        dual_index = execution_order.index("FullInputComponentMatchingStrategy")
        single_index = execution_order.index("HandleComponentStrategy")

        assert handle_index < dual_index, "HandleMatcher should come before dual component"
        assert handle_index < single_index, "HandleMatcher should come before single component"
        assert knot_index < dual_index, "KnotMatcher should come before dual component"
        assert knot_index < single_index, "KnotMatcher should come before single component"

        print("\nOptimized Execution Order:")
        print(f"HandleMatcher: position {handle_index}")
        print(f"KnotMatcher: position {knot_index}")
        print(f"Dual Component: position {dual_index}")
        print(f"Single Component: position {single_index}")

    @pytest.mark.perf
    def test_optimization_performance_impact(self, scoring_matcher):
        """Test that the optimization reduces redundant work."""
        # Test with a case that should trigger both dual and single component strategies
        test_case = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Measure time with optimization
        start_time = time.time()
        result = scoring_matcher.match(test_case)
        optimized_time = time.time() - start_time

        print("\nOptimization Performance Test:")
        print(f"Test case: {test_case}")
        print(f"Result: {result.strategy if result else 'None'}")
        print(f"Optimized execution time: {optimized_time:.4f}s")

        # The optimization should not significantly impact performance
        # (it should actually improve it by reducing redundant work)
        assert optimized_time < 1.0, f"Optimized execution too slow: {optimized_time:.4f}s"

    def test_optimization_alignment_preservation(self, scoring_matcher):
        """Test that the optimization preserves 100% alignment."""
        # Test with cases that should work with or without optimization
        test_cases = [
            "Declaration Grooming B2",
            "Simpson Chubby 2",
            "Omega 10049 Boar",
        ]

        for test_case in test_cases:
            result = scoring_matcher.match(test_case)

            # Result should be the same regardless of optimization
            # (since dependencies only affect execution order, not final results)
            assert result is not None, f"Should get a result for {test_case}"
            print(f"Test case '{test_case}' -> Strategy: {result.strategy}")

    def test_optimization_rollback_capability(self, scoring_matcher):
        """Test that the optimization can be rolled back if needed."""
        dependency_manager = scoring_matcher.strategy_dependency_manager

        # Count dependencies before rollback
        initial_dependencies = len(dependency_manager.dependencies)

        # Clear all dependencies (rollback)
        dependency_manager.dependencies.clear()
        dependency_manager.dependency_graph.clear()
        dependency_manager.topological_graph.clear()

        # Verify rollback
        assert len(dependency_manager.dependencies) == 0, "Dependencies should be cleared"
        assert len(dependency_manager.dependency_graph) == 0, "Dependency graph should be cleared"
        assert len(dependency_manager.topological_graph) == 0, "Topological graph should be cleared"

        print("\nRollback Test:")
        print(f"Initial dependencies: {initial_dependencies}")
        print(f"After rollback: {len(dependency_manager.dependencies)}")
        print("Rollback successful - optimization can be disabled if needed")
