#!/usr/bin/env python3
"""Tests for soap mashup enricher."""

from pathlib import Path

import pytest

from sotd.enrich.soap_mashup_enricher import SoapMashupEnricher


class TestSoapMashupEnricher:
    """Test soap mashup enricher functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.enricher = SoapMashupEnricher()

    def test_target_field(self):
        """Test target field property."""
        assert self.enricher.target_field == "soap"

    def test_applies_to_with_soap(self):
        """Test applies_to when soap field is present."""
        record = {"soap": {"original": "test", "normalized": "test"}}
        assert self.enricher.applies_to(record) is True

    def test_applies_to_without_soap(self):
        """Test applies_to when soap field is missing."""
        record = {"blade": {"original": "test", "normalized": "test"}}
        assert self.enricher.applies_to(record) is False

    def test_applies_to_with_none_soap(self):
        """Test applies_to when soap field is None."""
        record = {"soap": None}
        assert self.enricher.applies_to(record) is False

    def test_enrich_from_countable_false(self):
        """Test is_mashup True when matched.countable is False."""
        field_data = {
            "original": "Mama Bear Sample Mashup",
            "normalized": "mama bear sample mashup",
            "matched": {"brand": "Mama Bear", "scent": "Sample Mashup", "countable": False},
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_from_text_mashup(self):
        """Test is_mashup True when text contains mashup (unbranded)."""
        field_data = {
            "original": "soap mashup",
            "normalized": "soap mashup",
            "matched": None,
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_from_text_sample_mashup(self):
        """Test is_mashup True when text contains Sample mashup (matched null)."""
        field_data = {
            "original": "Sample mashup",
            "normalized": "sample mashup",
            "matched": None,
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_from_text_mash_up(self):
        """Test is_mashup True when text contains mash up."""
        field_data = {
            "original": "mash up",
            "normalized": "mash up",
            "matched": {},
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_from_text_mash_hyphen_up(self):
        """Test is_mashup True when text contains mash-up."""
        field_data = {
            "original": "mash-up",
            "normalized": "mash-up",
            "matched": {},
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_no_mashup(self):
        """Test is_mashup False when no catalog or text mashup."""
        field_data = {
            "original": "Barrister and Mann - Seville",
            "normalized": "barrister and mann - seville",
            "matched": {"brand": "Barrister and Mann", "scent": "Seville", "countable": True},
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": False}

    def test_enrich_matched_null_no_mashup_text(self):
        """Test is_mashup False when matched is null and no mashup in text."""
        field_data = {
            "original": "Unknown soap",
            "normalized": "unknown soap",
            "matched": None,
        }
        result = self.enricher.enrich(field_data, "")
        assert result == {"is_mashup": False}

    def test_enrich_from_catalog_lookup_when_countable_absent(self, tmp_path: Path):
        """Test is_mashup True when matched has brand+scent but no countable (e.g. correct_matches)."""
        soaps_yaml = tmp_path / "soaps.yaml"
        soaps_yaml.write_text("""
Mama Bear's Soaps:
  scents:
    Sample Mashup:
      countable: false
      patterns: []
""")
        enricher = SoapMashupEnricher(soaps_path=soaps_yaml)
        field_data = {
            "original": "Mama Bear's Soap Tri-Mix",
            "normalized": "mama bear's soap tri-mix",
            "matched": {"brand": "Mama Bear's Soaps", "scent": "Sample Mashup"},
        }
        result = enricher.enrich(field_data, "")
        assert result == {"is_mashup": True}

    def test_enrich_from_catalog_lookup_countable_true_not_mashup(self, tmp_path: Path):
        """Test is_mashup False when catalog lookup returns countable true."""
        soaps_yaml = tmp_path / "soaps.yaml"
        soaps_yaml.write_text("""
Some Brand:
  scents:
    Normal Scent:
      countable: true
      patterns: []
""")
        enricher = SoapMashupEnricher(soaps_path=soaps_yaml)
        field_data = {
            "original": "Some Brand - Normal Scent",
            "normalized": "some brand - normal scent",
            "matched": {"brand": "Some Brand", "scent": "Normal Scent"},
        }
        result = enricher.enrich(field_data, "")
        assert result == {"is_mashup": False}
