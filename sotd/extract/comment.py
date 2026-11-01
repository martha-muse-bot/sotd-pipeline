import json
import logging
import re
from collections import OrderedDict
from pathlib import Path
from typing import Optional

from sotd.extract.fields import extract_field_with_pattern, get_patterns
from sotd.extract.override_manager import OverrideManager
from sotd.utils.aliases import FIELD_ALIASES
from sotd.utils.extract_normalization import normalize_for_matching
from sotd.utils.text import preprocess_body

logger = logging.getLogger(__name__)

# Labels that mark the start of a new SOTD field line, including non-extracted ones
# (e.g. Post Shave). Used to avoid joining wrapped values into the next field.
_FIELD_MARKER_ALIASES = sorted(
    {
        *(alias for aliases in FIELD_ALIASES.values() for alias in aliases),
        "pre-shave",
        "presave",
        "prep",
        "post shave",
        "post-shave",
        "aftershave",
        "fragrance",
        "scent",
        "edp",
    },
    key=len,
    reverse=True,
)
_FIELD_MARKER_PATTERN: Optional[re.Pattern[str]] = None


def _get_field_marker_pattern() -> re.Pattern[str]:
    """Compile (once) a pattern that detects a new field marker on a line."""
    global _FIELD_MARKER_PATTERN
    if _FIELD_MARKER_PATTERN is not None:
        return _FIELD_MARKER_PATTERN

    alias_alt = "|".join(re.escape(alias).replace(r"\ ", r"\s+") for alias in _FIELD_MARKER_ALIASES)
    _FIELD_MARKER_PATTERN = re.compile(
        rf"^\s*(?:[-*•]\s+)?(?:\*\*)?(?:{alias_alt})(?:\*\*)?\s*[-:=]",
        flags=re.IGNORECASE,
    )
    return _FIELD_MARKER_PATTERN


def _is_field_marker_line(line: str) -> bool:
    """Return True if the line starts a new SOTD field (extracted or not)."""
    return bool(_get_field_marker_pattern().match(line))


def _maybe_join_wrapped_continuation(value: str, lines: list[str], line_index: int) -> str:
    """
    Join a wrapped field continuation when the value ends with a trailing dash.

    Rule (validated against 2024-2026 comment data):
    - extracted value ends with '-'
    - next line exists and is non-blank
    - next line is not a field marker

    Otherwise return the original value unchanged.
    """
    if not re.search(r"-\s*$", value):
        return value
    if line_index + 1 >= len(lines):
        return value

    next_line = lines[line_index + 1].strip()
    if not next_line or _is_field_marker_line(next_line):
        return value

    return f"{value} {next_line}"


def parse_comment(
    comment: dict,
    override_manager: Optional[OverrideManager] = None,
    processing_month: Optional[str] = None,
) -> Optional[dict]:
    if "body" in comment:
        comment["body"] = preprocess_body(comment["body"])
    else:
        comment["body"] = None
    lines = comment["body"].splitlines() if comment["body"] else []

    lines = [re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line) for line in lines]

    result = {}

    # Process fields with line-by-line extraction and priority buckets
    # Algorithm:
    # 1. First pass: For each line (in order), try all high-priority patterns (0-14b with explicit markers)
    #    Return on first match found
    # 2. Second pass: If no match found, for each line (in order), try all low-priority patterns (15, ambiguous)
    #    Return on first match found
    # This ensures earlier lines (product listings) are preferred over later lines (descriptions)
    for field in ("razor", "blade", "brush", "soap"):
        if field in result:
            continue  # Already found this field

        # Get all aliases for this field
        aliases = FIELD_ALIASES.get(field, [field])

        # Collect all patterns grouped by priority bucket
        # High priority: patterns 0-14b (indices 0-15) with explicit markers (:,-,=)
        # Low priority: pattern 15 (index 16) with ambiguous format (no explicit markers)
        high_priority_patterns = []  # Patterns 0-14b (explicit markers)
        low_priority_patterns = []  # Pattern 15 (ambiguous)

        for alias in aliases:
            alias_patterns = get_patterns(alias)
            for pattern_num, pattern in enumerate(alias_patterns):
                # Pattern 15 (ambiguous) is at index 16, all others are high priority
                if pattern_num < len(alias_patterns) - 1:  # All except last pattern
                    high_priority_patterns.append((alias, pattern))
                else:  # Last pattern is low priority (pattern 15)
                    low_priority_patterns.append((alias, pattern))

        # First pass: Try high-priority patterns line by line
        for line_index, line in enumerate(lines):
            for alias, pattern in high_priority_patterns:
                value = extract_field_with_pattern(line, field, pattern)
                if value:
                    value = _maybe_join_wrapped_continuation(value, lines, line_index)
                    normalized_value = normalize_for_matching(value, field=field)
                    result[field] = {"original": value, "normalized": normalized_value}
                    break  # Found match, move to next field
            if field in result:
                break  # Found match for this field

        # Second pass: Try low-priority patterns line by line (only if no match found)
        if field not in result:
            for line_index, line in enumerate(lines):
                for alias, pattern in low_priority_patterns:
                    value = extract_field_with_pattern(line, field, pattern)
                    if value:
                        value = _maybe_join_wrapped_continuation(value, lines, line_index)
                        normalized_value = normalize_for_matching(value, field=field)
                        result[field] = {"original": value, "normalized": normalized_value}
                        break  # Found match, move to next field
                if field in result:
                    break  # Found match for this field

    # Apply overrides if override manager is provided
    # Use processing_month if provided, otherwise fall back to extracting from created_utc
    if override_manager and comment.get("id"):
        if processing_month:
            month_str = processing_month
        else:
            # Fallback: extract month from created_utc timestamp
            month = comment.get("created_utc", "").split("-")[:2]
            if len(month) != 2:
                month_str = None
            else:
                month_str = f"{month[0]}-{month[1]:0>2}"

        if month_str:
            comment_id = comment["id"]

            for field in ("razor", "blade", "brush", "soap"):
                override_value = override_manager.get_override(month_str, comment_id, field)
                if override_value:
                    field_exists = field in result
                    result[field] = override_manager.apply_override(
                        result.get(field), override_value, field_exists, field=field
                    )

    ordered_comment = OrderedDict()
    for key in ("author", "body", "created_utc", "id", "thread_id", "thread_title", "url"):
        if key in comment:
            ordered_comment[key] = comment[key]

    for field in ("razor", "blade", "brush", "soap"):
        value = result.get(field)
        if value:
            ordered_comment[field] = value

    return ordered_comment if result else None


# Added function to run extraction for a month
# Skips extraction and logging a warning if input file is missing


def run_extraction_for_month(
    month: str, base_path: str = "data", override_manager: Optional[OverrideManager] = None
) -> Optional[dict]:
    input_path = Path(base_path) / "comments" / f"{month}.json"
    if not input_path.exists():
        logger.warning("Skipping extraction for missing input file: %s", input_path)
        return None

    with open(input_path, encoding="utf-8") as f:
        raw = json.load(f)
        comments = raw.get("data", [])

    extracted = []
    skipped = []

    for comment in comments:
        parsed = parse_comment(comment, override_manager, processing_month=month)
        if parsed:
            extracted.append(parsed)
        else:
            skipped.append(comment)

    field_coverage = {"razor": 0, "blade": 0, "brush": 0, "soap": 0}
    for entry in extracted:
        for field in field_coverage:
            if field in entry:
                field_coverage[field] += 1

    return {
        "meta": {
            "month": month,
            "comment_count": len(comments),
            "shave_count": len(extracted),
            "skipped_count": len(skipped),
            "field_coverage": field_coverage,
        },
        "data": extracted,
        "skipped": skipped,
    }
