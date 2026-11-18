import pytest

from sotd.match.brush.handle_matcher import HandleMatcher
from sotd.match.brush.splitter import BrushSplitter
from sotd.match.brush.strategies.known.known_brush_strategy import KnownBrushMatchingStrategy
from sotd.match.brush.strategies.other_brushes_strategy import OtherBrushMatchingStrategy


class TestBrushSplitterSmartAnalysis:
    """Test smart analysis for medium-reliability delimiters."""

    @pytest.fixture
    def brush_splitter(self):
        """Create brush splitter with handle matcher and strategies."""
        handle_matcher = HandleMatcher()
        # Mock strategies for testing
        strategies = [
            KnownBrushMatchingStrategy({}),
            OtherBrushMatchingStrategy({}),
        ]
        return BrushSplitter(handle_matcher, strategies)

    def test_plus_delimiter_handle_knot_combinations(self, brush_splitter):
        """Test that ' + ' delimiter handles handle/knot combinations correctly."""
        # Handle/knot combinations with different makers
        # Note: Current system uses content analysis, so results may differ from domain expectations
        test_cases = [
            ("C&H + TnS 27mm H8", "C&H", "TnS 27mm H8"),  # Chisel & Hound + Turn N Shave
            (
                "Wolf Whiskers + Declaration B15",
                "Wolf Whiskers",
                "Declaration B15",
            ),  # Content analysis prioritizes B15 pattern as knot
            ("Elite + Zenith B2", "Elite", "Zenith B2"),  # Content analysis result
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_plus_delimiter_joint_ventures(self, brush_splitter):
        """Test that ' + ' delimiter handles joint ventures correctly."""
        # Joint ventures (same maker collaboration)
        test_cases = [
            (
                "C&H + Mammoth DinoS'mores",
                "C&H",
                "Mammoth DinoS'mores",
            ),  # C&H + Mammoth collaboration
            (
                "Declaration + Chisel & Hound",
                "Declaration",
                "Chisel & Hound",
            ),  # DG + C&H collaboration
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            # For joint ventures, either order could be correct depending on context
            handle_val = handle.strip()
            knot_val = knot.strip()
            assert {handle_val, knot_val} == {
                expected_handle,
                expected_knot,
            }, f"Handle/knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_plus_delimiter_fiber_mixes(self, brush_splitter):
        """Test that ' + ' delimiter handles fiber mixes correctly."""
        # Fiber mixes (one side is fiber type, other is brand)
        test_cases = [
            ("Elite + Synthetic", "Elite", "Synthetic"),  # Brand + fiber type
            (
                "Synthetic + Elite",
                "Elite",
                "Synthetic",
            ),  # Fiber type + brand (should be normalized)
            ("Declaration + Boar", "Declaration", "Boar"),  # Brand + fiber type
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            # For fiber mixes, either order could be correct depending on context
            handle_val = handle.strip()
            knot_val = knot.strip()
            assert {handle_val, knot_val} == {
                expected_handle,
                expected_knot,
            }, f"Handle/knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_minus_delimiter_advanced_scoring(self, brush_splitter):
        """Test that ' - ' delimiter uses advanced scoring."""
        # Advanced scoring should prioritize handle vs knot based on content analysis
        test_cases = [
            # "Chisel & Hound - Rob's Finest - 25mm Synthetic" removed:
            # In prod this matches as known_brush (rob's.*finest.*syn),
            # so splitting never applies.
            # "Wolf Whiskers - Custom Handle - 26mm Badger" removed:
            # In prod this matches as a complete other_brush (wolf.*whiskers),
            # so splitting never applies.
            (
                "Elite - Declaration B15",
                "Elite",
                "Declaration B15",
            ),  # B15 should score higher as knot
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_in_delimiter_handle_priority(self, brush_splitter):
        """Test that ' in ' delimiter prioritizes handle component."""
        # Handle-primary delimiters should prioritize handle over knot
        test_cases = [
            ("Declaration Grooming in Stirling handle", "Stirling handle", "Declaration Grooming"),
            ("Zenith B2 in Custom handle", "Custom handle", "Zenith B2"),
            ("Simpson Chubby 2 in Wood handle", "Wood handle", "Simpson Chubby 2"),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "handle_primary", f"Wrong delimiter type for: {input_text}"

    def test_multiple_plus_delimiters(self, brush_splitter):
        """Test handling of multiple ' + ' delimiters in same text."""
        test_cases = [
            ("C&H + TnS 27mm", "C&H", "TnS 27mm"),  # C&H handle with TnS 27mm knot
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_ambiguous_plus_delimiter_cases(self, brush_splitter):
        """Test ambiguous cases where ' + ' delimiter could be interpreted multiple ways."""
        test_cases = [
            # Neither side has knot signals → tiebreaker uses left=handle convention
            (
                "Unknown Brand A + Unknown Brand B",
                "Unknown Brand A",
                "Unknown Brand B",
            ),
            ("Brand + Fiber + Size", "Brand", "Fiber + Size"),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "smart_analysis", f"Wrong delimiter type for: {input_text}"

    def test_advanced_scoring_handle_indicators(self, brush_splitter):
        """Test that advanced scoring correctly identifies handle indicators."""
        # Test cases where handle indicators should score higher
        test_cases = [
            (
                "Custom handle + Declaration B15",
                "Custom handle",
                "Declaration B15",
            ),  # Content analysis result
            ("Wood handle + Zenith B2", "Wood handle", "Zenith B2"),  # Content analysis result
            (
                "Artisan handle + Simpson Chubby 2",
                "Artisan handle",
                "Simpson Chubby 2",
            ),  # Content analysis result
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"

    def test_advanced_scoring_knot_indicators(self, brush_splitter):
        """Test that advanced scoring correctly identifies knot indicators."""
        # Test cases where knot indicators should score lower as handle
        test_cases = [
            ("Elite + 26mm Badger", "Elite", "26mm Badger"),  # Size + fiber should be knot
            ("Wolf Whiskers + B15", "Wolf Whiskers", "B15"),  # B15 should be knot
            (
                "Declaration + 28mm Synthetic",
                "Declaration",
                "28mm Synthetic",
            ),  # Size + fiber should be knot
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"

    def test_edge_cases_medium_reliability_delimiters(self, brush_splitter):
        """Test edge cases for medium-reliability delimiters."""
        test_cases = [
            ("", None, None),  # Empty string
            ("   ", None, None),  # Whitespace only
            ("SingleWord", None, None),  # No delimiters
            ("+", None, None),  # Delimiter only
            (" + ", None, None),  # Delimiter only with spaces
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot == expected_knot, f"Knot mismatch for: {input_text}"
            if expected_handle is None:
                # When no splitting occurs, delimiter_type can be None (known brush) or
                # "not_known_brush"
                assert delimiter_type in [
                    None,
                    "not_known_brush",
                ], f"Should not have delimiter type: {input_text}"

    def test_parentheses_delimiter_handle_knot_pattern(self, brush_splitter):
        """Test that ' (' delimiter handles handle (knot) pattern correctly."""
        # Basic pattern - handle (knot) - content-based scoring determines handle vs knot
        test_cases = [
            (
                "TurnNShave Shoat 28mm (Oumo Compass Avocado)",
                "Oumo Compass Avocado",  # Content scoring determines this is handle
                "TurnNShave Shoat 28mm",  # Content scoring determines this is knot
            ),
            (
                "Wolf Whiskers Custom Handle (Declaration B15)",
                "Wolf Whiskers Custom Handle",  # Handle description scores higher as handle
                "Declaration B15",  # B15 pattern scores higher as knot
            ),
            (
                "Elite Razor Handle (Zenith B2 Boar)",
                "Elite Razor Handle",  # Handle description scores higher as handle
                "Zenith B2 Boar",  # B2 Boar pattern scores higher as knot
            ),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "medium_reliability", f"Wrong delimiter type for: {input_text}"

    def test_parentheses_delimiter_knot_handle_pattern(self, brush_splitter):
        """Test that ' (' delimiter handles knot (handle) pattern correctly."""
        # Reverse pattern - knot (handle) - content-based scoring determines handle vs knot
        test_cases = [
            (
                "Oumo Compass 28mm (TurnNShave Shoat)",
                "TurnNShave Shoat",  # Brand name scores higher as handle
                "Oumo Compass 28mm",  # Size pattern scores higher as knot
            ),
            (
                "Declaration B15 (Wolf Whiskers Custom)",
                "Wolf Whiskers Custom",  # Brand name scores higher as handle
                "Declaration B15",  # B15 pattern scores higher as knot
            ),
            (
                "Zenith B2 Boar (Elite Razor Handle)",
                "Elite Razor Handle",  # Handle description scores higher as handle
                "Zenith B2 Boar",  # B2 Boar pattern scores higher as knot
            ),
        ]

        for input_text, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            assert handle is not None, f"Failed to split: {input_text}"
            assert knot is not None, f"Failed to split: {input_text}"
            assert handle.strip() == expected_handle, f"Handle mismatch for: {input_text}"
            assert knot.strip() == expected_knot, f"Knot mismatch for: {input_text}"
            assert delimiter_type == "medium_reliability", f"Wrong delimiter type for: {input_text}"

    def test_parentheses_delimiter_edge_cases(self, brush_splitter):
        """Test parentheses delimiter edge cases."""
        # Edge cases that should not split on parentheses
        edge_cases = [
            "TurnNShave Shoat 28mm",  # No parentheses
            "TurnNShave Shoat(",  # No leading space before parentheses
            "TurnNShave Shoat (",  # Missing closing parenthesis
            "TurnNShave Shoat ()",  # Empty content inside parentheses
            "TurnNShave Shoat (Oumo Compass",  # Missing closing parenthesis
        ]

        for input_text in edge_cases:
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(input_text)
            # These should not split on parentheses, may split on other delimiters or not at all
            if handle is not None and knot is not None:
                # If it does split, it shouldn't be due to parentheses
                assert (
                    delimiter_type != "medium_reliability" or " (" not in input_text
                ), f"Unexpected parentheses split for: {input_text}"
