"""Tests for unified MatchResult class and related utilities."""

from sotd.match.types import MatchResult, create_match_result


class TestUnifiedMatchResultCreation:
    """Test unified MatchResult class creation and attributes."""

    def test_unified_match_result_creation(self):
        """Test unified MatchResult class creation and attributes."""
        # Simple matcher result (no section info)
        simple_result = MatchResult(
            original="Koraat Moarteen",
            matched={"brand": "Koraat", "model": "Moarteen"},
            match_type="regex",
            pattern="koraat.*moarteen",
            # section=None, priority=None by default
        )

        assert simple_result.original == "Koraat Moarteen"
        assert simple_result.matched is not None
        assert simple_result.matched["brand"] == "Koraat"
        assert simple_result.section is None
        assert simple_result.priority is None
        assert not simple_result.has_section_info

        # Section-based matcher result (with section info)
        section_result = MatchResult(
            original="Zenith B2",
            matched={"brand": "Zenith", "model": "B2"},
            match_type="regex",
            pattern="zenith.*\\bb2\\b",
            section="known_knots",
            priority=1,
        )

        assert section_result.section == "known_knots"
        assert section_result.priority == 1
        assert section_result.has_section_info


class TestBackwardCompatibilityWithExistingProducers:
    """Test that existing MatchResult producers continue to work."""

    def test_backward_compatibility_with_existing_producers(self):
        """Test that existing MatchResult producers continue to work."""
        # Test factory function still works
        result = create_match_result(
            original="Test Product",
            matched={"brand": "Test", "model": "Product"},
            match_type="regex",
            pattern="test.*product",
        )

        assert isinstance(result, MatchResult)
        assert result.original == "Test Product"
        assert result.matched is not None
        assert result.matched["brand"] == "Test"
        assert result.section is None  # Default for backward compatibility
        assert result.priority is None  # Default for backward compatibility

        # Test direct instantiation with old-style parameters
        old_style_result = MatchResult(
            original="Old Style", matched={"brand": "Old"}, match_type="regex", pattern="old.*style"
        )

        assert old_style_result.section is None
        assert old_style_result.priority is None


class TestBackwardCompatibilityWithExistingConsumers:
    """Test that existing MatchResult consumers continue to work."""

    def test_backward_compatibility_with_existing_consumers(self):
        """Test that existing MatchResult consumers continue to work."""
        # Test that existing properties still work
        result = MatchResult(
            original="Test Product",
            matched={"brand": "Test", "model": "Product"},
            match_type="regex",
            pattern="test.*product",
        )

        # Test existing property access
        assert result.original == "Test Product"
        assert result.matched is not None
        assert result.matched["brand"] == "Test"
        assert result.match_type == "regex"
        assert result.pattern == "test.*product"

        # Test existing method access
        assert result.get("brand") == "Test"
        assert result.get("nonexistent", "default") == "default"

        # Test that new fields don't break existing code
        assert result.section is None
        assert result.priority is None
        assert not result.has_section_info


class TestMatchResultProperties:
    """Test MatchResult properties and methods."""

    def test_has_section_info_property(self):
        """Test has_section_info property for clarity."""
        # Simple matcher result
        simple_result = MatchResult(
            original="Test", matched={"brand": "Test"}, match_type="regex", pattern="test"
        )
        assert not simple_result.has_section_info

        # Section-based matcher result
        section_result = MatchResult(
            original="Test",
            matched={"brand": "Test"},
            match_type="regex",
            pattern="test",
            section="known_knots",
            priority=1,
        )
        assert section_result.has_section_info

    def test_matched_bool_property(self):
        """Test matched_bool property for backward compatibility."""
        # Successful match
        success_result = MatchResult(
            original="Test", matched={"brand": "Test"}, match_type="regex", pattern="test"
        )
        assert success_result.matched_bool

        # Failed match
        failed_result = MatchResult(original="Test", matched=None, match_type=None, pattern=None)
        assert not failed_result.matched_bool
