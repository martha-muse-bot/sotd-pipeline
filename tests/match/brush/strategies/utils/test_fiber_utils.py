"""Tests for brush fiber matching utilities."""

import pytest

from sotd.match.brush.strategies.utils.fiber_utils import match_fiber


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Handle "Hybrid" (wood/resin) must not force Mixed Badger/Boar
        ("Virginia Cheng - Silvertip Badger Dogwood Hybrid 26mm", "Badger"),
        ("Dogwood Handcrafts Hybrid / Maggard Boar", "Boar"),
        ("Doglaration 28mm B9A badger in hybrid handle", "Badger"),
        (
            "Chisel & Hound - Spice Blow - Maple Burl & Resin Hybrid handle "
            "w/ 26mm Fanchurian Badger knot",
            "Badger",
        ),
        ("Dogwood Hybrid", None),
        # True fiber mixes still match (hybrid wording optional / redundant)
        ("Zenith Badger / Boar Hybrid", "Mixed Badger/Boar"),
        ("Maggard 26mm badger/boar hybrid", "Mixed Badger/Boar"),
        ("badger boar hybrid", "Mixed Badger/Boar"),
        ("Omega 11047 Mixed Badger/Boar", "Mixed Badger/Boar"),
        ("Semogue Mistura", "Mixed Badger/Boar"),
        ("Dogwood Handcrafts custom with Badger/Boar hybrid knot", "Mixed Badger/Boar"),
    ],
)
def test_match_fiber_hybrid_handle_vs_true_mix(text: str, expected: str | None) -> None:
    assert match_fiber(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # European / catalog "bristle" = boar when qualified
        ("Omega Pure Bristle 10065", "Boar"),
        ("Omega 10049 - 100% Boar Bristle - RED", "Boar"),
        ("Zenith - Unbleached Bristle 509BC XSE", "Boar"),
        ("Zenith - Bleached Bristle - 26mm x 60mm Boar Knot", "Boar"),
        ("Century Pure Bristle 18mm", "Boar"),
        ("Semogue 1460 Natural Boar Bristle Shaving Brush", "Boar"),
        # Bare stiff bristle still cues Boar (stiff/vintage/finest added as
        # boar-bristle qualifiers in 814c109be for analyzer input parsing)
        ("unknown - stiff bristle brush", "Boar"),
    ],
)
def test_match_fiber_bristle_as_boar_when_qualified(text: str, expected: str | None) -> None:
    assert match_fiber(text) == expected


def test_match_fiber_bristle_brushwerks_brand_is_not_boar() -> None:
    """Brand name 'Bristle Brushwerks' must not map to Boar via bare 'bristle'."""
    assert match_fiber("Bristle Brushwerks Amber Hucklaration B3") != "Boar"
    # SHD correctly yields Badger; still must not be Boar from 'bristle'
    assert match_fiber("Bristle Brushwerks 28mm SHD") == "Badger"
