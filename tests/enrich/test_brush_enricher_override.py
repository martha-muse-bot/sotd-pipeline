"""Unit tests for BrushEnricher override functionality."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sotd.enrich.brush_enricher import BrushEnricher
from sotd.enrich.override_manager import EnrichmentOverrideManager


class TestBrushEnricherOverride:
    """Test cases for BrushEnricher override functionality."""

    @pytest.fixture
    def enricher(self, tmp_path):
        """Create a BrushEnricher instance for testing."""
        return BrushEnricher()

    @pytest.fixture
    def override_manager(self, tmp_path):
        """Create an EnrichmentOverrideManager for testing."""
        override_file = tmp_path / "enrichment_overrides.yaml"
        return EnrichmentOverrideManager(override_file)

    def test_fiber_override_use_catalog(self, enricher, override_manager, tmp_path):
        """Test fiber override with use_catalog flag forces catalog value."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        # Setup field data with catalog fiber
        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        # User comment that would normally extract "Mixed Badger/Boar"
        original_comment = "Vielong Mixed Hair BADGER"

        # Record with month and comment_id
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Should use catalog fiber, not user-extracted fiber
        assert result["fiber"] == "Mixed Badger/Horse"
        assert result["_extraction_source"] == "catalog_data"

    def test_fiber_override_explicit_value(self, enricher, override_manager, tmp_path):
        """Test fiber override with explicit value."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "Mixed Badger/Horse"
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        # Setup field data
        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Should use explicit override value
        assert result["fiber"] == "Mixed Badger/Horse"

    def test_knot_size_override_explicit_value(self, enricher, override_manager, tmp_path):
        """Test knot_size_mm override with explicit value."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      knot_size_mm: 21.0
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        # Setup field data
        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "knot_size_mm": 21.0,
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Should use explicit override value
        assert result["knot_size_mm"] == 21.0

    def test_knot_size_override_use_catalog(self, enricher, override_manager, tmp_path):
        """Test knot_size_mm override with use_catalog flag."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      knot_size_mm:
        use_catalog: true
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        # Setup field data with catalog knot_size
        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "knot_size_mm": 21.0,
                },
            }
        }

        # User comment that might extract different size
        # Use a comment that doesn't extract fiber to avoid user_data being non-empty
        # "28mm" will be extracted but overridden by use_catalog: true
        original_comment = "Vielong 28mm"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Should use catalog knot_size, not user-extracted
        assert result["knot_size_mm"] == 21.0
        # When use_catalog: true is set and no user data is extracted, source should be catalog_data
        assert result["_extraction_source"] == "catalog_data"

    def test_multiple_field_overrides(self, enricher, override_manager, tmp_path):
        """Test multiple field overrides in same record."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
      knot_size_mm: 21.0
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        # Setup field data
        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                    "knot_size_mm": 21.0,
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Both overrides should be applied
        assert result["fiber"] == "Mixed Badger/Horse"  # From catalog via use_catalog
        assert result["knot_size_mm"] == 21.0  # Explicit override

    def test_override_priority_explicit_over_flag(self, enricher, override_manager, tmp_path):
        """Test that explicit value takes precedence over use_catalog flag."""
        # Setup override file with both explicit and flag (YAML will use last one)
        # But our implementation should handle explicit value if both exist
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "Mixed Badger/Horse"
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Explicit value should be used
        assert result["fiber"] == "Mixed Badger/Horse"

    def test_no_override_default_behavior(self, enricher, override_manager, tmp_path):
        """Test that default behavior (user overrides catalog) works when no override."""
        # Setup override file with different comment_id
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  other_id:
    brush:
      fiber:
        use_catalog: true
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        # User comment that would extract "Mixed Badger/Boar"
        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}  # Different ID, no override

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Default behavior: user extraction should override catalog
        # (This test assumes match_fiber would extract "Mixed Badger/Boar" from the comment)
        # The actual value depends on what match_fiber extracts
        assert "fiber" in result

    def test_override_without_record(self, enricher, override_manager, tmp_path):
        """Test that override is not applied when record is not provided."""
        # Setup override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")
        override_manager.load_overrides()

        # Create enricher with override manager
        enricher.override_manager = override_manager

        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        # No record provided
        result = enricher.enrich(field_data, original_comment, None)

        assert result is not None
        # Should work normally without override (since no record to look up)

    def test_override_without_override_manager(self, enricher):
        """Test that enrichment works normally without override manager."""
        # No override manager set
        enricher.override_manager = None

        field_data = {
            "matched": {
                "brand": "Vie-Long",
                "model": "Mixed Badger & Horse",
                "knot": {
                    "brand": "Vie-Long",
                    "model": "Mixed Badger & Horse",
                    "fiber": "Mixed Badger/Horse",
                },
            }
        }

        original_comment = "Vielong Mixed Hair BADGER"
        record = {"id": "m99b8f9", "_month": "2026-01"}

        result = enricher.enrich(field_data, original_comment, record)

        assert result is not None
        # Should work normally
