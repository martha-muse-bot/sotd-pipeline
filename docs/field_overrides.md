# Field Overrides for SOTD Pipeline

## Overview

The SOTD Pipeline includes a field override system that allows data analysts to correct extracted fields when the initial extraction is ambiguous or incorrect. This is particularly useful for cases where:

- Abbreviated product names (e.g., "Ko" for "Koraat")
- Ambiguous product references
- Missing fields that should have been extracted
- User feedback confirms the correct product

## How It Works

The override system integrates into the **extract phase** of the pipeline, ensuring that all downstream phases (match, enrich, aggregate) automatically receive the corrected data. Overrides are applied during field processing and include audit trails to track what was changed.

## Configuration

### Override File Location

By default, the system looks for overrides in:
```
data/extract_overrides.yaml
```

You can specify a custom location using the `--override-file` argument:
```bash
python run.py extract --month 2025-01 --override-file /path/to/custom_overrides.yaml
```

### Override File Format

The override file uses YAML format with the following structure:

```yaml
# Month in YYYY-MM format
2025-01:
  # Reddit comment ID
  m99b8f9:
    # Field name and corrected value
    razor: "Koraat"
    blade: "Gillette Minora Platinum"
  
  m99b8f0:
    soap: "Declaration Grooming - Seville"

2025-02:
  m99b8f1:
    brush: "Semogue 610"
```

### Bulk Overrides

Use the reserved month-level key `bulk` when many comment IDs share the same field value (e.g. mystery/Blind Date smushes rewritten to `Unknown Mystery`):

```yaml
2026-10:
  phnejcv:
    razor: Wilkinson black plastic
  bulk:
    - field: soap
      value: Unknown Mystery
      comment_ids:
        - abc123
        - def456
```

Rules:
- `bulk` is not a comment ID; it expands into the same in-memory map as per-ID overrides
- Each bulk entry requires `field`, `value`, and a non-empty `comment_ids` list
- If the same `comment_id` + `field` appears in both a per-ID entry and bulk (or in two bulk entries), loading **fails with `ValueError`** — there is no silent winner
- Per-ID and bulk on the **same comment but different fields** is allowed

### Valid Fields

Only these core fields can be overridden:
- `razor` - Straight razors, safety razors, etc.
- `blade` - Razor blades
- `brush` - Shaving brushes
- `soap` - Shaving soaps, creams, etc.

### Override Values

- Must be non-empty strings
- Maximum length: 200 characters
- Whitespace is automatically stripped
- Should be the corrected, normalized product name

## Usage Examples

### Correcting an Existing Field

**Original extraction:**
```json
{
  "razor": {
    "original": "Ko",
    "normalized": "Ko"
  }
}
```

**Override file:**
```yaml
2025-01:
  m99b8f9:
    razor: "Koraat"
```

**Result after override:**
```json
{
  "razor": {
    "original": "Ko",
    "normalized": "Koraat",
    "overridden": "Normalized"
  }
}
```

### Creating a Missing Field

**Original extraction:** No razor field

**Override file:**
```yaml
2025-01:
  m99b8f9:
    razor: "Feather Artist Club"
```

**Result after override:**
```json
{
  "razor": {
    "original": "Feather Artist Club",
    "normalized": "Feather Artist Club",
    "overridden": "Original,Normalized"
  }
}
```

### Multiple Field Corrections

**Override file:**
```yaml
2025-01:
  m99b8f9:
    razor: "Koraat"
    blade: "Gillette Minora Platinum"
    soap: "Declaration Grooming - Seville"
```

This will correct all three fields for the same comment.

## Audit Trail

The override system maintains a complete audit trail through the `overridden` field:

- **`"Normalized"`** - The `normalized` field was overridden, `original` preserved
- **`"Original,Normalized"`** - Both fields were created from the override value

Fields without overrides do not have an `overridden` field, making it easy to identify what was changed.

The match phase preserves `overridden` into matched (and thus enriched) output so Comment Modal can show Original vs Override from phase data after rematch.

## WebUI (Comment Modal)

From Comment Details in the WebUI you can edit extract overrides for the current comment:

1. Open a comment → **Edit overrides**
2. Set Override values for razor / blade / brush / soap (clear a field to remove that override)
3. **Save** writes `data/extract_overrides.yaml` only — it does not re-run the pipeline
4. Re-run `extract → match → enrich` with `--force` for that month so matched/enriched data (and the `overridden` flag) update

API:

- `GET /api/extract-overrides/{month}/{comment_id}`
- `PUT /api/extract-overrides/{month}/{comment_id}` — body keys upsert; `null` or `""` deletes that field

One-shot rematch after the `overridden` pass-through (or to refresh all override months):

```bash
python scripts/rerun_extract_override_months.py --dry-run
python scripts/rerun_extract_override_months.py
```

## Validation and Error Handling

### Automatic Validation

The system automatically validates:
- YAML syntax
- Field name validity
- Override value format (non-empty, reasonable length)
- Comment ID existence in source data
- Duplicate override prevention

### Error Handling

The system follows a **fail-fast** approach:
- Invalid override files cause immediate pipeline failure
- Clear error messages explain what went wrong
- Debug logging provides troubleshooting information

### Common Error Scenarios

**Invalid field name:**
```yaml
2025-01:
  m99b8f9:
    invalid_field: "value"  # Error: Invalid field 'invalid_field'
```

**Empty override value:**
```yaml
2025-01:
  m99b8f9:
    razor: ""  # Error: cannot be empty or whitespace-only
```

**Non-existent comment ID:**
```yaml
2025-01:
  nonexistent_id:  # Error: references non-existent comment IDs
    razor: "Koraat"
```

## Performance Considerations

- **Minimal overhead**: Override processing adds minimal performance impact
- **Efficient lookup**: Overrides are loaded once and cached for the entire pipeline run
- **Scalable**: Performance impact decreases with larger datasets

## Best Practices

### 1. Use Descriptive Values
```yaml
# Good
razor: "Koraat Moarteen 15/16 Full Hollow"

# Avoid
razor: "K"
```

### 2. Validate Against Source Data
Ensure comment IDs in your override file exist in the source data before running the pipeline.

### 3. Keep Overrides Focused
Only override fields that genuinely need correction. Don't use overrides for minor formatting preferences.

### 4. Document Changes
Use comments in your override file to document why changes were made:
```yaml
2025-01:
  m99b8f9:
    razor: "Koraat"  # User confirmed this was a Koraat razor
```

### 5. Regular Review
Periodically review and clean up override files to remove outdated corrections.

## Troubleshooting

### Debug Mode
Enable debug logging to see detailed override operations:
```bash
python run.py extract --month 2025-01 --debug
```

### Override Summary
The system provides summary statistics about loaded overrides:
```python
from sotd.extract.override_manager import OverrideManager

manager = OverrideManager(Path("data/extract_overrides.yaml"))
manager.load_overrides()
summary = manager.get_override_summary()
print(f"Loaded {summary['total_overrides']} overrides")
```

### Common Issues

**"Override file not found"**
- Check the file path in your `--override-file` argument
- Ensure the file exists and is readable

**"Invalid YAML syntax"**
- Validate your YAML file using an online YAML validator
- Check for missing colons, incorrect indentation, or special characters

**"Invalid field"**
- Ensure you're only using the four valid field names: `razor`, `blade`, `brush`, `soap`
- Check for typos or extra spaces

**"Non-existent comment IDs"**
- Verify that comment IDs in your override file exist in the source data
- Check that you're using the correct month format (YYYY-MM)

## Integration with Pipeline

The override system integrates seamlessly with the existing pipeline:

1. **Extract Phase**: Overrides are applied during field extraction
2. **Match Phase**: Receives corrected data automatically
3. **Enrich Phase**: Works with corrected field values
4. **Aggregate Phase**: Uses corrected data for statistics and reports

No changes are needed to downstream phases - they automatically benefit from the corrections.

## Example Workflow

1. **Identify Issues**: Review extraction results and identify ambiguous or incorrect fields
2. **Gather Feedback**: Get user confirmation or manual review of correct values
3. **Create Overrides**: Add corrections to `data/extract_overrides.yaml`
4. **Validate**: Check that all comment IDs exist in source data
5. **Run Pipeline**: Execute extract phase with overrides enabled
6. **Verify Results**: Confirm that corrections were applied correctly
7. **Monitor**: Use audit trail to track what was changed

## Support

For questions or issues with the override system:
- Check the error messages for specific guidance
- Enable debug logging for detailed information
- Review the validation rules and error handling sections
- Ensure your override file follows the correct format

The override system is designed to be robust and user-friendly, providing a reliable way to correct extraction issues while maintaining data integrity and audit trails.
