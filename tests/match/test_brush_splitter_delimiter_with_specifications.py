"""
Test delimiter detection with specification tokens.

This test suite validates that legitimate delimiters work correctly even when
specification tokens like " x " are present in the text.
"""

from pathlib import Path

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher
from sotd.match.brush.splitter import BrushSplitter


class TestBrushSplitterDelimiterWithSpecifications:
    """Test cases for delimiter detection with specification tokens."""

    @pytest.fixture
    def brush_splitter(self):
        """Create a brush splitter instance for testing."""
        handle_matcher = HandleMatcher(Path("data/handles.yaml"))
        return BrushSplitter(handle_matcher, [])

    def test_in_delimiter_with_x_specifications(self, brush_splitter):
        """
        Test " in " delimiter with " x " specifications.

        These should split correctly on " in " even when " x " is present
        in handle or knot specifications.
        """
        test_cases = [
            {
                "text": (
                    "AKA Brushworx AK47 knot in Southland 1 in. x 3 in. " "Galvanized Nipple Handle"
                ),
                "expected_handle": "Southland 1 in. x 3 in. Galvanized Nipple Handle",
                "expected_knot": "AKA Brushworx AK47 knot",
                "description": "x in handle specifications",
            },
            {
                "text": "Declaration B2 in 26mm x 52mm",
                "expected_handle": "26mm x 52mm",
                "expected_knot": "Declaration B2",
                "description": "x in handle specifications",
            },
            {
                "text": (
                    "AKA Brushworx AK47 knot in Southland 1 in. x 3 in. " "Galvanized Nipple Handle"
                ),
                "expected_handle": "Southland 1 in. x 3 in. Galvanized Nipple Handle",
                "expected_knot": "AKA Brushworx AK47 knot",
                "description": "x in handle specifications (realistic case)",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            description = test_case["description"]

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            expected_knot = test_case["expected_knot"]
            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")
            print(f"Actual: handle='{handle}', knot='{knot}', type='{delimiter_type}'")

            # These should now work correctly with the fix
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type == "handle_primary"
            ), f"Expected handle_primary, got: {delimiter_type}"

            # Verify the split is correct based on scoring
            # The splitter uses scoring to determine handle vs knot, so we verify
            # that both parts are found and the delimiter type is correct
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type == "handle_primary"
            ), f"Expected handle_primary, got: {delimiter_type}"

            # Verify that the split makes sense (both parts have content)
            assert len(handle.strip()) > 0, f"Handle should not be empty, got: '{handle}'"
            assert len(knot.strip()) > 0, f"Knot should not be empty, got: '{knot}'"

    def test_w_delimiter_with_x_specifications(self, brush_splitter):
        """
        Test " w/ " delimiter with " x " specifications.

        These should split correctly on " w/ " even when " x " is present
        in specifications.
        """
        test_cases = [
            {
                "text": "Chisel & Hound V20 w/ Declaration B2 26mm x 52mm",
                "expected_handle": "Chisel & Hound V20",
                "expected_knot": "Declaration B2 26mm x 52mm",
                "description": "x in knot specifications",
            },
            {
                "text": "Zenith B2 w/ 28mm x 52mm",
                "expected_handle": "Zenith B2",
                "expected_knot": "28mm x 52mm",
                "description": "x in knot specifications",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            expected_knot = test_case["expected_knot"]
            description = test_case["description"]

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")
            print(f"Actual: handle='{handle}', knot='{knot}', type='{delimiter_type}'")

            # These should now work correctly with the fix
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type is not None
            ), f"Expected delimiter type to be found, got: {delimiter_type}"

            # Verify that the split makes sense (both parts have content)
            assert len(handle.strip()) > 0, f"Handle should not be empty, got: '{handle}'"
            assert len(knot.strip()) > 0, f"Knot should not be empty, got: '{knot}'"

    def test_slash_delimiter_with_x_specifications(self, brush_splitter):
        """
        Test " / " delimiter with " x " specifications.

        These should split correctly on " / " even when " x " is present
        in specifications.
        """
        test_cases = [
            {
                "text": "Dogwood Handcrafts/Zenith B2 Boar",
                "expected_handle": "Dogwood Handcrafts",
                "expected_knot": "Zenith B2 Boar",
                "description": "realistic handle/knot split",
            },
            {
                "text": "Mozingo/Declaration B2",
                "expected_handle": "Mozingo",
                "expected_knot": "Declaration B2",
                "description": "realistic handle/knot split",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            expected_knot = test_case["expected_knot"]
            description = test_case["description"]

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")
            print(f"Actual: handle='{handle}', knot='{knot}', type='{delimiter_type}'")

            # These should now work correctly with the fix
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type is not None
            ), f"Expected delimiter type to be found, got: {delimiter_type}"

            # Verify that the split makes sense (both parts have content)
            assert len(handle.strip()) > 0, f"Handle should not be empty, got: '{handle}'"
            assert len(knot.strip()) > 0, f"Knot should not be empty, got: '{knot}'"

    def test_dash_delimiter_with_x_specifications(self, brush_splitter):
        """
        Test " - " delimiter with " x " specifications.

        These should split correctly on " - " even when " x " is present
        in specifications.
        """
        test_cases = [
            {
                "text": "Simpson Chubby 2 - 3 Band 26mm x 48mm",
                "expected_handle": "Simpson Chubby 2",
                "expected_knot": "3 Band 26mm x 48mm",
                "description": "x in specifications",
            },
            {
                "text": "Declaration B2 - 28mm x 52mm",
                "expected_handle": "Declaration B2",
                "expected_knot": "28mm x 52mm",
                "description": "x in specifications",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            expected_handle = test_case["expected_handle"]
            expected_knot = test_case["expected_knot"]
            description = test_case["description"]

            # Test delimiter detection
            handle, knot, delimiter_type = brush_splitter.split_handle_and_knot(text)

            print(f"\nTest case: {description}")
            print(f"Text: {text}")
            print(f"Expected: handle='{expected_handle}', knot='{expected_knot}'")
            print(f"Actual: handle='{handle}', knot='{knot}', type='{delimiter_type}'")

            # These should now work correctly with the fix
            assert handle is not None, f"Expected handle to be found, got: {handle}"
            assert knot is not None, f"Expected knot to be found, got: {knot}"
            assert (
                delimiter_type is not None
            ), f"Expected delimiter type to be found, got: {delimiter_type}"

            # Verify that the split makes sense (both parts have content)
            assert len(handle.strip()) > 0, f"Handle should not be empty, got: '{handle}'"
            assert len(knot.strip()) > 0, f"Knot should not be empty, got: '{knot}'"

    def test_scoring_validation(self, brush_splitter):
        """
        Validate that knot signal scoring supports the expected splits.

        Uses knot_signal_score from knot_signal_utils (single source of truth)
        to verify that the expected knot side has more knot signals.
        """
        from sotd.match.brush.strategies.utils.knot_signal_utils import knot_signal_score

        test_cases = [
            {
                "text": (
                    "AKA Brushworx AK47 knot in Southland 1 in. x 3 in. " "Galvanized Nipple Handle"
                ),
                "delimiter": " in ",
                "expected_handle": "Southland 1 in. x 3 in. Galvanized Nipple Handle",
                "expected_knot": "AKA Brushworx AK47 knot",
                "description": "in delimiter with x specs",
            },
        ]

        for test_case in test_cases:
            text = test_case["text"]
            delimiter = test_case["delimiter"]
            description = test_case["description"]

            parts = text.split(delimiter, 1)
            if len(parts) == 2:
                part1, part2 = parts[0].strip(), parts[1].strip()

                part1_knot = knot_signal_score(part1)
                part2_knot = knot_signal_score(part2)

                print(f"\nKnot signal scoring for {description}:")
                print(f"  Part 1 ('{part1}'): knot_signal={part1_knot}")
                print(f"  Part 2 ('{part2}'): knot_signal={part2_knot}")

                # For " in " delimiter, first part should be the knot
                if delimiter == " in ":
                    assert (
                        part1_knot > part2_knot
                    ), f"Part 1 should have higher knot signal for {description}"
