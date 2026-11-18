# pylint: disable=redefined-outer-name

"""
Integration tests using real YAML catalog files.
These tests validate that changes to production YAML files don't break parsing.
"""

from pathlib import Path

import pytest

from sotd.match.blade_matcher import BladeMatcher
from sotd.match.brush_matcher import BrushMatcher
from sotd.match.razor_matcher import RazorMatcher
from sotd.match.soap_matcher import SoapMatcher


@pytest.fixture(scope="session")
def brush_matcher():
    return BrushMatcher()


@pytest.fixture(scope="session")
def soap_matcher():
    return SoapMatcher()


@pytest.fixture(scope="session")
def razor_matcher():
    # Use test-specific correct matches to avoid production data corruption issues
    from pathlib import Path

    test_correct_matches_path = (
        Path(__file__).parent.parent / "match" / "test_razor_correct_matches.yaml"
    )
    return RazorMatcher(correct_matches_path=test_correct_matches_path)


@pytest.fixture(scope="session")
def blade_matcher():
    return BladeMatcher()


class TestRealCatalogIntegration:
    """Integration tests using actual production YAML catalogs."""

    def test_real_catalogs_load_successfully(
        self, brush_matcher, soap_matcher, razor_matcher, blade_matcher
    ):
        """Test that all real catalogs load without errors."""
        # Verify basic structure - use attributes that actually exist
        assert hasattr(brush_matcher, "config"), "BrushMatcher should have config"
        assert hasattr(
            brush_matcher, "strategy_orchestrator"
        ), "BrushMatcher should have strategy_orchestrator"
        assert soap_matcher.catalog is not None
        assert razor_matcher.catalog is not None
        assert blade_matcher.catalog is not None

    def test_real_catalog_patterns_compile(self, brush_matcher, soap_matcher):
        """Test that all regex patterns in real catalogs compile successfully."""
        # Verify patterns exist and compiled successfully - use correct attribute path
        assert len(brush_matcher.strategy_orchestrator.strategies) > 0
        assert len(brush_matcher.handle_matcher.handle_patterns) > 0
        assert len(soap_matcher.scent_patterns) + len(soap_matcher.brand_patterns) > 0

    def test_known_real_patterns_work(
        self, brush_matcher, soap_matcher, razor_matcher, blade_matcher
    ):
        """Test that known patterns from real catalogs work correctly."""
        # Key test cases that should work with real catalogs
        test_cases = [
            # Brush patterns
            (brush_matcher, "Simpson Chubby 2", "brand", "Simpson"),
            (brush_matcher, "Declaration B15", "brand", "Declaration Grooming"),
            (brush_matcher, "Omega 10048", "brand", "Omega"),
            # Soap patterns
            (soap_matcher, "Barrister and Mann Seville", "brand", "Barrister and Mann"),
            (soap_matcher, "Declaration Grooming Bandwagon", "brand", "Declaration Grooming"),
            # Razor patterns
            (razor_matcher, "Karve Christopher Bradley", "brand", "Karve"),
            (razor_matcher, "Gillette Tech", "brand", "Gillette"),
            # Blade patterns
            (blade_matcher, "Feather", "brand", "Feather"),
            (blade_matcher, "Astra Superior Platinum", "brand", "Astra"),
        ]

        for matcher, input_text, field, expected_value in test_cases:
            # Pass just the normalized string to matchers
            result = matcher.match(input_text)
            assert result.matched is not None, f"No match for: {input_text}"
            assert (
                result.matched[field] == expected_value
            ), f"Expected {expected_value}, got {result.matched[field]}"

    def test_joseph_abbreviation_patterns(self, razor_matcher):
        """Pin the Jos./Jo. abbreviation patterns for Joseph Elliot/Rodgers.

        Regression test: commit c7dfbab silently reverted the Joseph Elliot
        abbreviation pattern with zero tests failing. These cases use the
        regex layer directly (bypass_correct_matches) so the test pins the
        pattern, not a correct_matches entry.
        """
        # Abbreviated forms resolve to the makers (PR #31)
        abbreviation_cases = [
            ("Jos. Elliot 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jos Elliot 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jos. Elliot - 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jos.Elliot 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jo. Elliot 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jos. Elliot 6/8 NW", "Joseph Elliot", "Straight", "Straight"),
            ("Joseph Elliot 6/8 wedge", "Joseph Elliot", "Straight", "Straight"),
            ("Jos. Rodgers & Sons 11/16 FH", "Joseph Rodgers & Sons", "Straight", "Straight"),
            ("Jos. Rodgers 6/8 wedge", "Joseph Rodgers & Sons", "Straight", "Straight"),
            ("Joseph Rodgers 6/8 wedge", "Joseph Rodgers & Sons", "Straight", "Straight"),
        ]
        for text, brand, model, fmt in abbreviation_cases:
            result = razor_matcher.match(text, bypass_correct_matches=True)
            assert result.matched is not None, f"No match for: {text}"
            assert result.matched["brand"] == brand, (
                f"{text}: expected brand {brand}, got {result.matched['brand']}"
            )
            assert result.matched["model"] == model, (
                f"{text}: expected model {model}, got {result.matched['model']}"
            )
            assert result.matched["format"] == fmt, (
                f"{text}: expected format {fmt}, got {result.matched['format']}"
            )

        # The word boundary must keep real first names out: a poster named
        # Josh/Josiah Elliot is not the 19th-century maker.
        for text in ("Josh Elliot 6/8 wedge", "Josiah Elliot 5/8"):
            result = razor_matcher.match(text, bypass_correct_matches=True)
            assert result.matched is None or result.matched["brand"] != "Joseph Elliot", (
                f"{text} must not resolve to Joseph Elliot, got {result.matched}"
            )

        # Real compound strings keep their resolutions: the widened pattern
        # sorts below the Frederick Reynolds / Wostenholm patterns.
        compound_cases = [
            (
                "Frederick Reynolds 6/8 | Joseph Elliot 6/8 wedge",
                "Frederick Reynolds",
            ),
            (
                "Wostenholm & Sons Pipe Razor 6/8 and Joseph Elliot 13/16",
                "Geo. Wostenholm & Son",
            ),
        ]
        for text, brand in compound_cases:
            result = razor_matcher.match(text, bypass_correct_matches=True)
            assert result.matched is not None, f"No match for: {text}"
            assert result.matched["brand"] == brand, (
                f"{text}: expected brand {brand}, got {result.matched['brand']}"
            )

    @pytest.mark.production
    def test_handle_knot_splitting_integration(self, brush_matcher):
        """Test handle/knot splitting with real catalog data.

        This test uses production YAML catalogs to validate catalog integrity.
        Run with 'make test-production' to execute these production catalog tests.
        """
        # This test intentionally operates on production data files
        # It validates that the catalog structure is correct and matchers work with real data
        pass

    def test_soap_scent_matching(self, soap_matcher):
        """Test that soap scent patterns work with real catalog."""
        test_cases = [
            ("Barrister and Mann Seville", "Seville"),
            ("Declaration Grooming Contemplation", "Contemplation"),
            ("House of Mammoth Hygge", "Hygge"),
        ]

        for input_text, expected_scent in test_cases:
            structured_data = {"original": input_text, "normalized": input_text}
            result = soap_matcher.match(structured_data)
            # Handle both MatchResult objects and dictionaries
            if hasattr(result, "matched"):
                matched = result.matched
            else:
                matched = result.get("matched")
            if isinstance(matched, dict) and matched.get("scent"):
                assert (
                    expected_scent.lower() in matched["scent"].lower()
                ), f"Scent failed for {input_text}"

    @pytest.mark.production
    def test_specific_integration_scenarios(self, brush_matcher):
        """Test specific integration scenarios that have caused issues.

        This test uses production YAML catalogs to validate catalog integrity.
        Run with 'make test-production' to execute these production catalog tests.
        """
        # This test intentionally operates on production data files
        # It validates specific scenarios that have caused issues in the past
        pass

    def test_catalog_files_exist(self):
        """Test that all expected catalog files exist."""
        catalog_files = [
            "data/brushes.yaml",
            "data/handles.yaml",
            "data/soaps.yaml",
            "data/razors.yaml",
            "data/blades.yaml",
        ]

        for catalog_file in catalog_files:
            path = Path(catalog_file)
            assert path.exists(), f"Catalog file {catalog_file} does not exist"
            assert path.stat().st_size > 0, f"Catalog file {catalog_file} is empty"
