#!/usr/bin/env python3
"""Product Usage API endpoints for the SOTD Pipeline WebUI."""

import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .utils.data_dir import get_aggregated_dir, get_enriched_dir  # noqa: E402

# Add the project root to the path to import from sotd
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sotd.aggregate.aggregators.product_usage import aggregate_product_usage  # noqa: E402

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/product-usage", tags=["product-usage"])


class Product(BaseModel):
    """Product information."""

    key: str
    brand: str
    model: str
    usage_count: int
    unique_users: int


class UserProductUsage(BaseModel):
    """User product usage information."""

    username: str
    usage_count: int
    usage_dates: List[str]
    comment_ids: List[str]


class ProductUsageAnalysis(BaseModel):
    """Product usage analysis result."""

    product: Dict[str, str]
    total_usage: int
    unique_users: int
    users: List[UserProductUsage]
    usage_by_date: Dict[str, List[str]]
    comments_by_date: Dict[str, List[str]]
    comment_urls: Optional[Dict[str, str]] = None  # Optional for backward compatibility


class MonthlyProductSummary(BaseModel):
    """Monthly product usage summary."""

    month: str
    shaves: int
    unique_users: int
    rank: Optional[int]  # None if product not found in that month
    has_data: bool


class ProductYearlySummary(BaseModel):
    """Yearly product usage summary."""

    product: Dict[str, str]
    months: List[MonthlyProductSummary]


def _generate_product_key(product_type: str, matched: Dict[str, Any]) -> str:
    """Generate product key based on product type."""
    if product_type == "razor":
        brand = matched.get("brand", "")
        model = matched.get("model", "")
        return f"{brand}|{model}"
    elif product_type == "blade":
        brand = matched.get("brand", "")
        model = matched.get("model", "")
        return f"{brand}|{model}"
    elif product_type == "brush":
        brand = matched.get("brand", "") or ""
        model = matched.get("model", "") or ""
        handle = matched.get("handle", {})
        knot = matched.get("knot", {})
        handle_brand = handle.get("brand", "") if handle else ""
        knot_brand = knot.get("brand", "") if knot else ""
        knot_model = knot.get("model", "") if knot else ""
        return f"{brand}|{model}|{handle_brand}|{knot_brand}|{knot_model}"
    elif product_type == "soap":
        brand = matched.get("brand", "")
        scent = matched.get("scent", "")
        return f"{brand}|{scent}"
    else:
        return ""


def _extract_product_info(
    product_type: str, product_data: Dict[str, Any]
) -> Optional[Dict[str, Any]]:
    """Extract product information from product data."""
    if not product_data:
        return None

    matched = product_data.get("matched", {})
    if not matched:
        return None

    if product_type == "razor":
        brand = matched.get("brand")
        model = matched.get("model")
        if brand and model:
            return {
                "key": _generate_product_key(product_type, matched),
                "brand": brand,
                "model": model,
            }
    elif product_type == "blade":
        brand = matched.get("brand")
        model = matched.get("model")
        if brand and model:
            return {
                "key": _generate_product_key(product_type, matched),
                "brand": brand,
                "model": model,
            }
    elif product_type == "brush":
        brand = matched.get("brand")
        model = matched.get("model")
        # Brushes can have brand/model at top level or in handle/knot
        if brand or model:
            return {
                "key": _generate_product_key(product_type, matched),
                "brand": brand or "",
                "model": model or "",
            }
    elif product_type == "soap":
        brand = matched.get("brand")
        scent = matched.get("scent")
        if brand and scent:
            return {
                "key": _generate_product_key(product_type, matched),
                "brand": brand,
                "model": scent,  # Use scent as model for consistency
            }

    return None


@router.get("/products/{month}/{product_type}", response_model=List[Product])
async def get_products_for_month(
    month: str,
    product_type: str,
    search: Optional[str] = Query(None, description="Search filter for products"),
) -> List[Product]:
    """Get list of available products for a month and product type."""
    try:
        # Validate product type
        if product_type not in ["razor", "blade", "brush", "soap"]:
            raise HTTPException(status_code=400, detail=f"Invalid product type: {product_type}")

        # Try to load from pre-computed product usage file
        product_usage_file = get_aggregated_dir() / "product_usage" / f"{month}.json"

        if product_usage_file.exists():
            try:
                with product_usage_file.open("r", encoding="utf-8") as f:
                    product_usage_data = json.load(f)

                # Extract products from the product type category
                products_dict = product_usage_data.get(product_type + "s", {})
                products = []
                for product_key, analysis in products_dict.items():
                    product_info = analysis.get("product", {})
                    products.append(
                        {
                            "key": product_key,
                            "brand": product_info.get("brand", ""),
                            "model": product_info.get("model", ""),
                            "usage_count": analysis.get("total_usage", 0),
                            "unique_users": analysis.get("unique_users", 0),
                        }
                    )

                # Sort by usage count (descending)
                products.sort(key=lambda x: x["usage_count"], reverse=True)

                # Apply search filter if provided
                if search:
                    search_lower = search.lower()
                    products = [
                        p
                        for p in products
                        if search_lower in p["brand"].lower() or search_lower in p["model"].lower()
                    ]

                return products

            except Exception as e:
                logger.warning(
                    f"Error loading product usage file for {month}: {e}, falling back to enriched data"
                )

        # Fallback: Load enriched data and process on-demand
        try:
            enriched_file = get_enriched_dir() / f"{month}.json"

            if not enriched_file.exists():
                return []

            with enriched_file.open("r", encoding="utf-8") as f:
                enriched_data = json.load(f)

            # Extract products from records
            products_dict: Dict[str, Dict[str, Any]] = {}
            records = enriched_data.get("data", [])

            for record in records:
                product_field = record.get(product_type)
                if not product_field:
                    continue

                product_info = _extract_product_info(product_type, product_field)
                if not product_info:
                    continue

                product_key = product_info["key"]
                if product_key not in products_dict:
                    products_dict[product_key] = {
                        "key": product_key,
                        "brand": product_info["brand"],
                        "model": product_info["model"],
                        "usage_count": 0,
                        "unique_users": set(),
                    }

                products_dict[product_key]["usage_count"] += 1
                author = record.get("author")
                if author:
                    products_dict[product_key]["unique_users"].add(author)

            # Convert to list and format
            products = []
            for product_data in products_dict.values():
                products.append(
                    {
                        "key": product_data["key"],
                        "brand": product_data["brand"],
                        "model": product_data["model"],
                        "usage_count": product_data["usage_count"],
                        "unique_users": len(product_data["unique_users"]),
                    }
                )

            # Sort by usage count (descending)
            products.sort(key=lambda x: x["usage_count"], reverse=True)

            # Apply search filter if provided
            if search:
                search_lower = search.lower()
                products = [
                    p
                    for p in products
                    if search_lower in p["brand"].lower() or search_lower in p["model"].lower()
                ]

            return products

        except Exception as e:
            logger.error(f"Error loading enriched data for {month}: {e}")
            return []

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting products for month {month} and type {product_type}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/analysis/{month}/{product_type}/{brand}/{model}", response_model=ProductUsageAnalysis)
async def get_product_usage_analysis(
    month: str, product_type: str, brand: str, model: str
) -> ProductUsageAnalysis:
    """Get product usage analysis for a specific product."""
    try:
        # Decode URL-encoded brand and model
        brand = unquote(brand)
        model = unquote(model)

        # Validate product type
        if product_type not in ["razor", "blade", "brush", "soap"]:
            raise HTTPException(status_code=400, detail=f"Invalid product type: {product_type}")

        # Generate product key for lookup
        if product_type == "soap":
            product_key = f"{brand}|{model}"  # model is scent for soap
        else:
            product_key = f"{brand}|{model}"

        # Try to load from pre-computed product usage file
        product_usage_file = get_aggregated_dir() / "product_usage" / f"{month}.json"

        if product_usage_file.exists():
            try:
                with product_usage_file.open("r", encoding="utf-8") as f:
                    product_usage_data = json.load(f)

                # Find product in the appropriate category
                products_dict = product_usage_data.get(product_type + "s", {})
                if product_key in products_dict:
                    analysis = products_dict[product_key]
                    # Ensure comment_urls is present (may be missing in older files)
                    if "comment_urls" not in analysis:
                        analysis["comment_urls"] = None
                    # Convert to expected format (already in correct structure)
                    return ProductUsageAnalysis(**analysis)
                else:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Product {product_type} '{brand} {model}' not found in month {month}",
                    )

            except HTTPException:
                raise
            except Exception as e:
                logger.warning(
                    f"Error loading product usage file for {month}: {e}, falling back to enriched data"
                )

        # Fallback: Load enriched data and process on-demand
        try:
            enriched_file = get_enriched_dir() / f"{month}.json"

            if not enriched_file.exists():
                raise HTTPException(status_code=404, detail=f"No data available for {month}")

            with enriched_file.open("r", encoding="utf-8") as f:
                enriched_data = json.load(f)

            # Generate product usage analysis on-demand
            product_analyses = aggregate_product_usage(enriched_data["data"])

            # Find product in the appropriate category
            products_dict = product_analyses.get(product_type + "s", {})
            if product_key in products_dict:
                analysis = products_dict[product_key]
                # Ensure comment_urls is present (may be missing in older aggregations)
                if "comment_urls" not in analysis:
                    analysis["comment_urls"] = None
                # Convert to expected format
                return ProductUsageAnalysis(**analysis)
            else:
                raise HTTPException(
                    status_code=404,
                    detail=f"Product {product_type} '{brand} {model}' not found in month {month}",
                )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error loading enriched data for {month}: {e}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Error loading enriched data: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error analyzing product {product_type} '{brand} {model}' for month {month}: {e}",
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


def _construct_product_name(product_type: str, brand: str, model: str) -> str:
    """Construct product name for matching against aggregated data."""
    if product_type == "soap":
        # Soaps use "Brand - Scent" format
        return f"{brand} - {model}"
    else:
        # Razors, blades, brushes use "Brand Model" format
        return f"{brand} {model}"


def _get_months_range(selected_month: str) -> List[str]:
    """Get list of 12 months (selected month and previous 11 months)."""
    try:
        year, month = map(int, selected_month.split("-"))
        months = []
        for i in range(12):
            # Calculate month and year going back i months
            current_month = month - i
            current_year = year

            # Handle month rollover
            while current_month <= 0:
                current_month += 12
                current_year -= 1

            months.append(f"{current_year:04d}-{current_month:02d}")
        months.reverse()  # Oldest to newest
        return months
    except (ValueError, AttributeError) as e:
        logger.error(f"Invalid month format: {selected_month} - {e}")
        raise HTTPException(status_code=400, detail=f"Invalid month format: {selected_month}")


@router.get(
    "/yearly-summary/{month}/{product_type}/{brand}/{model}", response_model=ProductYearlySummary
)
async def get_product_yearly_summary(
    month: str, product_type: str, brand: str, model: str
) -> ProductYearlySummary:
    """Get yearly summary for a specific product over the past 12 months."""
    try:
        # Decode URL-encoded brand and model
        brand = unquote(brand)
        model = unquote(model)

        # Validate product type
        if product_type not in ["razor", "blade", "brush", "soap"]:
            raise HTTPException(status_code=400, detail=f"Invalid product type: {product_type}")

        # Get list of months to query
        months = _get_months_range(month)

        # Construct product name for matching
        product_name = _construct_product_name(product_type, brand, model)
        product_name_lower = product_name.lower()

        # Map product type to aggregated data category
        category_map = {
            "razor": "razors",
            "blade": "blades",
            "brush": "brushes",
            "soap": "soaps",
        }
        category = category_map[product_type]

        # Load aggregated data for each month
        aggregated_dir = get_aggregated_dir()

        monthly_summaries = []

        for month_str in months:
            aggregated_file = aggregated_dir / f"{month_str}.json"

            if not aggregated_file.exists():
                # Month has no aggregated data
                monthly_summaries.append(
                    {
                        "month": month_str,
                        "shaves": 0,
                        "unique_users": 0,
                        "rank": None,
                        "has_data": False,
                    }
                )
                continue

            try:
                with aggregated_file.open("r", encoding="utf-8") as f:
                    aggregated_data = json.load(f)

                # Find product in category array
                category_data = aggregated_data.get("data", {}).get(category, [])
                product_found = None

                for item in category_data:
                    item_name = item.get("name", "")
                    if item_name.lower() == product_name_lower:
                        product_found = item
                        break

                if product_found:
                    monthly_summaries.append(
                        {
                            "month": month_str,
                            "shaves": product_found.get("shaves", 0),
                            "unique_users": product_found.get("unique_users", 0),
                            "rank": product_found.get("rank"),
                            "has_data": True,
                        }
                    )
                else:
                    # Product not found in this month
                    monthly_summaries.append(
                        {
                            "month": month_str,
                            "shaves": 0,
                            "unique_users": 0,
                            "rank": None,
                            "has_data": False,
                        }
                    )

            except Exception as e:
                logger.warning(f"Error loading aggregated data for {month_str}: {e}")
                monthly_summaries.append(
                    {
                        "month": month_str,
                        "shaves": 0,
                        "unique_users": 0,
                        "rank": None,
                        "has_data": False,
                    }
                )

        # Build response
        summary = {
            "product": {
                "type": product_type,
                "brand": brand,
                "model": model,
            },
            "months": monthly_summaries,
        }

        return ProductYearlySummary(**summary)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            f"Error getting yearly summary for {product_type} '{brand} {model}' starting from {month}: {e}"
        )
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "product-usage"}
