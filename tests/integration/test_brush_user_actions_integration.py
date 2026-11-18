"""Integration tests for brush user actions with existing workflows."""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import yaml

from sotd.match.brush.validation.user_actions import BrushUserActionsManager


class TestBrushUserActionsIntegration:
    """Integration tests for brush user actions."""

    def setup_method(self):
        """Set up test directories."""
        self.test_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.test_dir) / "data"
        self.test_learning_dir = self.test_data_dir / "learning"
        # Create a temporary correct_matches directory to avoid polluting production
        self.test_data_dir.mkdir(parents=True, exist_ok=True)
        test_correct_matches_path = self.test_data_dir / "correct_matches"
        test_correct_matches_path.mkdir(exist_ok=True)
        self.manager = BrushUserActionsManager(
            base_path=self.test_learning_dir, correct_matches_path=test_correct_matches_path
        )

    def teardown_method(self):
        """Clean up test directories."""
        shutil.rmtree(self.test_dir)

    def test_integration_with_file_io(self):
        """Test integration with existing FileIO utilities."""
        # Record some actions with proper test data structure
        self.manager.record_validation(
            input_text="Test Brush Integration",
            month="2025-08",
            system_used="scoring",
            system_choice={
                "strategy": "dual_component",
                "score": 85,
                "result": {
                    "brand": "Test Brand",
                    "model": "Test Model",
                    "handle": {"brand": "Test Handle", "model": "Handle Model"},
                    "knot": {"brand": "Test Knot", "model": "Knot Model"},
                },
            },
            user_choice={
                "strategy": "dual_component",
                "result": {
                    "brand": "Test Brand",
                    "model": "Test Model",
                    "handle": {"brand": "Test Handle", "model": "Handle Model"},
                    "knot": {"brand": "Test Knot", "model": "Knot Model"},
                },
            },
            all_brush_strategies=[],
            comment_ids=["test_comment_1"],
        )

        # Verify action was recorded
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "Test Brush Integration"
        assert actions[0].action == "validated"

        # Verify YAML file was created
        yaml_file = self.test_learning_dir / "brush_user_actions" / "2025-08.yaml"
        assert yaml_file.exists()

        # Verify YAML content structure
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        # Current implementation uses input_text as keys
        assert "Test Brush Integration" in data
        assert data["Test Brush Integration"]["action"] == "validated"

    def test_correct_matches_migration_integration(self):
        """Test integration with existing correct_matches.yaml workflow."""
        # Create a mock correct_matches.yaml file
        correct_matches_data = {
            "brush": {
                "Chisel & Hound / Omega 10098": {
                    "brand": "Chisel & Hound",
                    "model": "The Duke",
                    "handle": {"brand": "Chisel & Hound", "model": "The Duke"},
                    "knot": {"brand": "Omega", "model": "10098"},
                },
                "Summer Break Soaps Maize": {"brand": "Summer Break Soaps", "model": "Maize"},
            },
            "razor": {"Some Razor": {"brand": "Test", "model": "Razor"}},
            "soap": {"Some Soap": {"brand": "Test", "model": "Soap"}},
        }

        # Save to directory structure (correct_matches/brush.yaml)
        correct_matches_dir = self.test_data_dir / "correct_matches"
        correct_matches_dir.mkdir(exist_ok=True)
        brush_file = correct_matches_dir / "brush.yaml"
        with open(brush_file, "w") as f:
            yaml.dump(correct_matches_data["brush"], f)

        # Test migration - migrate_from_correct_matches now uses directory structure
        migrated_count = self.manager.migrate_from_correct_matches(correct_matches_dir, "2025-08")

        # Should only migrate brush entries, not razor/soap
        assert migrated_count == 2

        # Verify migrated actions
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 2

        # Check that both brush entries were migrated
        input_texts = [action.input_text for action in actions]
        assert "Chisel & Hound / Omega 10098" in input_texts
        assert "Summer Break Soaps Maize" in input_texts

        # All actions should be marked as migrated and validated
        for action in actions:
            assert action.system_used == "migrated"
            assert action.action == "validated"

    def test_monthly_file_structure_compatibility(self):
        """Test compatibility with expected monthly file structure."""
        # Record actions in multiple months with proper test data structure
        months = ["2025-06", "2025-07", "2025-08"]
        for i, month in enumerate(months):
            self.manager.record_validation(
                input_text=f"Test Brush {i}",
                month=month,
                system_used="scoring",
                system_choice={
                    "strategy": "test",
                    "score": 50,
                    "result": {
                        "brand": f"Test Brand {i}",
                        "model": f"Test Model {i}",
                        "handle": {"brand": f"Handle Brand {i}", "model": f"Handle Model {i}"},
                        "knot": {"brand": f"Knot Brand {i}", "model": f"Knot Model {i}"},
                    },
                },
                user_choice={
                    "strategy": "test",
                    "result": {
                        "brand": f"Test Brand {i}",
                        "model": f"Test Model {i}",
                        "handle": {"brand": f"Handle Brand {i}", "model": f"Handle Model {i}"},
                        "knot": {"brand": f"Knot Brand {i}", "model": f"Knot Model {i}"},
                    },
                },
                all_brush_strategies=[],
                comment_ids=[f"test_comment_{i}"],
            )

        # Verify files were created for all months
        for month in months:
            yaml_file = self.test_learning_dir / "brush_user_actions" / f"{month}.yaml"
            assert yaml_file.exists(), f"YAML file for {month} should exist"

        # Verify content structure for one month
        yaml_file = self.test_learning_dir / "brush_user_actions" / "2025-08.yaml"
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        # Current implementation uses input_text as keys
        assert "Test Brush 2" in data
        assert data["Test Brush 2"]["action"] == "validated"
        assert data["Test Brush 2"]["system_used"] == "scoring"

    def test_statistics_integration(self):
        """Test statistics integration with real data patterns."""
        # Create mix of scoring and legacy system data with proper test data structure
        # Scoring system validations
        for i in range(3):
            self.manager.record_validation(
                input_text=f"Scoring Brush {i}",
                month="2025-08",
                system_used="scoring",
                system_choice={
                    "strategy": "dual_component",
                    "score": 85,
                    "result": {
                        "brand": f"Scoring Brand {i}",
                        "model": f"Scoring Model {i}",
                        "handle": {"brand": f"Handle Brand {i}", "model": f"Handle Model {i}"},
                        "knot": {"brand": f"Knot Brand {i}", "model": f"Knot Model {i}"},
                    },
                },
                user_choice={
                    "strategy": "dual_component",
                    "result": {
                        "brand": f"Scoring Brand {i}",
                        "model": f"Scoring Model {i}",
                        "handle": {"brand": f"Handle Brand {i}", "model": f"Handle Model {i}"},
                        "knot": {"brand": f"Knot Brand {i}", "model": f"Knot Model {i}"},
                    },
                },
                all_brush_strategies=[],
                comment_ids=[f"scoring_comment_{i}"],
            )

        # Legacy system validations
        for i in range(2):
            self.manager.record_validation(
                input_text=f"Legacy Brush {i}",
                month="2025-08",
                system_used="legacy",
                system_choice={
                    "strategy": "legacy",
                    "score": None,
                    "result": {
                        "brand": f"Legacy Brand {i}",
                        "model": f"Legacy Model {i}",
                    },
                },
                user_choice={
                    "strategy": "legacy",
                    "result": {
                        "brand": f"Legacy Brand {i}",
                        "model": f"Legacy Model {i}",
                    },
                },
                all_brush_strategies=[],
                comment_ids=[f"legacy_comment_{i}"],
            )

        # Verify actions were recorded
        actions = self.manager.get_monthly_actions("2025-08")
        assert len(actions) == 5  # 3 scoring + 2 legacy

        # Test statistics calculation
        stats = self.manager.get_statistics("2025-08")
        assert stats["total_actions"] == 5
        assert stats["validated_count"] == 5
        assert stats["scoring_system_count"] == 3
        assert stats["legacy_system_count"] == 2

    def test_yaml_format_compatibility(self):
        """Test YAML format matches expected structure for downstream tools."""
        self.manager.record_validation(
            input_text="YAML Test Brush",
            month="2025-08",
            system_used="scoring",
            system_choice={
                "strategy": "dual_component",
                "score": 85,
                "result": {
                    "brand": "Test",
                    "model": "Brush",
                    "handle": {"brand": "Test", "model": "Handle"},
                    "knot": {"brand": "Test", "model": "Knot"},
                },
            },
            user_choice={
                "strategy": "dual_component",
                "result": {
                    "brand": "Test",
                    "model": "Brush",
                    "handle": {"brand": "Test", "model": "Handle"},
                    "knot": {"brand": "Test", "model": "Knot"},
                },
            },
            all_brush_strategies=[
                {"strategy": "complete_brush", "score": 45, "result": {}},
                {"strategy": "dual_component", "score": 85, "result": {}},
            ],
            comment_ids=["format_test_comment"],
        )

        # Verify YAML file was created
        yaml_file = self.test_learning_dir / "brush_user_actions" / "2025-08.yaml"
        assert yaml_file.exists()

        # Verify YAML content structure
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        # Current implementation uses input_text as keys, not wrapped in brush_user_actions array
        assert isinstance(data, dict), "YAML should be a dictionary"
        assert "YAML Test Brush" in data, "Input text should be a key in the dictionary"

        # Verify action structure
        action = data["YAML Test Brush"]
        required_fields = [
            "timestamp",
            "system_used",
            "action",
            "system_choice",
            "user_choice",
            "all_brush_strategies",
        ]
        for field in required_fields:
            assert field in action

        # Verify nested structure
        assert "strategy" in action["system_choice"]
        assert "score" in action["system_choice"]
        assert "result" in action["system_choice"]
        assert "strategy" in action["user_choice"]
        assert "result" in action["user_choice"]

        # Verify timestamp format (ISO 8601)
        timestamp_str = action["timestamp"]
        assert timestamp_str.endswith("Z")
        # Should be parseable back to datetime
        datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
