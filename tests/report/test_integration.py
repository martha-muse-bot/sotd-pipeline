"""Integration tests for report generation."""

import pytest

from sotd.report.monthly_generator import MonthlyReportGenerator
from sotd.report.process import generate_report_content


class TestReportIntegration:
    """Integration tests for report generation."""

    def test_hardware_report_generation(self, template_dir):
        """Test complete hardware report generation with sample data."""
        # Sample aggregated data
        metadata = {
            "month": "2025-01",
            "total_shaves": 1000,
            "unique_shavers": 50,
            "avg_shaves_per_user": 20.0,
        }

        data = {
            "razors": [
                {"name": "Gillette Super Speed", "shaves": 25, "unique_users": 12, "rank": 1},
                {"name": "Karve CB", "shaves": 18, "unique_users": 8, "rank": 2},
            ],
            "razor-manufacturers": [
                {"brand": "Gillette", "shaves": 30, "unique_users": 15, "rank": 1},
                {"brand": "Karve", "shaves": 18, "unique_users": 8, "rank": 2},
            ],
            "razor-formats": [
                {"format": "DE", "shaves": 45, "unique_users": 20, "rank": 1},
                {"format": "SE", "shaves": 5, "unique_users": 3, "rank": 2},
            ],
            "blades": [
                {"name": "Gillette Nacet", "shaves": 30, "unique_users": 15, "rank": 1},
                {"name": "Personna Lab Blue", "shaves": 20, "unique_users": 10, "rank": 2},
            ],
            "blade-manufacturers": [
                {"brand": "Gillette", "shaves": 35, "unique_users": 18, "rank": 1},
                {"brand": "Personna", "shaves": 25, "unique_users": 12, "rank": 2},
            ],
            "brushes": [
                {"name": "Simpson Chubby 2", "shaves": 15, "unique_users": 8, "rank": 1},
                {"name": "AP Shave Co", "shaves": 12, "unique_users": 6, "rank": 2},
            ],
            "brush-handle-makers": [
                {"handle_maker": "Simpson", "shaves": 15, "unique_users": 8, "rank": 1},
                {"handle_maker": "AP Shave Co", "shaves": 12, "unique_users": 6, "rank": 2},
            ],
            "brush-knot-makers": [
                {"brand": "Simpson", "shaves": 15, "unique_users": 8, "rank": 1},
                {"brand": "AP Shave Co", "shaves": 12, "unique_users": 6, "rank": 2},
            ],
            "brush-fibers": [
                {"fiber": "Badger", "shaves": 20, "unique_users": 10, "rank": 1},
                {"fiber": "Synthetic", "shaves": 10, "unique_users": 5, "rank": 2},
            ],
            "brush-knot-sizes": [
                {"knot_size": "24mm", "shaves": 15, "unique_users": 8, "rank": 1},
                {"knot_size": "26mm", "shaves": 12, "unique_users": 6, "rank": 2},
            ],
            "users": [
                {"user": "user1", "shaves": 31, "missed_days": 0, "position": 1, "rank": 1},
                {"user": "user2", "shaves": 28, "missed_days": 3, "position": 2, "rank": 2},
            ],
        }

        # Generate report content with custom template
        report_content = generate_report_content(
            "hardware", metadata, data, template_path=str(template_dir), debug=False
        )

        # Verify report structure
        assert "# Hardware Report - January 2025" in report_content
        assert "**Total Shaves:** 1,000" in report_content
        assert "**Unique Shavers:** 50" in report_content
        assert "Welcome to your SOTD Hardware Report for January 2025" in report_content
        assert "Average shaves per user: 20.0" in report_content
        assert "## Notes & Caveats" in report_content
        assert "Custom template content for testing" in report_content
        assert "## Razors" in report_content
        assert "## Blades" in report_content
        assert "## Blade Manufacturers" in report_content
        assert "## Brushes" in report_content
        assert "## Top Shavers" in report_content

        # Verify that tables are generated (should contain actual table content)
        assert "| Format" in report_content  # Razor Formats table header
        assert "| Name" in report_content  # Razors table header (uses actual column name)
        assert "| Brand" in report_content  # Razor/Blade Manufacturers table header
        assert "| Handle Maker" in report_content  # Brush Handle Makers table header
        assert "| Fiber" in report_content  # Knot Fibers table header
        assert "| User" in report_content  # User tables headers
        assert "Gillette Super Speed" in report_content
        assert "Gillette Nacet" in report_content
        assert "Simpson Chubby 2" in report_content
        assert "user1" in report_content

    def test_unified_monthly_generator(self, template_dir):
        """Test the unified monthly generator directly."""
        # Sample aggregated data
        metadata = {
            "month": "2025-01",
            "total_shaves": 1000,
            "unique_shavers": 50,
            "avg_shaves_per_user": 20.0,
            "median_shaves_per_user": 18.0,
            "unique_razors": 25,
            "unique_blades": 30,
            "unique_brushes": 20,
            "unique_soaps": 15,
            "unique_brands": 12,
            "total_samples": 50,
            "sample_percentage": 5.0,
            "sample_users": 8,
            "sample_brands": 6,
        }

        data = {
            "razors": [{"name": "Gillette Super Speed", "shaves": 25, "rank": 1}],
            "blades": [{"name": "Gillette Nacet", "shaves": 20, "rank": 1}],
            "brushes": [{"name": "Simpson Chubby 2", "shaves": 15, "rank": 1}],
            "soaps": [{"name": "Test Soap", "shaves": 30, "rank": 1}],
            "soap-makers": [{"brand": "Test Brand", "shaves": 30, "rank": 1}],
            "brand-diversity": [{"brand": "Test Brand", "unique_soaps": 1, "rank": 1}],
            "user-soap-brand-scent-diversity": [
                {"user": "testuser", "unique_combinations": 1, "shaves": 30, "rank": 1}
            ],
            "razor-formats": [{"format": "DE", "shaves": 25, "rank": 1}],
            "razor-manufacturers": [{"brand": "Gillette", "shaves": 25, "rank": 1}],
            "blade-manufacturers": [{"brand": "Gillette", "shaves": 20, "rank": 1}],
            "brush-handle-makers": [{"handle_maker": "Simpson", "shaves": 15, "rank": 1}],
            "brush-knot-makers": [{"brand": "Simpson", "shaves": 15, "rank": 1}],
            "brush-fibers": [{"fiber": "Badger", "shaves": 15, "rank": 1}],
            "brush-knot-sizes": [{"knot_size": "24mm", "shaves": 15, "rank": 1}],
            "users": [{"user": "testuser", "shaves": 50, "missed_days": 0, "rank": 1}],
        }

        # Test hardware report generation
        hardware_generator = MonthlyReportGenerator(
            "hardware", metadata, data, template_path=str(template_dir)
        )
        hardware_report = hardware_generator.generate_notes_and_caveats()

        assert "Hardware Report" in hardware_report
        assert "1,000" in hardware_report
        assert "50" in hardware_report

        # Test software report generation
        software_generator = MonthlyReportGenerator(
            "software", metadata, data, template_path=str(template_dir)
        )
        software_report = software_generator.generate_notes_and_caveats()

        assert "Software Report" in software_report
        assert "1,000" in software_report
        assert "50" in software_report

    def test_software_report_generation(self, template_dir):
        """Test complete software report generation with sample data."""
        # Sample aggregated data
        metadata = {
            "month": "2025-01",
            "total_shaves": 500,
            "unique_shavers": 25,
            "unique_soaps": 100,
            "unique_brands": 20,
        }

        data = {
            "soaps": [
                {"name": "Declaration Grooming", "shaves": 20, "unique_users": 10, "rank": 1},
                {"name": "Stirling Soap Co", "shaves": 15, "unique_users": 8, "rank": 2},
            ],
            "soap-makers": [
                {"brand": "Declaration Grooming", "shaves": 20, "unique_users": 10, "rank": 1},
                {"brand": "Stirling Soap Co", "shaves": 15, "unique_users": 8, "rank": 2},
            ],
            "brand-diversity": [
                {"brand": "Declaration Grooming", "unique_soaps": 5, "rank": 1},
                {"brand": "Stirling Soap Co", "unique_soaps": 5, "rank": 2},
            ],
            "user-soap-brand-scent-diversity": [],
            "users": [
                {"user": "user1", "shaves": 31, "missed_days": 0, "position": 1, "rank": 1},
                {"user": "user2", "shaves": 28, "missed_days": 3, "position": 2, "rank": 2},
            ],
        }

        # Generate report content with custom template
        report_content = generate_report_content(
            "software", metadata, data, template_path=str(template_dir), debug=False
        )

        # Verify report structure
        assert "# Software Report - January 2025" in report_content
        assert "**Total Shaves:** 500" in report_content
        assert "**Unique Shavers:** 25" in report_content
        assert "Welcome to your SOTD Lather Log for January 2025" in report_content
        assert "500 shave reports from 25 distinct shavers" in report_content
        assert "100 distinct soaps from 20 distinct brands" in report_content
        assert "## Notes & Caveats" in report_content
        assert "## Soap Makers" in report_content
        assert "## Soaps" in report_content
        assert "## Brand Diversity" in report_content
        assert "## Top Shavers" in report_content

        # Verify that tables are generated
        assert "| Brand" in report_content  # Soap Makers table header
        assert "| Name" in report_content  # Soaps table header
        assert "| Brand" in report_content  # Brand Diversity table header
        assert "Declaration Grooming" in report_content
        assert "Stirling Soap Co" in report_content
        assert "user1" in report_content

    def test_report_with_empty_data(self, template_dir):
        """Test report generation with empty data."""
        metadata = {"month": "2025-01", "total_shaves": 0, "unique_shavers": 0}

        data = {}

        # The system should fail fast with an exception when there's no data
        # This follows the project's fail-fast philosophy
        with pytest.raises(ValueError, match="No data provided for report generation"):
            generate_report_content(
                "hardware", metadata, data, template_path=str(template_dir), debug=False
            )

    def test_report_with_delta_calculations(self, template_dir):
        """Test report generation with historical data for delta calculations."""
        metadata = {
            "month": "2025-01",
            "total_shaves": 1000,
            "unique_shavers": 50,
            "avg_shaves_per_user": 20.0,  # 1000 / 50 = 20
        }

        data = {
            "razors": [
                {"name": "Gillette Super Speed", "shaves": 25, "unique_users": 12, "rank": 1},
                {"name": "Karve CB", "shaves": 18, "unique_users": 8, "rank": 2},
            ],
            "blades": [
                {"name": "Gillette Nacet", "shaves": 20, "unique_users": 10, "rank": 1},
            ],
            "brushes": [{"name": "Simpson Chubby 2", "shaves": 15, "unique_users": 8, "rank": 1}],
            "brush-handle-makers": [
                {"handle_maker": "Simpson", "shaves": 15, "unique_users": 8, "rank": 1}
            ],
            "brush-knot-makers": [{"brand": "Simpson", "shaves": 15, "unique_users": 8, "rank": 1}],
            "brush-fibers": [{"fiber": "Badger", "shaves": 15, "unique_users": 8, "rank": 1}],
            "brush-knot-sizes": [{"knot_size": "24mm", "shaves": 15, "unique_users": 8, "rank": 1}],
            "blade-manufacturers": [
                {"brand": "Gillette", "shaves": 20, "unique_users": 10, "rank": 1}
            ],
            "razor-formats": [{"format": "DE", "shaves": 43, "unique_users": 20, "rank": 1}],
            "razor-manufacturers": [
                {"brand": "Gillette", "shaves": 25, "unique_users": 12, "rank": 1}
            ],
            "users": [{"user": "testuser", "shaves": 50, "missed_days": 0, "rank": 1}],
        }

        comparison_data = {
            "previous month": (
                {"month": "2024-12"},  # metadata
                {  # data
                    "razors": [
                        {"name": "Karve CB", "shaves": 20, "unique_users": 10, "rank": 1},
                        {
                            "name": "Gillette Super Speed",
                            "shaves": 15,
                            "unique_users": 8,
                            "rank": 2,
                        },
                    ]
                },
            )
        }

        # Generate report content with deltas
        report_content = generate_report_content(
            "hardware",
            metadata,
            data,
            comparison_data,
            template_path=str(template_dir),
            debug=False,
        )

        # Should include delta column
        # The system uses default comparison periods (previous month, previous year, 5 years ago)
        # and shows "n/a" values when comparison data doesn't match these periods
        assert "Δ vs Dec 2024" in report_content  # Previous month
        assert "Δ vs Jan 2024" in report_content  # Previous year
        assert "n/a" in report_content  # Delta values should be n/a when no match found
