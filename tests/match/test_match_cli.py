"""Integration tests for match CLI functionality."""

from unittest.mock import patch

import pytest

from sotd.match.cli import get_parser
from sotd.match.run import main


class TestMatchCLI:
    """Test match CLI argument parsing and validation."""

    def test_get_parser_creates_parser(self):
        """Test that get_parser returns a valid ArgumentParser."""
        parser = get_parser()
        assert parser is not None
        assert (
            parser.description
            == "Match razors, blades, soaps, and brushes from extracted SOTD data"
        )

    # Note: Basic argument validation (month, year, range, start/end) is tested in
    # tests/cli_utils/test_base_parser.py. Only phase-specific tests are included here.

    def test_mode_argument_default(self):
        """Test mode argument default value."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01"])
        assert args.mode == "match"

    def test_mode_argument_custom(self):
        """Test custom mode argument."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--mode", "analyze_unmatched_razors"])
        assert args.mode == "analyze_unmatched_razors"

    def test_mode_argument_invalid(self):
        """Test invalid mode argument raises error."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--month", "2023-01", "--mode", "invalid_mode"])

    def test_parallel_processing_arguments(self):
        """Test parallel processing argument parsing."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--parallel"])
        assert args.parallel is True
        assert args.sequential is False

    def test_sequential_processing_arguments(self):
        """Test sequential processing argument parsing."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--sequential"])
        assert args.sequential is True
        assert args.parallel is False

    def test_max_workers_argument_default(self):
        """Test max-workers argument default value."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01"])
        assert args.max_workers == 8

    def test_max_workers_argument_custom(self):
        """Test custom max-workers argument."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2023-01", "--max-workers", "8"])
        assert args.max_workers == 8

    def test_parallel_sequential_mutually_exclusive(self):
        """Test that parallel and sequential are mutually exclusive."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["--month", "2023-01", "--parallel", "--sequential"])


class TestMatchMain:
    """Test match main function integration."""

    @patch("sotd.match.run.run_match")
    def test_main_with_match_mode(self, mock_run_match):
        """Test main function with match mode."""
        with patch("sys.argv", ["match", "--month", "2023-01"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_analysis")
    def test_main_with_analyze_mode(self, mock_run_analysis):
        """Test main function with analyze mode."""
        with patch(
            "sys.argv", ["match", "--month", "2023-01", "--mode", "analyze_unmatched_razors"]
        ):
            main()

        mock_run_analysis.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_year(self, mock_run_match):
        """Test main function with year argument."""
        with patch("sys.argv", ["match", "--year", "2023"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_range(self, mock_run_match):
        """Test main function with range argument."""
        with patch("sys.argv", ["match", "--range", "2023-01:2023-12"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_start_end(self, mock_run_match):
        """Test main function with start/end arguments."""
        with patch("sys.argv", ["match", "--start", "2023-01", "--end", "2023-12"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_debug_and_force(self, mock_run_match):
        """Test main function with debug and force flags."""
        with patch("sys.argv", ["match", "--month", "2023-01", "--debug", "--force"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_parallel_processing(self, mock_run_match):
        """Test main function with parallel processing."""
        with patch("sys.argv", ["match", "--month", "2023-01", "--parallel"]):
            main()

        mock_run_match.assert_called_once()

    @patch("sotd.match.run.run_match")
    def test_main_with_sequential_processing(self, mock_run_match):
        """Test main function with sequential processing."""
        with patch("sys.argv", ["match", "--month", "2023-01", "--sequential"]):
            main()

        mock_run_match.assert_called_once()
