from typing import Any, Dict, List, cast

import pandas as pd


def aggregate_highest_use_count_per_blade(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate individual physical blade use counts from enriched records.

    Returns a list of individual physical blade use counts sorted by uses desc.
    Each item includes rank field for delta calculations.
    Tracks each physical blade separately - multiple users can have the same blade type
    but different physical blades with different use counts.

    Args:
        records: List of enriched comment records

    Returns:
        List of individual physical blade use counts with rank, user,
        blade, format, and uses fields
    """
    if not records:
        return []

    # Extract individual physical blade use count data from records
    use_count_data = []
    for record in records:
        blade = record.get("blade", {})
        blade_matched = blade.get("matched", {})
        blade_enriched = blade.get("enriched", {})
        # Also check for blade_enriched at top level (for test compatibility)
        if not blade_enriched:
            blade_enriched = record.get("blade_enriched", {})
        author = record.get("author", "").strip()

        # Skip if no matched blade data or no author
        if not blade_matched or not author:
            continue

        blade_brand = blade_matched.get("brand", "")
        blade_model = blade_matched.get("model", "")
        blade_format = blade_matched.get("format", "")

        # Handle None values and strip strings
        blade_brand = blade_brand.strip() if blade_brand else ""
        blade_model = blade_model.strip() if blade_model else ""
        blade_format = blade_format.strip() if blade_format else ""

        # Skip if missing essential blade data
        if not (blade_brand and blade_model):
            continue

        blade_name = f"{blade_brand} {blade_model}"

        # Get use_count from enriched data, default to 1 if not available
        use_count = blade_enriched.get("use_count", 1)

        # Ensure use_count is an integer
        try:
            use_count = int(use_count) if use_count is not None else 1
        except (ValueError, TypeError):
            use_count = 1

        use_count_data.append(
            {
                "blade_name": blade_name,
                "blade_format": blade_format,
                "author": author,
                "uses": use_count,
            }
        )

    if not use_count_data:
        return []

    # Convert to DataFrame for efficient aggregation
    df = pd.DataFrame(use_count_data)

    # Group by blade_name, blade_format, and author to get per-user usage
    # Each physical blade is tracked separately by user
    user_max_usage = cast(
        pd.DataFrame,
        df.groupby(["blade_name", "blade_format", "author"], as_index=False)["uses"].max(),
    )

    # Convert to list of dictionaries - each physical blade is a separate entry
    blade_max_usage = user_max_usage.copy()

    # Sort by uses desc
    blade_max_usage = blade_max_usage.sort_values("uses", ascending=False)

    # Add competition ranking based on uses
    # Items with same uses get tied ranks
    blade_max_usage = blade_max_usage.reset_index(drop=True)

    # Create a composite key for ranking that preserves the order
    # Use sequential ranks, then group by uses to get same rank for ties
    blade_max_usage["temp_rank"] = range(1, len(blade_max_usage) + 1)
    blade_max_usage["rank"] = blade_max_usage.groupby("uses", sort=False)["temp_rank"].transform(
        "min"
    )
    blade_max_usage = blade_max_usage.drop("temp_rank", axis=1)

    # Sort by ranking first, then by blade_name for consistent ordering of tied entries
    blade_max_usage = blade_max_usage.sort_values(["rank", "blade_name"], ascending=[True, True])
    blade_max_usage = blade_max_usage.reset_index(drop=True)

    # OPTIMIZED: Convert to list of dictionaries using pandas operations
    # Rename columns and convert types using pandas operations
    blade_max_usage = blade_max_usage.rename(
        columns={"author": "user", "blade_name": "blade", "blade_format": "format"}
    )
    blade_max_usage["rank"] = blade_max_usage["rank"].astype(int)
    blade_max_usage["uses"] = blade_max_usage["uses"].astype(int)

    # Reorder columns to put rank first (consistent with other aggregators)
    cols = ["rank"] + [col for col in blade_max_usage.columns if col != "rank"]
    blade_max_usage = blade_max_usage[cols]

    # Convert to list of dictionaries - no manual processing needed
    # Type conversion to ensure str keys
    # Type ignore for to_dict - pandas supports "records" parameter
    result = [{str(k): v for k, v in item.items()} for item in blade_max_usage.to_dict("records")]  # type: ignore

    return result
