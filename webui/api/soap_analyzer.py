import json
import logging
from collections import defaultdict
from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

# Import non-matches loading function and normalization
from webui.api.utils.data_dir import get_matched_dir
from webui.api.utils.non_matches import (
    _canonicalize_brand_pair,
    _canonicalize_cross_brand_scent_key,
    _canonicalize_scent_pair,
    load_non_matches,
    save_brand_non_match,
    save_cross_brand_scent_non_match,
    save_scent_non_match,
)
from webui.api.wsdb_alignment import normalize_for_matching

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/soaps", tags=["soaps"])


# Request model for SoapAnalyzer non-matches
class SoapNonMatchRequest(BaseModel):
    """Request model for SoapAnalyzer non-match operations."""

    mode: str  # "brands", "brand_scent", or "scents"
    entry1_brand: str
    entry1_scent: Optional[str] = None
    entry2_brand: str
    entry2_scent: Optional[str] = None


# Pydantic models for response
class SoapDuplicateResult:
    def __init__(self, text1: str, text2: str, similarity: float, count: int):
        self.text1 = text1
        self.text2 = text2
        self.similarity = similarity
        self.count = count


class SoapPatternSuggestion:
    def __init__(self, pattern: str, count: int, examples: List[str]):
        self.pattern = pattern
        self.count = count
        self.examples = examples


def is_valid_month(month: str) -> bool:
    """Validate month format (YYYY-MM)"""
    try:
        if len(month) != 7 or month[4] != "-":
            return False
        year = int(month[:4])
        month_num = int(month[5:])
        return 2020 <= year <= 2030 and 1 <= month_num <= 12
    except ValueError:
        return False


@router.get("/duplicates")
async def get_soap_duplicates(
    months: str = Query(..., description="Comma-separated months (e.g., '2025-05,2025-06')"),
    similarity_threshold: float = Query(
        0.8, ge=0.0, le=1.0, description="Similarity threshold for duplicates"
    ),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results"),
):
    """Get potential duplicate soap matches"""
    try:
        # Parse months
        month_list = [m.strip() for m in months.split(",")]
        for month in month_list:
            if not is_valid_month(month):
                raise HTTPException(status_code=400, detail=f"Invalid month format: {month}")

        logger.info(f"🔍 Analyzing soap duplicates for months: {month_list}")

        # Load data from all specified months
        all_matches = []
        # SOTD_DATA_DIR is the data dir (data-dir convention); falls back to project data/
        data_dir = get_matched_dir()

        for month in month_list:
            month_file = data_dir / f"{month}.json"
            if not month_file.exists():
                logger.warning(f"No match data found for month: {month}")
                continue

            try:
                with open(month_file, "r") as f:
                    match_data = json.load(f)

                # Extract soap data from the data array
                if "data" in match_data and isinstance(match_data["data"], list):
                    for record in match_data["data"]:
                        if "soap" in record and record["soap"]:
                            all_matches.append(record["soap"])

            except Exception as e:
                logger.error(f"Error loading month {month}: {e}")
                continue

        if not all_matches:
            return {"message": "No soap matches found for the specified months", "results": []}

        logger.info(f"Processing {len(all_matches)} total soap matches")

        # Analyze duplicates
        results = analyze_soap_duplicates_web(all_matches, similarity_threshold, limit)

        return {
            "message": f"Found {len(results)} potential duplicates",
            "results": results,
            "total_matches": len(all_matches),
            "months_processed": month_list,
        }

    except Exception as e:
        logger.error(f"Error in soap duplicates analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pattern-suggestions")
async def get_soap_pattern_suggestions(
    months: str = Query(..., description="Comma-separated months (e.g., '2025-05,2025-06')"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results"),
):
    """Get soap pattern suggestions"""
    try:
        # Parse months
        month_list = [m.strip() for m in months.split(",")]
        for month in month_list:
            if not is_valid_month(month):
                raise HTTPException(status_code=400, detail=f"Invalid month format: {month}")

        logger.info(f"🔍 Analyzing soap patterns for months: {month_list}")

        # Load data from all specified months
        all_matches = []
        # SOTD_DATA_DIR is the data dir (data-dir convention); falls back to project data/
        data_dir = get_matched_dir()

        for month in month_list:
            month_file = data_dir / f"{month}.json"
            if not month_file.exists():
                logger.warning(f"No match data found for month: {month}")
                continue

            try:
                with open(month_file, "r") as f:
                    match_data = json.load(f)

                # Extract soap data from the data array
                if "data" in match_data and isinstance(match_data["data"], list):
                    for record in match_data["data"]:
                        if "soap" in record and record["soap"]:
                            all_matches.append(record["soap"])

            except Exception as e:
                logger.error(f"Error loading month {month}: {e}")
                continue

        if not all_matches:
            return {"message": "No soap matches found for the specified months", "results": []}

        logger.info(f"Processing {len(all_matches)} total soap matches for patterns")

        # Analyze patterns
        results = analyze_soap_patterns_web(all_matches, limit)

        return {
            "message": f"Found {len(results)} pattern suggestions",
            "results": results,
            "total_matches": len(all_matches),
            "months_processed": month_list,
        }

    except Exception as e:
        logger.error(f"Error in soap pattern analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/neighbor-similarity")
async def get_soap_neighbor_similarity(
    months: str = Query("", description="Comma-separated months (e.g., '2025-05,2025-06')"),
    mode: str = Query(..., description="Analysis mode: brands, brand_scent, or scents"),
    similarity_threshold: float = Query(
        0.5, ge=0.0, le=1.0, description="Similarity threshold for filtering results"
    ),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results"),
):
    """Get soap neighbor similarity analysis"""
    try:
        # Validate mode parameter
        valid_modes = ["brands", "brand_scent", "scents"]
        if mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {mode}. Must be one of: {', '.join(valid_modes)}",
            )

        # Parse months
        month_list = [m.strip() for m in months.split(",") if m.strip()]

        # Handle empty months gracefully
        if not month_list:
            return {
                "message": "No months specified",
                "results": [],
                "mode": mode,
                "total_entries": 0,
                "months_processed": [],
            }

        for month in month_list:
            if not is_valid_month(month):
                raise HTTPException(status_code=400, detail=f"Invalid month format: {month}")

        logger.info(f"🔍 Analyzing soap neighbor similarity for months: {month_list}, mode: {mode}")

        # Load data from all specified months
        all_matches = []
        # SOTD_DATA_DIR is the data dir (data-dir convention); falls back to project data/
        data_dir = get_matched_dir()

        for month in month_list:
            month_file = data_dir / f"{month}.json"
            if not month_file.exists():
                logger.warning(f"No match data found for month: {month}")
                continue

            try:
                with open(month_file, "r") as f:
                    match_data = json.load(f)

                # Extract soap data from the data array
                if "data" in match_data and isinstance(match_data["data"], list):
                    for record in match_data["data"]:
                        if "soap" in record and record["soap"]:
                            # Add the record ID as comment_id to the soap object
                            soap_data = record["soap"].copy()
                            soap_data["comment_id"] = record.get("id", record.get("comment_id", ""))
                            all_matches.append(soap_data)

            except Exception as e:
                logger.error(f"Error loading month {month}: {e}")
                continue

        if not all_matches:
            return {
                "message": "No soap matches found for the specified months",
                "results": [],
                "mode": mode,
                "total_entries": 0,
                "months_processed": month_list,
            }

        logger.info(f"Processing {len(all_matches)} total soap matches for neighbor similarity")

        # Load non-matches data for filtering
        try:
            non_matches_data = load_non_matches()
            brand_non_matches = non_matches_data.get("brand_non_matches", {})
            scent_non_matches = non_matches_data.get("scent_non_matches", {})
            scent_cross_brand_non_matches = non_matches_data.get(
                "scent_cross_brand_non_matches", {}
            )
        except Exception as e:
            logger.warning(f"Failed to load non-matches, continuing without filtering: {e}")
            brand_non_matches = {}
            scent_non_matches = {}
            scent_cross_brand_non_matches = {}

        # Analyze neighbor similarity
        try:
            results = analyze_soap_neighbor_similarity_web(
                all_matches,
                mode,
                similarity_threshold,
                limit,
                brand_non_matches,
                scent_non_matches,
                scent_cross_brand_non_matches,
            )
        except Exception as e:
            logger.error(f"Error in analyze_soap_neighbor_similarity_web: {e}", exc_info=True)
            raise HTTPException(
                status_code=500, detail=f"Error analyzing neighbor similarity: {str(e)}"
            )

        return {
            "message": f"Neighbor similarity analysis completed for {mode} mode",
            "mode": mode,
            "results": results,
            "total_entries": len(results),
            "months_processed": month_list,
        }

    except HTTPException:
        # Re-raise HTTPException to preserve status codes
        raise
    except Exception as e:
        logger.error(f"Error in soap neighbor similarity analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/non-matches")
async def add_soap_non_match(request: SoapNonMatchRequest) -> dict[str, Any]:
    """
    Add a new non-match entry from SoapAnalyzer neighbor similarity analysis.

    Args:
        request: Non-match request with mode and entry data

    Returns:
        Dict with success status and message
    """
    try:
        logger.info(
            f"➕ Adding soap non-match: {request.mode} - {request.entry1_brand}/{request.entry1_scent} != {request.entry2_brand}/{request.entry2_scent}"
        )

        # Validate mode
        valid_modes = ["brands", "brand_scent", "scents"]
        if request.mode not in valid_modes:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid mode: {request.mode}. Must be one of: {', '.join(valid_modes)}",
            )

        # Normalize brands for comparison
        brand1_norm = normalize_for_matching(request.entry1_brand)
        brand2_norm = normalize_for_matching(request.entry2_brand)

        if request.mode == "brands":
            # Use shared utility to save brand non-match
            return save_brand_non_match(request.entry1_brand, request.entry2_brand)

        elif request.mode == "brand_scent":
            # Validate same brand for brand_scent mode
            if brand1_norm != brand2_norm:
                raise HTTPException(
                    status_code=400,
                    detail=f"brand_scent mode requires same brand, got {request.entry1_brand} and {request.entry2_brand}",
                )

            if not request.entry1_scent or not request.entry2_scent:
                raise HTTPException(status_code=400, detail="brand_scent mode requires both scents")

            # Use shared utility to save scent non-match (same brand)
            return save_scent_non_match(
                request.entry1_brand, request.entry1_scent, request.entry2_scent
            )

        elif request.mode == "scents":
            if not request.entry1_scent or not request.entry2_scent:
                raise HTTPException(status_code=400, detail="scents mode requires both scents")

            # Determine which file to use based on brand match
            if brand1_norm == brand2_norm:
                # Same brand: use shared utility to save scent non-match
                return save_scent_non_match(
                    request.entry1_brand, request.entry1_scent, request.entry2_scent
                )
            else:
                # Different brands: use shared utility to save cross-brand scent non-match
                return save_cross_brand_scent_non_match(
                    request.entry1_brand,
                    request.entry1_scent,
                    request.entry2_brand,
                    request.entry2_scent,
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Failed to add soap non-match: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add non-match: {str(e)}")


def analyze_soap_duplicates_web(
    matches: List[dict], similarity_threshold: float = 0.9, limit: Optional[int] = None
) -> List[dict]:
    """Analyze soap matches for potential duplicates (web-optimized version)"""
    from difflib import SequenceMatcher

    # Group by maker first, then by scent for efficiency
    maker_groups = defaultdict(list)
    for match in matches:
        # Handle both direct fields and nested matched fields
        if "matched" in match and match["matched"]:
            maker = match["matched"].get("maker", "").lower()
            scent = match["matched"].get("scent", "").lower()
        else:
            maker = match.get("maker", "").lower()
            scent = match.get("scent", "").lower()

        if maker and scent:  # Only add if both fields exist
            maker_groups[maker].append(scent)

    results = []
    shown = 0
    limit_reached = False

    # Compare within maker groups
    for maker1, scents1 in maker_groups.items():
        if limit_reached:
            break

        for maker2, scents2 in maker_groups.items():
            if limit_reached:
                break

            # Skip same maker comparisons
            if maker1 == maker2:
                continue

            # Calculate maker similarity once
            maker_similarity = SequenceMatcher(None, maker1, maker2).ratio()

            # Only proceed if makers are similar enough
            if maker_similarity < similarity_threshold * 0.8:
                continue

            # Compare scents within similar makers
            for scent1 in scents1:
                if limit_reached:
                    break

                for scent2 in scents2:
                    if limit_reached:
                        break

                    # Calculate overall similarity
                    scent_similarity = SequenceMatcher(None, scent1, scent2).ratio()
                    overall_similarity = (maker_similarity + scent_similarity) / 2

                    if overall_similarity >= similarity_threshold:
                        # Count occurrences
                        count1 = sum(
                            1
                            for m in matches
                            if (
                                (
                                    m.get("matched")
                                    and m["matched"].get("maker", "").lower() == maker1
                                    and m["matched"].get("scent", "").lower() == scent1
                                )
                                or (
                                    m.get("maker", "").lower() == maker1
                                    and m.get("scent", "").lower() == scent1
                                )
                            )
                        )
                        count2 = sum(
                            1
                            for m in matches
                            if (
                                (
                                    m.get("matched")
                                    and m["matched"].get("maker", "").lower() == maker2
                                    and m["matched"].get("scent", "").lower() == scent2
                                )
                                or (
                                    m.get("maker", "").lower() == maker2
                                    and m.get("scent", "").lower() == scent2
                                )
                            )
                        )
                        total_count = count1 + count2

                        result = {
                            "text1": f"{maker1.title()} {scent1.title()}",
                            "text2": f"{maker2.title()} {scent2.title()}",
                            "similarity": round(overall_similarity, 3),
                            "count": total_count,
                            "maker1": maker1.title(),
                            "scent1": scent1.title(),
                            "maker2": maker2.title(),
                            "scent2": scent2.title(),
                        }

                        results.append(result)
                        shown += 1

                        if limit is not None and shown >= limit:
                            limit_reached = True
                            break

    # Sort by similarity (highest first) and count
    results.sort(key=lambda x: (x["similarity"], x["count"]), reverse=True)

    return results


def analyze_soap_patterns_web(matches: List[dict], limit: Optional[int] = None) -> List[dict]:
    """Analyze soap patterns for suggestions (web-optimized version)"""
    # Count patterns
    pattern_counts = defaultdict(int)
    pattern_examples = defaultdict(list)

    for match in matches:
        # Handle both direct fields and nested matched fields
        if "matched" in match and match["matched"]:
            maker = match["matched"].get("maker", "").lower()
            scent = match["matched"].get("scent", "").lower()
        else:
            maker = match.get("maker", "").lower()
            scent = match.get("scent", "").lower()

        if maker and scent:
            pattern = f"{maker} {scent}"
            pattern_counts[pattern] += 1

            # Keep up to 3 examples
            if len(pattern_examples[pattern]) < 3:
                original = match.get("original", "")
                if original:
                    pattern_examples[pattern].append(original)

    # Convert to results
    results = []
    for pattern, count in sorted(pattern_counts.items(), key=lambda x: x[1], reverse=True):
        if limit and len(results) >= limit:
            break

        result = {
            "pattern": pattern.title(),
            "count": count,
            "examples": pattern_examples[pattern][:3],
        }
        results.append(result)

    return results


def symmetric_similarity(text1: str, text2: str) -> float:
    """Calculate symmetric similarity between two strings.

    SequenceMatcher is inherently asymmetric, but we want symmetric similarity scores.
    This function ensures that similarity(A, B) == similarity(B, A) by taking the
    maximum of both directions.
    """
    from difflib import SequenceMatcher

    score_1_to_2 = SequenceMatcher(None, text1, text2).ratio()
    score_2_to_1 = SequenceMatcher(None, text2, text1).ratio()
    return max(score_1_to_2, score_2_to_1)


def are_entries_non_matches(
    entry1: dict,
    entry2: dict,
    mode: str,
    brand_non_matches: dict,
    scent_non_matches: dict,
    scent_cross_brand_non_matches: dict = None,
) -> bool:
    """
    Check if two neighbor entries are known non-matches.

    Args:
        entry1: First entry dict with original_matches list
        entry2: Second entry dict with original_matches list
        mode: Analysis mode ("brands", "brand_scent", or "scents")
        brand_non_matches: Dict of brand -> [non_match_brands]
        scent_non_matches: Dict of brand -> scent -> [non_match_scents] (same-brand)
        scent_cross_brand_non_matches: Dict of scent_name -> [list of {brand, scent} dicts] (cross-brand)

    Returns:
        True if the two entries are known non-matches
    """
    if scent_cross_brand_non_matches is None:
        scent_cross_brand_non_matches = {}

    # Extract brand and scent from first occurrence of each entry
    def extract_brand_scent(entry_dict):
        """Extract brand and scent from entry's first original match."""
        if not entry_dict.get("original_matches"):
            return None, None

        first_match = entry_dict["original_matches"][0]
        if "matched" in first_match and first_match["matched"]:
            brand = first_match["matched"].get("brand", "")
            scent = first_match["matched"].get("scent", "")
        else:
            brand = first_match.get("brand", "")
            scent = first_match.get("scent", "")
        return brand, scent

    brand1, scent1 = extract_brand_scent(entry1)
    brand2, scent2 = extract_brand_scent(entry2)

    if not brand1 or not brand2:
        return False

    # Normalize brands for comparison
    brand1_norm = normalize_for_matching(brand1)
    brand2_norm = normalize_for_matching(brand2)

    if mode == "brands":
        # Build canonical pair and check (relationships stored under alphabetically first key)
        canonical_key, other_brand = _canonicalize_brand_pair(brand1, brand2)

        # Case-insensitive brand lookup (normalize brand for comparison)
        canonical_key_norm = normalize_for_matching(canonical_key)
        for stored_brand in brand_non_matches.keys():
            if normalize_for_matching(stored_brand) == canonical_key_norm:
                if any(
                    normalize_for_matching(nm) == normalize_for_matching(other_brand)
                    for nm in brand_non_matches[stored_brand]
                ):
                    return True
                break

        return False

    elif mode == "brand_scent":
        # For brand_scent mode, check if same brand but different scents are non-matches
        if brand1_norm != brand2_norm:
            return False  # Different brands, not a scent non-match

        if not scent1 or not scent2:
            return False

        scent1_norm = normalize_for_matching(scent1)
        scent2_norm = normalize_for_matching(scent2)

        # Build canonical pair and check (relationships stored under alphabetically first scent)
        canonical_key, other_scent = _canonicalize_scent_pair(scent1, scent2)
        canonical_key_norm = normalize_for_matching(canonical_key)
        other_scent_norm = normalize_for_matching(other_scent)

        # Case-insensitive brand and scent lookup (normalize for comparison)
        # (brand1_norm already calculated above)
        for stored_brand in scent_non_matches.keys():
            if normalize_for_matching(stored_brand) == brand1_norm:
                # Case-insensitive scent key lookup
                for stored_scent_key in scent_non_matches[stored_brand].keys():
                    if normalize_for_matching(stored_scent_key) == canonical_key_norm:
                        if any(
                            normalize_for_matching(nm) == other_scent_norm
                            for nm in scent_non_matches[stored_brand][stored_scent_key]
                        ):
                            return True
                        break
                break

        return False

    elif mode == "scents":
        if not scent1 or not scent2:
            return False

        scent1_norm = normalize_for_matching(scent1)
        scent2_norm = normalize_for_matching(scent2)

        # If brands match, check same-brand scent non-matches
        if brand1_norm == brand2_norm:
            # Build canonical pair and check (relationships stored under alphabetically first scent)
            canonical_key, other_scent = _canonicalize_scent_pair(scent1, scent2)
            canonical_key_norm = normalize_for_matching(canonical_key)
            other_scent_norm = normalize_for_matching(other_scent)

            # Case-insensitive brand and scent lookup (normalize for comparison)
            # (brand1_norm already calculated above)
            for stored_brand in scent_non_matches.keys():
                if normalize_for_matching(stored_brand) == brand1_norm:
                    # Case-insensitive scent key lookup
                    for stored_scent_key in scent_non_matches[stored_brand].keys():
                        if normalize_for_matching(stored_scent_key) == canonical_key_norm:
                            if any(
                                normalize_for_matching(nm) == other_scent_norm
                                for nm in scent_non_matches[stored_brand][stored_scent_key]
                            ):
                                return True
                            break
                    break
        else:
            # Different brands: check cross-brand scent non-matches
            # Get canonical scent key (alphabetically first)
            canonical_key = _canonicalize_cross_brand_scent_key(scent1, scent2)
            canonical_key_norm = normalize_for_matching(canonical_key)

            # Case-insensitive scent key lookup
            for stored_scent_key in scent_cross_brand_non_matches.keys():
                if normalize_for_matching(stored_scent_key) == canonical_key_norm:
                    brand_scent_pairs = scent_cross_brand_non_matches[stored_scent_key]
                    # Check if entry1 is in this group
                    entry1_in_group = any(
                        normalize_for_matching(pair.get("brand", "")) == brand1_norm
                        and normalize_for_matching(pair.get("scent", "")) == scent1_norm
                        for pair in brand_scent_pairs
                    )
                    # Check if entry2 is in this group
                    entry2_in_group = any(
                        normalize_for_matching(pair.get("brand", "")) == brand2_norm
                        and normalize_for_matching(pair.get("scent", "")) == scent2_norm
                        for pair in brand_scent_pairs
                    )
                    # If both are in the same group, they're non-matches
                    if entry1_in_group and entry2_in_group:
                        return True
                    break
        return False

    return False


def analyze_soap_neighbor_similarity_web(
    matches: list[dict],
    mode: str,
    similarity_threshold: float = 0.5,
    limit: Optional[int] = None,
    brand_non_matches: dict = None,
    scent_non_matches: dict = None,
    scent_cross_brand_non_matches: dict = None,
) -> list[dict]:
    """Analyze soap matches for neighbor similarity (web-optimized version)"""
    import logging

    logger = logging.getLogger(__name__)

    # Default to empty dicts if not provided
    if brand_non_matches is None:
        brand_non_matches = {}
    if scent_non_matches is None:
        scent_non_matches = {}
    if scent_cross_brand_non_matches is None:
        scent_cross_brand_non_matches = {}

    # Memory optimization: Process in chunks for very large datasets
    if len(matches) > 10000:  # If more than 10k matches, log memory usage
        logger.info(f"Processing large dataset: {len(matches)} matches")

    # Extract data based on mode with comment tracking
    entries_data = []
    for match in matches:
        # Handle both direct fields and nested matched fields
        if "matched" in match and match["matched"]:
            brand = match["matched"].get("brand", "")
            scent = match["matched"].get("scent", "")
        else:
            brand = match.get("brand", "")
            scent = match.get("scent", "")

        # Mode-specific validation
        should_include = False
        if mode == "brands" and brand:
            should_include = True
        elif mode == "brand_scent" and brand:
            # Include entries with brand (even if scent is empty) - this is what we want to analyze
            should_include = True
        elif mode == "scents" and scent:
            should_include = True

        if should_include:
            comment_id = match.get("comment_id", "")
            entry = ""
            normalized = ""

            if mode == "brands":
                entry = brand
                normalized = brand.lower().strip()
            elif mode == "brand_scent":
                entry = f"{brand} - {scent}"
                brand_lower = brand.lower().strip()
                scent_lower = scent.lower().strip()
                normalized = f"{brand_lower} - {scent_lower}"
            elif mode == "scents":
                entry = scent
                normalized = scent.lower().strip()

            if entry and normalized:  # Only add if we have valid data
                entries_data.append(
                    {
                        "entry": entry,
                        "normalized": normalized,
                        "comment_id": comment_id,
                        "original_match": match,
                    }
                )

    if not entries_data:
        return []

    # Group by normalized string (case-insensitive grouping)
    grouped_entries = {}
    for entry_data in entries_data:
        normalized = entry_data["normalized"]
        if normalized not in grouped_entries:
            grouped_entries[normalized] = {
                "entry": entry_data["entry"],
                "normalized_string": normalized,
                "comment_ids": [],
                "count": 0,
                "original_matches": [],
            }

        grouped_entries[normalized]["comment_ids"].append(entry_data["comment_id"])
        grouped_entries[normalized]["count"] += 1
        grouped_entries[normalized]["original_matches"].append(entry_data["original_match"])

    # Convert to list and sort by normalized string
    unique_entries = sorted(grouped_entries.values(), key=lambda x: x["normalized_string"])

    # First pass: calculate similarities and identify entries that meet threshold
    entries_with_similarities = []

    # Memory optimization: Process in smaller chunks for very large datasets
    chunk_size = 1000
    total_entries = len(unique_entries)

    if total_entries > 5000:
        logger.info(f"Processing {total_entries} entries in chunks of {chunk_size}")

    for i in range(len(unique_entries)):
        current = unique_entries[i]

        # Calculate similarity to entry above (if exists)
        similarity_to_above = None
        if i > 0:
            above = unique_entries[i - 1]
            # Check if entries are known non-matches first
            if are_entries_non_matches(
                current,
                above,
                mode,
                brand_non_matches,
                scent_non_matches,
                scent_cross_brand_non_matches,
            ):
                similarity_to_above = 0.0
            else:
                above_normalized = above["normalized_string"]
                current_normalized = current["normalized_string"]
                similarity_to_above = symmetric_similarity(current_normalized, above_normalized)

        # Calculate similarity to entry below (if exists)
        similarity_to_below = None
        if i < len(unique_entries) - 1:
            below = unique_entries[i + 1]
            # Check if entries are known non-matches first
            if are_entries_non_matches(
                current,
                below,
                mode,
                brand_non_matches,
                scent_non_matches,
                scent_cross_brand_non_matches,
            ):
                similarity_to_below = 0.0
            else:
                below_normalized = below["normalized_string"]
                current_normalized = current["normalized_string"]
                similarity_to_below = symmetric_similarity(current_normalized, below_normalized)

        # Check if this entry meets the similarity threshold with either neighbor
        meets_threshold = (
            similarity_to_above is not None and similarity_to_above >= similarity_threshold
        ) or (similarity_to_below is not None and similarity_to_below >= similarity_threshold)

        if meets_threshold:
            entries_with_similarities.append(
                {
                    "entry": current["entry"],
                    "normalized_string": current["normalized_string"],
                    "comment_ids": current["comment_ids"],
                    "count": current["count"],
                    "original_matches": current["original_matches"],
                    "original_similarity_to_above": similarity_to_above,
                    "original_similarity_to_below": similarity_to_below,
                }
            )

    # Second pass: recalculate similarities for the filtered entries only
    results = []
    for i in range(len(entries_with_similarities)):
        current = entries_with_similarities[i]

        # Calculate similarity to entry above (if exists) in the filtered dataset
        similarity_to_above = None
        if i > 0:
            above = entries_with_similarities[i - 1]
            # Check if entries are known non-matches first
            if are_entries_non_matches(
                current,
                above,
                mode,
                brand_non_matches,
                scent_non_matches,
                scent_cross_brand_non_matches,
            ):
                similarity_to_above = 0.0
            else:
                above_normalized = above["normalized_string"]
                current_normalized = current["normalized_string"]
                similarity_to_above = symmetric_similarity(current_normalized, above_normalized)

        # Calculate similarity to entry below (if exists) in the filtered dataset
        similarity_to_below = None
        if i < len(entries_with_similarities) - 1:
            below = entries_with_similarities[i + 1]
            # Check if entries are known non-matches first
            if are_entries_non_matches(
                current,
                below,
                mode,
                brand_non_matches,
                scent_non_matches,
                scent_cross_brand_non_matches,
            ):
                similarity_to_below = 0.0
            else:
                below_normalized = below["normalized_string"]
                current_normalized = current["normalized_string"]
                similarity_to_below = symmetric_similarity(current_normalized, below_normalized)

        # Determine pattern and normalized string from the first occurrence
        first_match = current["original_matches"][0]
        pattern = first_match.get("pattern", current["entry"])
        normalized_string = first_match.get("normalized", current["normalized_string"])

        # Collect all unique match_types from all matches in this group
        match_types = set()
        for match in current["original_matches"]:
            match_type = match.get("match_type", "unknown")
            match_types.add(match_type)
        match_types = sorted(list(match_types))  # Sort for consistent display

        # Extract matched data from the first occurrence for consistent display
        first_match = current["original_matches"][0]
        matched_data = None
        if "matched" in first_match and first_match["matched"]:
            # Get brand (prefer "brand" field, fallback to "maker" for compatibility)
            brand = first_match["matched"].get("brand", "") or first_match["matched"].get(
                "maker", ""
            )
            matched_data = {
                "brand": brand,  # Use "brand" consistently
                "maker": brand,  # Also include "maker" for frontend compatibility
                "scent": first_match["matched"].get("scent", ""),
            }

        # Recalculate entry from matched data for consistency
        # This ensures the entry string matches the actual matched brand/scent,
        # even if different records had slightly different formatting
        entry = current["entry"]
        if matched_data and mode == "brand_scent":
            # Recalculate entry from matched data to ensure consistency
            recalculated_entry = f"{matched_data['brand']} - {matched_data['scent']}"
            entry = recalculated_entry
        elif matched_data and mode == "brands":
            entry = matched_data["brand"]
        elif matched_data and mode == "scents":
            entry = matched_data["scent"]

        # Get next entry for display (recalculate it too for consistency)
        next_entry = None
        if i < len(entries_with_similarities) - 1:
            next_group = entries_with_similarities[i + 1]
            next_first_match = next_group["original_matches"][0]
            next_matched_data = None
            if "matched" in next_first_match and next_first_match["matched"]:
                # Get brand (prefer "brand" field, fallback to "maker" for compatibility)
                next_brand = next_first_match["matched"].get("brand", "") or next_first_match[
                    "matched"
                ].get("maker", "")
                next_matched_data = {
                    "brand": next_brand,
                    "maker": next_brand,  # Also include "maker" for frontend compatibility
                    "scent": next_first_match["matched"].get("scent", ""),
                }
            if next_matched_data and mode == "brand_scent":
                next_entry = f"{next_matched_data['brand']} - {next_matched_data['scent']}"
            elif next_matched_data and mode == "brands":
                next_entry = next_matched_data["brand"]
            elif next_matched_data and mode == "scents":
                next_entry = next_matched_data["scent"]
            else:
                next_entry = next_group["entry"]

        results.append(
            {
                "entry": entry,
                "similarity_to_above": similarity_to_above,
                "similarity_to_next": similarity_to_below,
                "next_entry": next_entry,
                "normalized_string": normalized_string,
                "pattern": pattern,
                "comment_ids": current["comment_ids"],
                "count": current["count"],
                "matched": matched_data,
                "match_types": match_types,
            }
        )

    # Apply limit if specified
    if limit is not None:
        results = results[:limit]

    # Final memory cleanup and logging
    if total_entries > 5000:
        logger.info(
            f"Completed processing {total_entries} entries, returned {len(results)} results"
        )

    # Clear large intermediate data structures to free memory
    del entries_with_similarities
    del unique_entries
    del grouped_entries
    del entries_data

    return results


@router.get("/group-by-matched")
async def get_soap_group_by_matched(
    months: str = Query(..., description="Comma-separated months (e.g., '2025-05,2025-06')"),
    group_by_matched: bool = Query(True, description="Group by matched string (brand + scent)"),
    limit: Optional[int] = Query(None, ge=1, description="Maximum number of results"),
):
    """
    Group soap matches by matched string (brand + scent) to show total usage counts
    for each soap across all match types.

    When group_by_matched=True:
    - Groups results by matched string (brand + scent) instead of original string
    - Shows matched string, total count, and top 3 most common original patterns with
      individual counts
    - Includes all match types (exact, brand, alias, regex) to show complete usage
    - Helps identify which soaps are most commonly mentioned and need better patterns

    When group_by_matched=False:
    - Groups results by original string (existing behavior)
    """
    try:
        # Validate months
        month_list = [m.strip() for m in months.split(",")]
        for month in month_list:
            if not is_valid_month(month):
                raise HTTPException(
                    status_code=400, detail=f"Invalid month format: {month}. Use YYYY-MM format."
                )

        # Load soap match data for the specified months
        matches = []
        # data-dir convention: SOTD_DATA_DIR is the data dir; falls back to project data/
        data_dir = get_matched_dir()
        for month in month_list:
            month_file = data_dir / f"{month}.json"
            if not month_file.exists():
                logger.warning(f"Month file not found: {month_file}")
                continue

            try:
                with open(month_file, "r", encoding="utf-8") as f:
                    month_data = json.load(f)
                    # Extract soap data from the data array
                    if "data" in month_data and isinstance(month_data["data"], list):
                        for record in month_data["data"]:
                            if "soap" in record and record["soap"]:
                                matches.append(record["soap"])
            except Exception as e:
                logger.error(f"Error loading month {month}: {e}")
                continue

        if not matches:
            return {
                "groups": [],
                "total_groups": 0,
                "total_matches": 0,
                "months_processed": month_list,
                "group_by_matched": group_by_matched,
            }

        # Debug: Log match types being processed
        match_types = {}
        for match in matches:
            match_type = match.get("match_type", "unknown")
            match_types[match_type] = match_types.get(match_type, 0) + 1
        print(f"🔍 DEBUG: Processing {len(matches)} matches with types: {match_types}")
        logger.info(f"🔍 DEBUG: Processing {len(matches)} matches with types: {match_types}")

        # Group the matches
        if group_by_matched:
            groups = group_soap_matches_by_matched(matches, limit)
        else:
            groups = group_soap_matches_by_original(matches, limit)

        return {
            "groups": groups,
            "total_groups": len(groups),
            "total_matches": sum(group["total_count"] for group in groups),
            "months_processed": month_list,
            "group_by_matched": group_by_matched,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in soap group by matched analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def group_soap_matches_by_matched(matches: List[dict], limit: Optional[int] = None) -> List[dict]:
    """
    Group soap matches by matched string (brand + scent) with original pattern aggregation.

    Returns groups sorted by total count (descending) with top 3 original patterns per group.
    """
    from collections import Counter, defaultdict

    # Group by matched string (brand + scent)
    matched_groups = defaultdict(list)

    for match in matches:
        # Include all match types (exact, brand, alias, regex) to show total counts
        # This helps identify which soaps are most commonly mentioned regardless of match type

        # Extract matched data
        matched_data = match.get("matched", {})
        if not matched_data:
            continue

        brand = matched_data.get("brand", "").strip()
        scent = matched_data.get("scent", "").strip()
        countable = matched_data.get("countable", True)  # Extract flag, default to True
        match_type = match.get("match_type", "unknown")

        if not brand or not scent:
            if match_type == "dash_split":
                print(f"🔍 DEBUG: Skipping dash_split match due to missing brand/scent: {match}")
            continue

        # Create matched string key (case-insensitive for grouping)
        matched_key = f"{brand} - {scent}".lower()

        # Store normalized pattern and match type (for Group by Matched we want normalized patterns)
        normalized = match.get("normalized", "").strip()
        match_type = match.get("match_type", "unknown")

        if normalized:
            enriched = match.get("enriched") or {}
            is_mashup = enriched.get("is_mashup") is True
            sample_type = enriched.get("sample_type") or None
            if isinstance(sample_type, str):
                sample_type = sample_type.strip() or None
            else:
                sample_type = None
            matched_groups[matched_key].append(
                {
                    "original": normalized,  # Use normalized field for pattern display
                    "match_type": match_type,
                    "count": match.get("count", 1),
                    "brand": brand,  # Store original case brand
                    "scent": scent,  # Store original case scent
                    "countable": countable,  # Preserve flag
                    "is_mashup": is_mashup,
                    "sample_type": sample_type,
                }
            )

    # Convert to result format
    results = []
    for matched_string_lower, patterns in matched_groups.items():
        # Get the proper case from the first pattern's stored brand/scent
        # This preserves the original case from the catalog data
        if patterns and "brand" in patterns[0] and "scent" in patterns[0]:
            brand = patterns[0]["brand"]  # Use original case from catalog
            scent = patterns[0]["scent"]  # Use original case from catalog
        else:
            # Fallback to title case if no stored data
            brand_lower, scent_lower = (
                matched_string_lower.split(" - ", 1)
                if " - " in matched_string_lower
                else (matched_string_lower, "")
            )
            brand = brand_lower.title()
            scent = scent_lower.title()

        # Create display version of matched_string with proper case
        matched_string = f"{brand} - {scent}"

        # Count total occurrences
        total_count = sum(pattern["count"] for pattern in patterns)

        # Count original patterns with match type information
        # Use case-insensitive grouping for original patterns to avoid duplicates like
        # "sample" vs "Sample"
        pattern_data = {}
        for pattern in patterns:
            original = pattern["original"]
            # Create a normalized key for grouping (case-insensitive)
            normalized_key = original.lower()

            if normalized_key not in pattern_data:
                pattern_data[normalized_key] = {
                    "count": 0,
                    "match_types": Counter(),
                    "original_display": original,  # Store original case for display
                }
            pattern_data[normalized_key]["count"] += pattern["count"]
            pattern_data[normalized_key]["match_types"][pattern["match_type"]] += pattern["count"]

        # Get top 3 most common original patterns
        top_patterns = sorted(pattern_data.items(), key=lambda x: x[1]["count"], reverse=True)[:3]
        remaining_count = len(pattern_data) - 3

        # Format top patterns with match type
        top_patterns_formatted = [
            {
                "original": data["original_display"],  # Use original case for display
                "count": data["count"],
                "match_type": (
                    data["match_types"].most_common(1)[0][0] if data["match_types"] else "unknown"
                ),
            }
            for pattern, data in top_patterns
        ]

        # Get all patterns for "+ n more" functionality
        all_patterns = [
            {
                "original": data["original_display"],  # Use original case for display
                "count": data["count"],
                "match_type": (
                    data["match_types"].most_common(1)[0][0] if data["match_types"] else "unknown"
                ),
            }
            for pattern, data in sorted(
                pattern_data.items(), key=lambda x: x[1]["count"], reverse=True
            )
        ]

        # Aggregate match types for this group
        match_type_counts = Counter()
        for pattern in patterns:
            match_type_counts[pattern["match_type"]] += pattern["count"]

        # Determine primary match type with priority: regex > brand > dash_split > exact
        # If a soap has regex matches, it should be categorized as regex regardless of other counts
        if "regex" in match_type_counts:
            primary_match_type = "regex"
        elif "brand" in match_type_counts:
            primary_match_type = "brand"
        elif "dash_split" in match_type_counts:
            primary_match_type = "dash_split"
        else:
            # If only exact matches, use exact as primary
            primary_match_type = "exact"

        # Debug: Log match type counts for groups with dash_split matches
        if "dash_split" in match_type_counts:
            print(
                f"🔍 DEBUG: Group '{matched_string}' has dash_split matches: "
                f"{dict(match_type_counts)} -> primary: {primary_match_type}"
            )

        # Create match type breakdown (exact + primary)
        match_type_breakdown = {
            "exact": match_type_counts.get("exact", 0),
            primary_match_type: match_type_counts.get(primary_match_type, 0),
        }

        # Extract countable flag from first pattern (all patterns in group have same brand/scent)
        countable = patterns[0].get("countable", True) if patterns else True
        is_mashup = any(p.get("is_mashup") for p in patterns)
        sample_type = next(
            (p.get("sample_type") for p in patterns if p.get("sample_type")),
            None,
        )

        results.append(
            {
                "matched_string": matched_string,
                "brand": brand,
                "scent": scent,
                "countable": countable,  # Include flag for UI indicator
                "is_mashup": is_mashup,
                "sample_type": sample_type,
                "total_count": total_count,
                "top_patterns": top_patterns_formatted,
                "remaining_count": max(0, remaining_count),
                "all_patterns": all_patterns,
                "pattern_count": len(pattern_data),
                "match_type": primary_match_type,
                "match_type_breakdown": match_type_breakdown,
                "is_grouped": True,
            }
        )

    # Sort by total count (descending)
    results.sort(key=lambda x: x["total_count"], reverse=True)

    # Apply limit if specified
    if limit:
        results = results[:limit]

    return results


def group_soap_matches_by_original(matches: List[dict], limit: Optional[int] = None) -> List[dict]:
    """
    Group soap matches by original string (existing behavior).

    This maintains backward compatibility when group_by_matched=False.
    """
    from collections import Counter, defaultdict

    # Group by original string
    original_groups = defaultdict(list)

    for match in matches:
        original = match.get("original", "").strip()
        if not original:
            continue

        matched_data = match.get("matched", {})
        if not matched_data:
            continue

        brand = matched_data.get("brand", "").strip()
        scent = matched_data.get("scent", "").strip()

        if brand and scent:
            matched_string = f"{brand} - {scent}"
        else:
            matched_string = "Unknown"

        match_type = match.get("match_type", "unknown")
        count = match.get("count", 1)

        original_groups[original].append(
            {"matched_string": matched_string, "match_type": match_type, "count": count}
        )

    # Convert to result format
    results = []
    for original_string, matches_list in original_groups.items():
        # Count total occurrences
        total_count = sum(match["count"] for match in matches_list)

        # Count matched strings
        matched_counts = Counter()
        for match in matches_list:
            matched_counts[match["matched_string"]] += match["count"]

        # Get top 3 most common matched strings
        top_matched = matched_counts.most_common(3)
        remaining_count = len(matched_counts) - 3

        # Format top matched strings
        top_matched_formatted = [
            {"matched_string": matched_string, "count": count}
            for matched_string, count in top_matched
        ]

        # Get all matched strings for "+ n more" functionality
        all_matched = [
            {"matched_string": matched_string, "count": count}
            for matched_string, count in matched_counts.most_common()
        ]

        results.append(
            {
                "original_string": original_string,
                "total_count": total_count,
                "top_matched": top_matched_formatted,
                "remaining_count": max(0, remaining_count),
                "all_matched": all_matched,
                "matched_count": len(matched_counts),
            }
        )

    # Sort by total count (descending)
    results.sort(key=lambda x: x["total_count"], reverse=True)

    # Apply limit if specified
    if limit:
        results = results[:limit]

    return results
