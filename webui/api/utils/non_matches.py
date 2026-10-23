#!/usr/bin/env python3
"""Shared utility module for managing non-matches files.

This module provides functions for loading and saving non-matches data
with support for recursive alphabetical sorting and atomic file writes.
"""

import copy
import logging
from pathlib import Path
from typing import Any

import yaml

# Import normalization function from wsdb_alignment
from webui.api.utils.data_dir import get_overrides_dir
from webui.api.wsdb_alignment import normalize_for_matching

logger = logging.getLogger(__name__)


def get_non_matches_dir() -> Path:
    """Get non-matches directory with SOTD_DATA_DIR support.

    Uses the data-dir convention: SOTD_DATA_DIR IS the data dir (as in
    containers, where the data tree is mounted at /data).

    Returns:
        Path to data/overrides/ directory
    """
    return get_overrides_dir()


def _sort_brand_non_matches(data: dict[str, list[str]]) -> dict[str, list[str]]:
    """Sort brand non-matches data recursively.

    Args:
        data: Dict mapping brand -> list of non-match brands

    Returns:
        Sorted dict with sorted keys and sorted lists
    """
    sorted_data = {}
    for brand in sorted(data.keys()):
        sorted_data[brand] = sorted(data[brand])
    return sorted_data


def _sort_scent_non_matches(
    data: dict[str, dict[str, list[str]]],
) -> dict[str, dict[str, list[str]]]:
    """Sort scent non-matches data recursively.

    Args:
        data: Dict mapping brand -> scent -> list of non-match scents

    Returns:
        Sorted dict with all keys and lists sorted alphabetically
    """
    sorted_data = {}
    for brand in sorted(data.keys()):
        sorted_data[brand] = {}
        for scent in sorted(data[brand].keys()):
            sorted_data[brand][scent] = sorted(data[brand][scent])
    return sorted_data


def _sort_cross_brand_scent_non_matches(
    data: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    """Sort cross-brand scent non-matches data recursively.

    Args:
        data: Dict mapping scent_name -> list of {brand, scent} dicts

    Returns:
        Sorted dict with sorted keys and sorted lists (by brand name)
    """
    sorted_data = {}
    for scent_name in sorted(data.keys()):
        # Sort the list of brand-scent pairs by brand name
        sorted_pairs = sorted(
            data[scent_name], key=lambda x: (x.get("brand", "").lower(), x.get("scent", "").lower())
        )
        sorted_data[scent_name] = sorted_pairs
    return sorted_data


def _sort_non_matches_data(data: dict, file_type: str) -> dict:
    """Recursively sort non-matches data based on file type.

    Args:
        data: The data to sort
        file_type: One of "brands", "scents", or "scents_cross_brand"

    Returns:
        Sorted data with all keys and nested values sorted alphabetically
    """
    if file_type == "brands":
        return _sort_brand_non_matches(data)
    elif file_type == "scents":
        return _sort_scent_non_matches(data)
    elif file_type == "scents_cross_brand":
        return _sort_cross_brand_scent_non_matches(data)
    else:
        logger.warning(f"Unknown file type for sorting: {file_type}, returning unsorted data")
        return data


def _canonicalize_brand_pair(brand1: str, brand2: str) -> tuple[str, str]:
    """Return canonical pair (alphabetically first, alphabetically second).

    Args:
        brand1: First brand name
        brand2: Second brand name

    Returns:
        Tuple of (canonical_key, other_brand) where canonical_key is alphabetically first
    """
    if brand1.lower() < brand2.lower():
        return (brand1, brand2)
    return (brand2, brand1)


def _canonicalize_scent_pair(scent1: str, scent2: str) -> tuple[str, str]:
    """Return canonical pair (alphabetically first, alphabetically second).

    Args:
        scent1: First scent name
        scent2: Second scent name

    Returns:
        Tuple of (canonical_key, other_scent) where canonical_key is alphabetically first
    """
    if scent1.lower() < scent2.lower():
        return (scent1, scent2)
    return (scent2, scent1)


def _canonicalize_cross_brand_scent_key(entry1_scent: str, entry2_scent: str) -> str:
    """Return canonical scent key (alphabetically first).

    Args:
        entry1_scent: First scent name
        entry2_scent: Second scent name

    Returns:
        Alphabetically first scent name
    """
    if entry1_scent.lower() < entry2_scent.lower():
        return entry1_scent
    return entry2_scent


def _dedupe_brand_non_matches(brand_non_matches: dict[str, list[str]]) -> dict[str, list[str]]:
    """Remove duplicates and canonicalize brand non-matches.

    Args:
        brand_non_matches: Dict mapping brand -> list of non-match brands

    Returns:
        Canonicalized dict with no duplicates, using alphabetically first key
    """
    canonical = {}
    seen_pairs = set()

    for brand, non_matches in brand_non_matches.items():
        for non_match in non_matches:
            # Skip self-matches
            if normalize_for_matching(brand) == normalize_for_matching(non_match):
                continue

            # Get canonical pair
            key, other = _canonicalize_brand_pair(brand, non_match)
            pair_key = (normalize_for_matching(key), normalize_for_matching(other))

            # Skip if already seen
            if pair_key in seen_pairs:
                continue
            seen_pairs.add(pair_key)

            # Add to canonical dict
            if key not in canonical:
                canonical[key] = []
            if other not in canonical[key]:
                canonical[key].append(other)

    return canonical


def _dedupe_scent_non_matches(
    scent_non_matches: dict[str, dict[str, list[str]]],
) -> dict[str, dict[str, list[str]]]:
    """Remove duplicates and canonicalize scent non-matches.

    Args:
        scent_non_matches: Dict mapping brand -> scent -> list of non-match scents

    Returns:
        Canonicalized dict with no duplicates, using alphabetically first scent as key
    """
    canonical = {}

    for brand, scents in scent_non_matches.items():
        canonical[brand] = {}
        seen_pairs = set()

        for scent, non_matches in scents.items():
            for non_match in non_matches:
                # Skip self-matches
                if normalize_for_matching(scent) == normalize_for_matching(non_match):
                    continue

                # Get canonical pair
                key, other = _canonicalize_scent_pair(scent, non_match)
                pair_key = (normalize_for_matching(key), normalize_for_matching(other))

                # Skip if already seen
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Add to canonical dict
                if key not in canonical[brand]:
                    canonical[brand][key] = []
                if other not in canonical[brand][key]:
                    canonical[brand][key].append(other)

    return canonical


def _dedupe_cross_brand_scent_non_matches(
    scent_cross_brand_non_matches: dict[str, list[dict[str, str]]],
) -> dict[str, list[dict[str, str]]]:
    """Remove duplicates and canonicalize cross-brand scent non-matches.

    Args:
        scent_cross_brand_non_matches: Dict mapping scent_name -> list of {brand, scent} dicts

    Returns:
        Canonicalized dict with no duplicates, using alphabetically first scent as key
    """
    canonical = {}
    seen_pairs = set()  # Track seen brand-scent pairs

    # First pass: collect all unique pairs and determine canonical keys
    all_pairs = []
    for scent_name, pairs in scent_cross_brand_non_matches.items():
        for pair in pairs:
            pair_scent = pair.get("scent", "")
            # Determine canonical key for this pair group
            canonical_key = _canonicalize_cross_brand_scent_key(scent_name, pair_scent)
            all_pairs.append((canonical_key, pair))

    # Second pass: group pairs by canonical key and dedupe
    for canonical_key, pair in all_pairs:
        if canonical_key not in canonical:
            canonical[canonical_key] = []

        # Check if pair already exists (normalized comparison)
        pair_key = (
            normalize_for_matching(pair.get("brand", "")),
            normalize_for_matching(pair.get("scent", "")),
        )
        if pair_key in seen_pairs:
            continue
        seen_pairs.add(pair_key)

        canonical[canonical_key].append(pair)

    return canonical


def _atomic_write_yaml(file_path: Path, data: dict, file_type: str) -> None:
    """Write YAML file atomically with recursive alphabetical sorting.

    Args:
        file_path: Path to the YAML file
        data: Data to write
        file_type: Type of file for sorting ("brands", "scents", or "scents_cross_brand")
    """
    # Sort data recursively
    sorted_data = _sort_non_matches_data(data, file_type)

    # Write to temporary file first
    temp_file = file_path.with_suffix(".tmp")
    with temp_file.open("w", encoding="utf-8") as f:
        yaml.dump(
            sorted_data,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=True,  # Additional top-level key sorting
        )
    # Atomic replace
    temp_file.replace(file_path)


def load_non_matches() -> dict[str, Any]:
    """Load all non-match files.

    Returns:
        Dict with keys:
        - brand_non_matches: dict[str, list[str]]
        - scent_non_matches: dict[str, dict[str, list[str]]]
        - scent_cross_brand_non_matches: dict[str, list[dict]]
    """
    try:
        logger.info("📂 Loading known non-matches")
        overrides_dir = get_non_matches_dir()
        brands_file = overrides_dir / "non_matches_brands.yaml"
        scents_file = overrides_dir / "non_matches_scents.yaml"
        scents_cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"

        # Load brand non-matches
        brand_non_matches = {}
        if brands_file.exists():
            with brands_file.open("r", encoding="utf-8") as f:
                brand_non_matches = yaml.safe_load(f) or {}

        # Load scent non-matches (same-brand)
        scent_non_matches = {}
        if scents_file.exists():
            with scents_file.open("r", encoding="utf-8") as f:
                scent_non_matches = yaml.safe_load(f) or {}

        # Load cross-brand scent non-matches
        scent_cross_brand_non_matches = {}
        if scents_cross_brand_file.exists():
            with scents_cross_brand_file.open("r", encoding="utf-8") as f:
                scent_cross_brand_non_matches = yaml.safe_load(f) or {}

        # Store original data to detect changes
        original_brand_non_matches = copy.deepcopy(brand_non_matches)
        original_scent_non_matches = copy.deepcopy(scent_non_matches)
        original_scent_cross_brand_non_matches = copy.deepcopy(scent_cross_brand_non_matches)

        # Canonicalize and dedupe loaded data
        brand_non_matches = _dedupe_brand_non_matches(brand_non_matches)
        scent_non_matches = _dedupe_scent_non_matches(scent_non_matches)
        scent_cross_brand_non_matches = _dedupe_cross_brand_scent_non_matches(
            scent_cross_brand_non_matches
        )

        # If canonicalization changed data, save the fixed data back
        if brand_non_matches != original_brand_non_matches:
            _atomic_write_yaml(brands_file, brand_non_matches, "brands")
            logger.info("🔧 Canonicalized and deduped brand non-matches and saved")

        if scent_non_matches != original_scent_non_matches:
            _atomic_write_yaml(scents_file, scent_non_matches, "scents")
            logger.info("🔧 Canonicalized and deduped scent non-matches and saved")

        if scent_cross_brand_non_matches != original_scent_cross_brand_non_matches:
            _atomic_write_yaml(
                scents_cross_brand_file, scent_cross_brand_non_matches, "scents_cross_brand"
            )
            logger.info("🔧 Canonicalized and deduped cross-brand scent non-matches and saved")

        brand_count = sum(len(v) for v in brand_non_matches.values())
        scent_count = sum(
            len(scents)
            for brand_scents in scent_non_matches.values()
            for scents in brand_scents.values()
        )
        cross_brand_count = sum(len(pairs) for pairs in scent_cross_brand_non_matches.values())

        logger.info(
            f"✅ Loaded {brand_count} brand non-matches, {scent_count} scent non-matches, {cross_brand_count} cross-brand scent non-matches"
        )

        return {
            "brand_non_matches": brand_non_matches,
            "scent_non_matches": scent_non_matches,
            "scent_cross_brand_non_matches": scent_cross_brand_non_matches,
        }

    except Exception as e:
        logger.error(f"❌ Failed to load non-matches: {e}")
        raise


def save_brand_non_match(pipeline_brand: str, wsdb_brand: str) -> dict[str, Any]:
    """Save brand non-match with duplicate checking.

    Args:
        pipeline_brand: Pipeline brand name
        wsdb_brand: WSDB brand name that doesn't match

    Returns:
        Dict with 'success' and 'message' keys
    """
    try:
        logger.info(f"➕ Adding brand non-match: {pipeline_brand} != {wsdb_brand}")

        overrides_dir = get_non_matches_dir()
        overrides_dir.mkdir(parents=True, exist_ok=True)
        brands_file = overrides_dir / "non_matches_brands.yaml"

        # Load existing data
        brand_non_matches = {}
        if brands_file.exists():
            with brands_file.open("r", encoding="utf-8") as f:
                brand_non_matches = yaml.safe_load(f) or {}

        # Get canonical pair
        canonical_key, other_brand = _canonicalize_brand_pair(pipeline_brand, wsdb_brand)

        # Initialize if needed
        if canonical_key not in brand_non_matches:
            brand_non_matches[canonical_key] = []

        # Check for duplicate
        other_norm = normalize_for_matching(other_brand)
        if any(normalize_for_matching(nm) == other_norm for nm in brand_non_matches[canonical_key]):
            logger.info("ℹ️ Non-match already exists, skipping")
            return {"success": True, "message": "Non-match already exists"}

        # Add the non-match
        brand_non_matches[canonical_key].append(other_brand)

        # Dedupe and canonicalize (removes any duplicates that crept in)
        brand_non_matches = _dedupe_brand_non_matches(brand_non_matches)

        # Save atomically with sorting
        _atomic_write_yaml(brands_file, brand_non_matches, "brands")

        logger.info("✅ Brand non-match added and saved successfully")
        return {"success": True, "message": "Brand non-match added successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to add brand non-match: {e}")
        raise


def save_scent_non_match(
    pipeline_brand: str, pipeline_scent: str, wsdb_scent: str
) -> dict[str, Any]:
    """Save same-brand scent non-match with duplicate checking.

    Args:
        pipeline_brand: Pipeline brand name
        pipeline_scent: Pipeline scent name
        wsdb_scent: WSDB scent name that doesn't match

    Returns:
        Dict with 'success' and 'message' keys
    """
    try:
        logger.info(
            f"➕ Adding scent non-match: {pipeline_brand} - {pipeline_scent} != {wsdb_scent}"
        )

        overrides_dir = get_non_matches_dir()
        overrides_dir.mkdir(parents=True, exist_ok=True)
        scents_file = overrides_dir / "non_matches_scents.yaml"

        # Load existing data
        scent_non_matches = {}
        if scents_file.exists():
            with scents_file.open("r", encoding="utf-8") as f:
                scent_non_matches = yaml.safe_load(f) or {}

        # Get canonical pair
        canonical_key, other_scent = _canonicalize_scent_pair(pipeline_scent, wsdb_scent)

        # Initialize if needed
        if pipeline_brand not in scent_non_matches:
            scent_non_matches[pipeline_brand] = {}
        if canonical_key not in scent_non_matches[pipeline_brand]:
            scent_non_matches[pipeline_brand][canonical_key] = []

        # Check for duplicate
        other_norm = normalize_for_matching(other_scent)
        if any(
            normalize_for_matching(nm) == other_norm
            for nm in scent_non_matches[pipeline_brand][canonical_key]
        ):
            logger.info("ℹ️ Non-match already exists, skipping")
            return {"success": True, "message": "Non-match already exists"}

        # Add the non-match
        scent_non_matches[pipeline_brand][canonical_key].append(other_scent)

        # Dedupe and canonicalize
        scent_non_matches = _dedupe_scent_non_matches(scent_non_matches)

        # Save atomically with sorting
        _atomic_write_yaml(scents_file, scent_non_matches, "scents")

        logger.info("✅ Scent non-match added and saved successfully")
        return {"success": True, "message": "Scent non-match added successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to add scent non-match: {e}")
        raise


def save_cross_brand_scent_non_match(
    entry1_brand: str, entry1_scent: str, entry2_brand: str, entry2_scent: str
) -> dict[str, Any]:
    """Save cross-brand scent non-match with duplicate checking.

    Args:
        entry1_brand: First entry brand name
        entry1_scent: First entry scent name
        entry2_brand: Second entry brand name
        entry2_scent: Second entry scent name

    Returns:
        Dict with 'success' and 'message' keys
    """
    try:
        logger.info(
            f"➕ Adding cross-brand scent non-match: {entry1_brand} - {entry1_scent} != {entry2_brand} - {entry2_scent}"
        )

        # Normalize for comparison
        brand1_norm = normalize_for_matching(entry1_brand)
        brand2_norm = normalize_for_matching(entry2_brand)
        scent1_norm = normalize_for_matching(entry1_scent)
        scent2_norm = normalize_for_matching(entry2_scent)

        overrides_dir = get_non_matches_dir()
        overrides_dir.mkdir(parents=True, exist_ok=True)
        scents_cross_brand_file = overrides_dir / "non_matches_scents_cross_brand.yaml"

        # Load existing data
        scent_cross_brand_non_matches = {}
        if scents_cross_brand_file.exists():
            with scents_cross_brand_file.open("r", encoding="utf-8") as f:
                scent_cross_brand_non_matches = yaml.safe_load(f) or {}

        # Get canonical scent key (alphabetically first)
        canonical_key = _canonicalize_cross_brand_scent_key(entry1_scent, entry2_scent)

        # Initialize if needed
        if canonical_key not in scent_cross_brand_non_matches:
            scent_cross_brand_non_matches[canonical_key] = []

        # Create brand-scent pairs for both entries
        entry1_pair = {"brand": entry1_brand, "scent": entry1_scent}
        entry2_pair = {"brand": entry2_brand, "scent": entry2_scent}

        # Check if entry1 is already in the group
        entry1_exists = any(
            normalize_for_matching(pair.get("brand", "")) == brand1_norm
            and normalize_for_matching(pair.get("scent", "")) == scent1_norm
            for pair in scent_cross_brand_non_matches[canonical_key]
        )

        # Check if entry2 is already in the group
        entry2_exists = any(
            normalize_for_matching(pair.get("brand", "")) == brand2_norm
            and normalize_for_matching(pair.get("scent", "")) == scent2_norm
            for pair in scent_cross_brand_non_matches[canonical_key]
        )

        # If both exist, they're already marked as non-matches
        if entry1_exists and entry2_exists:
            logger.info("ℹ️ Non-match already exists, skipping")
            return {"success": True, "message": "Non-match already exists"}

        # Add entries if they don't exist
        if not entry1_exists:
            scent_cross_brand_non_matches[canonical_key].append(entry1_pair)
        if not entry2_exists:
            scent_cross_brand_non_matches[canonical_key].append(entry2_pair)

        # Dedupe and canonicalize
        scent_cross_brand_non_matches = _dedupe_cross_brand_scent_non_matches(
            scent_cross_brand_non_matches
        )

        # Save atomically with sorting
        _atomic_write_yaml(
            scents_cross_brand_file, scent_cross_brand_non_matches, "scents_cross_brand"
        )

        logger.info("✅ Cross-brand scent non-match added and saved successfully")
        return {"success": True, "message": "Cross-brand scent non-match added successfully"}

    except Exception as e:
        logger.error(f"❌ Failed to add cross-brand scent non-match: {e}")
        raise
