"""Test brush user actions data model."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from sotd.match.brush.validation.user_actions import (
    BrushUserAction,
    BrushUserActionsManager,
    BrushUserActionsStorage,
    ValidationError,
)


class TestBrushUserAction:
    """Test BrushUserAction data model."""

    def test_create_valid_action(self):
        """Test creating a valid brush user action."""
        action = BrushUserAction(
            input_text="Chisel & Hound 'The Duke' / Omega 10098 Boar",
            timestamp=datetime.now(),
            system_used="scoring",
            action="validated",
            system_choice={
                "strategy": "dual_component",
                "score": 85,
                "result": {"brand": "Chisel & Hound", "model": "The Duke"},
            },
            user_choice={
                "strategy": "dual_component",
                "result": {"brand": "Chisel & Hound", "model": "The Duke"},
            },
            all_brush_strategies=[
                {"strategy": "complete_brush", "score": 45, "result": {}},
                {"strategy": "dual_component", "score": 85, "result": {"brand": "Chisel & Hound"}},
                {"strategy": "single_component", "score": 30, "result": {}},
            ],
            comment_ids=["comment1", "comment2"],
        )

        assert action.input_text == "Chisel & Hound 'The Duke' / Omega 10098 Boar"
        assert action.system_used == "scoring"
        assert action.action == "validated"
        assert action.system_choice["strategy"] == "dual_component"
        assert action.system_choice["score"] == 85
        assert action.user_choice["strategy"] == "dual_component"
        assert len(action.all_brush_strategies) == 3

    def test_create_action_with_legacy_system(self):
        """Test creating action with legacy system identification."""
        action = BrushUserAction(
            input_text="Summer Break Soaps Maize 26mm Timberwolf",
            timestamp=datetime.now(),
            system_used="legacy",
            action="overridden",
            system_choice={
                "strategy": "dual_component",
                "score": None,  # Legacy system doesn't have scores
                "result": {"brand": "Summer Break", "model": "Maize"},
            },
            user_choice={
                "strategy": "complete_brush",
                "result": {"brand": "Summer Break Soaps", "model": "Maize"},
            },
            all_brush_strategies=[],  # Legacy system doesn't track all strategies
            comment_ids=["comment3"],
        )

        assert action.system_used == "legacy"
        assert action.action == "overridden"
        assert action.system_choice["score"] is None
        assert action.all_brush_strategies == []

    def test_invalid_system_used(self):
        """Test validation of system_used field."""
        with pytest.raises(
            ValidationError, match="system_used must be either 'scoring', 'legacy', or 'migrated'"
        ):
            BrushUserAction(
                input_text="Test brush",
                timestamp=datetime.now(),
                system_used="invalid_system",
                action="validated",
                system_choice={"strategy": "test", "score": 50, "result": {}},
                user_choice={"strategy": "test", "result": {}},
                all_brush_strategies=[],
                comment_ids=["comment4"],
            )

    def test_invalid_action_type(self):
        """Test validation of action field."""
        with pytest.raises(
            ValidationError, match="action must be either 'validated' or 'overridden'"
        ):
            BrushUserAction(
                input_text="Test brush",
                timestamp=datetime.now(),
                system_used="scoring",
                action="invalid_action",
                system_choice={"strategy": "test", "score": 50, "result": {}},
                user_choice={"strategy": "test", "result": {}},
                all_brush_strategies=[],
                comment_ids=["comment5"],
            )

    def test_to_dict(self):
        """Test conversion to dictionary format."""
        timestamp = datetime(2025, 8, 6, 14, 30, 0)
        action = BrushUserAction(
            input_text="Test Brush",
            timestamp=timestamp,
            system_used="scoring",
            action="validated",
            system_choice={"strategy": "test", "score": 50, "result": {}},
            user_choice={"strategy": "test", "result": {}},
            all_brush_strategies=[],
            comment_ids=["comment7"],
        )

        result = action.to_dict()
        assert result["input_text"] == "Test Brush"
        assert result["timestamp"] == "2025-08-06T14:30:00Z"
        assert result["system_used"] == "scoring"
        assert result["action"] == "validated"

    def test_from_dict(self):
        """Test creation from dictionary format."""
        data = {
            "input_text": "Test Brush",
            "timestamp": "2025-08-06T14:30:00Z",
            "system_used": "scoring",
            "action": "validated",
            "system_choice": {"strategy": "test", "score": 50, "result": {}},
            "user_choice": {"strategy": "test", "result": {}},
            "all_brush_strategies": [],
        }

        action = BrushUserAction.from_dict(data)
        assert action.input_text == "Test Brush"
        assert action.timestamp == datetime(2025, 8, 6, 14, 30, 0)
        assert action.system_used == "scoring"
        assert action.action == "validated"


class TestBrushUserActionsStorage:
    """Test BrushUserActionsStorage for monthly file operations."""

    def setup_method(self):
        """Set up test directory."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.learning_dir = self.test_dir / "learning"
        self.learning_dir.mkdir()
        # Create brush_user_actions subdirectory
        self.brush_user_actions_dir = self.learning_dir / "brush_user_actions"
        self.brush_user_actions_dir.mkdir()

        self.storage = BrushUserActionsStorage(self.learning_dir)

    def teardown_method(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)

    def test_save_and_load_monthly_actions(self):
        """Test saving and loading monthly brush user actions."""
        actions = [
            BrushUserAction(
                input_text="Test Brush 1",
                timestamp=datetime(2025, 8, 6, 14, 30, 0),
                system_used="scoring",
                action="validated",
                system_choice={"strategy": "test", "score": 50, "result": {}},
                user_choice={"strategy": "test", "result": {}},
                all_brush_strategies=[],
                comment_ids=["comment8"],
            ),
            BrushUserAction(
                input_text="Test Brush 2",
                timestamp=datetime(2025, 8, 6, 15, 30, 0),
                system_used="legacy",
                action="overridden",
                system_choice={"strategy": "test", "score": None, "result": {}},
                user_choice={"strategy": "other", "result": {}},
                all_brush_strategies=[],
                comment_ids=["comment9"],
            ),
        ]

        # Save actions for August 2025
        self.storage.save_monthly_actions("2025-08", actions)

        # Verify file was created
        file_path = self.brush_user_actions_dir / "2025-08.yaml"
        assert file_path.exists()

        # Load and verify
        loaded_actions = self.storage.load_monthly_actions("2025-08")
        assert len(loaded_actions) == 2
        assert loaded_actions[0].input_text == "Test Brush 1"
        assert loaded_actions[1].input_text == "Test Brush 2"
        assert loaded_actions[0].system_used == "scoring"
        assert loaded_actions[1].system_used == "legacy"

    def test_load_nonexistent_file(self):
        """Test loading actions from nonexistent file."""
        actions = self.storage.load_monthly_actions("2025-12")
        assert actions == []

    def test_append_action(self):
        """Test appending single action to monthly file."""
        # Create initial action
        action1 = BrushUserAction(
            input_text="Test Brush 1",
            timestamp=datetime(2025, 8, 6, 14, 30, 0),
            system_used="scoring",
            action="validated",
            system_choice={"strategy": "test", "score": 50, "result": {}},
            user_choice={"strategy": "test", "result": {}},
            all_brush_strategies=[],
            comment_ids=["comment10"],
        )

        # Save initial action
        self.storage.save_monthly_actions("2025-08", [action1])

        # Append second action
        action2 = BrushUserAction(
            input_text="Test Brush 2",
            timestamp=datetime(2025, 8, 6, 15, 30, 0),
            system_used="legacy",
            action="overridden",
            system_choice={"strategy": "test", "score": None, "result": {}},
            user_choice={"strategy": "other", "result": {}},
            all_brush_strategies=[],
            comment_ids=["comment11"],
        )

        self.storage.append_action("2025-08", action2)

        # Verify both actions are present
        loaded_actions = self.storage.load_monthly_actions("2025-08")
        assert len(loaded_actions) == 2
        assert loaded_actions[0].input_text == "Test Brush 1"
        assert loaded_actions[1].input_text == "Test Brush 2"

    def test_get_file_path(self):
        """Test file path generation."""
        path = self.storage._get_file_path("2025-08")
        expected = self.brush_user_actions_dir / "2025-08.yaml"
        assert path == expected

    def test_invalid_month_format(self):
        """Test validation of month format."""
        with pytest.raises(ValidationError, match="Invalid month format"):
            self.storage.save_monthly_actions("2025-8", [])  # Should be 2025-08

        with pytest.raises(ValidationError, match="Invalid month format"):
            self.storage.load_monthly_actions("25-08")  # Should be 2025-08


class TestBrushUserActionsManager:
    """Test BrushUserActionsManager for high-level operations."""

    def setup_method(self):
        """Set up test environment."""
        self.test_dir = Path(tempfile.mkdtemp())
        self.learning_dir = self.test_dir / "learning"
        self.learning_dir.mkdir()
        # Create brush_user_actions subdirectory
        self.brush_user_actions_dir = self.learning_dir / "brush_user_actions"
        self.brush_user_actions_dir.mkdir()

        # Create a temporary correct_matches directory for testing
        self.correct_matches_path = self.test_dir / "correct_matches"

        self.manager = BrushUserActionsManager(
            base_path=self.learning_dir, correct_matches_path=self.correct_matches_path
        )

    def teardown_method(self):
        """Clean up test directory."""
        shutil.rmtree(self.test_dir)

    def test_record_validation(self):
        """Test recording a validation action."""
        system_choice = {
            "strategy": "dual_component",
            "score": 85,
            "result": {"brand": "Test Brand", "model": "Test Model"},
        }
        user_choice = {
            "strategy": "dual_component",
            "result": {"brand": "Test Brand", "model": "Test Model"},
        }
        all_strategies = [
            {
                "strategy": "complete_brush",
                "score": 45,
                "result": {"brand": "Test Brand", "model": "Test Model"},
            },
            {
                "strategy": "dual_component",
                "score": 85,
                "result": {"brand": "Test Brand", "model": "Test Model"},
            },
        ]

        self.manager.record_validation(
            input_text="Test Brush",
            month="2025-08",
            system_used="scoring",
            system_choice=system_choice,
            user_choice=user_choice,
            all_brush_strategies=all_strategies,
            comment_ids=["comment14"],
        )

        # Verify action was recorded
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "Test Brush"
        assert actions[0].action == "validated"
        assert actions[0].system_used == "scoring"

    def test_record_override(self):
        """Test recording an override action."""
        system_choice = {
            "strategy": "complete_brush",
            "score": 60,
            "result": {"brand": "Test Brand", "model": "Test Model"},
        }
        user_choice = {
            "strategy": "dual_component",
            "result": {"brand": "Test Brand", "model": "Test Model"},
        }
        all_strategies = []

        self.manager.record_override(
            input_text="Test Brush",
            month="2025-08",
            system_used="scoring",
            system_choice=system_choice,
            user_choice=user_choice,
            all_brush_strategies=all_strategies,
            comment_ids=["comment15"],
        )

        # Verify action was recorded
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "Test Brush"
        assert actions[0].action == "overridden"

    def test_get_all_actions(self):
        """Test getting actions across multiple months."""
        # Create actions with specific timestamps to ensure ordering
        action1 = BrushUserAction(
            input_text="Test Brush 1",
            timestamp=datetime(2025, 7, 1, 12, 0, 0),
            system_used="scoring",
            action="validated",
            system_choice={
                "strategy": "test",
                "score": 50,
                "result": {"brand": "Test Brand 1", "model": "Test Model 1"},
            },
            user_choice={
                "strategy": "test",
                "result": {"brand": "Test Brand 1", "model": "Test Model 1"},
            },
            all_brush_strategies=[],
            comment_ids=["comment12"],
        )

        action2 = BrushUserAction(
            input_text="Test Brush 2",
            timestamp=datetime(2025, 8, 1, 12, 0, 0),
            system_used="legacy",
            action="validated",
            system_choice={
                "strategy": "test",
                "score": None,
                "result": {"brand": "Test Brand 2", "model": "Test Model 2"},
            },
            user_choice={
                "strategy": "test",
                "result": {"brand": "Test Brand 2", "model": "Test Model 2"},
            },
            all_brush_strategies=[],
            comment_ids=["comment13"],
        )

        # Save actions directly to ensure specific timestamps
        self.manager.storage.append_action("2025-07", action1)
        self.manager.storage.append_action("2025-08", action2)

        # Get all actions
        all_actions = self.manager.get_all_actions()
        assert len(all_actions) == 2

        # Actions should be sorted by timestamp
        assert all_actions[0].input_text == "Test Brush 1"
        assert all_actions[1].input_text == "Test Brush 2"

    def test_migrate_from_correct_matches(self):
        """Test migration from existing correct_matches directory structure."""
        # Create a temporary correct_matches directory for migration
        # (separate from the manager's correct_matches directory)
        old_correct_matches_dir = Path(self.test_dir) / "old_correct_matches"
        old_correct_matches_dir.mkdir(exist_ok=True)
        brush_file = old_correct_matches_dir / "brush.yaml"
        brush_data = {"Test Brand": {"Test Model": ["test brush input"]}}

        with open(brush_file, "w") as f:
            yaml.dump(brush_data, f)

        # Test migration
        migrated_count = self.manager.migrate_from_correct_matches(
            old_correct_matches_dir, "2025-08"
        )
        assert migrated_count == 1

        # Verify action was created
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "test brush input"
        assert actions[0].system_used == "migrated"

    def test_dual_update_validation(self):
        """Test that validation actions update both learning files and correct_matches.yaml."""
        # Mock the correct matches updater
        with patch.object(self.manager, "_update_correct_matches") as mock_updater:
            system_choice = {"strategy": "dual_component", "score": 85, "result": {}}
            user_choice = {"strategy": "dual_component", "result": {}}
            all_strategies = [
                {"strategy": "complete_brush", "score": 45, "result": {}},
                {"strategy": "dual_component", "score": 85, "result": {}},
            ]

            self.manager.record_validation(
                input_text="Test Brush Dual Update",
                month="2025-08",
                system_used="scoring",
                system_choice=system_choice,
                user_choice=user_choice,
                all_brush_strategies=all_strategies,
                comment_ids=["comment1", "comment2"],
            )

            # Verify learning file was updated
            actions = self.manager.get_monthly_actions("2025-08")
            assert len(actions) == 1
            assert actions[0].input_text == "Test Brush Dual Update"

            # Verify correct_matches.yaml was updated
            mock_updater.assert_called_once_with("Test Brush Dual Update", user_choice, "validated")

    def test_dual_update_override(self):
        """Test that override actions update both learning files and correct_matches.yaml."""
        # Mock the correct matches updater
        with patch.object(self.manager, "_update_correct_matches") as mock_updater:
            system_choice = {"strategy": "complete_brush", "score": 60, "result": {}}
            user_choice = {"strategy": "dual_component", "result": {}}
            all_strategies = []

            self.manager.record_override(
                input_text="Test Brush Override Dual Update",
                month="2025-08",
                system_used="scoring",
                system_choice=system_choice,
                user_choice=user_choice,
                all_brush_strategies=all_strategies,
                comment_ids=["comment3"],
            )

            # Verify learning file was updated
            actions = self.manager.get_monthly_actions("2025-08")
            assert len(actions) == 1
            expected_text = "Test Brush Override Dual Update"
            assert actions[0].input_text == expected_text

            # Verify correct_matches.yaml was updated
            mock_updater.assert_called_once_with(
                "Test Brush Override Dual Update", user_choice, "overridden"
            )

    def test_dual_update_error_handling(self):
        """Test that validation workflow fails fast if correct_matches.yaml update fails."""
        # Mock the correct matches updater to fail
        with patch.object(
            self.manager, "_update_correct_matches", side_effect=Exception("Update failed")
        ):
            system_choice = {"strategy": "test", "score": 50, "result": {}}
            user_choice = {"strategy": "test", "result": {}}
            all_strategies = []

            # Should raise exception - fail fast approach
            with pytest.raises(Exception, match="Update failed"):
                self.manager.record_validation(
                    input_text="Test Brush Error Handling",
                    month="2025-08",
                    system_used="scoring",
                    system_choice=system_choice,
                    user_choice=user_choice,
                    all_brush_strategies=all_strategies,
                    comment_ids=["comment4"],
                )

            # Verify learning file was NOT updated due to failure
            actions = self.manager.get_monthly_actions("2025-08")
            assert len(actions) == 0

    def test_normalized_text_usage(self):
        """Test that normalized text is used for correct_matches.yaml keys."""
        # Mock the correct matches updater
        with patch.object(self.manager, "_update_correct_matches") as mock_updater:
            system_choice = {"strategy": "test", "score": 50, "result": {}}
            user_choice = {"strategy": "test", "result": {}}
            all_strategies = []

            # Test with mixed case input
            self.manager.record_validation(
                input_text="Test Brush Mixed Case",
                month="2025-08",
                system_used="scoring",
                system_choice=system_choice,
                user_choice=user_choice,
                all_brush_strategies=all_strategies,
                comment_ids=["comment5"],
            )

            # Verify correct_matches.yaml was updated with normalized text
            mock_updater.assert_called_once_with("Test Brush Mixed Case", user_choice, "validated")

    def test_get_statistics(self):
        """Test getting validation statistics."""
        # Record mix of validations and overrides
        for i in range(3):
            self.manager.record_validation(
                input_text=f"Validated Brush {i}",
                month="2025-08",
                system_used="scoring",
                system_choice={
                    "strategy": "test",
                    "score": 50,
                    "result": {"brand": f"Test Brand {i}", "model": f"Test Model {i}"},
                },
                user_choice={
                    "strategy": "test",
                    "result": {"brand": f"Test Brand {i}", "model": f"Test Model {i}"},
                },
                all_brush_strategies=[],
                comment_ids=[f"comment{i+16}"],
            )

        for i in range(2):
            self.manager.record_override(
                input_text=f"Overridden Brush {i}",
                month="2025-08",
                system_used="scoring",
                system_choice={
                    "strategy": "test",
                    "score": 50,
                    "result": {"brand": f"Test Brand {i}", "model": f"Test Model {i}"},
                },
                user_choice={
                    "strategy": "other",
                    "result": {"brand": f"Test Brand {i}", "model": f"Test Model {i}"},
                },
                all_brush_strategies=[],
                comment_ids=[f"comment{i+19}"],
            )

        stats = self.manager.get_statistics("2025-08")
        assert stats["total_actions"] == 5
        assert stats["validated_count"] == 3
        assert stats["overridden_count"] == 2
        assert stats["validation_rate"] == 0.6  # 3/5
        assert stats["scoring_system_count"] == 5
        assert stats["legacy_system_count"] == 0

    def test_real_dual_update_validation(self):
        """Test that validation actions actually write to both learning files and correct_matches.yaml."""
        # Create a temporary correct_matches.yaml for testing
        import shutil
        import tempfile
        from pathlib import Path

        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        temp_learning_dir = Path(temp_dir) / "learning"
        temp_learning_dir.mkdir()
        temp_correct_matches = Path(temp_dir) / "correct_matches"

        try:
            # Initialize manager with temporary paths
            temp_manager = BrushUserActionsManager(
                base_path=temp_learning_dir, correct_matches_path=temp_correct_matches
            )

            # Test data that should result in a brush field type
            system_choice = {
                "strategy": "known_brush",
                "score": 80,
                "result": {
                    "brand": "Test Brand",
                    "model": "Test Model",
                    "source_text": "Test Brush Real Dual Update",
                },
            }
            user_choice = {
                "strategy": "known_brush",
                "score": 80,
                "result": {
                    "brand": "Test Brand",
                    "model": "Test Model",
                    "source_text": "Test Brush Real Dual Update",
                },
            }
            all_strategies = []

            # Record validation action
            temp_manager.record_validation(
                input_text="Test Brush Real Dual Update",
                month="2025-08",
                system_used="scoring",
                system_choice=system_choice,
                user_choice=user_choice,
                all_brush_strategies=all_strategies,
                comment_ids=["comment1"],
            )

            # Verify learning file was created and updated
            expected_learning_file = temp_learning_dir / "brush_user_actions" / "2025-08.yaml"
            assert expected_learning_file.exists(), "Learning file should exist"

            # Load and verify learning file contents
            with open(expected_learning_file, "r") as f:
                learning_data = yaml.safe_load(f)

            # New format: actions stored directly without wrapper
            assert isinstance(learning_data, dict), "Learning file should be a dictionary"
            assert len(learning_data) == 1, "Learning file should have one action"
            # Check that the input_text is a key in the dictionary
            assert (
                "Test Brush Real Dual Update" in learning_data
            ), "Learning file should have input_text as key"

            # Verify correct_matches directory was created
            assert temp_correct_matches.exists(), "correct_matches directory should exist"
            assert temp_correct_matches.is_dir(), "correct_matches should be a directory"

            # Verify brush.yaml file was created within the directory
            brush_file = temp_correct_matches / "brush.yaml"
            assert brush_file.exists(), "brush.yaml should exist in correct_matches directory"

            # Load and verify brush.yaml contents
            with open(brush_file, "r") as f:
                brush_data = yaml.safe_load(f)

            assert "Test Brand" in brush_data, "brush.yaml should have Test Brand"
            assert "Test Model" in brush_data["Test Brand"], "brush.yaml should have Test Model"

            # Check that the original input text was added (not normalized)
            patterns = brush_data["Test Brand"]["Test Model"]
            assert (
                "Test Brush Real Dual Update" in patterns
            ), "Original input text should be in brush.yaml"

        finally:
            # Clean up
            shutil.rmtree(temp_dir)
