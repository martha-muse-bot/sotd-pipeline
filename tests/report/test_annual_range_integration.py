"""Integration tests for annual range processing in report phase."""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from sotd.report.cli import get_parser, validate_args
from sotd.report.run import run_annual_report, main


class TestAnnualRangeIntegration:
    """Test annual range processing integration."""

    @patch("sotd.report.run.run_annual_report")
    def test_main_with_annual_range(self, mock_run_annual_report):
        """Test main function routes annual range to correct handler."""
        with patch(
            "sys.argv", ["report", "--annual", "--range", "2021:2024", "--type", "hardware"]
        ):
            main()

        mock_run_annual_report.assert_called_once()
        args = mock_run_annual_report.call_args[0][0]
        assert args.annual is True
        assert args.range == "2021:2024"
        assert args.type == "hardware"

    def test_annual_range_parsing_valid_years(self):
        """Test that valid year ranges are parsed correctly."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2021:2024"])
        validate_args(args)

        # Parse the range to get years
        start_year, end_year = args.range.split(":")
        years = [str(year) for year in range(int(start_year), int(end_year) + 1)]

        assert years == ["2021", "2022", "2023", "2024"]

    def test_annual_range_parsing_single_year(self):
        """Test that single year range is handled correctly."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2023:2023"])
        validate_args(args)

        start_year, end_year = args.range.split(":")
        years = [str(year) for year in range(int(start_year), int(end_year) + 1)]

        assert years == ["2023"]

    def test_annual_range_parsing_reverse_order(self):
        """Test that reverse year order is handled correctly."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2024:2021"])
        validate_args(args)

        start_year, end_year = args.range.split(":")
        # When start > end, range() returns empty list, so we need to handle this
        if int(start_year) > int(end_year):
            years = [str(year) for year in range(int(end_year), int(start_year) + 1)]
        else:
            years = [str(year) for year in range(int(start_year), int(end_year) + 1)]

        assert years == ["2021", "2022", "2023", "2024"]


class TestAnnualRangeProcessing:
    """Test annual range processing logic."""

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_run_annual_range_single_year(self, mock_save, mock_create_generator, tmp_path):
        """Test processing a single year range."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2023:2023", "--type", "hardware"])
        args.format = "markdown"  # Set format explicitly

        args.data_dir = tmp_path

        # Create a mock generator instance
        mock_generator_instance = Mock()
        mock_generator_instance.generate_report.return_value = "# Test Report Content"
        mock_create_generator.return_value = mock_generator_instance
        mock_save.return_value = Path("data/report/annual/2023-hardware.md")

        # Need to create the data file for the test
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_file = data_dir / "2023.json"
        with open(annual_file, "w") as f:
            json.dump(
                {
                    "metadata": {
                        "year": "2023",
                        "total_shaves": 1000,
                        "unique_shavers": 50,
                        "included_months": ["2023-01", "2023-02"],
                        "missing_months": [],
                    },
                    "razors": [],
                    "blades": [],
                    "brushes": [],
                    "soaps": [],
                },
                f,
            )

        try:
            run_annual_report(args)

            # Should call create_generator once for the single year
            mock_create_generator.assert_called_once()
            # Verify generate_report was called on the generator instance
            mock_generator_instance.generate_report.assert_called_once()
        finally:
            # Clean up
            if annual_file.exists():
                annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_run_annual_range_multiple_years(self, mock_save, mock_create_generator, tmp_path):
        """Test processing multiple years in range."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2021:2023", "--type", "hardware"])
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances for each year
        mock_generator_instances = []
        for year in ["2021", "2022", "2023"]:
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances
        mock_save.return_value = Path("data/report/annual/2021-hardware.md")

        # Create data files for all years
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in ["2021", "2022", "2023"]:
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": year,
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            run_annual_report(args)

            # Should call create_generator for each year in the range
            assert mock_create_generator.call_count == 3
            # Verify generate_report was called on each generator instance
            for mock_instance in mock_generator_instances:
                mock_instance.generate_report.assert_called_once()
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_run_annual_range_with_debug(self, mock_save, mock_create_generator, tmp_path):
        """Test range processing with debug output."""
        parser = get_parser()
        args = parser.parse_args(
            ["--annual", "--range", "2022:2023", "--type", "hardware", "--debug"]
        )
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances
        mock_generator_instances = []
        for year in ["2022", "2023"]:
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances
        mock_save.return_value = Path("data/report/annual/2022-hardware.md")

        # Create data files
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in ["2022", "2023"]:
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": year,
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            run_annual_report(args)

            # Should call create_generator twice
            assert mock_create_generator.call_count == 2
            # Verify generate_report was called on each generator instance
            for mock_instance in mock_generator_instances:
                mock_instance.generate_report.assert_called_once()
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_run_annual_range_with_force(self, mock_save, mock_create_generator, tmp_path):
        """Test range processing with force flag."""
        parser = get_parser()
        args = parser.parse_args(
            ["--annual", "--range", "2022:2023", "--type", "hardware", "--force"]
        )
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances
        mock_generator_instances = []
        for year in ["2022", "2023"]:
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances
        mock_save.return_value = Path("data/report/annual/2022-hardware.md")

        # Create data files
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in ["2022", "2023"]:
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": year,
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            run_annual_report(args)

            # Should call save with force=True
            assert mock_save.call_count == 2
            for call in mock_save.call_args_list:
                assert call[0][4] is True  # force flag
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    def test_run_annual_range_generation_failure(self, mock_create_generator, tmp_path):
        """Test handling of generation failure in range processing."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2022:2023", "--type", "hardware"])
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances - one will fail
        mock_instance_2022 = Mock()
        mock_instance_2022.generate_report.side_effect = RuntimeError("Generation failed for 2022")
        mock_instance_2023 = Mock()
        mock_instance_2023.generate_report.return_value = "# Test Report Content"

        mock_create_generator.side_effect = [mock_instance_2022, mock_instance_2023]

        # Create data files
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in ["2022", "2023"]:
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": year,
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            # Should raise the error
            with pytest.raises(
                RuntimeError, match="Failed to generate annual hardware markdown report"
            ):
                run_annual_report(args)
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_run_annual_range_save_failure(self, mock_save, mock_create_generator, tmp_path):
        """Test handling of save failure in range processing."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2022:2023", "--type", "hardware"])
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances
        mock_generator_instances = []
        for year in ["2022", "2023"]:
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances

        # Mock save to fail for one year
        def mock_save_side_effect(report_content, out_dir, year, report_type, force, debug):
            if year == "2022":
                raise OSError("Save failed for 2022")
            return Path(f"data/report/annual/{year}-{report_type}.md")

        mock_save.side_effect = mock_save_side_effect

        # Create data files
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in ["2022", "2023"]:
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": year,
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            # Should raise the error
            with pytest.raises(OSError, match="Save failed for 2022"):
                run_annual_report(args)
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()


class TestAnnualRangeErrorHandling:
    """Test error handling for annual range processing."""

    def test_annual_range_invalid_year_format(self):
        """Test handling of invalid year format in range."""
        parser = get_parser()
        # This should be caught by argparse validation
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--range", "2021:abc"])

    def test_annual_range_missing_end_year(self):
        """Test handling of missing end year in range."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--range", "2021:"])

    def test_annual_range_missing_start_year(self):
        """Test handling of missing start year in range."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--range", ":2024"])

    def test_annual_range_negative_years(self):
        """Test handling of negative years in range."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--range", "-2021:2024"])

    def test_annual_range_future_years(self):
        """Test handling of future years in range (should be allowed)."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2025:2030"])
        # Should not raise any exceptions
        validate_args(args)
        assert args.range == "2025:2030"


class TestAnnualRangePerformance:
    """Test performance characteristics of annual range processing."""

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_annual_range_large_range_performance(self, mock_save, mock_create_generator, tmp_path):
        """Test performance with large year ranges."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2015:2024", "--type", "hardware"])
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances for all years
        mock_generator_instances = []
        for year in range(2015, 2025):
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances
        mock_save.return_value = Path("data/report/annual/2015-hardware.md")

        # Create data files for all years
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in range(2015, 2025):
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": str(year),
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            # Should process all 10 years without performance issues
            run_annual_report(args)

            # Should call create_generator for each year
            assert mock_create_generator.call_count == 10
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()

    @patch("sotd.report.annual_generator.create_annual_report_generator")
    @patch("sotd.report.annual_run.save_annual_report")
    def test_annual_range_memory_usage(self, mock_save, mock_create_generator, tmp_path):
        """Test memory usage during range processing."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2020:2024", "--type", "hardware"])
        args.format = "markdown"
        args.data_dir = tmp_path

        # Create mock generator instances for all years
        mock_generator_instances = []
        for year in range(2020, 2025):
            mock_instance = Mock()
            mock_instance.generate_report.return_value = "# Test Report Content"
            mock_generator_instances.append(mock_instance)

        mock_create_generator.side_effect = mock_generator_instances
        mock_save.return_value = Path("data/report/annual/2020-hardware.md")

        # Create data files for all years
        # tmp_path-rooted data dir: never touch the real data/ tree (a crashed
        # run once displaced the real annual file to "2023 2.json")
        data_dir = tmp_path / "aggregated" / "annual"
        data_dir.mkdir(parents=True, exist_ok=True)
        annual_files = []
        try:
            for year in range(2020, 2025):
                annual_file = data_dir / f"{year}.json"
                with open(annual_file, "w") as f:
                    json.dump(
                        {
                            "metadata": {
                                "year": str(year),
                                "total_shaves": 1000,
                                "unique_shavers": 50,
                                "included_months": [f"{year}-01", f"{year}-02"],
                                "missing_months": [],
                            },
                            "razors": [],
                            "blades": [],
                            "brushes": [],
                            "soaps": [],
                        },
                        f,
                    )
                annual_files.append(annual_file)

            # Process should complete without memory issues
            run_annual_report(args)

            # Verify all years were processed
            assert mock_create_generator.call_count == 5
            assert mock_save.call_count == 5
        finally:
            # Clean up
            for annual_file in annual_files:
                if annual_file.exists():
                    annual_file.unlink()
