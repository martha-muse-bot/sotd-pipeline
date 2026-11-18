#!/usr/bin/env python3
"""Tests for @ symbol normalization in extract_normalization.py"""

from sotd.utils.extract_normalization import strip_social_media_handles


class TestStripSocialMediaHandles:
    """Test cases for strip_social_media_handles function."""

    def test_strip_at_beginning_basic(self):
        """Test stripping @ symbols from the beginning of strings."""
        assert strip_social_media_handles("@hendrixclassics Lavender") == "hendrixclassics Lavender"
        assert (
            strip_social_media_handles("@aylsworth.razors Kopperkant Plus")
            == "aylsworth.razors Kopperkant Plus"
        )
        assert strip_social_media_handles("@karveshavingco") == "karveshavingco"
        assert strip_social_media_handles("@murphyandmcneil") == "murphyandmcneil"

    def test_strip_at_beginning_with_underscores(self):
        """Test stripping @ symbols with underscores and dots."""
        assert strip_social_media_handles("@turtleship_shave_co") == "turtleship_shave_co"
        assert strip_social_media_handles("@wetshavingproducts") == "wetshavingproducts"
        assert strip_social_media_handles("@biberman1 26mm") == "biberman1 26mm"
        assert (
            strip_social_media_handles("@likegrandpa / @karveshavingco")
            == "likegrandpa / @karveshavingco"
        )

    def test_preserve_at_middle(self):
        """Test that @ symbols in the middle are preserved."""
        assert (
            strip_social_media_handles("Vikings Blade Crusader Adjustable (Set @ #4)")
            == "Vikings Blade Crusader Adjustable (Set @ #4)"
        )
        assert strip_social_media_handles("H2 1962 Gillette Slim @9") == "H2 1962 Gillette Slim @9"
        assert (
            strip_social_media_handles("Zeppelin V2 Ti @seygusrazor")
            == "Zeppelin V2 Ti @seygusrazor"
        )
        assert (
            strip_social_media_handles('Colibri "hummingbird" @homelikeshaving')
            == 'Colibri "hummingbird" @homelikeshaving'
        )

    def test_preserve_at_end(self):
        """Test that @ symbols at the end are preserved."""
        assert strip_social_media_handles("Product name @") == "Product name @"
        assert strip_social_media_handles("Some product @handle") == "Some product @handle"

    def test_no_at_symbol(self):
        """Test strings without @ symbols are unchanged."""
        assert (
            strip_social_media_handles("Hendrix Classics Lavender") == "Hendrix Classics Lavender"
        )
        assert (
            strip_social_media_handles("Aylsworth Kopperkant Plus") == "Aylsworth Kopperkant Plus"
        )
        assert strip_social_media_handles("Karve") == "Karve"
        assert strip_social_media_handles("Murphy & McNeil") == "Murphy & McNeil"

    def test_empty_string(self):
        """Test empty string handling."""
        assert strip_social_media_handles("") == ""

    def test_whitespace_only(self):
        """Test whitespace-only string handling."""
        assert strip_social_media_handles("   ") == "   "

    def test_none_input(self):
        """Test None input handling."""
        # Type ignore for test - we're testing None handling
        assert strip_social_media_handles(None) is None  # type: ignore

    def test_multiple_at_beginning(self):
        """Test multiple @ symbols at the beginning."""
        assert (
            strip_social_media_handles("@@@hendrixclassics Lavender") == "hendrixclassics Lavender"
        )
        assert strip_social_media_handles("@ @ @karveshavingco") == "karveshavingco"

    def test_at_with_spaces(self):
        """Test @ symbols with various spacing."""
        assert (
            strip_social_media_handles("@ hendrixclassics Lavender") == "hendrixclassics Lavender"
        )
        assert (
            strip_social_media_handles("@  hendrixclassics  Lavender") == "hendrixclassics Lavender"
        )
        assert (
            strip_social_media_handles("@hendrixclassics  Lavender") == "hendrixclassics Lavender"
        )

    def test_complex_handle_patterns(self):
        """Test complex social media handle patterns."""
        assert strip_social_media_handles("@user.name123 Product") == "user.name123 Product"
        assert strip_social_media_handles("@user_name Product") == "user_name Product"
        assert strip_social_media_handles("@user-name Product") == "user-name Product"
        assert strip_social_media_handles("@user.name_123 Product") == "user.name_123 Product"

    def test_real_world_examples(self):
        """Test real-world examples from the data."""
        # From 2025-08.json
        assert (
            strip_social_media_handles("@aylsworth.razors Kopperkant Plus")
            == "aylsworth.razors Kopperkant Plus"
        )
        assert strip_social_media_handles("@hendrixclassics Lavender") == "hendrixclassics Lavender"

        # From 2020-09.json
        assert strip_social_media_handles("@karveshavingco") == "karveshavingco"
        assert strip_social_media_handles("@murphyandmcneil") == "murphyandmcneil"
        assert strip_social_media_handles("@turtleship_shave_co") == "turtleship_shave_co"
        assert strip_social_media_handles("@wetshavingproducts") == "wetshavingproducts"
        assert strip_social_media_handles("@biberman1 26mm") == "biberman1 26mm"

        # From 2020-07.json
        assert (
            strip_social_media_handles("@likegrandpa / @karveshavingco")
            == "likegrandpa / @karveshavingco"
        )
        assert strip_social_media_handles("@likegrandpa / @apshaveco") == "likegrandpa / @apshaveco"
        assert strip_social_media_handles("@likegrandpa") == "likegrandpa"
        assert strip_social_media_handles("@teton.shaves") == "teton.shaves"
        assert strip_social_media_handles("@stirlingsoap") == "stirlingsoap"
        assert strip_social_media_handles("@spearheadshaving") == "spearheadshaving"

    def test_edge_cases(self):
        """Test edge cases and boundary conditions."""
        # Single @ symbol
        assert strip_social_media_handles("@") == "@"

        # @ symbol with no handle
        assert strip_social_media_handles("@ ") == ""

        # @ symbol with only handle, no product
        assert strip_social_media_handles("@handle") == "handle"

        # @ symbol with handle and empty product
        assert strip_social_media_handles("@handle ") == "handle "

        # Very long handle
        assert (
            strip_social_media_handles("@very_long_handle_name_with_underscores_and_dots Product")
            == "very_long_handle_name_with_underscores_and_dots Product"
        )
