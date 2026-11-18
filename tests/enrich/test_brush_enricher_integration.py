"""Integration tests for BrushEnricher user intent detection with real catalog data."""

from pathlib import Path

import pytest

from sotd.enrich.brush_enricher import BrushEnricher


class TestBrushEnricherIntegration:
    """Integration tests for BrushEnricher user intent detection."""

    @pytest.fixture
    def brush_enricher(self):
        """Create BrushEnricher instance with real data path."""
        data_path = Path(__file__).parent.parent.parent / "data"
        return BrushEnricher(data_path)

    def test_user_intent_with_real_alpha_handle(self, brush_enricher):
        """Test user intent detection with real Alpha handle patterns."""
        brush_string = "Alpha T-400 in Zenith B03 Boar"
        handle_data = {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"}
        knot_data = {
            "brand": "Zenith",
            "model": "B03 (aka B2)",
            "fiber": "Boar",
            "knot_size_mm": 26,
        }

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent in ["handle_primary", "knot_primary", "unknown"]

    def test_user_intent_with_real_zenith_knot(self, brush_enricher):
        """Test user intent detection with real Zenith knot patterns."""
        brush_string = "Zenith B03 Boar in Alpha T-400"
        handle_data = {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"}
        knot_data = {
            "brand": "Zenith",
            "model": "B03 (aka B2)",
            "fiber": "Boar",
            "knot_size_mm": 26,
        }

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent in ["handle_primary", "knot_primary", "unknown"]

    def test_user_intent_with_real_alpha_patterns(self, brush_enricher):
        """Test user intent detection with real Alpha patterns."""
        brush_string = "Alpha T-400 with Alpha G5"
        handle_data = {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"}
        knot_data = {"brand": "Alpha", "model": "G5", "fiber": "Synthetic", "knot_size_mm": 28}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent in ["handle_primary", "knot_primary", "unknown"]

    def test_user_intent_with_real_ap_shave_patterns(self, brush_enricher):
        """Test user intent detection with real AP Shave Co patterns."""
        brush_string = "AP Shave Co Synbad knot in custom handle"
        handle_data = {"brand": "Custom", "model": "Unknown", "handle_maker": "Custom"}
        knot_data = {
            "brand": "AP Shave Co",
            "model": "Synbad",
            "fiber": "Synthetic",
            "knot_size_mm": 24,
        }

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent in ["handle_primary", "knot_primary", "unknown"]

    def test_catalog_loader_integration(self, brush_enricher):
        """Test that catalog loader is properly integrated."""
        # Test handle patterns loading
        handle_patterns = brush_enricher._load_handle_patterns("Alpha", "T-400")
        assert isinstance(handle_patterns, list)

        # Test knot patterns loading
        knot_patterns = brush_enricher._load_knot_patterns("Zenith", "B03 (aka B2)")
        assert isinstance(knot_patterns, list)

    def test_catalog_cache_functionality(self, brush_enricher):
        """Test that catalog caching works properly."""
        # First call should miss cache
        handle_patterns1 = brush_enricher._load_handle_patterns("Alpha", "T-400")

        # Second call should hit cache
        handle_patterns2 = brush_enricher._load_handle_patterns("Alpha", "T-400")

        # Results should be identical
        assert handle_patterns1 == handle_patterns2

        # Check cache stats
        cache_stats = brush_enricher.catalog_loader.get_cache_stats()
        assert cache_stats["cache_hits"] > 0
        assert cache_stats["cache_misses"] > 0

    def test_user_intent_debug_with_real_data(self, brush_enricher):
        """Test debug version with real catalog data."""
        brush_string = "Alpha T-400 in Zenith B03 Boar"
        handle_data = {"brand": "Alpha", "model": "T-400", "handle_maker": "Alpha"}
        knot_data = {
            "brand": "Zenith",
            "model": "B03 (aka B2)",
            "fiber": "Boar",
            "knot_size_mm": 26,
        }

        result = brush_enricher._detect_user_intent_debug(brush_string, handle_data, knot_data)

        # Verify debug result structure
        assert "intent" in result
        assert "handle_position" in result
        assert "knot_position" in result
        assert "handle_patterns" in result
        assert "knot_patterns" in result
        assert "handle_matched_pattern" in result
        assert "knot_matched_pattern" in result
        assert "brush_string_normalized" in result
        assert "processing_time_ms" in result
        assert "edge_case_triggered" in result
        assert "error_message" in result

        # Verify intent is valid
        assert result["intent"] in ["handle_primary", "knot_primary", "unknown"]

        # Verify patterns were loaded
        assert len(result["handle_patterns"]) > 0
        assert len(result["knot_patterns"]) > 0

        # Verify processing time is reasonable
        assert result["processing_time_ms"] < 1000  # Should be very fast

    def test_user_intent_with_missing_catalog_entries(self, brush_enricher):
        """Test user intent detection with non-existent catalog entries."""
        brush_string = "Unknown Brand X in Unknown Brand Y"
        handle_data = {
            "brand": "Unknown Brand X",
            "model": "Unknown Model",
            "handle_maker": "Unknown Brand X",
        }
        knot_data = {
            "brand": "Unknown Brand Y",
            "model": "Unknown Model",
            "fiber": "Unknown",
            "knot_size_mm": 24,
        }

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        # Should return handle_primary as default when patterns not found
        assert intent == "handle_primary"

    def test_user_intent_with_empty_patterns(self, brush_enricher):
        """Test user intent detection when catalog returns empty patterns."""
        brush_string = "Test brush string"
        handle_data = {
            "brand": "NonExistentBrand",
            "model": "NonExistentModel",
            "handle_maker": "NonExistentBrand",
        }
        knot_data = {
            "brand": "AnotherNonExistentBrand",
            "model": "AnotherNonExistentModel",
            "fiber": "Unknown",
            "knot_size_mm": 24,
        }

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        # Should return handle_primary as default when no patterns found
        assert intent == "handle_primary"
