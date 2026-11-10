import re
from typing import Optional

from sotd.utils.aliases import FIELD_ALIASES

# Cache for next field stop pattern (built once, reused)
_next_field_stop_pattern: Optional[str] = None

# Cache for compiled per-alias patterns (built once per alias, reused).
# get_patterns() rebuilds 17 long pattern strings per call — each embedding
# the multi-kilobyte next-field stop lookahead — and re.search() on a fresh
# string re-hashes/re-compiles it every time. At 19 aliases x 17 patterns
# per comment that dominated extract time (profiled: ~7.6 ms/comment,
# almost all of it in re._compile on rebuilt strings).
_compiled_patterns_cache: dict[str, list[re.Pattern[str]]] = {}


def get_compiled_patterns(alias: str) -> list[re.Pattern[str]]:
    """
    Compiled form of get_patterns(alias), built once per alias and reused.

    Returns the same list (same order, same patterns) as get_patterns(),
    compiled with re.IGNORECASE. Safe to share across comments: patterns
    are stateless.
    """
    cached = _compiled_patterns_cache.get(alias)
    if cached is None:
        cached = [re.compile(pattern, flags=re.IGNORECASE) for pattern in get_patterns(alias)]
        _compiled_patterns_cache[alias] = cached
    return cached


def _build_next_field_stop_pattern() -> str:
    """
    Build a regex pattern that matches any next field marker on the same line.

    This pattern is used in lookahead assertions to stop field extraction
    when another field marker is encountered (e.g., when multiple fields
    appear on the same line separated by field markers).

    Returns:
        Regex pattern string for use in positive lookahead
    """
    global _next_field_stop_pattern

    if _next_field_stop_pattern is not None:
        return _next_field_stop_pattern

    # Collect all field aliases
    all_aliases = []
    for field_aliases in FIELD_ALIASES.values():
        all_aliases.extend(field_aliases)

    # Remove duplicates while preserving order
    seen = set()
    unique_aliases = []
    for alias in all_aliases:
        if alias not in seen:
            seen.add(alias)
            unique_aliases.append(alias)

    # Build pattern alternatives for each alias
    # Handle spaces in aliases (e.g., "straight razor", "shaving brush")
    alias_patterns = []
    for alias in unique_aliases:
        # Escape special regex characters in alias
        escaped_alias = re.escape(alias)
        # Replace escaped spaces with \s+ to handle variable spacing
        escaped_alias = escaped_alias.replace(r"\ ", r"\s+")

        # Pattern 1: .* **Field: (most common - the user's case)
        alias_patterns.append(rf"\.\*\s+\*\*\s*\b{escaped_alias}\b\s*[-:=]")
        # Pattern 2: .* **Field**: (colon after **)
        alias_patterns.append(rf"\.\*\s+\*\*\s*\b{escaped_alias}\b\s*\*\*\s*[-:=]")
        # Pattern 3: .* Field: (simple format)
        alias_patterns.append(rf"\.\*\s+\b{escaped_alias}\b\s*[-:=]")
        # Pattern 4: .* Field - (dash format)
        alias_patterns.append(rf"\.\*\s+\b{escaped_alias}\b\s+[-:=]")
        # Pattern 5: * **Field: (with bullet prefix)
        alias_patterns.append(rf"[-*]\s+\*\*\s*\b{escaped_alias}\b\s*[-:=]")
        # Pattern 6: * Field: (with bullet prefix, simple)
        alias_patterns.append(rf"[-*]\s+\b{escaped_alias}\b\s*[-:=]")

    # Combine all patterns with alternation
    combined_pattern = "|".join(alias_patterns)

    # Cache the result
    _next_field_stop_pattern = combined_pattern
    return _next_field_stop_pattern


def extract_field(line: str, field: str) -> Optional[str]:
    return _extract_field_line(line, field)


def extract_field_with_pattern(
    line: str, field: str, pattern: str | re.Pattern[str]
) -> Optional[str]:
    """
    Try a specific pattern on a line for a field.

    Args:
        line: The line to check
        field: The field name (razor, blade, brush, soap)
        pattern: The regex pattern to try, as a string or a compiled
            pattern (compiled patterns from get_compiled_patterns() avoid
            re-compiling the same pattern string on every call)

    Returns:
        Extracted value if pattern matches, None otherwise
    """
    # Check exclusions first
    if field == "soap" and re.search(r"^lather\s+games", line, flags=re.IGNORECASE):
        return None
    if field == "razor" and re.search(r"^razor\s+test", line, flags=re.IGNORECASE):
        return None

    # Use search instead of match to handle fields that appear in the middle of a line
    # (e.g., when multiple fields are on the same line)
    if isinstance(pattern, re.Pattern):
        match = pattern.search(line)
    else:
        match = re.search(pattern, line, flags=re.IGNORECASE)
    if match:
        value = match.group(1).strip()
        # Filter out values that are just field markers (e.g., "**") or empty
        if not value or value in ("**", "*"):
            return None
        return value
    return None


def _extract_field_line(line: str, field: str) -> Optional[str]:
    # Special handling for soap field: ignore "lather" when followed by "games"
    if field == "soap" and re.match(r"^lather\s+games", line, flags=re.IGNORECASE):
        return None

    # Special handling for razor field: ignore "razor" when followed by "test"
    if field == "razor" and re.match(r"^razor\s+test", line, flags=re.IGNORECASE):
        return None

    aliases = FIELD_ALIASES.get(field, [field])

    patterns = []
    for alias in aliases:
        patterns.extend(get_patterns(alias))

    for pattern in patterns:
        # Use search instead of match to handle fields that appear in the middle of a line
        match = re.search(pattern, line, flags=re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Filter out values that are just field markers (e.g., "**") or empty
            if not value or value in ("**", "*"):
                continue
            return value

    return None


def get_patterns(alias: str) -> list[str]:
    """
    Get extraction patterns for a field alias, ordered by frequency/priority.

    Patterns are tried in order (0=highest priority, last=lowest priority).
    Patterns 0-14 have explicit markers (colon : or dash -) - highest priority.
    Patterns 14a-14b have explicit markers with equals sign (=) - medium priority.
    Pattern 15 is ambiguous (no explicit markers) and must remain last.

    Pattern 0 requires list item prefix (* or -) and is preferred over pattern 0b
    which matches narrative text without the prefix.

    Order is based on actual usage frequency from 2020-2025 data analysis.
    See docs/extraction_pattern_priorities.md for priority details.

    All patterns use non-greedy matching with lookahead to stop at next field marker
    when multiple fields appear on the same line.
    """
    # Get the stop pattern for next field markers
    next_field_pattern = _build_next_field_stop_pattern()
    # Build lookahead that stops at next field marker or end of line
    stop_lookahead = rf"(?={next_field_pattern}|$)"

    # Optional prefix to match field separator when fields appear on same line
    # Matches either:
    # - Start of line (^)
    # - Field separator with period (.*  or .* **)
    # - Field separator without period (*  or - ) - just the bullet/separator, not the field marker
    field_separator_prefix = r"(?:^|\.\*\s+|[-*]\s+)"

    return [
        # Pattern 0: Markdown bold with list prefix: * **alias:** value (highest priority)
        # Requires * or - prefix (list items) - preferred over narrative text
        # Colon/dash BEFORE second ** (e.g., * **Razor:** Blackbird)
        # Also matches when field appears after another: .* **Razor:**
        rf"{field_separator_prefix}[-*]\s+\*\*\b{alias}\b\s*[-:]\s*\*\*\s*(.+?){stop_lookahead}",  # * **alias:** value (list item)
        # Pattern 0b: Markdown bold without list prefix: **alias:** value (lower priority)
        # No * or - prefix (narrative text) - lower priority than list items
        # Colon/dash BEFORE second ** (e.g., **Razor:** Blackbird in narrative)
        # Also matches when field appears after another: .* **Razor:**
        rf"{field_separator_prefix}\*\*\b{alias}\b\s*[-:]\s*\*\*\s*(.+?){stop_lookahead}",  # **alias:** value (narrative)
        # Pattern 1: Simple explicit: Field: Value (20.66% usage - second most common)
        # Also matches when field appears after another: .* Field:
        rf"{field_separator_prefix}(?:[-*•‣⁃▪‧·~+]*\s*)?\b{alias}\b\s*[-:]\s*(.+?){stop_lookahead}",  # * alias: value (word boundary)
        # Pattern 2: Markdown bold: * **alias**: value (2.67% usage)
        # Colon/dash AFTER second ** (e.g., * **Razor**: Blackbird)
        # Also matches when field appears after another: .* **Razor**:
        rf"{field_separator_prefix}(?:[-*]\s*)?\*\*\b{alias}\b\*\*\s*[-:]\s*(.+?){stop_lookahead}",  # * **alias**: value
        # Pattern 3: Emoji-prefixed: *alias:* value (0.50% usage)
        rf"{field_separator_prefix}[^\w\s]?\s*\*\b{alias}\b\*\s*[-:]\s*(.+?){stop_lookahead}",  # emoji-prefixed *alias:* value
        # Pattern 5: Emoji-prefixed: *alias:* value variant 2 (0.43% usage)
        # emoji-prefixed *alias:* value (variant 2)
        rf"{field_separator_prefix}[^\w\s]\s*\*+\s*\b{alias}\b\s*\*+[-:]\s*(.*?){stop_lookahead}",
        # Pattern 6: Markdown bold: * **Field** Value no separator (0.20% usage)
        # No colon/dash, handles both **razor** and **razor ** (space before closing **)
        # (e.g., * **Razor** Blackbird, * **Razor**Blackbird, * **razor ** value,
        # - **Razor** Blackbird, **Razor** Blackbird)
        # * **Field** Value (no separator, space optional before closing **)
        rf"{field_separator_prefix}(?:[-*]\s*)?\*\*\b{alias}\b\s*\*\*\s*(.+?){stop_lookahead}",
        # Pattern 7: Emoji-prefixed: *alias:* value variant (0.16% usage)
        # emoji-prefixed *alias:* value (variant)
        rf"{field_separator_prefix}[^\w\s]\s*\*+\s*\b{alias}\b[-:]\s*\*+\s*(.*?){stop_lookahead}",
        # Pattern 8: Markdown bold: * **alias - value** (0.07% usage)
        # Note: This pattern has value inside **, so we need to stop before closing **
        # but also check for next field marker
        rf"{field_separator_prefix}(?:[-*]\s*)?\*\*\b{alias}\b\s*[-:]\s*(.+?)(?:\*\*|{stop_lookahead})",  # * **alias - value**
        # Pattern 9: Underscore: __alias:__ value (0.04% usage)
        rf"{field_separator_prefix}(?:[-*]\s*)?__{alias}:\__\s*(.+?){stop_lookahead}",  # __alias:__ value
        # Pattern 10: Forward slash: **alias //** value (0.02% usage)
        rf"{field_separator_prefix}(?:[-*]\s*)?\*\*\b{alias}\b\s*//\*\*\s*(.+?){stop_lookahead}",  # **alias //** value
        # Pattern 11: Checkmark: ✓Field: Value (0.00% usage)
        rf"{field_separator_prefix}✓\s*\b{alias}\b\s*[-:]\s*(.+?){stop_lookahead}",  # ✓Field: Value or ✓ Field: Value
        # Pattern 12: Double hash: ##alias## - value (0.00% usage)
        rf"{field_separator_prefix}(?:[-*•‣⁃▪‧·~+]\s*)?\#\#\b{alias}\b\#\#\s*[-:]\s*(.+?){stop_lookahead}",  # ##alias## - value
        # Pattern 13: Simple explicit: Field - Value (0.00% usage)
        rf"{field_separator_prefix}(?:[-*•‣⁃▪‧·~+]*\s*)?\b{alias}\b\s+[-:]\s*(.+?){stop_lookahead}",  # * alias - value (word boundary)
        # Pattern 14a: Simple explicit with equals: * Field = Value (medium priority, after : and -)
        # List item format with equals sign delimiter
        rf"{field_separator_prefix}[-*]\s+\b{alias}\b\s*=\s*(.+?){stop_lookahead}",  # * alias = value (list item)
        # Pattern 14b: Simple explicit with equals: Field = Value (medium priority, after : and -)
        # Narrative format with equals sign delimiter
        rf"{field_separator_prefix}\b{alias}\b\s*=\s*(.+?){stop_lookahead}",  # alias = value (narrative)
        # Pattern 15: Ambiguous format (0.08% usage - MUST REMAIN LAST)
        # This pattern is tried last and only matches if no explicit markers found
        # Note: This pattern already has negative lookahead for :, -, and =, so we add
        # the next field stop pattern as an additional constraint
        rf"{field_separator_prefix}\b{alias}\b\s+(?![^:]*:)(?![^\-]*\-)(?![^=]*=)(.+?){stop_lookahead}",  # Field product (no colon/dash/equals)
    ]
