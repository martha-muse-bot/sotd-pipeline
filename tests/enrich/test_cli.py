"""
Tests for the enrich phase CLI module.
"""

from pathlib import Path

import pytest

from sotd.enrich.cli import get_parser


class TestEnrichCLI:
    """Test cases for the enrich phase CLI."""

    def test_get_parser_returns_base_parser(self):
        """Test that get_parser returns a BaseCLIParser instance."""
        parser = get_parser()
        assert parser is not None
        assert hasattr(parser, "parse_args")
        assert hasattr(parser, "add_argument")

    def test_common_arguments_present(self):
        """Test that common arguments from BaseCLIParser are present."""
        parser = get_parser()
        args = parser.parse_args(["--month", "2025-01"])

        # Test common arguments
        assert args.month == "2025-01"
        assert args.data_dir == Path("data")
        assert not args.debug
        assert not args.force

    # Note: Basic argument validation (month, year, range, start/end) is tested in
    # tests/cli_utils/test_base_parser.py. Only phase-specific tests are included here.

    def test_help_text_includes_enrich_description(self):
        """Test that help text includes enrich-specific description."""
        parser = get_parser()
        help_text = parser.format_help()

        assert "Enrich SOTD data with detailed specifications" in help_text
        assert "--month" in help_text
        assert "--year" in help_text
        assert "--range" in help_text
        assert "--start" in help_text
        assert "--end" in help_text
        assert "--data-dir" in help_text
        assert "--debug" in help_text
        assert "--force" in help_text

    def test_parallel_processing_arguments_present(self):
        """Test that enrich CLI includes parallel processing arguments like other phases."""
        parser = get_parser()
        help_text = parser.format_help()

        # Should have parallel processing arguments (standard for all phases)
        assert "parallel" in help_text.lower()
        assert "sequential" in help_text.lower()
        assert "max-workers" in help_text.lower()

        # Should NOT have enrich-specific arguments that don't exist
        assert "mode" not in help_text.lower()

    def test_no_date_arguments_raises_error(self):
        """Test that no date arguments raises error (date required by main run.py)."""
        parser = get_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])
