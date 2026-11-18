#!/usr/bin/env python3
"""Soap mashup user aggregator for the SOTD pipeline."""

from typing import Any, Dict, List

import pandas as pd

from ..base_aggregator import BaseAggregator


class SoapMashupUserAggregator(BaseAggregator):
    """Aggregator for soap mashup data grouped by user from enriched records.

    Keys off soap.enriched.is_mashup only. No brand/scent (mashup content
    often unknown or multi-brand).
    """

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
        """Extract soap mashup data from records for aggregation."""
        mashup_data = []
        for record in records:
            soap = record.get("soap", {})
            enriched = soap.get("enriched", {})

            if not enriched or enriched.get("is_mashup") is not True:
                continue

            author = record.get("author") or ""
            author = author.strip() if isinstance(author, str) else ""

            if author:
                mashup_data.append({"author": author})

        return mashup_data

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        """Composite name is author (user) for user aggregator."""
        author = df["author"].fillna("")
        return pd.Series(author.tolist(), index=df.index)

    def _group_and_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group by author and count mashup shaves per user."""
        grouped = df.groupby("author").size().to_frame("shaves").reset_index()
        grouped["unique_users"] = 1
        return grouped

    def _sort_and_rank(self, grouped: pd.DataFrame) -> List[Dict[str, Any]]:
        """Sort by shaves desc and add rank."""
        grouped = grouped.sort_values(["shaves", "unique_users"], ascending=[False, False])
        grouped = grouped.reset_index(drop=True).assign(position=lambda d: range(1, len(d) + 1))
        result = []
        for row in grouped.to_dict(orient="records"):
            result.append(
                {
                    "rank": int(row["position"]),
                    "user": row["author"],
                    "shaves": int(row["shaves"]),
                    "unique_users": int(row["unique_users"]),
                }
            )
        return result

    def _get_group_columns(self, df: pd.DataFrame) -> List[str]:
        """Group by author."""
        return ["author"]


def aggregate_soap_mashup_users(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate soap mashup data by user from enriched records.

    Returns a list of soap mashup user aggregations sorted by shaves desc.
    Each item includes rank field for delta calculations.

    Args:
        records: List of enriched comment records

    Returns:
        List of soap mashup user aggregations with rank, user, shaves,
        and unique_users fields
    """
    aggregator = SoapMashupUserAggregator()
    return aggregator.aggregate(records)
