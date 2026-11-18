"""Unit tests for ResultConflictResolver component."""

from sotd.match.brush.scoring.resolver import (
    ConflictType,
    ResultConflictResolver,
)
from sotd.match.types import MatchResult


class TestResultConflictResolver:
    """Test cases for ResultConflictResolver."""

    def test_init_with_no_conflicts(self):
        """Test initialization with no conflicts."""
        resolver = ResultConflictResolver()
        assert resolver.conflicts == []
        assert resolver.resolutions == []

    def test_detect_brand_conflicts(self):
        """Test detection of brand conflicts."""
        resolver = ResultConflictResolver()

        # Create results with conflicting brands
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.BRAND
        assert conflicts[0].field == "brand"
        assert conflicts[0].values == {"Declaration Grooming", "Dogwood Handcrafts"}
        assert conflicts[0].affected_results == [result1, result2]

    def test_detect_model_conflicts(self):
        """Test detection of model conflicts."""
        resolver = ResultConflictResolver()

        # Create results with conflicting models
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B3"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.MODEL
        assert conflicts[0].field == "model"
        assert conflicts[0].values == {"B2", "B3"}
        assert conflicts[0].affected_results == [result1, result2]

    def test_detect_fiber_conflicts(self):
        """Test detection of fiber conflicts."""
        resolver = ResultConflictResolver()

        # Create results with conflicting fiber types
        result1 = MatchResult(
            original="Declaration badger",
            matched={"brand": "Declaration Grooming", "fiber": "badger"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration badger",
            matched={"brand": "Declaration Grooming", "fiber": "boar"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.FIBER
        assert conflicts[0].field == "fiber"
        # Order doesn't matter for set comparison
        assert conflicts[0].values == {"badger", "boar"}
        assert conflicts[0].affected_results == [result1, result2]

    def test_detect_knot_size_conflicts(self):
        """Test detection of knot size conflicts."""
        resolver = ResultConflictResolver()

        # Create results with conflicting knot sizes
        result1 = MatchResult(
            original="Declaration 26mm",
            matched={"brand": "Declaration Grooming", "knot_size": "26mm"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration 26mm",
            matched={"brand": "Declaration Grooming", "knot_size": "28mm"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])

        assert len(conflicts) == 1
        assert conflicts[0].conflict_type == ConflictType.KNOT_SIZE
        assert conflicts[0].field == "knot_size"
        assert conflicts[0].values == {"26mm", "28mm"}
        assert conflicts[0].affected_results == [result1, result2]

    def test_detect_multiple_conflicts(self):
        """Test detection of multiple conflicts in same results."""
        resolver = ResultConflictResolver()

        # Create results with multiple conflicts
        result1 = MatchResult(
            original="Declaration B2 badger",
            matched={"brand": "Declaration Grooming", "model": "B2", "fiber": "badger"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration B2 badger",
            matched={"brand": "Dogwood Handcrafts", "model": "B3", "fiber": "boar"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])

        assert len(conflicts) == 3

        conflict_types = {c.conflict_type for c in conflicts}
        assert conflict_types == {ConflictType.BRAND, ConflictType.MODEL, ConflictType.FIBER}

    def test_no_conflicts_detected(self):
        """Test when no conflicts are detected."""
        resolver = ResultConflictResolver()

        # Create results with no conflicts
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])
        assert len(conflicts) == 0

    def test_resolve_conflicts_by_score(self):
        """Test conflict resolution by confidence score."""
        resolver = ResultConflictResolver()

        # Create conflicting results with different confidence scores
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
            score=0.9,
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="strategy2",
            score=0.7,
        )

        resolution = resolver.resolve_conflicts([result1, result2], resolution_method="score")

        assert resolution.winning_result == result1
        assert resolution.resolution_method == "score"
        assert len(resolution.resolved_conflicts) == 1
        assert resolution.resolved_conflicts[0].conflict_type == ConflictType.BRAND

    def test_resolve_conflicts_by_strategy_priority(self):
        """Test conflict resolution by strategy priority."""
        resolver = ResultConflictResolver()

        # Create conflicting results with same confidence but different strategy priorities
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="BrushSplitter",  # Higher priority strategy
            score=0.8,
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="HandleMatcher",  # Lower priority strategy
            score=0.8,
        )

        resolution = resolver.resolve_conflicts([result1, result2], resolution_method="priority")

        assert resolution.winning_result == result1
        assert resolution.resolution_method == "priority"

    def test_resolve_conflicts_by_confidence(self):
        """Test conflict resolution by confidence level."""
        resolver = ResultConflictResolver()

        # Create conflicting results with different confidence levels
        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
            score=0.6,
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="strategy2",
            score=0.8,
        )

        resolution = resolver.resolve_conflicts([result1, result2], resolution_method="confidence")

        assert resolution.winning_result == result2
        assert resolution.resolution_method == "confidence"

    def test_resolve_conflicts_manual_selection(self):
        """Test conflict resolution with manual selection."""
        resolver = ResultConflictResolver()

        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
            score=0.8,
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="strategy2",
            score=0.7,
        )

        resolution = resolver.resolve_conflicts(
            [result1, result2], resolution_method="manual", selected_result=result2
        )

        assert resolution.winning_result == result2
        assert resolution.resolution_method == "manual"

    def test_get_conflict_summary(self):
        """Test generation of conflict summary."""
        resolver = ResultConflictResolver()

        # Create results with multiple conflicts
        result1 = MatchResult(
            original="Declaration B2 badger",
            matched={"brand": "Declaration Grooming", "model": "B2", "fiber": "badger"},
            strategy="strategy1",
        )
        result2 = MatchResult(
            original="Declaration B2 badger",
            matched={"brand": "Dogwood Handcrafts", "model": "B3", "fiber": "boar"},
            strategy="strategy2",
        )

        conflicts = resolver.detect_conflicts([result1, result2])
        summary = resolver.get_conflict_summary(conflicts)

        assert "3 conflicts detected" in summary
        assert "brand" in summary
        assert "model" in summary
        assert "fiber" in summary
        assert "Declaration Grooming vs Dogwood Handcrafts" in summary
        assert "B2 vs B3" in summary
        assert "badger vs boar" in summary

    def test_validate_resolution(self):
        """Test validation of conflict resolution."""
        resolver = ResultConflictResolver()

        result1 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
            score=0.8,
        )
        result2 = MatchResult(
            original="Declaration B2",
            matched={"brand": "Dogwood Handcrafts", "model": "B2"},
            strategy="strategy2",
            score=0.7,
        )

        resolution = resolver.resolve_conflicts([result1, result2])
        is_valid = resolver.validate_resolution(resolution)

        assert is_valid is True

    def test_handle_empty_results(self):
        """Test handling of empty result list."""
        resolver = ResultConflictResolver()

        conflicts = resolver.detect_conflicts([])
        assert len(conflicts) == 0

        resolution = resolver.resolve_conflicts([])
        assert resolution.winning_result is None

    def test_handle_single_result(self):
        """Test handling of single result (no conflicts)."""
        resolver = ResultConflictResolver()

        result = MatchResult(
            original="Declaration B2",
            matched={"brand": "Declaration Grooming", "model": "B2"},
            strategy="strategy1",
            score=0.8,
        )

        conflicts = resolver.detect_conflicts([result])
        assert len(conflicts) == 0

        resolution = resolver.resolve_conflicts([result])
        assert resolution.winning_result == result
        assert len(resolution.resolved_conflicts) == 0
