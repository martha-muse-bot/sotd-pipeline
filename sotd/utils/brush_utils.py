"""Brush-related regex patterns and utilities used across the SOTD Pipeline.

This module provides centralized brush pattern matching and extraction logic
to eliminate duplication across brush enrichers and matching strategies.
"""

import re
from typing import Optional

# Knot size patterns used in brush enrichers and strategies
KNOT_SIZE_PATTERNS = {
    # Standalone number with 'mm' (highest priority)
    "mm_standalone": r"\b(\d+(?:\.\d+)?)\s*mm?\b",
    # Patterns like '27x50' or '27.5x50' (take first number)
    "dimensions": r"(\d+(?:\.\d+)?)\s*[x×]\s*\d+(?:\.\d+)?",
    # Conservative range for reasonable knot sizes (20-35mm)
    "conservative_range": r"\b(2[0-9](?:\.\d+)?|3[0-5](?:\.\d+)?)\b",
}

# Fiber patterns used in brush enrichers and strategies
FIBER_PATTERNS = {
    "Mixed Badger/Boar": r"(mix|mixed|mi[sx]tura?|badg.*boar|boar.*badg|fusion)",
    "Synthetic": (
        r"(acrylic|timber|tux|mew|silk|synt|synbad|2bed|captain|cashmere|"
        r"faux.*horse|black.*(magic|wolf)|g4|boss|st-?(1|2)|trafalgar\s*t[23]|"
        r"\bt[23]\b|kong|hi\s*brush|ak47|g5[abc]|stf|quartermoon|fibre|"
        r"\bmig\b|synthetic badger|motherlode)"
    ),
    "Badger": (
        r"(hmw|high.*mo|(2|3|two|three)[\s-]*band|shd|badger|silvertip|super|"
        r"gelo|gelous|gelousy|finest|best|ultralux|fanchurian|\blod\b)"
    ),
    "Boar": r"\b(boar|shoat)\b",
    "Horse": r"\bhorse(hair)?\b",
}


def extract_knot_size(text: Optional[str]) -> Optional[float]:
    """Extract knot size in mm from text using standardized patterns.

    Args:
        text: The text to search for knot size patterns

    Returns:
        The extracted knot size as a float, or None if not found
    """
    if not text:
        return None

    # Look for standalone number with 'mm' (highest priority)
    match = re.search(KNOT_SIZE_PATTERNS["mm_standalone"], text, re.IGNORECASE)
    if match:
        return float(match.group(1))

    # Look for patterns like '27x50' or '27.5x50' (take first number)
    match = re.search(KNOT_SIZE_PATTERNS["dimensions"], text)
    if match:
        return float(match.group(1))

    # Fallback: any number in the text (but be more conservative)
    # Only match numbers that could reasonably be knot sizes (20-35mm range)
    match = re.search(KNOT_SIZE_PATTERNS["conservative_range"], text)
    if match:
        return float(match.group(1))

    return None


def extract_fiber(text: Optional[str]) -> Optional[str]:
    """Extract fiber type from text using standardized patterns.

    Args:
        text: The text to search for fiber patterns

    Returns:
        The extracted fiber type as a string, or None if not found
    """
    if not text:
        return None

    # Order matters - check more specific patterns first
    for fiber, pattern in FIBER_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return fiber

    return None
