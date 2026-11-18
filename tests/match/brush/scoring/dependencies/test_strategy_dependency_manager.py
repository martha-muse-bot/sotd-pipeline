"""
Unit tests for StrategyDependencyManager component.

Tests strategy dependency management functionality for the brush scoring system.
"""

from unittest.mock import Mock

import pytest

from sotd.match.brush.scoring.dependencies.strategy_dependency_manager import (
    DependencyType,
    StrategyDependency,
    StrategyDependencyManager,
)


class TestStrategyDependencyManager:
    """Test cases for StrategyDependencyManager."""

    def test_init_with_no_dependencies(self):
        """Test initialization with no dependencies."""
        manager = StrategyDependencyManager()
        assert manager.dependencies == []
        assert manager.dependency_graph == {}

    def test_add_dependency(self):
        """Test adding a dependency between strategies."""
        manager = StrategyDependencyManager()

        dependency = StrategyDependency(
            dependent_strategy="dual_component",
            depends_on_strategy="handle_component",
            dependency_type=DependencyType.REQUIRES_SUCCESS,
        )

        manager.add_dependency(dependency)

        assert len(manager.dependencies) == 1
        assert manager.dependencies[0] == dependency
        assert "dual_component" in manager.dependency_graph
        assert "handle_component" in manager.dependency_graph["dual_component"]

    def test_add_multiple_dependencies(self):
        """Test adding multiple dependencies."""
        manager = StrategyDependencyManager()

        deps = [
            StrategyDependency(
                "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
            ),
            StrategyDependency("dual_component", "knot_component", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency(
                "high_priority_split", "complete_brush", DependencyType.REQUIRES_FAILURE
            ),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        assert len(manager.dependencies) == 3
        assert len(manager.dependency_graph["dual_component"]) == 2
        assert "handle_component" in manager.dependency_graph["dual_component"]
        assert "knot_component" in manager.dependency_graph["dual_component"]

    def test_check_dependencies_requires_success(self):
        """Test dependency checking for REQUIRES_SUCCESS type."""
        manager = StrategyDependencyManager()

        dependency = StrategyDependency(
            "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
        )
        manager.add_dependency(dependency)

        # Mock strategy results
        handle_result = Mock()
        handle_result.matched = {"brand": "Test"}  # Success case

        strategy_results = {"handle_component": handle_result}

        # Should allow execution when dependency succeeds
        assert manager.can_execute_strategy("dual_component", strategy_results) is True

        # Should block execution when dependency fails
        handle_result.matched = None  # Failure case
        assert manager.can_execute_strategy("dual_component", strategy_results) is False

    def test_check_dependencies_requires_failure(self):
        """Test dependency checking for REQUIRES_FAILURE type."""
        manager = StrategyDependencyManager()

        dependency = StrategyDependency(
            "high_priority_split", "complete_brush", DependencyType.REQUIRES_FAILURE
        )
        manager.add_dependency(dependency)

        # Mock strategy results
        complete_brush_result = Mock()
        complete_brush_result.matched = None  # Failure case

        strategy_results = {"complete_brush": complete_brush_result}

        # Should allow execution when dependency fails
        assert manager.can_execute_strategy("high_priority_split", strategy_results) is True

        # Should block execution when dependency succeeds
        complete_brush_result.matched = {"brand": "Test"}  # Success case
        assert manager.can_execute_strategy("high_priority_split", strategy_results) is False

    def test_check_dependencies_requires_any(self):
        """Test dependency checking for REQUIRES_ANY type."""
        manager = StrategyDependencyManager()

        # Add multiple dependencies for REQUIRES_ANY
        deps = [
            StrategyDependency("fallback_strategy", "strategy_a", DependencyType.REQUIRES_ANY),
            StrategyDependency("fallback_strategy", "strategy_b", DependencyType.REQUIRES_ANY),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        # Mock strategy results
        strategy_a_result = Mock()
        strategy_b_result = Mock()

        # Should allow execution when any dependency succeeds
        strategy_a_result.matched = {"brand": "Test"}  # Success
        strategy_b_result.matched = None  # Failure
        strategy_results = {"strategy_a": strategy_a_result, "strategy_b": strategy_b_result}
        assert manager.can_execute_strategy("fallback_strategy", strategy_results) is True

        # Should also allow execution when the other dependency succeeds
        strategy_a_result.matched = None  # Failure
        strategy_b_result.matched = {"fiber": "badger"}  # Success
        assert manager.can_execute_strategy("fallback_strategy", strategy_results) is True

        # Should block execution when all dependencies fail
        strategy_a_result.matched = None  # Failure
        strategy_b_result.matched = None  # Failure
        assert manager.can_execute_strategy("fallback_strategy", strategy_results) is False

    def test_check_dependencies_requires_all(self):
        """Test dependency checking for REQUIRES_ALL type."""
        manager = StrategyDependencyManager()

        deps = [
            StrategyDependency("dual_component", "handle_component", DependencyType.REQUIRES_ALL),
            StrategyDependency("dual_component", "knot_component", DependencyType.REQUIRES_ALL),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        # Mock strategy results
        handle_result = Mock()
        knot_result = Mock()

        # Should allow execution when all dependencies succeed
        handle_result.matched = {"brand": "Test"}
        knot_result.matched = {"fiber": "badger"}
        strategy_results = {"handle_component": handle_result, "knot_component": knot_result}
        assert manager.can_execute_strategy("dual_component", strategy_results) is True

        # Should block execution when any dependency fails
        handle_result.matched = None  # Failure
        assert manager.can_execute_strategy("dual_component", strategy_results) is False

    def test_strategy_with_no_dependencies(self):
        """Test that strategies with no dependencies can always execute."""
        manager = StrategyDependencyManager()

        # Add dependency for one strategy
        dependency = StrategyDependency(
            "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
        )
        manager.add_dependency(dependency)

        # Strategy with no dependencies should always be able to execute
        strategy_results = {"handle_component": Mock()}
        assert manager.can_execute_strategy("complete_brush", strategy_results) is True

    def test_get_execution_order(self):
        """Test getting optimal execution order based on dependencies."""
        manager = StrategyDependencyManager()

        # Set up dependencies
        deps = [
            StrategyDependency(
                "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
            ),
            StrategyDependency("dual_component", "knot_component", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("fallback", "complete_brush", DependencyType.REQUIRES_FAILURE),
            StrategyDependency("fallback", "dual_component", DependencyType.REQUIRES_FAILURE),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        strategy_names = [
            "complete_brush",
            "handle_component",
            "knot_component",
            "dual_component",
            "fallback",
        ]

        execution_order = manager.get_execution_order(strategy_names)

        # handle_component and knot_component should come before dual_component
        assert execution_order.index("handle_component") < execution_order.index("dual_component")
        assert execution_order.index("knot_component") < execution_order.index("dual_component")

        # complete_brush and dual_component should come before fallback
        assert execution_order.index("complete_brush") < execution_order.index("fallback")
        assert execution_order.index("dual_component") < execution_order.index("fallback")

        # All strategies should be included
        assert len(execution_order) == len(strategy_names)
        assert set(execution_order) == set(strategy_names)

    def test_circular_dependency_detection(self):
        """Test detection of circular dependencies."""
        manager = StrategyDependencyManager()

        # Create circular dependency: A -> B -> C -> A
        deps = [
            StrategyDependency("strategy_a", "strategy_b", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("strategy_b", "strategy_c", DependencyType.REQUIRES_SUCCESS),
            StrategyDependency("strategy_c", "strategy_a", DependencyType.REQUIRES_SUCCESS),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        strategy_names = ["strategy_a", "strategy_b", "strategy_c"]

        # Should raise ValueError for circular dependency
        with pytest.raises(ValueError, match="Circular dependency detected"):
            manager.get_execution_order(strategy_names)

    def test_self_dependency_detection(self):
        """Test detection of self-dependencies."""
        manager = StrategyDependencyManager()

        # Create self-dependency
        dependency = StrategyDependency("strategy_a", "strategy_a", DependencyType.REQUIRES_SUCCESS)
        manager.add_dependency(dependency)

        strategy_names = ["strategy_a"]

        # Should raise ValueError for self-dependency
        with pytest.raises(ValueError, match="Self-dependency detected"):
            manager.get_execution_order(strategy_names)

    def test_get_blocked_strategies(self):
        """Test getting list of strategies blocked by dependencies."""
        manager = StrategyDependencyManager()

        # Set up dependencies
        deps = [
            StrategyDependency(
                "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
            ),
            StrategyDependency("dual_component", "knot_component", DependencyType.REQUIRES_SUCCESS),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        # Mock strategy results where handle_component fails
        handle_result = Mock()
        handle_result.matched = None  # Failure
        knot_result = Mock()
        knot_result.matched = {"fiber": "badger"}  # Success

        strategy_results = {"handle_component": handle_result, "knot_component": knot_result}

        blocked_strategies = manager.get_blocked_strategies(strategy_results)

        assert "dual_component" in blocked_strategies
        assert "handle_component" not in blocked_strategies  # Not blocked, just failed
        assert "knot_component" not in blocked_strategies  # Not blocked, just failed

    def test_get_dependency_status(self):
        """Test getting detailed dependency status for a strategy."""
        manager = StrategyDependencyManager()

        # Set up dependencies
        deps = [
            StrategyDependency(
                "dual_component", "handle_component", DependencyType.REQUIRES_SUCCESS
            ),
            StrategyDependency("dual_component", "knot_component", DependencyType.REQUIRES_SUCCESS),
        ]

        for dep in deps:
            manager.add_dependency(dep)

        # Mock strategy results
        handle_result = Mock()
        handle_result.matched = {"brand": "Test"}  # Success
        knot_result = Mock()
        knot_result.matched = None  # Failure

        strategy_results = {"handle_component": handle_result, "knot_component": knot_result}

        status = manager.get_dependency_status("dual_component", strategy_results)

        assert status["can_execute"] is False
        assert len(status["satisfied_dependencies"]) == 1
        assert len(status["unsatisfied_dependencies"]) == 1
        assert "handle_component" in status["satisfied_dependencies"]
        assert "knot_component" in status["unsatisfied_dependencies"]


class TestStrategyDependency:
    """Test cases for StrategyDependency data class."""

    def test_dependency_creation(self):
        """Test creating a dependency with all fields."""
        dependency = StrategyDependency(
            dependent_strategy="dual_component",
            depends_on_strategy="handle_component",
            dependency_type=DependencyType.REQUIRES_SUCCESS,
        )

        assert dependency.dependent_strategy == "dual_component"
        assert dependency.depends_on_strategy == "handle_component"
        assert dependency.dependency_type == DependencyType.REQUIRES_SUCCESS

    def test_dependency_equality(self):
        """Test dependency equality comparison."""
        dep1 = StrategyDependency("a", "b", DependencyType.REQUIRES_SUCCESS)
        dep2 = StrategyDependency("a", "b", DependencyType.REQUIRES_SUCCESS)
        dep3 = StrategyDependency("a", "c", DependencyType.REQUIRES_SUCCESS)

        assert dep1 == dep2
        assert dep1 != dep3

    def test_dependency_repr(self):
        """Test dependency string representation."""
        dependency = StrategyDependency("a", "b", DependencyType.REQUIRES_SUCCESS)
        repr_str = repr(dependency)

        assert "StrategyDependency" in repr_str
        assert "a" in repr_str
        assert "b" in repr_str
        assert "REQUIRES_SUCCESS" in repr_str


class TestDependencyType:
    """Test cases for DependencyType enum."""

    def test_dependency_type_values(self):
        """Test all dependency type values."""
        assert DependencyType.REQUIRES_SUCCESS.value == "requires_success"
        assert DependencyType.REQUIRES_FAILURE.value == "requires_failure"
        assert DependencyType.REQUIRES_ANY.value == "requires_any"
        assert DependencyType.REQUIRES_ALL.value == "requires_all"

    def test_dependency_type_names(self):
        """Test dependency type names."""
        assert DependencyType.REQUIRES_SUCCESS.name == "REQUIRES_SUCCESS"
        assert DependencyType.REQUIRES_FAILURE.name == "REQUIRES_FAILURE"
        assert DependencyType.REQUIRES_ANY.name == "REQUIRES_ANY"
        assert DependencyType.REQUIRES_ALL.name == "REQUIRES_ALL"
