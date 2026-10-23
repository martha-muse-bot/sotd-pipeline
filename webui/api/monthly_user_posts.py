#!/usr/bin/env python3
"""Monthly User Posts API endpoints for the SOTD Pipeline WebUI."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .utils.data_dir import get_enriched_dir, get_user_analysis_dir  # noqa: E402

# Add the project root to the path to import from sotd
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sotd.aggregate.aggregators.user_analysis import aggregate_user_analysis  # noqa: E402
from sotd.aggregate.aggregators.users.user_aggregator import (  # noqa: E402
    aggregate_users,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/monthly-user-posts", tags=["monthly-user-posts"])


class UserPostingAnalysis(BaseModel):
    """User posting analysis result."""

    user: str
    posted_days: int
    missed_days: int
    posted_dates: List[str]
    comment_ids: List[str]
    comments_by_date: Dict[str, List[str]]
    comment_urls: Optional[Dict[str, str]] = None  # Optional for backward compatibility
    # Product usage data
    razors: List[Dict[str, Any]]
    blades: List[Dict[str, Any]]
    brushes: List[Dict[str, Any]]
    soaps: List[Dict[str, Any]]


class MonthData(BaseModel):
    """Month data availability."""

    month: str
    has_data: bool
    user_count: int


@router.get("/months", response_model=List[MonthData])
async def get_available_months() -> List[MonthData]:
    """Get list of available months with data."""
    try:
        # Primary source: pre-computed user_analysis aggregates (present in the
        # public bundle, which has no enriched/).
        user_analysis_dir = get_user_analysis_dir()
        months = []
        if user_analysis_dir.exists():
            for file_path in user_analysis_dir.glob("*.json"):
                month = file_path.stem
                if month and len(month) == 7 and month[4] == "-":  # YYYY-MM format
                    try:
                        with file_path.open("r", encoding="utf-8") as f:
                            data = json.load(f)
                        months.append(
                            MonthData(
                                month=month,
                                has_data=True,
                                user_count=len(data.get("users", {})),
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Error reading {file_path}: {e}")
                        months.append(MonthData(month=month, has_data=False, user_count=0))

        # Fallback: scan enriched/ only when user_analysis yielded nothing.
        if not months:
            enriched_dir = get_enriched_dir()
            if enriched_dir.exists():
                for file_path in enriched_dir.glob("*.json"):
                    month = file_path.stem
                    if month and len(month) == 7 and month[4] == "-":  # YYYY-MM format
                        # Check if file has data
                        try:
                            with file_path.open("r", encoding="utf-8") as f:
                                data = json.load(f)
                                user_count = len(
                                    set(
                                        record.get("author")
                                        for record in data.get("data", [])
                                        if record.get("author")
                                    )
                                )

                            months.append(
                                MonthData(month=month, has_data=True, user_count=user_count)
                            )
                        except Exception as e:
                            logger.warning(f"Error reading {file_path}: {e}")
                            months.append(MonthData(month=month, has_data=False, user_count=0))

        # Sort by month (newest first)
        months.sort(key=lambda x: x.month, reverse=True)
        return months

    except Exception as e:
        logger.error(f"Error getting available months: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/users/{month}", response_model=List[Dict[str, Any]])
async def get_users_for_month(
    month: str, search: Optional[str] = Query(None, description="Search filter for usernames")
) -> List[Dict[str, Any]]:
    """Get list of users who posted in a specific month."""
    try:
        # Try to load from pre-computed user analysis file
        user_analysis_file = get_user_analysis_dir() / f"{month}.json"

        if user_analysis_file.exists():
            try:
                with user_analysis_file.open("r", encoding="utf-8") as f:
                    user_analysis_data = json.load(f)

                # Extract users from the analysis data
                users_dict = user_analysis_data.get("users", {})
                users = [
                    {"username": username, "post_count": analysis.get("posted_days", 0)}
                    for username, analysis in users_dict.items()
                ]

                # Apply search filter if provided
                if search:
                    search_lower = search.lower()
                    users = [user for user in users if search_lower in user["username"].lower()]

                # Sort by post_count descending
                users.sort(key=lambda x: x["post_count"], reverse=True)
                return users[:50]

            except Exception as e:
                logger.warning(
                    f"Error loading user analysis file for {month}: {e}, falling back to enriched data"
                )

        # Fallback: Load enriched data and process on-demand
        try:
            enriched_file = get_enriched_dir() / f"{month}.json"

            if not enriched_file.exists():
                return []

            with enriched_file.open("r", encoding="utf-8") as f:
                enriched_data = json.load(f)

            # Use existing user aggregation logic
            user_aggregations = aggregate_users(enriched_data["data"])

            # Convert to our expected format
            users = [
                {"username": user["user"], "post_count": user["shaves"]}
                for user in user_aggregations
            ]

            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                users = [user for user in users if search_lower in user["username"].lower()]

            # Return more users for better coverage (limit to top 50 instead of 20)
            return users[:50]

        except Exception as e:
            logger.error(f"Error loading enriched data for {month}: {e}")
            return []

    except Exception as e:
        logger.error(f"Error getting users for month {month}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analysis/{month}/{username}", response_model=UserPostingAnalysis)
async def get_user_posting_analysis(month: str, username: str) -> UserPostingAnalysis:
    """Get posting analysis for a specific user in a specific month."""
    try:
        # Try to load from pre-computed user analysis file
        user_analysis_file = get_user_analysis_dir() / f"{month}.json"

        if user_analysis_file.exists():
            try:
                with user_analysis_file.open("r", encoding="utf-8") as f:
                    user_analysis_data = json.load(f)

                # Find the specific user
                users_dict = user_analysis_data.get("users", {})
                if username not in users_dict:
                    raise HTTPException(
                        status_code=404, detail=f"User {username} not found in month {month}"
                    )

                user_analysis = users_dict[username]

                # Convert to expected format (already in correct structure)
                return UserPostingAnalysis(**user_analysis)

            except HTTPException:
                raise
            except Exception as e:
                logger.warning(
                    f"Error loading user analysis file for {month}: {e}, falling back to enriched data"
                )

        # Fallback: Load enriched data and process on-demand
        try:
            enriched_file = get_enriched_dir() / f"{month}.json"

            if not enriched_file.exists():
                raise HTTPException(status_code=404, detail=f"No data available for {month}")

            with enriched_file.open("r", encoding="utf-8") as f:
                enriched_data = json.load(f)

            # Generate user analysis on-demand
            user_analyses = aggregate_user_analysis(enriched_data["data"])

            if username not in user_analyses:
                raise HTTPException(
                    status_code=404, detail=f"User {username} not found in month {month}"
                )

            user_analysis = user_analyses[username]

            # Convert to expected format
            return UserPostingAnalysis(**user_analysis)

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading enriched data for {month}: {e}")
            raise HTTPException(status_code=500, detail="Error loading enriched data")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing user {username} for month {month}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "monthly-user-posts"}
