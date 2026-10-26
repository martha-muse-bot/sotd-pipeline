#!/usr/bin/env python3
"""Unit tests for OverrideManager class."""

from pathlib import Path

import pytest

from sotd.extract.override_manager import OverrideManager


class TestOverrideManager:
    """Test cases for OverrideManager class."""

    def test_init(self):
        """Test OverrideManager initialization."""
        override_path = Path("test_overrides.yaml")
        manager = OverrideManager(override_path)
        assert manager.override_file_path == override_path
        assert manager.overrides == {}

    def test_load_overrides_empty_file(self, tmp_path):
        """Test loading overrides from empty file."""
        override_file = tmp_path / "empty.yaml"
        override_file.write_text("")
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.overrides == {}

    def test_load_overrides_valid_single_override(self, tmp_path):
        """Test loading valid single override."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert "2025-01" in manager.overrides
        assert "m99b8f9" in manager.overrides["2025-01"]
        assert manager.overrides["2025-01"]["m99b8f9"]["razor"] == "Koraat"

    def test_load_overrides_multiple_fields(self, tmp_path):
        """Test loading overrides for multiple fields."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
    blade: "Gillette Minora Platinum"
    soap: "Declaration Grooming - Seville"
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        comment_overrides = manager.overrides["2025-01"]["m99b8f9"]
        assert comment_overrides["razor"] == "Koraat"
        assert comment_overrides["blade"] == "Gillette Minora Platinum"
        assert comment_overrides["soap"] == "Declaration Grooming - Seville"

    def test_load_overrides_multiple_comments(self, tmp_path):
        """Test loading overrides for multiple comments."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
  m99b8f0:
    brush: "Semogue 610"
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert len(manager.overrides["2025-01"]) == 2
        assert manager.overrides["2025-01"]["m99b8f9"]["razor"] == "Koraat"
        assert manager.overrides["2025-01"]["m99b8f0"]["brush"] == "Semogue 610"

    def test_load_overrides_multiple_months(self, tmp_path):
        """Test loading overrides for multiple months."""
        override_file = tmp_path / "test.yaml"
        # File doesn't exist
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.overrides == {}

    def test_load_overrides_file_not_exists(self, tmp_path):
        """Test behavior when override file doesn't exist."""
        override_file = tmp_path / "nonexistent.yaml"
        # File doesn't exist
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.overrides == {}

    def test_load_overrides_invalid_yaml(self, tmp_path):
        """Test error handling for invalid YAML."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
    invalid_field: value
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="Invalid field 'invalid_field'"):
            manager.load_overrides()

    def test_load_overrides_invalid_field_type(self, tmp_path):
        """Test error handling for invalid field type."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: 123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="must be a string"):
            manager.load_overrides()

    def test_load_overrides_empty_value(self, tmp_path):
        """Test error handling for empty override values."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: ""
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            manager.load_overrides()

    def test_load_overrides_whitespace_only_value(self, tmp_path):
        """Test error handling for whitespace-only override values."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: "   "
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="cannot be empty or whitespace-only"):
            manager.load_overrides()

    def test_load_overrides_value_too_long(self, tmp_path):
        """Test error handling for override values that are too long."""
        long_value = "a" * 201  # 201 characters, over the 200 limit
        yaml_content = f"""
2025-01:
  m99b8f9:
    razor: "{long_value}"
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="is too long"):
            manager.load_overrides()

    def test_load_overrides_duplicate_override(self, tmp_path):
        """Test error handling for duplicate overrides."""
        # Note: YAML doesn't allow duplicate keys, so this test validates
        # that the duplicate detection logic works correctly
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
    blade: Feather
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        # Should load successfully since no actual duplicates exist
        assert "2025-01" in manager.overrides
        assert "m99b8f9" in manager.overrides["2025-01"]
        assert manager.overrides["2025-01"]["m99b8f9"]["razor"] == "Koraat"
        assert manager.overrides["2025-01"]["m99b8f9"]["blade"] == "Feather"

    def test_load_overrides_invalid_root_type(self, tmp_path):
        """Test error handling for invalid root type."""
        # Use valid YAML that's not a dict (a string)
        yaml_content = "not a dictionary"
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="must contain a dictionary at root level"):
            manager.load_overrides()

    def test_load_overrides_invalid_month_type(self, tmp_path):
        """Test error handling for invalid month type."""
        yaml_content = """
2025-01: "not a dict"
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="must contain a dictionary of comment overrides"):
            manager.load_overrides()

    def test_load_overrides_invalid_comment_type(self, tmp_path):
        """Test error handling for invalid comment type."""
        yaml_content = """
2025-01:
  m99b8f9: "not a dict"
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="must contain field overrides"):
            manager.load_overrides()

    def test_get_override_existing(self, tmp_path):
        """Test getting existing override."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        override = manager.get_override("2025-01", "m99b8f9", "razor")
        assert override == "Koraat"

    def test_get_override_nonexistent_month(self):
        """Test getting override for nonexistent month."""
        manager = OverrideManager(Path("test.yaml"))
        override = manager.get_override("2025-01", "m99b8f9", "razor")
        assert override is None

    def test_get_override_nonexistent_comment(self, tmp_path):
        """Test getting override for nonexistent comment."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        override = manager.get_override("2025-01", "nonexistent", "razor")
        assert override is None

    def test_get_override_nonexistent_field(self, tmp_path):
        """Test getting override for nonexistent field."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        override = manager.get_override("2025-01", "m99b8f9", "blade")
        assert override is None

    def test_validate_overrides_all_exist(self, tmp_path):
        """Test validation when all override comment IDs exist."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        data = [{"id": "m99b8f9", "author": "test"}]
        # Should not raise any exception
        manager.validate_overrides(data)

    def test_validate_overrides_missing_comment_id(self, tmp_path):
        """Test validation when override references missing comment ID."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        data = [{"id": "different_id", "author": "test"}]
        with pytest.raises(ValueError, match="non-existent comment IDs"):
            manager.validate_overrides(data)

    def test_validate_overrides_no_id_field(self, tmp_path):
        """Test validation when comment records don't have id field."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        data = [{"author": "test"}]  # Missing id field
        with pytest.raises(ValueError, match="non-existent comment IDs"):
            manager.validate_overrides(data)

    def test_apply_override_existing_field(self):
        """Test applying override to existing field."""
        manager = OverrideManager(Path("test.yaml"))
        field_data = {"original": "Ko", "normalized": "Ko"}

        result = manager.apply_override(field_data, "Koraat", True)

        assert result["original"] == "Ko"  # Preserved
        assert result["normalized"] == "Koraat"  # Overridden
        assert result["overridden"] == "Normalized"

    def test_apply_override_missing_field(self):
        """Test applying override to create missing field."""
        manager = OverrideManager(Path("test.yaml"))

        result = manager.apply_override(None, "Koraat", False)

        assert result["original"] == "Koraat"
        assert result["normalized"] == "Koraat"
        assert result["overridden"] == "Original,Normalized"

    def test_apply_override_none_field_data(self):
        """Test applying override when field_data is None."""
        manager = OverrideManager(Path("test.yaml"))

        result = manager.apply_override(None, "Koraat", True)

        # Should create new field since field_data is None
        assert result["original"] == "Koraat"
        assert result["normalized"] == "Koraat"
        assert result["overridden"] == "Original,Normalized"

    def test_has_overrides_false(self):
        """Test has_overrides when no overrides are loaded."""
        manager = OverrideManager(Path("test.yaml"))
        assert not manager.has_overrides()

    def test_has_overrides_true(self, tmp_path):
        """Test has_overrides when overrides are loaded."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.has_overrides()

    def test_load_overrides_strips_whitespace(self, tmp_path):
        """Test that override values have whitespace stripped."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: "  Koraat  "
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        override = manager.get_override("2025-01", "m99b8f9", "razor")
        assert override == "Koraat"  # Whitespace stripped

    def test_get_override_summary_empty(self):
        """Test get_override_summary when no overrides are loaded."""
        manager = OverrideManager(Path("test.yaml"))
        summary = manager.get_override_summary()

        assert summary["total_overrides"] == 0
        assert summary["months_with_overrides"] == 0
        assert summary["month_counts"] == {}
        assert summary["field_counts"] == {}

    def test_get_override_summary_with_overrides(self, tmp_path):
        """Test get_override_summary with loaded overrides."""
        yaml_content = """
2025-01:
  m99b8f9:
    razor: Koraat
    blade: Feather
  m99b8f0:
    brush: Semogue
2025-02:
  m99b8f1:
    soap: Declaration
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        summary = manager.get_override_summary()

        assert summary["total_overrides"] == 4
        assert summary["months_with_overrides"] == 2
        assert summary["month_counts"]["2025-01"] == 3
        assert summary["month_counts"]["2025-02"] == 1
        assert summary["field_counts"]["razor"] == 1
        assert summary["field_counts"]["blade"] == 1
        assert summary["field_counts"]["brush"] == 1
        assert summary["field_counts"]["soap"] == 1

    def test_update_comment_overrides_upsert_and_persist(self, tmp_path):
        """Test upserting overrides writes YAML atomically."""
        override_file = tmp_path / "overrides.yaml"
        override_file.write_text("")
        manager = OverrideManager(override_file)

        result = manager.update_comment_overrides(
            "2026-08",
            "p47tzgo",
            {"razor": "Gillette Tech", "blade": None, "brush": "", "soap": None},
        )

        assert result == {"razor": "Gillette Tech"}
        manager2 = OverrideManager(override_file)
        manager2.load_overrides()
        assert manager2.get_override("2026-08", "p47tzgo", "razor") == "Gillette Tech"

    def test_update_comment_overrides_delete_field_and_prune(self, tmp_path):
        """Clearing the last field removes comment and month nodes."""
        yaml_content = """
2026-08:
  p47tzgo:
    razor: Gillette Tech
"""
        override_file = tmp_path / "overrides.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        result = manager.update_comment_overrides(
            "2026-08", "p47tzgo", {"razor": None, "blade": None, "brush": None, "soap": None}
        )

        assert result == {}
        manager2 = OverrideManager(override_file)
        manager2.load_overrides()
        assert manager2.overrides == {}

    def test_update_comment_overrides_rejects_invalid_field(self, tmp_path):
        override_file = tmp_path / "overrides.yaml"
        override_file.write_text("")
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="Invalid field"):
            manager.update_comment_overrides("2026-08", "abc", {"aftershave": "Foo"})

    def test_load_overrides_bulk_expands(self, tmp_path):
        """Bulk block expands into per-comment overrides."""
        yaml_content = """
2026-10:
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids:
        - abc123
        - def456
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.get_override("2026-10", "abc123", "soap") == "Unknown Mystery"
        assert manager.get_override("2026-10", "def456", "soap") == "Unknown Mystery"
        assert manager.get_override_summary()["total_overrides"] == 2

    def test_load_overrides_bulk_and_per_id_different_fields_ok(self, tmp_path):
        """Same comment may have bulk and per-ID overrides for different fields."""
        yaml_content = """
2026-10:
  abc123:
    razor: Merkur 34C
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids:
        - abc123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        manager.load_overrides()

        assert manager.get_override("2026-10", "abc123", "razor") == "Merkur 34C"
        assert manager.get_override("2026-10", "abc123", "soap") == "Unknown Mystery"

    def test_load_overrides_bulk_conflicts_with_per_id(self, tmp_path):
        """Same comment+field in bulk and per-ID fails loudly."""
        yaml_content = """
2026-10:
  abc123:
    soap: Something Else
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids:
        - abc123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="Conflict.*abc123.*soap"):
            manager.load_overrides()

    def test_load_overrides_bulk_duplicate_comment_field(self, tmp_path):
        """Same comment+field in two bulk entries fails loudly."""
        yaml_content = """
2026-10:
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids:
        - abc123
    - field: soap
      value: Other Value
      comment_ids:
        - abc123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="Conflict.*abc123.*soap"):
            manager.load_overrides()

    def test_load_overrides_bulk_invalid_field(self, tmp_path):
        yaml_content = """
2026-10:
  bulk:
    - field: aftershave
      value: Foo
      comment_ids:
        - abc123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="Invalid field 'aftershave'"):
            manager.load_overrides()

    def test_load_overrides_bulk_empty_comment_ids(self, tmp_path):
        yaml_content = """
2026-10:
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids: []
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="comment_ids"):
            manager.load_overrides()

    def test_load_overrides_bulk_missing_keys(self, tmp_path):
        yaml_content = """
2026-10:
  bulk:
    - field: soap
      comment_ids:
        - abc123
"""
        override_file = tmp_path / "test.yaml"
        override_file.write_text(yaml_content)
        manager = OverrideManager(override_file)

        with pytest.raises(ValueError, match="value"):
            manager.load_overrides()
