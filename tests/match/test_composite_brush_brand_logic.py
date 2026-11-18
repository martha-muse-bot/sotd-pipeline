"""Tests for composite brush brand logic in brush matcher.

This module tests the business rule that when handle and knot have the same brand,
that brand should be automatically set at the top level of the brush result.
"""

from sotd.match.base_matcher import MatchResult
from sotd.match.brush_matcher import BrushMatcher


class TestCompositeBrushBrandLogic:
    """Test composite brush brand logic for same vs different brands."""

    def test_same_brand_gets_set_at_top_level(self):
        """Test that when handle and knot have same brand, it's set at top level."""
        # Create mock handle and knot results with same brand
        handle_result = MatchResult(
            original="AP Shave Co Beehive w/ G5C",
            matched={
                "handle_maker": "AP Shave Co",
                "handle_model": "Beehive",
                "_source_text": "AP Shave Co Beehive w/ G5C",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="AP Shave Co Beehive w/ G5C",
            matched={
                "brand": "AP Shave Co",
                "model": "G5C",
                "fiber": "Synthetic",
                "knot_size_mm": 26.0,
                "source_text": "AP Shave Co Beehive w/ G5C",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure
        assert result.matched is not None
        assert result.matched["brand"] == "AP Shave Co"  # Same brand set at top level
        assert result.matched["model"] == "Beehive"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] == "AP Shave Co"
        assert result.matched["handle"]["model"] == "Beehive"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] == "AP Shave Co"
        assert result.matched["knot"]["model"] == "G5C"
        assert result.matched["knot"]["fiber"] == "Synthetic"
        assert result.matched["knot"]["knot_size_mm"] == 26.0

    def test_different_brands_dont_get_set_at_top_level(self):
        """Test that when handle and knot have different brands, top level brand is handle brand."""
        # Create mock handle and knot results with different brands
        handle_result = MatchResult(
            original="Custom Handle w/ Declaration Grooming B2",
            matched={
                "handle_maker": "Custom Handle",
                "handle_model": "Artisan Turned",
                "_source_text": "Custom Handle w/ Declaration Grooming B2",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="Custom Handle w/ Declaration Grooming B2",
            matched={
                "brand": "Declaration Grooming",
                "model": "B2",
                "fiber": "Badger",
                "knot_size_mm": 26.0,
                "source_text": "Custom Handle w/ Declaration Grooming B2",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure
        assert result.matched is not None
        assert result.matched["brand"] == "Custom Handle"  # Handle brand (fallback)
        assert result.matched["model"] == "Artisan Turned"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] == "Custom Handle"
        assert result.matched["handle"]["model"] == "Artisan Turned"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] == "Declaration Grooming"
        assert result.matched["knot"]["model"] == "B2"
        assert result.matched["knot"]["fiber"] == "Badger"
        assert result.matched["knot"]["knot_size_mm"] == 26.0

    def test_handle_only_brand_fallback(self):
        """Test that when only handle has brand, it's used as fallback."""
        # Create mock handle result with brand, knot result without brand
        handle_result = MatchResult(
            original="AP Shave Co Handle w/ Unknown Knot",
            matched={
                "handle_maker": "AP Shave Co",
                "handle_model": "Custom Handle",
                "_source_text": "AP Shave Co Handle w/ Unknown Knot",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="AP Shave Co Handle w/ Unknown Knot",
            matched={
                "brand": None,  # No brand for knot
                "model": "Unknown",
                "fiber": "Unknown",
                "knot_size_mm": None,
                "source_text": "AP Shave Co Handle w/ Unknown Knot",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure
        assert result.matched is not None
        assert result.matched["brand"] == "AP Shave Co"  # Handle brand as fallback
        assert result.matched["model"] == "Custom Handle"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] == "AP Shave Co"
        assert result.matched["handle"]["model"] == "Custom Handle"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] is None
        assert result.matched["knot"]["model"] == "Unknown"

    def test_knot_only_brand_fallback(self):
        """Test that when only knot has brand, handle brand is still used as fallback."""
        # Create mock handle result without brand, knot result with brand
        handle_result = MatchResult(
            original="Unknown Handle w/ Declaration Grooming B2",
            matched={
                "handle_maker": None,  # No brand for handle
                "handle_model": "Unknown",
                "_source_text": "Unknown Handle",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="Unknown Handle w/ Declaration Grooming B2",
            matched={
                "brand": "Declaration Grooming",
                "model": "B2",
                "fiber": "Badger",
                "knot_size_mm": 26.0,
                "source_text": "Unknown Handle w/ Declaration Grooming B2",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure
        assert result.matched is not None
        assert result.matched["brand"] is None  # Handle brand (None) as fallback
        assert result.matched["model"] == "Unknown"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] is None
        assert result.matched["handle"]["model"] == "Unknown"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] == "Declaration Grooming"
        assert result.matched["knot"]["model"] == "B2"
        assert result.matched["knot"]["fiber"] == "Badger"
        assert result.matched["knot"]["knot_size_mm"] == 26.0

    def test_case_insensitive_brand_matching(self):
        """Test that brand matching is case sensitive (different case = different brands)."""
        # Create mock handle and knot results with same brand but different case
        handle_result = MatchResult(
            original="AP SHAVE CO Beehive w/ ap shave co G5C",
            matched={
                "handle_maker": "AP SHAVE CO",  # Uppercase
                "handle_model": "Beehive",
                "_source_text": "AP SHAVE CO Beehive w/ ap shave co G5C",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="AP SHAVE CO Beehive w/ ap shave co G5C",
            matched={
                "brand": "ap shave co",  # Lowercase
                "model": "G5C",
                "fiber": "Synthetic",
                "knot_size_mm": 26.0,
                "source_text": "AP SHAVE CO Beehive w/ ap shave co G5C",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure - should NOT match due to case difference
        assert result.matched is not None
        assert result.matched["brand"] == "AP SHAVE CO"  # Handle brand (fallback, not same brand)
        assert result.matched["model"] == "Beehive"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] == "AP SHAVE CO"
        assert result.matched["handle"]["model"] == "Beehive"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] == "ap shave co"
        assert result.matched["knot"]["model"] == "G5C"

    def test_empty_or_none_brand_handling(self):
        """Test handling of empty or None brand values."""
        # Create mock handle and knot results with empty/None brands
        handle_result = MatchResult(
            original="Handle w/ Knot",
            matched={
                "handle_maker": "",  # Empty string
                "handle_model": "Custom",
                "_source_text": "Handle w/ Knot",
                "_pattern_used": "handle_pattern",
            },
            match_type="handle",
            pattern="handle_pattern",
        )

        knot_result = MatchResult(
            original="Handle w/ Knot",
            matched={
                "brand": None,  # None
                "model": "Unknown",
                "fiber": "Unknown",
                "knot_size_mm": None,
                "source_text": "Handle w/ Knot",
                "_pattern_used": "knot_pattern",
            },
            match_type="knot",
            pattern="knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify the result structure
        assert result.matched is not None
        assert result.matched["brand"] == ""  # Empty string from handle (not same as None)
        assert result.matched["model"] == "Custom"  # Handle model preserved

        # Verify handle section
        assert "handle" in result.matched
        assert result.matched["handle"]["brand"] == ""
        assert result.matched["handle"]["model"] == "Custom"

        # Verify knot section
        assert "knot" in result.matched
        assert result.matched["knot"]["brand"] is None
        assert result.matched["knot"]["model"] == "Unknown"

    def test_metadata_preservation(self):
        """Test that metadata fields are properly preserved in the combined result."""
        # Create mock handle and knot results
        handle_result = MatchResult(
            original="Test Handle w/ Test Knot",
            matched={
                "handle_maker": "Test Brand",
                "handle_model": "Test Handle",
                "_source_text": "Test Handle w/ Test Knot",
                "_pattern_used": "test_handle_pattern",
            },
            match_type="handle",
            pattern="test_handle_pattern",
        )

        knot_result = MatchResult(
            original="Test Handle w/ Test Knot",
            matched={
                "brand": "Test Brand",  # Same brand as handle
                "model": "Test Knot",
                "fiber": "Test Fiber",
                "knot_size_mm": 24.0,
                "source_text": "Test Handle w/ Test Knot",
                "_pattern_used": "test_knot_pattern",
            },
            match_type="knot",
            pattern="test_knot_pattern",
        )

        # Create a minimal brush matcher instance
        matcher = BrushMatcher.__new__(BrushMatcher)

        # Call the method that combines handle and knot results
        result = matcher._combine_handle_and_knot_results(handle_result, knot_result)

        # Verify metadata preservation
        assert result.matched is not None
        assert result.matched["_matched_by"] == "HandleMatcher+KnotMatcher"
        assert result.matched["_pattern"] == "test_handle_pattern"
        assert (
            result.matched["source_text"] == "Test Handle w/ Test Knot"
        )  # Uses full original text

        # Verify handle metadata
        assert result.matched["handle"]["_matched_by"] == "HandleMatcher"
        assert result.matched["handle"]["_pattern"] == "test_handle_pattern"

        # Verify knot metadata
        assert result.matched["knot"]["_matched_by"] == "KnotMatcher"
        assert result.matched["knot"]["_pattern"] == "test_knot_pattern"

        # Verify match type
        assert result.match_type == "composite"
        assert result.pattern == "test_handle_pattern"
