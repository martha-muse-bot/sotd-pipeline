from typing import Any, Dict, List

import pandas as pd


def aggregate_blade_usage_distribution(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate blade usage distribution data from enriched records.

    Returns a list of blade usage distribution aggregations sorted by use_count asc.
    Each item includes rank field for delta calculations.
    Groups blade usage by use count ranges and shows total shaves and unique users
    for each range. Extracts use_count from blade.enriched.use_count.

    Args:
        records: List of enriched comment records

    Returns:
        List of blade usage distribution aggregations with rank, use_count,
        shaves, and unique_users fields
    """
    if not records:
        return []

    # Extract blade usage data from records
    usage_data = []
    for record in records:
        blade = record.get("blade") or {}
        blade_matched = blade.get("matched", {})
        blade_enriched = blade.get("enriched", {})
        # Also check for blade_enriched at top level (for test compatibility)
        if not blade_enriched:
            blade_enriched = record.get("blade_enriched", {})
        author = record.get("author", "").strip()

        # Skip if no matched blade data or no author
        if not blade_matched or not author:
            continue

        # Get use_count from enriched data, default to 1 if not available
        use_count = blade_enriched.get("use_count", 1)

        # Ensure use_count is an integer
        try:
            use_count = int(use_count) if use_count is not None else 1
        except (ValueError, TypeError):
            use_count = 1

        # Skip invalid use counts (shouldn't happen, but safety check)
        if use_count < 1:
            continue

        usage_data.append(
            {
                "use_count": use_count,
                "author": author,
            }
        )

    if not usage_data:
        return []

    # Convert to DataFrame for efficient aggregation
    df = pd.DataFrame(usage_data)

    # Group by use_count and calculate metrics
    grouped = df.groupby("use_count").agg({"author": ["count", "nunique"]}).reset_index()

    # Flatten column names
    grouped.columns = ["use_count", "shaves", "unique_users"]

    # Sort by use_count ascending (1, 2, 3, 4, 5, etc.)
    grouped = grouped.sort_values("use_count", ascending=True)

    # Add rank field (1-based rank)
    grouped["rank"] = range(1, len(grouped) + 1)

    # Convert to list of dictionaries
    result = []
    for row in grouped.to_dict(orient="records"):
        result.append(
            {
                "rank": int(row["rank"]),
                "use_count": int(row["use_count"]),
                "shaves": int(row["shaves"]),
                "unique_users": int(row["unique_users"]),
            }
        )

    return result
