from sotd.enrich.enricher import BaseEnricher


class TestEnricher(BaseEnricher):
    """Test implementation of BaseEnricher for testing."""

    @property
    def target_field(self) -> str:
        return "test_field"

    def applies_to(self, record):
        return "test_field" in record and record["test_field"] is not None

    def enrich(self, field_data, original_comment):
        return {
            "test_value": "enriched",
            "_enriched_by": self.get_enricher_name(),
            "_extraction_source": "user_comment",
        }


class TestBaseEnricher:
    """Test cases for the BaseEnricher abstract class."""

    def test_target_field_property(self):
        """Test that target_field property is implemented."""
        enricher = TestEnricher()
        assert enricher.target_field == "test_field"

    def test_applies_to_method(self):
        """Test that applies_to method works correctly."""
        enricher = TestEnricher()

        # Should apply when field exists and is not None
        record = {"test_field": {"brand": "test"}}
        assert enricher.applies_to(record) is True

        # Should not apply when field is None
        record = {"test_field": None}
        assert enricher.applies_to(record) is False

        # Should not apply when field doesn't exist
        record = {"other_field": "test"}
        assert enricher.applies_to(record) is False

    def test_enrich_method(self):
        """Test that enrich method returns expected structure."""
        enricher = TestEnricher()
        field_data = {"brand": "test"}
        original_comment = "test comment"

        result = enricher.enrich(field_data, original_comment)

        assert result is not None
        assert "test_value" in result
        assert result["test_value"] == "enriched"
        assert "_enriched_by" in result
        assert result["_enriched_by"] == "TestEnricher"
        assert "_extraction_source" in result
        assert result["_extraction_source"] == "user_comment"

    def test_get_enricher_name(self):
        """Test that get_enricher_name returns class name."""
        enricher = TestEnricher()
        assert enricher.get_enricher_name() == "TestEnricher"

    def test_base_enricher_is_abstract(self):
        """Test that BaseEnricher is properly abstract."""
        # Check that BaseEnricher has abstract methods
        assert hasattr(BaseEnricher, "__abstractmethods__")
        assert len(BaseEnricher.__abstractmethods__) > 0

        # Verify that target_field, applies_to, and enrich are abstract
        abstract_methods = BaseEnricher.__abstractmethods__
        assert "target_field" in abstract_methods
        assert "applies_to" in abstract_methods
        assert "enrich" in abstract_methods


class TestSourceTrackingMethods:
    """Test cases for the new source tracking methods in BaseEnricher."""

    def test_create_enriched_data_user_only(self):
        """Test _create_enriched_data with user data only."""
        enricher = TestEnricher()
        user_data = {"knot_size_mm": 26, "fiber": "Badger"}
        catalog_data = {}

        result = enricher._create_enriched_data(user_data, catalog_data)

        assert result["knot_size_mm"] == 26
        assert result["fiber"] == "Badger"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "user_comment"

    def test_create_enriched_data_catalog_only(self):
        """Test _create_enriched_data with catalog data only."""
        enricher = TestEnricher()
        user_data = {}
        catalog_data = {"knot_size_mm": 28, "fiber": "Synthetic"}

        result = enricher._create_enriched_data(user_data, catalog_data)

        assert result["knot_size_mm"] == 28
        assert result["fiber"] == "Synthetic"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "catalog_data"

    def test_create_enriched_data_both_sources(self):
        """Test _create_enriched_data with both user and catalog data."""
        enricher = TestEnricher()
        user_data = {"knot_size_mm": 26, "fiber": "Badger"}
        catalog_data = {"knot_size_mm": 28, "fiber": "Synthetic"}

        result = enricher._create_enriched_data(user_data, catalog_data)

        # User data should take precedence
        assert result["knot_size_mm"] == 26
        assert result["fiber"] == "Badger"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "user_comment + catalog_data"

    def test_create_enriched_data_no_data(self):
        """Test _create_enriched_data with no data."""
        enricher = TestEnricher()
        user_data = {}
        catalog_data = {}

        result = enricher._create_enriched_data(user_data, catalog_data)

        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "none"
        # Should not contain any data fields
        assert "knot_size_mm" not in result
        assert "fiber" not in result

    def test_create_enriched_data_user_overrides_catalog(self):
        """Test that user data overrides catalog data."""
        enricher = TestEnricher()
        user_data = {"knot_size_mm": 26}
        catalog_data = {"knot_size_mm": 28, "fiber": "Synthetic"}

        result = enricher._create_enriched_data(user_data, catalog_data)

        # User knot_size should override catalog
        assert result["knot_size_mm"] == 26
        # Catalog fiber should be preserved
        assert result["fiber"] == "Synthetic"
        assert result["_extraction_source"] == "user_comment + catalog_data"

    def test_create_enriched_data_with_none_values(self):
        """Test _create_enriched_data handles None values gracefully."""
        enricher = TestEnricher()
        user_data = {"knot_size_mm": None, "fiber": "Badger"}
        catalog_data = {"knot_size_mm": 28, "fiber": None}

        result = enricher._create_enriched_data(user_data, catalog_data)

        # None values should be handled gracefully
        assert result["knot_size_mm"] == 28  # Catalog value since user is None
        assert result["fiber"] == "Badger"  # User value
        assert result["_extraction_source"] == "user_comment + catalog_data"

    def test_create_single_source_enriched_data(self):
        """Test _create_single_source_enriched_data with user data."""
        enricher = TestEnricher()
        data = {"gap": "0.84", "variant": "OC"}
        source = "user_comment"

        result = enricher._create_single_source_enriched_data(data, source)

        assert result["gap"] == "0.84"
        assert result["variant"] == "OC"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "user_comment"

    def test_create_single_source_enriched_data_catalog_source(self):
        """Test _create_single_source_enriched_data with catalog source."""
        enricher = TestEnricher()
        data = {"plate": "OC"}
        source = "catalog_data"

        result = enricher._create_single_source_enriched_data(data, source)

        assert result["plate"] == "OC"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "catalog_data"

    def test_create_single_source_enriched_data_empty_data(self):
        """Test _create_single_source_enriched_data with empty data."""
        enricher = TestEnricher()
        data = {}
        source = "user_comment"

        result = enricher._create_single_source_enriched_data(data, source)

        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "user_comment"
        # Should not contain any data fields
        assert "gap" not in result
        assert "variant" not in result

    def test_create_single_source_enriched_data_none_values(self):
        """Test _create_single_source_enriched_data handles None values."""
        enricher = TestEnricher()
        data = {"gap": None, "variant": "OC"}
        source = "user_comment"

        result = enricher._create_single_source_enriched_data(data, source)

        assert result["gap"] is None
        assert result["variant"] == "OC"
        assert result["_enriched_by"] == "TestEnricher"
        assert result["_extraction_source"] == "user_comment"
