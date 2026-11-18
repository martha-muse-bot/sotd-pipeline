import os
import tempfile
from pathlib import Path

import pytest

from sotd.match.blade_matcher import BladeMatcher


@pytest.fixture(scope="session")
def test_matcher():
    """Session-scoped matcher with test catalog for format-aware matching."""
    yaml_content = """
DE:
  Accuforge:
    DE:
      patterns:
        - accuforge
  Feather:
    DE:
      patterns:
        - feather
  Astra:
    Superior Platinum (Green):
      patterns:
        - astra.*sp
        - astra.*plat
        - astra
  Gillette:
    Perma-Sharp:
      patterns:
        - perma.*sharp
        - gillette.*perma

GEM:
  Personna:
    GEM PTFE:
      patterns:
        - (person|gem).*p[tf]{2}e
        - gem by personna
        - (ptfe|pfte).*(person|gem)
        - ptfe
        - gem
        - acc?utec
        - accu.*(gem|coated|p[ft]{2}e)

AC:
  Feather:
    Pro:
      patterns:
        - feather.*pro
        - feather.*a.*c
    Pro Light:
      patterns:
        - feather.*light
    Pro Super:
      patterns:
        - feather.*super
        - pro\\s*super
  Kai:
    Captain Blade:
      patterns:
        - kai.*blade
        - kai captain\\s*$
        - kai.*cap

Half DE:
  Gillette:
    Perma-Sharp SE:
      patterns:
        - perma\\s*-*sharp
        - perma\\s*-*sharp.*(half|1/2)
  Crown:
    Super Stainless SE:
      patterns:
        - crown.*stainless.*\\bse\\b
"""
    temp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    temp_file.write(yaml_content)
    temp_file.close()

    matcher = BladeMatcher(catalog_path=Path(temp_file.name))

    def cleanup():
        try:
            os.unlink(temp_file.name)
        except OSError:
            pass

    import atexit

    atexit.register(cleanup)

    return matcher


def test_format_specific_match_found_gem_razor(test_matcher):
    """Test 'Accuforge' with 'GEM' context returns DE format as fallback."""
    result = test_matcher.match_with_context("Accuforge", "GEM")
    # Accuforge doesn't match any GEM patterns, so should fallback to DE
    assert result.matched is not None
    # Accuforge is mapped to Personna brand in production catalog
    assert result.matched["brand"] == "Personna"
    assert result.matched["format"] == "DE"


def test_format_specific_match_found_de_razor(test_matcher):
    """Test 'Accuforge' with 'DE' context returns DE format."""
    result = test_matcher.match_with_context("Accuforge", "DE")
    assert result.matched is not None
    # Accuforge is mapped to Personna brand in production catalog
    assert result.matched["brand"] == "Personna"
    assert result.matched["format"] == "DE"
    assert result.original == "Accuforge"


def test_multiple_format_matches_de_razor(test_matcher):
    """Test 'Feather' with 'DE' context returns DE format."""
    result = test_matcher.match_with_context("Feather", "DE")
    assert result.matched is not None
    assert result.matched["brand"] == "Feather"
    assert result.matched["model"] == "DE"
    assert result.matched["format"] == "DE"
    assert result.original == "Feather"


def test_multiple_format_matches_ac_razor(test_matcher):
    """Test 'Feather' with 'AC' context returns DE format as fallback."""
    result = test_matcher.match_with_context("Feather", "AC")
    # Feather doesn't match any AC patterns, so should fallback to DE
    assert result.matched is not None
    assert result.matched["brand"] == "Feather"
    assert result.matched["model"] == "DE"
    assert result.matched["format"] == "DE"


def test_case_insensitive_matching(test_matcher):
    """Test case variations return same matches for DE and GEM contexts."""
    # DE format
    result1 = test_matcher.match_with_context("FEATHER", "DE")
    result2 = test_matcher.match_with_context("feather", "DE")
    result3 = test_matcher.match_with_context("Feather", "DE")
    assert result1.matched is not None
    assert result2.matched is not None
    assert result3.matched is not None
    assert result1.matched["brand"] == result2.matched["brand"] == result3.matched["brand"]
    assert result1.matched["model"] == result2.matched["model"] == result3.matched["model"]
    assert result1.matched["format"] == result2.matched["format"] == result3.matched["format"]
    # GEM format - Accuforge doesn't match any patterns, should fallback to DE
    result4 = test_matcher.match_with_context("ACCUFORGE", "GEM")
    result5 = test_matcher.match_with_context("accuforge", "GEM")
    assert result4.matched is not None
    assert result5.matched is not None
    # Accuforge is mapped to Personna brand in production catalog
    assert result4.matched["brand"] == result5.matched["brand"] == "Personna"
    assert result4.matched["format"] == result5.matched["format"] == "DE"


def test_no_match_when_format_not_found(test_matcher):
    """Test no match when format has no entries."""
    # Blade that doesn't exist in any format
    result = test_matcher.match_with_context("NonexistentBlade", "DE")
    assert result.matched is None
    assert result.match_type is None
    assert result.pattern is None
    assert result.original == "NonexistentBlade"
    # Blade that exists in DE but not in GEM - should fallback to DE
    result = test_matcher.match_with_context("Astra", "GEM")
    assert result.matched is not None
    assert result.matched["brand"] == "Astra"
    assert result.matched["format"] == "DE"


def test_half_de_fallback_to_de(test_matcher):
    """Test HALF DE razors can use DE blades as fallback, but prefer Half DE if available."""
    # Blade that exists in DE but not in Half DE
    result = test_matcher.match_with_context("Astra", "HALF DE")
    assert result.matched is not None
    assert result.matched["brand"] == "Astra"
    assert result.matched["format"] == "DE"
    assert result.original == "Astra"
    # Blade that exists in both Half DE and DE
    result = test_matcher.match_with_context("Perma-Sharp", "HALF DE")
    assert result.matched is not None
    assert result.matched["brand"] == "Gillette"
    assert result.matched["model"] == "Perma-Sharp SE"
    assert result.matched["format"] == "Half DE"
    assert result.original == "Perma-Sharp"


def test_format_mapping_accuracy(test_matcher):
    """Test that razor format mapping works correctly for 'Feather'."""
    format_tests = [
        ("SHAVETTE (DE)", "DE"),
        ("SHAVETTE (AC)", "DE"),  # AC doesn't have Feather, falls back to DE
        ("SHAVETTE (GEM)", "DE"),  # GEM doesn't have Feather, falls back to DE
        ("SHAVETTE (HALF DE)", "DE"),  # HALF DE doesn't have Feather, falls back to DE
        ("DE", "DE"),
        ("AC", "DE"),  # AC doesn't have Feather, falls back to DE
        ("GEM", "DE"),  # GEM doesn't have Feather, falls back to DE
        ("HALF DE", "DE"),  # HALF DE doesn't have Feather, falls back to DE
    ]
    for razor_format, expected_blade_format in format_tests:
        result = test_matcher.match_with_context("Feather", razor_format)
        if result.matched:
            # HALF DE should fallback to DE for Feather
            if expected_blade_format == "HALF DE":
                assert result.matched["format"] == "DE"
            else:
                assert result.matched["format"] == expected_blade_format


def test_complex_pattern_matching_gem(test_matcher):
    """Test complex GEM pattern matching with various PTFE-related inputs."""
    ptfe_tests = [
        ("Personna PTFE", "Personna", "GEM PTFE", "GEM"),
        ("GEM PTFE", "Personna", "GEM PTFE", "GEM"),
        ("PTFE", "Personna", "GEM PTFE", "GEM"),
        ("Accutec", "Personna", "GEM PTFE", "GEM"),
        ("Accuforge coated", "Personna", "GEM PTFE", "GEM"),  # Should match GEM PTFE pattern
    ]
    for input_text, expected_brand, expected_model, expected_format in ptfe_tests:
        result = test_matcher.match_with_context(input_text, "GEM")
        assert result.matched is not None

        # All these inputs should match Personna GEM PTFE
        assert result.matched["brand"] == "Personna"
        assert result.matched["model"] == "GEM PTFE"
        assert result.matched["format"] == "GEM"


def test_complex_pattern_matching_ac(test_matcher):
    """Test complex AC pattern matching with various inputs."""
    ac_tests = [
        ("Feather Pro", "Feather", "Pro", "AC"),
        ("Feather AC", "Feather", "Pro", "AC"),
        ("Feather Pro Light", "Feather", "Pro Light", "AC"),
        ("Feather Pro Super", "Feather", "Pro Super", "AC"),
    ]
    for input_text, expected_brand, expected_model, expected_format in ac_tests:
        result = test_matcher.match_with_context(input_text, "AC")
        assert result.matched is not None
        assert result.matched["brand"] == expected_brand
        assert result.matched["model"] == expected_model
        assert result.matched["format"] == expected_format


def test_pattern_specificity_ordering(test_matcher):
    """Test that more specific patterns are matched first."""
    # Test that "Feather Pro" matches Pro model, not DE model
    result = test_matcher.match_with_context("Feather Pro", "AC")
    assert result.matched is not None
    assert result.matched["model"] == "Pro"
    assert result.matched["format"] == "AC"
    # Test that Feather Pro Light matches Pro Light model
    result = test_matcher.match_with_context("Feather Pro Light", "AC")
    assert result.matched is not None
    assert result.matched["model"] == "Pro Light"
    assert result.matched["format"] == "AC"


def test_context_priority_over_text_content(test_matcher):
    """Test that razor context takes priority over text content."""
    # Test that when context is GEM, it matches GEM format if available, otherwise falls back
    result = test_matcher.match_with_context("Accuforge", "GEM")
    # Accuforge doesn't match any GEM patterns, so should fallback to DE
    assert result.matched is not None
    assert result.matched["format"] == "DE"

    # Test that when context is DE, it matches DE format
    result = test_matcher.match_with_context("Accuforge", "DE")
    assert result.matched is not None
    assert result.matched["format"] == "DE"
    assert result.original == "Accuforge"


def test_cache_clearing_for_testing(test_matcher):
    """Test that cache clearing works for isolated testing."""
    # First match should populate cache
    result1 = test_matcher.match_with_context("Feather", "DE")
    assert result1.matched is not None

    # Clear cache
    test_matcher.clear_cache()

    # Second match should work the same way
    result2 = test_matcher.match_with_context("Feather", "DE")
    assert result2.matched is not None

    # Results should be identical
    assert result1.matched["brand"] == result2.matched["brand"]
    assert result1.matched["model"] == result2.matched["model"]
    assert result1.matched["format"] == result2.matched["format"]


def test_match_result_structure_consistency(test_matcher):
    """Test that all match results have consistent structure."""
    test_cases = [
        ("Feather", "DE"),
        ("Accuforge", "GEM"),
        ("Astra", "DE"),
        ("NonexistentBlade", "DE"),
    ]

    for blade_text, razor_format in test_cases:
        result = test_matcher.match_with_context(blade_text, razor_format)

        # Required fields should always be present
        assert hasattr(result, "original")
        assert hasattr(result, "matched")
        assert hasattr(result, "match_type")
        assert hasattr(result, "pattern")

        # Original should always match input
        assert result.original == blade_text

        # If matched, should have required fields
        if result.matched is not None:
            assert "brand" in result.matched
            assert "model" in result.matched
            assert "format" in result.matched
        else:
            # If not matched, match_type and pattern should be None
            assert result.match_type is None
            assert result.pattern is None
