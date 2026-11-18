#!/usr/bin/env python3
"""Soap sample user aggregator for the SOTD pipeline."""

from typing import Any, Dict, List

import pandas as pd

from ...utils.soap_scent_filter import is_mashup_soap
from ..base_aggregator import BaseAggregator


class SoapSampleUserAggregator(BaseAggregator):
    """Aggregator for soap sample data grouped by user from enriched records."""

    @property
    def IDENTIFIER_FIELDS(self) -> List[str]:
        """Fields used for matching/grouping."""
        return ["user"]

    @property
    def METRIC_FIELDS(self) -> List[str]:
        """Calculated/metric fields."""
        return ["shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> List[str]:
        """Fields used for sorting/ranking."""
        return ["shaves", "unique_users"]

    def _extract_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract soap sample data from records for aggregation.

        Args:
            records: List of enriched comment records

        Returns:
            List of dictionaries with extracted soap sample data fields
        """
        sample_data = []
        for record in records:
            soap = record.get("soap", {})
            if is_mashup_soap(soap):
                continue

            enriched = soap.get("enriched", {})
            matched = soap.get("matched", {})

            # Skip if no sample enrichment data
            if not enriched or "sample_type" not in enriched:
                continue

            # Extract sample information
            sample_type = enriched.get("sample_type") or ""
            sample_type = sample_type.strip() if sample_type else ""
            sample_number = enriched.get("sample_number")
            total_samples = enriched.get("total_samples")

            # Extract soap identification
            brand = matched.get("brand") or "" if matched else ""
            brand = brand.strip() if brand else ""
            scent = matched.get("scent") or "" if matched else ""
            scent = scent.strip() if scent else ""
            author = record.get("author") or ""
            author = author.strip() if author else ""

            if sample_type and author:
                sample_data.append(
                    {
                        "sample_type": sample_type,
                        "sample_number": sample_number,
                        "total_samples": total_samples,
                        "brand": brand,
                        "scent": scent,
                        "author": author,
                    }
                )

        return sample_data

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        """Create composite name from sample type, brand, and scent.

        Args:
            df: DataFrame with extracted soap sample data

        Returns:
            Series with composite names in "Sample Type - Brand - Scent" format
        """
        # Handle None values by converting to empty strings
        sample_type = df["sample_type"].fillna("")
        brand = df["brand"].fillna("")
        scent = df["scent"].fillna("")

        # Create composite name using pandas operations
        import numpy as np

        # Create the composite name based on whether brand and scent exist
        composite_name = np.where(
            (brand != "") & (scent != ""),
            sample_type + " - " + brand + " - " + scent,
            np.where(brand != "", sample_type + " - " + brand, sample_type),
        )

        return pd.Series(composite_name)

    def _group_and_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group data and calculate aggregation metrics.

        Args:
            df: DataFrame with extracted data and composite name

        Returns:
            DataFrame with grouped and aggregated data
        """
        # Group by author to count sample shaves per user
        group_columns = ["author"]

        # Group by columns and calculate metrics
        grouped = df.groupby(group_columns).agg({"sample_type": "count"}).reset_index()

        # Rename columns for consistency
        grouped.columns = ["author", "shaves"]

        # Add unique_users field (always 1 for user aggregators)
        grouped["unique_users"] = 1

        return grouped

    def _sort_and_rank(self, grouped: pd.DataFrame) -> List[Dict[str, Any]]:
        """Sort grouped data and add position rankings.

        Args:
            grouped: DataFrame with grouped and aggregated data

        Returns:
            List of dictionaries with position, user, shaves, and unique_users fields
        """
        # Sort by shaves desc, unique_users desc
        grouped = grouped.sort_values(["shaves", "unique_users"], ascending=[False, False])

        # Add position field (1-based rank)
        grouped = grouped.reset_index(drop=True).assign(position=lambda df: range(1, len(df) + 1))  # type: ignore

        # Convert to list of dictionaries
        result = []
        for row in grouped.to_dict(orient="records"):  # type: ignore[reportCallIssue]  # pandas-stubs lack the "records" overload; runtime yields plain dicts
            item = {
                "rank": int(row["position"]),
                "user": row["author"],  # Keep clean, add "u/" in report
                "shaves": int(row["shaves"]),
                "unique_users": int(row["unique_users"]),
            }

            result.append(item)

        return result

    def _get_group_columns(self, df: pd.DataFrame) -> List[str]:
        """Get columns to use for grouping.

        Args:
            df: DataFrame with extracted data

        Returns:
            List of column names for grouping
        """
        # Group by author for user-focused analysis
        return ["author"]


# Legacy function interface for backward compatibility
def aggregate_soap_sample_users(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate soap sample data by user from enriched records.

    Returns a list of soap sample user aggregations sorted by shaves desc,
    unique_users desc. Each item includes position field for delta calculations.

    Args:
        records: List of enriched comment records

    Returns:
        List of soap sample user aggregations with position, user, shaves,
        and unique_users fields
    """
    aggregator = SoapSampleUserAggregator()
    return aggregator.aggregate(records)
