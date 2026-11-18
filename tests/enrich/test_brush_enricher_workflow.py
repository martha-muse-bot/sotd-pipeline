"""Integration tests for complete BrushEnricher workflow with user intent detection."""

from pathlib import Path

import pytest

from sotd.enrich.brush_enricher import BrushEnricher


class TestBrushEnricherWorkflow:
    """Integration tests for complete BrushEnricher workflow."""

    @pytest.fixture
    def brush_enricher(self):
        """Create BrushEnricher instance with real data path."""
        data_path = Path(__file__).parent.parent.parent / "data"
        return BrushEnricher(data_path)

    def test_enrich_composite_brush_with_user_intent(self, brush_enricher):
        """Test complete enrich workflow for composite brush with user intent detection."""
        field_data = {
            "matched": {
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"},
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                },
            }
        }
        original_comment = "Alpha T-400 in Zenith B03 Boar"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify basic enrichment worked
        assert result is not None
        assert isinstance(result, dict)

        # Verify user intent was detected
        assert "user_intent" in result
        assert result["user_intent"] in ["handle_primary", "knot_primary", "unknown"]

    def test_enrich_known_brush_no_user_intent(self, brush_enricher):
        """Test complete enrich workflow for known brush (should not detect user intent)."""
        field_data = {
            "matched": {
                "brand": "Alpha",
                "model": "T-400",
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"},
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                },
            }
        }
        original_comment = "Alpha T-400 in Zenith B03 Boar"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify basic enrichment worked
        assert result is not None
        assert isinstance(result, dict)

        # Verify user intent was NOT detected (known brush)
        assert "user_intent" not in result

    def test_enrich_missing_sections_no_user_intent(self, brush_enricher):
        """Test complete enrich workflow for brush missing sections (no user intent)."""
        field_data = {
            "matched": {
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"}
                # Missing knot section
            }
        }
        original_comment = "Alpha T-400 handle"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify basic enrichment worked
        assert result is not None
        assert isinstance(result, dict)

        # Verify user intent was NOT detected (missing sections)
        assert "user_intent" not in result

    def test_enrich_with_knot_size_and_fiber(self, brush_enricher):
        """Test complete enrich workflow with knot size and fiber extraction."""
        field_data = {
            "matched": {
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"},
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                },
            }
        }
        original_comment = "Alpha T-400 in Zenith B03 Boar 26mm"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify basic enrichment worked
        assert result is not None
        assert isinstance(result, dict)

        # Verify user intent was detected
        assert "user_intent" in result
        assert result["user_intent"] in ["handle_primary", "knot_primary", "unknown"]

        # Verify other enrichment fields are present
        assert "_extraction_source" in result
        assert "_fiber_extraction_source" in result

    def test_enrich_error_handling_user_intent(self, brush_enricher):
        """Test that user intent errors don't break the enrich workflow."""
        field_data = {
            "matched": {
                "handle": {
                    "brand": "InvalidBrand",
                    "model": "InvalidModel",
                    "handle_maker": "InvalidBrand",
                },
                "knot": {
                    "brand": "AnotherInvalidBrand",
                    "model": "AnotherInvalidModel",
                    "fiber": "Unknown",
                    "knot_size_mm": 24,
                },
            }
        }
        original_comment = "Invalid brush string"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify enrichment still worked despite user intent errors
        assert result is not None
        assert isinstance(result, dict)

        # Verify user intent was detected (should be handle_primary as default)
        assert "user_intent" in result
        assert result["user_intent"] == "handle_primary"

    def test_enrich_empty_field_data(self, brush_enricher):
        """Test enrich workflow with empty field data."""
        field_data = None
        original_comment = "Some brush string"

        result = brush_enricher.enrich(field_data, original_comment)

        # Should return None for invalid input
        assert result is None

    def test_enrich_empty_comment(self, brush_enricher):
        """Test enrich workflow with empty comment."""
        field_data = {
            "matched": {
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"},
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                },
            }
        }
        original_comment = ""

        result = brush_enricher.enrich(field_data, original_comment)

        # Should return enriched data from catalog even with empty comment
        assert result is not None
        assert result["_extraction_source"] == "catalog_data"

    def test_enrich_user_intent_handle_primary_scenario(self, brush_enricher):
        """Test user intent detection in handle_primary scenario."""
        field_data = {
            "matched": {
                "handle": {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"},
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                },
            }
        }
        original_comment = "Alpha T-400 in Zenith B03 Boar"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify user intent was detected
        assert "user_intent" in result
        # Should be handle_primary since "Alpha" appears before "Zenith"
        assert result["user_intent"] == "handle_primary"

    def test_enrich_user_intent_knot_primary_scenario(self, brush_enricher):
        """Test user intent detection in knot_primary scenario."""
        field_data = {
            "matched": {
                "handle": {
                    "brand": "Alpha",
                    "model": "T-400",
                    "handle_maker": "Alpha",
                    "source_text": "Alpha T-400",
                },
                "knot": {
                    "brand": "Zenith",
                    "model": "B03 (aka B2)",
                    "fiber": "Boar",
                    "knot_size_mm": 26,
                    "source_text": "Zenith B03 Boar",
                },
            }
        }
        original_comment = "Zenith B03 Boar in Alpha T-400"

        result = brush_enricher.enrich(field_data, original_comment)

        # Verify user intent was detected
        assert "user_intent" in result
        # Should be knot_primary since "Zenith" appears before "Alpha"
        assert result["user_intent"] == "knot_primary"
