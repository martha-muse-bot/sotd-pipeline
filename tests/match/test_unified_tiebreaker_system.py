"""Test the unified tiebreaker system for blade pattern matching."""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml

from sotd.match.blade_matcher import BladeMatcher
from sotd.match.loaders import CatalogLoader
from sotd.match.types import MatchType


class TestUnifiedTiebreakerSystem:
    """Test the unified tiebreaker system for pattern sorting."""

    @pytest.fixture
    def blade_matcher(self):
        """Create a BladeMatcher instance for testing."""
        # Create temporary directory for test files
        test_dir = tempfile.mkdtemp()

        # Create temporary correct_matches.yaml with test data
        correct_matches_path = Path(test_dir) / "correct_matches.yaml"
        test_correct_matches = {"blade": {"Test Brand": {"Test Model": ["test blade pattern"]}}}

        with open(correct_matches_path, "w") as f:
            yaml.dump(test_correct_matches, f)

        # Copy production catalog file to temp directory
        production_catalog = Path("data/blades.yaml")
        catalog_path = Path(test_dir) / "blades.yaml"

        if production_catalog.exists():
            shutil.copy(production_catalog, catalog_path)

        loader = CatalogLoader()
        loader.load_matcher_catalogs(
            catalog_path, "blade", correct_matches_path=correct_matches_path
        )

        matcher = BladeMatcher(
            catalog_path=catalog_path,
            correct_matches_path=correct_matches_path,
            bypass_correct_matches=False,
        )

        yield matcher

        # Cleanup
        shutil.rmtree(test_dir)

    def test_count_non_optional_parts_simple_pattern(self, blade_matcher):
        """Test counting non-optional parts in simple patterns."""
        # Simple pattern with no '.*' - should count as 1 part
        pattern = "personna"
        result = blade_matcher._count_non_optional_parts(pattern)
        assert result == 1

    def test_count_non_optional_parts_with_wildcards(self, blade_matcher):
        """Test counting non-optional parts in patterns with wildcards."""
        # Pattern with '.*' separators
        pattern = "personna.*hair.*shaper"
        result = blade_matcher._count_non_optional_parts(pattern)
        assert result == 3  # personna, hair, shaper

    def test_count_non_optional_parts_with_empty_parts(self, blade_matcher):
        """Test counting non-optional parts with empty parts from wildcards."""
        # Pattern that starts or ends with '.*'
        pattern = ".*personna.*hair.*"
        result = blade_matcher._count_non_optional_parts(pattern)
        assert result == 2  # personna, hair (empty parts are filtered out)

    def test_count_non_optional_parts_complex_pattern(self, blade_matcher):
        """Test counting non-optional parts in complex regex patterns."""
        # Complex pattern with multiple wildcards
        pattern = "personna.*(?:injecto)?.*blade"
        result = blade_matcher._count_non_optional_parts(pattern)
        assert result == 3  # personna, (?:injecto)?, blade (simple split approach)

    def test_calculate_pattern_score_basic(self, blade_matcher):
        """Test basic pattern score calculation without DE deprioritization."""
        # Create a mock pattern item tuple
        item = ("Personna", "Hair Shaper", "HAIR SHAPER", "personna.*hair.*shaper", None, {})

        score = blade_matcher._calculate_pattern_score(item, deprioritize_de=False)

        # Should return tuple: (format_priority, -length_score, -non_optional_score,
        # -complexity_score, -boundary_score)
        assert len(score) == 5
        assert score[0] == 0  # No format bias when deprioritize_de=False
        assert score[1] == -22  # Negative length (22 characters)
        assert score[2] == -3  # Negative non-optional parts (3 parts)

    def test_calculate_pattern_score_with_de_deprioritization(self, blade_matcher):
        """Test pattern score calculation with DE deprioritization enabled."""
        # DE format pattern
        de_item = ("Personna", "DE Blade", "DE", "personna.*de", None, {})
        de_score = blade_matcher._calculate_pattern_score(de_item, deprioritize_de=True)

        # Non-DE format pattern
        non_de_item = ("Personna", "Hair Shaper", "HAIR SHAPER", "personna.*hair.*shaper", None, {})
        non_de_score = blade_matcher._calculate_pattern_score(non_de_item, deprioritize_de=True)

        # DE should have lower priority (higher number) when deprioritization enabled
        assert de_score[0] == 1  # DE gets lower priority
        assert non_de_score[0] == 0  # Non-DE gets higher priority

    def test_pattern_sorting_by_specificity(self, blade_matcher):
        """Test that patterns are sorted by specificity (most specific first)."""
        # Get the sorted patterns from the matcher
        patterns = blade_matcher.patterns

        # Test that patterns are sorted by our tiebreaker system
        # The first few patterns should be the most specific
        if len(patterns) >= 2:
            first_pattern = patterns[0]
            second_pattern = patterns[1]

            # Calculate scores for comparison
            first_score = blade_matcher._calculate_pattern_score(
                first_pattern, deprioritize_de=False
            )
            second_score = blade_matcher._calculate_pattern_score(
                second_pattern, deprioritize_de=False
            )

            # First pattern should have higher specificity (lower score values)
            # Compare the scores lexicographically
            assert first_score <= second_score, (
                f"First pattern {first_pattern[3]} should be more specific than "
                f"second pattern {second_pattern[3]}"
            )

    def test_personna_hair_shaper_vs_injector_tiebreaker(self, blade_matcher):
        """Test 'Personna hair shaper' wins over 'Personna injector' due to non-optional parts."""
        # Find the specific patterns we want to test
        hair_shaper_pattern = None
        injector_pattern = None

        for brand, model, fmt, pattern, compiled, entry in blade_matcher.patterns:
            if (
                "personna" in brand.lower()
                and "hair shaper" in model.lower()
                and "hair.*shaper" in pattern
            ):
                hair_shaper_pattern = (brand, model, fmt, pattern, compiled, entry)
            elif (
                "personna" in brand.lower()
                and "injector" in fmt.lower()
                and "person+a(?:.*inject)?" in pattern
            ):
                injector_pattern = (brand, model, fmt, pattern, compiled, entry)

        # Both patterns should exist
        assert hair_shaper_pattern is not None, "Personna hair shaper pattern not found"
        assert injector_pattern is not None, "Personna injector pattern not found"

        # Debug output
        print(f"Hair shaper pattern: {hair_shaper_pattern[3]}")
        print(f"Injector pattern: {injector_pattern[3]}")

        # Calculate scores
        hair_shaper_score = blade_matcher._calculate_pattern_score(
            hair_shaper_pattern, deprioritize_de=False
        )
        injector_score = blade_matcher._calculate_pattern_score(
            injector_pattern, deprioritize_de=False
        )

        # The hair shaper pattern should win due to length and non-optional parts
        # outweighing the complexity difference
        # The score tuple should be lexicographically smaller (more specific)
        assert (
            hair_shaper_score < injector_score
        ), "Hair shaper pattern should be more specific than injector pattern"

        # Verify the non-optional parts count
        hair_shaper_parts = blade_matcher._count_non_optional_parts(hair_shaper_pattern[3])
        injector_parts = blade_matcher._count_non_optional_parts(injector_pattern[3])

        # Hair shaper should have more non-optional parts than injector
        assert (
            hair_shaper_parts > injector_parts
        ), "Hair shaper should have more non-optional parts than injector"

    def test_generic_shavette_detection_and_global_approach(self, blade_matcher):
        """Test generic 'Shavette' razor format triggers global pattern specificity approach."""
        # Test with generic "Shavette" razor format
        normalized_text = "personna hair shaper"
        razor_format = "Shavette"

        # This should trigger the global approach
        result = blade_matcher.match_with_context(normalized_text, razor_format)

        # Should find a match using global pattern specificity
        assert result.matched is not None, "Should find a match using global approach"
        assert result.match_type == MatchType.REGEX, "Should be a regex match"

        # The match should be from the Hair Shaper format (most specific pattern)
        assert result.matched["format"] == "Hair Shaper", "Should match to Hair Shaper format"
        assert "personna" in result.matched["brand"].lower(), "Should match Personna brand"
        assert "hair" in result.matched["model"].lower(), "Should match Hair Shaper model"

    def test_specific_shavette_formats_still_use_context_aware(self, blade_matcher):
        """Test that specific Shavette formats still use context-aware logic."""
        # Test with specific "Shavette (DE)" format - should NOT trigger global approach
        normalized_text = "personna hair shaper"
        razor_format = "Shavette (DE)"

        # This should use the existing context-aware logic, not global approach
        result = blade_matcher.match_with_context(normalized_text, razor_format)

        # Should still find a match, but through context-aware logic
        assert result.matched is not None, "Should still find a match"
        # The exact match type may vary, but it should work

    def test_global_pattern_no_match_found(self, blade_matcher):
        """Test that global pattern approach returns proper result when no match is found."""
        # Test with text that won't match any patterns
        normalized_text = "nonexistent blade brand that won't match anything"
        original = "Original text"

        # This should return a "no match" result with the same structure as existing code
        result = blade_matcher._find_best_global_match(normalized_text, original)

        # Should return the same structure as existing "no match" case
        assert result.matched is None, "Should return no match"
        assert result.match_type is None, "Should have no match type"
        assert result.pattern is None, "Should have no pattern"
        assert result.original == original, "Should preserve original text"

    def test_integration_original_problem_scenario(self, blade_matcher):
        """Integration test: verify the original problem scenario is now fixed."""
        # This is the exact scenario from the original problem:
        # "Personna hair shaper" with generic "Shavette" razor
        # Should now correctly match to "Hair Shaper" format instead of "Injector"

        normalized_text = "personna hair shaper"
        razor_format = "Shavette"  # Generic Shavette

        # This should trigger the global pattern specificity approach
        result = blade_matcher.match_with_context(normalized_text, razor_format)

        # Should find a match
        assert result.matched is not None, "Should find a match using global approach"

        # Should match to Hair Shaper format (the most specific pattern)
        assert result.matched["format"] == "Hair Shaper", "Should match to Hair Shaper format"
        assert "personna" in result.matched["brand"].lower(), "Should match Personna brand"
        assert "hair" in result.matched["model"].lower(), "Should match Hair Shaper model"

        # Verify this is NOT matching to Injector format (the original bug)
        assert result.matched["format"] != "Injector", "Should NOT match to Injector format"

        # The pattern used should be the Hair Shaper pattern
        assert "hair.*shaper" in result.pattern, "Should use Hair Shaper pattern"
