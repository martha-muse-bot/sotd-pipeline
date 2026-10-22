#!/usr/bin/env python3
"""Tests for soap extraction utilities."""

from sotd.utils.soap_extraction import (
    detect_soap_mashup,
    extract_soap_sample_via_normalization,
    normalize_soap_suffixes,
)


class TestDetectSoapMashup:
    """Test mashup detection (v1: mashup, mash up, mash-up only)."""

    def test_empty_or_none(self):
        assert detect_soap_mashup("") is False
        assert detect_soap_mashup("   ") is False

    def test_mashup_word(self):
        assert detect_soap_mashup("soap mashup") is True
        assert detect_soap_mashup("Sample mashup") is True
        assert detect_soap_mashup("MASHUP") is True
        assert detect_soap_mashup("  mashup  ") is True

    def test_mash_up_space(self):
        assert detect_soap_mashup("mash up") is True
        assert detect_soap_mashup("soap mash up") is True

    def test_mash_hyphen_up(self):
        assert detect_soap_mashup("mash-up") is True
        assert detect_soap_mashup("soap mash-up") is True

    def test_no_mashup(self):
        assert detect_soap_mashup("Barrister and Mann - Seville") is False
        assert detect_soap_mashup("sample") is False
        assert detect_soap_mashup("tri-mix") is False


class TestNormalizeSoapSuffixes:
    """Test soap suffix normalization functionality."""

    def test_empty_input(self):
        """Test handling of empty input."""
        assert normalize_soap_suffixes("") == ""
        # Type ignore for test - we're testing None handling
        assert normalize_soap_suffixes(None) is None  # type: ignore

    def test_no_suffixes(self):
        """Test text with no suffixes to normalize."""
        assert (
            normalize_soap_suffixes("summer break soaps - steady") == "summer break soaps - steady"
        )
        assert normalize_soap_suffixes("barrister and mann - roam") == "barrister and mann - roam"

    def test_product_type_suffixes(self):
        """Test removal of product type suffixes."""
        # - soap suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - soap")
            == "summer break soaps - steady"
        )
        # Note: Standalone "soap" at end is NOT removed to avoid breaking brand names like "Soap Commander"
        # Only "- soap" (with dash) is removed
        assert (
            normalize_soap_suffixes("summer break soaps steady soap")
            == "summer break soaps steady soap"
        )

        # - cream suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - cream")
            == "summer break soaps - steady"
        )

        # - puck suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - puck")
            == "summer break soaps - steady"
        )

        # - croap suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - croap")
            == "summer break soaps - steady"
        )
        # croap without dash (should also be stripped, like puck)
        assert (
            normalize_soap_suffixes("summer break soaps - steady croap")
            == "summer break soaps - steady"
        )

        # - shaving soap suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - shaving soap")
            == "summer break soaps - steady"
        )

        # - shave soap suffix
        assert (
            normalize_soap_suffixes("summer break soaps - steady - shave soap")
            == "summer break soaps - steady"
        )

        # standalone soap - NOT removed to avoid breaking brand names like "Soap Commander"
        # Only "- soap" (with dash) is removed
        assert (
            normalize_soap_suffixes("summer break soaps steady soap")
            == "summer break soaps steady soap"
        )

        # cream without dash (should be stripped, like puck and croap)
        assert (
            normalize_soap_suffixes("summer break soaps - steady cream")
            == "summer break soaps - steady"
        )

        # gel with and without dash
        assert (
            normalize_soap_suffixes("summer break soaps - steady - gel")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady gel")
            == "summer break soaps - steady"
        )

        # foam with and without dash
        assert (
            normalize_soap_suffixes("summer break soaps - steady - foam")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady foam")
            == "summer break soaps - steady"
        )

    def test_all_specified_formats_stripped(self):
        """Test that all specified formats are stripped with dash."""
        test_cases = [
            ("some brand - some scent - cream", "some brand - some scent"),
            ("some brand - some scent (vegan)", "some brand - some scent"),
            ("some brand - some scent - shaving soap", "some brand - some scent"),
            ("some brand - some scent - puck", "some brand - some scent"),
            ("some brand - some scent - stick", "some brand - some scent"),
            ("some brand - some scent - croap", "some brand - some scent"),
            ("some brand - some scent - shave soap", "some brand - some scent"),
            ("some brand - some scent - gel", "some brand - some scent"),
            ("some brand - some scent - foam", "some brand - some scent"),
        ]
        for inp, expected in test_cases:
            result = normalize_soap_suffixes(inp)
            assert result == expected, f"Failed for '{inp}': got '{result}', expected '{expected}'"

    def test_formats_stripped_without_dash(self):
        """Test that formats (except soap) are stripped without dash."""
        test_cases = [
            ("some brand - some scent cream", "some brand - some scent"),
            ("some brand - some scent gel", "some brand - some scent"),
            ("some brand - some scent foam", "some brand - some scent"),
            ("some brand - some scent puck", "some brand - some scent"),
            ("some brand - some scent stick", "some brand - some scent"),
            ("some brand - some scent croap", "some brand - some scent"),
            # Soap should NOT be stripped without dash
            ("some brand - some scent soap", "some brand - some scent soap"),
            ("Try This Soap", "Try This Soap"),
        ]
        for inp, expected in test_cases:
            result = normalize_soap_suffixes(inp)
            assert result == expected, f"Failed for '{inp}': got '{result}', expected '{expected}'"

    def test_shave_shaving_patterns_all_formats(self):
        """Test shave/shaving patterns for all formats."""
        formats = ["cream", "gel", "foam", "puck", "stick", "croap", "soap"]
        for fmt in formats:
            # With dash
            inp = f"some brand - some scent - shave {fmt}"
            result = normalize_soap_suffixes(inp)
            assert result == "some brand - some scent", f"Failed for '{inp}': got '{result}'"

            inp = f"some brand - some scent - shaving {fmt}"
            result = normalize_soap_suffixes(inp)
            assert result == "some brand - some scent", f"Failed for '{inp}': got '{result}'"

            # Without dash
            inp = f"some brand - some scent shave {fmt}"
            result = normalize_soap_suffixes(inp)
            assert result == "some brand - some scent", f"Failed for '{inp}': got '{result}'"

            inp = f"some brand - some scent shaving {fmt}"
            result = normalize_soap_suffixes(inp)
            assert result == "some brand - some scent", f"Failed for '{inp}': got '{result}'"

    def test_container_type_suffixes(self):
        """Test removal of container type suffixes."""
        # - stick suffix
        assert normalize_soap_suffixes("arko - shave stick") == "arko"
        assert normalize_soap_suffixes("la toja stick") == "la toja"

        # - shave stick suffix
        assert normalize_soap_suffixes("la toja shave stick") == "la toja"

        # - tube suffix
        assert normalize_soap_suffixes("proraso green tube") == "proraso green"

        # - hard suffix
        assert normalize_soap_suffixes("tabac - hard") == "tabac"

    def test_preserves_version_indicators(self):
        """Test that version indicators are preserved (not normalized)."""
        # These should NOT be normalized as they distinguish different products
        assert (
            normalize_soap_suffixes("barrister and mann - roam 2") == "barrister and mann - roam 2"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (v2)")
            == "barrister and mann - roam (v2)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (2024a)")
            == "barrister and mann - roam (2024a)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (og)")
            == "barrister and mann - roam (og)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (original)")
            == "barrister and mann - roam (original)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (1)")
            == "barrister and mann - roam (1)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (one)")
            == "barrister and mann - roam (one)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam (i)")
            == "barrister and mann - roam (i)"
        )
        assert (
            normalize_soap_suffixes("barrister and mann - roam ii")
            == "barrister and mann - roam ii"
        )

    def test_case_insensitive(self):
        """Test that normalization is case insensitive but preserves original case."""
        assert (
            normalize_soap_suffixes("SUMMER BREAK SOAPS - STEADY - SOAP")
            == "SUMMER BREAK SOAPS - STEADY"
        )
        assert (
            normalize_soap_suffixes("Summer Break Soaps - Steady - Soap")
            == "Summer Break Soaps - Steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady - PUCK")
            == "summer break soaps - steady"
        )

    def test_size_indicators(self):
        """Test removal of size indicators in parentheses."""
        # oz indicators
        assert (
            normalize_soap_suffixes("catie's bubbles - le marche du rasage (2oz)")
            == "catie's bubbles - le marche du rasage"
        )
        assert (
            normalize_soap_suffixes(
                "catie's bubbles - le marche du rasage (big ass og 8oz pour - french style)"
            )
            == "catie's bubbles - le marche du rasage"
        )

    def test_base_formula_indicators(self):
        """Test removal of base/formula indicators in parentheses."""
        # premium base
        assert (
            normalize_soap_suffixes("catie's bubbles - blugère (premium base)")
            == "catie's bubbles - blugère"
        )

        # luxury base
        assert (
            normalize_soap_suffixes("catie's bubbles - maggard meet exclusive (luxury base)")
            == "catie's bubbles - maggard meet exclusive"
        )

        # omnibus base
        assert (
            normalize_soap_suffixes("barrister and mann - adagio - omnibus")
            == "barrister and mann - adagio"
        )

        # milksteak
        assert (
            normalize_soap_suffixes("declaration grooming - puzzle (milksteak)")
            == "declaration grooming - puzzle"
        )

        # tusk
        assert (
            normalize_soap_suffixes("house of mammoth - kryptonite (tusk)")
            == "house of mammoth - kryptonite"
        )

        # professional
        assert (
            normalize_soap_suffixes("cella - buongiorno al sandalo - (professional)")
            == "cella - buongiorno al sandalo"
        )

        # tallow base
        assert (
            normalize_soap_suffixes("mäurer & wirtz - tabac (tallow base)")
            == "mäurer & wirtz - tabac"
        )

        # tallow formulation
        assert (
            normalize_soap_suffixes("mauer and wirtz - tabac (tallow formulation)")
            == "mauer and wirtz - tabac"
        )

        # vegan
        assert (
            normalize_soap_suffixes("southern witchcrafts - druantia - (vegan)")
            == "southern witchcrafts - druantia"
        )

    def test_whitespace_cleanup(self):
        """Test cleanup of extra whitespace and dashes."""
        # Remove trailing dash
        assert (
            normalize_soap_suffixes("summer break soaps - steady -")
            == "summer break soaps - steady"
        )

        # Normalize whitespace
        assert (
            normalize_soap_suffixes("summer  break   soaps   -   steady")
            == "summer break soaps - steady"
        )

        # Strip leading/trailing whitespace
        assert (
            normalize_soap_suffixes("  summer break soaps - steady  ")
            == "summer break soaps - steady"
        )

    def test_multiple_suffixes(self):
        """Test handling of multiple suffixes (should remove all)."""
        # Multiple product type suffixes
        assert (
            normalize_soap_suffixes("summer break soaps - steady - soap - puck")
            == "summer break soaps - steady"
        )

        # Product type + container type
        assert (
            normalize_soap_suffixes("summer break soaps - steady - soap - stick")
            == "summer break soaps - steady"
        )

        # Product type + size
        assert (
            normalize_soap_suffixes("summer break soaps - steady - soap (2oz)")
            == "summer break soaps - steady"
        )

    def test_sample_indicators(self):
        """Test removal of sample indicators."""
        # (sample) in parentheses
        assert (
            normalize_soap_suffixes("summer break soaps - steady (sample)")
            == "summer break soaps - steady"
        )
        # (smush) in parentheses
        assert (
            normalize_soap_suffixes("summer break soaps - steady (smush)")
            == "summer break soaps - steady"
        )
        # - sample at end
        assert (
            normalize_soap_suffixes("summer break soaps - steady - sample")
            == "summer break soaps - steady"
        )
        # - smush at end
        assert (
            normalize_soap_suffixes("summer break soaps - steady - smush")
            == "summer break soaps - steady"
        )
        # sample at end (without dash)
        assert (
            normalize_soap_suffixes("summer break soaps - steady sample")
            == "summer break soaps - steady"
        )
        # smush at end (without dash)
        assert (
            normalize_soap_suffixes("summer break soaps - steady smush")
            == "summer break soaps - steady"
        )

    def test_real_world_examples(self):
        """Test with real examples from soap.yaml."""
        # Summer Break Soaps examples
        assert (
            normalize_soap_suffixes("summer break soaps - steady - soap (sample -- thanks!!)")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady - puck")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady - croap")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady - shaving soap")
            == "summer break soaps - steady"
        )
        assert (
            normalize_soap_suffixes("summer break soaps - steady - shave soap")
            == "summer break soaps - steady"
        )

        # Cella examples
        assert normalize_soap_suffixes("cella - crema da barba") == "cella"
        assert (
            normalize_soap_suffixes("cella - milano crema da barba - (est. 1899)")
            == "cella - milano"
        )
        assert (
            normalize_soap_suffixes("cella - buongiorno al sandalo - (professional)")
            == "cella - buongiorno al sandalo"
        )

        # Tabac examples
        assert (
            normalize_soap_suffixes("mäurer & wirtz - tabac original (tallow)")
            == "mäurer & wirtz - tabac original"
        )
        assert normalize_soap_suffixes("tabac - shave stick") == "tabac"
        assert normalize_soap_suffixes("tabac - hard") == "tabac"


class TestExtractSoapSampleViaNormalization:
    """Test soap sample extraction functionality."""

    def test_empty_input(self):
        """Test handling of empty input."""
        result = extract_soap_sample_via_normalization("", "")
        assert result == (None, None, None, None)

        result = extract_soap_sample_via_normalization("text", "")
        assert result == (None, None, None, None)

        result = extract_soap_sample_via_normalization("", "text")
        assert result == (None, None, None, None)

    def test_no_sample_indicators(self):
        """Test text with no sample indicators."""
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady", "summer break soaps - steady"
        )
        assert result == (None, None, None, "")

    def test_basic_sample_patterns(self):
        """Test basic sample pattern extraction."""
        # (sample)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(sample)")

        # (tester)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (tester)", "summer break soaps - steady"
        )
        assert result == ("tester", None, None, "(tester)")

        # (samp) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (samp)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(samp)")

        # (smush) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(smush)")

    def test_numbered_sample_patterns(self):
        """Test numbered sample pattern extraction."""
        # (sample #23)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample #23)", "summer break soaps - steady"
        )
        assert result == ("sample", 23, None, "(sample #23)")

        # (sample 5 of 10)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample 5 of 10)", "summer break soaps - steady"
        )
        assert result == ("sample", 5, 10, "(sample 5 of 10)")

        # (sample 3/15)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample 3/15)", "summer break soaps - steady"
        )
        assert result == ("sample", 3, 15, "(sample 3/15)")

        # (smush #23) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush #23)", "summer break soaps - steady"
        )
        assert result == ("sample", 23, None, "(smush #23)")

        # (smush 5 of 10) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush 5 of 10)", "summer break soaps - steady"
        )
        assert result == ("sample", 5, 10, "(smush 5 of 10)")

        # (smush 3/15) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush 3/15)", "summer break soaps - steady"
        )
        assert result == ("sample", 3, 15, "(smush 3/15)")

    def test_trailing_sample_patterns(self):
        """Test trailing sample pattern extraction."""
        # - sample at end
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady - sample", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "- sample")

        # - tester at end
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady - tester", "summer break soaps - steady"
        )
        assert result == ("tester", None, None, "- tester")

        # - smush at end - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady - smush", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "- smush")

        # smush at end (without dash) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady smush", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "smush")

    def test_loose_sample_patterns(self):
        """Test loose sample pattern extraction with whitespace variations."""
        # ( sample ) with spaces
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady ( sample )", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "( sample )")

        # (tester) with spaces
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady ( tester )", "summer break soaps - steady"
        )
        assert result == ("tester", None, None, "( tester )")

        # ( smush ) with spaces - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady ( smush )", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "( smush )")

    def test_gratitude_sample_patterns(self):
        """Test sample patterns with gratitude expressions."""
        # (sample -- thanks!!)
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample -- thanks!!)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(sample -- thanks!!)")

        # (smush -- thanks!!) - should normalize to sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush -- thanks!!)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(smush -- thanks!!)")

    def test_case_insensitive(self):
        """Test that sample extraction is case insensitive."""
        # SAMPLE
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (SAMPLE)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(SAMPLE)")

        # Sample
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (Sample)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(Sample)")

        # SMUSH
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (SMUSH)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(SMUSH)")

        # Smush
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (Smush)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(Smush)")

    def test_real_world_examples(self):
        """Test with real examples from soap.yaml."""
        # Summer Break Soaps examples
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady - soap (sample -- thanks!!)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "- soap (sample -- thanks!!)")

        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (sample)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(sample)")

        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady - sample", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "- sample")

        # smush example
        result = extract_soap_sample_via_normalization(
            "summer break soaps - steady (smush)", "summer break soaps - steady"
        )
        assert result == ("sample", None, None, "(smush)")

    def test_normalized_text_not_found(self):
        """Test when normalized text is not found in original."""
        result = extract_soap_sample_via_normalization(
            "completely different text", "summer break soaps - steady"
        )
        assert result == (None, None, None, None)

    def test_embedded_samples_in_parenthetical_same_original_and_normalized(self):
        """Detect sample usage when 'samples' stays in both original and normalized.

        Real case: mashup of sized samples kept as product text, e.g.
        'Stirling VarenBury (combined Varen and Glastonbury 1oz samples)'.
        """
        text = "Stirling VarenBury (combined Varen and Glastonbury 1oz samples)"
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"
        assert result[1] is None
        assert result[2] is None
        assert result[3] == ""

    def test_embedded_samples_in_parenthetical_as_remainder(self):
        """Detect sample when parenthetical describing samples is the remainder."""
        result = extract_soap_sample_via_normalization(
            "Stirling VarenBury (combined Varen and Glastonbury 1oz samples)",
            "Stirling VarenBury",
        )
        assert result[0] == "sample"
        assert result[3] == "(combined Varen and Glastonbury 1oz samples)"

    def test_sample_mashup_product_name_not_treated_as_sample_usage(self):
        """Catalog scent names like 'Sample Mashup' alone are not sample usage."""
        text = "Mama Bear Sample Mashup"
        result = extract_soap_sample_via_normalization(text, text)
        assert result == (None, None, None, "")

    def test_mid_string_smush_from_user(self):
        """Mid-string 'smush from u/...' is sample usage (Oct 2026 real case)."""
        text = "a smush from u/Impressive_Donut114"
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"
        assert result[1] is None
        assert result[2] is None

    def test_smush_with_trailing_format_in_remainder(self):
        """Smush stripped for matching but remainder still has format suffix.

        Real case: 'Mystery Smush Croap' → normalized without Smush/Croap,
        remainder 'Smush Croap' must still count as sample usage.
        """
        result = extract_soap_sample_via_normalization(
            "u/solongamerica Mystery Smush Croap",
            "u/solongamerica Mystery",
        )
        assert result[0] == "sample"
        assert result[3] == "Smush Croap"

    def test_named_smush_product_phrase_is_sample_usage(self):
        """Named smushes (user mixes) count as sample/smush usage."""
        text = "u/AntwonPeachFuzz - Nonsensical Smush of Gloom and Despair"
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"

    def test_mid_string_sample_usage_phrases(self):
        """Clear mid-string sample usage phrases without relying on trailing/parens."""
        text = "a sample from u/Someone"
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"

    def test_trailing_sample_with_period(self):
        """Trailing 'sample.' must count even when norm keeps '... sample' (period stripped)."""
        result = extract_soap_sample_via_normalization(
            "House of Mammoth - Indigo sample.",
            "House of Mammoth - Indigo sample",
        )
        assert result[0] == "sample"

        result = extract_soap_sample_via_normalization(
            "MDC - Vetyver sample.",
            "MDC - Vetyver sample",
        )
        assert result[0] == "sample"

        result = extract_soap_sample_via_normalization(
            "Stirling Sandpiper Sample .",
            "Stirling Sandpiper Sample",
        )
        assert result[0] == "sample"

    def test_sample_before_location_dash(self):
        """'Product Sample - Location' is sample usage (SOTD location suffix)."""
        for text in (
            "Stirling Black Cherry Sample - Arkansas",
            'Barrister & Mann "Pencil Pusher" Sample - New York',
            "Martin de Candre Absynthe Sample - France",
        ):
            result = extract_soap_sample_via_normalization(text, text)
            assert result[0] == "sample", text

    def test_last_of_the_sample(self):
        text = "Henri et Victoria Cognac and Cuban Cigars - last of the sample :("
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"

    def test_sampler_parenthetical_and_trailing(self):
        result = extract_soap_sample_via_normalization(
            "Henri et Victoria Lime (sampler)",
            "Henri et Victoria Lime",
        )
        assert result[0] == "sample"

        text = "Stirling Island Man Sampler"
        result = extract_soap_sample_via_normalization(text, text)
        assert result[0] == "sample"

    def test_sample_mashup_still_not_usage(self):
        """Catalog/product 'Sample Mash Up' names remain non-usage."""
        for text in (
            "Stirling Sample Mash Up",
            "Mama Bear's Soap - Sample Mash Up",
            "Stirling Sample Mash Up - Arkansas",
            "Mama Bears Sample Mix (Nag Champa/Spice/Vetiver)",
        ):
            result = extract_soap_sample_via_normalization(text, text)
            assert result[0] is None, text
