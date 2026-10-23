"""Pattern compilation caching for brush matching strategies.

This module provides caching for compiled regex patterns to avoid redundant
compilation during BrushMatcher initialization. Since ProcessPoolExecutor reuses
worker processes, module-level caching within each process allows patterns to be
compiled once per worker and reused for subsequent months.
"""

import hashlib
import json
from typing import Any, Callable, Dict, List

# Module-level cache (per process)
# By-id fast path holds (catalog_ref, compiled) so the catalog dict stays alive:
# a live object's address can never be reused by a different object, so a stale
# id-keyed entry (freed catalog, address recycled by a new dict) is impossible.
_pattern_cache_by_id: Dict[tuple, tuple] = {}  # (id(catalog), pattern_type) -> (catalog, patterns)
_pattern_cache_by_hash: Dict[str, List[Dict[str, Any]]] = {}  # hash_key -> patterns


def _generate_cache_key(catalog_data: Dict[str, Any], pattern_type: str) -> str:
    """Generate a cache key from catalog data and pattern type.

    Args:
        catalog_data: The catalog data dictionary
        pattern_type: Type of pattern (e.g., "known_brush", "other_brush", "handle")

    Returns:
        Cache key string
    """
    # Create a stable hash of the catalog data
    # Sort keys to ensure consistent hashing regardless of dict iteration order
    catalog_str = json.dumps(catalog_data, sort_keys=True, default=str)
    catalog_hash = hashlib.md5(catalog_str.encode()).hexdigest()

    return f"{pattern_type}_{catalog_hash}"


def get_compiled_patterns(
    catalog_data: Dict[str, Any],
    pattern_type: str,
    compile_func: Callable[[Dict[str, Any]], List[Dict[str, Any]]],
) -> List[Dict[str, Any]]:
    """Get compiled patterns from cache or compile and cache.

    Optimized to use object identity for fast cache lookup, avoiding expensive
    hash generation on cache hits.

    Args:
        catalog_data: The catalog data to compile patterns from
        pattern_type: Type of pattern (e.g., "known_brush", "other_brush", "handle")
        compile_func: Function that compiles patterns from catalog data

    Returns:
        List of compiled patterns with metadata
    """
    # Fast path: Check cache by object identity first (O(1) dict lookup, no hashing).
    # The entry holds the catalog dict itself; require identity before serving so a
    # foreign/stale entry keyed by a reused address is never mistaken for a hit.
    id_key = (id(catalog_data), pattern_type)
    cached_entry = _pattern_cache_by_id.get(id_key)
    if cached_entry is not None and cached_entry[0] is catalog_data:
        return cached_entry[1]
    if cached_entry is not None:
        del _pattern_cache_by_id[id_key]

    # Slow path: Generate hash key and check content-based cache
    # (needed when same catalog data is passed as different dict objects)
    cache_key = _generate_cache_key(catalog_data, pattern_type)
    cached_patterns = _pattern_cache_by_hash.get(cache_key)
    if cached_patterns is not None:
        # Also cache by ID for future fast lookups
        _pattern_cache_by_id[id_key] = (catalog_data, cached_patterns)
        return cached_patterns

    # Cache miss: Compile patterns and cache them
    compiled = compile_func(catalog_data)
    _pattern_cache_by_hash[cache_key] = compiled
    _pattern_cache_by_id[id_key] = (catalog_data, compiled)
    return compiled


def clear_pattern_cache() -> None:
    """Clear the pattern cache. Useful for testing."""
    global _pattern_cache_by_id, _pattern_cache_by_hash
    _pattern_cache_by_id.clear()
    _pattern_cache_by_hash.clear()


def get_cache_stats() -> Dict[str, Any]:
    """Get cache statistics for debugging.

    Returns:
        Dictionary with cache statistics
    """
    return {
        "cache_size_by_id": len(_pattern_cache_by_id),
        "cache_size_by_hash": len(_pattern_cache_by_hash),
        "cache_keys_by_hash": list(_pattern_cache_by_hash.keys()),
    }
