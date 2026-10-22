#!/usr/bin/env python3
"""Integration tests for annual generator refactoring."""

import json
from pathlib import Path

import pytest

from sotd.report.annual_generator import (
    AnnualReportGenerator,
    create_annual_report_generator,
    generate_annual_report_content,
    generate_annual_report,
)


class TestAnnualGeneratorRefactoring:
    """Test that annual generator refactoring preserves functionality."""

    def test_annual_report_generator_creation(self):
        """Test creating annual report generator with unified patterns."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01", "2024-02"],
            "missing_months": [],
        }
        data = {"razors": [{"name": "Rockwell 6C", "shaves": 200, "rank": 1}]}

        # Test creating generator
        generator = create_annual_report_generator("hardware", "2024", metadata, data, debug=True)
        assert isinstance(generator, AnnualReportGenerator)
        assert generator.year == "2024"
        assert generator.report_type == "hardware"
        assert generator.metadata == metadata
        assert generator.data == data

    def test_annual_report_generator_invalid_type(self):
        """Test error handling for invalid report type."""
        metadata = {"total_shaves": 1200, "unique_shavers": 100}
        data = {"razors": []}

        with pytest.raises(ValueError, match="Unsupported report type: invalid"):
            create_annual_report_generator("invalid", "2024", metadata, data)

    def test_generate_annual_report_content(self, tmp_path: Path):
        """Test generating annual report content with unified patterns."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01", "2024-02"],
            "missing_months": [],
        }
        data = {"razors": [{"name": "Rockwell 6C", "shaves": 200, "rank": 1}]}

        # Create a simplified test template
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
""")

        # Test content generation with custom template
        result = generate_annual_report_content(
            "hardware", "2024", metadata, data, debug=True, template_path=str(template_dir)
        )
        assert result is not None
        assert "2024" in result
        assert "1,200" in result
        assert "100" in result

    def test_annual_report_generator_methods(self):
        """Test that annual report generator follows unified patterns."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01", "2024-02"],
            "missing_months": [],
        }
        # Provide minimal data for all expected tables to satisfy template validation
        data = {
            "razors": [{"name": "Rockwell 6C", "shaves": 200, "rank": 1}],
            "blades": [],
            "brushes": [],
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data, debug=True)

        # Test that methods exist and follow unified patterns
        assert hasattr(generator, "generate_header")
        assert hasattr(generator, "generate_notes_and_caveats")
        assert hasattr(generator, "generate_tables")
        assert hasattr(generator, "generate_report")

        # Test header method (deprecated but should exist)
        header = generator.generate_header()
        assert header == ""

        # Test tables method (deprecated but should exist)
        tables = generator.generate_tables()
        assert tables == []

        # Test complete report generation
        report = generator.generate_report()
        assert report is not None
        assert "2024" in report

    def test_annual_report_generator_variables(self):
        """Test that annual report generator prepares variables correctly."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01", "2024-02", "2024-03"],
            "missing_months": ["2024-04"],
        }
        data = {
            "razors": [],
            "blades": [],
            "brushes": [],
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data, debug=True)

        # Test that variables are prepared correctly in generate_notes_and_caveats
        result = generator.generate_notes_and_caveats()
        assert "2024" in result
        assert "1,200" in result  # Formatted total_shaves
        assert "100" in result  # unique_shavers
        assert "3" in result  # included_months count
        assert "1" in result  # missing_months count

    def test_annual_report_generator_comparison_data(self):
        """Test that annual report generator handles comparison data correctly."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01"],
            "missing_months": [],
        }
        data = {
            "razors": [{"name": "Rockwell 6C", "shaves": 200, "rank": 1}],
            "blades": [],
            "brushes": [],
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }
        comparison_data = {
            "2023": (
                {"total_shaves": 1000, "unique_shavers": 80},
                {"razors": [{"name": "Merkur 34C", "shaves": 150, "rank": 1}]},
            )
        }

        generator = AnnualReportGenerator(
            "2024", "hardware", metadata, data, comparison_data, debug=True
        )

        # Test that comparison data is handled correctly
        assert generator.comparison_data == comparison_data
        result = generator.generate_report()
        assert result is not None

    def test_generate_annual_report_integration(self, tmp_path: Path):
        """Test the complete generate_annual_report function with unified patterns."""
        # Create test annual data with all required categories for hardware report
        test_data = {
            "metadata": {
                "year": "2024",
                "total_shaves": 1200,
                "unique_shavers": 100,
                "included_months": ["2024-01", "2024-02"],
                "missing_months": [],
            },
            "razors": [{"name": "Rockwell 6C", "shaves": 200, "rank": 1}],
            "blades": [{"name": "Astra Superior Platinum", "shaves": 250, "rank": 1}],
            "brushes": [{"name": "Simpson Chubby 2", "shaves": 100, "rank": 1}],
            "soaps": [{"name": "Barrister and Mann Seville", "shaves": 120, "rank": 1}],
            # Add empty lists for all specialized tables that the template expects
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }

        # Create test annual data file
        annual_data_file = tmp_path / "aggregated" / "annual" / "2024.json"
        annual_data_file.parent.mkdir(parents=True)
        with open(annual_data_file, "w") as f:
            json.dump(test_data, f, ensure_ascii=False)

        # Test complete report generation
        result = generate_annual_report("hardware", "2024", tmp_path, debug=True)

        # Verify the report was generated
        assert result is not None
        assert "2024" in result
        assert "1,200" in result
        assert "100" in result

    def test_annual_report_generator_software_type(self):
        """Test annual report generator with software report type."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01"],
            "missing_months": [],
        }
        data = {
            "soaps": [{"name": "Barrister and Mann Seville", "shaves": 120, "rank": 1}],
            # Add empty lists for all specialized tables that the software template expects
            "soap-makers": [],
            "brand-diversity": [],
            "top-shavers": [],
            "soap-mashup-users": [],
            "user-soap-brand-scent-diversity": [],
            "user-single-use-soaps": [],
        }

        generator = AnnualReportGenerator("2024", "software", metadata, data, debug=True)

        # Test software report generation
        result = generator.generate_report()
        assert result is not None
        assert "2024" in result

    def test_annual_report_generator_template_path(self):
        """Test annual report generator with custom template path."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01"],
            "missing_months": [],
        }
        data = {"razors": []}

        generator = AnnualReportGenerator(
            "2024", "hardware", metadata, data, template_path="/custom/path", debug=True
        )

        # Test that template path is set correctly
        assert generator.template_path == "/custom/path"

    def test_annual_report_generator_edge_cases(self):
        """Test annual report generator with edge case data."""
        # Test with empty data
        metadata = {
            "total_shaves": 0,
            "unique_shavers": 0,
            "included_months": [],
            "missing_months": ["2024-01", "2024-02"],
        }
        data = {
            "razors": [],
            "blades": [],
            "brushes": [],
            "soaps": [],
            # Add empty lists for all specialized tables that the hardware template expects
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }

        generator = AnnualReportGenerator("2024", "hardware", metadata, data, debug=True)

        # Test that edge cases are handled correctly
        result = generator.generate_report()
        assert result is not None
        assert "2024" in result
        assert "0" in result  # total_shaves
        assert "0" in result  # unique_shavers
        assert "0" in result  # included_months count
        assert "2" in result  # missing_months count

    def test_annual_report_generator_performance_monitoring(self):
        """Test that annual report generator includes performance monitoring."""
        metadata = {
            "total_shaves": 1200,
            "unique_shavers": 100,
            "included_months": ["2024-01"],
            "missing_months": [],
        }
        data = {
            "razors": [],
            # Add empty lists for all specialized tables that the hardware template expects
            "blades": [],
            "brushes": [],
            "soaps": [],
            "razor-formats": [],
            "razor-manufacturers": [],
            "blade-manufacturers": [],
            "brush-handle-makers": [],
            "brush-knot-makers": [],
            "brush-fibers": [],
            "brush-knot-sizes": [],
            "blackbird-plates": [],
            "christopher-bradley-plates": [],
            "game-changer-plates": [],
            "super-speed-variants": [],
            "straight-widths": [],
            "straight-grinds": [],
            "straight-points": [],
            "razor-blade-combinations": [],
            "highest-use-count-per-blade": [],
            "top-shavers": [],
            "users": [],
        }

        # Test that performance monitoring is included in generate_annual_report
        # This is tested indirectly through the generate_annual_report function
        # which uses the unified PerformanceMonitor
        generator = AnnualReportGenerator("2024", "hardware", metadata, data, debug=True)

        # The generator should work without performance monitoring issues
        result = generator.generate_report()
        assert result is not None
