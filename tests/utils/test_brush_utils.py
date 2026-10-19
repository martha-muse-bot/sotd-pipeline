"""Tests for brush utilities module."""

from sotd.utils.brush_utils import extract_fiber, extract_knot_size


class TestExtractKnotSize:
    """Test knot size extraction functionality."""

    def test_mm_standalone_patterns(self):
        """Test standalone mm patterns."""
        assert extract_knot_size("27mm") == 27.0
        assert extract_knot_size("27.5mm") == 27.5
        assert extract_knot_size("27 mm") == 27.0
        assert extract_knot_size("27.5 mm") == 27.5

    def test_dimension_patterns(self):
        """Test dimension patterns like '27x50'."""
        assert extract_knot_size("27x50") == 27.0
        assert extract_knot_size("27.5x50") == 27.5
        assert extract_knot_size("27 × 50") == 27.0

    def test_conservative_range(self):
        """Test conservative range patterns (20-35mm)."""
        assert extract_knot_size("25") == 25.0
        assert extract_knot_size("30.5") == 30.5
        assert extract_knot_size("35") == 35.0
        # Should not match numbers outside range
        assert extract_knot_size("15") is None
        assert extract_knot_size("40") is None

    def test_no_match(self):
        """Test cases with no match."""
        assert extract_knot_size("") is None
        assert extract_knot_size(None) is None
        assert extract_knot_size("no numbers here") is None
        # Note: 15mm and 40mm should match the mm_standalone pattern even if outside conservative range
        # The conservative range only applies to standalone numbers without 'mm'
        assert extract_knot_size("15mm") == 15.0  # Should match mm pattern
        assert extract_knot_size("40mm") == 40.0  # Should match mm pattern
        # These should not match the conservative range pattern
        assert extract_knot_size("15") is None  # Too small for conservative range
        assert extract_knot_size("40") is None  # Too large for conservative range


class TestExtractFiber:
    """Test fiber extraction functionality."""

    def test_mixed_badger_boar(self):
        """Test mixed badger/boar patterns."""
        assert extract_fiber("mixed badger boar") == "Mixed Badger/Boar"
        assert extract_fiber("badger boar hybrid") == "Mixed Badger/Boar"
        assert extract_fiber("fusion brush") == "Mixed Badger/Boar"

    def test_handle_hybrid_is_not_mixed_fiber(self):
        """Handle material 'Hybrid' must not classify as Mixed Badger/Boar."""
        assert extract_fiber("Virginia Cheng - Silvertip Badger Dogwood Hybrid 26mm") == "Badger"
        assert extract_fiber("Dogwood Handcrafts Hybrid / Maggard Boar") == "Boar"
        assert extract_fiber("Dogwood Hybrid") is None

    def test_synthetic_patterns(self):
        """Test synthetic fiber patterns."""
        assert extract_fiber("synthetic") == "Synthetic"
        assert extract_fiber("acrylic") == "Synthetic"
        assert extract_fiber("tuxedo") == "Synthetic"
        assert extract_fiber("synbad") == "Synthetic"
        assert extract_fiber("2bed") == "Synthetic"

    def test_badger_patterns(self):
        """Test badger fiber patterns."""
        assert extract_fiber("badger") == "Badger"
        assert extract_fiber("silvertip") == "Badger"
        assert extract_fiber("2-band") == "Badger"
        assert extract_fiber("three band") == "Badger"
        assert extract_fiber("hmw") == "Badger"

    def test_boar_patterns(self):
        """Test boar fiber patterns."""
        assert extract_fiber("boar") == "Boar"
        assert extract_fiber("shoat") == "Boar"

    def test_horse_patterns(self):
        """Test horse fiber patterns."""
        assert extract_fiber("horse") == "Horse"
        assert extract_fiber("horsehair") == "Horse"

    def test_priority_order(self):
        """Test that more specific patterns take priority."""
        # Mixed should take priority over individual types
        assert extract_fiber("mixed badger boar") == "Mixed Badger/Boar"
        assert extract_fiber("badger boar hybrid") == "Mixed Badger/Boar"

    def test_no_match(self):
        """Test cases with no match."""
        assert extract_fiber("") is None
        assert extract_fiber(None) is None
        assert extract_fiber("cotton") is None
