from typing import Any, Dict, List

import pandas as pd

from ..base_aggregator import BaseAggregator


class RazorFormatAggregator(BaseAggregator):
    """Aggregator for razor format data from enriched records."""

    @property
    def IDENTIFIER_FIELDS(self) -> List[str]:
        """Fields used for matching/grouping."""
        return ["format"]

    @property
    def METRIC_FIELDS(self) -> List[str]:
        """Calculated/metric fields."""
        return ["shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> List[str]:
        """Fields used for sorting/ranking."""
        return ["shaves", "unique_users"]

    def _extract_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract razor format data from records for aggregation.

        Args:
            records: List of enriched comment records

        Returns:
            List of dictionaries with extracted format and author fields
        """
        format_data = []
        for record in records:
            razor = record.get("razor", {})
            razor_matched = razor.get("matched") if razor else None

            # Skip records with no razor match at all
            if razor_matched is None:
                continue

            # Use enriched format if available, otherwise fall back to matched format
            # This supports backward compatibility with records that haven't been enriched yet
            razor_enriched = razor.get("enriched", {})
            razor_format = razor_enriched.get("format") or razor_matched.get("format", "").strip()

            # Skip if no format determined
            if not razor_format:
                continue

            author = record.get("author", "").strip()

            if razor_format and author:
                format_data.append({"format": razor_format, "author": author})

        return format_data

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        """Create composite name from extracted data.

        For formats, the format itself is the identifier.

        Args:
            df: DataFrame with extracted data

        Returns:
            Series with format names
        """
        return df["format"]  # type: ignore[return-value]


def aggregate_razor_formats(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate razor format data from enriched records.

    This implementation uses the format that was already determined during the enrich phase,
    rather than re-determining it. Format determination logic has been moved to the enrich
    phase (RazorFormatEnricher) to ensure consistency and avoid duplication.

    Returns a list of razor format aggregations sorted by shaves desc, unique_users desc.
    Each item includes rank field for delta calculations.

    Args:
        records: List of enriched comment records

    Returns:
        List of razor format aggregations with rank, format, shaves, unique_users,
        avg_shaves_per_user, and median_shaves_per_user fields
    """
    if not records:
        return []

    # Extract razor format data from records
    format_data = []
    for record in records:
        razor = record.get("razor", {})
        razor_matched = razor.get("matched") if razor else None

        # Skip records with no razor match at all
        if razor_matched is None:
            continue

        # Use enriched format if available, otherwise fall back to matched format
        # This supports backward compatibility with records that haven't been enriched yet
        razor_enriched = razor.get("enriched", {})
        razor_format = razor_enriched.get("format") or razor_matched.get("format", "").strip()

        # Skip if no format determined
        if not razor_format:
            continue

        author = record.get("author", "").strip()

        if razor_format and author:
            format_data.append({"format": razor_format, "author": author})

    if not format_data:
        return []

    # Convert to DataFrame for efficient aggregation
    df = pd.DataFrame(format_data)

    # Group by format and calculate metrics
    grouped = df.groupby("format").agg({"author": ["count", "nunique"]}).reset_index()

    # Flatten column names
    grouped.columns = ["format", "shaves", "unique_users"]

    # Calculate average shaves per user
    grouped["avg_shaves_per_user"] = (
        grouped["shaves"] / grouped["unique_users"].replace(0, 1)
    ).round(1)
    # Handle division by zero: if unique_users is 0, set avg to 0.0
    grouped.loc[grouped["unique_users"] == 0, "avg_shaves_per_user"] = 0.0

    # Calculate median shaves per user
    # First, group by format and author to get shaves per user per format
    user_shaves_per_format = df.groupby(["format", "author"]).size().reset_index()
    user_shaves_per_format.columns = ["format", "author", "user_shaves"]

    # Calculate median shaves per user for each format
    median_shaves = user_shaves_per_format.groupby("format")["user_shaves"].median().reset_index()
    median_shaves.columns = ["format", "median_shaves_per_user"]
    median_shaves["median_shaves_per_user"] = median_shaves["median_shaves_per_user"].round(1)

    # Merge median data back into grouped dataframe
    grouped = grouped.merge(median_shaves, on="format", how="left")
    # Fill NaN values (shouldn't happen, but handle edge cases)
    grouped["median_shaves_per_user"] = grouped["median_shaves_per_user"].fillna(0.0)

    # Sort by shaves desc, unique_users desc
    grouped = grouped.sort_values(["shaves", "unique_users"], ascending=[False, False])

    # Add rank field (1-based rank)
    grouped["rank"] = range(1, len(grouped) + 1)

    # Convert to list of dictionaries
    result = []
    for row in grouped.to_dict(orient="records"):
        result.append(
            {
                "rank": int(row["rank"]),
                "format": row["format"],
                "shaves": int(row["shaves"]),
                "unique_users": int(row["unique_users"]),
                "avg_shaves_per_user": float(row["avg_shaves_per_user"]),
                "median_shaves_per_user": float(row["median_shaves_per_user"]),
            }
        )

    return result
