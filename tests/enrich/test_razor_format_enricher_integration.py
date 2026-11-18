"""Integration tests for RazorFormatEnricher with full record structure."""

import pytest

from sotd.enrich.razor_format_enricher import RazorFormatEnricher
from sotd.enrich.registry import EnricherRegistry


@pytest.fixture
def registry():
    """Create an enricher registry for testing."""
    reg = EnricherRegistry()
    reg.register(RazorFormatEnricher())
    return reg


class TestRazorFormatEnricherIntegration:
    """Integration tests with full record structure."""

    def test_enriched_format_appears_in_razor_enriched(self, registry):
        """Test that enriched format appears in razor.enriched.format."""
        record = {
            "author": "test_user",
            "razor": {
                "original": "AE Kai CLone Kamisori Shavette",
                "matched": {
                    "brand": "Other Shavette",
                    "format": "Shavette",
                },
            },
            "blade": {
                "original": "Feather Soft Guard AC",
                "matched": {
                    "brand": "Feather",
                    "format": "AC",
                },
            },
        }

        enriched_record = registry.enrich_record(record, "")

        assert "enriched" in enriched_record["razor"]
        assert enriched_record["razor"]["enriched"]["format"] == "Shavette (AC)"
        assert enriched_record["razor"]["matched"]["format"] == "Shavette"  # Original preserved

    def test_original_format_preserved(self, registry):
        """Test that original format is preserved in matched.format."""
        record = {
            "author": "test_user",
            "razor": {
                "original": "Gillette Tech",
                "matched": {
                    "brand": "Gillette",
                    "format": "DE",
                },
            },
            "blade": {
                "original": "Feather",
                "matched": {
                    "brand": "Feather",
                    "format": "DE",
                },
            },
        }

        enriched_record = registry.enrich_record(record, "")

        assert enriched_record["razor"]["matched"]["format"] == "DE"
        assert enriched_record["razor"]["enriched"]["format"] == "DE"

    def test_multiple_records_some_applicable(self, registry):
        """Test with multiple records, some applicable, some not."""
        records = [
            {
                "author": "user1",
                "razor": {
                    "matched": {"format": "Shavette"},
                },
                "blade": {
                    "matched": {"format": "AC"},
                },
            },
            {
                "author": "user2",
                "razor": {
                    "matched": {"format": "Shavette (AC)"},
                },
                "blade": {
                    "matched": {"format": "DE"},
                },
            },
            {
                "author": "user3",
                "razor": {
                    "matched": {"format": "Cartridge/Disposable"},
                },
                "blade": {
                    "matched": {"format": "DE"},
                },
            },
        ]

        original_comments = [""] * len(records)
        enriched_records = registry.enrich_records(records, original_comments)

        assert enriched_records[0]["razor"]["enriched"]["format"] == "Shavette (AC)"
        assert enriched_records[1]["razor"]["enriched"]["format"] == "Shavette (AC)"
        assert enriched_records[2]["razor"]["enriched"]["format"] == "Cartridge/Disposable"

    def test_cartridge_disposable_preserved(self, registry):
        """Test that Cartridge/Disposable format is preserved regardless of blade."""
        record = {
            "author": "test_user",
            "razor": {
                "matched": {
                    "format": "Cartridge/Disposable",
                }
            },
            "blade": {
                "matched": {
                    "format": "AC",
                }
            },
        }

        enriched_record = registry.enrich_record(record, "")

        assert enriched_record["razor"]["enriched"]["format"] == "Cartridge/Disposable"
        assert enriched_record["razor"]["matched"]["format"] == "Cartridge/Disposable"

    def test_shavette_de_conversion(self, registry):
        """Test that generic Shavette with DE blade converts to Half DE."""
        record = {
            "author": "test_user",
            "razor": {
                "matched": {
                    "format": "Shavette",
                }
            },
            "blade": {
                "matched": {
                    "format": "DE",
                }
            },
        }

        enriched_record = registry.enrich_record(record, "")

        assert enriched_record["razor"]["enriched"]["format"] == "Shavette (Half DE)"
        assert enriched_record["razor"]["matched"]["format"] == "Shavette"

    def test_metadata_fields_present(self, registry):
        """Test that metadata fields are present in enriched data."""
        record = {
            "author": "test_user",
            "razor": {
                "matched": {
                    "format": "Shavette",
                }
            },
            "blade": {
                "matched": {
                    "format": "AC",
                }
            },
        }

        enriched_record = registry.enrich_record(record, "")

        enriched = enriched_record["razor"]["enriched"]
        assert "_enriched_by" in enriched
        assert enriched["_enriched_by"] == "RazorFormatEnricher"
        assert "_extraction_source" in enriched
        assert enriched["_extraction_source"] == "blade_format_inference"
