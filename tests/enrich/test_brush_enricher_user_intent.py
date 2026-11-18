"""Tests for user intent detection in BrushEnricher."""

import re
from unittest.mock import patch

import pytest

from sotd.enrich.brush_enricher import BrushEnricher


class TestBrushEnricherUserIntent:
    """Test user intent detection functionality in BrushEnricher."""

    @pytest.fixture
    def brush_enricher(self):
        """Create BrushEnricher instance for testing."""
        return BrushEnricher()

    @pytest.fixture
    def mock_handle_data(self):
        """Mock handle data for testing - using realistic structure from match phase."""
        return {
            "brand": "Declaration",
            "model": "B2",
            "source_text": "Declaration B2 in Zenith B2 Boar",
            "_matched_by": "HandleMatcher",
            "_pattern": "declaration.*b2",
        }

    @pytest.fixture
    def mock_knot_data(self):
        """Mock knot data for testing - using realistic structure from match phase."""
        return {
            "brand": "Zenith",
            "model": "B2",
            "fiber": "Boar",
            "knot_size_mm": 26,
            "source_text": "Declaration B2 in Zenith B2 Boar",
            "_matched_by": "KnotMatcher",
            "_pattern": "zenith.*b2",
        }

    @pytest.fixture
    def mock_brush_string(self):
        """Mock brush string for testing - using realistic brush text."""
        return "Declaration B2 in Zenith B2 Boar"

    def test_detect_user_intent_handle_primary(
        self, brush_enricher, mock_brush_string, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when handle pattern appears before knot pattern."""
        # Mock pattern loading
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile("declaration.*b2", re.IGNORECASE)],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile("zenith.*b2", re.IGNORECASE)],
            ),
        ):

            intent = brush_enricher._detect_user_intent(
                mock_brush_string, mock_handle_data, mock_knot_data
            )
            assert intent == "handle_primary"

    def test_detect_user_intent_knot_primary(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when knot text appears before handle text."""
        brush_string = "Zenith B2 Boar in Declaration B2"

        # Update mock data to include source_text fields
        handle_data = {**mock_handle_data, "source_text": "Declaration B2"}
        knot_data = {**mock_knot_data, "source_text": "Zenith B2 Boar"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent == "knot_primary"

    def test_detect_user_intent_equal_positions(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when both patterns match at same position."""
        brush_string = "Declaration Zenith B2"

        # Mock pattern loading with patterns that would match at same position
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile("declaration", re.IGNORECASE)],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile("zenith", re.IGNORECASE)],
            ),
        ):

            intent = brush_enricher._detect_user_intent(
                brush_string, mock_handle_data, mock_knot_data
            )
            # In this case, "declaration" matches at position 0, "zenith" matches at position 10
            # Since declaration comes first, it should be handle_primary
            assert intent == "handle_primary"

    def test_detect_user_intent_actual_equal_positions(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when both source_text values are identical."""
        brush_string = "Declaration"

        # Update mock data to have identical source_text values
        handle_data = {**mock_handle_data, "source_text": "Declaration"}
        knot_data = {**mock_knot_data, "source_text": "Declaration"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        # Both source_text values are identical, so should default to handle_primary
        assert intent == "handle_primary"

    def test_detect_user_intent_missing_handle_patterns(
        self, brush_enricher, mock_brush_string, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when handle source_text is missing."""
        # Update mock data to have missing source_text for handle
        handle_data = {**mock_handle_data}
        handle_data.pop("source_text", None)  # Remove source_text if it exists
        knot_data = {**mock_knot_data, "source_text": "Zenith B2 Boar"}

        intent = brush_enricher._detect_user_intent(mock_brush_string, handle_data, knot_data)
        # Should default to handle_primary when source_text is missing
        assert intent == "handle_primary"

    def test_detect_user_intent_missing_knot_patterns(
        self, brush_enricher, mock_brush_string, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection when knot source_text is missing."""
        # Update mock data to have missing source_text for knot
        handle_data = {**mock_handle_data, "source_text": "Declaration B2"}
        knot_data = {**mock_knot_data}
        knot_data.pop("source_text", None)  # Remove source_text if it exists

        intent = brush_enricher._detect_user_intent(mock_brush_string, handle_data, knot_data)
        # Should default to handle_primary when source_text is missing
        assert intent == "handle_primary"

    def test_detect_user_intent_empty_brush_string(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection with empty brush string."""
        brush_string = ""

        with pytest.raises(ValueError, match="Missing brush_string for user intent detection"):
            brush_enricher._detect_user_intent(brush_string, mock_handle_data, mock_knot_data)

    def test_detect_user_intent_none_handle_data(
        self, brush_enricher, mock_brush_string, mock_knot_data
    ):
        """Test user intent detection with None handle data."""
        with pytest.raises(
            ValueError, match="Missing or invalid handle_data for user intent detection"
        ):
            brush_enricher._detect_user_intent(mock_brush_string, None, mock_knot_data)

    def test_detect_user_intent_none_knot_data(
        self, brush_enricher, mock_brush_string, mock_handle_data
    ):
        """Test user intent detection with None knot data."""
        with pytest.raises(
            ValueError, match="Missing or invalid knot_data for user intent detection"
        ):
            brush_enricher._detect_user_intent(mock_brush_string, mock_handle_data, None)

    def test_detect_user_intent_invalid_handle_data(
        self, brush_enricher, mock_brush_string, mock_knot_data
    ):
        """Test user intent detection with invalid handle data."""
        invalid_handle_data = {"invalid": "data"}

        intent = brush_enricher._detect_user_intent(
            mock_brush_string, invalid_handle_data, mock_knot_data
        )
        # Should default to handle_primary when source_text is missing
        assert intent == "handle_primary"

    def test_detect_user_intent_invalid_knot_data(
        self, brush_enricher, mock_brush_string, mock_handle_data
    ):
        """Test user intent detection with invalid knot data."""
        invalid_knot_data = {"invalid": "data"}

        intent = brush_enricher._detect_user_intent(
            mock_brush_string, mock_handle_data, invalid_knot_data
        )
        # Should default to handle_primary when source_text is missing
        assert intent == "handle_primary"

    def test_detect_user_intent_case_insensitive(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection is case insensitive."""
        brush_string = "DECLARATION B2 IN ZENITH B2 BOAR"

        # Mock pattern loading
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile("declaration.*b2", re.IGNORECASE)],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile("zenith.*b2", re.IGNORECASE)],
            ),
        ):

            intent = brush_enricher._detect_user_intent(
                brush_string, mock_handle_data, mock_knot_data
            )
            assert intent == "handle_primary"

    def test_detect_user_intent_special_characters(
        self, brush_enricher, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection with special characters in brush string."""
        brush_string = "Declaration B2 & Zenith B2 Boar"

        # Mock pattern loading
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile("declaration.*b2", re.IGNORECASE)],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile("zenith.*b2", re.IGNORECASE)],
            ),
        ):

            intent = brush_enricher._detect_user_intent(
                brush_string, mock_handle_data, mock_knot_data
            )
            assert intent == "handle_primary"

    def test_detect_user_intent_multiple_pattern_matches(
        self, brush_enricher, mock_brush_string, mock_handle_data, mock_knot_data
    ):
        """Test user intent detection with multiple pattern matches."""
        # Mock pattern loading with multiple patterns
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[
                    re.compile("declaration", re.IGNORECASE),
                    re.compile("declaration.*b2", re.IGNORECASE),
                ],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[
                    re.compile("zenith", re.IGNORECASE),
                    re.compile("zenith.*b2", re.IGNORECASE),
                ],
            ),
        ):

            intent = brush_enricher._detect_user_intent(
                mock_brush_string, mock_handle_data, mock_knot_data
            )
            assert intent == "handle_primary"

    def test_detect_user_intent_debug_version(
        self, brush_enricher, mock_brush_string, mock_handle_data, mock_knot_data
    ):
        """Test debug version of user intent detection."""
        # Mock pattern loading
        with (
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_handle_patterns",
                return_value=[re.compile("declaration.*b2", re.IGNORECASE)],
            ),
            patch.object(
                brush_enricher.catalog_loader,
                "load_compiled_knot_patterns",
                return_value=[re.compile("zenith.*b2", re.IGNORECASE)],
            ),
        ):

            result = brush_enricher._detect_user_intent_debug(
                mock_brush_string, mock_handle_data, mock_knot_data
            )

            # Verify debug result structure
            assert "intent" in result
            assert "handle_position" in result
            assert "knot_position" in result
            assert "handle_patterns" in result
            assert "knot_patterns" in result
            assert "handle_matched_pattern" in result
            assert "knot_matched_pattern" in result
            assert "brush_string_normalized" in result
            assert "processing_time_ms" in result
            assert "edge_case_triggered" in result
            assert "error_message" in result

            # Verify intent result
            assert result["intent"] == "handle_primary"
            assert result["handle_position"] is not None
            assert result["knot_position"] is not None
            assert result["handle_position"] < result["knot_position"]
            assert result["edge_case_triggered"] is False
            assert result["error_message"] is None

    def test_should_detect_user_intent_composite_brush(self, brush_enricher):
        """Test that user intent detection should run for composite brushes."""
        brush_data = {
            "brand": "Declaration",  # Top-level brand but no model
            "model": None,
            "handle": {"brand": "Declaration", "model": "B2"},
            "knot": {"brand": "Zenith", "model": "B2"},
        }

        should_detect = brush_enricher._should_detect_user_intent(brush_data)
        assert should_detect is True

    def test_should_detect_user_intent_known_brush(self, brush_enricher):
        """Test that user intent detection should NOT run for known brushes."""
        brush_data = {
            "brand": "Declaration",
            "model": "B2",
            "handle": {"brand": "Declaration", "model": "B2"},
            "knot": {"brand": "Zenith", "model": "B2"},
        }

        should_detect = brush_enricher._should_detect_user_intent(brush_data)
        assert should_detect is False

    def test_should_detect_user_intent_missing_sections(self, brush_enricher):
        """Test that user intent detection should NOT run when sections are missing."""
        brush_data = {
            "handle": {"brand": "Declaration", "model": "B2"}
            # Missing knot section
        }

        should_detect = brush_enricher._should_detect_user_intent(brush_data)
        assert should_detect is False

    def test_should_detect_user_intent_empty_data(self, brush_enricher):
        """Test that user intent detection should NOT run with empty data."""
        brush_data = {}

        should_detect = brush_enricher._should_detect_user_intent(brush_data)
        assert should_detect is False

    def test_extract_brush_text_from_matched_data_handle_source_text(self, brush_enricher):
        """Test _extract_brush_text_from_matched_data with handle source_text."""
        field_data = {
            "brand": "Summer Break",
            "model": None,
            "handle": {
                "brand": "Summer Break",
                "model": "Unspecified",
                "source_text": "Summer Break Soaps Maize 26mm Timberwolf",
                "_matched_by": "HandleMatcher",
                "_pattern": "summer.*break",
            },
            "knot": {
                "brand": "Summer Break",
                "model": "Badger",
                "fiber": "Badger",
                "knot_size_mm": None,
                "source_text": "Summer Break Soaps Maize 26mm Timberwolf",
                "_matched_by": "KnotMatcher",
                "_pattern": "summer.*break",
            },
        }

        brush_text = brush_enricher._extract_brush_text_from_matched_data(field_data)
        assert brush_text == "Summer Break Soaps Maize 26mm Timberwolf"

    def test_extract_brush_text_from_matched_data_knot_fallback(self, brush_enricher):
        """Test _extract_brush_text_from_matched_data with knot source_text fallback."""
        field_data = {
            "brand": "Mountain Hare Shaving",
            "model": None,
            "handle": {
                "brand": "Mountain Hare Shaving",
                "model": "Unspecified",
                "_matched_by": "HandleMatcher",
                "_pattern": "mountain.*hare",
            },
            "knot": {
                "brand": "Mountain Hare Shaving",
                "model": "Badger",
                "fiber": "Badger",
                "knot_size_mm": None,
                "source_text": "Mountain Hare Shaving - Maple Burl and Resin Badger",
                "_matched_by": "KnotMatcher",
                "_pattern": "mountain.*hare",
            },
        }

        brush_text = brush_enricher._extract_brush_text_from_matched_data(field_data)
        assert brush_text == "Mountain Hare Shaving - Maple Burl and Resin Badger"

    def test_extract_brush_text_from_matched_data_no_source_text(self, brush_enricher):
        """Test _extract_brush_text_from_matched_data with no source_text."""
        field_data = {
            "brand": "Test Brand",
            "model": None,
            "handle": {
                "brand": "Test Brand",
                "model": "Test Model",
                "_matched_by": "HandleMatcher",
            },
            "knot": {
                "brand": "Test Brand",
                "model": "Test Model",
                "fiber": "Badger",
                "_matched_by": "KnotMatcher",
            },
        }

        brush_text = brush_enricher._extract_brush_text_from_matched_data(field_data)
        assert brush_text == ""

    def test_user_intent_detection_with_realistic_data(self, brush_enricher):
        """Test user intent detection with realistic data structure from match phase."""
        # This test uses the actual data structure that the enrich phase receives
        field_data = {
            "brand": "Summer Break",
            "model": None,
            "handle": {
                "brand": "Summer Break",
                "model": "Unspecified",
                "source_text": "Summer Break Soaps Maize 26mm Timberwolf",
                "_matched_by": "HandleMatcher",
                "_pattern": "summer.*break",
            },
            "knot": {
                "brand": "Summer Break",
                "model": "Badger",
                "fiber": "Badger",
                "knot_size_mm": None,
                "source_text": "Summer Break Soaps Maize 26mm Timberwolf",
                "_matched_by": "KnotMatcher",
                "_pattern": "summer.*break",
            },
        }

        # Test the should_detect logic
        should_detect = brush_enricher._should_detect_user_intent(field_data)
        assert should_detect is True

        # Test the actual user intent detection
        brush_string = brush_enricher._extract_brush_text_from_matched_data(field_data)
        assert brush_string == "Summer Break Soaps Maize 26mm Timberwolf"

        handle_data = field_data["handle"]
        knot_data = field_data["knot"]

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        # Since both source_text values are identical, it should default to handle_primary
        assert intent == "handle_primary"

    def test_user_intent_detection_fail_fast_missing_brush_string(self, brush_enricher):
        """Test that user intent detection fails fast when brush_string is missing."""
        handle_data = {"source_text": "Test Handle"}
        knot_data = {"source_text": "Test Knot"}

        with pytest.raises(ValueError, match="Missing brush_string for user intent detection"):
            brush_enricher._detect_user_intent("", handle_data, knot_data)

    def test_user_intent_detection_fail_fast_missing_handle_data(self, brush_enricher):
        """Test that user intent detection fails fast when handle_data is missing."""
        brush_string = "Test Brush String"
        knot_data = {"source_text": "Test Knot"}

        with pytest.raises(
            ValueError, match="Missing or invalid handle_data for user intent detection"
        ):
            brush_enricher._detect_user_intent(brush_string, None, knot_data)

    def test_user_intent_detection_fail_fast_missing_knot_data(self, brush_enricher):
        """Test that user intent detection fails fast when knot_data is missing."""
        brush_string = "Test Brush String"
        handle_data = {"source_text": "Test Handle"}

        with pytest.raises(
            ValueError, match="Missing or invalid knot_data for user intent detection"
        ):
            brush_enricher._detect_user_intent(brush_string, handle_data, None)

    def test_user_intent_detection_handle_primary_when_handle_first(self, brush_enricher):
        """Test user intent detection when handle text appears before knot text."""
        brush_string = "Declaration B2 in Mozingo handle"
        handle_data = {"source_text": "Declaration B2"}
        knot_data = {"source_text": "Mozingo handle"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent == "handle_primary"

    def test_user_intent_detection_knot_primary_when_knot_first(self, brush_enricher):
        """Test user intent detection when knot text appears before handle text."""
        brush_string = "Mozingo handle with Declaration B2"
        handle_data = {"source_text": "Declaration B2"}
        knot_data = {"source_text": "Mozingo handle"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent == "knot_primary"

    def test_user_intent_detection_handle_primary_when_text_not_found(self, brush_enricher):
        """Test user intent detection defaults to handle_primary when text not found."""
        brush_string = "Some other brush text"
        handle_data = {"source_text": "Declaration B2"}
        knot_data = {"source_text": "Mozingo handle"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent == "handle_primary"

    def test_user_intent_detection_handle_primary_when_missing_source_text(self, brush_enricher):
        """Test user intent detection defaults to handle_primary when source_text missing."""
        brush_string = "Test Brush String"
        handle_data = {"brand": "Test Brand"}  # No source_text
        knot_data = {"source_text": "Test Knot"}

        intent = brush_enricher._detect_user_intent(brush_string, handle_data, knot_data)
        assert intent == "handle_primary"
