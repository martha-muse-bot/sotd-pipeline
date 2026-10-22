# Error Handling Philosophy for SOTD Pipeline

## Overview

The SOTD pipeline is designed for **interactive use by developers**. This means we prioritize **fail-fast error handling** to ensure issues are caught and fixed immediately during development, rather than being hidden or handled gracefully.

## Core Principles

### **MANDATORY**: Fail-Fast for Interactive Development

**ALWAYS** prefer fail-fast error handling for internal logic errors to ensure issues are caught and fixed immediately.

#### When to Use Fail-Fast (Let Exceptions Bubble Up)

- **Internal logic errors**: Data validation failures, configuration errors, algorithm bugs
- **Data structure violations**: Missing required fields, invalid data types, corrupted data
- **Configuration errors**: Invalid regex patterns, missing YAML files, malformed catalogs
- **Development-time issues**: Import errors, syntax errors, type mismatches

#### When to Use Defensive Error Handling (Return None/Empty)

- **External API failures**: Reddit API rate limits, network timeouts, server errors
- **Missing optional data**: Files that may not exist, optional fields in data
- **Graceful degradation**: When partial results are acceptable
- **User input validation**: Invalid command line arguments, malformed user input

## Enhanced Regex Error Reporting

The pipeline includes **enhanced regex error reporting** that provides detailed context when regex pattern compilation fails. This is implemented across all phases and follows the fail-fast philosophy.

### Error Message Format

Enhanced regex error messages include comprehensive context:

```
Invalid regex pattern '[invalid' in File: data/handles.yaml, Brand: Test Maker, Model: Test Model, Section: artisan_handles: unterminated character set at position 7
```

### Context Information Provided

- **File path**: Exact location of the YAML file containing the pattern
- **Brand/Maker**: Product brand or maker information
- **Model/Scent**: Product model or scent information  
- **Section**: Catalog section (e.g., artisan_handles, known_knots)
- **Field**: Field name (for filter patterns)
- **Specific regex error**: Detailed error from Python's re module

### Implementation Pattern

All regex compilation uses the enhanced error reporting utilities:

```python
from sotd.match.utils.regex_error_utils import compile_regex_with_context, create_context_dict

# Create context with relevant information
context = create_context_dict(
    file_path="data/filename.yaml",
    brand=brand_name,
    model=model_name,
    # Additional context as needed
)

# Use enhanced compilation
compiled_regex = compile_regex_with_context(pattern, context)
```

### Coverage

Enhanced regex error reporting is implemented across:

- **Match Phase**: All product matchers (razors, blades, brushes, soaps, handles)
- **Enrich Phase**: Catalog loaders and pattern utilities
- **Extract Phase**: Filter patterns and validation
- **All YAML Catalogs**: handles.yaml, knots.yaml, razors.yaml, blades.yaml, soaps.yaml, extract_filters.yaml

### Benefits

- **Immediate Issue Identification**: Users can quickly locate the exact file and pattern causing the error
- **Actionable Error Messages**: Clear guidance on what needs to be fixed
- **Development Efficiency**: Reduces debugging time for regex-related issues
- **Consistent Error Handling**: All regex errors follow the same detailed format

## Error Handling Patterns by Phase

### Fetch Phase: Defensive for External APIs, Fail-Fast for Configuration

```python
def fetch_threads(subreddit: str, year: int, month: int) -> list:
    """Fetch SOTD threads with mixed error handling."""
    # Fail fast on configuration errors
    if not subreddit or year < 2020 or month < 1 or month > 12:
        raise ValueError(f"Invalid parameters: subreddit={subreddit}, year={year}, month={month}")
    
    # Defensive for external API calls
    try:
        return reddit_api.search_threads(subreddit, year, month)
    except praw.exceptions.APIException as e:
        logger.warning(f"Reddit API error: {e}")
        return []
```

### Extract/Match/Enrich Phases: Fail-Fast for Internal Logic

```python
def extract_products(comment: dict) -> dict:
    """Extract products with fail-fast validation."""
    # Fail fast on invalid input
    if not isinstance(comment, dict):
        raise ValueError(f"Expected dict, got {type(comment)}")

    required_fields = ["id", "body", "created_utc"]
    for field in required_fields:
        if field not in comment:
            raise ValueError(f"Missing required field '{field}' in comment")

    # Process with fail-fast approach
    return process_extraction(comment)
```

### Aggregate Phase: Fail-Fast for Data Validation, Defensive for Individual Aggregations

```python
def aggregate_month(year: int, month: int) -> dict:
    """Aggregate month data with mixed error handling."""
    # Fail fast on invalid parameters
    if year < 2020 or month < 1 or month > 12:
        raise ValueError(f"Invalid year/month: {year}/{month}")
    
    # Load data with fail-fast validation
    data = load_enriched_data(get_data_path(year, month))  # Will fail fast on data issues
    
    # Individual aggregations can fail gracefully
    try:
        razors = aggregate_razors(data)
    except Exception as e:
        logger.warning(f"Razor aggregation failed: {e}")
        razors = []
    
    return {
        "razors": razors,
        # ... other aggregations
    }
```

## Implementation Examples

### Fail-Fast Input Validation

```python
def validate_sotd_comment(comment: dict) -> bool:
    """Validate SOTD comment structure."""
    required_fields = ["id", "body", "created_utc", "author"]
    for field in required_fields:
        if field not in comment:
            # Fail fast - this is a data structure violation
            raise ValueError(f"Missing required field '{field}' in comment: {comment}")
    return True
```

### Fail-Fast Configuration Loading

```python
def load_catalog(catalog_path: Path) -> dict:
    """Load product catalog with fail-fast validation."""
    if not catalog_path.exists():
        # Fail fast - missing catalog is a configuration error
        raise FileNotFoundError(f"Catalog file not found: {catalog_path}")

    try:
        with catalog_path.open("r", encoding="utf-8") as f:
            catalog = yaml.safe_load(f)
    except yaml.YAMLError as e:
        # Fail fast - malformed YAML is a configuration error
        raise ValueError(f"Invalid YAML in catalog {catalog_path}: {e}")

    if not isinstance(catalog, dict):
        # Fail fast - invalid structure is a configuration error
        raise ValueError(f"Catalog must be a dict, got {type(catalog)}")

    return catalog
```

### Defensive External API Handling

```python
def fetch_reddit_comments(thread_id: str) -> list:
    """Fetch Reddit comments with defensive error handling."""
    try:
        submission = reddit.submission(thread_id)
        comments = list(submission.comments)
        return comments
    except praw.exceptions.APIException as e:
        # External API failure - handle gracefully
        logger.warning(f"Reddit API error for thread {thread_id}: {e}")
        return []
    except Exception as e:
        # Unexpected external error - handle gracefully
        logger.error(f"Unexpected error fetching thread {thread_id}: {e}")
        return []
```

## CLI Error Handling

```python
def main(argv: list[str] | None = None) -> int:
    """Main CLI with appropriate error handling."""
    try:
        args = parse_args(argv)
        return run_phase(args)
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user")
        return 1
    except ValueError as e:
        # User input validation errors - clear message
        print(f"[ERROR] Invalid input: {e}")
        return 1
    except FileNotFoundError as e:
        # Configuration errors - clear message
        print(f"[ERROR] Configuration error: {e}")
        return 1
    except Exception as e:
        # Internal errors - fail fast with debug info
        print(f"[ERROR] Internal error: {e}")
        if args.debug:
            import traceback

            traceback.print_exc()
        return 1
```

## Testing Error Handling

### Test Fail-Fast Behavior

```python
def test_fail_fast_on_invalid_input():
    """Test that functions fail fast on invalid input."""
    with pytest.raises(ValueError, match="Expected dict"):
        extract_products("not a dict")


def test_fail_fast_on_missing_fields():
    """Test that functions fail fast on missing required fields."""
    incomplete_comment = {"id": "123", "body": "test"}
    with pytest.raises(ValueError, match="Missing required field"):
        extract_products(incomplete_comment)
```

### Test Defensive Behavior

```python
def test_defensive_on_external_failure():
    """Test that functions handle external failures gracefully."""
    with patch("reddit.submission") as mock_submission:
        mock_submission.side_effect = praw.exceptions.APIException("Rate limit")
        result = fetch_reddit_comments("test_id")
        assert result == []
```

## Benefits of This Approach

1. **Immediate Issue Detection**: Problems are caught during development, not in production
2. **Clear Error Messages**: Fail-fast errors provide specific information about what went wrong
3. **Data Quality**: Ensures data integrity by failing on invalid data structures
4. **Developer Productivity**: Reduces debugging time by surfacing issues immediately
5. **Configuration Validation**: Catches configuration errors at startup

## Common Mistakes to Avoid

### ❌ Don't Catch All Exceptions

```python
# BAD: Hides important errors
try:
    result = process_data(data)
except Exception as e:
    logger.warning(f"Error processing data: {e}")
    return None
```

### ❌ Don't Return None for Configuration Errors

```python
# BAD: Configuration errors should fail fast
def load_config(path: Path) -> dict | None:
    if not path.exists():
        return None  # Should raise FileNotFoundError
```

### ✅ Do Use Specific Exception Handling

```python
# GOOD: Handle specific external errors
try:
    result = api_call()
except requests.RequestException as e:
    logger.warning(f"API error: {e}")
    return None
# Let other exceptions bubble up
```

### ✅ Do Validate Early and Often

```python
# GOOD: Validate input immediately
def process_comment(comment: dict) -> dict:
    if not isinstance(comment, dict):
        raise ValueError(f"Expected dict, got {type(comment)}")

    required_fields = ["id", "body"]
    for field in required_fields:
        if field not in comment:
            raise ValueError(f"Missing required field '{field}'")

    return process_validated_comment(comment)
```

## Summary

The SOTD pipeline follows a **fail-fast philosophy** for interactive development:

- **Fail fast** on internal logic errors, configuration issues, and data validation problems
- **Handle gracefully** external API failures, network issues, and optional data
- **Provide clear error messages** that help developers identify and fix issues quickly
- **Validate early** to catch problems as soon as possible

This approach ensures that the pipeline is reliable, debuggable, and maintains high data quality while being robust against external failures. 