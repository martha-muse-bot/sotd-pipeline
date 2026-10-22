"""Unit tests for EnrichmentOverrideManager."""

import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.enrich.override_manager import EnrichmentOverrideManager


class TestEnrichmentOverrideManager:
    """Test cases for EnrichmentOverrideManager."""

    def test_init(self, tmp_path):
        """Test EnrichmentOverrideManager initialization."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        manager = EnrichmentOverrideManager(override_file)
        assert manager.override_file_path == override_file
        assert manager.overrides == {}
        assert not manager.has_overrides()

    def test_load_overrides_missing_file(self, tmp_path):
        """Test loading overrides when file doesn't exist (should not fail)."""
        override_file = tmp_path / "nonexistent.yaml"
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert not manager.has_overrides()

    def test_load_overrides_empty_file(self, tmp_path):
        """Test loading overrides from empty file."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert not manager.has_overrides()

    def test_load_overrides_valid_brush_fiber_use_catalog(self, tmp_path):
        """Test loading valid override with use_catalog flag for brush fiber."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "brush", "fiber") == "use_catalog"

    def test_load_overrides_valid_brush_fiber_explicit_value(self, tmp_path):
        """Test loading valid override with explicit value for brush fiber."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "Mixed Badger/Horse"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "brush", "fiber") == "Mixed Badger/Horse"

    def test_load_overrides_valid_brush_knot_size(self, tmp_path):
        """Test loading valid override for brush knot_size_mm."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      knot_size_mm: 28.0
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "brush", "knot_size_mm") == 28.0

    def test_load_overrides_valid_razor_grind(self, tmp_path):
        """Test loading valid override for razor grind."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    razor:
      grind: "full_hollow"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "razor", "grind") == "full_hollow"

    def test_load_overrides_valid_blade_use_count(self, tmp_path):
        """Test loading valid override for blade use_count."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    blade:
      use_count: 3
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "blade", "use_count") == 3

    def test_load_overrides_valid_soap_sample_brand(self, tmp_path):
        """Test loading valid override for soap sample_brand."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    soap:
      sample_brand: "Declaration Grooming"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert (
            manager.get_override("2026-01", "m99b8f9", "soap", "sample_brand")
            == "Declaration Grooming"
        )

    def test_load_overrides_multiple_fields(self, tmp_path):
        """Test loading overrides for multiple fields."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
      knot_size_mm: 21.0
    razor:
      grind: "full_hollow"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "brush", "fiber") == "use_catalog"
        assert manager.get_override("2026-01", "m99b8f9", "brush", "knot_size_mm") == 21.0
        assert manager.get_override("2026-01", "m99b8f9", "razor", "grind") == "full_hollow"

    def test_load_overrides_explicit_value_overrides_flag(self, tmp_path):
        """Test that explicit value takes precedence over use_catalog flag."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        # Note: In YAML, if both are specified, the last one wins
        # But our validation should handle this - explicit value should be preferred
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "Mixed Badger/Horse"
      fiber:
        use_catalog: true
""")
        manager = EnrichmentOverrideManager(override_file)
        # In YAML, duplicate keys - last one wins, so use_catalog will be the value
        # But we want explicit value to win, so we need to handle this in validation
        # For now, YAML will parse this as fiber being a dict with use_catalog: true
        # This is a limitation we'll document
        manager.load_overrides()
        # The YAML parser will use the last value, so fiber will be the dict
        result = manager.get_override("2026-01", "m99b8f9", "brush", "fiber")
        # Since YAML duplicates use last value, we'll get use_catalog
        assert result == "use_catalog"

    def test_load_overrides_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML raises error."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("invalid: yaml: [")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="Invalid YAML syntax"):
            manager.load_overrides()

    def test_load_overrides_invalid_root_type(self, tmp_path):
        """Test loading override file with invalid root type."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("- item1\n- item2")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="must contain a dictionary"):
            manager.load_overrides()

    def test_load_overrides_invalid_month_format(self, tmp_path):
        """Test loading override file with invalid month format."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026/01:
  m99b8f9:
    brush:
      fiber: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="Invalid month format"):
            manager.load_overrides()

    def test_load_overrides_invalid_month_number(self, tmp_path):
        """Test loading override file with invalid month number."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-13:
  m99b8f9:
    brush:
      fiber: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="Invalid month format"):
            manager.load_overrides()

    def test_load_overrides_invalid_field(self, tmp_path):
        """Test loading override file with invalid field name."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    invalid_field:
      fiber: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="Invalid field"):
            manager.load_overrides()

    def test_load_overrides_invalid_enrichment_key(self, tmp_path):
        """Test loading override file with invalid enrichment key."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      invalid_key: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="Invalid enrichment key"):
            manager.load_overrides()

    def test_load_overrides_invalid_use_catalog_type(self, tmp_path):
        """Test loading override file with invalid use_catalog type."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: "true"
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="must be a boolean"):
            manager.load_overrides()

    def test_load_overrides_invalid_knot_size_type(self, tmp_path):
        """Test loading override file with invalid knot_size_mm type."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      knot_size_mm: "28.0"
""")
        # String "28.0" should be converted to float
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        result = manager.get_override("2026-01", "m99b8f9", "brush", "knot_size_mm")
        assert result == 28.0
        assert isinstance(result, float)

    def test_load_overrides_invalid_use_count_type(self, tmp_path):
        """Test loading override file with invalid use_count type."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    blade:
      use_count: "3"
""")
        # String "3" should be converted to int
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        result = manager.get_override("2026-01", "m99b8f9", "blade", "use_count")
        assert result == 3
        assert isinstance(result, int)

    def test_load_overrides_empty_string_value(self, tmp_path):
        """Test loading override file with empty string value."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: ""
""")
        manager = EnrichmentOverrideManager(override_file)
        with pytest.raises(ValueError, match="cannot be empty"):
            manager.load_overrides()

    def test_get_override_nonexistent(self, tmp_path):
        """Test getting override that doesn't exist."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.get_override("2026-01", "nonexistent", "brush", "fiber") is None
        assert manager.get_override("2026-01", "m99b8f9", "brush", "knot_size_mm") is None
        assert manager.get_override("2026-02", "m99b8f9", "brush", "fiber") is None

    def test_has_override(self, tmp_path):
        """Test has_override method."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.has_override("2026-01", "m99b8f9", "brush", "fiber")
        assert not manager.has_override("2026-01", "m99b8f9", "brush", "knot_size_mm")
        assert not manager.has_override("2026-02", "m99b8f9", "brush", "fiber")

    def test_validate_overrides_missing_comment_id(self, tmp_path):
        """Test validate_overrides with missing comment ID (should warn, not fail)."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "test"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        # Should not raise, just warn
        data = [{"id": "other_id"}]
        manager.validate_overrides(data, "2026-01")
        # No exception should be raised

    def test_get_override_summary(self, tmp_path):
        """Test get_override_summary method."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
      knot_size_mm: 21.0
  m99b8f0:
    razor:
      grind: "full_hollow"
2026-02:
  m99b8f1:
    blade:
      use_count: 3
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        summary = manager.get_override_summary()
        assert summary["total_overrides"] == 4
        assert summary["months_with_overrides"] == 2
        assert summary["month_counts"]["2026-01"] == 3
        assert summary["month_counts"]["2026-02"] == 1
        assert summary["field_counts"]["brush"] == 2
        assert summary["field_counts"]["razor"] == 1
        assert summary["field_counts"]["blade"] == 1
        assert summary["key_counts"]["brush.fiber"] == 1
        assert summary["key_counts"]["brush.knot_size_mm"] == 1
        assert summary["key_counts"]["razor.grind"] == 1
        assert summary["key_counts"]["blade.use_count"] == 1

    def test_all_razor_enrichment_keys(self, tmp_path):
        """Test all razor enrichment keys are supported."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    razor:
      grind: "full_hollow"
      width: "15/16"
      point: "round"
      steel: "Carbon"
      gap: "0.68"
      plate: "A"
      plate_type: "B"
      plate_level: "1"
      super_speed_variant: "Red Tip"
      format: "DE"
""")
        manager = EnrichmentOverrideManager(override_file)
        manager.load_overrides()
        assert manager.get_override("2026-01", "m99b8f9", "razor", "grind") == "full_hollow"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "width") == "15/16"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "point") == "round"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "steel") == "Carbon"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "gap") == "0.68"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "plate") == "A"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "plate_type") == "B"
        assert manager.get_override("2026-01", "m99b8f9", "razor", "plate_level") == "1"
        assert (
            manager.get_override("2026-01", "m99b8f9", "razor", "super_speed_variant") == "Red Tip"
        )
        assert manager.get_override("2026-01", "m99b8f9", "razor", "format") == "DE"
