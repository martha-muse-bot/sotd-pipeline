#!/usr/bin/env python3
"""Exclusive-use soap aggregator: one point per soap when a shaver is the only user."""

from typing import Any, Dict, List

import pandas as pd

from ...utils.field_validation import get_field_value, has_required_fields
from ...utils.soap_scent_filter import counts_as_distinct_soap_scent
from ..base_aggregator import BaseAggregator
from .user_diversity_mixin import UserDiversityMixin


class UserSingleUseSoapsAggregator(BaseAggregator, UserDiversityMixin):
    """Count soaps where exactly one shaver used them in the period (1 point per soap)."""

    tie_columns = ["single_use_soaps", "shaves"]

    @property
    def IDENTIFIER_FIELDS(self) -> List[str]:
        return ["user"]

    @property
    def METRIC_FIELDS(self) -> List[str]:
        return ["single_use_soaps", "shaves", "unique_users"]

    @property
    def RANKING_FIELDS(self) -> List[str]:
        return ["single_use_soaps", "shaves"]

    def _extract_data(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        soap_data = []
        for record in records:
            soap = record.get("soap") or {}
            matched = soap.get("matched", {})

            if not counts_as_distinct_soap_scent(soap):
                continue

            if not matched or not has_required_fields(matched, "brand", "scent"):
                continue

            brand = get_field_value(matched, "brand")
            scent = get_field_value(matched, "scent")
            author = get_field_value(record, "author")

            if not brand or not author:
                continue

            original_brand = brand.strip()
            original_scent = scent.strip()

            soap_data.append(
                {
                    "brand": original_brand,
                    "scent": original_scent,
                    "author": author,
                    "brand_normalized": original_brand.lower(),
                    "scent_normalized": original_scent.lower(),
                }
            )

        return soap_data

    def _create_composite_name(self, df: pd.DataFrame) -> pd.Series:
        brand = df["brand"].fillna("")
        scent = df["scent"].fillna("")
        return brand.astype(str) + " - " + scent.astype(str)

    def _soap_group_columns(self) -> List[str]:
        return ["brand_normalized", "scent_normalized"]

    def _get_group_columns(self, df: pd.DataFrame) -> List[str]:
        return ["name"]

    def _group_and_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        """Award one point per soap with a single unique user; rank users by that count."""
        group_columns = self._soap_group_columns()

        soap_users = (
            df.groupby(group_columns)["author"]
            .agg(unique_users="nunique", sole_user="first")
            .reset_index()
        )
        exclusive_soaps = soap_users[soap_users["unique_users"] == 1]

        if exclusive_soaps.empty:
            return pd.DataFrame(columns=["name", "single_use_soaps", "shaves", "unique_users"])

        points = (
            exclusive_soaps.groupby("sole_user")
            .size()
            .to_frame("single_use_soaps")
            .reset_index()
            .rename(columns={"sole_user": "name"})
        )

        shave_counts = df.groupby("author").size().to_frame("shaves").reset_index()
        shave_counts = shave_counts.rename(columns={"author": "name"})

        grouped = points.merge(shave_counts, on="name", how="left")
        grouped["shaves"] = grouped["shaves"].fillna(0).astype(int)
        grouped["unique_users"] = 1

        return grouped

    def _call_base_aggregate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return super().aggregate(records)

    def aggregate(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.aggregate_with_tier_ranking(
            records,
            {
                "single_use_soaps": "single_use_soaps",
                "shaves": "shaves",
                "unique_users": "unique_users",
            },
        )


def aggregate_user_single_use_soaps(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate exclusive-use soap points per shaver."""
    return UserSingleUseSoapsAggregator().aggregate(records)
