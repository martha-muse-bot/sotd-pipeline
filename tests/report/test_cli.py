"""
Tests for report phase CLI functionality.

Tests the CLI interface for the report phase, including argument parsing,
validation, and integration with the report generation logic.
"""

from unittest.mock import patch

import pytest

from sotd.report.cli import get_parser
from sotd.report.run import main


class TestReportCLI:
    """Test report CLI functionality."""

    def test_get_parser_creates_parser(self):
        """Test that get_parser creates a valid parser."""
        parser = get_parser()
        assert parser is not None
        assert parser.description is not None

    # Phase-specific tests only - basic validation covered by BaseCLIParser tests
    def test_type_argument_default(self):
        """Test type argument default value."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01"])
        assert args.type == "all"

    def test_type_argument_hardware(self):
        """Test hardware type argument."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--type", "hardware"])
        assert args.type == "hardware"

    def test_type_argument_software(self):
        """Test software type argument."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--type", "software"])
        assert args.type == "software"

    def test_type_argument_invalid(self):
        """Test invalid type argument raises error."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--month", "2023-01", "--type", "invalid"])

    # Annual report CLI tests
    def test_annual_argument_parsing(self):
        """Test annual argument parsing."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--year", "2023"])
        assert args.annual is True
        assert args.year == "2023"
        assert args.month is None
        assert args.range is None

    def test_annual_with_year_argument_validation(self):
        """Test annual with year argument validation."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--year", "2023"])
        assert args.annual is True
        assert args.year == "2023"

    def test_annual_with_range_argument_validation(self):
        """Test annual with range argument validation."""
        parser = get_parser()
        args = parser.parse_args(["--annual", "--range", "2021:2023"])
        assert args.annual is True
        assert args.range == "2021:2023"

    def test_annual_without_year_or_range_raises_error(self):
        """Test annual without year or range raises error."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual"])

    def test_annual_with_month_raises_error(self):
        """Test annual with month raises error."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--month", "2023-01"])

    def test_annual_with_year_and_range_raises_error(self):
        """Test annual with both year and range raises error."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--annual", "--year", "2023", "--range", "2021:2023"])

    def test_annual_help_text_includes_annual_options(self):
        """Test that help text includes annual options."""
        parser = get_parser()
        help_text = parser.format_help()
        assert "--annual" in help_text
        assert "annual report" in help_text.lower()

    def test_no_slug_argument_parsing(self):
        """Test --no-slug argument parsing."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--no-slug"])
        assert getattr(args, "no_slug", False) is True

    def test_no_slug_default_false(self):
        """Test that no_slug defaults to False when not provided."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01"])
        assert getattr(args, "no_slug", False) is False

    def test_annual_backward_compatibility_monthly(self):
        """Test that annual flag doesn't break monthly functionality."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01"])
        assert args.month == "2023-01"
        assert args.annual is False


class TestReportCLIUtilities:
    """Test report CLI utility functions."""

    def test_get_default_month_format(self):
        """Test default month format."""
        from sotd.report.cli import get_default_month

        month = get_default_month()
        # Should be in YYYY-MM format
        assert len(month) == 7
        assert month[4] == "-"

    def test_get_default_month_current_month(self):
        """Test default month is current month."""
        import datetime

        from sotd.report.cli import get_default_month

        month = get_default_month()
        current_month = datetime.datetime.now().strftime("%Y-%m")
        assert month == current_month


class TestReportMain:
    """Test report main function integration."""

    @patch("sotd.report.run.run_report")
    def test_main_with_month(self, mock_run_report):
        """Test main function with month argument."""
        with patch("sys.argv", ["report", "--month", "2023-01"]):
            main()

        mock_run_report.assert_called_once()

    @patch("sotd.report.run.run_report")
    def test_main_with_type(self, mock_run_report):
        """Test main function with type argument."""
        with patch("sys.argv", ["report", "--month", "2023-01", "--type", "software"]):
            main()

        mock_run_report.assert_called_once()

    @patch("sotd.report.run.run_report")
    def test_main_with_debug_and_force(self, mock_run_report):
        """Test main function with debug and force flags."""
        with patch("sys.argv", ["report", "--month", "2023-01", "--debug", "--force"]):
            main()

        mock_run_report.assert_called_once()

    @patch("sotd.report.run.run_report")
    def test_main_with_data_root_and_out_dir(self, mock_run_report):
        """Test main function with data dir argument."""
        with patch(
            "sys.argv",
            ["report", "--month", "2023-01", "--data-dir", "/output"],
        ):
            main()

        mock_run_report.assert_called_once()

    @patch("sotd.report.run.run_report")
    def test_main_no_arguments_raises_error(self, mock_run_report):
        """Test main function raises error with no arguments."""
        with patch("sys.argv", ["report"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_invalid_year_argument_raises_error(self):
        """Test main function raises error with invalid year argument."""
        with patch("sys.argv", ["report", "--year", "invalid"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_invalid_range_argument_raises_error(self):
        """Test main function raises error with invalid range argument."""
        with patch("sys.argv", ["report", "--range", "invalid"]):
            with pytest.raises(SystemExit):
                main()

    @patch("sotd.report.run.run_annual_report")
    def test_main_annual_with_year(self, mock_run_annual_report):
        """Test main function with annual and year arguments."""
        with patch("sys.argv", ["report", "--annual", "--year", "2023"]):
            main()

        mock_run_annual_report.assert_called_once()

    @patch("sotd.report.run.run_annual_report")
    def test_main_annual_with_range(self, mock_run_annual_report):
        """Test main function with annual and range arguments."""
        with patch("sys.argv", ["report", "--annual", "--range", "2021:2023"]):
            main()

        mock_run_annual_report.assert_called_once()

    @patch("sotd.report.run.run_annual_report")
    def test_main_annual_with_type(self, mock_run_annual_report):
        """Test main function with annual and type arguments."""
        with patch("sys.argv", ["report", "--annual", "--year", "2023", "--type", "software"]):
            main()

        mock_run_annual_report.assert_called_once()

    def test_main_annual_without_year_or_range_raises_error(self, capsys):
        """Test main function raises error for annual without year or range."""
        with patch("sys.argv", ["report", "--annual"]):
            with pytest.raises(SystemExit):
                main()

    def test_main_annual_with_month_raises_error(self, capsys):
        """Test main function raises error for annual with month."""
        with patch("sys.argv", ["report", "--annual", "--month", "2023-01"]):
            with pytest.raises(SystemExit):
                main()
