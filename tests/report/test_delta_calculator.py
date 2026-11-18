#!/usr/bin/env python3
"""Tests for the delta calculator module."""

from typing import Any, Dict, Tuple

import pytest

from sotd.report.delta_calculator import DeltaCalculator, calculate_deltas_for_period


class TestDeltaCalculator:
    """Test the DeltaCalculator class."""

    def test_init(self):
        """Test DeltaCalculator initialization."""
        calculator = DeltaCalculator(debug=True)
        assert calculator.debug is True

        calculator = DeltaCalculator(debug=False)
        assert calculator.debug is False

    def test_calculate_deltas_basic(self):
        """Test basic delta calculation with rank fields."""
        current_data = [
            {"name": "Razor A", "shaves": 100, "rank": 1},
            {"name": "Razor B", "shaves": 80, "rank": 2},
            {"name": "Razor C", "shaves": 60, "rank": 3},
        ]

        historical_data = [
            {"name": "Razor B", "shaves": 90, "rank": 1},
            {"name": "Razor A", "shaves": 85, "rank": 2},
            {"name": "Razor C", "shaves": 70, "rank": 3},
        ]

        calculator = DeltaCalculator()
        result = calculator.calculate_deltas(current_data, historical_data)

        assert len(result) == 3

        # Razor A: moved from rank 2 to 1 (improved by 1)
        assert result[0]["name"] == "Razor A"
        assert result[0]["delta"] == 1
        assert result[0]["delta_symbol"] == "↑1"  # Improved by 1 rank
        assert result[0]["delta_text"] == "↑1"  # Improved by 1 rank

        # Razor B: moved from rank 1 to 2 (worsened by 1)
        assert result[1]["name"] == "Razor B"
        assert result[1]["delta"] == -1
        assert result[1]["delta_symbol"] == "↓1"  # Worsened by 1 rank
        assert result[1]["delta_text"] == "↓1"  # Worsened by 1 rank

        # Razor C: stayed at rank 3 (no change)
        assert result[2]["name"] == "Razor C"
        assert result[2]["delta"] == 0
        assert result[2]["delta_symbol"] == "="
        assert result[2]["delta_text"] == "="

    def test_calculate_deltas_new_item(self):
        """Test delta calculation with new items not in historical data."""
        current_data = [
            {"name": "Razor A", "shaves": 100, "rank": 1},
            {"name": "Razor B", "shaves": 80, "rank": 2},
            {"name": "New Razor", "shaves": 60, "rank": 3},
        ]

        historical_data = [
            {"name": "Razor A", "shaves": 90, "rank": 2},
            {"name": "Razor B", "shaves": 85, "rank": 1},
        ]

        calculator = DeltaCalculator()
        result = calculator.calculate_deltas(current_data, historical_data)

        assert len(result) == 3

        # New Razor: not in historical data
        assert result[2]["name"] == "New Razor"
        assert result[2]["delta"] is None
        assert result[2]["delta_symbol"] == "n/a"
        assert result[2]["delta_text"] == "n/a"

    def test_calculate_deltas_missing_rank(self):
        """Test delta calculation with missing rank fields."""
        current_data = [
            {"name": "Razor A", "shaves": 100, "rank": 1},  # Has rank
            {"name": "Razor B", "shaves": 80},  # Missing rank
        ]

        historical_data = [
            {"name": "Razor A", "shaves": 90, "rank": 2},
            {"name": "Razor B", "shaves": 85},
        ]

        calculator = DeltaCalculator()
        result = calculator.calculate_deltas(current_data, historical_data)

        # Should only process items with rank fields
        assert len(result) == 1
        assert result[0]["name"] == "Razor A"

    def test_calculate_deltas_empty_data(self):
        """Test delta calculation with empty data."""
        calculator = DeltaCalculator()

        # Empty current data
        result = calculator.calculate_deltas([], [{"name": "Razor A"}])
        assert result == []

        # Empty historical data - should return current data with delta fields set to n/a
        result = calculator.calculate_deltas([{"name": "Razor A", "rank": 1}], [])
        assert len(result) == 1  # Current data should be returned
        assert result[0]["name"] == "Razor A"
        assert result[0]["delta"] is None
        assert result[0]["delta_symbol"] == "n/a"
        assert result[0]["delta_text"] == "n/a"

    def test_calculate_deltas_invalid_input(self):
        """Test delta calculation with invalid input types."""
        calculator = DeltaCalculator()

        with pytest.raises(ValueError, match="Expected list for current_data"):
            calculator.calculate_deltas("invalid", [])  # type: ignore

        with pytest.raises(ValueError, match="Expected list for historical_data"):
            calculator.calculate_deltas([], "invalid")  # type: ignore

    def test_calculate_deltas_max_items(self):
        """Test delta calculation with max_items limit."""
        current_data = [
            {"name": "Razor A", "shaves": 100, "rank": 1},
            {"name": "Razor B", "shaves": 80, "rank": 2},
            {"name": "Razor C", "shaves": 60, "rank": 3},
        ]

        historical_data = [
            {"name": "Razor A", "shaves": 90, "rank": 2},
            {"name": "Razor B", "shaves": 85, "rank": 1},
            {"name": "Razor C", "shaves": 70, "rank": 3},
        ]

        calculator = DeltaCalculator()
        result = calculator.calculate_deltas(current_data, historical_data, max_items=2)

        assert len(result) == 2
        assert result[0]["name"] == "Razor A"
        assert result[1]["name"] == "Razor B"

    def test_calculate_deltas_custom_name_key(self):
        """Test delta calculation with custom name key."""
        current_data = [
            {"product": "Razor A", "shaves": 100, "rank": 1},
            {"product": "Razor B", "shaves": 80, "rank": 2},
        ]

        historical_data = [
            {"product": "Razor A", "shaves": 90, "rank": 2},
            {"product": "Razor B", "shaves": 85, "rank": 1},
        ]

        calculator = DeltaCalculator()
        result = calculator.calculate_deltas(current_data, historical_data, name_key="product")

        assert len(result) == 2
        assert result[0]["product"] == "Razor A"
        assert result[0]["delta"] == 1

    def test_get_delta_symbol(self):
        """Test delta symbol generation."""
        calculator = DeltaCalculator()

        assert calculator._get_delta_symbol(1) == "↑1"  # Improved by 1 rank
        assert calculator._get_delta_symbol(-1) == "↓1"  # Worsened by 1 rank
        assert calculator._get_delta_symbol(0) == "="  # No change
        assert calculator._get_delta_symbol(None) == "n/a"  # New item

    def test_calculate_category_deltas(self):
        """Test delta calculation for multiple categories."""
        current_data = {
            "razors": [
                {"name": "Razor A", "shaves": 100, "rank": 1},
                {"name": "Razor B", "shaves": 80, "rank": 2},
            ],
            "blades": [
                {"name": "Blade A", "shaves": 50, "rank": 1},
                {"name": "Blade B", "shaves": 40, "rank": 2},
            ],
        }

        historical_data = {
            "razors": [
                {"name": "Razor B", "shaves": 90, "rank": 1},
                {"name": "Razor A", "shaves": 85, "rank": 2},
            ],
            "blades": [
                {"name": "Blade A", "shaves": 45, "rank": 1},
                {"name": "Blade B", "shaves": 35, "rank": 2},
            ],
        }

        calculator = DeltaCalculator()
        result = calculator.calculate_category_deltas(
            current_data, historical_data, ["razors", "blades"]
        )

        assert "razors" in result
        assert "blades" in result

        # Check razors
        razors = result["razors"]
        assert len(razors) == 2
        assert razors[0]["name"] == "Razor A"
        assert razors[0]["delta"] == 1

        # Check blades
        blades = result["blades"]
        assert len(blades) == 2
        assert blades[0]["name"] == "Blade A"
        assert blades[0]["delta"] == 0

    def test_calculate_category_deltas_invalid_category(self):
        """Test delta calculation with invalid category data."""
        current_data = {
            "razors": [
                {"name": "Razor A", "shaves": 100, "rank": 1},
                {"name": "Razor B", "shaves": 80, "rank": 2},
            ],
            "invalid": "not a list",  # Invalid category data
        }

        historical_data = {
            "razors": [
                {"name": "Razor A", "shaves": 90, "rank": 2},
                {"name": "Razor B", "shaves": 85, "rank": 1},
            ],
        }

        calculator = DeltaCalculator()
        result = calculator.calculate_category_deltas(
            current_data, historical_data, ["razors", "invalid"]
        )

        # Should process valid categories and skip invalid ones
        assert "razors" in result
        assert len(result["razors"]) == 2
        assert "invalid" not in result  # Invalid category should be skipped

    def test_format_delta_column(self):
        """Test delta column formatting."""
        calculator = DeltaCalculator()

        # Test with valid delta data
        items = [
            {"name": "Item A", "delta": 1, "delta_symbol": "↑1", "delta_text": "↑1"},
            {"name": "Item B", "delta": -2, "delta_symbol": "↓2", "delta_text": "↓2"},
            {"name": "Item C", "delta": 0, "delta_symbol": "=", "delta_text": "="},
            {"name": "Item D", "delta": None, "delta_symbol": "n/a", "delta_text": "n/a"},
        ]

        result = calculator.format_delta_column(items, "delta_symbol")
        assert result == ["↑1", "↓2", "=", "n/a"]

    def test_format_delta_column_missing_keys(self):
        """Test delta column formatting with missing keys."""
        items = [
            {"name": "Item A", "delta_text": "↑"},  # Missing delta_symbol
            {"name": "Item B"},  # Missing both
        ]

        calculator = DeltaCalculator()
        formatted = calculator.format_delta_column(items)

        assert formatted == ["↑", "n/a"]

    def test_format_delta_column_invalid_items(self):
        """Test delta column formatting with invalid items."""
        items = [
            {"name": "Item A", "delta_text": "↑", "delta_symbol": "↑"},
            "not a dict",  # Invalid item
            {"name": "Item B", "delta_text": "↓", "delta_symbol": "↓"},
        ]

        calculator = DeltaCalculator()
        formatted = calculator.format_delta_column(items)

        assert formatted == ["↑", "n/a", "↓"]

    def test_calculate_deltas_christopher_bradley_plates_bug(self):
        """Test that the Christopher Bradley plates delta calculation bug is fixed.

        This test verifies that the bug where all delta columns showed "n/a" has been resolved.
        """
        calculator = DeltaCalculator()

        # Current month data (June 2025) - includes ranks assigned by aggregator
        current_data = [
            {"name": "Christopher Bradley Plate A", "shaves": 45, "rank": 1},
            {"name": "Christopher Bradley Plate B", "shaves": 32, "rank": 2},
            {"name": "Christopher Bradley Plate C", "shaves": 18, "rank": 3},
        ]

        # Previous month data (May 2025) - these plates definitely existed
        historical_data = [
            {"name": "Christopher Bradley Plate A", "shaves": 42, "rank": 2},
            {"name": "Christopher Bradley Plate B", "shaves": 35, "rank": 1},
            {"name": "Christopher Bradley Plate C", "shaves": 20, "rank": 3},
        ]

        # Calculate deltas
        result = calculator.calculate_deltas(current_data, historical_data)

        # Verify that deltas are calculated correctly
        assert len(result) == 3

        # Plate A: moved from rank 2 to rank 1 (improved by 1)
        plate_a = next(item for item in result if item["name"] == "Christopher Bradley Plate A")
        assert plate_a["delta"] == 1
        assert plate_a["delta_symbol"] == "↑1"
        assert plate_a["delta_text"] == "↑1"

        # Plate B: moved from rank 1 to rank 2 (worsened by 1)
        plate_b = next(item for item in result if item["name"] == "Christopher Bradley Plate B")
        assert plate_b["delta"] == -1
        assert plate_b["delta_symbol"] == "↓1"
        assert plate_b["delta_text"] == "↓1"

        # Plate C: stayed at rank 3 (no change)
        plate_c = next(item for item in result if item["name"] == "Christopher Bradley Plate C")
        assert plate_c["delta"] == 0
        assert plate_c["delta_symbol"] == "="
        assert plate_c["delta_text"] == "="


class TestCalculateDeltasForPeriod:
    """Test the calculate_deltas_for_period function."""

    def test_calculate_deltas_for_period_success(self):
        """Test successful delta calculation for a period."""
        current_data = {
            "razors": [
                {"name": "Razor A", "shaves": 100, "rank": 1},
                {"name": "Razor B", "shaves": 80, "rank": 2},
            ]
        }

        comparison_data: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {
            "previous_month": (
                {"month": "2024-12"},
                {
                    "razors": [
                        {"name": "Razor B", "shaves": 90, "rank": 1},
                        {"name": "Razor A", "shaves": 85, "rank": 2},
                    ]
                },
            )
        }

        result = calculate_deltas_for_period(
            current_data, comparison_data, "previous_month", ["razors"]
        )

        assert result is not None
        assert "razors" in result
        assert len(result["razors"]) == 2

        # Razor A improved from position 2 to 1
        assert result["razors"][0]["name"] == "Razor A"
        assert result["razors"][0]["delta"] == 1

    def test_calculate_deltas_for_period_not_found(self):
        """Test delta calculation for non-existent period."""
        current_data = {"razors": []}
        comparison_data: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {}

        result = calculate_deltas_for_period(
            current_data, comparison_data, "previous_month", ["razors"]
        )

        assert result is None

    def test_calculate_deltas_for_period_invalid_historical_data(self):
        """Test delta calculation with invalid historical data structure."""
        current_data = {"razors": []}
        comparison_data: Dict[str, Tuple[Dict[str, Any], Any]] = {
            "previous_month": (
                {"month": "2024-12"},
                "not a dict",  # Invalid historical data
            )
        }

        result = calculate_deltas_for_period(
            current_data, comparison_data, "previous_month", ["razors"], debug=True  # type: ignore
        )

        assert result is None

    def test_calculate_deltas_for_period_with_debug(self):
        """Test delta calculation with debug mode enabled."""
        current_data = {"razors": [{"name": "Razor A", "shaves": 100, "rank": 1}]}

        comparison_data: Dict[str, Tuple[Dict[str, Any], Dict[str, Any]]] = {
            "previous_month": (
                {"month": "2024-12"},
                {"razors": [{"name": "Razor A", "shaves": 90, "rank": 2}]},
            )
        }

        result = calculate_deltas_for_period(
            current_data, comparison_data, "previous_month", ["razors"], debug=True
        )

        assert result is not None
        assert "razors" in result
        assert len(result["razors"]) == 1
        assert result["razors"][0]["delta"] == 1
