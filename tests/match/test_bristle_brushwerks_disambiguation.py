"""Regression: 'bristle' fiber language must not match Bristle Brushwerks.

Handle/knot catalogs previously used `bristle.*brush`, which matched Omega/Semogue/
Zenith 'boar bristle brush' phrases as Bristle Brushwerks. Brand matches require
Brushwerks/Brushworks/Werks (same idea as brushes.yaml).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from sotd.match.brush.handle_matcher import HandleMatcher
from sotd.match.brush.matcher import BrushMatcher, clear_brush_catalog_cache
from sotd.match.brush.strategies.utils.pattern_cache import clear_pattern_cache

HANDLES_PATH = Path("data/handles.yaml")

# True Bristle Brushwerks handle cues
BBW_TRUE_POSITIVES = [
    "Bristle Brushwerks 28mm SHD",
    "bristle brushworks b9b",
    "Bristle Brush Werks Maggard 26mm 2 Band Bulb Badger",
    "bristlebrushwerks bay laruel burl gelousy",
    "Bristle Brushwerks Amber Hucklaration B3",
]

# Fiber / non-brand strings that must never resolve as BBW handle
BBW_FALSE_POSITIVES = [
    "Annie boar bristle brush",
    "boar bristle brush, soaked for 15 minutes in warm/hot water",
    "Boar bristle brush, soaked in warm water",
    "Omega Pure Boar Bristle 10049 Shaving Brush",
    "Semogue 1460 Natural Boar Bristle Shaving Brush",
    "Semogue 2000 Beech Wood Handle Pure Boar Bristle Shaving Brush",
    "Semogue Boar Bristle Brush (28 mm knot)",
    "Some Omega boar-bristle brush and an unidentified synthetic, PIF'd by u/scarpux",
    (
        "100% Silvertip Badger Bristle Shaving Brush-Chrome Handle with "
        "3-Band-Silvertip Badger Hair Bristles (thanks to u/GroundbreakingRole )"
    ),
    "Zenith 508A XL Bristle (B35) (2022 r/ws brush)",
    "Zenith 508A XL/Bristle (B35) (2022 r/ws brush)",
    "unknown - stiff bristle brush",
]


def _bbw_brands_from_brush_match(matched: dict | None) -> set[str]:
    if not matched:
        return set()
    brands: set[str] = set()
    brand = matched.get("brand")
    if brand:
        brands.add(brand)
    for key in ("handle", "knot"):
        sub = matched.get(key)
        if isinstance(sub, dict) and sub.get("brand"):
            brands.add(sub["brand"])
    return {b for b in brands if b and "bristle brushwerks" in b.lower()}


@pytest.fixture
def handle_matcher() -> HandleMatcher:
    clear_pattern_cache()
    return HandleMatcher(handles_path=HANDLES_PATH)


@pytest.fixture(scope="module")
def brush_matcher() -> BrushMatcher:
    clear_pattern_cache()
    clear_brush_catalog_cache()
    return BrushMatcher()


@pytest.mark.parametrize("text", BBW_TRUE_POSITIVES)
def test_handle_matcher_matches_true_bristle_brushwerks(
    handle_matcher: HandleMatcher, text: str
) -> None:
    result = handle_matcher.match(text)
    assert result is not None, f"Expected BBW handle match for: {text}"
    assert result.matched is not None
    assert result.matched.get("handle_maker") == "Bristle Brushwerks"


@pytest.mark.parametrize("text", BBW_FALSE_POSITIVES)
def test_handle_matcher_rejects_fiber_bristle_as_bbw(
    handle_matcher: HandleMatcher, text: str
) -> None:
    result = handle_matcher.match(text)
    if result is None or result.matched is None:
        return
    assert (
        result.matched.get("handle_maker") != "Bristle Brushwerks"
    ), f"Fiber language matched as Bristle Brushwerks handle: {text}"


def test_handle_matcher_matches_brothers_bristle(handle_matcher: HandleMatcher) -> None:
    result = handle_matcher.match("Brothers Bristle Aluminum / AP Shave Co. Tuxedo 24mm")
    assert result is not None
    assert result.matched is not None
    assert result.matched.get("handle_maker") == "Brothers Bristle"


def test_brush_matcher_bruskwerks_typo_resolves_bbw_handle(
    brush_matcher: BrushMatcher,
) -> None:
    """Typo 'Bruskwerks' should still yield BBW handle + Declaration B9B knot."""
    result = brush_matcher.match("Bristle Bruskwerks B9B")
    assert result is not None and result.matched is not None
    matched = result.matched
    handle_raw = matched.get("handle")
    knot_raw = matched.get("knot")
    assert isinstance(handle_raw, dict)
    assert isinstance(knot_raw, dict)
    assert handle_raw.get("brand") == "Bristle Brushwerks"
    assert knot_raw.get("brand") == "Declaration Grooming"
    assert knot_raw.get("model") == "B9B"


@pytest.mark.parametrize("text", BBW_TRUE_POSITIVES)
def test_brush_matcher_true_bbw_still_resolves(brush_matcher: BrushMatcher, text: str) -> None:
    result = brush_matcher.match(text)
    assert result is not None and result.matched is not None, f"No match for: {text}"
    assert _bbw_brands_from_brush_match(result.matched), f"Expected BBW somewhere in: {text}"


@pytest.mark.parametrize("text", BBW_FALSE_POSITIVES)
def test_brush_matcher_rejects_fiber_bristle_as_bbw(brush_matcher: BrushMatcher, text: str) -> None:
    result = brush_matcher.match(text)
    matched = result.matched if result else None
    assert not _bbw_brands_from_brush_match(
        matched
    ), f"Fiber language matched as Bristle Brushwerks: {text} -> {matched}"
