import pytest

from sotd.match.brush.strategies.specialized.zenith_strategy import ZenithBrushMatchingStrategy


@pytest.fixture
def strategy():
    return ZenithBrushMatchingStrategy()


def test_zenith_b_series_match(strategy):
    """Test Zenith B-series model"""
    result = strategy.match("Zenith B26")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b26"
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert "knot_size_mm" not in result.matched, "Should not have root-level knot_size_mm"
    assert result.matched["knot"]["fiber"] == "Boar"
    assert result.matched["knot"]["knot_size_mm"] is None
    assert result.matched["handle"]["brand"] == "Zenith"
    assert result.matched["handle"]["model"] is None
    assert result.pattern == r"zenith\s+(b\d{1,2})\b"  # Actual pattern used by strategy


def test_zenith_with_synthetic_fiber(strategy):
    """Test Zenith with synthetic fiber mentioned (but not detected by strategy)."""
    result = strategy.match("Zenith B26 Synthetic")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b26"
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert "knot_size_mm" not in result.matched, "Should not have root-level knot_size_mm"
    assert result.matched["knot"]["fiber"] == "Boar"  # Strategy always returns default fiber
    assert result.matched["knot"]["knot_size_mm"] is None


def test_zenith_with_badger_fiber(strategy):
    """Test Zenith with badger fiber mentioned (but not detected by strategy)."""
    result = strategy.match("Zenith B26 Badger")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b26"
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert "knot_size_mm" not in result.matched, "Should not have root-level knot_size_mm"
    assert result.matched["knot"]["fiber"] == "Boar"  # Strategy always returns default fiber
    assert result.matched["knot"]["knot_size_mm"] is None


def test_zenith_case_insensitive(strategy):
    """Test case insensitive matching"""
    result = strategy.match("zenith b26")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b26"  # Strategy returns lowercase model names
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert result.matched["knot"]["fiber"] == "Boar"


def test_zenith_various_letters(strategy):
    """Test various letter prefixes (excluding X which is not in range a-wyz)"""
    test_cases = [
        ("Zenith B26", "b26"),
        ("Zenith B15", "b15"),
        ("Zenith B2", "b2"),
        ("Zenith B3", "b3"),
    ]

    for input_str, expected_model in test_cases:
        result = strategy.match(input_str)
        assert result.matched is not None
        assert result.matched["brand"] == "Zenith"
        assert result.matched["model"] == expected_model


def test_zenith_single_digit_model(strategy):
    """Test single digit model numbers"""
    result = strategy.match("Zenith B3")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b3"
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert result.matched["knot"]["fiber"] == "Boar"


def test_zenith_no_match_three_digit_model(strategy):
    """Test that 3-digit model numbers are rejected (Zenith only uses 1-2 digits)."""
    result = strategy.match("Zenith B100")
    assert result.matched is None

    result = strategy.match("Zenith B123")
    assert result.matched is None


def test_zenith_with_extra_text(strategy):
    """Test with additional text"""
    result = strategy.match("My favorite Zenith B26 brush")

    assert result.matched is not None
    assert result.matched["brand"] == "Zenith"
    assert result.matched["model"] == "b26"
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert result.matched["knot"]["fiber"] == "Boar"


def test_zenith_no_match_x_series(strategy):
    """Test that X-series models don't match (X not in range a-wyz)"""
    result = strategy.match("Zenith X26")

    assert result.matched is None


def test_zenith_no_match_no_model(strategy):
    """Test Zenith without model"""
    result = strategy.match("Zenith brush")

    assert result.matched is None


def test_zenith_no_match_different_brand(strategy):
    """Test with different brand"""
    result = strategy.match("Simpson B26")

    assert result.matched is None


def test_zenith_no_match_invalid_pattern(strategy):
    """Test patterns that don't match the regex"""
    test_cases = [
        "Zenith 26",  # No letter prefix
        "Zenith B",  # No number suffix
        "Zenith X26",  # X not in range a-wyz
    ]

    for test_case in test_cases:
        result = strategy.match(test_case)
        assert result.matched is None


def test_invalid_input_types(strategy):
    """Test with invalid input types"""
    result = strategy.match(None)
    assert result.matched is None

    result = strategy.match(123)
    assert result.matched is None


def test_zenith_fiber_detection_priority(strategy):
    """Test that default fiber is always Boar (strategy doesn't detect fiber from input)."""
    result = strategy.match("Zenith B26")  # No fiber mentioned
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    assert result.matched["knot"]["fiber"] == "Boar"  # Default

    result = strategy.match("Zenith B26 horse")  # Horse fiber mentioned but not detected
    # Check nested structure (no redundant root fields)
    assert "fiber" not in result.matched, "Should not have root-level fiber"
    # Still default since strategy doesn't parse fiber
    assert result.matched["knot"]["fiber"] == "Boar"


def test_zenith_lowercase_model_conversion(strategy):
    """Test that model is returned as lowercase (as captured from input)."""
    result = strategy.match("zenith b26")

    assert result.matched is not None
    assert result.matched["model"] == "b26"  # Strategy returns lowercase model names
