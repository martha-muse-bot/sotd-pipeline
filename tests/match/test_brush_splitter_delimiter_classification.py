"""Test delimiter classification for brush splitting."""

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher
from sotd.match.brush.splitter import BrushSplitter


class TestBrushSplitterDelimiterClassification:
    """Test delimiter classification and reliability-based splitting."""

    @pytest.fixture
    def brush_splitter(self):
        """Create brush splitter with handle matcher and strategies."""
        handle_matcher = HandleMatcher()
        # Mock strategies for testing
        strategies = []
        return BrushSplitter(handle_matcher, strategies)

    def test_high_reliability_delimiters_always_trigger_splitting(self, brush_splitter):
        """Test that high-reliability delimiters always trigger splitting."""
        # High-reliability delimiters: " w/ ", " with " (removed "/" - now medium-priority)
        test_cases = [
            (
                "Wolf Whiskers RCE 1301 w/ Omega 10049 Boar",
                "Wolf Whiskers RCE 1301",
                "Omega 10049 Boar",
            ),
            (
                "Carnavis and Richardson with Declaration B15",
                "Carnavis and Richardson",
                "Declaration B15",
            ),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "high_reliability", f"Wrong delimiter type for: {input_text}"

    def test_medium_reliability_delimiters_use_smart_analysis(self, brush_splitter):
        """Test that medium-reliability delimiters use smart analysis."""
        # Medium-reliability delimiters: " + ", " - "
        test_cases = [
            ("C&H + TnS 27mm H8", "C&H", "TnS 27mm H8"),  # Handle/knot combination
            ("C&H + Mammoth DinoS'mores", "C&H", "Mammoth DinoS'mores"),  # Joint venture
            (
                "Chisel & Hound - Rob's Finest - 25mm Synthetic",
                "Chisel & Hound",
                "Rob's Finest - 25mm Synthetic",
            ),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            # Should use smart analysis for medium-reliability delimiters
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_smart_analysis_joint_ventures_and_fiber_mixes(self, brush_splitter):
        """Test smart analysis for joint ventures and fiber mixes.
        Covers medium-reliability delimiters and all '/' variants.
        All '/' variants (with or without spaces) should be treated as medium-priority delimiters.
        """
        test_cases = [
            # All variants of '/' delimiter should be treated identically
            ("Unknown Brand A/Unknown Brand B Brush", "Unknown Brand A", "Unknown Brand B Brush"),
            ("Unknown Brand A /Unknown Brand B Brush", "Unknown Brand A", "Unknown Brand B Brush"),
            ("Unknown Brand A/ Unknown Brand B Brush", "Unknown Brand A", "Unknown Brand B Brush"),
            ("Unknown Brand A / Unknown Brand B Brush", "Unknown Brand A", "Unknown Brand B Brush"),
            # Ambiguous: one side is a brand, one is a fiber
            ("Elite + Synthetic", "Elite", "Synthetic"),
            ("Synthetic + Elite", "Elite", "Synthetic"),
        ]
        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            # Allow either order for ambiguous/joint-venture cases
            handle_val = handle.strip()
            knot_val = knot.strip()
            assert {handle_val, knot_val} == {
                expected_handle,
                expected_knot,
            }, f"Handle/knot mismatch for: {input_text} (got: {handle_val}, {knot_val})"
            # All '/' variants should be medium_reliability
            if "/" in input_text and "+" not in input_text:
                assert (
                    delimiter_type == "medium_reliability"
                ), f"Wrong delimiter type for: {input_text}"
            else:
                assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_handle_primary_delimiters(self, brush_splitter):
        """Test that handle-primary delimiters work correctly."""
        # Handle-primary delimiters: " in "
        test_cases = [
            ("Declaration Grooming in Stirling handle", "Stirling handle", "Declaration Grooming"),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            # Should use handle-primary logic
            assert delimiter_type == "handle_primary", f"Wrong delimiter type for: {input_text}"

    def test_non_delimiters_do_not_trigger_splitting(self, brush_splitter):
        """Test that non-delimiters do not trigger splitting."""
        # Non-delimiters: " × ", " & "
        # Note: " x " IS now a delimiter for collaborations, but NOT for dimensions
        # Note: Parentheses "()" are now treated as medium-priority delimiters
        test_cases = [
            "Simpson Chubby 2 x 24mm",  # bare-number x size = dimension, not split
            "Zenith B2 × 26mm",
            "Chisel & Hound Sakura",
        ]

        for input_text in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            # Should not split on non-delimiters or dimension specs
            assert handle is None, f"Should not split: {input_text}"
            assert knot is None, f"Should not split: {input_text}"
            # When no splitting occurs, delimiter_type can be None (known brush) or
            # "not_known_brush"
            assert delimiter_type in [
                None,
                "not_known_brush",
            ], f"Should not have delimiter type: {input_text}"

    def test_x_collaboration_delimiter_triggers_splitting(self, brush_splitter):
        """Test that ' x ' triggers splitting for collaboration patterns."""
        test_cases = [
            ("Ever-Ready 200 x Tuxedo Knot", "Ever-Ready 200", "Tuxedo Knot"),
            (
                'ap shave co. - g5c 26mm x rad dinosaur creations "atlas" handle',
                'rad dinosaur creations "atlas" handle',
                "ap shave co. - g5c 26mm",
            ),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle == expected_handle, f"Wrong handle for: {input_text}"
            assert knot == expected_knot, f"Wrong knot for: {input_text}"

    def test_multiple_delimiters_handled_correctly(self, brush_splitter):
        """Test edge cases with multiple delimiters."""
        test_cases = [
            # Mixed delimiters - current implementation splits on first delimiter
            ("C&H + TnS w/ 27mm", "C&H + TnS", "27mm"),
            # Delimiters with extra spaces — neither side has knot signals,
            # so tiebreaker uses w/ convention: left=handle, right=knot
            ("Elite   w/   Declaration", "Elite", "Declaration"),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"

    def test_empty_or_invalid_inputs(self, brush_splitter):
        """Test handling of empty or invalid inputs."""
        test_cases = [
            "",  # Empty string
            "   ",  # Whitespace only
            "SingleWord",  # No delimiters
            "w/",  # Delimiter only
            "/",  # Delimiter only
        ]

        for input_text in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            # Should return None for all parts
            assert handle is None, f"Should not split: {input_text}"
            assert knot is None, f"Should not split: {input_text}"
            # When no splitting occurs, delimiter_type can be None (known brush) or
            # "not_known_brush"
            assert delimiter_type in [
                None,
                "not_known_brush",
            ], f"Should not have delimiter type: {input_text}"

    def test_delimiter_reliability_classification(self, brush_splitter):
        """Test that delimiter reliability is correctly classified."""
        # Test the internal delimiter classification
        high_reliability = [" w/ ", " with "]  # Removed " / " - now medium-priority
        handle_primary = [" in "]
        medium_reliability = [" + ", " - ", " / "]  # Added " / " to medium-priority
        non_delimiters = [" × ", " & ", "()"]

        # This test assumes the implementation will have a method to check delimiter reliability
        # We'll test this through the actual splitting behavior
        for delimiter in high_reliability:
            test_input = f"Handle{delimiter}Knot"
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(test_input)
            assert handle is not None, f"High-reliability delimiter failed: {delimiter}"
            assert knot is not None, f"High-reliability delimiter failed: {delimiter}"
            assert (
                delimiter_type == "high_reliability"
            ), f"Wrong type for high-reliability: {delimiter}"

        # Test medium-reliability delimiters
        for delimiter in medium_reliability:
            test_input = f"Handle{delimiter}Knot"
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(test_input)
            assert handle is not None, f"Medium-reliability delimiter failed: {delimiter}"
            assert knot is not None, f"Medium-reliability delimiter failed: {delimiter}"
            # Different delimiters return different types in the actual implementation
            if delimiter == " / ":
                assert (
                    delimiter_type == "medium_reliability"
                ), f"Wrong type for medium-reliability: {delimiter}"
            else:
                assert (
                    delimiter_type == "smart_analysis"
                ), f"Wrong type for smart analysis: {delimiter}"

        for delimiter in handle_primary:
            test_input = f"Handle{delimiter}Knot"
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(test_input)
            # Handle-primary delimiters should trigger splitting
            assert handle is not None, f"Handle-primary delimiter failed: {delimiter}"
            assert knot is not None, f"Handle-primary delimiter failed: {delimiter}"
            assert delimiter_type == "handle_primary", f"Wrong type for handle-primary: {delimiter}"

        for delimiter in non_delimiters:
            test_input = f"Handle{delimiter}Knot"
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(test_input)
            # Non-delimiters should not trigger splitting
            assert handle is None, f"Non-delimiter should not split: {delimiter}"
            assert knot is None, f"Non-delimiter should not split: {delimiter}"
            # When no splitting occurs, delimiter_type can be None (known brush) or
            # "not_known_brush"
            assert delimiter_type in [
                None,
                "not_known_brush",
            ], f"Non-delimiter should not have type: {delimiter}"
