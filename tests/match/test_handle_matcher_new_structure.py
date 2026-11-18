"""Test handle matcher with new brand/model hierarchy structure."""

from pathlib import Path

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher


class TestHandleMatcherNewStructure:
    """Test handle matcher with new brand/model hierarchy structure."""

    @pytest.fixture
    def handle_matcher_new_structure(self):
        """Create handle matcher instance with new structure."""
        return HandleMatcher(Path("data/handles_new_structure.yaml"))

    def test_declaration_grooming_washington_model(self, handle_matcher_new_structure):
        """Test Declaration Grooming Washington model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming Washington")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["handle_model"] == "Washington"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "washington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_jefferson_model(self, handle_matcher_new_structure):
        """Test Declaration Grooming Jefferson model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming Jefferson")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["handle_model"] == "Jefferson"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "jefferson(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_jeffington_model(self, handle_matcher_new_structure):
        """Test Declaration Grooming Jeffington model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming Jeffington")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["handle_model"] == "Jeffington"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "jeffington(?# PAD FOR PRIORITY LENGTH xxxxxxxxxxxx)"

    def test_declaration_grooming_unspecified_model(self, handle_matcher_new_structure):
        """Test Declaration Grooming Unspecified model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming handle")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["handle_model"] == "Unspecified"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] in ["^(?!.*dogwood)declaration", "^(?!.*dogwood)\\bdg\\b"]

    def test_jayaruh_unspecified_model(self, handle_matcher_new_structure):
        """Test Jayaruh Unspecified model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Jayaruh handle")
        assert result is not None
        assert result["handle_maker"] == "Jayaruh"
        assert result["handle_model"] == "Unspecified"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "jayaruh"

    def test_dogwood_handcrafts_unspecified_model(self, handle_matcher_new_structure):
        """Test Dogwood Handcrafts Unspecified model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Dogwood Handcrafts handle")
        assert result is not None
        assert result["handle_maker"] == "Dogwood Handcrafts"
        assert result["handle_model"] == "Unspecified"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "dogwood.*handcrafts+"

    def test_chisel_hound_unspecified_model(self, handle_matcher_new_structure):
        """Test Chisel & Hound Unspecified model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Chisel & Hound handle")
        assert result is not None
        assert result["handle_maker"] == "Chisel & Hound"
        assert result["handle_model"] == "Unspecified"
        assert result["_matched_by_section"] == "artisan_handles"
        assert result["_pattern_used"] == "chisel.*hound"

    def test_manufacturer_handles_unspecified_model(self, handle_matcher_new_structure):
        """Test manufacturer handles Unspecified model matching."""
        result = handle_matcher_new_structure.match_handle_maker("Simpson handle")
        assert result is not None
        assert result["handle_maker"] == "Simpson"
        assert result["handle_model"] == "Unspecified"
        assert result["_matched_by_section"] == "manufacturer_handles"
        assert result["_pattern_used"] == "simpson"

    def test_case_insensitive_model_matching(self, handle_matcher_new_structure):
        """Test that model matching is case insensitive."""
        test_cases = [
            ("DECLARATION GROOMING WASHINGTON", "Declaration Grooming", "Washington"),
            ("jayaruh", "Jayaruh", "Unspecified"),
            ("DOGWOOD HANDCRAFTS", "Dogwood Handcrafts", "Unspecified"),
        ]

        for text, expected_maker, expected_model in test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"

    def test_model_priority_specific_over_unspecified(self, handle_matcher_new_structure):
        """Test that specific models take precedence over Unspecified."""
        # Washington should match Washington model, not Unspecified
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming Washington")
        assert result["handle_model"] == "Washington"

        # General declaration should match Unspecified model
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming handle")
        assert result["handle_model"] == "Unspecified"

    def test_empty_input(self, handle_matcher_new_structure):
        """Test handle matching with empty input."""
        result = handle_matcher_new_structure.match_handle_maker("")
        assert result is None

    def test_no_match(self, handle_matcher_new_structure):
        """Test handle matching with text that doesn't match any patterns."""
        result = handle_matcher_new_structure.match_handle_maker("Unknown Brand Handle")
        assert result is None

    def test_resolve_handle_maker_with_model(self, handle_matcher_new_structure):
        """Test resolve_handle_maker method with new model structure."""
        # Test with full text
        updated = {}
        handle_matcher_new_structure.resolve_handle_maker(
            updated, "Declaration Grooming Washington"
        )
        assert updated["handle_maker"] == "Declaration Grooming"
        assert updated["handle_model"] == "Washington"

        # Test with brand field
        updated = {"brand": "Jayaruh"}
        handle_matcher_new_structure.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Jayaruh"
        assert updated["handle_model"] == "Unspecified"

        # Test with model field
        updated = {"model": "Declaration Grooming Jefferson"}
        handle_matcher_new_structure.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Declaration Grooming"
        assert updated["handle_model"] == "Jefferson"

    def test_all_existing_patterns_work_with_new_structure(self, handle_matcher_new_structure):
        """Test that all existing patterns work with new structure."""
        # Test a representative sample of patterns from each section

        # Artisan handles with models
        artisan_test_cases = [
            ("AKA Brushworx handle", "AKA Brushworx", "Unspecified"),
            ("Alpha handle", "Alpha", "Unspecified"),
            ("Brad Sears handle", "Brad Sears", "Unspecified"),
            ("Chisel & Hound handle", "Chisel & Hound", "Unspecified"),
            ("Declaration Grooming Washington", "Declaration Grooming", "Washington"),
            ("Dogwood Handcrafts handle", "Dogwood Handcrafts", "Unspecified"),
            ("Jayaruh handle", "Jayaruh", "Unspecified"),
        ]

        for text, expected_maker, expected_model in artisan_test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match artisan handle: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"
            assert result["_matched_by_section"] == "artisan_handles", f"Wrong section for: {text}"

        # Manufacturer handles
        manufacturer_test_cases = [
            ("Simpson handle", "Simpson", "Unspecified"),
            ("Omega handle", "Omega", "Unspecified"),
            ("Semogue handle", "Semogue", "Unspecified"),
            ("Muhle handle", "Muhle", "Unspecified"),
        ]

        for text, expected_maker, expected_model in manufacturer_test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match manufacturer handle: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"
            assert (
                result["_matched_by_section"] == "manufacturer_handles"
            ), f"Wrong section for: {text}"
