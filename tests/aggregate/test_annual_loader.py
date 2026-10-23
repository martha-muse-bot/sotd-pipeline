#!/usr/bin/env python3
"""
Tests for the annual data loader module.

This module tests the functionality for loading 12 months of aggregated data
for a given year, including handling missing months and data validation.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from sotd.aggregate.annual_loader import (
    AnnualDataLoader,
    load_annual_data,
    validate_monthly_data_structure,
)


class TestAnnualDataLoader:
    """Test the AnnualDataLoader class."""

    def test_init_with_valid_year(self):
        """Test initialization with valid year."""
        loader = AnnualDataLoader("2024", Path("/data"))
        assert loader.year == "2024"
        assert loader.data_dir == Path("/data")

    def test_init_with_invalid_year_format(self):
        """Test initialization with invalid year format."""
        with pytest.raises(ValueError, match="Year must be in YYYY format"):
            AnnualDataLoader("24", Path("/data"))

    def test_init_with_non_numeric_year(self):
        """Test initialization with non-numeric year."""
        with pytest.raises(ValueError, match="Year must be numeric"):
            AnnualDataLoader("abcd", Path("/data"))

    def test_get_monthly_file_paths(self):
        """Test getting monthly file paths for a year."""
        loader = AnnualDataLoader("2024", Path("/data"))
        paths = loader.get_monthly_file_paths()

        assert len(paths) == 12
        assert paths[0] == Path("/data/2024-01.json")
        assert paths[5] == Path("/data/2024-06.json")
        assert paths[11] == Path("/data/2024-12.json")

    def test_load_monthly_file_success(self):
        """Test successfully loading a monthly file."""
        mock_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        with patch("sotd.aggregate.annual_loader.load_json_data", return_value=mock_data):
            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load_monthly_file(Path("/data/2024-01.json"))

            assert result == mock_data

    def test_load_monthly_file_missing(self):
        """Test loading a missing monthly file."""
        # Mock load_json_data (not builtins.open): the loader uses
        # file_path.exists()/open(), so a builtins.open mock also intercepts
        # unrelated opens (e.g. stdlib lazy data reads on CI runners) and its
        # FileNotFoundError escapes the loader's try block.
        with patch(
            "sotd.aggregate.annual_loader.load_json_data",
            side_effect=FileNotFoundError("File not found"),
        ):
            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load_monthly_file(Path("/data/2024-01.json"))

            assert result is None

    def test_load_monthly_file_corrupted(self):
        """Test loading a corrupted monthly file."""
        with patch(
            "sotd.aggregate.annual_loader.load_json_data",
            side_effect=json.JSONDecodeError("Invalid JSON", "invalid json", 0),
        ):
            loader = AnnualDataLoader("2024", Path("/data"))

            result = loader.load_monthly_file(Path("/data/2024-01.json"))
            assert result is None

    def test_load_all_months_all_present(self):
        """Test loading all months when all files are present."""
        mock_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        with patch.object(AnnualDataLoader, "load_monthly_file") as mock_load:
            mock_load.return_value = mock_data

            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load_all_months()

            assert len(result["monthly_data"]) == 12
            assert result["included_months"] == [
                "2024-01",
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ]
            assert result["missing_months"] == []
            assert all(data == mock_data for data in result["monthly_data"].values())

    def test_load_all_months_some_missing(self):
        """Test loading months when some files are missing."""
        mock_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        with patch.object(AnnualDataLoader, "load_monthly_file") as mock_load:
            # Return data for some months, None for others
            mock_load.side_effect = lambda path: (
                mock_data if "01" in str(path) or "06" in str(path) else None
            )

            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load_all_months()

            assert len(result["monthly_data"]) == 2
            assert result["included_months"] == ["2024-01", "2024-06"]
            assert result["missing_months"] == [
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ]

    def test_load_all_months_all_missing(self):
        """Test loading months when all files are missing."""
        with patch.object(AnnualDataLoader, "load_monthly_file") as mock_load:
            mock_load.return_value = None

            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load_all_months()

            assert len(result["monthly_data"]) == 0
            assert result["included_months"] == []
            assert result["missing_months"] == [
                "2024-01",
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ]

    def test_validate_data_structure_valid(self):
        """Test validation of valid data structure."""
        valid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        loader = AnnualDataLoader("2024", Path("/data"))
        assert loader.validate_data_structure(valid_data) is True

    def test_validate_data_structure_missing_metadata(self):
        """Test validation of data missing metadata."""
        invalid_data = {
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        loader = AnnualDataLoader("2024", Path("/data"))
        assert loader.validate_data_structure(invalid_data) is False

    def test_validate_data_structure_missing_product_sections(self):
        """Test validation of data missing product sections."""
        invalid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                # Missing blades, brushes, soaps
            },
        }

        loader = AnnualDataLoader("2024", Path("/data"))
        assert loader.validate_data_structure(invalid_data) is False

    def test_validate_data_structure_invalid_product_structure(self):
        """Test validation of data with invalid product structure."""
        invalid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": "not a list",
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        loader = AnnualDataLoader("2024", Path("/data"))
        assert loader.validate_data_structure(invalid_data) is False

    def test_load_with_validation_all_valid(self):
        """Test loading with validation when all data is valid."""
        mock_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        with patch.object(AnnualDataLoader, "load_monthly_file") as mock_load:
            mock_load.return_value = mock_data

            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load()

            assert result["year"] == "2024"
            assert len(result["monthly_data"]) == 12
            assert result["included_months"] == [
                "2024-01",
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ]
            assert result["missing_months"] == []
            assert result["validation_errors"] == []

    def test_load_with_validation_some_invalid(self):
        """Test loading with validation when some data is invalid."""
        valid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        invalid_data = {
            "meta": {"month": "2024-02", "total_shaves": 100},
            "data": {
                "razors": "invalid",
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        with patch.object(AnnualDataLoader, "load_monthly_file") as mock_load:
            # Return valid data for odd months, invalid for even months
            mock_load.side_effect = lambda path: (
                valid_data if int(str(path).split("-")[1].split(".")[0]) % 2 == 1 else invalid_data
            )

            loader = AnnualDataLoader("2024", Path("/data"))
            result = loader.load()

            assert result["year"] == "2024"
            assert len(result["monthly_data"]) == 6  # Only valid months included
            assert result["included_months"] == [
                "2024-01",
                "2024-03",
                "2024-05",
                "2024-07",
                "2024-09",
                "2024-11",
            ]
            assert result["missing_months"] == [
                "2024-02",
                "2024-04",
                "2024-06",
                "2024-08",
                "2024-10",
                "2024-12",
            ]
            assert len(result["validation_errors"]) == 6  # One error per invalid month


class TestValidateMonthlyDataStructure:
    """Test the validate_monthly_data_structure function."""

    def test_valid_structure(self):
        """Test validation of valid data structure."""
        valid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        assert validate_monthly_data_structure(valid_data) is True

    def test_missing_metadata(self):
        """Test validation of data missing metadata."""
        invalid_data = {
            "data": {
                "razors": [],
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        assert validate_monthly_data_structure(invalid_data) is False

    def test_missing_product_sections(self):
        """Test validation of data missing product sections."""
        invalid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": [],
                # Missing blades, brushes, soaps
            },
        }

        assert validate_monthly_data_structure(invalid_data) is False

    def test_invalid_product_structure(self):
        """Test validation of data with invalid product structure."""
        invalid_data = {
            "meta": {"month": "2024-01", "total_shaves": 100},
            "data": {
                "razors": "not a list",
                "blades": [],
                "brushes": [],
                "soaps": [],
            },
        }

        assert validate_monthly_data_structure(invalid_data) is False


class TestLoadAnnualData:
    """Test the load_annual_data function."""

    def test_load_annual_data_success(self):
        """Test successful loading of annual data."""
        mock_data = {
            "year": "2024",
            "monthly_data": {
                "2024-01": {"meta": {"month": "2024-01", "total_shaves": 100}},
            },
            "included_months": ["2024-01"],
            "missing_months": [
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ],
            "validation_errors": [],
        }

        with patch.object(AnnualDataLoader, "load") as mock_load:
            mock_load.return_value = mock_data

            result = load_annual_data("2024", Path("/data"))

            assert result == mock_data
            mock_load.assert_called_once()

    def test_load_annual_data_invalid_year(self):
        """Test loading with invalid year."""
        with pytest.raises(ValueError, match="Year must be in YYYY format"):
            load_annual_data("24", Path("/data"))

    def test_load_annual_data_with_validation_errors(self):
        """Test loading with validation errors."""
        mock_data = {
            "year": "2024",
            "monthly_data": {},
            "included_months": [],
            "missing_months": [
                "2024-01",
                "2024-02",
                "2024-03",
                "2024-04",
                "2024-05",
                "2024-06",
                "2024-07",
                "2024-08",
                "2024-09",
                "2024-10",
                "2024-11",
                "2024-12",
            ],
            "validation_errors": ["2024-01: Invalid data structure"],
        }

        with patch.object(AnnualDataLoader, "load") as mock_load:
            mock_load.return_value = mock_data

            result = load_annual_data("2024", Path("/data"))

            assert result == mock_data
            assert result["validation_errors"] == ["2024-01: Invalid data structure"]
