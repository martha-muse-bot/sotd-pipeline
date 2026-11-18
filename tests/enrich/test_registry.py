import pytest

from sotd.enrich.blade_enricher import BladeCountEnricher
from sotd.enrich.enricher import BaseEnricher
from sotd.enrich.registry import EnricherRegistry
from sotd.enrich.straight_razor_enricher import StraightRazorEnricher


class MockBladeEnricher(BaseEnricher):
    """Mock blade enricher for testing."""

    @property
    def target_field(self) -> str:
        return "blade"

    def applies_to(self, record):
        return "blade" in record and record["blade"] is not None

    def enrich(self, field_data, original_comment):
        return {
            "use_count": 3,
            "_enriched_by": self.get_enricher_name(),
            "_extraction_source": "user_comment",
        }


class MockRazorEnricher(BaseEnricher):
    """Mock razor enricher for testing."""

    @property
    def target_field(self) -> str:
        return "razor"

    def applies_to(self, record):
        return "razor" in record and record["razor"] is not None

    def enrich(self, field_data, original_comment):
        return {
            "grind": "full_hollow",
            "_enriched_by": self.get_enricher_name(),
            "_extraction_source": "user_comment",
        }


class TestEnricherRegistry:
    """Test cases for EnricherRegistry."""

    @pytest.fixture
    def registry(self):
        """Create an EnricherRegistry instance for testing."""
        return EnricherRegistry()

    def test_register_enricher(self, registry):
        """Test registering an enricher."""
        enricher = BladeCountEnricher()
        registry.register(enricher)

        assert len(registry.get_all_enrichers()) == 1
        assert registry.get_all_enrichers()[0] == enricher

    def test_register_multiple_enrichers(self, registry):
        """Test registering multiple enrichers."""
        blade_enricher = BladeCountEnricher()
        straight_enricher = StraightRazorEnricher()

        registry.register(blade_enricher)
        registry.register(straight_enricher)

        enrichers = registry.get_all_enrichers()
        assert len(enrichers) == 2
        assert blade_enricher in enrichers
        assert straight_enricher in enrichers

    def test_get_enrichers_for_field(self, registry):
        """Test getting enrichers for a specific field."""
        blade_enricher = BladeCountEnricher()
        straight_enricher = StraightRazorEnricher()

        registry.register(blade_enricher)
        registry.register(straight_enricher)

        blade_enrichers = registry.get_enrichers_for_field("blade")
        assert len(blade_enrichers) == 1
        assert blade_enrichers[0] == blade_enricher

        razor_enrichers = registry.get_enrichers_for_field("razor")
        assert len(razor_enrichers) == 1
        assert razor_enrichers[0] == straight_enricher

    def test_get_enrichers_for_nonexistent_field(self, registry):
        """Test getting enrichers for a field that has no enrichers."""
        enrichers = registry.get_enrichers_for_field("nonexistent")
        assert len(enrichers) == 0

    def test_register_duplicate_enricher(self, registry):
        """Test that registering the same enricher twice doesn't create duplicates."""
        enricher = BladeCountEnricher()
        registry.register(enricher)
        registry.register(enricher)

        assert len(registry.get_all_enrichers()) == 2  # Both instances are registered

    def test_enricher_priority_order(self, registry):
        """Test that enrichers are returned in registration order."""
        blade_enricher = BladeCountEnricher()
        straight_enricher = StraightRazorEnricher()

        registry.register(blade_enricher)
        registry.register(straight_enricher)

        enrichers = registry.get_all_enrichers()
        assert enrichers[0] == blade_enricher
        assert enrichers[1] == straight_enricher

    def test_register_invalid_enricher(self):
        """Test that registering an invalid enricher raises an error."""
        registry = EnricherRegistry()

        with pytest.raises(ValueError):
            registry.register("not an enricher")  # type: ignore

    def test_enrich_single_record(self):
        """Test enriching a single record."""
        registry = EnricherRegistry()
        blade_enricher = BladeCountEnricher()
        registry.register(blade_enricher)

        record = {
            "blade": {
                "original": "Feather (3)",
                "normalized": "Feather",
                "matched": {"brand": "Feather", "model": "Hi-Stainless"},
            },
            "razor": {
                "original": "Gillette Super Speed",
                "normalized": "Gillette Super Speed",
                "matched": {"brand": "Gillette", "model": "Super Speed"},
            },
            "blade_extracted": "Feather (3)",
            "razor_extracted": "Gillette Super Speed",
        }
        original_comment = "Feather (3) - great blade!"

        enriched_record = registry.enrich_record(record, original_comment)

        # Check for unified structure: enriched data under product fields
        assert "enriched" in enriched_record["blade"]
        assert enriched_record["blade"]["enriched"]["use_count"] == 3

    def test_enrich_multiple_records(self):
        """Test enriching multiple records."""
        registry = EnricherRegistry()
        blade_enricher = BladeCountEnricher()
        straight_enricher = StraightRazorEnricher()
        registry.register(blade_enricher)
        registry.register(straight_enricher)

        records = [
            {
                "blade": {
                    "original": "Feather (3)",
                    "normalized": "Feather",
                    "matched": {"brand": "Feather", "model": "Hi-Stainless"},
                },
                "razor": {
                    "original": "Gillette Super Speed",
                    "normalized": "Gillette Super Speed",
                    "matched": {"brand": "Gillette", "model": "Super Speed"},
                },
                "blade_extracted": "Feather (3)",
                "razor_extracted": "Gillette Super Speed",
            },
            {
                "blade": {
                    "original": "Astra SP [2]",
                    "normalized": "Astra SP",
                    "matched": {"brand": "Astra", "model": "Superior Platinum"},
                },
                "razor": {
                    "original": "Dovo 6/8 full hollow round point",
                    "normalized": "Dovo 6/8 full hollow round point",
                    "matched": {"brand": "Dovo", "model": "Best Quality", "format": "Straight"},
                },
                "blade_extracted": "Astra SP [2]",
                "razor_extracted": "Dovo 6/8 full hollow round point",
            },
        ]
        original_comments = [
            "Feather (3) - great blade!",
            "Astra SP [2] with Dovo 6/8 full hollow round point",
        ]

        enriched_records = registry.enrich_records(records, original_comments)

        assert len(enriched_records) == 2

        # First record should have blade enrichment
        assert "enriched" in enriched_records[0]["blade"]
        assert enriched_records[0]["blade"]["enriched"]["use_count"] == 3

        # Second record should have both blade and razor enrichment
        assert "enriched" in enriched_records[1]["blade"]
        assert "enriched" in enriched_records[1]["razor"]
        assert enriched_records[1]["blade"]["enriched"]["use_count"] == 2
        assert enriched_records[1]["razor"]["enriched"]["grind"] == "Full Hollow"
        assert enriched_records[1]["razor"]["enriched"]["width"] == "6/8"
        assert enriched_records[1]["razor"]["enriched"]["point"] == "Round"

    def test_enrich_records_length_mismatch(self):
        """Test that enriching records with mismatched lengths raises an error."""
        registry = EnricherRegistry()

        records = [{"blade": {"matched": {"brand": "Feather"}}}]
        original_comments = ["comment 1", "comment 2"]

        with pytest.raises(ValueError):
            registry.enrich_records(records, original_comments)

    def test_enrich_record_enricher_error_handling(self):
        """Test that enricher errors are handled gracefully."""
        registry = EnricherRegistry()

        class FailingEnricher(BaseEnricher):
            @property
            def target_field(self) -> str:
                return "blade"

            def applies_to(self, record):
                return True

            def enrich(self, field_data, original_comment):
                raise Exception("Test error")

        failing_enricher = FailingEnricher()
        registry.register(failing_enricher)

        record = {
            "comment_id": "test123",
            "blade": {
                "original": "Astra SP (3)",
                "normalized": "Astra SP",
                "matched": {"brand": "Astra", "model": "Superior Platinum"},
            },
            "blade_extracted": "Astra SP (3)",
        }
        original_comment = "Using Astra blade"

        # Should not raise exception, should return original record
        result = registry.enrich_record(record, original_comment)
        assert result == record
