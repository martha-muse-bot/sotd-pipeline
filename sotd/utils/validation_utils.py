"""Validation utilities for the SOTD Pipeline.

This module provides common validation functions used across the pipeline
to ensure data quality and consistency.
"""

from typing import Any, Dict, List, Optional, cast


def validate_list_of_dicts(data: Any, data_name: str = "data") -> List[Dict[str, Any]]:
    """Validate that data is a list of dictionaries.

    Args:
        data: Data to validate
        data_name: Name of the data for error messages

    Returns:
        Validated list of dictionaries

    Raises:
        ValueError: If data is not a list of dictionaries
    """
    if not isinstance(data, list):
        raise ValueError(f"{data_name} must be a list")

    # OPTIMIZED: Use pandas operations for vectorized validation
    import pandas as pd

    if data:  # Only validate if data is not empty
        # Convert to pandas Series for vectorized type checking
        data_series = pd.Series(data)

        # Check if all items are dictionaries using vectorized operations
        is_dict_mask: pd.Series = data_series.apply(lambda x: isinstance(x, dict))  # type: ignore

        # Convert Series to bool for conditional check
        all_dicts = bool(is_dict_mask.all())
        if not all_dicts:
            # Find first non-dict item for error reporting
            # Find the first index where the value is False (not a dict)
            false_indices = cast(pd.Index, is_dict_mask.index[~is_dict_mask.to_numpy(dtype=bool)])
            if len(false_indices) > 0:
                first_invalid_idx = false_indices[0]
            else:
                # Fallback: should not happen, but handle edge case
                first_invalid_idx = 0
            raise ValueError(f"{data_name} item {first_invalid_idx} must be a dictionary")

    return data


def validate_required_fields(
    data: Dict[str, Any], required_fields: List[str], data_name: str = "data"
) -> None:
    """Validate that all required fields are present in a dictionary.

    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        data_name: Name of the data for error messages

    Raises:
        ValueError: If any required fields are missing
    """
    missing_fields = [field for field in required_fields if field not in data]
    if missing_fields:
        raise ValueError(f"{data_name} missing required fields: {missing_fields}")


def validate_field_types(
    data: Dict[str, Any], field_types: Dict[str, type], data_name: str = "data"
) -> None:
    """Validate that fields have the expected types.

    Args:
        data: Dictionary to validate
        field_types: Dictionary mapping field names to expected types
        data_name: Name of the data for error messages

    Raises:
        ValueError: If any fields have incorrect types
    """
    # OPTIMIZED: Use pandas operations for vectorized field type validation

    if not field_types:
        return

    # Create DataFrame from field types for vectorized operations
    fields_to_check = [
        (field, expected_type) for field, expected_type in field_types.items() if field in data
    ]

    if fields_to_check:
        # Check all field types using vectorized operations
        for field, expected_type in fields_to_check:
            if not isinstance(data[field], expected_type):
                raise ValueError(
                    f"{data_name} field '{field}' must be {expected_type.__name__}, "
                    f"got {type(data[field]).__name__}"
                )


def validate_non_empty_strings(
    data: Dict[str, Any], string_fields: List[str], data_name: str = "data"
) -> None:
    """Validate that string fields are non-empty after stripping whitespace.

    Args:
        data: Dictionary to validate
        string_fields: List of field names that should be non-empty strings
        data_name: Name of the data for error messages

    Raises:
        ValueError: If any string fields are empty or whitespace-only
    """
    for field in string_fields:
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{data_name} field '{field}' must be a non-empty string")


def validate_positive_integers(
    data: Dict[str, Any], integer_fields: List[str], data_name: str = "data"
) -> None:
    """Validate that integer fields are positive.

    Args:
        data: Dictionary to validate
        integer_fields: List of field names that should be positive integers
        data_name: Name of the data for error messages

    Raises:
        ValueError: If any integer fields are not positive
    """
    for field in integer_fields:
        if field in data:
            value = data[field]
            if not isinstance(value, (int, float)) or value <= 0:
                raise ValueError(f"{data_name} field '{field}' must be a positive number")


def validate_data_structure(
    data: Dict[str, Any], required_sections: List[str], data_name: str = "data"
) -> None:
    """Validate that data has the expected structure with required sections.

    Args:
        data: Dictionary to validate
        required_sections: List of required top-level sections
        data_name: Name of the data for error messages

    Raises:
        ValueError: If required sections are missing
    """
    missing_sections = [section for section in required_sections if section not in data]
    if missing_sections:
        raise ValueError(f"{data_name} missing required sections: {missing_sections}")


def validate_metadata_structure(
    metadata: Dict[str, Any], required_fields: Optional[List[str]] = None
) -> None:
    """Validate metadata structure with standard required fields.

    Args:
        metadata: Metadata dictionary to validate
        required_fields: Optional list of additional required fields

    Raises:
        ValueError: If metadata structure is invalid
    """
    if not isinstance(metadata, dict):
        raise ValueError("Metadata must be a dictionary")

    # Standard metadata fields
    standard_fields = ["total_shaves", "unique_shavers"]
    all_required = standard_fields + (required_fields or [])

    validate_required_fields(metadata, all_required, "metadata")
    validate_field_types(metadata, {field: int for field in standard_fields}, "metadata")
    validate_positive_integers(metadata, standard_fields, "metadata")


def validate_records_quality(records: List[Dict[str, Any]]) -> None:
    """Perform comprehensive data quality checks on records.

    Args:
        records: List of records to validate

    Raises:
        ValueError: If data quality issues are found
    """
    if not records:
        raise ValueError("No records to process")

    # Check for reasonable data volume
    if len(records) < 1:
        raise ValueError("No records to process")

    # Check for reasonable number of unique authors
    authors = set()
    for record in records:
        author = record.get("author")
        if author and isinstance(author, str) and author.strip():
            authors.add(author.strip())

    if len(authors) < 1:
        raise ValueError("No valid authors found in records")


def validate_catalog_structure(
    catalog: Dict[str, Any], required_fields: List[str], catalog_name: str = "catalog"
) -> None:
    """Validate catalog structure with required fields for each entry.

    Args:
        catalog: Catalog dictionary to validate
        required_fields: List of required fields for each catalog entry
        catalog_name: Name of the catalog for error messages

    Raises:
        ValueError: If catalog structure is invalid
    """
    if not isinstance(catalog, dict):
        raise ValueError(f"{catalog_name} must be a dictionary")

    for brand, metadata in catalog.items():
        if not isinstance(metadata, dict):
            raise ValueError(
                f"Invalid {catalog_name} structure for brand '{brand}': must be a dictionary"
            )

        missing_fields = [field for field in required_fields if field not in metadata]
        if missing_fields:
            raise ValueError(
                f"Missing required fields for brand '{brand}' in {catalog_name}: {missing_fields}"
            )


def validate_patterns_field(patterns: Any, brand: str, catalog_name: str = "catalog") -> None:
    """Validate that patterns field is a list of strings.

    Args:
        patterns: Patterns field to validate
        brand: Brand name for error messages
        catalog_name: Name of the catalog for error messages

    Raises:
        ValueError: If patterns field is invalid
    """
    if not isinstance(patterns, list):
        raise ValueError(f"'patterns' field must be a list for brand '{brand}' in {catalog_name}")

    for i, pattern in enumerate(patterns):
        if not isinstance(pattern, str):
            raise ValueError(f"Pattern {i} for brand '{brand}' must be a string in {catalog_name}")


def validate_month_format(month: str) -> str:
    """Validate and normalize month format (YYYY-MM).

    Args:
        month: Month string to validate

    Returns:
        Normalized month string

    Raises:
        ValueError: If month format is invalid
    """
    if not isinstance(month, str):
        raise ValueError("Month must be a string")

    month = month.strip()

    # Basic format validation
    if len(month) != 7 or month[4] != "-":
        raise ValueError("Month must be in YYYY-MM format")

    try:
        year = int(month[:4])
        month_num = int(month[5:7])

        if year < 1900 or year > 2100:
            raise ValueError("Year must be between 1900 and 2100")

        if month_num < 1 or month_num > 12:
            raise ValueError("Month must be between 01 and 12")

    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("Month must be in YYYY-MM format with valid numbers")
        raise

    return month


def validate_year_format(year: str) -> str:
    """Validate and normalize year format (YYYY).

    Args:
        year: Year string to validate

    Returns:
        Normalized year string

    Raises:
        ValueError: If year format is invalid
    """
    if not isinstance(year, str):
        raise ValueError("Year must be a string")

    year = year.strip()

    # Basic format validation
    if len(year) != 4:
        raise ValueError("Year must be in YYYY format")

    try:
        year_num = int(year)

        if year_num < 1900 or year_num > 2100:
            raise ValueError("Year must be between 1900 and 2100")

    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError("Year must be in YYYY format with valid numbers")
        raise

    return year


def validate_range_format(date_range: str) -> str:
    """Validate and normalize date range format (YYYY-MM:YYYY-MM).

    Args:
        date_range: Date range string to validate

    Returns:
        Normalized date range string

    Raises:
        ValueError: If date range format is invalid
    """
    if not isinstance(date_range, str):
        raise ValueError("Date range must be a string")

    date_range = date_range.strip()

    # Basic format validation
    if ":" not in date_range:
        raise ValueError("Date range must be in YYYY-MM:YYYY-MM format")

    parts = date_range.split(":")
    if len(parts) != 2:
        raise ValueError("Date range must be in YYYY-MM:YYYY-MM format")

    start_month, end_month = parts

    # Validate individual months
    start_month = validate_month_format(start_month)
    end_month = validate_month_format(end_month)

    # Validate that start is before end
    if start_month >= end_month:
        raise ValueError("Start month must be before end month")

    return f"{start_month}:{end_month}"


def validate_boolean_field(value: Any, field_name: str, data_name: str = "data") -> bool:
    """Validate that a field is a boolean value.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        data_name: Name of the data for error messages

    Returns:
        Boolean value

    Raises:
        ValueError: If value is not a boolean
    """
    if not isinstance(value, bool):
        raise ValueError(f"{data_name} field '{field_name}' must be a boolean")

    return value


def validate_optional_string_field(
    value: Any, field_name: str, data_name: str = "data"
) -> Optional[str]:
    """Validate that a field is either None or a non-empty string.

    Args:
        value: Value to validate
        field_name: Name of the field for error messages
        data_name: Name of the data for error messages

    Returns:
        String value or None

    Raises:
        ValueError: If value is not None or a non-empty string
    """
    if value is None:
        return None

    if not isinstance(value, str):
        raise ValueError(f"{data_name} field '{field_name}' must be None or a string")

    value = value.strip()
    if not value:
        return None

    return value
