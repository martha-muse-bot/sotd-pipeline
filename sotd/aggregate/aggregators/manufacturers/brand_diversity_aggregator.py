#!/usr/bin/env python3
"""Brand diversity aggregator for counting unique soaps per brand."""

from typing import Any, Dict, List

import pandas as pd


def aggregate_brand_diversity(
    soap_makers: List[Dict[str, Any]], soaps: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Aggregate brand diversity data from pre-aggregated soap data.

    This aggregator takes the already aggregated soap_makers and soaps data
    to count unique soaps per brand, preserving full brand names.

    Note: This aggregator does not filter by unique soap count - all brands
    are included. Filtering (e.g., 5+ unique soaps) should be handled
    during report generation.

    Args:
        soap_makers: List of soap maker aggregations with maker field
        soaps: List of soap aggregations with name field

    Returns:
        List of brand diversity aggregations with rank, maker, and unique_soaps fields
    """
    if not soap_makers or not soaps:
        return []

    # Extract brand names from soap_makers (which have full names like "Barrister and Mann")
    # Handle both "brand" (monthly) and "name" (annual) field names
    brand_names = set()
    for maker_data in soap_makers:
        brand = maker_data.get("brand") or maker_data.get("name", "")
        if brand:
            brand = str(brand).strip()
            if brand:
                brand_names.add(brand)

    if not brand_names:
        return []

    # Count unique soaps per brand from soaps data
    brand_soap_counts = {}
    for soap_data in soaps:
        soap_name = soap_data.get("name", "").strip()
        if not soap_name:
            continue

        # Extract brand from soap name (first part before " - ")
        # Format is typically "Brand - Scent"
        if " - " in soap_name:
            brand = soap_name.split(" - ")[0].strip()
        else:
            # Fallback: use the full name if no delimiter
            brand = soap_name

        if brand in brand_names:
            if brand not in brand_soap_counts:
                brand_soap_counts[brand] = set()
            brand_soap_counts[brand].add(soap_name)

    # Convert all brands to list (no filtering - let report generation handle limits)
    diversity_data = []
    for brand, soap_names in brand_soap_counts.items():
        unique_soap_count = len(soap_names)
        diversity_data.append({"brand": brand, "unique_soaps": unique_soap_count})

    if not diversity_data:
        return []

    # Convert to DataFrame for efficient sorting
    df = pd.DataFrame(diversity_data)

    # Sort by unique_soaps desc, then by brand name asc for tie-breaking
    df = df.sort_values(["unique_soaps", "brand"], ascending=[False, True])
    df = df.reset_index(drop=True)

    # Add rank field with competition ranking (1, 2, 2, 4, 5...)
    # Ties get the same rank, and the next rank skips the tied positions
    df["temp_rank"] = range(1, len(df) + 1)
    df["rank"] = df.groupby("unique_soaps", sort=False)["temp_rank"].transform("min")
    df = df.drop("temp_rank", axis=1)

    # Convert to list of dictionaries
    result = []
    for row in df.to_dict(orient="records"):  # type: ignore[reportCallIssue]  # pandas-stubs lack the "records" overload; runtime yields plain dicts
        result.append(
            {
                "rank": int(row["rank"]),
                "brand": row["brand"],
                "unique_soaps": int(row["unique_soaps"]),
            }
        )

    return result
