#!/usr/bin/env python3
"""Soap brand+scent diversity aggregator for the SOTD pipeline."""

from typing import Any, Dict, List, cast

import pandas as pd

from ...utils.field_validation import get_field_value, has_required_fields
from ...utils.soap_scent_filter import counts_as_distinct_soap_scent
from ..base_aggregator import BaseAggregator
from .user_diversity_mixin import UserDiversityMixin


class SoapBrandScentDiversityAggregator(BaseAggregator, UserDiversityMixin):
    """Aggregator for soap brand scent diversity data from enriched records."""

    # Override tie_columns for tier-based ranking
    tie_columns = ["unique_combinations", "shaves"]

    @property
    def IDENTIFIER_FIELDS(self) -> List[str]:
        """Fields used for matching/grouping."""
        return ["user"]

    @property
    def METRIC_FIELDS(self) -> List[str]:
        """Calculated/metric fields."""
        return [
            "unique_combinations",
            "shaves",
            "avg_shaves_per_combination",
            "hhi",
            "effective_soaps",
        ]

    @property
    def RANKING_FIELDS(self) -> List[str]:
        """Fields used for sorting/ranking."""
        return ["unique_combinations", "shaves"]

    def _extract_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract soap brand scent diversity data from records for aggregation.

        Args:
            records: List of enriched comment records

        Returns:
            List of dictionaries with extracted soap brand scent diversity data fields
        """
        diversity_data = []
        for record in records:
            soap = record.get("soap") or {}
            matched = soap.get("matched", {})

            # Skip if no matched soap data or missing required fields
            # Note: Empty strings are valid values, only None is invalid
            if not matched or not has_required_fields(matched, "brand", "scent"):
                continue

            brand = get_field_value(matched, "brand")
            scent = get_field_value(matched, "scent")
            counts_as_distinct = counts_as_distinct_soap_scent(soap)
            author = get_field_value(record, "author")

            if brand and author:  # scent can be empty string, which is valid
                diversity_data.append(
                    {
                        "brand": brand,
                        "scent": scent,
                        "author": author,  # Keep username clean, add "u/" in report phase
                        "counts_as_distinct": counts_as_distinct,
                    }
                )

        return diversity_data

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        """Create composite name from brand and scent.

        Args:
            df: DataFrame with extracted soap brand scent diversity data

        Returns:
            Series with composite names in "Brand - Scent" format
        """
        # Handle None values by converting to empty strings and concatenate properly
        brand = df["brand"].fillna("")
        scent = df["scent"].fillna("")

        # Use pandas string concatenation to avoid Series ambiguity
        # Always concatenate with dash - empty scents will just show as "Brand - "
        return brand.astype(str) + " - " + scent.astype(str)

    def _group_and_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group data and calculate aggregation metrics.

        Args:
            df: DataFrame with extracted data and composite name

        Returns:
            DataFrame with grouped and aggregated data
        """
        # Filter to distinct catalog scents (excludes mashups and non-countable)
        if "counts_as_distinct" not in df.columns:
            df["counts_as_distinct"] = True
        distinct_scent_df = df[df["counts_as_distinct"]].copy()

        # Group by author to count unique brand+scent combinations per user
        # Use all data (including mashups) for brand counting
        grouped = (
            df.groupby("author")
            .agg(
                {
                    "brand": "nunique",  # Count unique brands (for reference)
                }
            )
            .reset_index()
        )

        # Rename columns for consistency
        grouped.columns = ["author", "unique_brands"]

        # Count unique brand+scent combinations per user
        # Use only distinct catalog scents for unique combination counting
        distinct_scent_df["brand_scent_key"] = (
            distinct_scent_df["brand"].astype(str) + " - " + distinct_scent_df["scent"].astype(str)
        )
        brand_scent_counts = (
            distinct_scent_df.groupby("author")["brand_scent_key"].nunique().reset_index()
        )
        brand_scent_counts.columns = ["author", "unique_combinations"]

        # Count total shaves per user (all matched soaps, including mashups)
        shave_counts = df.groupby("author").size().reset_index(name="shaves")  # type: ignore

        # Merge all the data
        grouped = grouped.merge(brand_scent_counts, on="author")
        grouped = grouped.merge(shave_counts, on="author")

        # Calculate average shaves per combination
        grouped["avg_shaves_per_combination"] = (
            grouped["shaves"] / grouped["unique_combinations"]
        ).round(2)

        # Calculate HHI (Herfindahl-Hirschman Index) for each user
        # HHI measures concentration: HHI = Σ p_i² where p_i = count_i / total_shaves
        # For each user, count occurrences of each brand-scent combination
        # Use only distinct catalog scents for HHI calculation
        soap_counts = (
            distinct_scent_df.groupby(["author", "brand_scent_key"])
            .size()
            .reset_index(name="count")  # type: ignore
        )

        # Merge with total shaves to calculate shares
        soap_counts = soap_counts.merge(grouped[["author", "shaves"]], on="author")

        # Calculate shares: p_i = count_i / total_shaves
        soap_counts["share"] = soap_counts["count"] / soap_counts["shaves"]

        # Calculate squared shares: p_i²
        soap_counts["squared_share"] = soap_counts["share"] ** 2

        # Calculate HHI per user: HHI = Σ p_i²
        hhi_by_user = cast(
            pd.DataFrame, soap_counts.groupby("author", as_index=False)["squared_share"].sum()
        )
        hhi_by_user.columns = ["author", "hhi"]
        hhi_by_user["hhi"] = hhi_by_user["hhi"].round(4)

        # Calculate effective_soaps = 1 / HHI
        hhi_by_user["effective_soaps"] = (1.0 / hhi_by_user["hhi"]).round(2)
        # Handle edge case where HHI is 0 (shouldn't happen, but be safe)
        hhi_by_user.loc[hhi_by_user["hhi"] == 0, "effective_soaps"] = 0.0

        # Merge HHI and effective_soaps back into grouped
        grouped = grouped.merge(
            hhi_by_user[["author", "hhi", "effective_soaps"]], on="author", how="left"
        )

        # Fill any missing values (shouldn't happen, but be safe)
        grouped["hhi"] = grouped["hhi"].fillna(0.0)
        grouped["effective_soaps"] = grouped["effective_soaps"].fillna(0.0)

        # Add unique_users field (always 1 for user aggregators)
        grouped["unique_users"] = 1

        # Use mixin to prepare for base class ranking
        grouped = self._prepare_for_base_ranking(grouped)

        return grouped

    def _get_group_columns(self, df: pd.DataFrame) -> List[str]:
        """Get columns to use for grouping."""
        return ["name"]

    def _call_base_aggregate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Call the base class aggregate method."""
        return super().aggregate(records)

    def aggregate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate data using tier-based ranking with custom output format."""
        return self.aggregate_with_tier_ranking(
            records,
            {
                "unique_combinations": "unique_combinations",
                "shaves": "shaves",
                "avg_shaves_per_combination": "avg_shaves_per_combination",
                "hhi": "hhi",
                "effective_soaps": "effective_soaps",
                "unique_users": "unique_users",
            },
        )


# Legacy function interface for backward compatibility
def aggregate_soap_brand_scent_diversity(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate soap brand scent diversity data from enriched records.

    Returns a list of soap brand scent diversity aggregations sorted by shaves desc,
    unique_users desc. Each item includes position field for delta calculations.

    Args:
        records: List of enriched comment records

    Returns:
        List of soap brand scent diversity aggregations with position, name, shaves, and
        unique_users fields
    """
    aggregator = SoapBrandScentDiversityAggregator()
    return aggregator.aggregate(records)
