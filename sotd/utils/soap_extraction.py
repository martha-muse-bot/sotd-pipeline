#!/usr/bin/env python3
"""Soap-specific extraction utilities for the SOTD pipeline."""

import re
from typing import Optional, Tuple

# v1: "mashup", "mash up", "mash-up" only (word-boundary, case-insensitive)
_MASHUP_PATTERN = re.compile(r"\bmash[- ]?up\b", re.IGNORECASE)


def detect_soap_mashup(text: str) -> bool:
    """Detect mashup indicators in soap field text (original or normalized).

    v1 patterns: "mashup", "mash up", "mash-up" only. Used to count unbranded
    mashup shaves (e.g. "soap mashup", "Sample mashup") when matched is null.

    Args:
        text: Soap field text (original or normalized)

    Returns:
        True if text contains a mashup indicator, False otherwise.
    """
    if not text or not isinstance(text, str):
        return False
    return _MASHUP_PATTERN.search(text.strip()) is not None


def extract_soap_sample_via_normalization(
    original_text: str, normalized_text: str
) -> Tuple[Optional[str], Optional[int], Optional[int], Optional[str]]:
    """
    Extract soap sample information by removing normalized text from original text.

    This approach leverages the already-done normalization work to find sample indicators
    that remain after the normalized product text is stripped out.

    Args:
        original_text: The original soap text from user comment
        normalized_text: The normalized soap text (with sample indicators stripped)

    Returns:
        Tuple of (sample_type, sample_number, total_samples, remainder_text) where:
        - sample_type: The type of sample ("sample", "tester", etc.) or None
        - sample_number: The sample number if specified, or None
        - total_samples: The total number of samples if specified, or None
        - remainder_text: The text that remains after stripping normalized from original
    """
    if not original_text or not normalized_text:
        return None, None, None, None

    # Strip whitespace from both texts for comparison
    original_stripped = original_text.strip()
    normalized_stripped = normalized_text.strip()

    # Find the normalized text within the original text
    # Use case-insensitive search to handle minor case differences
    original_lower = original_stripped.lower()
    normalized_lower = normalized_stripped.lower()

    # Find the position of the normalized text in the original
    pos = original_lower.find(normalized_lower)
    if pos == -1:
        # Normalized text not found in original - this shouldn't happen in normal operation
        return None, None, None, None

    # Extract the remainder text (what comes before and after the normalized text)
    before_normalized = original_stripped[:pos]
    after_normalized = original_stripped[pos + len(normalized_stripped) :]

    # Combine the remainder parts
    remainder = (before_normalized + after_normalized).strip()

    # Extract sample information from the remainder first
    sample_type, sample_number, total_samples = _extract_sample_patterns(remainder)

    # When sample indicators are kept inside normalized product text (common for
    # mashups of samples), original == normalized and remainder is empty — fall
    # back to scanning the full original text.
    if sample_type is None and original_stripped:
        sample_type, sample_number, total_samples = _extract_sample_patterns(original_stripped)

    return sample_type, sample_number, total_samples, remainder


def _extract_sample_patterns(remainder: str) -> Tuple[Optional[str], Optional[int], Optional[int]]:
    """
    Extract sample patterns from remainder text.

    Args:
        remainder: Text remaining after stripping normalized product text

    Returns:
        Tuple of (sample_type, sample_number, total_samples)
    """
    if not remainder:
        return None, None, None

    # Convert to lowercase for case-insensitive matching
    remainder_lower = remainder.lower()

    def _normalize_sample_token(token: str) -> str:
        if token in ("samp", "smush", "samples", "sampler"):
            return "sample"
        return token

    # Pattern 1: (sample), (tester), (smush), (sampler)
    basic_sample_match = re.search(r"\((\w+)\)", remainder_lower)
    if basic_sample_match:
        sample_type = basic_sample_match.group(1)
        if sample_type in ["sample", "samp", "tester", "smush", "sampler"]:
            return _normalize_sample_token(sample_type), None, None

    # Pattern 2: (sample #23), (sample #5), (smush #23)
    numbered_sample_match = re.search(r"\((?:sample|smush)\s+#(\d+)\)", remainder_lower)
    if numbered_sample_match:
        try:
            sample_number = int(numbered_sample_match.group(1))
            return "sample", sample_number, None
        except ValueError:
            pass

    # Pattern 3: (sample 5 of 10), (sample 3 of 15), (smush 5 of 10)
    range_sample_match = re.search(r"\((?:sample|smush)\s+(\d+)\s+of\s+(\d+)\)", remainder_lower)
    if range_sample_match:
        try:
            sample_number = int(range_sample_match.group(1))
            total_samples = int(range_sample_match.group(2))
            return "sample", sample_number, total_samples
        except ValueError:
            pass

    # Pattern 4: (sample 5/10), (sample 3/15), (smush 5/10)
    fraction_sample_match = re.search(r"\((?:sample|smush)\s+(\d+)/(\d+)\)", remainder_lower)
    if fraction_sample_match:
        try:
            sample_number = int(fraction_sample_match.group(1))
            total_samples = int(fraction_sample_match.group(2))
            return "sample", sample_number, total_samples
        except ValueError:
            pass

    # Pattern 5: trailing sample/tester/smush/sampler with optional punctuation
    # (e.g. "Brand - Scent - sample", "Indigo sample.", "Island Man Sampler")
    trailing_sample_match = re.search(
        r"\b(sample|samp|tester|smush|sampler)\b\s*[.!?,:;]*\s*$",
        remainder_lower,
    )
    if trailing_sample_match:
        return _normalize_sample_token(trailing_sample_match.group(1)), None, None

    # Pattern 6: (sample) with any whitespace variations
    loose_sample_match = re.search(
        r"\(\s*(sample|samp|tester|smush|sampler)\s*\)",
        remainder_lower,
    )
    if loose_sample_match:
        return _normalize_sample_token(loose_sample_match.group(1)), None, None

    # Pattern 7: (sample -- thanks!!) or similar gratitude patterns, (smush -- thanks!!)
    gratitude_sample_match = re.search(r"\((?:sample|smush)[^)]*thanks[^)]*\)", remainder_lower)
    if gratitude_sample_match:
        return "sample", None, None

    # Pattern 8: (sample) or (smush) with trailing punctuation
    trailing_punct_match = re.search(r"\((?:sample|smush)\)[^\w]", remainder_lower)
    if trailing_punct_match:
        return "sample", None, None

    # Pattern 9: (sample) or (smush) with emojis or special characters
    emoji_sample_match = re.search(r"\((?:sample|smush)[^)]*[^\w\s][^)]*\)", remainder_lower)
    if emoji_sample_match:
        return "sample", None, None

    # Pattern 10: parenthetical describing sample usage (e.g. "1oz samples",
    # "combined ... samples"). Prefer plural / sized forms so scent names like
    # "Sample Mashup" are not treated as sample usage.
    descriptive_paren_match = re.search(
        r"\([^)]*\b(?:\d+(?:\.\d+)?\s*oz\s+)?(?:samples?|samp|tester|smush|sampler)\b[^)]*\)",
        remainder_lower,
    )
    if descriptive_paren_match:
        token = re.search(
            r"\b(samples?|samp|tester|smush|sampler)\b",
            descriptive_paren_match.group(0),
        )
        if token:
            return _normalize_sample_token(token.group(1)), None, None

    # Pattern 11: plural "samples" or sized "N oz sample(s)" outside bare markers
    # (usage language; avoids matching singular "Sample" in product names).
    if re.search(r"\b(?:\d+(?:\.\d+)?\s*oz\s+samples?|samples)\b", remainder_lower):
        return "sample", None, None

    # Pattern 12: bare mid-string smush/samp (usage language; rarely catalog scent tokens).
    # Covers "a smush from u/...", "Mystery Smush Croap", "Nonsensical Smush of...".
    if re.search(r"\b(smush|samp)\b", remainder_lower):
        return "sample", None, None

    # Pattern 13: clear mid-string sample usage phrases (avoid scent names like "Sample Mashup").
    if re.search(r"\b(?:a\s+sample|samples?\s+from|sample\s+of)\b", remainder_lower):
        return "sample", None, None

    # Pattern 14: "Product Sample - Location" (SOTD location suffix after sample marker).
    # Does not match "Sample Mash Up - Location" (no dash immediately after sample).
    if re.search(r"\b(sample|samp|tester|smush|sampler)\b\s*[-–—]", remainder_lower):
        return "sample", None, None

    # Pattern 15: "last of the sample"
    if re.search(r"\blast of the samples?\b", remainder_lower):
        return "sample", None, None

    return None, None, None


def normalize_soap_suffixes(text: str) -> str:
    """
    Normalize soap text by removing common suffixes and indicators using iterative approach.

    This function removes various suffixes and indicators that are commonly
    found in soap descriptions but don't affect the core product identification.
    Uses a loop-based approach to ensure all patterns are applied until no more
    changes occur.

    Args:
        text: The soap text to normalize

    Returns:
        The normalized soap text with original case preserved
    """
    if not text or not text.strip():
        return text

    # Work with original case to preserve it
    current_text = text

    # Define format indicators that support shave/shaving prefixes
    # All formats except soap (soap is special - only stripped with dash)
    formats_with_shave_support = ["cream", "gel", "foam", "puck", "stick", "croap", "soap"]

    # Define all normalization patterns in order of priority
    # Higher priority patterns are applied first
    # Use case-insensitive matching with re.IGNORECASE flag
    normalization_patterns = [
        # Sample indicators in parentheses (highest priority)
        (r"\s*\(sample[^)]*\)\s*", re.IGNORECASE),  # (sample), (sample -- thanks!!), etc.
        (r"\s*\(tester[^)]*\)\s*", re.IGNORECASE),  # (tester), etc.
        (r"\s*\(sampler[^)]*\)\s*", re.IGNORECASE),  # (sampler), etc.
        (r"\s*\(samp[^)]*\)\s*", re.IGNORECASE),  # (samp), etc.
        (r"\s*\(smush[^)]*\)\s*", re.IGNORECASE),  # (smush), etc.
        # Size indicators in parentheses
        (r"\s*\(\d+oz\)\s*", re.IGNORECASE),  # (2oz), (4oz), etc.
        (r"\s*\(big\s+ass\s+og\s+\d+oz[^)]*\)\s*", re.IGNORECASE),  # (big ass og 4oz), etc.
        # Establishment date indicators
        (r"\s*\(est\.\s*\d+[^)]*\)\s*", re.IGNORECASE),  # (est. 1899), etc.
        # Base/formula indicators in parentheses
        (r"\s*\(premium\s+base\)\s*", re.IGNORECASE),
        (r"\s*\(luxury\s+base\)\s*", re.IGNORECASE),
        (r"\s*\(omnibus\s+base\)\s*", re.IGNORECASE),
        (r"\s*\(milksteak\)\s*", re.IGNORECASE),
        (r"\s*\(tusk\)\s*", re.IGNORECASE),
        (r"\s*\(professional\)\s*", re.IGNORECASE),
        (r"\s*\(tallow\s+base\)\s*", re.IGNORECASE),
        (r"\s*\(tallow\s+formulation\)\s*", re.IGNORECASE),
        (r"\s*\(tallow\)\s*", re.IGNORECASE),  # (tallow) standalone
        (r"\s*\(vegan\)\s*", re.IGNORECASE),
        # Trailing sample indicators (without parentheses; optional trailing punct)
        (r"\s*-\s*sample\s*[.!?]*\s*$", re.IGNORECASE),  # "- sample" / "- sample."
        (r"\s*-\s*tester\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s*-\s*sampler\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s*-\s*samp\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s*-\s*smush\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s+sample\s*[.!?]*\s*$", re.IGNORECASE),  # "sample" / "sample."
        (r"\s+tester\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s+sampler\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s+samp\s*[.!?]*\s*$", re.IGNORECASE),
        (r"\s+smush\s*[.!?]*\s*$", re.IGNORECASE),
        # "Product Sample - Location" → strip sample + location tail for matching
        (r"\s+sample\s*[-–—]\s*[A-Za-z].*$", re.IGNORECASE),
        (r"\s+sampler\s*[-–—]\s*[A-Za-z].*$", re.IGNORECASE),
        (r"\s+tester\s*[-–—]\s*[A-Za-z].*$", re.IGNORECASE),
        (r"\s+smush\s*[-–—]\s*[A-Za-z].*$", re.IGNORECASE),
        # "last of the sample" usage tails
        (r"\s*[-–—:]?\s*last of the samples?\b.*$", re.IGNORECASE),
        # Shave/Shaving prefix patterns for all formats (MUST come before standalone formats)
        # Generate patterns for " - shaving [format]" and " - shave [format]" for each format
        # Longer patterns (shaving) come before shorter (shave) to avoid partial matches
        *[
            (
                rf"\s*-\s*shaving\s+{fmt}\s*[.!?]*\s*$",
                re.IGNORECASE,
            )  # f"- shaving {fmt}" at end
            for fmt in formats_with_shave_support
        ],
        *[
            (
                rf"\s+shaving\s+{fmt}\s*[.!?]*\s*$",
                re.IGNORECASE,
            )  # f"shaving {fmt}" at end (without dash)
            for fmt in formats_with_shave_support
        ],
        *[
            (
                rf"\s*-\s*shave\s+{fmt}\s*[.!?]*\s*$",
                re.IGNORECASE,
            )  # f"- shave {fmt}" at end
            for fmt in formats_with_shave_support
        ],
        *[
            (
                rf"\s+shave\s+{fmt}\s*[.!?]*\s*$",
                re.IGNORECASE,
            )  # f"shave {fmt}" at end (without dash)
            for fmt in formats_with_shave_support
        ],
        # Container type suffixes (standalone formats, after shave/shaving patterns)
        (
            r"\s*-\s*stick\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- stick" at end (with optional punctuation)
        (
            r"\s+stick\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "stick" at end (without dash, with optional punctuation)
        (r"\s*-\s*tube\s*[.!?]*\s*$", re.IGNORECASE),  # "- tube" at end (with optional punctuation)
        (
            r"\s+tube\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "tube" at end (without dash, with optional punctuation)
        (r"\s*-\s*hard\s*[.!?]*\s*$", re.IGNORECASE),  # "- hard" at end (with optional punctuation)
        (
            r"\s+hard\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "hard" at end (without dash, with optional punctuation)
        # Product type suffixes
        (
            r"\s*-\s*crema\s+da\s+barba\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- crema da barba" at end (with optional punctuation)
        (
            r"\s+crema\s+da\s+barba\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "crema da barba" at end (without dash, with optional punctuation)
        # Base format patterns (standalone formats, after shave/shaving patterns)
        # Soap is special - only stripped with dash
        (r"\s*-\s*soap\s*[.!?]*\s*$", re.IGNORECASE),  # "- soap" at end (with optional punctuation)
        # Other formats: stripped with or without dash
        (
            r"\s*-\s*cream\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- cream" at end (with optional punctuation)
        (
            r"\s+cream\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "cream" at end (without dash, with optional punctuation)
        (
            r"\s*-\s*gel\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- gel" at end (with optional punctuation)
        (
            r"\s+gel\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "gel" at end (without dash, with optional punctuation)
        (
            r"\s*-\s*foam\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- foam" at end (with optional punctuation)
        (
            r"\s+foam\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "foam" at end (without dash, with optional punctuation)
        (r"\s*-\s*puck\s*[.!?]*\s*$", re.IGNORECASE),  # "- puck" at end (with optional punctuation)
        (
            r"\s+puck\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "puck" at end (without dash, with optional punctuation)
        (
            r"\s*-\s*croap\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- croap" at end (with optional punctuation)
        (
            r"\s+croap\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "croap" at end (without dash, with optional punctuation)
        # Removed: standalone "soap" at end - too aggressive, breaks brand
        # names like "Soap Commander"
        # Only strip "soap" when preceded by delimiters (handled by line 244)
        # General product suffixes that can appear anywhere
        (r"\s+crema\s+da\s+barba\s+", re.IGNORECASE),  # "crema da barba" anywhere (with spaces)
        # Standalone base/formula indicators (without parentheses)
        (r"\s*-\s*omnibus\s*$", re.IGNORECASE),  # "- omnibus" at end
        (r"\s+omnibus\s*$", re.IGNORECASE),  # "omnibus" at end (without dash)
        # Additional product type suffixes
        (
            r"\s*-\s*shaving\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "- shaving" at end (with optional punctuation)
        (
            r"\s+shaving\s*[.!?]*\s*$",
            re.IGNORECASE,
        ),  # "shaving" at end (without dash, with optional punctuation)
    ]

    # Apply normalization iteratively until no more changes occur
    previous_text = ""

    while previous_text != current_text:
        previous_text = current_text

        # Apply all patterns in order
        for pattern, flags in normalization_patterns:
            current_text = re.sub(pattern, "", current_text, flags=flags)

        # Clean up extra whitespace and dashes after each iteration
        current_text = re.sub(r"\s+", " ", current_text)  # Multiple spaces to single space
        current_text = re.sub(r"\s*-\s*$", "", current_text)  # Remove trailing dash
        current_text = re.sub(r"^\s*-\s*", "", current_text)  # Remove leading dash
        current_text = current_text.strip()

    return current_text
