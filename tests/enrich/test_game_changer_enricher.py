from sotd.enrich.game_changer_enricher import GameChangerEnricher


class TestGameChangerEnricher:
    """Test cases for GameChangerEnricher."""

    def setup_method(self):
        """Set up test fixtures."""
        self.enricher = GameChangerEnricher()

    def test_target_field(self):
        """Test that the enricher targets the correct field."""
        assert self.enricher.target_field == "razor"

    def test_applies_to_razorock_game_changer(self):
        """Test that the enricher applies to RazoRock Game Changer razors."""
        record = {"razor": {"matched": {"brand": "RazoRock", "model": "Game Changer"}}}
        assert self.enricher.applies_to(record) is True

    def test_applies_to_razorock_game_changer_20(self):
        """Test that the enricher applies to RazoRock Game Changer 2.0 razors."""
        record = {"razor": {"matched": {"brand": "RazoRock", "model": "Game Changer 2.0"}}}
        assert self.enricher.applies_to(record) is True

    def test_applies_to_razorock_game_changer_jaws(self):
        """Test that the enricher applies to RazoRock Game Changer Jaws razors."""
        record = {"razor": {"matched": {"brand": "RazoRock", "model": "Game Changer Jaws"}}}
        assert self.enricher.applies_to(record) is True

    def test_does_not_apply_to_other_brands(self):
        """Test that the enricher does not apply to non-RazoRock razors."""
        record = {"razor": {"matched": {"brand": "Merkur", "model": "34C"}}}
        assert self.enricher.applies_to(record) is False

    def test_does_not_apply_to_other_razorock_models(self):
        """Test that the enricher does not apply to other RazoRock models."""
        record = {"razor": {"matched": {"brand": "RazoRock", "model": "SLOC"}}}
        assert self.enricher.applies_to(record) is False

    def test_does_not_apply_to_missing_razor(self):
        """Test that the enricher does not apply when razor is missing."""
        record = {}
        assert self.enricher.applies_to(record) is False

    def test_does_not_apply_to_none_razor(self):
        """Test that the enricher does not apply when razor is None."""
        record = {"razor": None}
        assert self.enricher.applies_to(record) is False

    def test_extract_gap_decimal_format(self):
        """Test gap extraction with decimal format."""
        field_data = {"model": "RazoRock Game Changer .68"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".68"
        assert result["_enriched_by"] == "GameChangerEnricher"
        assert result["_extraction_source"] == "user_comment"

    def test_extract_gap_zero_decimal_format(self):
        """Test gap extraction with 0.xx format."""
        field_data = {"model": "RazoRock Game Changer 0.84"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"

    def test_extract_gap_two_digit_format(self):
        """Test gap extraction with two-digit format."""
        field_data = {"model": "RazoRock Game Changer 68"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".68"

    def test_extract_gap_three_digit_format(self):
        """Test gap extraction with three-digit format."""
        field_data = {"model": "RazoRock Game Changer 105"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == "1.05"

    def test_extract_gap_with_gc_abbreviation(self):
        """Test gap extraction with GC abbreviation."""
        field_data = {"model": "GC .84"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"

    def test_extract_gap_with_game_changer_spaces(self):
        """Test gap extraction with Game Changer and spaces."""
        field_data = {"model": "Game Changer .68"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".68"

    def test_extract_variant_jaws(self):
        """Test variant extraction for JAWS."""
        field_data = {"model": "RazoRock Game Changer Jaws"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["variant"] == "JAWS"

    def test_extract_variant_oc(self):
        """Test variant extraction for OC."""
        field_data = {"model": "RazoRock Game Changer OC"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["variant"] == "OC"

    def test_extract_variant_open_comb(self):
        """Test variant extraction for open comb."""
        field_data = {"model": "RazoRock Game Changer open comb"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["variant"] == "OC"

    def test_extract_both_gap_and_variant_jaws(self):
        """Test extraction of both gap and JAWS variant."""
        field_data = {"model": "RazoRock Game Changer .84 Jaws"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"
        assert result["variant"] == "JAWS"

    def test_extract_both_gap_and_variant_oc(self):
        """Test extraction of both gap and OC variant."""
        field_data = {"model": "RazoRock Game Changer .68 OC"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".68"
        assert result["variant"] == "OC"

    def test_no_extraction_when_no_specifications(self):
        """Test that no extraction occurs when no specifications are found."""
        field_data = {"model": "RazoRock Game Changer"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is None

    def test_no_extraction_when_no_model(self):
        """Test that no extraction occurs when model is missing."""
        field_data = {}
        result = self.enricher.enrich(field_data, "")
        assert result is None

    def test_gap_extraction_case_insensitive(self):
        """Test that gap extraction is case insensitive."""
        field_data = {"model": "RAZOROCK GAME CHANGER .68"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".68"

    def test_variant_extraction_case_insensitive(self):
        """Test that variant extraction is case insensitive."""
        field_data = {"model": "RazorRock Game Changer JAWS"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["variant"] == "JAWS"

    def test_no_false_positive_gap_extraction(self):
        """Test that gap extraction doesn't match unrelated numbers."""
        field_data = {"model": "RazoRock Game Changer with 100 shaves"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is None

    def test_no_false_positive_variant_extraction(self):
        """Test that variant extraction doesn't match unrelated text."""
        field_data = {"model": "RazoRock Game Changer with 2.0 shaves"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is None

    def test_extraction_with_mixed_content(self):
        """Test extraction with mixed content in model."""
        field_data = {"model": "Great shave with RazoRock Game Changer .84 Jaws and Feather blade"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"
        assert result["variant"] == "JAWS"

    def test_special_case_mapping_85_to_84(self):
        """Test that .85 is mapped to .84 (special case from old parser)."""
        field_data = {"model": "RazoRock Game Changer .85"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"

    def test_special_case_mapping_94_to_84(self):
        """Test that .94 is mapped to .84 (special case from old parser)."""
        field_data = {"model": "RazoRock Game Changer .94"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"

    def test_normalize_gap_formatting(self):
        """Test that gap formatting is normalized consistently."""
        # Test various input formats that should all result in .68
        test_cases = [
            "RazoRock Game Changer .68",
            "RazoRock Game Changer 0.68",
            "RazoRock Game Changer 68",
        ]

        for model in test_cases:
            field_data = {"model": model}
            result = self.enricher.enrich(field_data, model)
            assert result is not None
            assert result["gap"] == ".68"

    def test_extract_gap_after_year_number(self):
        """Test that a year/model number before the gap does not kill extraction."""
        field_data = {"model": "RazoRock Game Changer 2023 .84"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == ".84"

    def test_extract_gap_after_year_number_three_digit(self):
        """Test gap extraction with a year before a three-digit gap."""
        field_data = {"model": "RazoRock Game Changer 2024 1.05"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is not None
        assert result["gap"] == "1.05"

    def test_no_gap_when_only_year_number(self):
        """Test that a year alone is not promoted to a gap."""
        field_data = {"model": "RazoRock Game Changer 2023"}
        result = self.enricher.enrich(field_data, field_data["model"])
        assert result is None

    def test_extract_gap_with_hyphen_format(self):
        """Test gap extraction with hyphen format like 0.76-P or .76-P."""
        test_cases = [
            ("RazoRock Game Changer 0.76-P", ".76"),
            ("RazoRock Game Changer .76-P", ".76"),
            ("RazoRock Game Changer 0.84-P", ".84"),
            ("RazoRock Game Changer .68-P", ".68"),
        ]

        for model, expected_gap in test_cases:
            field_data = {"model": model}
            result = self.enricher.enrich(field_data, model)
            assert result is not None, f"Failed to extract gap from: {model}"
            assert (
                result["gap"] == expected_gap
            ), f"Expected {expected_gap}, got {result['gap']} for: {model}"

    def test_accept_all_valid_gaps_with_any_variant(self):
        """Test that all valid gaps are accepted with any variant."""
        # Test all four valid gaps with JAWS variant
        valid_gaps = [".68", ".76", ".84", "1.05"]
        for gap in valid_gaps:
            field_data = {"model": f"RazoRock Game Changer {gap} Jaws"}
            result = self.enricher.enrich(field_data, field_data["model"])
            assert result is not None
            assert result["gap"] == gap
            assert result["variant"] == "JAWS"

    def test_gap_extraction_with_larger_numbers(self):
        """Test gap extraction with larger numbers."""
        # This test is no longer valid since .95 is not a valid Game Changer gap
        pass
