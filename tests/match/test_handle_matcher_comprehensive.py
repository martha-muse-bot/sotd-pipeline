"""Comprehensive tests for handle matcher with new brand/model hierarchy structure."""

from pathlib import Path

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher


class TestHandleMatcherComprehensive:
    """Comprehensive tests for handle matcher with new structure."""

    @pytest.fixture
    def handle_matcher_new_structure(self):
        """Create handle matcher instance with new structure."""
        return HandleMatcher(Path("data/handles_new_structure.yaml"))

    def test_complex_pattern_matching(self, handle_matcher_new_structure):
        """Test complex pattern matching with multi-word brands and regex patterns."""
        # Test complex regex patterns
        test_cases = [
            ("Declaration Grooming Washington handle", "Declaration Grooming", "Washington"),
            ("DG Washington", "Declaration Grooming", "Washington"),
            ("Dogwood Handcrafts handle", "Dogwood Handcrafts", "Unspecified"),
            ("DW handle", "Dogwood Handcrafts", "Unspecified"),
            ("Chisel & Hound handle", "Chisel & Hound", "Unspecified"),
            ("C&H handle", "Chisel & Hound", "Unspecified"),
        ]

        for text, expected_maker, expected_model in test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"

    def test_model_priority_specific_over_unspecified(self, handle_matcher_new_structure):
        """Test that specific models take precedence over Unspecified models."""
        # Test that specific models are matched correctly
        specific_test_cases = [
            ("Declaration Grooming Washington", "Washington"),
            ("Declaration Grooming Jefferson", "Jefferson"),
            ("Declaration Grooming Jeffington", "Jeffington"),
        ]

        for text, expected_model in specific_test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"
            assert result["handle_maker"] == "Declaration Grooming", f"Wrong maker for: {text}"

        # Test that general patterns match Unspecified model
        general_test_cases = [
            ("Declaration Grooming handle", "Unspecified"),
            ("DG handle", "Unspecified"),
        ]

        for text, expected_model in general_test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"
            assert result["handle_maker"] == "Declaration Grooming", f"Wrong maker for: {text}"

    def test_pattern_conflicts_resolution(self, handle_matcher_new_structure):
        """Test that pattern conflicts are resolved correctly."""
        # Test that longer patterns take precedence (due to padding)
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming Washington")
        assert result["handle_model"] == "Washington"
        assert "PAD FOR PRIORITY LENGTH" in result["_pattern_used"]

        # Test that general patterns work when specific models don't match
        result = handle_matcher_new_structure.match_handle_maker("Declaration Grooming general")
        assert result["handle_model"] == "Unspecified"

    def test_performance_with_large_dataset(self, handle_matcher_new_structure):
        """Test performance with a large number of handle matching operations."""
        import time

        # Test data with various handle types
        test_texts = [
            "Declaration Grooming Washington",
            "Declaration Grooming Jefferson",
            "Declaration Grooming Jeffington",
            "Declaration Grooming handle",
            "Jayaruh handle",
            "Dogwood Handcrafts handle",
            "Chisel & Hound handle",
            "Simpson handle",
            "Omega handle",
            "Semogue handle",
        ] * 100  # Repeat 100 times for performance testing

        start_time = time.time()

        for text in test_texts:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert "handle_maker" in result
            assert "handle_model" in result

        end_time = time.time()
        elapsed_time = end_time - start_time

        # Should complete in reasonable time (less than 1 second for 1000 operations)
        assert elapsed_time < 1.0, f"Performance test took too long: {elapsed_time:.3f} seconds"

    def test_error_handling_invalid_yaml_structure(self):
        """Test error handling with invalid YAML structure."""
        # Test with non-existent file
        handle_matcher = HandleMatcher(Path("non_existent_file.yaml"))
        result = handle_matcher.match_handle_maker("test")
        assert result is None

        # Test with empty file
        empty_file = Path("empty_handles.yaml")
        try:
            empty_file.write_text("")
            handle_matcher = HandleMatcher(empty_file)
            result = handle_matcher.match_handle_maker("test")
            assert result is None
        finally:
            if empty_file.exists():
                empty_file.unlink()

    def test_edge_cases(self, handle_matcher_new_structure):
        """Test edge cases and boundary conditions."""
        # Test empty input
        result = handle_matcher_new_structure.match_handle_maker("")
        assert result is None

        # Test whitespace-only input
        result = handle_matcher_new_structure.match_handle_maker("   ")
        assert result is None

        # Test very long input
        long_text = "Declaration Grooming Washington " + "x" * 1000
        result = handle_matcher_new_structure.match_handle_maker(long_text)
        assert result is not None
        assert result["handle_model"] == "Washington"

        # Test input with special characters
        special_text = "Declaration Grooming Washington!@#$%^&*()"
        result = handle_matcher_new_structure.match_handle_maker(special_text)
        assert result is not None
        assert result["handle_model"] == "Washington"

    def test_case_insensitive_matching_comprehensive(self, handle_matcher_new_structure):
        """Test comprehensive case insensitive matching."""
        test_cases = [
            ("DECLARATION GROOMING WASHINGTON", "Declaration Grooming", "Washington"),
            ("declaration grooming washington", "Declaration Grooming", "Washington"),
            ("Declaration Grooming WASHINGTON", "Declaration Grooming", "Washington"),
            ("DECLARATION GROOMING jefferson", "Declaration Grooming", "Jefferson"),
            ("jayaruh", "Jayaruh", "Unspecified"),
            ("JAYARUH", "Jayaruh", "Unspecified"),
            ("Dogwood Handcrafts", "Dogwood Handcrafts", "Unspecified"),
            ("DOGWOOD HANDCRAFTS", "Dogwood Handcrafts", "Unspecified"),
        ]

        for text, expected_maker, expected_model in test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"

    def test_all_existing_patterns_preserved(self, handle_matcher_new_structure):
        """Test that all existing patterns from the old structure are preserved."""
        # Test a comprehensive set of patterns from the old structure
        comprehensive_test_cases = [
            # Artisan handles
            ("AKA Brushworx handle", "AKA Brushworx", "Unspecified"),
            ("Alpha handle", "Alpha", "Unspecified"),
            ("Brad Sears handle", "Brad Sears", "Unspecified"),
            ("Chisel & Hound handle", "Chisel & Hound", "Unspecified"),
            ("Declaration Grooming Washington", "Declaration Grooming", "Washington"),
            ("Declaration Grooming Jefferson", "Declaration Grooming", "Jefferson"),
            ("Declaration Grooming Jeffington", "Declaration Grooming", "Jeffington"),
            ("Declaration Grooming handle", "Declaration Grooming", "Unspecified"),
            ("Dogwood Handcrafts handle", "Dogwood Handcrafts", "Unspecified"),
            ("Jayaruh handle", "Jayaruh", "Unspecified"),
            ("Mozingo handle", "Mozingo", "Unspecified"),
            ("Wald handle", "Wald", "Unspecified"),
            # Manufacturer handles
            ("Simpson handle", "Simpson", "Unspecified"),
            ("Omega handle", "Omega", "Unspecified"),
            ("Semogue handle", "Semogue", "Unspecified"),
            ("Muhle handle", "Muhle", "Unspecified"),
            ("RazoRock handle", "Razorock", "Unspecified"),
            ("PAA handle", "PAA", "Unspecified"),
            ("Yaqi handle", "Yaqi", "Unspecified"),
            ("Zenith handle", "Zenith", "Unspecified"),
        ]

        for text, expected_maker, expected_model in comprehensive_test_cases:
            result = handle_matcher_new_structure.match_handle_maker(text)
            assert result is not None, f"Failed to match: {text}"
            assert result["handle_maker"] == expected_maker, f"Wrong maker for: {text}"
            assert result["handle_model"] == expected_model, f"Wrong model for: {text}"

    def test_handle_matcher_backward_compatibility(self):
        """Test that handle matcher works with the new YAML structure."""
        # Test with new structure (should have handle_model field)
        handle_matcher = HandleMatcher(Path("data/handles.yaml"))
        result = handle_matcher.match_handle_maker("Declaration Grooming Washington")
        assert result is not None
        assert result["handle_maker"] == "Declaration Grooming"
        assert result["handle_model"] == "Washington"  # New structure uses specific model

    def test_resolve_handle_maker_comprehensive(self, handle_matcher_new_structure):
        """Test resolve_handle_maker method comprehensively."""
        # Test with full text containing specific model
        updated = {}
        handle_matcher_new_structure.resolve_handle_maker(
            updated, "Declaration Grooming Washington"
        )
        assert updated["handle_maker"] == "Declaration Grooming"
        assert updated["handle_model"] == "Washington"

        # Test with brand field only
        updated = {"brand": "Jayaruh"}
        handle_matcher_new_structure.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Jayaruh"
        assert updated["handle_model"] == "Unspecified"

        # Test with model field containing specific model
        updated = {"model": "Declaration Grooming Jefferson"}
        handle_matcher_new_structure.resolve_handle_maker(updated, "some text")
        assert updated["handle_maker"] == "Declaration Grooming"
        assert updated["handle_model"] == "Jefferson"

        # Test that existing handle_maker is not overridden
        updated = {"handle_maker": "Existing Maker"}
        handle_matcher_new_structure.resolve_handle_maker(
            updated, "Declaration Grooming Washington"
        )
        assert updated["handle_maker"] == "Existing Maker"
        assert "handle_model" not in updated  # Should not be set if handle_maker already exists
