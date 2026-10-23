#!/usr/bin/env python3
"""Performance tests for Handle/Knot Dependency Implementation.

This test file measures the performance impact of handle/knot dependencies
within automated split strategies.
"""

import time
import pytest

from sotd.match.brush_matcher import BrushMatcher
from sotd.match.brush.scoring.dependencies.strategy_dependency_manager import (
    StrategyDependency,
    DependencyType,
)

# Wall-clock threshold asserts are load-sensitive; excluded in CI via `-m "not perf"`.
pytestmark = pytest.mark.perf


class TestHandleKnotDependencyPerformance:
    """Test performance impact of handle/knot dependencies."""

    @pytest.fixture
    def scoring_matcher_with_dependencies(
        self,
        test_correct_matches_path,
        test_brushes_path,
        test_handles_path,
        test_knots_path,
        test_brush_scoring_config_path,
    ):
        """Create scoring matcher with dependencies configured."""
        return BrushMatcher(
            correct_matches_path=test_correct_matches_path,
            brushes_path=test_brushes_path,
            handles_path=test_handles_path,
            knots_path=test_knots_path,
            brush_scoring_config_path=test_brush_scoring_config_path,
        )

    @pytest.fixture
    def scoring_matcher_without_dependencies(
        self,
        test_correct_matches_path,
        test_brushes_path,
        test_handles_path,
        test_knots_path,
        test_brush_scoring_config_path,
    ):
        """Create scoring matcher with dependencies disabled."""
        matcher = BrushMatcher(
            correct_matches_path=test_correct_matches_path,
            brushes_path=test_brushes_path,
            handles_path=test_handles_path,
            knots_path=test_knots_path,
            brush_scoring_config_path=test_brush_scoring_config_path,
        )
        # Clear all dependencies to simulate no-dependency scenario
        matcher.strategy_dependency_manager.dependencies.clear()
        matcher.strategy_dependency_manager.dependency_graph.clear()
        matcher.strategy_dependency_manager.topological_graph.clear()
        return matcher

    def test_dependency_performance_impact(
        self, scoring_matcher_with_dependencies, scoring_matcher_without_dependencies
    ):
        """Test performance impact of dependency configuration."""
        # Test cases that should trigger automated splitting
        test_cases = [
            "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar",
            "Declaration Grooming - B15",
            "Wolf Whiskers + Mixed Badger/Boar",
            "Declaration Grooming B2 w/ Declaration Grooming B2",
            "Custom Handle w/ Synthetic Knot",
        ]

        # Measure performance with dependencies
        start_time = time.time()
        for test_case in test_cases:
            _ = scoring_matcher_with_dependencies.match(test_case)
        dependency_time = time.time() - start_time

        # Measure performance without dependencies
        start_time = time.time()
        for test_case in test_cases:
            _ = scoring_matcher_without_dependencies.match(test_case)
        no_dependency_time = time.time() - start_time

        # Calculate performance difference
        time_difference = dependency_time - no_dependency_time
        percentage_change = (time_difference / no_dependency_time) * 100

        # Log performance metrics
        print("\nPerformance Test Results:")
        print(f"With Dependencies: {dependency_time:.4f}s")
        print(f"Without Dependencies: {no_dependency_time:.4f}s")
        print(f"Time Difference: {time_difference:.4f}s")
        print(f"Percentage Change: {percentage_change:.2f}%")

        # Assert that performance impact is reasonable (less than 300% overhead)
        # Note: Performance tests can be flaky due to system load, so we use a more generous threshold
        assert percentage_change < 300, f"Performance overhead too high: {percentage_change:.2f}%"

    def test_dependency_configuration_overhead(self, scoring_matcher_with_dependencies):
        """Test overhead of dependency configuration itself."""
        # Measure time to check dependencies
        test_case = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Get strategy results
        strategy_results = (
            scoring_matcher_with_dependencies.strategy_orchestrator.run_all_strategies(test_case)
        )

        # Measure dependency checking overhead
        start_time = time.time()
        for _ in range(100):  # Run 100 times to get measurable difference
            _ = scoring_matcher_with_dependencies._apply_dependency_constraints(strategy_results)
        dependency_check_time = time.time() - start_time

        # Measure without dependency checking (just pass through)
        start_time = time.time()
        for _ in range(100):
            _ = strategy_results  # No dependency checking
        no_check_time = time.time() - start_time

        overhead_per_check = (dependency_check_time - no_check_time) / 100

        print("\nDependency Check Overhead:")
        print(f"With Dependency Checking: {dependency_check_time:.4f}s (100 checks)")
        print(f"Without Dependency Checking: {no_check_time:.4f}s (100 checks)")
        print(f"Overhead per check: {overhead_per_check:.6f}s")

        # Assert that overhead is minimal (less than 1ms per check)
        assert (
            overhead_per_check < 0.001
        ), f"Dependency check overhead too high: {overhead_per_check:.6f}s"

    def test_dependency_execution_order_optimization(self, scoring_matcher_with_dependencies):
        """Test that dependency execution order optimization works."""
        # Test with a case that should trigger dependencies
        test_case = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        # Get strategy results
        strategy_results = (
            scoring_matcher_with_dependencies.strategy_orchestrator.run_all_strategies(test_case)
        )

        # Get strategy names
        strategy_names = [result.strategy for result in strategy_results if result.strategy]

        # Get optimized execution order
        optimized_order = (
            scoring_matcher_with_dependencies.strategy_dependency_manager.get_execution_order(
                strategy_names
            )
        )

        # Verify that BrushSplitter comes before HandleMatcher and KnotMatcher
        if "BrushSplitter" in optimized_order and "HandleMatcher" in optimized_order:
            brush_splitter_index = optimized_order.index("BrushSplitter")
            handle_matcher_index = optimized_order.index("HandleMatcher")
            assert (
                brush_splitter_index < handle_matcher_index
            ), "BrushSplitter should come before HandleMatcher"

        if "BrushSplitter" in optimized_order and "KnotMatcher" in optimized_order:
            brush_splitter_index = optimized_order.index("BrushSplitter")
            knot_matcher_index = optimized_order.index("KnotMatcher")
            assert (
                brush_splitter_index < knot_matcher_index
            ), "BrushSplitter should come before KnotMatcher"

        print("\nExecution Order Optimization:")
        print(f"Original order: {strategy_names}")
        print(f"Optimized order: {optimized_order}")

    def test_dependency_memory_usage(self, scoring_matcher_with_dependencies):
        """Test memory usage impact of dependency configuration."""
        import sys

        # Measure memory usage before dependency operations
        test_case = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"
        strategy_results = (
            scoring_matcher_with_dependencies.strategy_orchestrator.run_all_strategies(test_case)
        )

        # Get memory usage before dependency operations
        memory_before = sys.getsizeof(strategy_results)

        # Apply dependency constraints
        executable_results = scoring_matcher_with_dependencies._apply_dependency_constraints(
            strategy_results
        )

        # Get memory usage after dependency operations
        memory_after = sys.getsizeof(executable_results)

        # Calculate memory overhead
        memory_overhead = memory_after - memory_before

        print("\nMemory Usage Impact:")
        print(f"Before dependency operations: {memory_before} bytes")
        print(f"After dependency operations: {memory_after} bytes")
        print(f"Memory overhead: {memory_overhead} bytes")

        # Assert that memory overhead is reasonable (less than 1KB)
        assert memory_overhead < 1024, f"Memory overhead too high: {memory_overhead} bytes"

    def test_dependency_configuration_scalability(self, scoring_matcher_with_dependencies):
        """Test scalability of dependency configuration with multiple dependencies."""
        # Add more dependencies to test scalability
        dependency_manager = scoring_matcher_with_dependencies.strategy_dependency_manager

        # Add additional dependencies
        additional_dependencies = [
            StrategyDependency("StrategyA", "BrushSplitter", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("StrategyB", "HandleMatcher", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("StrategyC", "KnotMatcher", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("StrategyD", "StrategyA", DependencyType.REQUIRES_ANY),
            StrategyDependency("StrategyE", "StrategyB", DependencyType.REQUIRES_ALL),
        ]

        for dependency in additional_dependencies:
            dependency_manager.add_dependency(dependency)

        # Test performance with more dependencies
        test_case = "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar"

        start_time = time.time()
        for _ in range(10):  # Run 10 times
            strategy_results = (
                scoring_matcher_with_dependencies.strategy_orchestrator.run_all_strategies(
                    test_case
                )
            )
            executable_results = scoring_matcher_with_dependencies._apply_dependency_constraints(
                strategy_results
            )
        scalability_time = time.time() - start_time

        print(f"\nScalability Test (with {len(dependency_manager.dependencies)} dependencies):")
        print(f"Time for 10 operations: {scalability_time:.4f}s")
        print(f"Average time per operation: {scalability_time / 10:.4f}s")

        # Assert that performance is still reasonable (less than 1s for 10 operations)
        assert scalability_time < 1.0, f"Scalability performance too slow: {scalability_time:.4f}s"
