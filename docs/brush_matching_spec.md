# Brush Matching Specification

## Catalog Brushes vs. Combo Brushes

- **Catalog-driven brushes**: These are brushes that are explicitly defined in the catalog (e.g., `Simpson Chubby 2`, `Muninn Woodworks/EldrormR Industries / BFM`). They represent complete, commercially available products. For these, the matcher preserves the top-level `brand` and `model` fields AND populates the `handle` and `knot` subsections to reflect the complete brush. This provides both backward compatibility and the new unified structure.

- **Combo brushes**: These are user-assembled or dynamically split brushes that do **not** match any known brush in the catalog. The matcher splits the input into handle and knot components and matches each separately. For these, the matcher clears the top-level `brand` and `model` fields (sets them to `None`) and only populates the `handle` and `knot` subsections.

### Implementation Rule
- **For catalog-driven brushes**: Preserve top-level `brand`/`model` AND populate `handle`/`knot` sections with the same values to represent the complete brush.
- **For combo brushes**: Clear top-level `brand`/`model` (set to `None`) and only populate `handle`/`knot` sections.

This ensures that reporting, aggregation, and user-facing output are correct for both known products and user combos.

---

## Catalog pattern hygiene: Bristle Brushwerks vs fiber “bristle”

“Bristle” in SOTD text usually means **boar fiber** (e.g. Omega/Zenith “pure/bleached/unbleached bristle”), not the maker **Bristle Brushwerks**. Handle and knot catalog patterns for Bristle Brushwerks must require a Werks/Works form (`bristle.*brush ?w[eo]rks?`), matching `brushes.yaml` — never bare `bristle.*brush`. Qualified fiber phrases (`pure|bleached|unbleached|boar` + `bristle`) map to Boar in `fiber_utils.match_fiber`.

## Goal

Match and normalize shaving brush metadata from the `brush` field extracted during the extraction phase using a sophisticated strategy pattern with intelligent handle/knot separation.

## Input

A single `brush` string provided by the extraction phase. This string may contain:
- Simple brush descriptions: `"Simpson Chubby 2"`
- Complex handle/knot combinations: `"DG B15 w/ C&H Zebra"`
- Mixed specifications: `"Elite 26mm Boar handle w/ Declaration B10"`

## Matching Priority Order

The brush matcher follows a specific priority order to ensure correct handling of different input types:

1. **Correct Matches Check** (Fastest) - Check entire input against `brush` and `split_brush` sections in correct_matches.yaml
2. **Brush Splits Check** (Human-curated) - Check `brush_splits.yaml` for human-curated splits
3. **Automated Splitting on High-Priority Delimiters** - Split on "w/", "with", "in" before known brush check
4. **Complete Brush Matching** - Apply brush strategies (includes Known Brush matching)
5. **Dual Component Matching** - Try to match both handle and knot in same string (BEFORE medium priority splitting)
6. **Automated Splitting on Medium-Priority Delimiters** - Split on "-", "+" as fallback
7. **Single Component Fallback** - Try handle-only or knot-only matching

### Enhanced Correct Matches Integration

The system checks correct matches at multiple levels:

#### **Step 1: Full String Correct Matches**
- **Check the entire input string against both the `brush` and `split_brush` sections in `correct_matches.yaml`.**
    - If a match is found in the `brush` section, return a complete brush match.
      - *If handle enrichment is enabled (per `handle_matching: true` in `brushes.yaml`), the matcher will also perform a handle lookup and include the matched handle fields in the result, as described in [plan_complete_brush_handle_matching_tdd_implementation_2025-07-31.mdc](../plans/plan_complete_brush_handle_matching_tdd_implementation_2025-07-31.mdc).*
    - If a match is found in the `split_brush` section, return a split result with both handle and knot components, each matched using the appropriate catalog and matching logic.
- **Highest priority for complete brush matches and human-curated splits.**
- **The returned structure will include:**
    - For complete brush: top-level `brand`, `model`, and (if enriched) a `handle` subfield.
    - For split brush: `handle` and `knot` subfields, each with their own `brand`, `model`, and other matched attributes.

#### **Step 2: Split Component Correct Matches** 
- After splitting into handle and knot components, check each component individually
- Handle component checked against `handle` section in correct_matches.yaml
- Knot component checked against `knot` section in correct_matches.yaml
- Correct matches take priority over strategy-based matching for individual components

#### **Step 6: Dual Component Fallback Correct Matches**
- When attempting dual component matching on the entire string
- Check handle component against `handle` section in correct_matches.yaml
- Check knot component against `knot` section in correct_matches.yaml
- Correct matches take priority over strategy-based matching for individual components

### Correct Matches Priority Hierarchy
1. **Full String Correct Match** (Step 1) - Highest priority
2. **Split Component Correct Matches** (Step 2) - Component-level validation
3. **Dual Component Fallback Correct Matches** (Step 6) - Component-level validation
4. **Strategy-Based Matching** - Fallback when correct matches not found

## Output Structure

```python
{
    "original": "input_string",
    "matched": {
        "brand": str | None,
        "model": str | None,
        "fiber": str | None,
        "knot_size_mm": float | None,
        # Removed redundant fields: handle_maker, knot_maker
        "handle": {
            "brand": str | None,
            "model": str | None,
            "source_text": str | None,
            "_matched_by": str | None,  # Strategy attribution
            "_pattern": str | None,  # Pattern used for matching
        }
        | None,
        "knot": {
            "brand": str | None,
            "model": str | None,
            "fiber": str | None,
            "knot_size_mm": float | None,
            "source_text": str | None,
            "_matched_by": str | None,  # Strategy attribution
            "_pattern": str | None,  # Pattern used for matching
        }
        | None,
        "user_intent": str | None,  # "handle_primary" | "knot_primary" | None
    }
    | None,
    "match_type": "exact|regex|alias|brand|fiber|knot|artisan|unmatched" | None,
    "pattern": str | None,
}
```

**Note:**
- The `handle` and `knot` subsections are always present in the output (when information is available), regardless of whether the match was catalog-driven or split-driven.
- For catalog-driven matches (e.g., BFM), these subsections are populated directly from the catalog's nested `handle` and `knot` fields if present. For split/strategy matches, they are inferred from the input and matching logic.
- **New fields**: `source_text` provides the original text that was matched for each component, `_matched_by` indicates which strategy was used, and `_pattern` shows the specific pattern that matched.
- **Removed fields**: `handle_maker` and `knot_maker` are no longer included as they were redundant with the handle/knot section structure.

### Example Output (Simple Catalog Brush, e.g., Simpson Chubby 2)
```python
{
    "original": "Simpson Chubby 2",
    "matched": {
        "brand": "Simpson",
        "model": "Chubby 2",
        "fiber": "Badger",
        "knot_size_mm": 27,
        "handle": {
            "brand": "Simpson",
            "model": "Chubby 2",
            "source_text": "Simpson Chubby 2",
            "_matched_by": "known_brush",
            "_pattern": "\\bchubby\\s*2\\b",
        },
        "knot": {
            "brand": "Simpson",
            "model": "Chubby 2",
            "fiber": "Badger",
            "knot_size_mm": 27,
            "source_text": "Simpson Chubby 2",
            "_matched_by": "known_brush",
            "_pattern": "\\bchubby\\s*2\\b",
        },
    },
    "match_type": "regex",
    "pattern": "\\bchubby\\s*2\\b",
}
```

### Example Output (Complex Catalog Brush, e.g., BFM)
```python
{
    "original": "Muninn Woodworks BFM",
    "matched": {
        "brand": "Muninn Woodworks/EldrormR Industries",
        "model": "BFM",
        "fiber": "Synthetic",
        "knot_size_mm": 50,
        "handle": {
            "brand": "Muninn Woodworks",
            "model": None,
            "source_text": "Muninn Woodworks BFM",
            "_matched_by": "known_brush",
            "_pattern": "\\bbfm\\b",
        },
        "knot": {
            "brand": "Moti",
            "model": "Motherlode",
            "fiber": "Synthetic",
            "knot_size_mm": 50,
            "source_text": "Muninn Woodworks BFM",
            "_matched_by": "known_brush",
            "_pattern": "\\bbfm\\b",
        },
    },
    "match_type": "regex",
    "pattern": "\\bbfm\\b(.*50mm)?",
}
```

## Integration with correct_matches.yaml

- The file `data/correct_matches.yaml` contains manually confirmed brush matches.
- If a brush string matches an entry in this file, it is matched directly, and all catalog fields are included in the output.
- This takes precedence over all regex and fallback strategies.
- The `match_type` will be `exact` for these matches.

### User Intent Preservation

**Important**: The system preserves user intent information when processing correct matches to prevent data loss.

- **User Intent Detection**: The system detects whether a user considers a composite brush "handle-primary" or "knot-primary" based on the order of components in the input string.
- **Data Preservation**: When brushes are added to `correct_matches.yaml`, the system maintains the same user intent that would be detected through automated matching.
- **No Data Loss**: Correct matches enhance rather than degrade data quality by preserving all available information, including user intent.
- **Consistent Behavior**: All correct match processing methods (`_process_handle_knot_correct_match`, `_process_split_brush_correct_match`, `_process_regular_correct_match`, `_process_split_result`) include user intent detection.

**Example**: For input "G5C Rad Dinosaur Creation", the system detects "knot_primary" intent (G5C appears first) and preserves this information whether the brush is matched through automated processing or correct matches.

## Complete Brush Handle Matching

The brush matching system supports complete brush handle matching for brands that require handle/knot splitting. This feature allows the system to automatically split and match brush components for brands that are known to require this approach.

### Configuration

Brands can be configured to use complete brush handle matching by setting `handle_matching: true` in the `brushes.yaml` catalog:

```yaml
brands:
  declaration_grooming:
    handle_matching: true  # Brand-level configuration
    models:
      cold_2_0:
        handle_matching: false  # Model-level override
```

### Hierarchical Configuration

- **Brand-level**: Set `handle_matching: true` at the brand level to enable for all models
- **Model-level**: Override brand-level setting for specific models
- **Default**: If not specified, `handle_matching` defaults to `false`

### Complete Brush Handle Matching Workflow

When `handle_matching: true` is configured for a brand:

1. **Configuration Check**: System checks if the brand requires handle matching
2. **Handle Pattern Matching**: Uses `HandleMatcher` to match handle patterns for the brand
3. **Result Enhancement**: Enhances existing brush match with handle information
4. **Fail Fast**: If handle matching fails, raises `ValueError` for debugging

**Note**: This feature is integrated into the existing brush matching workflow rather than being a separate process. It enhances complete brush matches that already have `brand` and `model` fields set.

### Implementation Details

- **Method**: Uses `_complete_brush_handle_matching()` method in `BrushMatcher`
- **Handle Patterns**: Searches across all sections in `handles.yaml` for the brand
- **Error Handling**: Uses fail-fast approach - raises `ValueError` if handle matching fails
- **Integration**: Called from two sites in the main `match()` method workflow
- **Preservation**: Maintains complete catalog specifications in match output

### Example Processing

```
Input: "Declaration B2 Washington"
Configuration: declaration_grooming.handle_matching = true

1. Configuration Check: handle_matching = true for Declaration Grooming
2. Handle Pattern Matching: "Washington" matches Declaration Grooming Washington handle
3. Result Enhancement: Enhanced brush match with handle information
4. Result: Unified brush with complete handle/knot specifications
```

### Benefits

- **Automatic Processing**: No manual intervention required for configured brands
- **Consistent Results**: Standardized handle matching for known brands
- **Data Preservation**: Maintains all catalog specifications in output
- **Fail-Fast Debugging**: Clear error messages when handle matching fails
- **Integration**: Seamlessly integrated into existing brush matching workflow

## Architecture

The system uses a **Strategy Pattern** with multiple specialized matching strategies tried in priority order, combined with intelligent handle/knot splitting and content analysis.

### Matching Steps (Sequential Processing)

1. **Step 1: Correct Matches Check** - Check entire input against `brush` and `split_brush` sections in correct_matches.yaml
2. **Step 2: Brush Splits Check** - Check `brush_splits.yaml` for human-curated splits
3. **Step 3: Automated Splitting on High-Priority Delimiters** - Split on "w/", "with", "in" before known brush check
   - Check handle component against `handle` section in correct_matches.yaml
   - Check knot component against `knot` section in correct_matches.yaml
   - Fall back to strategy-based matching for individual components
4. **Step 4: Complete Brush Matching** - Apply brush-specific strategies to full string (includes Known Brush matching)
5. **Step 5: Dual Component Matching** - Try to match both handle and knot in same string (BEFORE medium priority splitting)
   - Check handle component against `handle` section in correct_matches.yaml
   - Check knot component against `knot` section in correct_matches.yaml
   - Fall back to strategy-based matching for individual components
   - Create composite brush if both components match
6. **Step 6: Automated Splitting on Medium-Priority Delimiters** - Split on "-", "+" as fallback
   - Check handle component against `handle` section in correct_matches.yaml
   - Check knot component against `knot` section in correct_matches.yaml
   - Fall back to strategy-based matching for individual components
7. **Step 7: Single Component Fallback** - Try handle-only or knot-only matching

### Strategy Priority Order (Within Each Step)

1. **Correct Matches File** (highest priority within each step)
2. **KnownBrushMatchingStrategy** - Exact catalog matches from `known_brushes` section
3. **DeclarationGroomingBrushMatchingStrategy** - DG-specific patterns with smart brand detection
4. **ChiselAndHoundBrushMatchingStrategy** - C&H versioned knots (V10-V27)
5. **OmegaSemogueBrushMatchingStrategy** - Omega/Semogue brand patterns
6. **ZenithBrushMatchingStrategy** - Zenith brand patterns  
7. **OtherBrushMatchingStrategy** - Generic brand patterns from `other_brushes` section

## Intelligent Handle/Knot Splitting

### Delimiter Recognition
The system recognizes various delimiters and applies semantic understanding:

- **`" w/ "`, `" with "`** - Knot-ambiguous delimiters (requires content analysis)
- **`" in "`** - Handle-primary delimiter  
- **`" / "`, `"/"`, `" - "`** - Neutral delimiters

### Data-Driven Validation and Real-World Patterns

The brush splitter logic has been validated against real SOTD data to ensure it handles actual community usage patterns correctly.

#### Real-World Data Analysis
- **Analyzed 5+ months of real SOTD data** (9+ years available)
- **Found 0 cases** where both " in " and " x " appear together in the same brush string
- **Confirmed realistic patterns** from actual community data

#### Common Real-World Patterns

**Handle/Knot Combinations:**
- `"Dogwood Handcrafts/Zenith B2 Boar"` → Handle: "Dogwood Handcrafts", Knot: "Zenith B2 Boar"
- `"Mozingo/Declaration B2"` → Handle: "Mozingo", Knot: "Declaration B2"
- `"Declaration B2 in Mozingo handle"` → Handle: "Mozingo handle", Knot: "Declaration B2"

**Brand Collaborations:**
- `"Druidia x Mammoth 26mm SHD"` → Brand collaboration (not handle/knot split)
- `"AP Shaveco x Declaration Grooming B10"` → Brand collaboration (not handle/knot split)

**Size Specifications:**
- `"24mm x 51mm"`, `"65mm x 30mm"` → Size specifications (not delimiters)
- `"28mm x 52mm"` → Knot specifications (diameter x loft)

#### Test Case Validation
**Before (unrealistic test cases):**
- ❌ `"Declaration B2 in 26mm x 52mm x 48mm"` (doesn't exist in real data)
- ❌ `"Zenith B2 / 28mm x 52mm"` (unrealistic pattern)

**After (realistic test cases):**
- ✅ `"Declaration B2 in Mozingo handle"` → `('Mozingo handle', 'Declaration B2', 'handle_primary')`
- ✅ `"Dogwood Handcrafts/Zenith B2 Boar"` → `('Dogwood Handcrafts', 'Zenith B2 Boar', 'high_reliability')`

#### Key Insights from Real Data
1. **"Zenith B2"** = Zenith brand B2 knot (not Declaration Grooming)
2. **"28mm x 52mm"** = knot specifications (diameter x loft), not a handle
3. **Real data patterns** are much simpler and more predictable than contrived test cases
4. **Brand collaborations** use " x " but are not handle/knot splits
5. **Size specifications** with " x " are not delimiters

#### Implementation Impact
- **Test cases updated** to use realistic patterns from actual SOTD data
- **Delimiter detection** works correctly with real-world patterns
- **All 33 brush splitter tests pass** with realistic data validation
- **No breaking changes** to existing functionality

### Dual Component Matching Enhancement

The system now includes dual component matching that runs BEFORE medium priority delimiter splitting to handle cases where the same maker produces both handle and knot:

#### **Step 5: Dual Component Matching**
- **Purpose**: Handle cases where the same maker produces both handle and knot components (e.g., "Wolf Whiskers - Mixed Badger/Boar")
- **Example**: `"Wolf Whiskers - Mixed Badger/Boar"` (Wolf Whiskers handle + Wolf Whiskers knot)
- **Process**: 
  1. Run handle matcher on entire string
  2. Run knot matcher on entire string  
  3. If both return valid matches from the same maker, create dual component brush structure
  4. Detect user intent based on component order in original string
- **Priority**: Runs BEFORE medium priority delimiter splitting to prevent false splits

#### **User Intent Tracking**
- **`"handle_primary"`**: Handle component appears first in input string
- **`"knot_primary"`**: Knot component appears first in input string
- **Application**: Tracks user's primary focus for both split and dual component scenarios
- **Example**: `"G5C Rad Dinosaur"` → `"knot_primary"`, `"Rad Dinosaur G5C"` → `"handle_primary"`

#### **Dual Component Validation**
- **Same-brand makers**: Valid dual component matches (e.g., "Wolf Whiskers - Mixed Badger/Boar" with Wolf Whiskers handle and knot)
- **Different-brand makers**: Standard dual component validation
- **Priority**: Dual component matches always take priority over medium priority delimiter splitting

### Content Analysis Scoring
Uses `_score_as_handle()` to determine which part is likely the handle:

**Handle Indicators (+points):**
- Contains "handle" keyword (+10)
- Matches `handles.yaml` patterns (+6 to +12 based on section)
- Handle-related terms: "stock", "custom", "artisan", "turned" (+2 each)

**Knot Indicators (-points):**
- Fiber types: "badger", "boar", "synthetic" (-8)
- Size patterns: "26mm" (-6)
- Versioning patterns: "V20" (-6)
- Multiple brush strategy matches (-4 to -8)

### Example Processing
```
Input: "DG B15 w/ C&H Zebra"
1. Split on " w/ " → ["DG B15", "C&H Zebra"]  
2. Score "DG B15" as handle: -4 (brush strategy match)
3. Score "C&H Zebra" as handle: +8 (handle pattern match)
4. Result: Handle="C&H Zebra", Knot="DG B15"
5. Match knot against strategies → Declaration Grooming B15
6. Match handle against handles.yaml → Chisel & Hound
```

## Fiber Strategy Tracking

The system tracks the **source** of fiber information:

### Strategy Types
- **`"user_input"`** - Explicitly specified by user (e.g., "26mm Boar")
- **`"yaml"`** - From catalog data (authoritative)
- **`"default"`** - Brand default values
- **`"conflict"`** - User input conflicts with catalog (both recorded)

### Resolution Priority
1. **YAML exact fields** (highest priority - authoritative manufacturer data)
2. **Parsed user input** (if no YAML field present)
3. **YAML default fields** (fallback only)
4. **Unset** (if no information available)

### Conflict Handling
When user input conflicts with catalog data:
```python
# User says "Synthetic", catalog says "Badger"
{
    "fiber": "Badger",  # YAML wins
    "fiber_strategy": "yaml",
    "fiber_conflict": "user_input: Synthetic",  # Conflict recorded
}
```

**Note**: Knot size processing has been moved to the enrich phase for better conflict resolution and catalog data preservation.

## Output Schema

```yaml
brand: string | null                    # Brush manufacturer
model: string | null                    # Brush model/name
fiber: "Badger" | "Boar" | "Synthetic" | null  # Knot fiber type
knot_size_mm: float | null             # Knot diameter in millimeters
# Removed redundant fields: handle_maker, knot_maker
handle:                                 # Handle subsection (if available)
  brand: string | null
  model: string | null
  source_text: string | null            # Original text that was matched
  _matched_by: string | null           # Strategy that produced the match
  _pattern: string | null              # Regex pattern that matched
knot:                                   # Knot subsection (if available)
  brand: string | null
  model: string | null
  fiber: string | null
  knot_size_mm: float | null
  source_text: string | null            # Original text that was matched
  _matched_by: string | null           # Strategy that produced the match
  _pattern: string | null              # Regex pattern that matched
user_intent: "handle_primary" | "knot_primary" | null  # User's primary focus
fiber_strategy: "user_input" | "yaml" | "default"    # Source of fiber information
match_type: "exact" | "regex" | "alias" | "brand" | "fiber" | "knot" | "artisan" | "unmatched"
pattern: string | null                  # Overall pattern that matched
```

## Brand-Specific Intelligence

### Declaration Grooming Strategy
- **Default matching**: Standalone patterns like `"B2"`, `"B15"` default to Declaration Grooming
- **Brand rejection**: Explicit other brands prevent false matches: `"Zenith B2"` → Zenith (not DG)
- **Context awareness**: `"DG B2"` → Declaration Grooming (explicit context)

### Chisel & Hound Strategy  
- **Version range**: Handles V10-V27 versioned knots
- **Abbreviation support**: "C&H", "Chisel & Hound", "chis hou"
- **Boundary validation**: V9 and V28 rejected (outside known range)

### Zenith/Omega/Semogue Strategies
- **Brand-specific defaults**: Zenith → Boar default, Omega → Boar default
- **Series recognition**: B-series patterns, model number patterns
- **Fiber inference**: Uses brand-typical fiber types when not specified

## Data Sources

### Primary Catalogs
- **`data/brushes.yaml`** - Main brush catalog with known_brushes, declaration_grooming, other_brushes sections
- **`data/handles.yaml`** - Handle maker patterns (artisan_handles, manufacturer_handles, other_handles)

### Catalog Structure Requirements
```yaml
# brushes.yaml
known_brushes:
  Brand Name:
    Model Name:
      fiber: "Badger|Boar|Synthetic"
      knot_size_mm: 26
      patterns:
        - "regex_pattern"

other_brushes:
  Brand Name:
    default: "Badger|Boar|Synthetic"    # Default fiber for brand
    knot_size_mm: 26                    # Optional default knot size  
    patterns:
      - "regex_pattern"

# handles.yaml  
artisan_handles:      # Highest priority
  Handle Maker:
    patterns:
      - "regex_pattern"
```

## Error Handling and Resilience

### Graceful Degradation
- **Missing catalogs**: Empty catalog handling
- **Invalid regex**: Pattern compilation errors logged and excluded
- **Strategy failures**: Continue to next strategy on exception
- **Malformed YAML**: Safe loading with error reporting

### Performance Optimizations
- **Pattern compilation**: Regex patterns compiled once at initialization
- **Strategy caching**: Results cached where appropriate
- **Priority ordering**: Most specific strategies tried first

## Testing Requirements

### Unit Test Coverage
- All regex patterns with positive/negative cases
- Boundary conditions (version ranges, size limits)
- Handle/knot splitting with various delimiters
- Fiber/knot size conflict detection and resolution
- Strategy priority order with overlapping patterns
- Error handling and edge cases

### Integration Test Coverage  
- Real catalog compatibility testing
- Production data validation
- Catalog change regression testing
- End-to-end workflow validation

## Future Enhancements

### Planned Improvements
- **Partial match extraction**: Return matched substrings rather than full input
- **Enhanced handle detection**: More sophisticated handle maker inference
- **Synonym expansion**: Handle common abbreviations and variations
- **Machine learning integration**: Pattern learning from user corrections

### Backwards Compatibility
- All changes maintain existing API contracts
- Legacy pattern support preserved
- Gradual migration strategies for breaking changes

## Assumptions and Limitations

### Current Assumptions
- Only one brush matched per comment
- Input restricted to structured `brush` field from extraction
- Regex-based matching sufficient for current accuracy requirements

### Known Limitations
- Complex multi-brush descriptions may not parse perfectly
- Regional naming variations may require pattern updates
- New brush releases require catalog maintenance

This specification reflects the current implementation as of the latest codebase review and should be maintained as the system evolves.
