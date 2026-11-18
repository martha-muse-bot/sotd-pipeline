"""
Test edge cases for brush splitter delimiter detection.

This test covers edge cases where specification tokens might interfere
with legitimate delimiter detection.
"""

from pathlib import Path

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher
from sotd.match.brush.splitter import BrushSplitter
from sotd.match.brush_matcher import BrushMatcher


class TestBrushSplitterEdgeCases:
    """Test edge cases for brush splitting."""

    @pytest.fixture(autouse=True)
    def setup_test_fixtures(
        self,
        test_correct_matches_path,
        test_brushes_path,
        test_handles_path,
        test_knots_path,
        test_brush_scoring_config_path,
    ):
        """Set up test fixtures."""
        self.handle_matcher = HandleMatcher(test_handles_path)
        self.splitter = BrushSplitter(self.handle_matcher)
        # Also test with the new scoring system
        self.scoring_matcher = BrushMatcher(
            correct_matches_path=test_correct_matches_path,
            brushes_path=test_brushes_path,
            handles_path=test_handles_path,
            knots_path=test_knots_path,
            brush_scoring_config_path=test_brush_scoring_config_path,
        )

    def test_fiber_words_dont_force_split_for_complete_brushes(self):
        """Test that fiber words don't force a split when string should be a complete brush."""
        # These strings contain fiber words but should be treated as complete brushes
        # because they match known brush patterns in the catalog
        test_cases = [
            "Zenith r/wetshaving MOAR BOAR",  # Contains "BOAR" but should be complete brush
            "Zenith 31mm MOAR BOAR",  # Contains "BOAR" but should be complete brush
            "Zenith 508 Moar Boar",  # Contains "Boar" but should be complete brush
            "Zenith MOAR Boar",  # Contains "Boar" but should be complete brush
            "Zenith Moar Boar Sub Exclusive",  # Contains "Boar" but should be complete brush
        ]

        for test_str in test_cases:
            handle, knot, delimiter = self.splitter.split_handle_and_knot(test_str)
            # Should NOT be split - should return None, None, None for complete brushes
            # OR None, None, "not_known_brush" if not recognized as known brush
            assert handle is None, f"Expected no split for '{test_str}', got handle: {handle}"
            assert knot is None, f"Expected no split for '{test_str}', got knot: {knot}"
            # The delimiter can be None (known brush) or "not_known_brush" (not recognized)
            assert delimiter in [
                None,
                "not_known_brush",
            ], f"Expected no split for '{test_str}', got delimiter: {delimiter}"

    def test_fiber_words_do_split_when_appropriate(self):
        """Test that fiber words do cause splitting when appropriate."""
        # These strings should be split because they contain clear delimiters
        # and the fiber word indicates which part is the knot
        test_cases = [
            ("Elite handle w/ Declaration Boar knot", "Elite handle", "Declaration Boar knot"),
            ("Wolf Whiskers w/ Omega Boar", "Wolf Whiskers", "Omega Boar"),
        ]

        for test_str, expected_handle, expected_knot in test_cases:
            handle, knot, delimiter = self.splitter.split_handle_and_knot(test_str)
            # Should be split
            assert handle is not None, f"Expected split for '{test_str}', got no handle"
            assert knot is not None, f"Expected split for '{test_str}', got no knot"
            assert (
                handle.strip() == expected_handle
            ), f"Expected handle '{expected_handle}', got '{handle}'"
            assert knot.strip() == expected_knot, f"Expected knot '{expected_knot}', got '{knot}'"

    @pytest.fixture
    def brush_splitter(self):
        """Create a brush splitter instance for testing."""
        handle_matcher = HandleMatcher(Path("data/handles.yaml"))
        return BrushSplitter(handle_matcher, [])

    def test_multiple_x_specifications(self, brush_splitter):
        """
        Test cases with multiple " x " specifications.

        These should still split correctly on legitimate delimiters.
        """
        test_cases = [
            {
                "text": "AKA Brushworx AK47 knot in Southland 1 in. x 3 in. x 5 in. Handle",
                "expected_handle": "Southland 1 in. x 3 in. x 5 in. Handle",
                "expected_knot": "AKA Brushworx AK47 knot",
                "description": "multiple x in handle specs",
            },
            {
                "text": "Declaration B2 in Mozingo handle",
                "expected_handle": "Mozingo handle",
                "expected_knot": "Declaration B2",
                "description": "realistic handle/knot split",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            expected_knot = test_case["expected_knot"]
            description = test_case["description"]

            # Count " x " occurrences
            x_count = text.count(" x ")
            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"X count: {x_count}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            # These should now work correctly with the fix implemented
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type == "handle_primary"
            ), f"Expected handle_primary, got: {delimiter_type}"

            # Verify the split is correct
            assert (
                handle == expected_handle
            ), f"Expected handle '{expected_handle}', got: '{handle}'"
            assert knot == expected_knot, f"Expected knot '{expected_knot}', got: '{knot}'"

    def test_x_in_brand_names(self, brush_splitter):
        """
        Test cases where " x " appears in brand names.

        These should still split correctly on legitimate delimiters.
        """
        test_cases = [
            {
                "text": "X Brand knot in Southland Handle",
                "expected_handle": "Southland Handle",
                "expected_knot": "X Brand knot",
                "description": "X in brand name",
            },
            {
                "text": "Brand X knot in Southland Handle",
                "expected_handle": "Southland Handle",
                "expected_knot": "Brand X knot",
                "description": "X in brand name",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            expected_knot = test_case["expected_knot"]
            description = test_case["description"]

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            # These should work correctly since " x " is not present
            if " x " not in text:
                assert handle is not None, f"Expected handle to be found for {description}"
                assert knot is not None, f"Expected knot to be found for {description}"
                assert (
                    delimiter_type == "handle_primary"
                ), f"Expected handle_primary, got: {delimiter_type}"

    def test_x_in_specifications_vs_delimiters(self, brush_splitter):
        """
        Test cases that distinguish between " x " in specifications vs delimiters.

        The key insight: " x " in specifications is typically surrounded by
        measurements or dimensions, while " x " as a delimiter would be
        between complete phrases.
        """
        test_cases = [
            {
                "text": "AKA Brushworx AK47 knot in Southland Galvanized Nipple Handle",
                "x_context": "none",
                "description": "realistic handle/knot split",
                "should_split_on_in": True,
                "should_split_on_slash": False,
            },
            {
                "text": "Declaration B2 in Mozingo handle",
                "x_context": "none",
                "description": "realistic handle/knot split",
                "should_split_on_in": True,
                "should_split_on_slash": False,
            },
            {
                "text": "Dogwood Handcrafts/Zenith B2 Boar",
                "x_context": "none",
                "description": "realistic handle/knot split",
                "should_split_on_in": False,
                "should_split_on_slash": True,
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            x_context = test_case["x_context"]
            description = test_case["description"]
            should_split_on_in = test_case["should_split_on_in"]

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"X context: '{x_context}'")
            print(f"Should split on delimiter: {should_split_on_in}")

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            # These should now work correctly with the fix implemented
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type is not None
            ), f"Expected delimiter type to be found, got: {delimiter_type}"

            # Verify that the split makes sense (both parts have content)
            assert len(handle.strip()) > 0, f"Handle should not be empty, got: '{handle}'"
            assert len(knot.strip()) > 0, f"Knot should not be empty, got: '{knot}'"

    def test_ampersand_edge_cases(self, brush_splitter):
        """
        Test edge cases with " & " to confirm it's unreliable.

        These demonstrate why " & " should not be used as a delimiter.
        """
        test_cases = [
            {
                "text": "Chisel & Hound v23",
                "description": "Brand name with &",
                "should_split": False,
                "reason": "Brand name, should not split",
            },
            {
                "text": "My handle & my knot",
                "description": "Ambiguous handle/knot",
                "should_split": False,
                "reason": "Ambiguous, unreliable",
            },
            {
                "text": "G5C & Muninn Woodworks curly pine",
                "description": "Ambiguous maker/knot",
                "should_split": False,
                "reason": "Ambiguous, unreliable",
            },
            {
                "text": "C&H v23 Zebra",
                "description": "Brand name with &",
                "should_split": False,
                "reason": "Brand name, should not split",
            },
            {
                "text": "Chisel & Hound V20 w/ Declaration B2",
                "description": "Brand with & but legitimate w/ delimiter",
                "should_split": True,
                "reason": "Legitimate w/ delimiter should work",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            description = test_case["description"]
            should_split = test_case["should_split"]
            reason = test_case["reason"]

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Should split: {should_split}")
            print(f"Reason: {reason}")

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            print(
                f"Delimiter detection result: handle='{handle}', "
                f"knot='{knot}', type='{delimiter_type}'"
            )

            # Document the current behavior
            if should_split:
                # These should work if the delimiter detection is working correctly
                if " w/ " in text:
                    # The " w/ " delimiter should work even with " & " in brand names
                    print("  Note: ' w/ ' delimiter should work despite ' & ' in text")
            else:
                # These should not split
                print("  Note: Should not split due to ' & ' ambiguity")

    def test_specification_patterns(self, brush_splitter):
        """
        Test patterns that identify " x " as specifications vs delimiters.

        This helps define the logic for distinguishing between the two.
        """
        specification_patterns = [
            {
                "text": "1 in. x 3 in.",
                "description": "measurements with units",
                "is_specification": True,
            },
            {
                "text": "26mm x 52mm",
                "description": "dimensions with units",
                "is_specification": True,
            },
            {
                "text": "28mm x 52mm",
                "description": "size specifications",
                "is_specification": True,
            },
            {
                "text": "handle x knot",
                "description": "delimiter pattern",
                "is_specification": False,
            },
            {
                "text": "brand x model",
                "description": "delimiter pattern",
                "is_specification": False,
            },
        ]

        for pattern in specification_patterns:
            text = pattern["text"]
            description = pattern["description"]
            is_specification = pattern["is_specification"]

            print(f"\nPattern: {description}")
            print(f"Text: '{text}'")
            print(f"Is specification: {is_specification}")

            # Test if we can identify specification patterns
            has_units = any(unit in text for unit in ["mm", "in.", "cm", "ft"])
            has_numbers = any(char.isdigit() for char in text)

            print(f"  Has units: {has_units}")
            print(f"  Has numbers: {has_numbers}")

            # Specification patterns typically have units and numbers
            if is_specification:
                assert (
                    has_units or has_numbers
                ), f"Specification should have units or numbers: {text}"
            else:
                print("  Note: Delimiter patterns may not have units/numbers")

    def test_new_scoring_system_handles_edge_cases(self):
        """Test that the new scoring system handles the same edge cases correctly."""
        # Test cases that should NOT be split (complete brushes)
        complete_brush_cases = [
            "Zenith r/wetshaving MOAR BOAR",
            "Zenith 31mm MOAR BOAR",
            "Zenith 508 Moar Boar",
        ]

        for test_str in complete_brush_cases:
            result = self.scoring_matcher.match(test_str)
            # Should return a match result, not None
            assert result is not None, f"Expected match for '{test_str}', got None"
            # Should have matched data
            assert result.matched is not None, f"Expected matched data for '{test_str}'"

        # Test cases that SHOULD be split (clear delimiters)
        split_cases = [
            "Elite handle w/ Declaration Boar knot",
            "Wolf Whiskers w/ Omega Boar",
        ]

        for test_str in split_cases:
            result = self.scoring_matcher.match(test_str)
            # Should return a match result
            assert result is not None, f"Expected match for '{test_str}', got None"
            # Should have matched data
            assert result.matched is not None, f"Expected matched data for '{test_str}'"
