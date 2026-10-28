"""Integration tests for enrichment override system."""

import json
from pathlib import Path

import pytest

from sotd.enrich.enrich import enrich_comments, setup_enrichers
from sotd.enrich.override_manager import EnrichmentOverrideManager


class TestEnrichmentOverrideIntegration:
    """Integration tests for enrichment override system."""

    def test_end_to_end_brush_fiber_override(self, tmp_path):
        """Test end-to-end override application for brush fiber."""
        # Create override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")

        # Initialize override manager
        override_manager = EnrichmentOverrideManager(override_file)
        override_manager.load_overrides()

        # Setup enrichers with override manager
        setup_enrichers(override_manager=override_manager)

        # Create test data
        comments = [
            {
                "id": "m99b8f9",
                "_month": "2026-01",
                "brush": {
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
                },
                "brush_extracted": "Vielong Mixed Hair BADGER",
            }
        ]
        original_comments = ["Vielong Mixed Hair BADGER"]

        # Enrich comments
        enriched_comments = enrich_comments(comments, original_comments)

        # Verify override was applied
        assert len(enriched_comments) == 1
        enriched = enriched_comments[0]
        assert enriched["brush"]["enriched"]["fiber"] == "Mixed Badger/Horse"
        assert enriched["brush"]["enriched"]["_extraction_source"] == "catalog_data"

    def test_end_to_end_brush_explicit_value_override(self, tmp_path):
        """Test end-to-end override application with explicit value."""
        # Create override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber: "Mixed Badger/Horse"
      knot_size_mm: 28.0
""")

        # Initialize override manager
        override_manager = EnrichmentOverrideManager(override_file)
        override_manager.load_overrides()

        # Setup enrichers with override manager
        setup_enrichers(override_manager=override_manager)

        # Create test data
        comments = [
            {
                "id": "m99b8f9",
                "_month": "2026-01",
                "brush": {
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
                },
                "brush_extracted": "Vielong Mixed Hair BADGER",
            }
        ]
        original_comments = ["Vielong Mixed Hair BADGER"]

        # Enrich comments
        enriched_comments = enrich_comments(comments, original_comments)

        # Verify explicit overrides were applied
        assert len(enriched_comments) == 1
        enriched = enriched_comments[0]
        assert enriched["brush"]["enriched"]["fiber"] == "Mixed Badger/Horse"
        assert enriched["brush"]["enriched"]["knot_size_mm"] == 28.0

    def test_override_persistence_in_enriched_output(self, tmp_path):
        """Test that overrides persist correctly in enriched output structure."""
        # Create override file
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
""")

        # Initialize override manager
        override_manager = EnrichmentOverrideManager(override_file)
        override_manager.load_overrides()

        # Setup enrichers with override manager
        setup_enrichers(override_manager=override_manager)

        # Create test data
        comments = [
            {
                "id": "m99b8f9",
                "_month": "2026-01",
                "brush": {
                    "matched": {
                        "brand": "Vie-Long",
                        "model": "Mixed Badger & Horse",
                        "knot": {
                            "brand": "Vie-Long",
                            "model": "Mixed Badger & Horse",
                            "fiber": "Mixed Badger/Horse",
                        },
                    }
                },
                "brush_extracted": "Vielong Mixed Hair BADGER",
            }
        ]
        original_comments = ["Vielong Mixed Hair BADGER"]

        # Enrich comments
        enriched_comments = enrich_comments(comments, original_comments)

        # Verify structure is correct
        assert len(enriched_comments) == 1
        enriched = enriched_comments[0]
        assert "brush" in enriched
        assert "enriched" in enriched["brush"]
        assert "fiber" in enriched["brush"]["enriched"]
        assert enriched["brush"]["enriched"]["fiber"] == "Mixed Badger/Horse"

    def test_override_with_multiple_months(self, tmp_path):
        """Test override application across multiple months."""
        # Create override file with multiple months
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m99b8f9:
    brush:
      fiber:
        use_catalog: true
2026-02:
  m99b8f0:
    brush:
      fiber: "Badger"
""")

        # Initialize override manager
        override_manager = EnrichmentOverrideManager(override_file)
        override_manager.load_overrides()

        # Setup enrichers with override manager
        setup_enrichers(override_manager=override_manager)

        # Create test data for first month
        comments_2026_01 = [
            {
                "id": "m99b8f9",
                "_month": "2026-01",
                "brush": {
                    "matched": {
                        "brand": "Vie-Long",
                        "model": "Mixed Badger & Horse",
                        "knot": {
                            "brand": "Vie-Long",
                            "model": "Mixed Badger & Horse",
                            "fiber": "Mixed Badger/Horse",
                        },
                    }
                },
                "brush_extracted": "Vielong Mixed Hair BADGER",
            }
        ]
        original_comments_2026_01 = ["Vielong Mixed Hair BADGER"]

        # Enrich comments for first month
        enriched_2026_01 = enrich_comments(comments_2026_01, original_comments_2026_01)

        # Verify override for first month
        assert len(enriched_2026_01) == 1
        assert enriched_2026_01[0]["brush"]["enriched"]["fiber"] == "Mixed Badger/Horse"

        # Create test data for second month
        comments_2026_02 = [
            {
                "id": "m99b8f0",
                "_month": "2026-02",
                "brush": {
                    "matched": {
                        "brand": "Simpson",
                        "model": "Chubby 2",
                        "knot": {
                            "brand": "Simpson",
                            "model": "Chubby 2",
                            "fiber": "Badger",
                        },
                    }
                },
                "brush_extracted": "Simpson Chubby 2",
            }
        ]
        original_comments_2026_02 = ["Simpson Chubby 2"]

        # Enrich comments for second month
        enriched_2026_02 = enrich_comments(comments_2026_02, original_comments_2026_02)

        # Verify explicit override for second month
        assert len(enriched_2026_02) == 1
        assert enriched_2026_02[0]["brush"]["enriched"]["fiber"] == "Badger"

    def test_repeat_setup_updates_straight_razor_override_manager(self, tmp_path):
        """Repeat setup_enrichers() must update StraightRazorEnricher.

        Production path (sotd/enrich/run.py) calls setup_enrichers() once
        with no manager, then once per month with that month's manager.
        Previously only BrushEnricher was updated on repeat calls, so the
        StraightRazorEnricher kept override_manager=None and its
        grind/width/point/steel overrides never applied in real runs.
        """
        override_file = tmp_path / "enrichment_overrides.yaml"
        override_file.write_text("""
2026-01:
  m77:
    razor:
      grind: wedge
""")

        override_manager = EnrichmentOverrideManager(override_file)
        override_manager.load_overrides()

        # Production call order: bare setup first, manager setup second
        setup_enrichers()
        setup_enrichers(override_manager=override_manager)

        comments = [
            {
                "id": "m77",
                "_month": "2026-01",
                "razor": {
                    "matched": {
                        "brand": "Dovo",
                        "model": "Straight",
                        "format": "Straight",
                    },
                },
                "razor_extracted": "Dovo 5/8",
            }
        ]

        enriched_comments = enrich_comments(comments, ["Dovo 5/8"])

        assert len(enriched_comments) == 1
        assert enriched_comments[0]["razor"]["enriched"]["grind"] == "wedge"
