#!/usr/bin/env python3
"""Razor format user aggregator for the SOTD pipeline."""

from typing import Any, Dict, List

import pandas as pd

from ..base_aggregator import BaseAggregator


class RazorFormatUserAggregator(BaseAggregator):
    """Aggregator for tracking top users within each razor format category."""

    @property
    def IDENTIFIER_FIELDS(self) -> List[str]:
        """Fields used for matching/grouping."""
        return ["format", "user"]

    @property
    def METRIC_FIELDS(self) -> List[str]:
        """Calculated/metric fields."""
        return ["shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> List[str]:
        """Fields used for sorting/ranking."""
        return ["shaves", "unique_users"]

    def _extract_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Extract razor format data from enriched records."""
        extracted = []

        for record in records:
            razor_data = record.get("razor", {})
            matched = razor_data.get("matched", {})

            # Skip records without matched razor data
            if not matched:
                continue

            # Extract format and author
            format_type = matched.get("format")
            author = record.get("author")

            # Skip if no format or author
            if not format_type or not author:
                continue

            extracted.append(
                {
                    "author": author,
                    "format": format_type,
                }
            )

        return extracted

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        """Create composite names for grouping (not used in this aggregator)."""
        # This aggregator doesn't use composite names in the traditional sense
        # We group by format first, then by user
        result = df["format"]
        # Ensure we return a Series
        if isinstance(result, pd.Series):
            return result
        else:
            return pd.Series(result, index=df.index)

    def _group_and_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Group data by format first, then by user within each format."""
        # Group by format and author to count shaves per user per format
        grouped = df.groupby(["format", "author"]).size().reset_index(name="shaves")  # type: ignore

        # Add unique_users field (always 1 for user aggregators)
        grouped["unique_users"] = 1

        return grouped

    def _sort_and_rank(self, grouped: pd.DataFrame) -> List[Dict[str, Any]]:
        """Sort grouped data by format, then by shaves, and add position rankings."""
        # Sort by format asc, then shaves desc, then unique_users desc
        grouped = grouped.sort_values(
            ["format", "shaves", "unique_users"], ascending=[True, False, False]
        )

        # Add position field within each format group
        result = []
        current_format = None
        current_position = 1

        for row in grouped.to_dict(orient="records"):  # type: ignore[reportCallIssue]  # pandas-stubs lack the "records" overload; runtime yields plain dicts
            format_type = str(row["format"])

            # Reset position counter for new format
            if format_type != current_format:
                current_format = format_type
                current_position = 1

            item = {
                "rank": current_position,
                "format": format_type,
                "user": row["author"],  # Keep clean, add "u/" in report
                "shaves": int(row["shaves"]),
                "unique_users": int(row["unique_users"]),
            }
            result.append(item)

            current_position += 1

        return result

    def _get_group_columns(self, df: pd.DataFrame) -> List[str]:
        """Get columns for grouping."""
        return ["format", "author"]


def aggregate_razor_format_users(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate razor format usage by user from enriched records."""
    aggregator = RazorFormatUserAggregator()
    return aggregator.aggregate(records)
