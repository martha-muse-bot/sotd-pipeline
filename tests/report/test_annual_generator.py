#!/usr/bin/env python3
"""Tests for the annual report generator."""

import json
from pathlib import Path

import pytest

from sotd.report import annual_generator
from sotd.report.annual_generator import AnnualReportGenerator


class TestAnnualReportGenerator:
    def test_generate_annual_report_valid(self, tmp_path: Path):
        """Test generating a valid annual report from data and template."""
        # Create test annual data
        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 1200,
                "unique_shavers": 100,
                "included_months": 12,
                "missing_months": 0,
            },
            "razors": [
                {"name": "Rockwell 6C", "shaves": 200, "unique_users": 80, "rank": 1},
                {"name": "Merkur 34C", "shaves": 150, "unique_users": 60, "rank": 2},
            ],
            "blades": [
                {
                    "name": "Astra Superior Platinum",
                    "shaves": 250,
                    "unique_users": 90,
                    "rank": 1,
                },
                {"name": "Feather Hi-Stainless", "shaves": 200, "unique_users": 85, "rank": 2},
            ],
            "brushes": [
                {"name": "Simpson Chubby 2", "shaves": 100, "unique_users": 40, "rank": 1},
                {"name": "Omega 10049", "shaves": 80, "unique_users": 35, "rank": 2},
            ],
            "soaps": [
                {
                    "name": "Barrister and Mann Seville",
                    "shaves": 120,
                    "unique_users": 50,
                    "rank": 1,
                },
                {
                    "name": "Stirling Executive Man",
                    "shaves": 100,
                    "unique_users": 45,
                    "rank": 2,
                },
            ],
        }

        # Create test annual data file
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Create a simplified test template that only includes the tables we have
        template_dir = tmp_path / "test_templates"
        template_dir.mkdir()

        # Create a simplified annual hardware template
        annual_hardware_template = template_dir / "annual_hardware.md"
        annual_hardware_template.write_text("""# Annual Hardware Report - {{year}}

Welcome to your Annual SOTD Hardware Report for {{year}}

## Annual Summary

* {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during {{year}} were analyzed to produce this report.
* Data includes {{included_months}} months of the year.
{% if missing_months > 0 %}
* Note: {{missing_months}} months were missing from the data set.
{% endif %}

## Razors

{{tables.razors}}

## Blades

{{tables.blades}}

## Brushes

{{tables.brushes}}

## Soaps

{{tables.soaps}}
""")

        # Generate annual hardware report with custom template
        result = annual_generator.generate_annual_report(
            report_type="hardware",
            year="2024",
            data_dir=tmp_path,
            debug=False,
            template_path=str(template_dir),
        )

        # Verify the report was generated
        assert result is not None
        assert "Welcome to your Annual SOTD Hardware Report for 2024" in result
        assert "1,200 shave reports from 100 distinct shavers during 2024" in result
        assert "Data includes 12 months of the year" in result
        assert "Rockwell 6C" in result
        assert "Astra Superior Platinum" in result

    def test_generate_annual_report_missing_data(self, tmp_path: Path):
        """Test error handling when annual data is missing."""
        # Do not create the annual data file
        with pytest.raises(FileNotFoundError):
            annual_generator.generate_annual_report(
                report_type="hardware",
                year="2024",
                data_dir=tmp_path,
                debug=False,
            )

    def test_generate_annual_report_invalid_template(self, tmp_path: Path):
        """Test error handling for invalid/malformed template."""
        # Create a template directory with only monthly templates (missing annual_hardware)
        template_dir = tmp_path / "test_templates"
        template_dir.mkdir()

        # Create a hardware template but not annual_hardware
        (template_dir / "hardware.md").write_text("Monthly hardware report")

        # Create valid annual data file
        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 1200,
                "unique_shavers": 100,
                "included_months": 12,
                "missing_months": 0,
            },
            "razors": [],
            "blades": [],
            "brushes": [],
            "soaps": [],
        }
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Should raise KeyError for missing annual_hardware template
        with pytest.raises(KeyError, match="Template 'annual_hardware' not found"):
            annual_generator.generate_annual_report(
                report_type="hardware",
                year="2024",
                data_dir=tmp_path,
                debug=False,
                template_path=str(template_dir),
            )

    def test_generate_annual_report_with_extra_fields(self, tmp_path: Path):
        """Test that extra fields in data/template do not break report generation."""
        # Create test annual data with extra fields
        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 1200,
                "unique_shavers": 100,
                "included_months": 12,
                "missing_months": 0,
                "extra_metadata_field": "should be ignored",
            },
            "razors": [{"name": "Rockwell 6C", "shaves": 200, "unique_users": 80, "rank": 1}],
            "blades": [
                {
                    "name": "Astra Superior Platinum",
                    "shaves": 250,
                    "unique_users": 90,
                    "rank": 1,
                }
            ],
            "brushes": [{"name": "Simpson Chubby 2", "shaves": 100, "unique_users": 40, "rank": 1}],
            "soaps": [
                {
                    "name": "Barrister and Mann Seville",
                    "shaves": 120,
                    "unique_users": 50,
                    "rank": 1,
                }
            ],
            "extra_category": [
                {"name": "Extra Product", "shaves": 50, "unique_users": 20, "rank": 1}
            ],
        }

        # Create test annual data file
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Create template with extra fields
        template_dir = tmp_path / "test_templates"
        template_dir.mkdir()

        template_content = (
            "Welcome to your Annual SOTD Hardware Report for {{year}}\n\n"
            "* {{total_shaves}} shaves from {{unique_shavers}} "
            "distinct shavers during {{year}}.\n\n"
            "## Razors\n\n{{tables.razors}}\n\n"
            "## Extra Section\n\nThis is an extra section that should be included."
        )
        (template_dir / "annual_hardware.md").write_text(template_content)

        # Generate annual hardware report
        result = annual_generator.generate_annual_report(
            report_type="hardware",
            year="2024",
            data_dir=tmp_path,
            debug=False,
            template_path=str(template_dir),
        )

        # Verify the report was generated correctly despite extra fields
        assert result is not None
        assert "Welcome to your Annual SOTD Hardware Report for 2024" in result
        assert "1,200 shaves from 100 distinct shavers during 2024" in result
        assert "Rockwell 6C" in result
        assert "Extra Section" in result  # Extra template content should be included
        # Extra fields should not cause errors or appear in output
        assert "extra_metadata_field" not in result
        assert "extra_category" not in result
        assert "extra_template_field" not in result

    def test_generate_annual_report_performance(self, tmp_path: Path):
        """Test performance with large annual data sets."""
        # Create large dataset with many products
        large_razors = [
            {"name": f"Razor {i}", "shaves": 100 + i, "unique_users": 50 + i, "rank": i}
            for i in range(1, 101)
        ]
        large_blades = [
            {"name": f"Blade {i}", "shaves": 200 + i, "unique_users": 100 + i, "rank": i}
            for i in range(1, 101)
        ]
        large_brushes = [
            {"name": f"Brush {i}", "shaves": 50 + i, "unique_users": 25 + i, "rank": i}
            for i in range(1, 101)
        ]
        large_soaps = [
            {"name": f"Soap {i}", "shaves": 75 + i, "unique_users": 40 + i, "rank": i}
            for i in range(1, 101)
        ]

        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 50000,
                "unique_shavers": 1000,
                "included_months": [f"2024-{i:02d}" for i in range(1, 13)],
                "missing_months": [],
            },
            "razors": large_razors,
            "blades": large_blades,
            "brushes": large_brushes,
            "soaps": large_soaps,
        }

        # Create test annual data file
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Create a simplified test template for performance testing
        template_dir = tmp_path / "test_templates"
        template_dir.mkdir()

        # Create a simplified annual hardware template
        annual_hardware_template = template_dir / "annual_hardware.md"
        annual_hardware_template.write_text("""# Annual Hardware Report - {{year}}

Welcome to your Annual SOTD Hardware Report for {{year}}

## Annual Summary

* {{total_shaves}} shave reports from {{unique_shavers}} distinct shavers during {{year}} were analyzed to produce this report.
* Data includes {{included_months}} months of the year.

## Razors

{{tables.razors}}

## Blades

{{tables.blades}}

## Brushes

{{tables.brushes}}

## Soaps

{{tables.soaps}}
""")

        # Generate annual hardware report and measure performance
        import time

        start_time = time.time()

        result = annual_generator.generate_annual_report(
            report_type="hardware",
            year="2024",
            data_dir=tmp_path,
            debug=False,
            template_path=str(template_dir),
        )

        end_time = time.time()
        generation_time = end_time - start_time

        # Verify the report was generated correctly
        assert result is not None
        assert "Welcome to your Annual SOTD Hardware Report for 2024" in result
        assert "50,000 shave reports from 1,000 distinct shavers during 2024" in result
        assert "Razor 1" in result
        assert "Blade 1" in result
        assert "Brush 1" in result

        # Performance assertion: should complete in under 5 seconds
        assert (
            generation_time < 5.0
        ), f"Report generation took {generation_time:.2f}s, expected under 5s"

    def test_generate_annual_report_integration(self, tmp_path: Path):
        """Test integration with loader and template processor."""
        # Create test annual data with realistic structure
        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 15000,
                "unique_shavers": 500,
                "included_months": [
                    "2024-01",
                    "2024-02",
                    "2024-03",
                    "2024-04",
                    "2024-05",
                    "2024-06",
                ],
                "missing_months": [
                    "2024-07",
                    "2024-08",
                    "2024-09",
                    "2024-10",
                    "2024-11",
                    "2024-12",
                ],
            },
            "razors": [
                {"name": "Rockwell 6C", "shaves": 1200, "unique_users": 300, "rank": 1},
                {"name": "Merkur 34C", "shaves": 800, "unique_users": 250, "rank": 2},
                {"name": "Gillette Super Speed", "shaves": 600, "unique_users": 200, "rank": 3},
            ],
            "blades": [
                {
                    "name": "Astra Superior Platinum",
                    "shaves": 2000,
                    "unique_users": 400,
                    "rank": 1,
                },
                {
                    "name": "Feather Hi-Stainless",
                    "shaves": 1500,
                    "unique_users": 350,
                    "rank": 2,
                },
                {
                    "name": "Gillette Silver Blue",
                    "shaves": 1000,
                    "unique_users": 300,
                    "rank": 3,
                },
            ],
            "brushes": [
                {"name": "Simpson Chubby 2", "shaves": 500, "unique_users": 150, "rank": 1},
                {"name": "Omega 10049", "shaves": 400, "unique_users": 120, "rank": 2},
                {"name": "Yaqi Sagrada Familia", "shaves": 300, "unique_users": 100, "rank": 3},
            ],
            "soaps": [
                {
                    "name": "Barrister and Mann Seville",
                    "shaves": 800,
                    "unique_users": 200,
                    "rank": 1,
                },
                {
                    "name": "Stirling Executive Man",
                    "shaves": 600,
                    "unique_users": 180,
                    "rank": 2,
                },
                {
                    "name": "Declaration Grooming Original",
                    "shaves": 400,
                    "unique_users": 120,
                    "rank": 3,
                },
            ],
        }

        # Create test annual data file
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Create custom template to test template processor integration
        template_dir = tmp_path / "test_templates"
        template_dir.mkdir()

        template_content = (
            "# Annual SOTD Hardware Report for {{year}}\n\n"
            "## Overview\n\n"
            "* {{total_shaves}} shaves from {{unique_shavers}} "
            "distinct shavers during {{year}}.\n"
            "* Data includes {{included_months}} months of the year.\n"
            "* Missing data for {{missing_months}} months.\n\n"
            "## Top Razors\n\n"
            "{{tables.razors}}\n\n"
            "## Top Blades\n\n"
            "{{tables.blades}}\n\n"
            "## Top Brushes\n\n"
            "{{tables.brushes}}\n\n"
            "## Summary\n\n"
            "This report covers {{included_months}} months of {{year}} "
            "with {{total_shaves}} total shaves."
        )
        (template_dir / "annual_hardware.md").write_text(template_content)

        # Generate annual hardware report with integration testing
        result = annual_generator.generate_annual_report(
            report_type="hardware",
            year="2024",
            data_dir=tmp_path,
            debug=True,  # Enable debug to test logging integration
            template_path=str(template_dir),
        )

        # Verify complete integration workflow
        assert result is not None
        assert "# Annual SOTD Hardware Report for 2024" in result
        assert "15,000 shaves from 500 distinct shavers during 2024" in result
        assert "Data includes 6 months of the year" in result
        assert "Missing data for 6 months" in result

        # Verify table generation integration
        assert "## Top Razors" in result
        assert "Rockwell 6C" in result
        assert "Merkur 34C" in result
        assert "Gillette Super Speed" in result

        assert "## Top Blades" in result
        assert "Astra Superior Platinum" in result
        assert "Feather Hi-Stainless" in result
        assert "Gillette Silver Blue" in result

        assert "## Top Brushes" in result
        assert "Simpson Chubby 2" in result
        assert "Omega 10049" in result
        assert "Yaqi Sagrada Familia" in result

        # Verify summary section
        assert "This report covers 6 months of 2024 with 15,000 total shaves" in result

        # Verify data loading integration (metadata values)
        assert "500" in result  # unique_shavers
        assert "6" in result  # included_months count
        assert "6" in result  # missing_months count

        # Verify template processor integration (variable substitution)
        assert "{{year}}" not in result  # Template variables should be substituted
        assert "{{total_shaves}}" not in result
        assert "{{unique_shavers}}" not in result

    def test_get_structured_data_basic(self):
        """Test get_structured_data returns correct structure."""
        metadata = {
            "year": "2024",
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": 12,
            "missing_months": 0,
        }
        data = {
            "razors": [
                {"rank": 1, "name": "Test Razor", "shaves": 200},
                {"rank": 2, "name": "Another Razor", "shaves": 150},
            ],
            "blades": [{"rank": 1, "name": "Test Blade", "shaves": 250}],
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data)

        result = generator.get_structured_data()

        # Verify structure
        assert "metadata" in result
        assert "tables" in result
        assert "stats" in result

        # Verify metadata
        assert result["metadata"]["year"] == "2024"
        assert result["metadata"]["total_shaves"] == 1200
        assert result["metadata"]["unique_shavers"] == 100

        # Verify tables
        assert "razors" in result["tables"]
        assert "blades" in result["tables"]
        assert len(result["tables"]["razors"]) == 2  # No row limits
        assert len(result["tables"]["blades"]) == 1

        # Verify table data structure
        assert isinstance(result["tables"]["razors"][0], dict)
        # Column names are formatted to Title Case
        assert "Name" in result["tables"]["razors"][0]
        assert "Shaves" in result["tables"]["razors"][0]

        # Verify stats
        assert result["stats"]["total_tables"] == 2
        assert result["stats"]["tables_with_data"] == 2

    def test_get_structured_data_no_row_limits(self):
        """Test get_structured_data returns all rows (no limits)."""
        metadata = {"year": "2024", "total_shaves": 1200}
        # Create data with many rows
        data = {
            "razors": [
                {"rank": i, "name": f"Razor {i}", "shaves": 200 - i}
                for i in range(1, 101)  # 100 razors
            ]
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data)

        result = generator.get_structured_data()

        # Verify all rows are included (no row limits)
        assert len(result["tables"]["razors"]) == 100

    def test_get_structured_data_with_missing_months(self):
        """Test get_structured_data handles missing months in metadata."""
        metadata = {
            "year": "2024",
            "total_shaves": 1000,
            "included_months": 10,
            "missing_months": ["2024-03", "2024-07"],
        }
        data = {
            "razors": [{"rank": 1, "name": "Test Razor", "shaves": 100}],
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data)

        result = generator.get_structured_data()

        # Verify metadata includes missing months as list
        assert result["metadata"]["missing_months"] == ["2024-03", "2024-07"]
        assert result["metadata"]["included_months"] == 10

    def test_get_structured_data_software_report(self):
        """Test get_structured_data for software reports."""
        metadata = {
            "year": "2024",
            "total_shaves": 1200,
            "unique_shavers": 100,
        }
        data = {
            "soaps": [
                {"rank": 1, "name": "Test Soap", "shaves": 150},
            ],
            "soap_makers": [
                {"rank": 1, "name": "Test Maker", "shaves": 200},
            ],
        }

        generator = AnnualReportGenerator("2024", "software", metadata, data)

        result = generator.get_structured_data()

        # Verify structure
        assert "tables" in result
        assert "soaps" in result["tables"]
        assert "soap-makers" in result["tables"]  # Converted to kebab-case

        # Verify all rows included
        assert len(result["tables"]["soaps"]) == 1
        assert len(result["tables"]["soap-makers"]) == 1
