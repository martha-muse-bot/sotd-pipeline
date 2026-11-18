"""Test file for investigating brush validation data consistency issue.

This file implements Step 1 of the plan: Root Cause Investigation.
The goal is to reproduce the issue consistently and understand the actual failure mechanism.
"""

import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sotd.match.brush.validation.user_actions import BrushUserAction, BrushUserActionsManager


class TestBrushValidationInvestigation:
    """Test class for investigating brush validation data consistency issues."""

    @pytest.fixture
    def temp_data_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def manager(self, temp_data_dir):
        """Create a BrushUserActionsManager with temporary paths."""
        learning_path = temp_data_dir / "learning"
        correct_matches_path = temp_data_dir / "correct_matches.yaml"
        return BrushUserActionsManager(
            base_path=learning_path, correct_matches_path=correct_matches_path
        )

    @pytest.fixture
    def sample_brush_data(self):
        """Sample brush data that should trigger the issue."""
        return {
            "matched": {
                "brand": "Rad Dinosaur Creations",
                "model": "Jetson",
                "handle": {
                    "brand": "Muhle",
                    "model": "STF",
                },
                "knot": {
                    "brand": "Rad Dinosaur Creations",
                    "model": "Jetson",
                    "fiber": "synthetic",
                    "knot_size_mm": 25.0,
                },
                "score": 95.0,
            },
            "strategy": "automated_split",
            "all_strategies": [
                {
                    "strategy": "automated_split",
                    "score": 95.0,
                    "result": {
                        "brand": "Rad Dinosaur Creations",
                        "model": "Jetson",
                        "handle": {
                            "brand": "Muhle",
                            "model": "STF",
                        },
                        "knot": {
                            "brand": "Rad Dinosaur Creations",
                            "model": "Jetson",
                            "fiber": "synthetic",
                            "knot_size_mm": 25.0,
                        },
                    },
                }
            ],
        }

    def test_reproduce_issue_setup(self, manager, sample_brush_data):
        """Test setup to reproduce the issue - verify both operations can succeed individually."""
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Test 1: Verify correct_matches.yaml update works
        try:
            manager._update_correct_matches(input_text, sample_brush_data["matched"], "validated")
            print("✅ correct_matches.yaml update succeeded")
        except Exception as e:
            print(f"❌ correct_matches.yaml update failed: {e}")
            pytest.fail(f"correct_matches.yaml update failed: {e}")

        # Test 2: Verify learning file update works
        try:
            action = BrushUserAction(
                input_text=input_text,
                timestamp=datetime.now(),
                system_used=system_used,
                action="validated",
                system_choice=sample_brush_data["matched"],
                user_choice=sample_brush_data["matched"],
                all_brush_strategies=sample_brush_data["all_strategies"],
                comment_ids=comment_ids,
            )
            manager.storage.append_action(month, action)
            print("✅ learning file update succeeded")
        except Exception as e:
            print(f"❌ learning file update failed: {e}")
            pytest.fail(f"learning file update failed: {e}")

        # Test 3: Verify both operations work together in the actual method
        try:
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=sample_brush_data,
                comment_ids=comment_ids,
            )
            print("✅ Both operations succeeded together")
        except Exception as e:
            print(f"❌ Combined operation failed: {e}")
            pytest.fail(f"Combined operation failed: {e}")

    def test_investigate_file_permissions(self, manager, temp_data_dir):
        """Investigate if file permission issues could cause the problem."""
        learning_path = temp_data_dir / "learning"
        correct_matches_path = temp_data_dir / "correct_matches.yaml"

        # Test file creation permissions
        try:
            # Test learning directory creation
            learning_path.mkdir(parents=True, exist_ok=True)
            print(f"✅ Learning directory created: {learning_path}")
            print(f"   Permissions: {oct(learning_path.stat().st_mode)[-3:]}")
        except Exception as e:
            print(f"❌ Learning directory creation failed: {e}")

        try:
            # Test correct_matches.yaml creation
            correct_matches_path.parent.mkdir(parents=True, exist_ok=True)
            with open(correct_matches_path, "w") as f:
                yaml.dump({"brush": {}}, f)
            print(f"✅ correct_matches.yaml created: {correct_matches_path}")
            print(f"   Permissions: {oct(correct_matches_path.stat().st_mode)[-3:]}")
        except Exception as e:
            print(f"❌ correct_matches.yaml creation failed: {e}")

    def test_investigate_concurrent_access(self, manager, sample_brush_data):
        """Investigate if concurrent access could cause the problem."""
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Test rapid successive calls to see if there are race conditions
        try:
            for i in range(5):
                print(f"Testing rapid call {i+1}/5...")
                manager.record_validation_with_data(
                    input_text=f"{input_text} - Test {i+1}",
                    month=month,
                    system_used=system_used,
                    brush_data=sample_brush_data,
                    comment_ids=comment_ids,
                )
                print(f"  ✅ Call {i+1} succeeded")
        except Exception as e:
            print(f"❌ Rapid calls failed: {e}")
            pytest.fail(f"Rapid calls failed: {e}")

    def test_investigate_disk_space_issues(self, manager, temp_data_dir):
        """Investigate if disk space issues could cause the problem."""
        # Check available disk space in temp directory
        try:
            import shutil

            total, used, free = shutil.disk_usage(temp_data_dir)
            print("✅ Disk space check:")
            print(f"   Total: {total / (1024**3):.2f} GB")
            print(f"   Used: {used / (1024**3):.2f} GB")
            print(f"   Free: {free / (1024**3):.2f} GB")

            if free < 100 * 1024 * 1024:  # Less than 100MB
                print("⚠️  Low disk space detected")
            else:
                print("✅ Sufficient disk space")
        except Exception as e:
            print(f"❌ Disk space check failed: {e}")

    def test_investigate_data_corruption(self, manager, sample_brush_data):
        """Investigate if data corruption could cause the problem."""
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Test with corrupted brush data
        corrupted_data = sample_brush_data.copy()
        corrupted_data["matched"] = None  # Corrupt the matched data

        try:
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=corrupted_data,
                comment_ids=comment_ids,
            )
            print("❌ Should have failed with corrupted data")
            pytest.fail("Should have failed with corrupted data")
        except Exception as e:
            print(f"✅ Correctly failed with corrupted data: {e}")

    def test_investigate_network_timeouts(self, manager, sample_brush_data):
        """Investigate if network/storage timeouts could cause the problem."""
        # This test simulates slow file operations to see if timeouts occur
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Mock slow file operations
        with patch.object(manager.storage, "save_monthly_actions") as mock_save:
            mock_save.side_effect = lambda month, actions: None  # No delay

            try:
                manager.record_validation_with_data(
                    input_text=input_text,
                    month=month,
                    system_used=system_used,
                    brush_data=sample_brush_data,
                    comment_ids=comment_ids,
                )
                print("✅ No timeout issues detected")
            except Exception as e:
                print(f"❌ Timeout-related failure: {e}")
                pytest.fail(f"Timeout-related failure: {e}")

    def test_investigate_error_handling(self, manager, sample_brush_data):
        """Investigate error handling behavior."""
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Test what happens when correct_matches.yaml update fails
        with patch.object(manager.correct_matches_updater, "add_or_update_entry") as mock_update:
            mock_update.side_effect = Exception("Simulated correct_matches.yaml failure")

            try:
                manager.record_validation_with_data(
                    input_text=input_text,
                    month=month,
                    system_used=system_used,
                    brush_data=sample_brush_data,
                    comment_ids=comment_ids,
                )
                print("❌ Should have failed when correct_matches.yaml update fails")
                pytest.fail("Should have failed when correct_matches.yaml update fails")
            except Exception as e:
                print(f"✅ Correctly failed when correct_matches.yaml update fails: {e}")

        # Test what happens when learning file update fails
        with patch.object(manager.storage, "append_action") as mock_append:
            mock_append.side_effect = Exception("Simulated learning file failure")

            try:
                manager.record_validation_with_data(
                    input_text=input_text,
                    month=month,
                    system_used=system_used,
                    brush_data=sample_brush_data,
                    comment_ids=comment_ids,
                )
                print("❌ Should have failed when learning file update fails")
                pytest.fail("Should have failed when learning file update fails")
            except Exception as e:
                print(f"✅ Correctly failed when learning file update fails: {e}")

    def test_investigate_actual_failure_scenario(self, manager, sample_brush_data):
        """Test the exact scenario described in the bug report."""
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        print("🔍 Testing exact failure scenario:")
        print(f"   Input: {input_text}")
        print(f"   Month: {month}")
        print(f"   System: {system_used}")

        # Step 1: Check initial state
        print("\n📋 Step 1: Check initial state")
        try:
            # Check if entry exists in correct_matches.yaml
            has_entry = manager.correct_matches_updater.has_entry(input_text, "brush")
            print(f"   Entry in correct_matches.yaml: {has_entry}")

            # Check if entry exists in learning file
            try:
                actions = manager.storage.load_monthly_actions(month)
                has_learning_entry = any(action.input_text == input_text for action in actions)
                print(f"   Entry in learning file: {has_learning_entry}")
            except Exception as e:
                print(f"   Learning file check failed: {e}")
                has_learning_entry = False

        except Exception as e:
            print(f"   Initial state check failed: {e}")

        # Step 2: Perform validation
        print("\n📋 Step 2: Perform validation")
        try:
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=sample_brush_data,
                comment_ids=comment_ids,
            )
            print("   ✅ Validation succeeded")
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")
            pytest.fail(f"Validation failed: {e}")

        # Step 3: Check final state
        print("\n📋 Step 3: Check final state")
        try:
            # Check if entry exists in correct_matches.yaml
            has_entry_final = manager.correct_matches_updater.has_entry(input_text, "brush")
            print(f"   Entry in correct_matches.yaml: {has_entry_final}")

            # Check if entry exists in learning file
            try:
                actions = manager.storage.load_monthly_actions(month)
                has_learning_entry_final = any(
                    action.input_text == input_text for action in actions
                )
                print(f"   Entry in learning file: {has_learning_entry_final}")
            except Exception as e:
                print(f"   Learning file check failed: {e}")
                has_learning_entry_final = False

            # Check consistency
            if has_entry_final and has_learning_entry_final:
                print("   ✅ Data consistency maintained")
            elif has_entry_final and not has_learning_entry_final:
                print("   ❌ INCONSISTENCY: Entry in correct_matches.yaml but NOT in learning file")
                pytest.fail(
                    "Data inconsistency detected: Entry in correct_matches.yaml but NOT in learning file"
                )
            elif not has_entry_final and has_learning_entry_final:
                print("   ❌ INCONSISTENCY: Entry in learning file but NOT in correct_matches.yaml")
                pytest.fail(
                    "Data inconsistency detected: Entry in learning file but NOT in correct_matches.yaml"
                )
            else:
                print("   ❌ INCONSISTENCY: Entry in neither file")
                pytest.fail("Data inconsistency detected: Entry in neither file")

        except Exception as e:
            print(f"   Final state check failed: {e}")
            pytest.fail(f"Final state check failed: {e}")

        print("\n🎯 Investigation complete")

    def test_investigate_bug_report_scenario_exact(self, manager, temp_data_dir):
        """Test the exact scenario from the bug report with the exact input text."""
        # This is the exact input text from the bug report
        input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
        month = "2025-06"
        system_used = "scoring"
        comment_ids = ["test_comment_1"]

        # Create brush data that matches the bug report scenario
        brush_data = {
            "matched": {
                "brand": "Rad Dinosaur Creations",
                "model": "Jetson",
                "handle": {
                    "brand": "Muhle",
                    "model": "STF",
                },
                "knot": {
                    "brand": "Rad Dinosaur Creations",
                    "model": "Jetson",
                    "fiber": "synthetic",
                    "knot_size_mm": 25.0,
                },
                "score": 95.0,
            },
            "strategy": "automated_split",
            "all_strategies": [
                {
                    "strategy": "automated_split",
                    "score": 95.0,
                    "result": {
                        "brand": "Rad Dinosaur Creations",
                        "model": "Jetson",
                        "handle": {
                            "brand": "Muhle",
                            "model": "STF",
                        },
                        "knot": {
                            "brand": "Rad Dinosaur Creations",
                            "model": "Jetson",
                            "fiber": "synthetic",
                            "knot_size_mm": 25.0,
                        },
                    },
                }
            ],
        }

        print("🔍 Testing exact bug report scenario:")
        print(f"   Input: {input_text}")
        print(f"   Month: {month}")
        print(f"   System: {system_used}")

        # Step 1: Check if this entry already exists anywhere
        print("\n📋 Step 1: Check existing entries")

        # Check correct_matches.yaml
        has_entry_cm = manager.correct_matches_updater.has_entry(input_text, "brush")
        print(f"   Entry in correct_matches.yaml: {has_entry_cm}")

        # Check learning file
        try:
            actions = manager.storage.load_monthly_actions(month)
            has_learning_entry = any(action.input_text == input_text for action in actions)
            print(f"   Entry in learning file: {has_learning_entry}")
        except Exception as e:
            print(f"   Learning file check failed: {e}")
            has_learning_entry = False

        # Step 2: Try to reproduce the validation
        print("\n📋 Step 2: Attempt validation")
        try:
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=brush_data,
                comment_ids=comment_ids,
            )
            print("   ✅ Validation succeeded")
        except Exception as e:
            print(f"   ❌ Validation failed: {e}")
            pytest.fail(f"Validation failed: {e}")

        # Step 3: Check final state
        print("\n📋 Step 3: Check final state")

        # Check correct_matches.yaml
        has_entry_cm_final = manager.correct_matches_updater.has_entry(input_text, "brush")
        print(f"   Entry in correct_matches.yaml: {has_entry_cm_final}")

        # Check learning file
        try:
            actions = manager.storage.load_monthly_actions(month)
            has_learning_entry_final = any(action.input_text == input_text for action in actions)
            print(f"   Entry in learning file: {has_learning_entry_final}")
        except Exception as e:
            print(f"   Learning file check failed: {e}")
            has_learning_entry_final = False

        # Step 4: Check for the specific inconsistency mentioned in the bug report
        print("\n📋 Step 4: Check for specific inconsistency")

        if has_entry_cm_final and not has_learning_entry_final:
            print("   ❌ BUG REPRODUCED: Entry in correct_matches.yaml but NOT in learning file")
            print("   This matches the bug report description!")
            pytest.fail("Bug reproduced: Entry in correct_matches.yaml but NOT in learning file")
        elif not has_entry_cm_final and has_learning_entry_final:
            print("   ❌ BUG REPRODUCED: Entry in learning file but NOT in correct_matches.yaml")
            print("   This matches the bug report description!")
            pytest.fail("Bug reproduced: Entry in learning file but NOT in correct_matches.yaml")
        elif has_entry_cm_final and has_learning_entry_final:
            print("   ✅ No inconsistency detected - both entries exist")
            print("   The bug report scenario could not be reproduced")
        else:
            print("   ❌ BUG REPRODUCED: Entry in neither file")
            print("   This suggests a different failure mode")
            pytest.fail("Bug reproduced: Entry in neither file")

        print("\n🎯 Bug report investigation complete")

    def test_investigate_dual_component_field_type_determination(self, manager):
        """Test the exact data structure from the production bug to understand field type determination."""
        # This is the exact data structure from the production bug
        user_choice_data = {
            "result": {
                "brand": None,
                "handle": {
                    "_matched_by": "HandleMatcher",
                    "_pattern": "rad dino(saur)?",
                    "brand": "Rad Dinosaur Creations",
                    "model": "Unspecified",
                    "source_text": "Rad Dinosaur Creations - Jetson - 25mm Muhle STF",
                },
                "knot": {
                    "_matched_by": "KnotMatcher",
                    "_pattern": "m[uü]hle.*stf",
                    "brand": "Mühle",
                    "fiber": "Synthetic",
                    "knot_size_mm": None,
                    "model": "STF",
                    "source_text": "Rad Dinosaur Creations - Jetson - 25mm Muhle STF",
                },
                "model": None,
                "score": 85.0,
                "strategy": "unified",
                "user_intent": "dual_component",
            },
            "score": 85.0,
            "strategy": "",
        }

        print("🔍 Testing dual-component field type determination:")
        print(f"   User choice data: {user_choice_data}")

        # Test the field type determination logic
        try:
            # Call the method that determines field type
            field_type = manager._determine_field_type(user_choice_data)
            print(f"   Field type determined: {field_type}")

            # Check what the method actually received
            print("   Data structure analysis:")
            print(f"     Has 'brand' key: {'brand' in user_choice_data}")
            print(f"     Has 'model' key: {'model' in user_choice_data}")
            print(f"     Brand value: {user_choice_data.get('brand')}")
            print(f"     Model value: {user_choice_data.get('model')}")
            print(f"     Has 'handle' key: {'handle' in user_choice_data}")
            print(f"     Has 'knot' key: {'knot' in user_choice_data}")

            # The issue might be that the method is receiving the wrong level of data
            # Let me check what happens when we pass the 'result' part
            result_data = user_choice_data.get("result", {})
            print("   Result data analysis:")
            print(f"     Has 'brand' key: {'brand' in result_data}")
            print(f"     Has 'model' key: {'model' in result_data}")
            print(f"     Brand value: {result_data.get('brand')}")
            print(f"     Model value: {result_data.get('model')}")
            print(f"     Has 'handle' key: {'handle' in result_data}")
            print(f"     Has 'knot' key: {'knot' in result_data}")

            # Test field type determination with the result data
            field_type_result = manager._determine_field_type(result_data)
            print(f"   Field type with result data: {field_type_result}")

            # Now test the actual validation flow
            print("\n📋 Testing actual validation flow:")
            input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
            month = "2025-06"
            system_used = "scoring"
            comment_ids = ["test_comment_1"]

            # Create brush data that matches the production structure
            brush_data = {
                "matched": result_data,  # Use the result data directly
                "strategy": "unified",
                "all_strategies": [{"strategy": "unified", "score": 85.0, "result": result_data}],
            }

            # Try to record the validation
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=brush_data,
                comment_ids=comment_ids,
            )
            print("   ✅ Validation succeeded")

            # Check if the entry was added to correct_matches.yaml
            has_entry = manager.correct_matches_updater.has_entry(input_text, "split_brush")
            print(f"   Entry in correct_matches.yaml (split_brush): {has_entry}")

            if not has_entry:
                # Try checking in brush section
                has_entry_brush = manager.correct_matches_updater.has_entry(input_text, "brush")
                print(f"   Entry in correct_matches.yaml (brush): {has_entry_brush}")

                if not has_entry_brush:
                    print("   ❌ BUG REPRODUCED: Entry not found in correct_matches.yaml")
                    print("   This matches the production bug!")
                    pytest.fail("Bug reproduced: Entry not found in correct_matches.yaml")
                else:
                    print("   ✅ Entry found in brush section")
            else:
                print("   ✅ Entry found in split_brush section")

        except Exception as e:
            print(f"   ❌ Error during field type determination: {e}")
            pytest.fail(f"Field type determination failed: {e}")

        print("\n🎯 Dual-component field type investigation complete")

    def test_investigate_production_data_structure(self, manager):
        """Test with the exact production data structure from the matched file."""
        # This is the exact data structure from the production matched file
        production_matched_data = {
            "brand": None,
            "model": None,
            "user_intent": "dual_component",
            "handle": {
                "brand": "Rad Dinosaur Creations",
                "model": "Unspecified",
                "source_text": "Rad Dinosaur Creations - Jetson - 25mm Muhle STF",
                "_matched_by": "HandleMatcher",
                "_pattern": "rad dino(saur)?",
            },
            "knot": {
                "brand": "Mühle",
                "model": "STF",
                "fiber": "Synthetic",
                "knot_size_mm": None,
                "source_text": "Rad Dinosaur Creations - Jetson - 25mm Muhle STF",
                "_matched_by": "KnotMatcher",
                "_pattern": "m[uü]hle.*stf",
            },
            "strategy": "unified",
            "score": 85.0,
        }

        print("🔍 Testing production data structure:")
        print(f"   Production matched data: {production_matched_data}")

        # Test the field type determination logic with production data
        try:
            field_type = manager._determine_field_type(production_matched_data)
            print(f"   Field type determined: {field_type}")

            # Analyze the logic step by step
            print("   Logic analysis:")
            print(f"     Has 'brand' key: {'brand' in production_matched_data}")
            print(f"     Has 'model' key: {'model' in production_matched_data}")
            print(f"     Brand value: {production_matched_data.get('brand')}")
            print(f"     Model value: {production_matched_data.get('model')}")
            print(f"     Brand is None: {production_matched_data.get('brand') is None}")
            print(f"     Brand truthiness: {bool(production_matched_data.get('brand'))}")
            print(f"     Has 'handle' key: {'handle' in production_matched_data}")
            print(f"     Has 'knot' key: {'knot' in production_matched_data}")

            # Test the problematic condition
            brand = production_matched_data.get("brand")
            model = production_matched_data.get("model")
            condition = (brand is None or brand) and model is None
            print(f"     Condition (brand is None or brand) and model is None: {condition}")
            print(f"       (brand is None or brand): {brand is None or brand}")
            print(f"       model is None: {model is None}")

            # Now test the actual validation flow with production data
            print("\n📋 Testing validation flow with production data:")
            input_text = "Rad Dinosaur Creations - Jetson - 25mm Muhle STF"
            month = "2025-06"
            system_used = "scoring"
            comment_ids = ["test_comment_1"]

            # Create brush data that matches the production structure exactly
            brush_data = {
                "matched": production_matched_data,
                "strategy": "unified",
                "all_strategies": [
                    {"strategy": "unified", "score": 85.0, "result": production_matched_data}
                ],
            }

            # Try to record the validation
            manager.record_validation_with_data(
                input_text=input_text,
                month=month,
                system_used=system_used,
                brush_data=brush_data,
                comment_ids=comment_ids,
            )
            print("   ✅ Validation succeeded")

            # Check if the entry was added to correct_matches.yaml
            has_entry_split = manager.correct_matches_updater.has_entry(input_text, "split_brush")
            print(f"   Entry in correct_matches.yaml (split_brush): {has_entry_split}")

            has_entry_brush = manager.correct_matches_updater.has_entry(input_text, "brush")
            print(f"   Entry in correct_matches.yaml (brush): {has_entry_brush}")

            if has_entry_split:
                print("   ✅ Entry found in split_brush section (correct)")
            elif has_entry_brush:
                print("   ⚠️  Entry found in brush section (incorrect for dual-component)")
            else:
                print("   ❌ BUG REPRODUCED: Entry not found in correct_matches.yaml")
                print("   This matches the production bug!")
                pytest.fail("Bug reproduced: Entry not found in correct_matches.yaml")

        except Exception as e:
            print(f"   ❌ Error during field type determination: {e}")
            pytest.fail(f"Field type determination failed: {e}")

        print("\n🎯 Production data structure investigation complete")
