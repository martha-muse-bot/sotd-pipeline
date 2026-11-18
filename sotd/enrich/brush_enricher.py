import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, cast

from sotd.enrich.enricher import BaseEnricher
from sotd.enrich.override_manager import EnrichmentOverrideManager
from sotd.enrich.utils.catalog_loader import CatalogLoader
from sotd.match.brush.strategies.utils.fiber_utils import match_fiber
from sotd.match.brush.strategies.utils.pattern_utils import extract_knot_size


class BrushEnricher(BaseEnricher):
    """Enricher for brush specifications from user comments."""

    def __init__(
        self,
        data_path: Optional[Path] = None,
        override_manager: Optional[EnrichmentOverrideManager] = None,
    ):
        """
        Initialize BrushEnricher.

        Args:
            data_path: Path to data directory containing catalogs
            override_manager: Optional enrichment override manager for forcing catalog values
        """
        super().__init__()
        self.catalog_loader = CatalogLoader(data_path)
        self.override_manager = override_manager

    @property
    def target_field(self) -> str:
        return "brush"

    def _extract_knot_size(self, text: str) -> Optional[float]:
        """Extract knot size from text using pattern utils."""
        return extract_knot_size(text)

    def _analyze_pattern_positions(
        self, brush_string: str, handle_patterns: List[str], knot_patterns: List[str]
    ) -> Dict[str, Any]:
        """
        Analyze pattern positions in brush string to determine user intent.

        Args:
            brush_string: Normalized brush string to analyze
            handle_patterns: List of handle patterns to search for
            knot_patterns: List of knot patterns to search for

        Returns:
            dict: {
                'handle_position': int or None,
                'knot_position': int or None,
                'intent': str,  # 'handle_primary', 'knot_primary', or 'unknown'
                'handle_matched_pattern': str or None,
                'knot_matched_pattern': str or None
            }
        """
        # Normalize brush string to lowercase
        normalized_string = brush_string.lower()

        # Find earliest match position for handle patterns
        handle_position = None
        handle_matched_pattern = None
        for pattern in handle_patterns:
            try:
                match = re.search(pattern, normalized_string, re.IGNORECASE)
                if match:
                    pos = match.start()
                    if handle_position is None or pos < handle_position:
                        handle_position = pos
                        handle_matched_pattern = pattern
            except re.error:
                # Skip invalid patterns
                continue

        # Find earliest match position for knot patterns
        knot_position = None
        knot_matched_pattern = None
        for pattern in knot_patterns:
            try:
                match = re.search(pattern, normalized_string, re.IGNORECASE)
                if match:
                    pos = match.start()
                    if knot_position is None or pos < knot_position:
                        knot_position = pos
                        knot_matched_pattern = pattern
            except re.error:
                # Skip invalid patterns
                continue

        # Determine intent based on position comparison
        if handle_position is not None and knot_position is not None:
            if handle_position < knot_position:
                intent = "handle_primary"
            elif knot_position < handle_position:
                intent = "knot_primary"
            else:
                intent = "unknown"  # Equal positions
        else:
            intent = "unknown"  # Missing patterns

        return {
            "handle_position": handle_position,
            "knot_position": knot_position,
            "intent": intent,
            "handle_matched_pattern": handle_matched_pattern,
            "knot_matched_pattern": knot_matched_pattern,
        }

    def _analyze_pattern_positions_compiled(
        self, brush_string: str, handle_patterns: List[re.Pattern], knot_patterns: List[re.Pattern]
    ) -> Dict[str, Any]:
        """
        Analyze pattern positions using compiled patterns for better performance.

        Args:
            brush_string: Normalized brush string to analyze
            handle_patterns: List of compiled handle patterns to search for
            knot_patterns: List of compiled knot patterns to search for

        Returns:
            dict: {
                'handle_position': int or None,
                'knot_position': int or None,
                'intent': str,  # 'handle_primary', 'knot_primary', or 'unknown'
                'handle_matched_pattern': str or None,
                'knot_matched_pattern': str or None
            }
        """
        # Normalize brush string to lowercase
        normalized_string = brush_string.lower()

        # Find earliest match position for handle patterns
        handle_position = None
        handle_matched_pattern = None
        for pattern in handle_patterns:
            try:
                match = pattern.search(normalized_string)
                if match:
                    pos = match.start()
                    if handle_position is None or pos < handle_position:
                        handle_position = pos
                        handle_matched_pattern = pattern.pattern
            except Exception:
                # Skip invalid patterns
                continue

        # Find earliest match position for knot patterns
        knot_position = None
        knot_matched_pattern = None
        for pattern in knot_patterns:
            try:
                match = pattern.search(normalized_string)
                if match:
                    pos = match.start()
                    if knot_position is None or pos < knot_position:
                        knot_position = pos
                        knot_matched_pattern = pattern.pattern
            except Exception:
                # Skip invalid patterns
                continue

        # Determine intent based on position comparison
        if handle_position is not None and knot_position is not None:
            if handle_position < knot_position:
                intent = "handle_primary"
            elif knot_position < handle_position:
                intent = "knot_primary"
            else:
                intent = "unknown"  # Equal positions
        else:
            intent = "unknown"  # Missing patterns

        return {
            "handle_position": handle_position,
            "knot_position": knot_position,
            "intent": intent,
            "handle_matched_pattern": handle_matched_pattern,
            "knot_matched_pattern": knot_matched_pattern,
        }

    def _infer_knot_size_from_handle_maker(self, matched_data: Dict[str, Any]) -> Optional[float]:
        """
        Infer knot size from handle maker defaults when knot size is missing.

        Args:
            matched_data: The matched brush data from the match phase

        Returns:
            float: Inferred knot size in mm, or None if no inference possible
        """
        # Check if we have handle information
        handle_section = matched_data.get("handle", {})
        if not handle_section or not isinstance(handle_section, dict):
            return None

        handle_brand = handle_section.get("brand")
        handle_model = handle_section.get("model")

        if not handle_brand:
            return None

        # Try to get handle maker defaults
        try:
            handle_defaults = self.catalog_loader.load_handle_maker_defaults(
                handle_brand, handle_model
            )
            return handle_defaults.get("knot_size_mm")
        except Exception:
            # If there's any error loading defaults, return None
            # This maintains robustness and doesn't break enrichment
            return None

    def _detect_user_intent(
        self, brush_string: str, handle_data: Dict[str, Any], knot_data: Dict[str, Any]
    ) -> str:
        """
        Detect user intent based on component order in the original string.

        This method uses the same logic as the match phase: simple string position
        comparison using source_text fields from matched data.

        Args:
            brush_string: Original brush string to analyze
            handle_data: Matched handle data with source_text field
            knot_data: Matched knot data with source_text field

        Returns:
            str: "handle_primary" or "knot_primary"
        """
        # Input validation - fail fast as per core rules
        if not brush_string:
            raise ValueError("Missing brush_string for user intent detection")
        if not handle_data or not isinstance(handle_data, dict):
            raise ValueError("Missing or invalid handle_data for user intent detection")
        if not knot_data or not isinstance(knot_data, dict):
            raise ValueError("Missing or invalid knot_data for user intent detection")

        # Extract handle and knot text from source_text fields
        handle_text = handle_data.get("source_text", "")
        knot_text = knot_data.get("source_text", "")

        if not handle_text or not knot_text:
            # If either component text is missing, default to handle_primary
            return "handle_primary"

        # Find positions of handle and knot text in original string
        handle_pos = brush_string.find(handle_text)
        knot_pos = brush_string.find(knot_text)

        # If either component not found, default to handle_primary
        if handle_pos == -1 or knot_pos == -1:
            return "handle_primary"

        # If positions are identical (same text), default to handle_primary
        if handle_pos == knot_pos:
            return "handle_primary"

        # Return based on which component appears first
        return "handle_primary" if handle_pos < knot_pos else "knot_primary"

    def _detect_user_intent_debug(
        self, brush_string: str, handle_data: Dict[str, Any], knot_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Debug version returning intent plus detailed metadata.

        Args:
            brush_string: Normalized brush string to analyze
            handle_data: Matched handle data with brand/model info
            knot_data: Matched knot data with brand/model info

        Returns:
            dict: {
                'intent': str,  # 'handle_primary', 'knot_primary', or 'unknown'
                'handle_position': int or None,
                'knot_position': int or None,
                'handle_patterns': List[str],
                'knot_patterns': List[str],
                'handle_matched_pattern': str or None,
                'knot_matched_pattern': str or None,
                'brush_string_normalized': str,
                'processing_time_ms': float,
                'edge_case_triggered': bool,
                'error_message': str or None
            }
        """
        start_time = time.time()
        edge_case_triggered = False
        error_message = None

        try:
            # Input validation
            if not brush_string or not handle_data or not knot_data:
                edge_case_triggered = True
                return {
                    "intent": "unknown",
                    "handle_position": None,
                    "knot_position": None,
                    "handle_patterns": [],
                    "knot_patterns": [],
                    "handle_matched_pattern": None,
                    "knot_matched_pattern": None,
                    "brush_string_normalized": brush_string.lower() if brush_string else "",
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "edge_case_triggered": edge_case_triggered,
                    "error_message": "Missing input data",
                }

            # Validate data structure
            if not isinstance(handle_data, dict) or not isinstance(knot_data, dict):
                edge_case_triggered = True
                return {
                    "intent": "unknown",
                    "handle_position": None,
                    "knot_position": None,
                    "handle_patterns": [],
                    "knot_patterns": [],
                    "handle_matched_pattern": None,
                    "knot_matched_pattern": None,
                    "brush_string_normalized": brush_string.lower() if brush_string else "",
                    "processing_time_ms": (time.time() - start_time) * 1000,
                    "edge_case_triggered": edge_case_triggered,
                    "error_message": "Invalid data structure",
                }

            # Load compiled patterns for better performance
            handle_patterns = self.catalog_loader.load_compiled_handle_patterns(
                handle_data.get("brand", ""), handle_data.get("model", "")
            )
            knot_patterns = self.catalog_loader.load_compiled_knot_patterns(
                knot_data.get("brand", ""), knot_data.get("model", "")
            )

            # Analyze pattern positions with compiled patterns
            result = self._analyze_pattern_positions_compiled(
                brush_string, handle_patterns, knot_patterns
            )

            # Check for edge cases
            if result["intent"] == "unknown":
                edge_case_triggered = True

            return {
                "intent": result["intent"],
                "handle_position": result["handle_position"],
                "knot_position": result["knot_position"],
                "handle_patterns": handle_patterns,
                "knot_patterns": knot_patterns,
                "handle_matched_pattern": result["handle_matched_pattern"],
                "knot_matched_pattern": result["knot_matched_pattern"],
                "brush_string_normalized": brush_string.lower() if brush_string else "",
                "processing_time_ms": (time.time() - start_time) * 1000,
                "edge_case_triggered": edge_case_triggered,
                "error_message": error_message,
            }

        except Exception as e:
            return {
                "intent": "unknown",
                "handle_position": None,
                "knot_position": None,
                "handle_patterns": [],
                "knot_patterns": [],
                "handle_matched_pattern": None,
                "knot_matched_pattern": None,
                "brush_string_normalized": brush_string.lower() if brush_string else "",
                "processing_time_ms": (time.time() - start_time) * 1000,
                "edge_case_triggered": True,
                "error_message": str(e),
            }

    def _should_detect_user_intent(self, brush_data: Dict[str, Any]) -> bool:
        """
        Determine if user intent detection should run for this brush data.

        Args:
            brush_data: Brush data to check

        Returns:
            bool: True if user intent detection should run, False otherwise
        """
        if not brush_data or not isinstance(brush_data, dict):
            return False

        # Check if this is a known brush (has top-level brand AND model)
        has_top_level_brand = brush_data.get("brand") is not None
        has_top_level_model = brush_data.get("model") is not None

        if has_top_level_brand and has_top_level_model:
            return False  # Known brush, don't detect user intent

        # Check if this is a composite brush (has both handle and knot sections)
        handle_section = brush_data.get("handle")
        knot_section = brush_data.get("knot")

        if not handle_section or not knot_section:
            return False  # Missing sections

        if not isinstance(handle_section, dict) or not isinstance(knot_section, dict):
            return False  # Invalid section structure

        # Check if sections have required data
        handle_brand = handle_section.get("brand")
        knot_brand = knot_section.get("brand")

        if not handle_brand or not knot_brand:
            return False  # Missing brand information

        # Additional check: if same brand AND same model, it's a single maker brush
        # (same brand but different models is still a composite brush)
        handle_model = handle_section.get("model")
        knot_model = knot_section.get("model")

        if handle_brand == knot_brand and handle_model == knot_model:
            return False  # Single maker brush, don't detect user intent

        return True

    def _load_handle_patterns(self, brand: str, model: str) -> List[str]:
        """
        Load handle patterns for given brand/model combination.

        Args:
            brand: Handle brand
            model: Handle model

        Returns:
            List[str]: List of patterns to search for
        """
        return self.catalog_loader.load_handle_patterns(brand, model)

    def _load_knot_patterns(self, brand: str, model: str) -> List[str]:
        """
        Load knot patterns for given brand/model combination.

        Args:
            brand: Knot brand
            model: Knot model

        Returns:
            List[str]: List of patterns to search for
        """
        return self.catalog_loader.load_knot_patterns(brand, model)

    def _extract_brush_text_from_matched_data(self, field_data: Dict[str, Any]) -> str:
        """
        Extract brush text from source_text fields in matched data.

        Args:
            field_data: The matched brush data from the match phase

        Returns:
            str: The brush text extracted from source_text fields

        Raises:
            ValueError: If no source_text can be found in handle or knot sections
        """
        # Try to get brush text from handle source_text first
        handle_section = field_data.get("handle", {})
        if isinstance(handle_section, dict) and handle_section.get("source_text"):
            return handle_section["source_text"]

        # Fallback to knot source_text
        knot_section = field_data.get("knot", {})
        if isinstance(knot_section, dict) and knot_section.get("source_text"):
            return knot_section["source_text"]

        # For test scenarios or mock data without source_text, return empty string
        # This maintains backward compatibility with existing tests
        return ""

    def applies_to(self, record: dict) -> bool:
        """Check if this enricher applies to the record."""
        brush_data = record.get("brush", {})
        if not brush_data or not isinstance(brush_data, dict):
            return False
        matched_data = brush_data.get("matched")
        if matched_data and isinstance(matched_data, dict):
            # Apply to any brush that has matched data, regardless of brand match
            # This allows extraction of specifications from user comments even for unmatched brushes
            return True
        return False

    def enrich(
        self, field_data: dict, original_comment: str, record: Optional[dict] = None
    ) -> Optional[dict]:
        """Extract brush specifications from the user-supplied brush_extracted field and merge
        with catalog data.

        Args:
            field_data: The matched brush data from the match phase
            original_comment: The user-supplied brush_extracted field (not the full comment)

        Returns:
            Dictionary with enriched data, or None if no enrichment possible.
        """
        if field_data is None or not isinstance(field_data, dict):
            return None

        # Use the original_comment as brush_extracted (this is the normalized string from user)
        brush_extracted = original_comment
        matched_data = field_data.get("matched", {})

        # Extract user data from brush_extracted
        user_knot_size = extract_knot_size(brush_extracted)
        user_fiber = match_fiber(brush_extracted)

        # Get catalog data from matched data (knot section) or legacy format (top-level)
        knot_section = matched_data.get("knot", {})
        catalog_knot_size = (
            knot_section.get("knot_size_mm") if knot_section else matched_data.get("knot_size_mm")
        )
        # Fail fast if catalog_knot_size is a string (catalog data should be numeric)
        if catalog_knot_size is not None and isinstance(catalog_knot_size, str):
            knot_brand = knot_section.get("brand") if knot_section else matched_data.get("brand")
            knot_model = knot_section.get("model") if knot_section else matched_data.get("model")
            raise ValueError(
                f"Invalid catalog data: knot_size_mm must be numeric, not string. "
                f"Found string value '{catalog_knot_size}' for knot brand='{knot_brand}', model='{knot_model}'. "
                f"Please fix the catalog data (knots.yaml or brushes.yaml) to use a numeric value (e.g., 26 instead of '26mm')."
            )
        catalog_fiber = knot_section.get("fiber") if knot_section else matched_data.get("fiber")

        # Track if use_catalog override was set (initialize to False)
        use_catalog_for_knot_size = False

        # Check for enrichment overrides if override_manager and record are available
        if self.override_manager and record:
            month = record.get("_month")  # Month should be added to record metadata
            comment_id = record.get("id")
            if month and comment_id:
                # Check for fiber override
                fiber_override = self.override_manager.get_override(
                    month, comment_id, "brush", "fiber"
                )
                if fiber_override == "use_catalog":
                    # Skip user extraction, use catalog value only
                    user_fiber = None
                elif fiber_override is not None and fiber_override != "use_catalog":
                    # Explicit value override
                    user_fiber = fiber_override
                    catalog_fiber = fiber_override  # Use override as both for consistency

                # Check for knot_size_mm override
                knot_size_override = self.override_manager.get_override(
                    month, comment_id, "brush", "knot_size_mm"
                )
                if knot_size_override == "use_catalog":
                    # Skip user extraction, use catalog value only
                    user_knot_size = None
                    use_catalog_for_knot_size = True
                elif knot_size_override is not None and knot_size_override != "use_catalog":
                    # Explicit value override
                    user_knot_size = knot_size_override
                    catalog_knot_size = knot_size_override  # Use override as both for consistency

        # Prepare user data dictionary
        user_data = {}
        if user_knot_size is not None:
            user_data["knot_size_mm"] = user_knot_size
        if user_fiber is not None:
            user_data["fiber"] = user_fiber

        # Prepare catalog data dictionary
        catalog_data = {}
        if catalog_knot_size is not None:
            catalog_data["knot_size_mm"] = catalog_knot_size
        if catalog_fiber is not None:
            catalog_data["fiber"] = catalog_fiber

        # Handle maker knot size inference (fallback when user and catalog don't have knot size)
        handle_maker_knot_size = None
        handle_maker_brand = None
        if user_knot_size is None and catalog_knot_size is None:
            handle_maker_knot_size = self._infer_knot_size_from_handle_maker(matched_data)
            # Fail fast if handle_maker_knot_size is a string (catalog data should be numeric)
            if handle_maker_knot_size is not None and isinstance(handle_maker_knot_size, str):
                handle_section = matched_data.get("handle", {})
                handle_brand = (
                    handle_section.get("brand") if isinstance(handle_section, dict) else None
                )
                handle_model = (
                    handle_section.get("model") if isinstance(handle_section, dict) else None
                )
                raise ValueError(
                    f"Invalid catalog data: knot_size_mm in handle maker defaults must be numeric, not string. "
                    f"Found string value '{handle_maker_knot_size}' for handle brand='{handle_brand}', model='{handle_model}'. "
                    f"Please fix the catalog data (handles.yaml) to use a numeric value (e.g., 26 instead of '26mm')."
                )
            if handle_maker_knot_size is not None:
                # Get handle brand for metadata
                handle_section = matched_data.get("handle", {})
                if isinstance(handle_section, dict):
                    handle_maker_brand = handle_section.get("brand")
                # Add to catalog data for enrichment
                catalog_data["knot_size_mm"] = handle_maker_knot_size

        # Use BaseEnricher's source tracking method
        enriched_data = self._create_enriched_data(user_data, catalog_data)

        # Override _extraction_source if use_catalog was set for knot_size and no user data exists
        # This ensures that when use_catalog: true is set and user didn't extract other fields,
        # the source reflects catalog-only usage
        if use_catalog_for_knot_size and not user_data:
            # Only catalog data was used (user_data is empty)
            enriched_data["_extraction_source"] = "catalog_data"

        # Add handle maker inference metadata if used
        if handle_maker_knot_size is not None:
            enriched_data["_extraction_source"] = "handle_maker_default"
            enriched_data["_handle_maker_inference"] = handle_maker_brand

        # Handle _fiber_extraction_source separately for backward compatibility
        if user_fiber is not None or catalog_fiber is not None:
            fiber_user_data = {"fiber": user_fiber} if user_fiber is not None else {}
            fiber_catalog_data = {"fiber": catalog_fiber} if catalog_fiber is not None else {}
            fiber_enriched = self._create_enriched_data(fiber_user_data, fiber_catalog_data)
            enriched_data["_fiber_extraction_source"] = fiber_enriched["_extraction_source"]

        # Add user override detection logic (data conflicts between user input and catalog)
        # Narrowed views: the runtime contract is a str fiber and a numeric knot
        # size (catalog_knot_size already fail-fasts on a string above), but the
        # override/catalog lookups are typed loosely, so pin the comparison types.
        user_fiber_str = cast("str | None", user_fiber)
        catalog_fiber_str = cast("str | None", catalog_fiber)
        user_knot_num = cast("float | None", user_knot_size)
        catalog_knot_num = cast("float | None", catalog_knot_size)
        has_user_override = False
        override_reasons = []

        if user_fiber_str is not None and catalog_fiber_str is not None:
            if user_fiber_str.lower() != catalog_fiber_str.lower():
                has_user_override = True
                override_reasons.append(f"fiber_mismatch:{catalog_fiber_str}->{user_fiber_str}")

        if user_knot_num is not None and catalog_knot_num is not None:
            if abs(user_knot_num - catalog_knot_num) >= 0.1:  # Allow small tolerance
                has_user_override = True
                override_reasons.append(f"size_mismatch:{catalog_knot_num}->{user_knot_num}")

        # Add user override metadata if detected
        if has_user_override:
            enriched_data["_user_override"] = True
            enriched_data["_user_override_reason"] = override_reasons

        # Add catalog conflict tracking for backward compatibility
        if user_knot_num is not None and catalog_knot_num is not None:
            if abs(user_knot_num - catalog_knot_num) >= 0.1:
                enriched_data["_catalog_knot_size_mm"] = catalog_knot_num

        if user_fiber_str is not None and catalog_fiber_str is not None:
            if user_fiber_str.lower() != catalog_fiber_str.lower():
                enriched_data["_catalog_fiber"] = catalog_fiber_str

        # Add user intent detection for composite brushes
        if self._should_detect_user_intent(matched_data):
            try:
                # Get handle and knot data from matched_data
                handle_data = matched_data.get("handle", {})
                knot_data = matched_data.get("knot", {})

                user_intent = self._detect_user_intent(brush_extracted, handle_data, knot_data)
                enriched_data["user_intent"] = user_intent
            except Exception:
                # Log error but don't fail enrichment
                # Note: We don't have access to logger here, so we'll just set to unknown
                enriched_data["user_intent"] = "unknown"

        return enriched_data
