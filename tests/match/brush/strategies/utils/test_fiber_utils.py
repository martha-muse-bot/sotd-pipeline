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
