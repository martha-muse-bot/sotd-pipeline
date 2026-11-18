"""Test baseline for current handle matching functionality before restructuring."""

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher


class TestHandleMatcherBaseline:
    """Test baseline for current handle matching functionality."""

    @pytest.fixture
    def handle_matcher(self, tmp_path):
        """Create handle matcher instance with test-specific YAML data."""
        # Create a test-specific handles.yaml file with known patterns
        # This prevents tests from failing when users modify production YAML files
        test_handles_data = {
            "artisan_handles": {
                "Declaration Grooming": {
                    "Washington": {
                        "patterns": ["washington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"]
                    },
                    "Jefferson": {
                        "patterns": ["jefferson(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"]
                    },
                    "Jeffington": {
                        "patterns": ["jeffington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"]
                    },
                    "Unspecified": {"patterns": ["declaration", "\\bdg\\b"]},
                },
                "Jayaruh": {"Unspecified": {"patterns": ["jayaruh"]}},
                "Dogwood": {
                    "Unspecified": {
                        "patterns": [
                            "dogwood.*(handcrafts+)?(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)",
                            "^voa",
                            "\\bdw\\b",
                        ]
                    }
                },
                "Chisel & Hound": {
                    "Unspecified": {
                        "patterns": [
                            "chisel.*hound(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)",
                            "\\bc(?:\\&|and|\\+\\s)?h\\b",
                        ]
                    }
                },
                "AKA Brushworx": {"Unspecified": {"patterns": ["aka.*brushworx"]}},
                "Alpha": {"Unspecified": {"patterns": ["alpha"]}},
                "Brad Sears": {"Unspecified": {"patterns": ["brad.*sears"]}},
            },
            "manufacturer_handles": {
                "Simpson": {"Unspecified": {"patterns": ["simpson"]}},
                "Omega": {"Unspecified": {"patterns": ["omega"]}},
                "Semogue": {"Unspecified": {"patterns": ["semogue"]}},
                "Mühle": {"Unspecified": {"patterns": ["muhle"]}},
            },
            "other_handles": {},
        }

        # Write test data to temporary YAML file
        import yaml

        test_handles_path = tmp_path / "test_handles.yaml"
        with test_handles_path.open("w") as f:
            yaml.dump(test_handles_data, f)

        # Create handle matcher with test data
        return HandleMatcher(handles_path=test_handles_path)

    def test_declaration_grooming_washington_pattern(self, handle_matcher):
        """Test Declaration Grooming Washington pattern matching."""
        result = handle_matcher.match_handle_maker("Declaration Grooming Washington")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["_matched_by_section"] == "artisan_handles"
        # New behavior: specific model patterns match first due to padding
        assert result["_pattern_used"] == "washington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_jefferson_pattern(self, handle_matcher):
        """Test Declaration Grooming Jefferson pattern matching."""
        result = handle_matcher.match_handle_maker("Declaration Grooming Jefferson")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["_matched_by_section"] == "artisan_handles"
        # New behavior: specific model patterns match first due to padding
        assert result["_pattern_used"] == "jefferson(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_jeffington_pattern(self, handle_matcher):
        """Test Declaration Grooming Jeffington pattern matching."""
        result = handle_matcher.match_handle_maker("Declaration Grooming Jeffington")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["_matched_by_section"] == "artisan_handles"
        # New behavior: specific model patterns match first due to padding
        assert result["_pattern_used"] == "jeffington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_general_pattern(self, handle_matcher):
        """Test Declaration Grooming general brand pattern matching."""
        result = handle_matcher.match_handle_maker("Declaration Grooming handle")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["_matched_by_section"] == "artisan_handles"
        # Test data has "declaration" pattern for general Declaration Grooming matching
        assert result["_pattern_used"] == "declaration"

    def test_declaration_grooming_dg_abbreviation(self, handle_matcher):
        """Test Declaration Grooming DG abbreviation pattern matching."""
        result = handle_matcher.match_handle_maker("DG handle")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["_matched_by_section"] == "artisan_handles"
        # Test data has "\\bdg\\b" pattern for DG abbreviation matching
        assert result["_pattern_used"] == "\\bdg\\b"

    def test_jayaruh_pattern(self, handle_matcher):
        """Test Jayaruh pattern matching."""
        result = handle_matcher.match_handle_maker("Jayaruh handle")
        assert result is not None
        assert result["handle_maker"] == "Jayaruh"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "jayaruh"

    def test_dogwood_handcrafts_patterns(self, handle_matcher):
        """Test Dogwood Handcrafts pattern matching."""
        # Test various Dogwood patterns
        test_cases = [
            ("Dogwood handle", "dogwood.*(handcrafts+)?(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"),
            (
                "Dogwood Handcrafts handle",
                "dogwood.*(handcrafts+)?(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)",
            ),
            ("VOA handle", "^voa"),
            ("DW handle", "\\bdw\\b"),
        ]

        for text, expected_pattern in test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == "Dogwood", f"Wrong maker for: {text}"
            assert result["_matched_by_section"] == "artisan_handles", f"Wrong section for: {text}"
            assert result["_pattern_used"] == expected_pattern, f"Wrong pattern for: {text}"

    def test_chisel_hound_patterns(self, handle_matcher):
        """Test Chisel & Hound pattern matching."""
        test_cases = [
            ("Chisel & Hound handle", "chisel.*hound"),
            ("C&H handle", r"\bc(?:\&|and|\+\s)?h\b"),
        ]

        for text, expected_pattern in test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == "Chisel & Hound", f"Wrong maker for: {text}"
            assert result["_matched_by_section"] == "artisan_handles", f"Wrong section for: {text}"

            # The implementation now uses priority padding for better pattern matching
            # Check that the pattern contains the expected base pattern
            actual_pattern = result["_pattern_used"]
            if expected_pattern == "chisel.*hound":
                # For Chisel & Hound, expect priority padding
                assert (
                    "chisel.*hound" in actual_pattern
                ), f"Pattern should contain 'chisel.*hound': {actual_pattern}"
                assert (
                    "PAD FOR PRIORITY LENGTH" in actual_pattern
                ), f"Pattern should contain priority padding: {actual_pattern}"
            else:
                # For other patterns, expect exact match
                assert actual_pattern == expected_pattern, f"Wrong pattern for: {text}"

    def test_manufacturer_handles_patterns(self, handle_matcher):
        """Test manufacturer handles pattern matching."""
        # Test some manufacturer patterns
        test_cases = [
            ("Simpson handle", "simpson"),
            ("Omega handle", "omega"),
            ("Semogue handle", "semogue"),
        ]

        for text, expected_pattern in test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert (
                result["_matched_by_section"] == "manufacturer_handles"
            ), f"Wrong section for: {text}"
            assert result["_pattern_used"] == expected_pattern, f"Wrong pattern for: {text}"

    def test_case_insensitive_matching(self, handle_matcher):
        """Test that handle matching is case insensitive."""
        test_cases = [
            ("DECLARATION GROOMING WASHINGTON", "Declaration Grooming"),
            ("jayaruh", "Jayaruh"),
            ("DOGWOOD HANDCRAFTS", "Dogwood"),
            ("chisel & hound", "Chisel & Hound"),
        ]

        for text, expected_maker in test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"

    def test_empty_input(self, handle_matcher):
        """Test handle matching with empty input."""
        result = handle_matcher.match_handle_maker("")
        assert result is None

    def test_no_match(self, handle_matcher):
        """Test handle matching with text that doesn't match any patterns."""
        result = handle_matcher.match_handle_maker("Unknown Brand Handle")
        assert result is None

    def test_priority_order(self, handle_matcher):
        """Test that artisan handles have priority over manufacturer handles."""
        # This test assumes that if there are overlapping patterns,
        # artisan_handles should take precedence over manufacturer_handles
        # The current implementation sorts by priority (lower = higher)
        patterns = handle_matcher.handle_patterns

        # Check that artisan_handles have priority 1
        artisan_patterns = [p for p in patterns if p["section"] == "artisan_handles"]
        for pattern in artisan_patterns:
            assert pattern["priority"] == 1

        # Check that manufacturer_handles have priority 2
        manufacturer_patterns = [p for p in patterns if p["section"] == "manufacturer_handles"]
        for pattern in manufacturer_patterns:
            assert pattern["priority"] == 2

    def test_is_known_handle_maker(self, handle_matcher):
        """Test is_known_handle_maker method."""
        # Test known handle makers
        assert handle_matcher.is_known_handle_maker("Declaration Grooming") is True
        assert handle_matcher.is_known_handle_maker("Jayaruh") is True
        assert handle_matcher.is_known_handle_maker("Dogwood") is True
        assert handle_matcher.is_known_handle_maker("Simpson") is True

        # Test unknown handle makers
        assert handle_matcher.is_known_handle_maker("Unknown Brand") is False
        assert handle_matcher.is_known_handle_maker("") is False

        # Test case insensitive
        assert handle_matcher.is_known_handle_maker("declaration grooming") is True
        assert handle_matcher.is_known_handle_maker("JAYARUH") is True

    def test_resolve_handle_maker(self, handle_matcher):
        """Test resolve_handle_maker method."""
        # Test with full text
        updated = {}
        handle_matcher.resolve_handle_maker(updated, "Declaration Grooming Washington")
        assert updated["handle_maker"] == "Declaration Grooming"

        # Test with brand field
        updated = {"brand": "Jayaruh"}
        handle_matcher.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Jayaruh"

        # Test with model field
        updated = {"model": "Declaration Grooming Jefferson"}
        handle_matcher.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Declaration Grooming"

    def test_all_existing_patterns_work(self, handle_matcher):
        """Test that all existing patterns in handles.yaml work correctly."""
        # This is a comprehensive test to ensure no patterns are broken
        # We'll test a representative sample of patterns from each section

        # Artisan handles
        artisan_test_cases = [
            ("AKA Brushworx handle", "AKA Brushworx"),
            ("Alpha handle", "Alpha"),
            ("Brad Sears handle", "Brad Sears"),
            ("Chisel & Hound handle", "Chisel & Hound"),
            ("Declaration Grooming Washington", "Declaration Grooming"),
            ("Dogwood Handcrafts handle", "Dogwood"),
            ("Jayaruh handle", "Jayaruh"),
        ]

        for text, expected_maker in artisan_test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match artisan handle: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["_matched_by_section"] == "artisan_handles", f"Wrong section for: {text}"

        # Manufacturer handles
        manufacturer_test_cases = [
            ("Simpson handle", "Simpson"),
            ("Omega handle", "Omega"),
            ("Semogue handle", "Semogue"),
            ("Muhle handle", "Mühle"),  # Note: actual catalog uses "Mühle"
        ]

        for text, expected_maker in manufacturer_test_cases:
            result = handle_matcher.match_handle_maker(text)
            assert result is not None, f"Failed to match manufacturer handle: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert (
                result["_matched_by_section"] == "manufacturer_handles"
            ), f"Wrong section for: {text}"
