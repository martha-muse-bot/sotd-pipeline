"""
Tests for automatic Cartridge/Disposable blade matching functionality.

When a razor has format "Cartridge/Disposable", the blade should automatically
be matched to the Cartridge/Disposable blade entry regardless of the blade text.
"""

from unittest.mock import Mock

from sotd.match.run import match_record
from sotd.match.types import MatchResult
from sotd.match.utils.performance import PerformanceMonitor


class TestCartridgeBladeMatching:
    """Test automatic blade matching for Cartridge/Disposable razors."""

    def test_cartridge_razor_auto_matches_cartridge_blade(self):
        """Test that Cartridge/Disposable razors automatically match Cartridge/Disposable blades."""
        # Setup
        razor_matcher = Mock()
        blade_matcher = Mock()
        soap_matcher = Mock()
        brush_matcher = Mock()
        monitor = PerformanceMonitor()

        # Mock razor matcher to return Cartridge/Disposable format
        razor_matcher.match.return_value = MatchResult(
            original="Gillette Fusion",
            matched={"brand": "Gillette", "model": "Fusion", "format": "Cartridge/Disposable"},
            match_type="exact",
            pattern=None,
        )

        # Mock blade matcher to return the expected Cartridge/Disposable match
        expected_cartridge_match = MatchResult(
            original="Feather DE",  # Preserve original blade text
            matched={
                "brand": "Cartridge/Disposable",
                "model": "",
                "format": "Cartridge/Disposable",
            },
            match_type="auto_cartridge",
            pattern="cartridge_razor_format",
        )
        blade_matcher.match_cartridge_auto.return_value = expected_cartridge_match

        # Test record (using extract phase format)
        record = {
            "razor": {"original": "Gillette Fusion", "normalized": "gillette fusion"},
            "blade": {"original": "Feather DE", "normalized": "feather de"},
            "soap": {"original": "Test Soap", "normalized": "test soap"},
            "brush": {"original": "Test Brush", "normalized": "test brush"},
        }

        # Execute
        result = match_record(
            record, razor_matcher, blade_matcher, soap_matcher, brush_matcher, monitor
        )

        # Verify
        assert result["blade"].matched is not None
        assert result["blade"].matched["brand"] == "Cartridge/Disposable"
        assert result["blade"].matched["model"] == ""
        assert result["blade"].matched["format"] == "Cartridge/Disposable"
        assert result["blade"].match_type == "auto_cartridge"
        assert result["blade"].pattern == "cartridge_razor_format"

        # Verify original blade text is preserved
        assert result["blade"].original == "Feather DE"

        # Verify blade matcher was called with auto-matching method
        blade_matcher.match_cartridge_auto.assert_called_once_with("feather de")

    def test_cartridge_razor_preserves_original_blade_text(self):
        """Test that original blade text is preserved when auto-matching."""
        # Setup
        razor_matcher = Mock()
        blade_matcher = Mock()
        soap_matcher = Mock()
        brush_matcher = Mock()
        monitor = PerformanceMonitor()

        # Mock razor matcher to return Cartridge/Disposable format
        razor_matcher.match.return_value = MatchResult(
            original="Harry's Razor",
            matched={"brand": "Harry's", "model": "Razor", "format": "Cartridge/Disposable"},
            match_type="exact",
            pattern=None,
        )

        # Mock blade matcher to return the expected Cartridge/Disposable match
        original_blade_text = "Some random blade text that doesn't matter"
        expected_cartridge_match = MatchResult(
            original=original_blade_text,
            matched={
                "brand": "Cartridge/Disposable",
                "model": "",
                "format": "Cartridge/Disposable",
            },
            match_type="auto_cartridge",
            pattern="cartridge_razor_format",
        )
        blade_matcher.match_cartridge_auto.return_value = expected_cartridge_match

        # Test record (using extract phase format)
        record = {
            "razor": {"original": "Harry's Razor", "normalized": "harry's razor"},
            "blade": {"original": original_blade_text, "normalized": original_blade_text.lower()},
            "soap": {"original": "Test Soap", "normalized": "test soap"},
            "brush": {"original": "Test Brush", "normalized": "test brush"},
        }

        # Execute
        result = match_record(
            record, razor_matcher, blade_matcher, soap_matcher, brush_matcher, monitor
        )

        # Verify original blade text is preserved
        assert result["blade"].original == original_blade_text

    def test_non_cartridge_razor_uses_normal_matching(self):
        """Test that non-cartridge razors use normal blade matching logic."""
        # Setup
        razor_matcher = Mock()
        blade_matcher = Mock()
        soap_matcher = Mock()
        brush_matcher = Mock()
        monitor = PerformanceMonitor()

        # Mock razor matcher to return DE format
        razor_matcher.match.return_value = MatchResult(
            original="Merkur 34C",
            matched={"brand": "Merkur", "model": "34C", "format": "DE"},
            match_type="exact",
            pattern=None,
        )

        # Mock blade matcher to return normal match
        blade_matcher.match_with_context.return_value = MatchResult(
            original="Feather DE",
            matched={"brand": "Feather", "model": "DE", "format": "DE"},
            match_type="exact",
            pattern=None,
        )

        # Test record (using extract phase format)
        record = {
            "razor": {"original": "Merkur 34C", "normalized": "merkur 34c"},
            "blade": {"original": "Feather DE", "normalized": "feather de"},
            "soap": {"original": "Test Soap", "normalized": "test soap"},
            "brush": {"original": "Test Brush", "normalized": "test brush"},
        }

        # Execute
        result = match_record(
            record, razor_matcher, blade_matcher, soap_matcher, brush_matcher, monitor
        )

        # Verify normal matching was used
        assert result["blade"].matched["brand"] == "Feather"
        blade_matcher.match_with_context.assert_called_once()
        blade_matcher.match_cartridge_auto.assert_not_called()

    def test_cartridge_razor_with_no_blade_info(self):
        """Test that Cartridge/Disposable razors work even when no blade info is provided."""
        # Setup
        razor_matcher = Mock()
        blade_matcher = Mock()
        soap_matcher = Mock()
        brush_matcher = Mock()
        monitor = PerformanceMonitor()

        # Mock razor matcher to return Cartridge/Disposable format
        razor_matcher.match.return_value = MatchResult(
            original="Gillette Mach3",
            matched={"brand": "Gillette", "model": "Mach3", "format": "Cartridge/Disposable"},
            match_type="exact",
            pattern=None,
        )

        # Mock blade matcher to return the expected Cartridge/Disposable match
        expected_cartridge_match = MatchResult(
            original="",
            matched={
                "brand": "Cartridge/Disposable",
                "model": "",
                "format": "Cartridge/Disposable",
            },
            match_type="auto_cartridge",
            pattern="cartridge_razor_format",
        )
        blade_matcher.match_cartridge_auto.return_value = expected_cartridge_match

        # Test record (using extract phase format)
        record = {
            "razor": {"original": "Gillette Mach3", "normalized": "gillette mach3"},
            "blade": {"original": "", "normalized": ""},
            "soap": {"original": "Test Soap", "normalized": "test soap"},
            "brush": {"original": "Test Brush", "normalized": "test brush"},
        }

        # Execute
        result = match_record(
            record, razor_matcher, blade_matcher, soap_matcher, brush_matcher, monitor
        )

        # Verify
        assert result["blade"].matched is not None
        assert result["blade"].matched["brand"] == "Cartridge/Disposable"
        assert result["blade"].matched["model"] == ""
        assert result["blade"].matched["format"] == "Cartridge/Disposable"

    def test_cartridge_razor_case_insensitive_format_matching(self):
        """Test that Cartridge/Disposable format matching is case insensitive."""
        # Setup
        razor_matcher = Mock()
        blade_matcher = Mock()
        soap_matcher = Mock()
        brush_matcher = Mock()
        monitor = PerformanceMonitor()

        # Mock razor matcher to return lowercase format
        razor_matcher.match.return_value = MatchResult(
            original="Gillette Fusion",
            matched={
                "brand": "Gillette",
                "model": "Fusion",
                "format": "cartridge/disposable",  # lowercase
            },
            match_type="exact",
            pattern=None,
        )

        # Mock blade matcher to return the expected Cartridge/Disposable match
        expected_cartridge_match = MatchResult(
            original="Feather DE",
            matched={
                "brand": "Cartridge/Disposable",
                "model": "",
                "format": "Cartridge/Disposable",
            },
            match_type="auto_cartridge",
            pattern="cartridge_razor_format",
        )
        blade_matcher.match_cartridge_auto.return_value = expected_cartridge_match

        # Test record (using extract phase format)
        record = {
            "razor": {"original": "Gillette Fusion", "normalized": "gillette fusion"},
            "blade": {"original": "Feather DE", "normalized": "feather de"},
            "soap": {"original": "Test Soap", "normalized": "test soap"},
            "brush": {"original": "Test Brush", "normalized": "test brush"},
        }

        # Execute
        result = match_record(
            record, razor_matcher, blade_matcher, soap_matcher, brush_matcher, monitor
        )

        # Verify
        assert result["blade"].matched is not None
        assert result["blade"].matched["brand"] == "Cartridge/Disposable"
        blade_matcher.match_cartridge_auto.assert_called_once()
