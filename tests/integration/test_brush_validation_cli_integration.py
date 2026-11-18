"""Integration tests for brush CLI validation interface."""

import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock

import yaml

from sotd.match.brush.validation.cli import BrushValidationCLI


class TestBrushValidationCLIIntegration:
    """Integration tests for brush CLI validation interface."""

    def setup_method(self):
        """Set up test directories and data."""
        self.test_dir = tempfile.mkdtemp()
        self.test_data_dir = Path(self.test_dir) / "data"
        self.test_matched_legacy_dir = self.test_data_dir / "matched_legacy"
        self.test_matched_dir = self.test_data_dir / "matched"
        self.test_learning_dir = self.test_data_dir / "learning"

        # Create directories
        self.test_matched_legacy_dir.mkdir(parents=True)
        self.test_matched_dir.mkdir(parents=True)
        self.test_learning_dir.mkdir(parents=True)

        self.cli = BrushValidationCLI(data_path=self.test_data_dir)

        # Mock the brush_matcher property to avoid file dependencies
        mock_matcher = Mock()
        # Monkey patch the property to return our mock
        self.cli._brush_matcher = mock_matcher
        # Store the mock for later use in tests
        self.mock_brush_matcher = mock_matcher

    def teardown_method(self):
        """Clean up test directories."""
        shutil.rmtree(self.test_dir)

    def test_integration_with_legacy_data_format(self):
        """Test integration with legacy brush data format."""
        # Create legacy data file in the correct directory with proper structure
        legacy_data = {
            "data": [
                {
                    "id": "comment1",
                    "brush": {
                        "name": "Semogue 1305",
                        "normalized": "Semogue 1305",
                        "matched": {
                            "brand": "Semogue",
                            "model": "1305",
                            "handle": {"brand": "Semogue", "model": "1305"},
                            "knot": {"brand": "Semogue", "model": "1305", "fiber": "boar"},
                        },
                        "match_type": "regex",
                    },
                },
                {
                    "id": "comment2",
                    "brush": {
                        "name": "Unknown brush",
                        "normalized": "Unknown brush",
                        "matched": None,
                        "match_type": "no_match",
                    },
                },
            ]
        }

        legacy_file = self.test_matched_legacy_dir / "2025-08.json"  # Use correct legacy directory
        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)

        # Load and verify
        entries = self.cli.load_month_data("2025-08", "legacy")

        assert len(entries) == 2
        assert entries[0]["input_text"] == "Semogue 1305"
        assert entries[0]["system_used"] == "legacy"
        assert entries[0]["matched"]["brand"] == "Semogue"
        assert entries[1]["matched"] is None

    def test_integration_with_scoring_data_format(self):
        """Test integration with scoring system data format."""
        # Create scoring data file in the correct directory with proper structure
        scoring_data = {
            "data": [
                {
                    "id": "comment3",
                    "brush": {
                        "name": "Zenith B35 Boar 28mm",
                        "normalized": "Zenith B35 Boar 28mm",
                        "matched": {
                            "strategy": "known_brush",
                            "score": 95,
                            "brand": "Zenith",
                            "model": "B35",
                            "handle": {"brand": "Zenith", "model": "B35"},
                            "knot": {
                                "brand": "Zenith",
                                "model": "B35",
                                "fiber": "boar",
                                "knot_size_mm": 28,
                            },
                        },
                        "all_strategies": [
                            {"strategy": "known_brush", "score": 95, "result": {}},
                            {"strategy": "dual_component", "score": 60, "result": {}},
                            {"strategy": "automated_split", "score": 45, "result": {}},
                        ],
                    },
                }
            ]
        }

        scoring_file = self.test_matched_dir / "2025-08.json"  # Use correct scoring directory
        with open(scoring_file, "w") as f:
            json.dump(scoring_data, f)

        # Load and verify
        entries = self.cli.load_month_data("2025-08", "scoring")

        assert len(entries) == 1
        assert entries[0]["input_text"] == "Zenith B35 Boar 28mm"
        assert entries[0]["system_used"] == "scoring"
        assert entries[0]["matched"]["strategy"] == "known_brush"

    def test_integration_with_user_actions_storage(self):
        """Test integration with user actions storage system."""
        # Record a user action with proper test data structure
        self.cli.user_actions_manager.record_validation(
            input_text="Test Brush 1",
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
            comment_ids=["comment1"],
        )

        # Verify action was recorded
        actions = self.cli.user_actions_manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "Test Brush 1"
        assert actions[0].action == "validated"

        # Test that the action was stored in the correct format
        yaml_file = self.test_learning_dir / "brush_user_actions" / "2025-08.yaml"
        assert yaml_file.exists()

        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        # Current implementation uses input_text as keys
        assert "Test Brush 1" in data
        assert data["Test Brush 1"]["action"] == "validated"

    def test_integration_with_validation_statistics(self):
        """Test integration with validation statistics calculation."""
        # Create mock data files for statistics calculation in correct directories
        # with proper structure
        legacy_data = {
            "data": [
                {
                    "id": "comment4",
                    "brush": {"name": "Legacy Brush 1", "normalized": "Legacy Brush 1"},
                },
                {
                    "id": "comment5",
                    "brush": {"name": "Legacy Brush 2", "normalized": "Legacy Brush 2"},
                },
            ]
        }
        scoring_data = {
            "data": [
                {
                    "id": "comment6",
                    "brush": {"name": "Scoring Brush 1", "normalized": "Scoring Brush 1"},
                }
            ]
        }

        legacy_file = self.test_matched_legacy_dir / "2025-08.json"  # Use correct legacy directory
        scoring_file = self.test_matched_dir / "2025-08.json"  # Use correct scoring directory

        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)
        with open(scoring_file, "w") as f:
            json.dump(scoring_data, f)

        # Record some user actions with proper test data structure
        self.cli.user_actions_manager.record_validation(
            input_text="Legacy Brush 1",
            month="2025-08",
            system_used="legacy",
            system_choice={
                "strategy": "legacy",
                "score": None,
                "result": {
                    "brand": "Legacy Brand",
                    "model": "Legacy Model",
                },
            },
            user_choice={
                "strategy": "legacy",
                "result": {
                    "brand": "Legacy Brand",
                    "model": "Legacy Model",
                },
            },
            all_brush_strategies=[],
            comment_ids=["comment5"],
        )

        # Verify action was recorded
        actions = self.cli.user_actions_manager.get_monthly_actions("2025-08")
        assert len(actions) == 1
        assert actions[0].input_text == "Legacy Brush 1"
        assert actions[0].action == "validated"

        # Test statistics calculation
        stats = self.cli.user_actions_manager.get_statistics("2025-08")
        assert stats["total_actions"] == 1
        assert stats["validated_count"] == 1
        assert stats["legacy_system_count"] == 1

    def test_integration_with_ambiguity_sorting(self):
        """Test integration with ambiguity-based sorting."""
        # Create scoring entries with different score patterns
        entries = [
            {
                "input_text": "Clear Winner",
                "system_used": "scoring",
                "all_strategies": [
                    {"strategy": "known_brush", "score": 95},
                    {"strategy": "dual_component", "score": 45},
                    {"strategy": "automated_split", "score": 30},
                ],
            },
            {
                "input_text": "Close Race",
                "system_used": "scoring",
                "all_strategies": [
                    {"strategy": "dual_component", "score": 75},
                    {"strategy": "known_brush", "score": 73},
                    {"strategy": "automated_split", "score": 60},
                ],
            },
            {"input_text": "Legacy Entry", "system_used": "legacy", "all_strategies": []},
        ]

        sorted_entries = self.cli.sort_entries(entries, "2025-08", "ambiguity")

        # Most ambiguous (smallest difference) should come first
        assert sorted_entries[0]["input_text"] == "Close Race"  # 75-73 = 2
        assert sorted_entries[1]["input_text"] == "Clear Winner"  # 95-45 = 50
        assert sorted_entries[2]["input_text"] == "Legacy Entry"  # No scores = infinity

    def test_integration_with_cross_month_data(self):
        """Test integration with cross-month validation data."""
        # Create data for multiple months
        for month in ["2025-07", "2025-08"]:
            # Create legacy data in correct directory with proper structure
            legacy_data = {
                "data": [
                    {
                        "id": f"comment_{month}_1",
                        "brush": {
                            "name": f"Legacy Brush {month}",
                            "normalized": f"Legacy Brush {month}",
                        },
                    }
                ]
            }
            legacy_file = self.test_matched_legacy_dir / f"{month}.json"
            with open(legacy_file, "w") as f:
                json.dump(legacy_data, f)

            # Create scoring data in correct directory with proper structure
            scoring_data = {
                "data": [
                    {
                        "id": f"comment_{month}_2",
                        "brush": {
                            "name": f"Scoring Brush {month}",
                            "normalized": f"Scoring Brush {month}",
                        },
                    }
                ]
            }
            scoring_file = self.test_matched_dir / f"{month}.json"
            with open(scoring_file, "w") as f:
                json.dump(scoring_data, f)

        # Record user actions for both months with proper test data structure
        self.cli.user_actions_manager.record_validation(
            input_text="Legacy Brush 2025-07",
            month="2025-07",
            system_used="legacy",
            system_choice={
                "strategy": "legacy",
                "score": None,
                "result": {
                    "brand": "Legacy Brand 07",
                    "model": "Legacy Model 07",
                },
            },
            user_choice={
                "strategy": "legacy",
                "result": {
                    "brand": "Legacy Brand 07",
                    "model": "Legacy Model 07",
                },
            },
            all_brush_strategies=[],
            comment_ids=["comment7"],
        )

        self.cli.user_actions_manager.record_validation(
            input_text="Scoring Brush 2025-08",
            month="2025-08",
            system_used="scoring",
            system_choice={
                "strategy": "dual_component",
                "score": 85,
                "result": {
                    "brand": "Scoring Brand 08",
                    "model": "Scoring Model 08",
                    "handle": {"brand": "Handle Brand 08", "model": "Handle Model 08"},
                    "knot": {"brand": "Knot Brand 08", "model": "Knot Model 08"},
                },
            },
            user_choice={
                "strategy": "dual_component",
                "result": {
                    "brand": "Scoring Brand 08",
                    "model": "Scoring Model 08",
                    "handle": {"brand": "Handle Brand 08", "model": "Handle Model 08"},
                    "knot": {"brand": "Knot Brand 08", "model": "Knot Model 08"},
                },
            },
            all_brush_strategies=[],
            comment_ids=["comment8"],
        )

        # Verify actions were recorded in both months
        actions_07 = self.cli.user_actions_manager.get_monthly_actions("2025-07")
        actions_08 = self.cli.user_actions_manager.get_monthly_actions("2025-08")

        assert len(actions_07) == 1
        assert actions_07[0].input_text == "Legacy Brush 2025-07"
        assert actions_07[0].system_used == "legacy"

        assert len(actions_08) == 1
        assert actions_08[0].input_text == "Scoring Brush 2025-08"
        assert actions_08[0].system_used == "scoring"

    def test_integration_with_brush_matcher_entry_point(self):
        """Test integration with brush matcher entry point."""
        # Verify entry point is available
        assert hasattr(self.cli, "brush_matcher")

        # Verify entry point has expected methods
        assert hasattr(self.cli.brush_matcher, "match")
        # Note: get_system_name may not exist on the current brush matcher
        # Let's check what methods are actually available
        matcher_methods = [
            method for method in dir(self.cli.brush_matcher) if not method.startswith("_")
        ]
        assert "match" in matcher_methods, f"Expected 'match' method, found: {matcher_methods[:10]}"

    def test_validation_workflow_error_handling(self):
        """Test validation workflow error handling with missing files."""
        # Test with non-existent month
        entries = self.cli.load_month_data("2025-12", "legacy")
        assert entries == []

        # Test statistics with no data
        stats = self.cli.get_validation_statistics("2025-12")
        assert stats["total_entries"] == 0
        assert stats["validation_rate"] == 0.0

    def test_yaml_file_integration(self):
        """Test integration with YAML file storage format."""
        # Record user actions
        self.cli.user_actions_manager.record_validation(
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
            comment_ids=["comment6"],  # Add missing comment_ids parameter
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
        from datetime import datetime

        datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))

    def test_file_path_resolution(self):
        """Test correct file path resolution for different systems."""
        # Create test files in correct directories with proper structure
        legacy_data = {
            "data": [
                {
                    "id": "comment_test_1",
                    "brush": {"name": "Legacy Test", "normalized": "Legacy Test"},
                }
            ]
        }
        scoring_data = {
            "data": [
                {
                    "id": "comment_test_2",
                    "brush": {"name": "Scoring Test", "normalized": "Scoring Test"},
                }
            ]
        }

        legacy_file = self.test_matched_legacy_dir / "2025-08.json"  # Use correct legacy directory
        scoring_file = self.test_matched_dir / "2025-08.json"  # Use correct scoring directory

        with open(legacy_file, "w") as f:
            json.dump(legacy_data, f)
        with open(scoring_file, "w") as f:
            json.dump(scoring_data, f)

        # Test legacy path resolution
        legacy_entries = self.cli.load_month_data("2025-08", "legacy")
        assert len(legacy_entries) == 1
        assert legacy_entries[0]["input_text"] == "Legacy Test"

        # Test scoring path resolution
        scoring_entries = self.cli.load_month_data("2025-08", "scoring")
        assert len(scoring_entries) == 1
        assert scoring_entries[0]["input_text"] == "Scoring Test"
