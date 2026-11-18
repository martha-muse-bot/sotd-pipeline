#!/usr/bin/env python3
"""Integration tests for @ symbol normalization in the complete pipeline."""

from sotd.utils.extract_normalization import normalize_for_matching


class TestAtSymbolNormalizationIntegration:
    """Test @ symbol normalization in the complete normalization pipeline."""

    def test_soap_normalization_with_at_symbols(self):
        """Test soap normalization with @ symbols."""
        # Test cases from real data
        test_cases = [
            ("@hendrixclassics Lavender", "hendrixclassics Lavender"),
            ("@karveshavingco", "karveshavingco"),
            ("@murphyandmcneil", "murphyandmcneil"),
            ("@turtleship_shave_co", "turtleship_shave_co"),
            ("@wetshavingproducts", "wetshavingproducts"),
            ("@biberman1 26mm", "biberman1 26mm"),
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(input_text, field="soap")
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    def test_razor_normalization_with_at_symbols(self):
        """Test razor normalization with @ symbols."""
        # Test cases from real data
        test_cases = [
            ("@aylsworth.razors Kopperkant Plus", "aylsworth.razors Kopperkant Plus"),
            ("@karveshavingco", "karveshavingco"),
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(input_text, field="razor")
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    def test_preserve_at_symbols_in_middle(self):
        """Test that @ symbols in the middle are preserved."""
        # Test cases from real data
        test_cases = [
            (
                "Vikings Blade Crusader Adjustable (Set @ #4)",
                "Vikings Blade Crusader Adjustable (Set @ #4)",
            ),
            ("H2 1962 Gillette Slim @9", "H2 1962 Gillette Slim @9"),
            ("Zeppelin V2 Ti @seygusrazor", "Zeppelin V2 Ti @seygusrazor"),
            ('Colibri "hummingbird" @homelikeshaving', 'Colibri "hummingbird" @homelikeshaving'),
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(input_text, field="razor")
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    def test_complex_at_symbol_cases(self):
        """Test complex @ symbol cases with other normalization."""
        # Test cases that combine @ symbols with other patterns
        test_cases = [
            ("@hendrixclassics Lavender (sample)", "hendrixclassics Lavender"),
            ("@karveshavingco - sample", "karveshavingco"),  # Keep handle, strip sample suffix
            (
                "@murphyandmcneil *bold*",
                "murphyandmcneil bold",
            ),  # Keep handle, asterisks removed
            ("@aylsworth.razors Kopperkant Plus (x3)", "aylsworth.razors Kopperkant Plus"),
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(input_text, field="soap")
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    def test_no_at_symbols_unchanged(self):
        """Test that strings without @ symbols are unchanged."""
        # Test cases without @ symbols
        test_cases = [
            "Hendrix Classics Lavender",
            "Aylsworth Kopperkant Plus",
            "Karve",
            "Murphy & McNeil",
            "Vikings Blade Crusader Adjustable",
        ]

        for input_text in test_cases:
            result = normalize_for_matching(input_text, field="soap")
            assert (
                result == input_text
            ), f"Failed for '{input_text}': expected unchanged, got '{result}'"

    def test_edge_cases_in_pipeline(self):
        """Test edge cases in the complete pipeline."""
        # Edge cases
        test_cases = [
            ("@", "@"),  # Single @ symbol
            ("@ ", "@"),  # @ with space - the space is stripped but @ remains
            ("", ""),  # Empty string
            ("   ", ""),  # Whitespace only - gets stripped by final cleanup
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(input_text, field="soap")
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"

    def test_competition_tags_with_at_symbols(self):
        """Test that competition tags work with @ symbols."""
        # Test with competition tags
        competition_tags = {"strip_tags": ["SAMPLE", "TESTER"], "preserve_tags": []}

        test_cases = [
            ("@hendrixclassics Lavender $SAMPLE", "hendrixclassics Lavender"),
            ("@karveshavingco $TESTER", "karveshavingco"),
            ("@murphyandmcneil $SAMPLE $TESTER", "murphyandmcneil"),
        ]

        for input_text, expected in test_cases:
            result = normalize_for_matching(
                input_text, competition_tags=competition_tags, field="soap"
            )
            assert (
                result == expected
            ), f"Failed for '{input_text}': expected '{expected}', got '{result}'"
