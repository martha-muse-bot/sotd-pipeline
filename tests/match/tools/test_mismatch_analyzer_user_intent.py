#!/usr/bin/env python3
"""
Tests for user intent bolding feature in mismatch analyzer.

Tests that the mismatch analyzer correctly bolds the primary component
based on user_intent in brush matches.
"""

from unittest.mock import Mock  # noqa: F401

import pytest  # noqa: F401

from sotd.match.tools.analyzers.mismatch_analyzer import MismatchAnalyzer


class TestMismatchAnalyzerUserIntent:
    """Test user intent bolding in mismatch analyzer."""

    def test_get_matched_text_brush_handle_primary(self):
        """Test that handle_primary user intent bolds the handle component."""
        analyzer = MismatchAnalyzer()

        # Composite brush with handle_primary user intent
        matched = {
            "user_intent": "handle_primary",
            "handle": {"brand": "Rad Dinosaur", "model": "Creation"},
            "knot": {"brand": "AP Shave Co", "model": "G5C"},
        }

        result = analyzer._get_matched_text("brush", matched)

        # Should bold the handle component
        expected = "**Rad Dinosaur Creation** w/ AP Shave Co G5C"
        assert result == expected

    def test_get_matched_text_brush_knot_primary(self):
        """Test that knot_primary user intent bolds the knot component."""
        analyzer = MismatchAnalyzer()

        # Composite brush with knot_primary user intent
        matched = {
            "user_intent": "knot_primary",
            "handle": {"brand": "Rad Dinosaur", "model": "Creation"},
            "knot": {"brand": "AP Shave Co", "model": "G5C"},
        }

        result = analyzer._get_matched_text("brush", matched)

        # Should bold the knot component
        expected = "Rad Dinosaur Creation w/ **AP Shave Co G5C**"
        assert result == expected

    def test_get_matched_text_brush_no_user_intent(self):
        """Test that no user intent shows components without bolding."""
        analyzer = MismatchAnalyzer()

        # Composite brush without user intent
        matched = {
            "handle": {"brand": "Rad Dinosaur", "model": "Creation"},
            "knot": {"brand": "AP Shave Co", "model": "G5C"},
        }

        result = analyzer._get_matched_text("brush", matched)

        # Should show without bolding
        expected = "Rad Dinosaur Creation w/ AP Shave Co G5C"
        assert result == expected

    def test_get_matched_text_brush_simple_brush(self):
        """Test that simple brushes are not affected by user intent bolding."""
        analyzer = MismatchAnalyzer()

        # Simple brush (not composite)
        matched = {"brand": "Simpson", "model": "Chubby 2"}

        result = analyzer._get_matched_text("brush", matched)

        # Should show simple format without bolding
        expected = "Simpson Chubby 2"
        assert result == expected

    def test_get_matched_text_brush_unknown_user_intent(self):
        """Test that unknown user intent values show without bolding."""
        analyzer = MismatchAnalyzer()

        # Composite brush with unknown user intent
        matched = {
            "user_intent": "unknown_value",
            "handle": {"brand": "Rad Dinosaur", "model": "Creation"},
            "knot": {"brand": "AP Shave Co", "model": "G5C"},
        }

        result = analyzer._get_matched_text("brush", matched)

        # Should show without bolding for unknown user intent
        expected = "Rad Dinosaur Creation w/ AP Shave Co G5C"
        assert result == expected

    def test_get_matched_text_brush_empty_components(self):
        """Test that empty components are handled gracefully."""
        analyzer = MismatchAnalyzer()

        # Composite brush with empty components
        matched = {
            "user_intent": "handle_primary",
            "handle": {"brand": "", "model": ""},
            "knot": {"brand": "", "model": ""},
        }

        result = analyzer._get_matched_text("brush", matched)

        # Should handle empty components gracefully
        expected = "** ** w/"
        assert result == expected

    def test_get_matched_text_brush_missing_components(self):
        """Test that missing components are handled gracefully."""
        analyzer = MismatchAnalyzer()

        # Composite brush with missing components
        matched = {"user_intent": "handle_primary", "handle": {}, "knot": {}}

        result = analyzer._get_matched_text("brush", matched)

        # Should handle missing components gracefully
        expected = ""
        assert result == expected
