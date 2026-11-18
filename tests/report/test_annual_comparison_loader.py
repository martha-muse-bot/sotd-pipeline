#!/usr/bin/env python3
"""Tests for the annual comparison data loader module."""

import json
import tempfile
from pathlib import Path

from sotd.report.annual_comparison_loader import AnnualComparisonLoader


class TestAnnualComparisonLoader:
    def setup_method(self):
        self.loader = AnnualComparisonLoader(debug=True)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp_dir.name)

    def teardown_method(self):
        self.temp_dir.cleanup()

    def _write_annual_file(self, year: str, data: dict):
        file_path = self.data_dir / f"{year}.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
        return file_path

    def test_load_single_year(self):
        """Test loading a single year's annual data."""
        year = "2023"
        data = {"year": year, "meta": {"total_shaves": 1000}, "data": {"razors": []}}
        self._write_annual_file(year, data)
        result = self.loader.load_comparison_years([year], self.data_dir)
        assert year in result
        assert result[year]["year"] == year
        assert "meta" in result[year]
        assert "data" in result[year]

    def test_load_multiple_years(self):
        """Test loading multiple years' annual data."""
        years = ["2022", "2023"]
        for y in years:
            self._write_annual_file(y, {"year": y, "meta": {}, "data": {}})
        result = self.loader.load_comparison_years(years, self.data_dir)
        assert set(result.keys()) == set(years)

    def test_missing_year_file(self):
        """Test handling missing year file with warning and skip."""
        year = "2020"
        # No file written
        result = self.loader.load_comparison_years([year], self.data_dir)
        assert year not in result

    def test_invalid_json_file(self):
        """Test handling invalid/corrupted JSON file as missing data."""
        year = "2021"
        file_path = self.data_dir / f"{year}.json"
        with file_path.open("w", encoding="utf-8") as f:
            f.write("not a json")
        result = self.loader.load_comparison_years([year], self.data_dir)
        assert year not in result

    def test_invalid_data_structure(self):
        """Test handling file with invalid structure (not a dict)."""
        year = "2025"
        file_path = self.data_dir / f"{year}.json"
        with file_path.open("w", encoding="utf-8") as f:
            json.dump([1, 2, 3], f, ensure_ascii=False)
        result = self.loader.load_comparison_years([year], self.data_dir)
        assert year not in result

    def test_partial_years(self):
        """Test loading some years present, some missing."""
        years = ["2020", "2021", "2022"]
        self._write_annual_file("2021", {"year": "2021", "meta": {}, "data": {}})
        result = self.loader.load_comparison_years(years, self.data_dir)
        assert "2021" in result
        assert "2020" not in result
        assert "2022" not in result

    def test_debug_output(self, capsys):
        """Test debug output for missing and invalid files."""
        years = ["2019", "2020"]
        self._write_annual_file("2020", {"year": "2020", "meta": {}, "data": {}})
        self.loader.load_comparison_years(years, self.data_dir)
        captured = capsys.readouterr()
        assert "[DEBUG] Missing annual file for year 2019" in captured.out
        assert "[DEBUG] Loaded annual file for year 2020" in captured.out
