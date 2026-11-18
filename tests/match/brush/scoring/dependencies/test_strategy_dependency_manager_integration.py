"""Integration tests for StrategyDependencyManager in scoring engine."""

from sotd.match.brush.scoring.dependencies.strategy_dependency_manager import (
    DependencyType,
    StrategyDependency,
    StrategyDependencyManager,
)
from sotd.match.brush_matcher import BrushMatcher
from sotd.match.types import MatchResult


class TestStrategyDependencyManagerIntegration:
    """Test StrategyDependencyManager integration with scoring engine."""

    def setup_method(self):
        """Set up test fixtures."""
        self.matcher = BrushMatcher()
        self.dependency_manager = StrategyDependencyManager()

    def test_integration_with_strategy_dependencies(self):
        """Test that dependency manager can handle strategy dependencies."""
        # Set up dependencies
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_FAILURE)
        )

        # Check execution order
        execution_order = self.dependency_manager.get_execution_order(
            ["StrategyA", "StrategyB", "StrategyC"]
        )

        # StrategyA should come first (no dependencies)
        assert execution_order[0] == "StrategyA"
        assert "StrategyB" in execution_order
        assert "StrategyC" in execution_order

    def test_integration_dependency_satisfaction(self):
        """Test dependency satisfaction logic with strategy results."""
        # Set up dependencies
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_FAILURE)
        )

        # Simulate StrategyA success
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }

        # Check which strategies can execute
        assert self.dependency_manager.can_execute_strategy("StrategyA", strategy_results)
        assert self.dependency_manager.can_execute_strategy("StrategyB", strategy_results)
        assert not self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Simulate StrategyA failure
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched=None,
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }

        assert self.dependency_manager.can_execute_strategy("StrategyA", strategy_results)
        assert not self.dependency_manager.can_execute_strategy("StrategyB", strategy_results)
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

    def test_integration_complex_dependency_scenarios(self):
        """Test complex dependency scenarios with multiple strategies."""
        # Set up complex dependency chain
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyB", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyD", "StrategyA", DependencyType.REQUIRES_ANY)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyE", "StrategyA", DependencyType.REQUIRES_ALL)
        )

        # Test execution order
        execution_order = self.dependency_manager.get_execution_order(
            ["StrategyA", "StrategyB", "StrategyC", "StrategyD", "StrategyE"]
        )

        # StrategyA should be first (no dependencies)
        assert execution_order[0] == "StrategyA"

        # StrategyB and StrategyC should be after StrategyA
        strategy_a_index = execution_order.index("StrategyA")
        strategy_b_index = execution_order.index("StrategyB")
        strategy_c_index = execution_order.index("StrategyC")

        assert strategy_b_index > strategy_a_index
        assert strategy_c_index > strategy_b_index

    def test_integration_requires_any_dependencies(self):
        """Test REQUIRES_ANY dependency type with multiple dependencies."""
        # Set up multiple dependencies with REQUIRES_ANY
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_ANY)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyB", DependencyType.REQUIRES_ANY)
        )

        # Test with no results (should be able to execute - no dependencies checked yet)
        strategy_results = {}
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with StrategyA success (should be able to execute)
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with StrategyB success (should be able to execute)
        strategy_results = {
            "StrategyB": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyB",
            )
        }
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with both failures (should not be able to execute)
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched=None,
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            ),
            "StrategyB": MatchResult(
                original="test",
                matched=None,
                match_type="regex",
                pattern="test",
                strategy="StrategyB",
            ),
        }
        assert not self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

    def test_integration_requires_all_dependencies(self):
        """Test REQUIRES_ALL dependency type with multiple dependencies."""
        # Set up multiple dependencies with REQUIRES_ALL
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_ALL)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyB", DependencyType.REQUIRES_ALL)
        )

        # Test with no results (should not be able to execute)
        strategy_results = {}
        assert not self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with only StrategyA success (should not be able to execute)
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }
        assert not self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with both successes (should be able to execute)
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            ),
            "StrategyB": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyB",
            ),
        }
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

        # Test with one failure (should not be able to execute)
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            ),
            "StrategyB": MatchResult(
                original="test",
                matched=None,
                match_type="regex",
                pattern="test",
                strategy="StrategyB",
            ),
        }
        assert not self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)

    def test_integration_circular_dependency_detection(self):
        """Test circular dependency detection in integration."""
        # Set up circular dependency
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyA", "StrategyB", DependencyType.REQUIRES_SUCCESS)
        )

        # Should detect circular dependency
        try:
            self.dependency_manager.get_execution_order(["StrategyA", "StrategyB"])
            assert False, "Should have raised ValueError for circular dependency"
        except ValueError as e:
            assert "circular dependency" in str(e).lower()

    def test_integration_dependency_status_monitoring(self):
        """Test dependency status monitoring and blocked strategies."""
        # Set up dependencies
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_FAILURE)
        )

        # Check dependency status for StrategyB (depends on StrategyA)
        status = self.dependency_manager.get_dependency_status("StrategyB", {})

        # StrategyB should have dependencies
        assert status["total_dependencies"] == 1
        assert "StrategyA" in status["unsatisfied_dependencies"]

        # Check dependency status for StrategyA (no dependencies)
        status = self.dependency_manager.get_dependency_status("StrategyA", {})

        # StrategyA should have no dependencies
        assert status["total_dependencies"] == 0
        assert status["can_execute"] is True

    def test_integration_blocked_strategies(self):
        """Test identification of blocked strategies."""
        # Set up dependencies
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_FAILURE)
        )

        # With no results, StrategyB and StrategyC should be blocked
        strategy_results = {}
        blocked = self.dependency_manager.get_blocked_strategies(strategy_results)

        assert "StrategyB" in blocked
        assert "StrategyC" in blocked
        assert "StrategyA" not in blocked

        # With StrategyA success, StrategyC should be blocked
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }
        blocked = self.dependency_manager.get_blocked_strategies(strategy_results)

        assert "StrategyC" in blocked
        assert "StrategyB" not in blocked
        assert "StrategyA" not in blocked

    def test_integration_mixed_dependency_types(self):
        """Test mixed dependency types in complex scenarios."""
        # Set up mixed dependency types
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyB", "StrategyA", DependencyType.REQUIRES_SUCCESS)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyA", DependencyType.REQUIRES_ANY)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyC", "StrategyB", DependencyType.REQUIRES_ANY)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyD", "StrategyA", DependencyType.REQUIRES_ALL)
        )
        self.dependency_manager.add_dependency(
            StrategyDependency("StrategyD", "StrategyB", DependencyType.REQUIRES_ALL)
        )

        # Test execution order
        execution_order = self.dependency_manager.get_execution_order(
            ["StrategyA", "StrategyB", "StrategyC", "StrategyD"]
        )

        # StrategyA should be first
        assert execution_order[0] == "StrategyA"

        # StrategyB should be after StrategyA
        strategy_a_index = execution_order.index("StrategyA")
        strategy_b_index = execution_order.index("StrategyB")
        assert strategy_b_index > strategy_a_index

        # Test dependency satisfaction with StrategyA success
        strategy_results = {
            "StrategyA": MatchResult(
                original="test",
                matched={"brand": "test"},
                match_type="regex",
                pattern="test",
                strategy="StrategyA",
            )
        }

        assert self.dependency_manager.can_execute_strategy("StrategyA", strategy_results)
        assert self.dependency_manager.can_execute_strategy("StrategyB", strategy_results)
        assert self.dependency_manager.can_execute_strategy("StrategyC", strategy_results)
        # Needs both A and B
        assert not self.dependency_manager.can_execute_strategy("StrategyD", strategy_results)
