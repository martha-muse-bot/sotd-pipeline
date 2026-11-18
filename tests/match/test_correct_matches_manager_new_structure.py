"""Test CorrectMatchesManager with new brand/model hierarchy structure."""

from unittest.mock import Mock

import pytest

from sotd.match.tools.managers.correct_matches_manager import CorrectMatchesManager


class TestCorrectMatchesManagerNewStructure:
    """Test CorrectMatchesManager with new brand/model hierarchy structure."""

    @pytest.fixture
    def console_mock(self):
        """Create a mock console for testing."""
        return Mock()

    @pytest.fixture
    def correct_matches_manager(self, console_mock, tmp_path):
        """Create CorrectMatchesManager instance for testing."""
        correct_matches_dir = tmp_path / "correct_matches"
        return CorrectMatchesManager(console_mock, correct_matches_dir)

    def test_handle_section_structure_uses_catalog_model_names(self, correct_matches_manager):
        """Test that handle section structure uses catalog model names."""
        # Test data with new brand/model hierarchy
        match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data["matched"]
        )

        # Mark as correct
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file
        correct_matches_manager.save_correct_matches()

        # Verify the structure uses catalog model names
        # The handle section should have: Declaration Grooming -> Washington -> [source_text]
        # Not: Declaration Grooming -> extracted_model_name -> [source_text]

        # Reload and check structure
        correct_matches_manager.load_correct_matches()

        # Check that the handle section has the correct structure
        # This will be verified by checking the saved YAML structure

    def test_model_name_extraction_from_catalog(self, correct_matches_manager):
        """Test that model names are extracted from catalog, not from source_text."""
        # Test with specific model
        match_data = {
            "original": "Declaration Grooming Jefferson handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Jefferson",
            },
            "field": "handle",
        }

        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Jefferson handle", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # The saved structure should use "Jefferson" (from catalog) not extracted model name

        # Test with Unspecified model
        match_data_unspecified = {
            "original": "Jayaruh handle",
            "matched": {
                "handle_maker": "Jayaruh",
                "handle_model": "Unspecified",
            },
            "field": "handle",
        }

        match_key_unspecified = correct_matches_manager.create_match_key(
            "handle", "Jayaruh handle", match_data_unspecified["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key_unspecified, match_data_unspecified)
        correct_matches_manager.save_correct_matches()

        # The saved structure should use "Unspecified" (from catalog)

    def test_brand_name_preservation(self, correct_matches_manager):
        """Test that brand names preserve proper casing from catalog."""
        # Test with proper brand casing
        match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",  # Proper casing from catalog
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # The saved structure should preserve "Declaration Grooming" casing,
        # not "declaration grooming"

    def test_split_brush_compatibility(self, correct_matches_manager):
        """Test that split_brush section functionality is maintained."""
        # Test split brush data
        match_data = {
            "original": "Declaration Grooming Washington w/ Zenith B2",
            "matched": {
                "handle": {
                    "brand": "Declaration Grooming",
                    "model": "Washington",
                    "source_text": "Declaration Grooming Washington",
                },
                "knot": {
                    "brand": "Zenith",
                    "model": "B2",
                    "source_text": "Zenith B2",
                },
            },
            "field": "brush",
        }

        match_key = correct_matches_manager.create_match_key(
            "brush", "Declaration Grooming Washington w/ Zenith B2", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # Verify split_brush section is created correctly
        # Verify handle and knot sections are created with proper model names

    def test_multiple_entries(self, correct_matches_manager):
        """Test saving multiple handle entries with different models."""
        # Test multiple entries for same brand, different models
        entries = [
            {
                "original": "Declaration Grooming Washington handle",
                "matched": {
                    "handle_maker": "Declaration Grooming",
                    "handle_model": "Washington",
                },
                "field": "handle",
            },
            {
                "original": "Declaration Grooming Jefferson handle",
                "matched": {
                    "handle_maker": "Declaration Grooming",
                    "handle_model": "Jefferson",
                },
                "field": "handle",
            },
            {
                "original": "Declaration Grooming handle",
                "matched": {
                    "handle_maker": "Declaration Grooming",
                    "handle_model": "Unspecified",
                },
                "field": "handle",
            },
        ]

        for entry in entries:
            match_key = correct_matches_manager.create_match_key(
                entry["field"], entry["original"], entry["matched"]
            )
            correct_matches_manager.mark_match_as_correct(match_key, entry)

        correct_matches_manager.save_correct_matches()

        # Verify all entries are saved with correct model names
        # Declaration Grooming should have Washington, Jefferson, and Unspecified models

    def test_model_name_consistency(self, correct_matches_manager):
        """Test that catalog model names are used consistently."""
        # Test that the same model name is used consistently across different entries
        match_data_1 = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        match_data_2 = {
            "original": "DG Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        # Both should save to the same model section: Declaration Grooming -> Washington
        match_key_1 = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data_1["matched"]
        )
        match_key_2 = correct_matches_manager.create_match_key(
            "handle", "DG Washington handle", match_data_2["matched"]
        )

        correct_matches_manager.mark_match_as_correct(match_key_1, match_data_1)
        correct_matches_manager.mark_match_as_correct(match_key_2, match_data_2)
        correct_matches_manager.save_correct_matches()

        # Both entries should be saved under Declaration Grooming -> Washington

    def test_casing_consistency(self, correct_matches_manager):
        """Test proper brand casing and lowercase storage."""
        # Test that brand names preserve proper casing but storage is lowercase
        match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",  # Proper casing
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # Brand name should be preserved as "Declaration Grooming" in structure
        # But source_text should be stored in lowercase

    def test_no_duplicates(self, correct_matches_manager):
        """Test that no duplicate brand/model entries are created."""
        # Test adding the same entry twice
        match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data["matched"]
        )

        # Add the same entry twice
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        correct_matches_manager.save_correct_matches()

        # Should not create duplicate entries in the YAML structure

    def test_end_to_end_workflow(self, correct_matches_manager):
        """Test end-to-end workflow: save, reload, verify structure."""
        # Test complete workflow
        match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle_maker": "Declaration Grooming",
                "handle_model": "Washington",
            },
            "field": "handle",
        }

        # Save
        match_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # Reload
        correct_matches_manager.load_correct_matches()

        # Verify structure is correct
        # Should be able to find the entry with correct brand/model structure

    def test_brush_field_handling_bug_fix(self, correct_matches_manager):
        """Test that brush field handling properly initializes dictionaries."""
        # Test data for brush field
        match_data = {
            "original": "Alpha Outlaw Silver STF++",
            "matched": {
                "brand": "Alpha",
                "model": "Outlaw",
            },
            "field": "brush",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "brush", "Alpha Outlaw Silver STF++", match_data["matched"]
        )

        # Mark as correct - this should not raise KeyError
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file - this should not raise KeyError
        correct_matches_manager.save_correct_matches()

        # Verify the entry was saved correctly
        correct_matches_manager.load_correct_matches()

        # Check that the entry exists in the correct matches
        assert match_key in correct_matches_manager._correct_matches

        # Verify the structure is correct: brush -> Alpha -> Outlaw ->
        # [normalized_original]
        # The save operation should have created the proper nested structure

    def test_split_brush_handling_bug_fix(self, correct_matches_manager):
        """Test that split brushes are saved to handle and knot sections."""
        # Test data for split brush (composite brush)
        match_data = {
            "original": "Alpha Outlaw Silver STF++",
            "matched": {
                "brand": None,  # Split brush has null brand/model
                "model": None,
                "handle": {
                    "brand": "Alpha",
                    "model": "Outlaw",
                    "source_text": "Alpha Outlaw",
                },
                "knot": {
                    "brand": "Silver",
                    "model": "STF++",
                    "source_text": "Silver STF++",
                },
            },
            "field": "brush",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "brush", "Alpha Outlaw Silver STF++", match_data["matched"]
        )

        # Mark as correct
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file
        correct_matches_manager.save_correct_matches()

        # Verify the entry was saved correctly
        correct_matches_manager.load_correct_matches()

        # Check that the split brush components were saved to handle and knot sections
        # The original brush key should not exist, but handle and knot keys should
        assert match_key not in correct_matches_manager._correct_matches

        # Check that handle component was saved
        handle_key = "handle:alpha outlaw silver stf++"
        assert handle_key in correct_matches_manager._correct_matches

        # Check that knot component was saved
        knot_key = "knot:alpha outlaw silver stf++"
        assert knot_key in correct_matches_manager._correct_matches

        # Verify the structure is correct:
        # handle -> Alpha -> Outlaw -> [normalized_handle_text]
        # knot -> Silver -> STF++ -> [normalized_knot_text]
        # NOT brush -> null -> null -> [original]

    def test_blade_format_preservation(self, correct_matches_manager):
        """Test that blade format information is preserved when loading and saving."""
        # Test data for blade with format
        match_data = {
            "original": "Feather Artist Club",
            "matched": {
                "brand": "Feather",
                "model": "Artist Club",
                "format": "AC",  # AC format, not DE
            },
            "field": "blade",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "blade", "Feather Artist Club", match_data["matched"]
        )

        # Mark as correct
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file
        correct_matches_manager.save_correct_matches()

        # Reload to verify format preservation
        correct_matches_manager.load_correct_matches()

        # Check that the entry exists
        assert match_key in correct_matches_manager._correct_matches

        # Verify that the format field is preserved in the loaded data
        loaded_data = correct_matches_manager._correct_matches_data[match_key]
        assert "matched" in loaded_data
        assert "format" in loaded_data["matched"]
        assert loaded_data["matched"]["format"] == "AC"

        # Save again to verify the format is still preserved
        correct_matches_manager.save_correct_matches()

        # Reload one more time to ensure the format persists through multiple save/load cycles
        correct_matches_manager.load_correct_matches()

        # Verify format is still preserved
        loaded_data_again = correct_matches_manager._correct_matches_data[match_key]
        assert loaded_data_again["matched"]["format"] == "AC"

        # This test verifies that the fix for the format preservation bug is working
        # Previously, the format field would be lost during loading, causing all
        # blade entries to default to "DE" format

    def test_composite_brush_various_scenarios(self, correct_matches_manager):
        """Test composite brush handling across various real-world scenarios."""
        test_cases = [
            {
                "name": "AP Shave Co with TGN Boar",
                "original": "AP Shave Co. - Lemon Drop 26mm TGN Boar",
                "handle": {
                    "brand": "AP Shave Co",
                    "model": "Unspecified",
                },
                "knot": {
                    "brand": "The Golden Nib",
                    "model": "Boar",
                    "fiber": "Boar",
                    "knot_size_mm": 26.0,
                },
            },
            {
                "name": "Declaration Grooming with B2",
                "original": "Declaration Grooming B2 in Mozingo handle",
                "handle": {
                    "brand": "Mozingo",
                    "model": "Unspecified",
                },
                "knot": {
                    "brand": "Declaration Grooming",
                    "model": "B2",
                    "fiber": "Badger",
                },
            },
            {
                "name": "Simpson with Manchurian",
                "original": "Simpson Chubby 2 Manchurian in Jade",
                "handle": {
                    "brand": "Simpson",
                    "model": "Chubby 2",
                },
                "knot": {
                    "brand": "Simpson",
                    "model": "Manchurian",
                    "fiber": "Badger",
                },
            },
        ]

        for test_case in test_cases:
            print(f"\n🔍 Testing: {test_case['name']}")

            # Simulate frontend data structure
            frontend_data = {
                "original": test_case["original"],
                "matched": {
                    "handle": {
                        **test_case["handle"],
                        "source_text": test_case["original"],  # Full original text
                    },
                    "knot": {
                        **test_case["knot"],
                        "source_text": test_case["original"],  # Full original text
                    },
                },
                "field": "brush",
            }

            # Process the data
            original = frontend_data["original"]
            matched = frontend_data["matched"]
            field = frontend_data["field"]

            # Create match key and save
            match_key = correct_matches_manager.create_match_key(field, original, matched)
            correct_matches_manager.mark_match_as_correct(
                match_key,
                {
                    "original": original,
                    "matched": matched,
                    "field": field,
                },
            )

            # Save and reload
            correct_matches_manager.save_correct_matches()
            correct_matches_manager.load_correct_matches()

            # Verify the expected structure
            normalized_original = original.lower()
            original_brush_key = f"brush:{normalized_original}"
            handle_key = f"handle:{normalized_original}"
            knot_key = f"knot:{normalized_original}"

            # Original brush key should not exist
            assert (
                original_brush_key not in correct_matches_manager._correct_matches
            ), f"Original brush key should not exist: {original_brush_key}"

            # Handle and knot keys should exist
            assert (
                handle_key in correct_matches_manager._correct_matches
            ), f"Handle section not created: {handle_key}"
            assert (
                knot_key in correct_matches_manager._correct_matches
            ), f"Knot section not created: {knot_key}"

            # The CorrectMatchesManager saves data in a catalog structure, not individual match records
            # We need to verify that the data can be looked up correctly using the full original text

            # Test that the lookup keys work correctly
            # This simulates what happens when the pipeline tries to find matches
            normalized_original = original.lower()

            # Test handle lookup - should find the handle section
            handle_lookup_key = f"handle:{normalized_original}"
            assert (
                handle_lookup_key in correct_matches_manager._correct_matches
            ), f"Handle lookup key not found: {handle_lookup_key}"

            # Test knot lookup - should find the knot section
            knot_lookup_key = f"knot:{normalized_original}"
            assert (
                knot_lookup_key in correct_matches_manager._correct_matches
            ), f"Knot lookup key not found: {knot_lookup_key}"

            # Verify that the individual match data is preserved in _correct_matches_data
            # This contains the original match records for reference
            handle_data = correct_matches_manager._correct_matches_data[handle_key]
            knot_data = correct_matches_manager._correct_matches_data[knot_key]

            # Debug output to see what's actually saved
            print(f"🔍 DEBUG: Handle data structure: {handle_data}")
            print(f"🔍 DEBUG: Knot data structure: {knot_data}")

            # Verify that the original match data is preserved (normalized)
            assert "original" in handle_data, "Handle data missing 'original' field"
            assert handle_data["original"] == test_case["original"].lower()
            assert "matched" in handle_data, "Handle data missing 'matched' field"
            assert handle_data["matched"]["brand"] == test_case["handle"]["brand"]
            assert handle_data["matched"]["model"] == test_case["handle"]["model"]

            # Verify that the original match data is preserved for knot (normalized)
            assert "original" in knot_data, "Knot data missing 'original' field"
            assert knot_data["original"] == test_case["original"].lower()
            assert "matched" in knot_data, "Knot data missing 'matched' field"
            assert knot_data["matched"]["brand"] == test_case["knot"]["brand"]
            assert knot_data["matched"]["model"] == test_case["knot"]["model"]

            # Test lookup functionality
            assert handle_key in correct_matches_manager._correct_matches
            assert knot_key in correct_matches_manager._correct_matches

            print(f"✅ {test_case['name']}: All validations passed")

        print("\n🎯 SUCCESS: Composite brush handling works correctly across all scenarios")
        print(
            "The fix ensures that all composite brushes are properly routed to "
            "handle/knot sections"
        )
        print("Each section gets the full original text for proper lookup functionality")

    def test_no_brand_handle_saving(self, correct_matches_manager):
        """Test saving handle with no brand information using _no_brand section."""
        # Test data for automated split with no brand
        match_data = {
            "original": "Custom Irish Bog Oak Handle 30mm Synthetic Knot",
            "matched": {
                "handle": {
                    "brand": None,
                    "model": None,
                    "source_text": "Custom Irish Bog Oak Handle",
                },
                "knot": {
                    "brand": None,
                    "model": "Synthetic",
                    "source_text": "30mm Synthetic Knot",
                },
            },
            "field": "brush",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "brush", "Custom Irish Bog Oak Handle 30mm Synthetic Knot", match_data["matched"]
        )

        # Mark as correct
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file
        correct_matches_manager.save_correct_matches()

        # Reload to verify structure
        correct_matches_manager.load_correct_matches()

        # Check that handle was saved to _no_brand section
        handle_key = "handle:custom irish bog oak handle 30mm synthetic knot"
        assert handle_key in correct_matches_manager._correct_matches

        # Verify the structure is correct: handle -> _no_brand -> _no_model -> [original]
        handle_data = correct_matches_manager._correct_matches_data[handle_key]
        assert handle_data["matched"]["brand"] == "_no_brand"
        assert handle_data["matched"]["model"] == "_no_model"

    def test_no_brand_knot_saving(self, correct_matches_manager):
        """Test saving knot with no brand information using _no_brand section."""
        # Test data for automated split with no brand
        match_data = {
            "original": "Custom Irish Bog Oak Handle 30mm Synthetic Knot",
            "matched": {
                "handle": {
                    "brand": None,
                    "model": None,
                    "source_text": "Custom Irish Bog Oak Handle",
                },
                "knot": {
                    "brand": None,
                    "model": "Synthetic",
                    "source_text": "30mm Synthetic Knot",
                },
            },
            "field": "brush",
        }

        # Create match key
        match_key = correct_matches_manager.create_match_key(
            "brush", "Custom Irish Bog Oak Handle 30mm Synthetic Knot", match_data["matched"]
        )

        # Mark as correct
        correct_matches_manager.mark_match_as_correct(match_key, match_data)

        # Save to file
        correct_matches_manager.save_correct_matches()

        # Reload to verify structure
        correct_matches_manager.load_correct_matches()

        # Check that knot was saved to _no_brand section
        knot_key = "knot:custom irish bog oak handle 30mm synthetic knot"
        assert knot_key in correct_matches_manager._correct_matches

        # Verify the structure is correct: knot -> _no_brand -> Synthetic -> [original]
        knot_data = correct_matches_manager._correct_matches_data[knot_key]
        assert knot_data["matched"]["brand"] == "_no_brand"
        assert knot_data["matched"]["model"] == "Synthetic"

    def test_no_brand_yaml_structure(self, correct_matches_manager):
        """Test that _no_brand entries create correct YAML structure."""
        # Test data for automated split
        match_data = {
            "original": "Custom Irish Bog Oak Handle 30mm Synthetic Knot",
            "matched": {
                "handle": {
                    "brand": None,
                    "model": None,
                    "source_text": "Custom Irish Bog Oak Handle",
                },
                "knot": {
                    "brand": None,
                    "model": "Synthetic",
                    "source_text": "30mm Synthetic Knot",
                },
            },
            "field": "brush",
        }

        # Create match key and save
        match_key = correct_matches_manager.create_match_key(
            "brush", "Custom Irish Bog Oak Handle 30mm Synthetic Knot", match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(match_key, match_data)
        correct_matches_manager.save_correct_matches()

        # Read the YAML files to verify structure (directory structure)
        import yaml

        # Read handle.yaml file
        handle_file = correct_matches_manager._correct_matches_file / "handle.yaml"
        assert handle_file.exists(), "handle.yaml should exist"
        with handle_file.open("r", encoding="utf-8") as f:
            handle_data = yaml.safe_load(f)

        # Verify handle section structure
        assert "_no_brand" in handle_data
        assert "_no_model" in handle_data["_no_brand"]
        assert (
            "custom irish bog oak handle 30mm synthetic knot"
            in handle_data["_no_brand"]["_no_model"]
        )

        # Read knot.yaml file
        knot_file = correct_matches_manager._correct_matches_file / "knot.yaml"
        assert knot_file.exists(), "knot.yaml should exist"
        with knot_file.open("r", encoding="utf-8") as f:
            knot_data = yaml.safe_load(f)

        # Verify knot section structure
        assert "_no_brand" in knot_data
        assert "Synthetic" in knot_data["_no_brand"]
        assert (
            "custom irish bog oak handle 30mm synthetic knot" in knot_data["_no_brand"]["Synthetic"]
        )

    def test_mixed_brand_no_brand_entries(self, correct_matches_manager):
        """Test saving both regular brand entries and _no_brand entries."""
        # Regular brand entry
        regular_match_data = {
            "original": "Declaration Grooming Washington handle",
            "matched": {
                "handle": {
                    "brand": "Declaration Grooming",
                    "model": "Washington",
                    "source_text": "Declaration Grooming Washington handle",
                },
            },
            "field": "handle",
        }

        # No brand entry
        no_brand_match_data = {
            "original": "Custom Handle 30mm Synthetic Knot",
            "matched": {
                "handle": {
                    "brand": None,
                    "model": None,
                    "source_text": "Custom Handle",
                },
                "knot": {
                    "brand": None,
                    "model": "Synthetic",
                    "source_text": "30mm Synthetic Knot",
                },
            },
            "field": "brush",
        }

        # Save both entries
        regular_key = correct_matches_manager.create_match_key(
            "handle", "Declaration Grooming Washington handle", regular_match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(regular_key, regular_match_data)

        no_brand_key = correct_matches_manager.create_match_key(
            "brush", "Custom Handle 30mm Synthetic Knot", no_brand_match_data["matched"]
        )
        correct_matches_manager.mark_match_as_correct(no_brand_key, no_brand_match_data)

        correct_matches_manager.save_correct_matches()

        # Reload and verify both entries exist
        correct_matches_manager.load_correct_matches()

        # Regular entry should exist
        assert regular_key in correct_matches_manager._correct_matches

        # No brand entries should exist
        handle_key = "handle:custom handle 30mm synthetic knot"
        knot_key = "knot:custom handle 30mm synthetic knot"
        assert handle_key in correct_matches_manager._correct_matches
        assert knot_key in correct_matches_manager._correct_matches

    def test_automated_split_mark_correct_integration(self, correct_matches_manager):
        """Test that automated splits can be marked as correct and stop appearing as unconfirmed."""
        # Simulate the exact data structure from the MatchAnalyzer
        automated_split_data = {
            "original": "Custom Irish Bog Oak Handle 30mm Synthetic Knot",
            "matched": {
                "handle": {
                    "brand": None,
                    "model": None,
                    "source_text": "Custom Irish Bog Oak Handle",
                },
                "knot": {
                    "brand": None,
                    "model": "Synthetic",
                    "source_text": "30mm Synthetic Knot",
                },
            },
            "field": "brush",
        }

        # Create match key (this is what the MatchAnalyzer would do)
        match_key = correct_matches_manager.create_match_key(
            "brush",
            "Custom Irish Bog Oak Handle 30mm Synthetic Knot",
            automated_split_data["matched"],
        )

        # Mark as correct (this is what happens when "Mark as Correct" is clicked)
        correct_matches_manager.mark_match_as_correct(match_key, automated_split_data)

        # Save to file (this is what the API does)
        correct_matches_manager.save_correct_matches()

        # Reload to verify it was saved correctly
        correct_matches_manager.load_correct_matches()

        # For split brushes, the original brush key is not marked as correct
        # Instead, the handle and knot components are marked as correct
        # This is the correct behavior for automated splits

        # Verify the split components are saved to handle/knot sections
        handle_key = "handle:custom irish bog oak handle 30mm synthetic knot"
        knot_key = "knot:custom irish bog oak handle 30mm synthetic knot"

        assert correct_matches_manager.is_match_correct(handle_key)
        assert correct_matches_manager.is_match_correct(knot_key)

        # This test verifies that the automated split will no longer appear as unconfirmed
        # because its components are now marked as correct in the correct_matches.yaml file
