"""
API endpoint for brush matching analyzer.

This endpoint provides a web interface to the brush matching analysis tool,
allowing users to test brush strings and see detailed scoring results.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import SOTD modules - will be handled in the function

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/brushes/matching", tags=["brushes", "matching"])


class BrushAnalysisRequest(BaseModel):
    brushString: str
    bypass_correct_matches: bool = False


class BrushMatchResult(BaseModel):
    strategy: str
    score: float
    matchType: str
    pattern: str
    scoreBreakdown: Dict[str, Any]
    matchedData: Dict[str, Any]
    componentDetails: Optional[Dict[str, Any]] = None
    splitInformation: Optional[Dict[str, Any]] = None


class InputParsing(BaseModel):
    """Fiber and knot size parsed from the raw input string (not catalog defaults)."""

    fiber: Optional[str] = None
    knot_size_mm: Optional[float] = None


class BrushAnalysisResponse(BaseModel):
    results: List[BrushMatchResult]
    winner: BrushMatchResult
    enrichedData: Dict[str, Any] = {}
    inputParsing: InputParsing = InputParsing()


def _get_modifier_description(modifier_name: str, modifier_value: float, brush_string: str) -> str:
    """
    Helper function to generate a user-friendly description for a modifier.
    """
    if modifier_name == "knot_indicators":
        if modifier_value > 0:
            # Look for fiber words in the input
            fiber_words = [
                "badger",
                "boar",
                "synthetic",
                "syn",
                "nylon",
                "plissoft",
                "tuxedo",
                "cashmere",
                "mixed",
                "timberwolf",
            ]
            found_words = [word for word in fiber_words if word.lower() in brush_string.lower()]
            if found_words:
                return f"Fiber type detected: {', '.join(found_words)}"
            else:
                return "Knot indicators detected"
        return "Knot indicators"

    elif modifier_name == "handle_indicators":
        if modifier_value > 0:
            # Look for handle-related words
            handle_words = [
                "handle",
                "wood",
                "resin",
                "acrylic",
                "metal",
                "brass",
                "aluminum",
                "steel",
                "titanium",
                "ebonite",
                "ivory",
                "horn",
                "bone",
                "stone",
                "marble",
                "granite",
            ]
            found_words = [word for word in handle_words if word.lower() in brush_string.lower()]
            if found_words:
                return f"Handle material detected: {', '.join(found_words)}"
            else:
                return "Handle indicators detected"
        return "Handle indicators"

    elif modifier_name == "fiber_mismatch":
        return "Fiber type mismatch between input and catalog"

    elif modifier_name == "size_specification":
        if modifier_value > 0:
            # Look for size specifications
            import re

            size_patterns = [r"\b\d+mm\b", r"\b\d+\s*mm\b", r"\b\d+x\d+\b", r"\b\d+\s*x\s*\d+\b"]
            for pattern in size_patterns:
                match = re.search(pattern, brush_string.lower())
                if match:
                    return f"Size specification detected: {match.group()}"
            return "Size specification detected"
        return "Size specification"

    elif modifier_name == "multiple_brands":
        return "Multiple brands detected"

    elif modifier_name == "high_confidence":
        return "High confidence delimiter used"

    elif modifier_name == "delimiter_confidence":
        return "High confidence delimiter detected"

    elif modifier_name == "dual_component":
        return "Both handle and knot components matched"

    elif modifier_name == "handle_brand_without_knot_brand":
        return "Handle brand detected without knot brand"

    elif modifier_name == "knot_brand_without_handle_brand":
        return "Knot brand detected without handle brand"

    elif modifier_name == "same_brand":
        if modifier_value > 0:
            return "Handle and knot share the same brand (penalty)"
        else:
            return "Handle and knot have different brands"

    elif modifier_name == "neither_brand":
        return "Neither handle nor knot has a brand detected"

    else:
        return f"Modifier: {modifier_name}"


def _extract_component_details(strategy_result, strategy_name: str) -> Optional[Dict[str, Any]]:
    """Extract component details for strategies that support component analysis."""
    if not strategy_result or not hasattr(strategy_result, "matched"):
        return None

    matched_data = strategy_result.matched or {}

    # Only provide component details for strategies that support them
    if strategy_name not in [
        "automated_split",
        "full_input_component_matching",
        "known_split",
    ]:
        return None

    component_details = {}

    # Extract handle component details
    if "handle" in matched_data and matched_data["handle"]:
        handle = matched_data["handle"]
        handle_breakdown = _calculate_handle_score_breakdown(handle)
        handle_score = sum(handle_breakdown.values())
        component_details["handle"] = {
            "score": handle_score,
            "breakdown": handle_breakdown,
            "metadata": {
                "brand": handle.get("brand"),
                "model": handle.get("model"),
                "source": handle.get("source_text", ""),
            },
            "patterns": {
                "brand_pattern": handle.get("_pattern"),
                "model_pattern": handle.get("_pattern"),
                "handle_pattern": handle.get("_pattern"),
                "source": handle.get("source_text", ""),
            },
        }

    # Extract knot component details
    if "knot" in matched_data and matched_data["knot"]:
        knot = matched_data["knot"]
        knot_breakdown = _calculate_knot_score_breakdown(knot)
        knot_score = sum(knot_breakdown.values())
        # Get pattern from knot data, fallback to None if not available
        knot_pattern = knot.get("_pattern") or knot.get("_pattern_used") or knot.get("pattern")
        component_details["knot"] = {
            "score": knot_score,
            "breakdown": knot_breakdown,
            "metadata": {
                "brand": knot.get("brand"),
                "model": knot.get("model"),
                "fiber": knot.get("fiber"),
                "source": knot.get("source_text", ""),
            },
            "patterns": {
                "brand_pattern": knot_pattern,
                "model_pattern": knot_pattern,
                "fiber_pattern": knot_pattern,
                "size_pattern": knot_pattern,
                "source": knot.get("source_text", ""),
            },
        }

    return component_details if component_details else None


def _calculate_handle_score_breakdown(handle_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate detailed breakdown of handle component score."""
    breakdown = {}

    # Brand match (5 points)
    if handle_data.get("brand"):
        breakdown["brand_match"] = 5.0
    else:
        breakdown["brand_match"] = 0.0

    # Model match (5 points)
    if handle_data.get("model"):
        breakdown["model_match"] = 5.0
    else:
        breakdown["model_match"] = 0.0

    # Handle indicators (look for handle-related terms)
    handle_indicators = 0.0
    source_text = handle_data.get("source_text", "").lower()
    handle_terms = [
        "handle",
        "wood",
        "resin",
        "acrylic",
        "metal",
        "brass",
        "aluminum",
        "steel",
        "titanium",
        "ebonite",
        "ivory",
        "horn",
        "bone",
        "stone",
        "marble",
        "granite",
    ]
    for term in handle_terms:
        if term in source_text:
            handle_indicators += 2.0
            break  # Only count once

    breakdown["handle_indicators"] = handle_indicators

    # Priority bonus (2 points for priority 1, 1 point for priority 2)
    priority = handle_data.get("priority")
    if priority == 1:
        breakdown["priority_score"] = 2.0
    elif priority == 2:
        breakdown["priority_score"] = 1.0
    else:
        breakdown["priority_score"] = 0.0

    return breakdown


def _calculate_knot_score_breakdown(knot_data: Dict[str, Any]) -> Dict[str, float]:
    """Calculate detailed breakdown of knot component score."""
    breakdown = {}

    # Brand match (5 points)
    if knot_data.get("brand"):
        breakdown["brand_match"] = 5.0
    else:
        breakdown["brand_match"] = 0.0

    # Model match (5 points)
    if knot_data.get("model"):
        breakdown["model_match"] = 5.0
    else:
        breakdown["model_match"] = 0.0

    # Fiber match (5 points)
    if knot_data.get("fiber"):
        breakdown["fiber_match"] = 5.0
    else:
        breakdown["fiber_match"] = 0.0

    # Size match (2 points)
    if knot_data.get("knot_size_mm"):
        breakdown["size_match"] = 2.0
    else:
        breakdown["size_match"] = 0.0

    # Knot indicators (look for knot-related terms)
    knot_indicators = 0.0
    source_text = knot_data.get("source_text", "").lower()
    knot_terms = ["syn", "mm", "knot", "badger", "boar", "synthetic", "fiber"]
    for term in knot_terms:
        if term in source_text:
            knot_indicators += 2.0

    # Cap knot indicators at 10 points
    knot_indicators = min(knot_indicators, 10.0)
    breakdown["knot_indicators"] = knot_indicators

    # Priority bonus (2 points for priority 1, 1 point for priority 2)
    priority = knot_data.get("priority")
    if priority == 1:
        breakdown["priority_score"] = 2.0
    elif priority == 2:
        breakdown["priority_score"] = 1.0
    else:
        breakdown["priority_score"] = 0.0

    return breakdown


def _extract_split_information(strategy_result, strategy_name: str) -> Optional[Dict[str, Any]]:
    """Extract split information for strategies that split brush strings."""
    if not strategy_result or not hasattr(strategy_result, "matched"):
        return None

    matched_data = strategy_result.matched or {}

    # Only provide split information for strategies that split
    if strategy_name not in [
        "automated_split",
        "full_input_component_matching",
        "known_split",
    ]:
        return None

    # Extract split information from matched data
    split_info = {}

    if "handle" in matched_data and matched_data["handle"]:
        split_info["handleText"] = matched_data["handle"].get("source_text", "")

    if "knot" in matched_data and matched_data["knot"]:
        split_info["knotText"] = matched_data["knot"].get("source_text", "")

    # Add split priority if available
    if hasattr(strategy_result, "split_priority"):
        split_info["splitPriority"] = strategy_result.split_priority
    elif strategy_name == "automated_split":
        split_info["splitPriority"] = "medium"  # Default for automated split

    return split_info if split_info else None


@router.post("/analyze", response_model=BrushAnalysisResponse)
async def analyze_brush(request: BrushAnalysisRequest) -> BrushAnalysisResponse:
    """
    Analyze a brush string and return detailed scoring results.

    Args:
        request: Contains the brush string to analyze and bypass option

    Returns:
        Detailed analysis results including all strategies and scores
    """
    try:
        # Import SOTD modules inside the function to avoid linter issues
        import sys
        from pathlib import Path

        # Add the parent directory to Python path to import SOTD modules
        parent_dir = Path(__file__).parent.parent.parent
        sys.path.insert(0, str(parent_dir))

        # Change to the parent directory where the data files are located
        import os

        original_cwd = os.getcwd()
        os.chdir(parent_dir)

        try:
            # Clear ALL caches to ensure fresh data on every analysis
            from sotd.match.base_matcher import clear_catalog_cache
            from sotd.match.brush.matcher import clear_brush_catalog_cache
            from sotd.match.loaders import clear_yaml_cache

            clear_catalog_cache()
            clear_yaml_cache()
            clear_brush_catalog_cache()
            logger.info("Cleared all catalog caches for fresh data")

            # Use the brush matcher directly
            from sotd.match.brush_matcher import BrushMatcher

            matcher = BrushMatcher()

            def transform_brush_data(flat_data: dict) -> dict:
                """Transform flat brush data into nested handle/knot structure."""
                if not flat_data:
                    return {}

                # Check if this is an automated_split result with handle/knot sections
                if "handle" in flat_data and "knot" in flat_data:
                    # This is already in the correct nested structure
                    return {
                        "brand": flat_data.get("brand"),
                        "model": flat_data.get("model"),
                        "handle": {
                            "brand": flat_data["handle"].get("brand"),
                            "model": flat_data["handle"].get("model"),
                            "source_text": flat_data["handle"].get("source_text"),
                        },
                        "knot": {
                            "brand": flat_data["knot"].get("brand"),
                            "model": flat_data["knot"].get("model"),
                            "fiber": flat_data["knot"].get("fiber"),
                            "knot_size_mm": flat_data["knot"].get("knot_size_mm"),
                            "source_text": flat_data["knot"].get("source_text"),
                        },
                    }

                # Check if this is simple flat data (like other_brush strategy)
                # that already has brand, model, fiber in the correct format
                if (
                    flat_data.get("brand")
                    and flat_data.get("model")
                    and not flat_data.get("handle_maker")
                ):
                    # This is already in the correct flat format, add empty handle/knot sections
                    return {
                        "brand": flat_data.get("brand"),
                        "model": flat_data.get("model"),
                        "fiber": flat_data.get("fiber"),
                        "knot_size_mm": flat_data.get("knot_size_mm"),
                        "handle": {
                            "brand": None,
                            "model": None,
                            "source_text": "",
                        },
                        "knot": {
                            "brand": None,
                            "model": None,
                            "fiber": flat_data.get("fiber"),
                            "knot_size_mm": flat_data.get("knot_size_mm"),
                            "source_text": "",
                        },
                    }

                # Extract handle information - use handle_maker as brand,
                # try to extract handle model
                handle_brand = flat_data.get("handle_maker")
                handle_model = flat_data.get("handle_model")

                # Try to extract handle model from source_text if available
                source_text = flat_data.get("source_text", "")
                if not handle_model and source_text and "/" in source_text:
                    # Extract handle part before "/"
                    handle_part = source_text.split("/")[0].strip()
                    handle_model = handle_part if handle_part else None

                handle_data = {
                    "brand": handle_brand,
                    "model": handle_model,
                    "source_text": (
                        flat_data.get("_original_handle_text")
                        or (source_text.split("/")[0].strip() if "/" in source_text else "")
                    ),
                }

                # Extract knot information - use fiber and knot_size_mm from flat data
                knot_brand = flat_data.get("knot_brand") or flat_data.get("brand")
                knot_model = flat_data.get("knot_model") or flat_data.get("model")

                # Try to extract knot info from source_text if available
                knot_source_text = ""
                if source_text and "*" in source_text:
                    # Extract part after "*" as knot info
                    knot_part = source_text.split("*")[-1].strip()
                    knot_source_text = knot_part if knot_part else ""

                knot_data = {
                    "brand": knot_brand,
                    "model": knot_model,
                    "fiber": flat_data.get("fiber"),
                    "knot_size_mm": flat_data.get("knot_size_mm"),
                    "source_text": (flat_data.get("_original_knot_text") or knot_source_text),
                }

                # Create nested structure
                return {
                    "brand": flat_data.get("brand"),
                    "model": flat_data.get("model"),
                    "handle": handle_data,
                    "knot": knot_data,
                }

            # Use the matcher's built-in bypass functionality
            result = matcher.match(
                request.brushString, bypass_correct_matches=request.bypass_correct_matches
            )

            # Convert to expected format
            if result and hasattr(result, "all_strategies"):
                analysis_result = {
                    "all_strategies": result.all_strategies,
                    "enriched_data": result.matched if result.matched else {},
                }
            else:
                # Fallback if no results
                analysis_result = {"all_strategies": [], "enriched_data": {}}
        finally:
            # Restore original working directory
            os.chdir(original_cwd)

        # Check for errors
        if "error" in analysis_result:
            raise HTTPException(
                status_code=500, detail=f"Analysis failed: {analysis_result['error']}"
            )

        # Format results for the API response
        formatted_results = []

        # Get strategies from analysis result
        strategies = analysis_result.get("all_strategies", []) or []

        # Process all strategy results
        for strategy_result in strategies:
            # The new matcher now provides full MatchResult objects with complete data
            # Initialize strategy_name early to avoid unbound variable in exception handler
            strategy_name = "unknown"
            try:
                # Extract data from the MatchResult object
                strategy_name = strategy_result.strategy or "unknown"
                match_type = strategy_result.match_type or "unknown"
                pattern = strategy_result.pattern or "unknown"
                matched_data = strategy_result.matched or {}

                # Transform flat brush data to nested structure for React component
                transformed_matched_data = transform_brush_data(matched_data)

                # Use the actual score from the matched data, which contains the
                # strategy's calculated score. This is more reliable than
                # strategy_result.score which may be modified by the scoring engine
                total_score = 0.0
                if matched_data and isinstance(matched_data, dict) and "score" in matched_data:
                    total_score = matched_data["score"] or 0.0
                elif strategy_result.score is not None:
                    # Fallback to strategy_result.score if no score in matched data
                    total_score = strategy_result.score

                # Get detailed scoring breakdown using the ScoringEngine
                from sotd.match.brush.config import BrushScoringConfig
                from sotd.match.brush.scoring.engine import ScoringEngine

                config_path = (
                    Path(__file__).parent.parent.parent / "data" / "brush_scoring_config.yaml"
                )
                config = BrushScoringConfig(config_path=config_path)
                engine = ScoringEngine(config)

                # Calculate base score and modifiers for breakdown display
                base_score = engine.config.get_base_strategy_score(strategy_name)

                modifier_score = engine._calculate_modifiers(
                    strategy_result, request.brushString, strategy_name
                )
                # Use actual score as total, but keep base_score and modifier_score for breakdown

                # Get modifier details
                modifier_details = []
                modifier_names = config.get_all_modifier_names(strategy_name)

                for modifier_name in modifier_names:
                    modifier_weight = config.get_strategy_modifier(strategy_name, modifier_name)
                    if modifier_weight:
                        # Calculate the actual modifier value using the scoring engine
                        modifier_function = getattr(engine, f"_modifier_{modifier_name}", None)
                        modifier_value = 0.0  # Default value

                        if modifier_function and callable(modifier_function):
                            modifier_value = modifier_function(
                                request.brushString, strategy_result, strategy_name
                            )

                            # Ensure modifier_value is numeric for multiplication
                            if isinstance(modifier_value, (int, float)):
                                actual_modifier_score = modifier_value * modifier_weight
                            else:
                                actual_modifier_score = modifier_weight
                        else:
                            # If no modifier function exists, just use the weight directly
                            actual_modifier_score = modifier_weight

                        # Only include modifiers with non-zero calculated score
                        # This prevents showing 0.0 modifiers in the UI
                        if actual_modifier_score != 0.0:
                            modifier_details.append(
                                {
                                    "name": modifier_name,
                                    "weight": actual_modifier_score,  # Use calculated value
                                    "description": _get_modifier_description(
                                        modifier_name, modifier_value, request.brushString
                                    ),
                                }
                            )

                # Create the formatted result
                formatted_result = BrushMatchResult(
                    strategy=strategy_name,
                    score=total_score,
                    matchType=match_type,
                    pattern=pattern,
                    scoreBreakdown={
                        "baseScore": base_score,
                        "modifiers": modifier_score,
                        "modifierDetails": modifier_details,
                        "total": total_score,
                    },
                    matchedData=transformed_matched_data,
                    # Add component details for strategies that support them
                    componentDetails=_extract_component_details(strategy_result, strategy_name),
                    # Add split information for strategies that split brush strings
                    splitInformation=_extract_split_information(strategy_result, strategy_name),
                )

                formatted_results.append(formatted_result)

            except Exception as e:
                # Fail fast - let the exception bubble up
                raise Exception(f"Error processing strategy {strategy_name}: {str(e)}") from e

        # If no strategies, create a basic result
        if not formatted_results:
            basic_matching = analysis_result.get("analysis_summary", {}).get("basic_matching", {})
            formatted_result = BrushMatchResult(
                strategy="basic_matcher",
                score=0.0,
                matchType=basic_matching.get("match_type", "unknown"),
                pattern=basic_matching.get("pattern", "unknown"),
                scoreBreakdown={"baseScore": 0.0, "modifiers": 0.0, "modifierDetails": []},
                matchedData=basic_matching.get("matched", {}),
            )
            formatted_results.append(formatted_result)

        # Find the winner (highest score among valid results)
        # Filter out results with no valid matches, just like the pipeline does
        valid_results = [
            r
            for r in formatted_results
            if r.matchedData
            and (
                r.matchedData.get("brand")
                or r.matchedData.get("handle")
                or r.matchedData.get("knot")
            )
        ]

        # If no valid results but we have enriched data, create a winner from enriched data
        if not valid_results and analysis_result.get("enriched_data"):
            enriched_data = analysis_result.get("enriched_data", {})
            # Create a winner result from enriched data
            winner = BrushMatchResult(
                strategy=enriched_data.get("strategy", "correct_matches"),
                score=100.0,  # High score for correct matches
                matchType=enriched_data.get("_pattern", "exact"),
                pattern=enriched_data.get("_pattern", "exact_match"),
                scoreBreakdown={"baseScore": 100.0, "modifiers": 0.0, "modifierDetails": []},
                matchedData=transform_brush_data(enriched_data),
            )
        else:
            winner = (
                max(valid_results, key=lambda x: x.score)
                if valid_results
                else max(formatted_results, key=lambda x: x.score)
            )

        # Get enriched data
        enriched_data = analysis_result.get("enriched_data", {})

        # Parse fiber / knot size from the raw input (independent of catalog match)
        from sotd.match.brush.strategies.utils.fiber_utils import match_fiber
        from sotd.match.brush.strategies.utils.knot_size_utils import parse_knot_size

        input_parsing = InputParsing(
            fiber=match_fiber(request.brushString),
            knot_size_mm=parse_knot_size(request.brushString),
        )

        return BrushAnalysisResponse(
            results=formatted_results,
            winner=winner,
            enrichedData=enriched_data,
            inputParsing=input_parsing,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy", "service": "brush_matching_analyzer"}
