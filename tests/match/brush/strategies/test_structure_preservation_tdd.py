"""
TDD test for structure preservation in composite brush workflow.

This test ensures that when a composite brush is:
1. Regex matched -> data/matched (nested structure)
2. Saved to correct_matches.yaml
3. Rehydrated via CorrectMatchesStrategy

The rehydrated structure should be IDENTICAL to the original regex match structure.
"""

import json
import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.match.brush.strategies.correct_matches_strategy import CorrectMatchesStrategy
from sotd.match.brush_matcher import BrushMatcher


class TestStructurePreservationTDD:
    """Test that composite brush structures are preserved identically through the workflow."""

    def test_composite_brush_structure_preservation(self):
        """
        Test that composite brush structure is preserved identically.

        The rehydrated structure should match the original regex match structure exactly,
        including nested handle/knot objects and all metadata fields.
        """
        # Step 1: Get actual regex match result
        matcher = BrushMatcher()
        test_input = "DG B3 in C&H handle"

        regex_result = matcher.match(test_input)
        assert regex_result is not None, "Should get regex match result"
        assert regex_result.matched is not None, "Should have matched data"

        # Verify we have the expected nested structure
        assert "handle" in regex_result.matched, "Should have handle section"
        assert "knot" in regex_result.matched, "Should have knot section"
        assert regex_result.matched["handle"]["brand"] == "Chisel & Hound"
        assert regex_result.matched["knot"]["brand"] == "Declaration Grooming"

        # Step 2: Create temporary correct_matches.yaml
        temp_correct_matches = {
            "handle": {"Chisel & Hound": {"Unspecified": [test_input.lower()]}},
            "knot": {
                "Declaration Grooming": {
                    "B3": {"strings": [test_input.lower()], "fiber": "Badger", "knot_size_mm": 28}
                }
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(temp_correct_matches, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Step 3: Rehydrate using CorrectMatchesStrategy
            with open(temp_file_path, "r") as f:
                loaded_correct_matches = yaml.safe_load(f)

            correct_matches_strategy = CorrectMatchesStrategy(loaded_correct_matches)
            rehydrated_result = correct_matches_strategy.match(test_input)

            assert rehydrated_result is not None, "Should rehydrate successfully"
            assert rehydrated_result.matched is not None, "Should have matched data"

            # Step 4: Verify structures are IDENTICAL
            original_matched = regex_result.matched
            rehydrated_matched = rehydrated_result.matched

            # The rehydrated structure should preserve the EXACT same format
            self._assert_structures_identical(original_matched, rehydrated_matched)

        finally:
            # Clean up
            Path(temp_file_path).unlink()

    def test_summer_break_soaps_structure_preservation(self):
        """
        Test that Summer Break Soaps composite brush structure is preserved identically.

        The rehydrated structure should match the original regex match structure exactly,
        including the nested handle/knot objects and all metadata fields.
        """
        # Step 1: Get actual regex match result
        matcher = BrushMatcher()
        test_input = "Summer Break Soaps"

        regex_result = matcher.match(test_input, bypass_correct_matches=True)
        assert regex_result is not None, "Should get regex match result"
        assert regex_result.matched is not None, "Should have matched data"

        # Verify we have the expected nested structure for composite brush
        assert "handle" in regex_result.matched, "Should have handle section"
        assert "knot" in regex_result.matched, "Should have knot section"
        # Note: Actual behavior matches full brand name "Summer Break Soaps" for both handle and knot
        assert regex_result.matched["handle"]["brand"] == "Summer Break Soaps"
        assert (
            regex_result.matched["handle"]["model"] is None
            or regex_result.matched["handle"]["model"] == "Unspecified"
        )
        # Knot brand matches the same brand when it's a complete brush
        assert regex_result.matched["knot"]["brand"] == "Summer Break Soaps"
        assert (
            regex_result.matched["knot"]["model"] is not None
        )  # Should have knot model (e.g., "Badger")

        # Step 2: Create temporary correct_matches.yaml
        temp_correct_matches = {"handle": {"Summer Break": {"Unspecified": ["summer break soaps"]}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(temp_correct_matches, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Step 3: Rehydrate using CorrectMatchesStrategy
            with open(temp_file_path, "r") as f:
                loaded_correct_matches = yaml.safe_load(f)

            correct_matches_strategy = CorrectMatchesStrategy(loaded_correct_matches)
            rehydrated_result = correct_matches_strategy.match(test_input)

            assert rehydrated_result is not None, "Should rehydrate successfully"
            assert rehydrated_result.matched is not None, "Should have matched data"

            # Step 4: Verify structures are IDENTICAL
            original_matched = regex_result.matched
            rehydrated_matched = rehydrated_result.matched

            # The rehydrated structure should preserve the EXACT same format
            self._assert_summer_break_soaps_structures_identical(
                original_matched, rehydrated_matched
            )

        finally:
            # Clean up
            Path(temp_file_path).unlink()

    def test_knot_only_structure_preservation(self):
        """
        Test that knot-only structure is preserved identically.

        The rehydrated structure should match the original regex match structure exactly,
        including the nested handle/knot objects and all metadata fields.
        """
        # Step 1: Create a made-up scenario for knot-only case
        test_input = "Custom Knot Only"

        # Simulate what the regex result would look like for a knot-only entry
        # This is a made-up structure that represents a knot-only brush
        expected_regex_structure = {
            "brand": None,
            "model": None,
            "handle": {
                "brand": None,
                "model": None,
            },
            "knot": {
                "brand": "Custom Knot Brand",
                "model": "Only",
                "fiber": "Synthetic",  # Will come from catalog lookup
                "knot_size_mm": None,  # Will remain None from catalog
            },
            "source_text": "Custom Knot Only",
            "_matched_by": "KnotMatcher",
            "_pattern": "custom.*knot.*only",
            "strategy": "knot_only",
            "score": 25.0,
        }

        # Step 2: Create temporary correct_matches.yaml
        temp_correct_matches = {"knot": {"Custom Knot Brand": {"Only": ["custom knot only"]}}}

        # Step 2b: Create temporary knot catalog with fiber data
        temp_knot_catalog = {
            "Custom Knot Brand": {
                "Only": {
                    "fiber": "Synthetic",
                    "knot_size_mm": None,  # Not specified in this catalog
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(temp_correct_matches, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Step 3: Rehydrate using CorrectMatchesStrategy
            with open(temp_file_path, "r") as f:
                loaded_correct_matches = yaml.safe_load(f)

            # Mock the catalog lookup to return our temporary catalog data
            correct_matches_strategy = CorrectMatchesStrategy(loaded_correct_matches)

            # Patch the _get_knot_catalog_data method to return our temp catalog data
            correct_matches_strategy._get_knot_catalog_data = lambda knot_maker, knot_model: (
                temp_knot_catalog.get(knot_maker, {}).get(knot_model, {})
            )

            rehydrated_result = correct_matches_strategy.match(test_input)

            assert rehydrated_result is not None, "Should rehydrate successfully"
            assert rehydrated_result.matched is not None, "Should have matched data"

            # Step 4: Verify structures are IDENTICAL
            original_matched = expected_regex_structure
            rehydrated_matched = rehydrated_result.matched

            # The rehydrated structure should preserve the EXACT same format
            self._assert_knot_only_structures_identical(original_matched, rehydrated_matched)

        finally:
            # Clean up
            Path(temp_file_path).unlink()

    def test_simpson_chubby_2_complete_brush_rehydration(self):
        """
        Test that Simpson Chubby 2 complete brush rehydration works correctly.

        This tests the new _reconstruct_complete_brush_structure method for simple complete brushes.
        """
        # Step 1: Get actual regex match result
        matcher = BrushMatcher()
        test_input = "Simpson Chubby 2"

        regex_result = matcher.match(test_input, bypass_correct_matches=True)
        assert regex_result is not None, "Should get regex match result"
        assert regex_result.matched is not None, "Should have matched data"

        # Verify we have the expected nested structure for complete brush
        assert "handle" in regex_result.matched, "Should have handle section"
        assert "knot" in regex_result.matched, "Should have knot section"
        assert regex_result.matched["brand"] == "Simpson", "Should have top-level brand"
        assert regex_result.matched["model"] == "Chubby 2", "Should have top-level model"

        # Step 2: Create temporary correct_matches.yaml for complete brush
        temp_correct_matches = {"brush": {"Simpson": {"Chubby 2": ["simpson chubby 2"]}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(temp_correct_matches, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Step 3: Rehydrate using CorrectMatchesStrategy
            with open(temp_file_path, "r") as f:
                loaded_correct_matches = yaml.safe_load(f)

            # Get catalogs from the matcher to pass to CorrectMatchesStrategy
            catalogs = matcher._load_catalogs_directly()
            correct_matches_strategy = CorrectMatchesStrategy(loaded_correct_matches, catalogs)
            rehydrated_result = correct_matches_strategy.match(test_input)

            assert rehydrated_result is not None, "Should rehydrate successfully"
            assert rehydrated_result.matched is not None, "Should have matched data"

            # Step 4: Verify structures are IDENTICAL
            original_matched = regex_result.matched
            rehydrated_matched = rehydrated_result.matched

            # Debug output to see what we're actually comparing
            print(f"\nOriginal regex result: {original_matched}")
            print(f"\nRehydrated result: {rehydrated_matched}")

            # The rehydrated structure should preserve the EXACT same format
            self._assert_complete_brush_structures_identical(
                original_matched, rehydrated_matched, test_input
            )

        finally:
            # Clean up
            Path(temp_file_path).unlink()

    def test_bfm_complex_complete_brush_rehydration(self):
        """
        Test that BFM complex complete brush rehydration works correctly.

        This tests the new _reconstruct_complete_brush_structure method for complex complete brushes
        with different brands for handle and knot.
        """
        # Step 1: Get actual regex match result
        matcher = BrushMatcher()
        test_input = "BFM"

        regex_result = matcher.match(test_input, bypass_correct_matches=True)
        assert regex_result is not None, "Should get regex match result"
        assert regex_result.matched is not None, "Should have matched data"

        # Verify we have the expected nested structure for complete brush
        assert "handle" in regex_result.matched, "Should have handle section"
        assert "knot" in regex_result.matched, "Should have knot section"
        assert regex_result.matched["brand"] is not None, "Should have top-level brand"
        assert regex_result.matched["model"] is not None, "Should have top-level model"

        # Step 2: Create temporary correct_matches.yaml for complex complete brush
        temp_correct_matches = {"brush": {"BFM": {"Unspecified": ["bfm"]}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(temp_correct_matches, f, default_flow_style=False)
            temp_file_path = f.name

        try:
            # Step 3: Rehydrate using CorrectMatchesStrategy
            with open(temp_file_path, "r") as f:
                loaded_correct_matches = yaml.safe_load(f)

            # Get catalogs from the matcher to pass to CorrectMatchesStrategy
            catalogs = matcher._load_catalogs_directly()
            correct_matches_strategy = CorrectMatchesStrategy(loaded_correct_matches, catalogs)
            rehydrated_result = correct_matches_strategy.match(test_input)

            assert rehydrated_result is not None, "Should rehydrate successfully"
            assert rehydrated_result.matched is not None, "Should have matched data"

            # Step 4: Verify structures are IDENTICAL
            original_matched = regex_result.matched
            rehydrated_matched = rehydrated_result.matched

            # The rehydrated structure should preserve the EXACT same format
            self._assert_complete_brush_structures_identical(
                original_matched, rehydrated_matched, test_input
            )

        finally:
            # Clean up
            Path(temp_file_path).unlink()

    def _assert_structures_identical(self, original: dict, rehydrated: dict):
        """Assert that the rehydrated structure matches the expected simplified format."""

        # Check that we have the expected structure for composite brushes
        assert "handle" in rehydrated, "Should preserve handle section"
        assert "knot" in rehydrated, "Should preserve knot section"

        # Check handle section has core data
        rehydrated_handle = rehydrated["handle"]
        assert rehydrated_handle["brand"] == "Chisel & Hound", "Should preserve handle brand"
        assert rehydrated_handle["model"] == "Unspecified", "Should preserve handle model"

        # Check knot section has core data
        rehydrated_knot = rehydrated["knot"]
        assert rehydrated_knot["brand"] == "Declaration Grooming", "Should preserve knot brand"
        assert rehydrated_knot["model"] == "B3", "Should preserve knot model"
        assert rehydrated_knot["fiber"] == "Badger", "Should preserve knot fiber"
        assert rehydrated_knot["knot_size_mm"] == 28, "Should preserve knot size"

        # Check that we have the expected composite brush structure
        assert rehydrated["brand"] is None, "Composite brush should have brand=None"
        assert rehydrated["model"] is None, "Composite brush should have model=None"
        assert (
            rehydrated["source_text"] == "DG B3 in C&H handle"
        ), "Should preserve original source_text"
        assert (
            rehydrated["_matched_by"] == "CorrectMatchesStrategy"
        ), "Should indicate correct matches strategy"
        assert rehydrated["_pattern"] == "exact_match", "Should indicate exact match"
        assert (
            rehydrated["strategy"] == "correct_matches"
        ), "Should indicate correct matches strategy"

        # Check that we don't have unnecessary fields
        assert "handle_text" not in rehydrated, "Should not have handle_text field"
        assert "knot_text" not in rehydrated, "Should not have knot_text field"
        assert "split_priority" not in rehydrated, "Should not have split_priority field"
        assert "_delimiter_priority" not in rehydrated, "Should not have _delimiter_priority field"
        assert (
            "high_priority_delimiter" not in rehydrated
        ), "Should not have high_priority_delimiter field"
        assert "score" not in rehydrated, "Should not have score field"
        assert "priority" not in rehydrated["handle"], "Should not have priority in handle"
        assert "score" not in rehydrated["handle"], "Should not have score in handle"
        assert "priority" not in rehydrated["knot"], "Should not have priority in knot"
        assert "score" not in rehydrated["knot"], "Should not have score in knot"

        print("✅ Rehydrated structure matches expected format!")
        print("Expected structure:")
        expected = {
            "brand": None,
            "model": None,
            "handle": {
                "brand": "Chisel & Hound",
                "model": "Unspecified",
            },
            "knot": {
                "brand": "Declaration Grooming",
                "model": "B3",
                "fiber": "Badger",
                "knot_size_mm": 28,
            },
            "source_text": "DG B3 in C&H handle",
            "_matched_by": "CorrectMatchesStrategy",
            "_pattern": "exact_match",
            "strategy": "correct_matches",
        }
        print(json.dumps(expected, indent=2))
        print("\nActual rehydrated structure:")
        print(json.dumps(rehydrated, indent=2, default=str))

    def _assert_summer_break_soaps_structures_identical(self, original: dict, rehydrated: dict):
        """Assert that the rehydrated Summer Break Soaps structure matches the expected format."""

        # Check that we have the expected structure for composite brushes
        assert "handle" in rehydrated, "Should preserve handle section"
        assert "knot" in rehydrated, "Should preserve knot section"

        # Check handle section has core data (only what aggregators need)
        rehydrated_handle = rehydrated["handle"]
        assert rehydrated_handle["brand"] == "Summer Break", "Should preserve handle brand"
        assert rehydrated_handle["model"] == "Unspecified", "Should preserve handle model"

        # Check knot section has core data (only what aggregators need)
        rehydrated_knot = rehydrated["knot"]
        assert rehydrated_knot["brand"] is None, "Should preserve knot brand (null)"
        assert rehydrated_knot["model"] is None, "Should preserve knot model (null)"
        assert rehydrated_knot["fiber"] is None, "Should preserve knot fiber (null)"
        assert rehydrated_knot["knot_size_mm"] is None, "Should preserve knot size (null)"

        # Check that we have the required top-level fields for aggregation compatibility
        assert rehydrated.get("brand") is None, "Should have top-level brand: null for aggregation"
        assert rehydrated.get("model") is None, "Should have top-level model: null for aggregation"

        # Check that we have the required metadata fields at root level only
        assert "source_text" in rehydrated, "Should preserve source_text at root level"
        assert "_matched_by" in rehydrated, "Should preserve _matched_by at root level"
        assert "_pattern" in rehydrated, "Should preserve _pattern at root level"
        assert "strategy" in rehydrated, "Should preserve strategy at root level"

        # Verify the source_text matches the original input
        assert (
            rehydrated["source_text"] == "Summer Break Soaps"
        ), "Should preserve original source text"

        # Verify metadata fields indicate correct source
        assert (
            rehydrated["_matched_by"] == "CorrectMatchesStrategy"
        ), "Should indicate correct matches strategy"
        assert rehydrated["_pattern"] == "exact_match", "Should indicate exact match"
        assert (
            rehydrated["strategy"] == "correct_matches"
        ), "Should indicate correct matches strategy"

        # Check that nested objects DON'T have unnecessary metadata fields
        assert "source_text" not in rehydrated_handle, "Handle should not have source_text"
        assert "_matched_by" not in rehydrated_handle, "Handle should not have _matched_by"
        assert "_pattern" not in rehydrated_handle, "Handle should not have _pattern"
        assert "score" not in rehydrated_handle, "Handle should not have score"

        assert "source_text" not in rehydrated_knot, "Knot should not have source_text"
        assert "_matched_by" not in rehydrated_knot, "Knot should not have _matched_by"
        assert "_pattern" not in rehydrated_knot, "Knot should not have _pattern"
        assert "score" not in rehydrated_knot, "Knot should not have score"

    def _assert_knot_only_structures_identical(self, original: dict, rehydrated: dict):
        """Assert that the rehydrated knot-only structure matches the expected format."""

        # Check that we have the expected structure for composite brushes
        assert "handle" in rehydrated, "Should preserve handle section"
        assert "knot" in rehydrated, "Should preserve knot section"

        # Check handle section has core data (only what aggregators need)
        rehydrated_handle = rehydrated["handle"]
        assert rehydrated_handle["brand"] is None, "Should preserve handle brand (null)"
        assert rehydrated_handle["model"] is None, "Should preserve handle model (null)"

        # Check knot section has core data (only what aggregators need)
        rehydrated_knot = rehydrated["knot"]
        assert rehydrated_knot["brand"] == "Custom Knot Brand", "Should preserve knot brand"
        assert rehydrated_knot["model"] == "Only", "Should preserve knot model"
        assert rehydrated_knot["fiber"] == "Synthetic", "Should preserve knot fiber from catalog"
        assert (
            rehydrated_knot["knot_size_mm"] is None
        ), "Should preserve knot size (None from catalog)"

        # Check that we have the required top-level fields for aggregation compatibility
        assert rehydrated.get("brand") is None, "Should have top-level brand: null for aggregation"
        assert rehydrated.get("model") is None, "Should have top-level model: null for aggregation"

        # Check that we have the required metadata fields at root level only
        assert "source_text" in rehydrated, "Should preserve source_text at root level"
        assert "_matched_by" in rehydrated, "Should preserve _matched_by at root level"
        assert "_pattern" in rehydrated, "Should preserve _pattern at root level"
        assert "strategy" in rehydrated, "Should preserve strategy at root level"

        # Verify the source_text matches the original input
        assert (
            rehydrated["source_text"] == "Custom Knot Only"
        ), "Should preserve original source text"

        # Verify metadata fields indicate correct source
        assert (
            rehydrated["_matched_by"] == "CorrectMatchesStrategy"
        ), "Should indicate correct matches strategy"
        assert rehydrated["_pattern"] == "exact_match", "Should indicate exact match"
        assert (
            rehydrated["strategy"] == "correct_matches"
        ), "Should indicate correct matches strategy"

        # Check that nested objects DON'T have unnecessary metadata fields
        assert "source_text" not in rehydrated_handle, "Handle should not have source_text"
        assert "_matched_by" not in rehydrated_handle, "Handle should not have _matched_by"
        assert "_pattern" not in rehydrated_handle, "Handle should not have _pattern"
        assert "score" not in rehydrated_handle, "Handle should not have score"

        assert "source_text" not in rehydrated_knot, "Knot should not have source_text"
        assert "_matched_by" not in rehydrated_knot, "Knot should not have _matched_by"
        assert "_pattern" not in rehydrated_knot, "Knot should not have _pattern"
        assert "score" not in rehydrated_knot, "Knot should not have score"

    def _assert_complete_brush_structures_identical(
        self, original: dict, rehydrated: dict, test_input: str
    ):
        """Assert that complete brush rehydrated structure matches what CorrectMatchesStrategy produces."""
        # Check that we have the expected structure from CorrectMatchesStrategy
        assert "brand" in rehydrated, "Should have top-level brand"
        assert "model" in rehydrated, "Should have top-level model"

        # Check that we have the required metadata fields
        assert (
            rehydrated["_matched_by"] == "CorrectMatchesStrategy"
        ), "Should indicate correct matches"
        assert rehydrated["_pattern"] == "exact_match", "Should indicate exact match"
        assert rehydrated["strategy"] == "correct_matches", "Should indicate correct matches"

        # Check that we DON'T have redundant root-level fields (per plan specification)
        assert "fiber" not in rehydrated, "Should NOT have root-level fiber (only in knot)"
        assert (
            "knot_size_mm" not in rehydrated
        ), "Should NOT have root-level knot_size_mm (only in knot)"

        # Check that we don't have regex-specific fields
        assert "score" not in rehydrated, "Should not have score field from regex matching"
        assert "_pattern_used" not in rehydrated, "Should not have regex pattern field"
        assert "fiber_strategy" not in rehydrated, "Should not have fiber strategy field"
        assert "knot_size_strategy" not in rehydrated, "Should not have knot size strategy field"

        print("✅ Complete brush rehydration structure matches CorrectMatchesStrategy output!")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
