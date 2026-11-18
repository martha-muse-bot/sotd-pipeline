"""Tests for filtered entries integration in match phase."""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.match.run import _get_filtered_entries_manager, match_record


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory with test filtered entries."""
    temp_dir = tempfile.mkdtemp()
    data_dir = Path(temp_dir) / "data"
    data_dir.mkdir()

    # Create test filtered entries file
    filtered_file = data_dir / "intentionally_unmatched.yaml"
    test_data = {
        "razor": {
            "Hot Wheels Play Razor": {
                "added_date": "2025-01-27",
                "comment_ids": [
                    {"file": "data/comments/2025-01.json", "id": "abc123", "source": "user"}
                ],
            }
        },
        "brush": {},
        "blade": {},
        "soap": {},
    }

    with open(filtered_file, "w", encoding="utf-8") as f:
        yaml.dump(test_data, f)

    yield temp_dir

    # Cleanup
    shutil.rmtree(temp_dir)


class TestFilteredEntriesIntegration:
    """Test filtered entries integration in match phase."""

    def test_filtered_razor_is_skipped(self, temp_data_dir, monkeypatch):
        """Test that filtered razors are skipped during matching."""
        # Mock the filtered entries manager to return a mock that can check if items are filtered
        from unittest.mock import Mock

        mock_filtered_manager = Mock()
        mock_filtered_manager.is_filtered.return_value = True  # Mark razor as filtered
        monkeypatch.setattr(
            "sotd.match.run._get_filtered_entries_manager", lambda: mock_filtered_manager
        )

        # Mock the Path constructor to return our test file
        original_path = Path

        def mock_path(path_str):
            if "intentionally_unmatched.yaml" in str(path_str):
                return Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml"
            return original_path(path_str)

        monkeypatch.setattr("sotd.match.run.Path", mock_path)

        # Test record with filtered razor (modern structured format)
        record = {
            "razor": {"original": "Hot Wheels Play Razor", "normalized": "hot wheels play razor"},
            "blade": {"original": "Feather", "normalized": "feather"},
            "brush": {"original": "Simpson Chubby 2", "normalized": "simpson chubby 2"},
            "soap": {"original": "Declaration Grooming", "normalized": "declaration grooming"},
        }

        # Create mock matcher objects for testing
        from unittest.mock import Mock

        mock_razor_matcher = Mock()
        mock_blade_matcher = Mock()
        mock_soap_matcher = Mock()
        mock_brush_matcher = Mock()
        mock_monitor = Mock()

        # Configure mock matchers to return proper MatchResult objects
        from sotd.match.types import MatchResult

        mock_razor_matcher.match.return_value = MatchResult(
            original="Merkur 34C",
            normalized="merkur 34c",
            matched={"brand": "Merkur", "model": "34C"},
            match_type="regex",
            pattern="merkur.*34c",
        )
        mock_blade_matcher.match_with_context.return_value = MatchResult(
            original="Feather",
            normalized="feather",
            matched={"brand": "Feather", "model": "Super Platinum"},
            match_type="exact",
            pattern="feather",
        )
        mock_soap_matcher.match.return_value = MatchResult(
            original="Declaration Grooming",
            normalized="declaration grooming",
            matched={"brand": "Declaration Grooming"},
            match_type="brand",
            pattern="declaration.*grooming",
        )
        mock_brush_matcher.match.return_value = MatchResult(
            original="Simpson Chubby 2",
            normalized="simpson chubby 2",
            matched={"brand": "Simpson", "model": "Chubby 2"},
            match_type="regex",
            pattern="simpson.*chubby.*2",
        )

        result = match_record(
            record,
            mock_razor_matcher,
            mock_blade_matcher,
            mock_soap_matcher,
            mock_brush_matcher,
            mock_monitor,
        )

        # Razor should be marked as filtered
        assert result["razor"].original == "Hot Wheels Play Razor"
        assert result["razor"].matched is None
        assert result["razor"].match_type == "filtered"
        assert result["razor"].pattern is None

        # Other fields should be processed normally
        assert "blade" in result
        assert "brush" in result
        assert "soap" in result

    def test_non_filtered_entries_processed_normally(self, temp_data_dir, monkeypatch):
        """Test that non-filtered entries are processed normally."""
        # Mock the filtered entries manager to return a mock that marks nothing as filtered
        from unittest.mock import Mock

        mock_filtered_manager = Mock()
        mock_filtered_manager.is_filtered.return_value = False  # Mark nothing as filtered
        monkeypatch.setattr(
            "sotd.match.run._get_filtered_entries_manager", lambda: mock_filtered_manager
        )

        # Mock the Path constructor to return our test file
        original_path = Path

        def mock_path(path_str):
            if "intentionally_unmatched.yaml" in str(path_str):
                return Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml"
            return original_path(path_str)

        monkeypatch.setattr("sotd.match.run.Path", mock_path)

        # Test record with non-filtered entries (modern structured format)
        record = {
            "razor": {"original": "Merkur 34C", "normalized": "merkur 34c"},
            "blade": {"original": "Feather", "normalized": "feather"},
            "brush": {"original": "Simpson Chubby 2", "normalized": "simpson chubby 2"},
            "soap": {"original": "Declaration Grooming", "normalized": "declaration grooming"},
        }

        # Create mock matcher objects for testing
        from unittest.mock import Mock

        mock_razor_matcher = Mock()
        mock_blade_matcher = Mock()
        mock_soap_matcher = Mock()
        mock_brush_matcher = Mock()
        mock_monitor = Mock()

        # Configure mock matchers to return proper MatchResult objects
        from sotd.match.types import MatchResult

        mock_razor_matcher.match.return_value = MatchResult(
            original="Merkur 34C",
            normalized="merkur 34c",
            matched={"brand": "Merkur", "model": "34C"},
            match_type="regex",
            pattern="merkur.*34c",
        )
        mock_blade_matcher.match_with_context.return_value = MatchResult(
            original="Feather",
            normalized="feather",
            matched={"brand": "Feather", "model": "Super Platinum"},
            match_type="exact",
            pattern="feather",
        )
        mock_soap_matcher.match.return_value = MatchResult(
            original="Declaration Grooming",
            normalized="declaration grooming",
            matched={"brand": "Declaration Grooming"},
            match_type="brand",
            pattern="declaration.*grooming",
        )
        mock_brush_matcher.match.return_value = MatchResult(
            original="Simpson Chubby 2",
            normalized="simpson chubby 2",
            matched={"brand": "Simpson", "model": "Chubby 2"},
            match_type="regex",
            pattern="simpson.*chubby.*2",
        )

        result = match_record(
            record,
            mock_razor_matcher,
            mock_blade_matcher,
            mock_soap_matcher,
            mock_brush_matcher,
            mock_monitor,
        )

        # All entries should be processed normally (not marked as intentionally unmatched)
        assert result["razor"].original == "Merkur 34C"
        assert result["razor"].match_type != "intentionally_unmatched"

        assert result["blade"].original == "Feather"
        assert result["blade"].match_type != "intentionally_unmatched"

        # Brush is converted to dict for consistency
        assert result["brush"]["original"] == "Simpson Chubby 2"
        assert result["brush"]["match_type"] != "intentionally_unmatched"

        assert result["soap"].original == "Declaration Grooming"
        assert result["soap"].match_type != "intentionally_unmatched"

    def test_filtered_entries_manager_initialization(self, temp_data_dir, monkeypatch):
        """Test that filtered entries manager initializes correctly."""
        # Mock the filtered entries file path to use our test file
        monkeypatch.setattr("sotd.match.run._filtered_entries_manager", None)

        # Mock the Path constructor to return our test file
        original_path = Path

        def mock_path(path_str):
            if "intentionally_unmatched.yaml" in str(path_str):
                return Path(temp_data_dir) / "data" / "intentionally_unmatched.yaml"
            return original_path(path_str)

        monkeypatch.setattr("sotd.match.run.Path", mock_path)

        # Get the manager
        manager = _get_filtered_entries_manager()

        # Verify it loaded the test data
        assert manager.is_filtered("razor", "Hot Wheels Play Razor")
        assert not manager.is_filtered("razor", "Merkur 34C")
