# Brush Correct Matches Enhancement Specification

## Overview

This specification defines the enhancement to add `handle:` and `knot:` sections to `correct_matches.yaml`, allowing manual confirmation of handle and knot components for **combo brush/handle brushes**. Simple brushes like "Simpson Chubby 2" continue to work exactly as they do now using the existing `brush:` section. This enhancement is specifically for complex brushes that combine handle and knot components.

## Problem Statement

### Current Limitations

1. **Brush correct matches only store brand/model**: Current `brush:` section only captures brush brand and model, not the handle/knot breakdown
2. **Missing aggregation data**: Correct matches don't provide handle maker or knot maker information needed for aggregation
3. **Re-parsing required**: Even with correct matches, complex brushes still need handle/knot parsing for aggregation
4. **No handle/knot validation**: Can't use mismatch analyzer to validate handle and knot components separately

### Use Case Examples

#### Simple Brush (Unaffected)
**Input**: `"Simpson Chubby 2"`
**Behavior**: Continues to work exactly as now using `brush:` section
```yaml
brush:
  Simpson:
    Chubby 2:
      - "Simpson Chubby 2"
```

#### Combo Brush/Handle (New Enhancement)
**Input**: `"AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"`

**Current Behavior**:
- Correct match: Brand = "AP Shave Co", Model = "Black Matte Alumihandle Layered Comfort"
- Missing: Handle maker = "AP Shave Co", Knot maker = "Mühle", Knot model = "STF"

**Desired Behavior**:
- Handle: AP Shave Co (handle maker)
- Knot: Mühle STF (knot maker + model + size)

## Requirements

### Functional Requirements

#### FR-1: Handle Section Support
- Add `handle:` section to `correct_matches.yaml` for combo brush/handle brushes only
- Structure: `handle: {handle_maker: {handle_model | null: [input_strings]}}`
- Support both cases:
  - **Handle maker + model**: `{handle_maker: {handle_model: [input_strings]}}`
  - **Handle maker only**: `{handle_maker: {null: [input_strings]}}`
- Examples:
  ```yaml
  # Handle maker + specific model
  handle:
    AP Shave Co:
      Black Matte Alumihandle Layered Comfort:
        - "AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"
  
  # Handle maker only (no specific model)
  handle:
    Muninn Woodworks:
      null:
        - "Muninn Woodworks BFM"
  ```
- **Note**: Simple brushes like "Simpson Chubby 2" continue using the existing `brush:` section

#### FR-2: Knot Section Support
- Add `knot:` section to `correct_matches.yaml` for combo brush/handle brushes only
- Structure: `knot: {knot_maker: {knot_model: {strings: [input_strings], metadata: {...}}}}`
- Example:
  ```yaml
  knot:
    Mühle:
      STF:
        strings:
          - "AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"
        fiber: "Synthetic"
        knot_size_mm: 25.0
  ```
- **Note**: Simple brushes like "Simpson Chubby 2" continue using the existing `brush:` section

#### FR-3: Brush Matcher Enhancement
- Modify brush matcher to check `handle:` and `knot:` sections before regex matching
- When found in correct matches, bypass all parsing and regex logic
- Return complete handle/knot breakdown from correct matches

#### FR-4: Backward Compatibility
- Maintain existing `brush:` section functionality for simple brushes
- Existing brush correct matches (like "Simpson Chubby 2") continue to work unchanged
- No migration required for simple brushes - they stay in `brush:` section
- `handle:`/`knot:` sections are only for combo brush/handle brushes

#### FR-5: Reporting Layer Support
- Update reporting logic to handle brushes with only handle/knot data
- Fallback logic: if no brush brand/model, use knot brand/model for reporting
- Maintain aggregation functionality for handle makers and knot makers

### Non-Functional Requirements

#### NFR-1: Performance
- Correct matches must bypass all regex matching and parsing
- No performance regression for existing functionality
- Fast lookup for confirmed handle/knot combinations

#### NFR-2: Data Integrity
- All catalog specifications must be preserved in correct matches
- Handle and knot metadata must be complete and accurate
- No data loss during migration from `brush:` to `handle:`/`knot:` sections

#### NFR-3: Validation
- Support mismatch analyzer validation for handle and knot components
- Clear error messages for malformed correct matches
- Validation of handle/knot metadata completeness

## Data Structures

### Current Structure (Brush Section)
```yaml
brush:
  AP Shave Co:
    Black Matte Alumihandle Layered Comfort:
      - "AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"
```

### New Structure (Handle/Knot Sections)
```yaml
# Handle maker + specific model
handle:
  AP Shave Co:
    Black Matte Alumihandle Layered Comfort:
      - "AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"

# Handle maker only (no specific model)
handle:
  Muninn Woodworks:
    null:
      - "Muninn Woodworks BFM"

knot:
  Mühle:
    STF:
      strings:
        - "AP Shave Co - Black Matte Alumihandle Layered Comfort - 25mm Mühle STF"
      fiber: "Synthetic"
      knot_size_mm: 25.0
```

### Match Output Structure

#### Current Output (Brush Section)
```python
{
    "matched": {
        "brand": "AP Shave Co",
        "model": "Black Matte Alumihandle Layered Comfort",
        "handle_maker": None,  # Missing
        "handle": None,  # Missing
        "knot": None,  # Missing
    },
    "match_type": "exact",
}
```

#### New Output (Handle/Knot Sections)
```python
# Case 1: Handle maker + specific model
{
    "matched": {
        "brand": "Mühle",  # From knot
        "model": "STF",  # From knot
        "handle_maker": "AP Shave Co",
        "handle": {
            "brand": "AP Shave Co",
            "model": "Black Matte Alumihandle Layered Comfort",
            "source_text": "AP Shave Co - Black Matte Alumihandle Layered Comfort",
        },
        "knot": {
            "brand": "Mühle",
            "model": "STF",
            "fiber": "Synthetic",
            "knot_size_mm": 25.0,
            "source_text": "25mm Mühle STF",
        },
    },
    "match_type": "exact",
}

# Case 2: Handle maker only (no specific model)
{
    "matched": {
        "brand": "Moti",  # From knot
        "model": "Motherlode",  # From knot
        "handle_maker": "Muninn Woodworks",
        "handle": {
            "brand": "Muninn Woodworks",
            "model": None,  # No specific model
            "source_text": "Muninn Woodworks BFM",
        },
        "knot": {
            "brand": "Moti",
            "model": "Motherlode",
            "fiber": "Synthetic",
            "knot_size_mm": 50.0,
            "source_text": "Muninn Woodworks BFM",
        },
    },
    "match_type": "exact",
}
```

## Implementation Phases

### Phase 1: Data Structure Enhancement
- [ ] Update `correct_matches.yaml` to support `handle:` and `knot:` sections
- [ ] Add validation for new section structures
- [ ] Create migration utilities for existing brush entries

### Phase 2: Brush Matcher Enhancement
- [ ] Modify brush matcher to check `handle:` and `knot:` sections
- [ ] Implement correct match lookup for handle/knot combinations
- [ ] Add post-processing logic for handle/knot metadata

### Phase 3: Reporting Layer Updates
- [ ] Update aggregation logic to handle handle/knot-only brushes
- [ ] Implement fallback logic for reporting
- [ ] Add tests for new reporting behavior

### Phase 4: Validation and Tools
- [ ] Update mismatch analyzer to support handle/knot sections
- [ ] Add validation tools for handle/knot correct matches
- [ ] Create migration scripts for existing data

## Testing Strategy

### Unit Tests
- [ ] Test handle section lookup and parsing
- [ ] Test knot section lookup and parsing
- [ ] Test backward compatibility with existing brush section
- [ ] Test error handling for malformed correct matches

### Integration Tests
- [ ] Test complete brush matching workflow with handle/knot sections
- [ ] Test aggregation with handle/knot-only brushes
- [ ] Test reporting fallback logic

### Performance Tests
- [ ] Benchmark correct match lookup vs regex matching
- [ ] Test performance with large correct matches files
- [ ] Verify no regression in existing functionality

## Migration Strategy

### Phase 1: Parallel Support
- Support both `brush:` and `handle:`/`knot:` sections simultaneously
- Existing brush entries continue to work
- New entries can use either approach

### Phase 2: Gradual Migration
- Create migration tools to convert `brush:` entries to `handle:`/`knot:` format
- Validate migrated entries with mismatch analyzer
- Update documentation and examples

### Phase 3: Deprecation
- Mark `brush:` section as deprecated
- Encourage use of `handle:`/`knot:` sections for new entries
- Plan for eventual removal of `brush:` section

## Success Criteria

1. **Performance**: Correct matches bypass all regex matching and parsing
2. **Reliability**: Confirmed handle/knot combinations return consistent results
3. **Completeness**: All handle and knot metadata preserved in correct matches
4. **Compatibility**: Existing functionality continues to work unchanged
5. **Validation**: Mismatch analyzer can validate handle and knot components
6. **Reporting**: Aggregation and reporting work correctly with handle/knot-only brushes

## Risks and Mitigation

### Risk 1: Data Migration Complexity
- **Mitigation**: Create comprehensive migration tools and validation
- **Mitigation**: Support parallel operation during transition period

### Risk 2: Reporting Logic Changes
- **Mitigation**: Thorough testing of aggregation and reporting logic
- **Mitigation**: Clear fallback rules for handle/knot-only brushes

### Risk 3: Performance Impact
- **Mitigation**: Benchmark all changes and verify no regression
- **Mitigation**: Optimize correct match lookup performance

## Dependencies

- Existing brush matcher and splitter functionality
- Mismatch analyzer for validation
- Aggregation and reporting systems
- Test infrastructure for validation

## Timeline

- **Phase 1**: 1-2 days (data structure and validation)
- **Phase 2**: 2-3 days (brush matcher enhancement)
- **Phase 3**: 1-2 days (reporting layer updates)
- **Phase 4**: 1-2 days (validation and tools)
- **Total**: 5-9 days

## Conclusion

This enhancement will significantly improve the reliability and performance of brush matching by allowing manual confirmation of handle and knot components. The phased approach ensures backward compatibility while providing a clear migration path to the new structure. 