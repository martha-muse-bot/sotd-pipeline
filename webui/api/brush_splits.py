"""
Brush Split Validator API endpoints for loading, saving, and managing brush string splits.

This module provides REST API endpoints for the Brush Split Validator web UI,
including data loading, YAML file management, and statistics calculation.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Get logger for this module
logger = logging.getLogger(__name__)


class BrushSplitError(Exception):
    """Base exception for brush split operations."""

    pass


class FileNotFoundError(BrushSplitError):
    """Raised when a required file is not found."""

    pass


class DataCorruptionError(BrushSplitError):
    """Raised when data is corrupted or invalid."""

    pass


class ValidationError(BrushSplitError):
    """Raised when validation fails."""

    pass


class ProcessingError(BrushSplitError):
    """Raised when data processing fails."""

    pass


# Create router for brush split endpoints
router = APIRouter(prefix="/api/brushes/splits", tags=["brushes", "splits"])


def normalize_brush_string(brush_string: str) -> Optional[str]:
    """Normalize a brush string for consistent processing.

    Args:
        brush_string: The raw brush string from matched data

    Returns:
        Normalized brush string or None if invalid
    """
    if not brush_string or not brush_string.strip():
        return None

    # Basic normalization
    normalized = brush_string.strip()

    # Remove common prefixes/suffixes that don't add value
    normalized = re.sub(r"^(brush|b):\s*", "", normalized, flags=re.IGNORECASE)
    normalized = re.sub(r"\s+", " ", normalized)  # Normalize whitespace

    return normalized if normalized else None


class ConfidenceLevel(Enum):
    """Confidence levels for brush string splits."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ValidationStatus(Enum):
    """Validation status for brush splits."""

    UNVALIDATED = "unvalidated"
    VALIDATED = "validated"
    CORRECTED = "corrected"


@dataclass
class BrushSplitOccurrence:
    """Represents an occurrence of a brush string in a specific file."""

    file: str
    comment_ids: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {"file": self.file, "comment_ids": self.comment_ids}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BrushSplitOccurrence":
        """Create from dictionary."""
        return cls(file=data["file"], comment_ids=data.get("comment_ids", []))


@dataclass
class BrushSplit:
    """Represents a validated brush string split."""

    original: str
    handle: Optional[str]
    knot: Optional[str]  # Can be None when should_not_split is True
    match_type: Optional[str] = None
    corrected: bool = False  # Whether this split was corrected (changed)
    validated_at: Optional[str] = None  # ISO timestamp when validated
    system_handle: Optional[str] = None
    system_knot: Optional[str] = None
    system_confidence: Optional[ConfidenceLevel] = None
    system_reasoning: Optional[str] = None
    occurrences: List[BrushSplitOccurrence] = field(default_factory=list)
    should_not_split: bool = False

    @property
    def validated(self) -> bool:
        """Return True if this split has been validated (has a validated_at timestamp)."""
        return self.validated_at is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "original": self.original,  # Include for API responses
            "handle": self.handle,
            "knot": self.knot,
            "match_type": self.match_type,
            "corrected": self.corrected,
            "validated": self.validated,  # Include validated property
            "validated_at": self.validated_at,
            "should_not_split": self.should_not_split,  # Include for API responses
            "occurrences": [occ.to_dict() for occ in self.occurrences],
        }

        # Only include system fields if corrected
        if self.corrected:
            result.update(
                {
                    "system_handle": self.system_handle,
                    "system_knot": self.system_knot,
                    "system_confidence": (
                        self.system_confidence.value if self.system_confidence else None
                    ),
                    "system_reasoning": self.system_reasoning,
                }
            )

        return result

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for YAML serialization (without original field)."""
        result = {
            "handle": self.handle,
            "knot": self.knot,
            "match_type": self.match_type,
            "corrected": self.corrected,
            "validated_at": self.validated_at,
            "should_not_split": self.should_not_split,  # Include for YAML consistency
            "occurrences": [occ.to_dict() for occ in self.occurrences],
        }

        # Only include system fields if corrected
        if self.corrected:
            result.update(
                {
                    "system_handle": self.system_handle,
                    "system_knot": self.system_knot,
                    "system_confidence": (
                        self.system_confidence.value if self.system_confidence else None
                    ),
                    "system_reasoning": self.system_reasoning,
                }
            )

        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any], original: Optional[str] = None) -> "BrushSplit":
        """Create from dictionary."""
        # Handle system confidence enum
        system_confidence = None
        if data.get("system_confidence"):
            try:
                system_confidence = ConfidenceLevel(data["system_confidence"])
            except ValueError:
                system_confidence = None

        # Use provided original or fall back to data field
        original_value = original or data.get("original", "")

        # Check if this is a do_not_split entry (no handle/knot fields)
        should_not_split = data.get("should_not_split", False)

        # For do_not_split entries, handle and knot should be None
        if should_not_split:
            handle = None
            knot = None
        else:
            # Regular split entries require handle and knot
            handle = data["handle"]
            knot = data["knot"]

        return cls(
            original=original_value,
            handle=handle,
            knot=knot,
            match_type=data.get("match_type"),
            corrected=data.get("corrected", False),
            validated_at=data.get("validated_at"),
            system_handle=data.get("system_handle"),
            system_knot=data.get("system_knot"),
            system_confidence=system_confidence,
            system_reasoning=data.get("system_reasoning"),
            should_not_split=should_not_split,
            occurrences=[
                BrushSplitOccurrence.from_dict(occ) for occ in data.get("occurrences", [])
            ],
        )


@dataclass
class BrushSplitStatistics:
    """Statistics for brush split validation progress."""

    total: int = 0
    validated: int = 0
    corrected: int = 0
    validation_percentage: float = 0.0
    correction_percentage: float = 0.0
    split_types: Dict[str, int] = field(
        default_factory=lambda: {"delimiter": 0, "fiber_hint": 0, "no_split": 0}
    )
    confidence_breakdown: Dict[str, int] = field(
        default_factory=lambda: {"high": 0, "medium": 0, "low": 0}
    )
    month_breakdown: Dict[str, int] = field(default_factory=dict)
    recent_activity: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "total": self.total,
            "validated": self.validated,
            "corrected": self.corrected,
            "validation_percentage": self.validation_percentage,
            "correction_percentage": self.correction_percentage,
            "split_types": self.split_types,
            "confidence_breakdown": self.confidence_breakdown,
            "month_breakdown": self.month_breakdown,
            "recent_activity": self.recent_activity,
        }

    def calculate_percentages(self):
        """Calculate validation and correction percentages."""
        if self.total > 0:
            self.validation_percentage = (self.validated / self.total) * 100
        else:
            self.validation_percentage = 0.0
        if self.validated > 0:
            self.correction_percentage = (self.corrected / self.validated) * 100
        else:
            self.correction_percentage = 0.0

    def add_split(self, split: "BrushSplit", month: Optional[str] = None):
        """Add a split to the statistics."""
        self.total += 1
        if split.validated_at:  # If there's a validation timestamp, it's validated
            self.validated += 1
        if split.corrected:
            self.corrected += 1

        # Update split type breakdown
        if split.handle is None:
            self.split_types["no_split"] += 1
        else:
            # This will be calculated by the validator when needed
            pass

        # Update month breakdown
        if month:
            self.month_breakdown[month] = self.month_breakdown.get(month, 0) + 1

        # Update confidence breakdown for corrected splits
        if split.corrected and split.system_confidence:
            confidence = split.system_confidence.value
            self.confidence_breakdown[confidence] = self.confidence_breakdown.get(confidence, 0) + 1

    def reset(self):
        """Reset all statistics to zero."""
        self.total = 0
        self.validated = 0
        self.corrected = 0
        self.validation_percentage = 0.0
        self.correction_percentage = 0.0
        self.split_types = {"delimiter": 0, "fiber_hint": 0, "no_split": 0}
        self.confidence_breakdown = {"high": 0, "medium": 0, "low": 0}
        self.month_breakdown = {}
        self.recent_activity = {}


# Pydantic models for API request/response validation
class BrushSplitOccurrenceModel(BaseModel):
    """Pydantic model for brush split occurrence."""

    file: str = Field(..., description="File containing the occurrence")
    comment_ids: List[str] = Field(default_factory=list, description="List of comment IDs")


class BrushSplitModel(BaseModel):
    """Pydantic model for brush split data."""

    original: str = Field(..., description="Original brush string")
    handle: Optional[str] = Field(None, description="Handle component")
    knot: Optional[str] = Field(
        None, description="Knot component (null when should_not_split is true)"
    )
    match_type: Optional[str] = Field(None, description="Match type from brush matcher")
    corrected: bool = Field(False, description="Whether this split was corrected (changed)")
    validated_at: Optional[str] = Field(None, description="ISO timestamp when validated")
    system_handle: Optional[str] = Field(None, description="System-generated handle")
    system_knot: Optional[str] = Field(None, description="System-generated knot")
    system_confidence: Optional[str] = Field(None, description="System confidence level")
    system_reasoning: Optional[str] = Field(None, description="System reasoning")
    should_not_split: bool = Field(False, description="Whether this brush should not be split")
    occurrences: List[BrushSplitOccurrenceModel] = Field(
        default_factory=list, description="List of occurrences"
    )


class SaveSplitsRequest(BaseModel):
    """Request model for saving brush splits."""

    brush_splits: List[BrushSplitModel] = Field(..., description="List of brush splits to save")


class SaveSplitsResponse(BaseModel):
    """Response model for saving brush splits."""

    success: bool = Field(..., description="Whether the save operation was successful")
    message: str = Field(..., description="Human-readable message")
    saved_count: int = Field(..., description="Number of splits saved")


class SaveSplitRequest(BaseModel):
    """Request model for saving a single brush split correction."""

    original: str = Field(..., description="Original brush string")
    handle: Optional[str] = Field(None, description="Corrected handle component")
    knot: Optional[str] = Field(
        None, description="Corrected knot component (null when should_not_split is true)"
    )
    should_not_split: bool = Field(False, description="Whether this brush should not be split")
    occurrences: Optional[List[BrushSplitOccurrenceModel]] = Field(
        default_factory=list, description="List of occurrences for this brush split"
    )


class SaveSplitResponse(BaseModel):
    """Response model for saving a single brush split."""

    success: bool = Field(..., description="Whether the save operation was successful")
    message: str = Field(..., description="Human-readable message")
    corrected: bool = Field(..., description="Whether this was a correction of an existing split")
    system_handle: Optional[str] = Field(None, description="Previous system-generated handle")
    system_knot: Optional[str] = Field(None, description="Previous system-generated knot")
    system_confidence: Optional[str] = Field(None, description="System confidence level")
    system_reasoning: Optional[str] = Field(None, description="System reasoning")


class DeleteSplitResponse(BaseModel):
    """Response model for deleting a brush split override."""

    success: bool = Field(..., description="Whether the delete operation was successful")
    message: str = Field(..., description="Human-readable message")
    deleted: bool = Field(..., description="Whether an entry was removed (False if already absent)")


class LoadResponse(BaseModel):
    """Response model for loading brush splits."""

    brush_splits: List[BrushSplitModel] = Field(..., description="List of brush splits")
    statistics: Dict[str, Any] = Field(..., description="Validation statistics")
    processing_info: Optional[Dict[str, Any]] = Field(
        None, description="Processing information and metrics"
    )
    errors: Optional[Dict[str, Any]] = Field(None, description="Error information if any")


class YAMLResponse(BaseModel):
    """Response model for YAML loading."""

    brush_splits: List[BrushSplitModel] = Field(..., description="List of validated splits")
    file_info: Dict[str, Any] = Field(..., description="File information")


class StatisticsResponse(BaseModel):
    """Response model for statistics."""

    total: int = Field(..., description="Total number of splits")
    validated: int = Field(..., description="Number of validated splits")
    corrected: int = Field(..., description="Number of corrected splits")
    validation_percentage: float = Field(..., description="Validation percentage")
    correction_percentage: float = Field(..., description="Correction percentage")
    split_types: Dict[str, int] = Field(..., description="Breakdown by split type")
    confidence_breakdown: Dict[str, int] = Field(..., description="Breakdown by confidence level")
    month_breakdown: Dict[str, int] = Field(..., description="Breakdown by month")
    recent_activity: Dict[str, Any] = Field(..., description="Recent validation activity")


class StatisticsCalculator:
    """Statistics calculator for brush split validation."""

    def __init__(self, validator: "BrushSplitValidator"):
        self.validator = validator

    def calculate_comprehensive_statistics(
        self, splits: List[BrushSplit], months: Optional[List[str]] = None
    ) -> BrushSplitStatistics:
        """Calculate comprehensive statistics for brush splits."""
        stats = BrushSplitStatistics()

        # Process each split
        for split in splits:
            # Determine month from occurrences if not provided
            month = None
            if months and len(months) > 0:
                month = months[0]  # Use first month as representative
            elif split.occurrences:
                # Extract month from first occurrence file
                first_file = split.occurrences[0].file
                if first_file.endswith(".json"):
                    month = first_file.replace(".json", "")

            stats.add_split(split, month)

            # Calculate split type if not already done
            if split.handle is not None:
                confidence, reasoning = self.validator.calculate_confidence(
                    split.original, split.handle, split.knot
                )
                if "delimiter" in reasoning.lower():
                    stats.split_types["delimiter"] += 1
                elif "fiber" in reasoning.lower():
                    stats.split_types["fiber_hint"] += 1
                else:
                    stats.split_types["no_split"] += 1

        # Calculate percentages
        stats.calculate_percentages()

        # Add recent activity information
        stats.recent_activity = self._calculate_recent_activity(splits)

        return stats

    def calculate_filtered_statistics(
        self, splits: List[BrushSplit], filters: Dict[str, Any]
    ) -> BrushSplitStatistics:
        """Calculate statistics with filters applied."""
        filtered_splits = self._apply_filters(splits, filters)
        return self.calculate_comprehensive_statistics(filtered_splits)

    def _apply_filters(self, splits: List[BrushSplit], filters: Dict[str, Any]) -> List[BrushSplit]:
        """Apply filters to splits."""
        filtered = splits

        # Filter by validation status
        if "validated_only" in filters and filters["validated_only"]:
            filtered = [s for s in filtered if s.validated]

        # Filter by confidence level
        if "confidence_level" in filters:
            confidence = filters["confidence_level"]
            filtered = [
                s
                for s in filtered
                if s.system_confidence and s.system_confidence.value == confidence
            ]

        # Filter by split type
        if "split_type" in filters:
            split_type = filters["split_type"]
            filtered = [s for s in filtered if self._get_split_type(s) == split_type]

        # Filter by month
        if "months" in filters and filters["months"]:
            target_months = set(filters["months"])
            filtered = [
                s
                for s in filtered
                if any(occ.file.replace(".json", "") in target_months for occ in s.occurrences)
            ]

        return filtered

    def _get_split_type(self, split: BrushSplit) -> str:
        """Get the split type for a brush split."""
        if split.handle is None:
            return "no_split"

        confidence, reasoning = self.validator.calculate_confidence(
            split.original, split.handle, split.knot
        )
        if "delimiter" in reasoning.lower():
            return "delimiter"
        elif "fiber" in reasoning.lower():
            return "fiber_hint"
        else:
            return "no_split"

    def _calculate_recent_activity(self, splits: List[BrushSplit]) -> Dict[str, Any]:
        """Calculate recent validation activity."""
        recent_corrections = []
        now = datetime.now()

        for split in splits:
            if split.corrected and split.validated_at:
                try:
                    # Handle both timezone-aware and timezone-naive datetimes
                    corrected_date_str = split.validated_at.replace("Z", "+00:00")
                    corrected_date = datetime.fromisoformat(corrected_date_str)

                    # Check if within the last 30 days
                    if (now - corrected_date).days <= 30:
                        recent_corrections.append(
                            {
                                "original": split.original,
                                "validated_at": split.validated_at,
                                "corrected": split.corrected,
                            }
                        )
                except (ValueError, TypeError):
                    # Skip invalid dates
                    continue

        # Count validations by time period
        corrected_today = 0
        corrected_this_week = 0

        for correction in recent_corrections:
            try:
                corrected_date_str = correction["validated_at"].replace("Z", "+00:00")
                corrected_date = datetime.fromisoformat(corrected_date_str)
                corrected_date_only = corrected_date.date()

                if corrected_date_only == now.date():
                    corrected_today += 1
                corrected_this_week += 1
            except ValueError:
                continue

        return {
            "recent_corrections": recent_corrections[:10],  # Limit to 10 most recent
            "total_recent": len(recent_corrections),
            "corrected_today": corrected_today,
            "corrected_this_week": corrected_this_week,
            "validated_today": corrected_today,  # For now, use corrected_today as validated_today
            "validated_this_week": corrected_this_week,  # Use corrected_this_week
        }


class BrushSplitValidator:
    """Validates and manages brush string splits with comprehensive error handling."""

    def __init__(self):
        self.yaml_path = Path("../data/brush_splits.yaml")
        self.validated_splits: Dict[str, BrushSplit] = {}

    def load_validated_splits(self) -> None:
        """Load validated splits from YAML file."""
        try:
            if not self.yaml_path.exists():
                logger.warning(f"YAML file not found: {self.yaml_path}")
                return

            with open(self.yaml_path, "r", encoding="utf-8") as f:
                yaml_data = yaml.safe_load(f)

            if not yaml_data:
                logger.warning("YAML file is empty")
                return

            # Check if yaml_data is a dictionary (expected structure)
            if not isinstance(yaml_data, dict):
                raise DataCorruptionError(
                    f"YAML file {self.yaml_path} does not contain a dictionary structure"
                )

            # Handle flat structure where each key is a brush name
            for brush_name, split_data in yaml_data.items():
                if isinstance(split_data, dict):
                    # Single entry
                    split_data["should_not_split"] = split_data.get("should_not_split", False)
                    brush_split = BrushSplit.from_dict(split_data, original=brush_name)
                    self.validated_splits[brush_name] = brush_split
                elif isinstance(split_data, list):
                    # Legacy list structure (for backward compatibility)
                    for item in split_data:
                        if isinstance(item, dict):
                            item["should_not_split"] = item.get("should_not_split", False)
                            brush_split = BrushSplit.from_dict(item, original=brush_name)
                            self.validated_splits[brush_name] = brush_split

            logger.info(
                f"Loaded {len(self.validated_splits)} validated splits from {self.yaml_path}"
            )

        except yaml.YAMLError as e:
            raise DataCorruptionError(f"Invalid YAML format in {self.yaml_path}: {e}")
        except DataCorruptionError:
            # Re-raise DataCorruptionError without wrapping
            raise
        except Exception as e:
            raise ProcessingError(f"Error loading validated splits from {self.yaml_path}: {e}")

    def save_validated_splits(self, splits: List[BrushSplit]) -> bool:
        """Save validated splits to YAML file."""
        try:
            # Create backup of existing file
            if self.yaml_path.exists():
                backup_path = self.yaml_path.with_suffix(".yaml.backup")
                import shutil

                shutil.copy2(self.yaml_path, backup_path)
                logger.info(f"Created backup: {backup_path}")

            # Convert splits to flat YAML structure
            yaml_data = {}
            for split in splits:
                # Use original as the key
                yaml_data[split.original] = split.to_yaml_dict()

            # Sort alphabetically by brush name
            sorted_data = dict(sorted(yaml_data.items()))

            # Write to file with explicit Unicode handling
            with open(self.yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(
                    sorted_data,
                    f,
                    default_flow_style=False,
                    sort_keys=False,
                    allow_unicode=True,  # Explicitly allow Unicode characters
                    encoding="utf-8",  # Explicitly set encoding
                )

            logger.info(f"Saved {len(splits)} validated splits to {self.yaml_path}")
            return True

        except Exception as e:
            logger.error(f"Error saving validated splits to {self.yaml_path}: {e}")
            return False

    def calculate_confidence(
        self, original: str, handle: Optional[str], knot: Optional[str]
    ) -> tuple[ConfidenceLevel, str]:
        """Calculate confidence level and reasoning for a brush split."""
        # Check for empty components first
        if handle is None or not handle.strip() or knot is None or not knot.strip():
            if handle is None:
                return ConfidenceLevel.HIGH, "Single component brush"
            return ConfidenceLevel.LOW, "Warning: empty component detected"

        if not handle:  # Single component brush
            return ConfidenceLevel.HIGH, "Single component brush"

        # Check for very short components
        if len(handle) < 3 or len(knot) < 3:
            return ConfidenceLevel.LOW, "Warning: component too short (<3 chars)"

        # Check for delimiter splits (most reliable)
        if " w/ " in original or " with " in original:
            return ConfidenceLevel.HIGH, "Delimiter split detected (w/ or with)"

        # Check for other delimiters
        if " / " in original or "/" in original or " - " in original:
            return ConfidenceLevel.HIGH, "Delimiter split detected (/, -, or -)"

        # Check for fiber indicators in components
        fiber_indicators = ["badger", "boar", "synthetic", "silvertip", "syn"]
        handle_has_fiber = any(indicator in handle.lower() for indicator in fiber_indicators)
        knot_has_fiber = any(indicator in knot.lower() for indicator in fiber_indicators)

        if handle_has_fiber and not knot_has_fiber:
            return ConfidenceLevel.HIGH, "Fiber-hint split: handle contains fiber indicator"
        elif knot_has_fiber and not handle_has_fiber:
            return ConfidenceLevel.HIGH, "Fiber-hint split: knot contains fiber indicator"
        elif handle_has_fiber and knot_has_fiber:
            return (
                ConfidenceLevel.MEDIUM,
                "Fiber-hint split: both components contain fiber indicators",
            )

        # Analyze component quality for unknown splits
        handle_quality = len(handle) >= 5 and not handle.isdigit()
        knot_quality = len(knot) >= 5 and not knot.isdigit()

        if handle_quality and knot_quality:
            return ConfidenceLevel.MEDIUM, "Unknown split type with good component quality"
        else:
            return ConfidenceLevel.LOW, "Unknown split type with poor component quality"

    def validate_split(
        self,
        original: str,
        handle: Optional[str],
        knot: str,
        should_not_split: bool = False,
        validated_at: Optional[str] = None,
    ) -> BrushSplit:
        """Create a validated brush split."""
        # If should_not_split is True, override the handle and knot
        if should_not_split:
            handle = None
            knot = original  # Use the original string as the knot

        # Calculate system confidence and reasoning
        system_confidence, system_reasoning = self.calculate_confidence(original, handle, knot)

        # Check if this is a correction or validation
        existing = None
        for validated_key, validated_split in self.validated_splits.items():
            if validated_key.lower() == original.lower():
                existing = validated_split
                break

        # Determine if this is a correction (changes made) or validation (accepted as-is)
        is_corrected = False
        system_handle = None
        system_knot = None

        if existing:
            # Check if any changes were made
            is_corrected = (
                existing.handle != handle
                or existing.knot != knot
                or existing.should_not_split != should_not_split
            )

            if is_corrected:
                # This is a correction - store the original system values
                system_handle = existing.handle
                system_knot = existing.knot

        # Set timestamp
        final_validated_at = validated_at or (existing.validated_at if existing else None)

        # Only set current time if this is an actual validation (not just creating a new split)
        if not final_validated_at and existing:
            from datetime import datetime

            final_validated_at = datetime.now().isoformat()

        return BrushSplit(
            original=original,
            handle=handle,
            knot=knot,
            corrected=is_corrected,
            validated_at=final_validated_at,
            system_handle=system_handle,
            system_knot=system_knot,
            system_confidence=system_confidence if is_corrected else None,
            system_reasoning=system_reasoning if is_corrected else None,
            should_not_split=should_not_split,
            occurrences=existing.occurrences if existing else [],
        )

    def merge_occurrences(self, original: str, new_occurrences: List[BrushSplitOccurrence]) -> None:
        """Merge new occurrences with existing validated entries."""
        existing_split = None
        for validated_key, validated_split in self.validated_splits.items():
            if validated_key.lower() == original.lower():
                existing_split = validated_split
                break

        if existing_split is None:
            return

        # Create a set of existing file/comment_id combinations for efficient lookup
        existing_combinations = set()
        for occ in existing_split.occurrences:
            for comment_id in occ.comment_ids:
                existing_combinations.add((occ.file, comment_id))

        # Add new occurrences that don't already exist
        for new_occ in new_occurrences:
            for comment_id in new_occ.comment_ids:
                if (new_occ.file, comment_id) not in existing_combinations:
                    # Find existing occurrence for this file or create new one
                    existing_file_occ = None
                    for occ in existing_split.occurrences:
                        if occ.file == new_occ.file:
                            existing_file_occ = occ
                            break

                    if existing_file_occ:
                        existing_file_occ.comment_ids.append(comment_id)
                    else:
                        existing_split.occurrences.append(
                            BrushSplitOccurrence(file=new_occ.file, comment_ids=[comment_id])
                        )
                    existing_combinations.add((new_occ.file, comment_id))

    def get_all_validated_splits(self) -> List[BrushSplit]:
        """Get all validated splits as a list."""
        return list(self.validated_splits.values())

    def delete_validated_split(self, original: str) -> tuple[bool, bool]:
        """Remove a brush split override so default automated parsing applies.

        Removes both manual handle/knot splits and should_not_split entries.

        Args:
            original: Original brush string key to remove

        Returns:
            Tuple of (success, deleted) where deleted is True if an entry was removed
        """
        self.validated_splits.clear()
        self.load_validated_splits()

        key_to_remove = None
        for key in self.validated_splits:
            if key.lower() == original.lower():
                key_to_remove = key
                break

        if key_to_remove is None:
            return True, False

        del self.validated_splits[key_to_remove]
        success = self.save_validated_splits(list(self.validated_splits.values()))
        return success, True


# Global validator instance
validator = BrushSplitValidator()
calculator = StatisticsCalculator(validator)


@router.get("/load", response_model=LoadResponse, summary="Load brush splits from selected months")
async def load_brush_splits(
    months: List[str] = Query(..., description="Months to load data from"),
    unmatched_only: bool = Query(True, description="Show only unmatched items"),
):
    """Load brush splits from selected months."""
    logger.info(f"🔄 Loading brush splits for months: {months}, unmatched_only: {unmatched_only}")
    start_time = time.time()
    """Load brush strings from selected months with data processing.

    Args:
        months: List of months in YYYY-MM format to load data from
        unmatched_only: If True, show only unmatched items. If False, show all items.

    Returns:
        LoadResponse containing brush splits and statistics

    Raises:
        HTTPException: If no months specified, data loading fails, or files are corrupted
    """
    try:
        if not months:
            raise HTTPException(status_code=400, detail="No months specified")

        # Load validated splits first
        try:
            validator.load_validated_splits()
        except (FileNotFoundError, DataCorruptionError, ProcessingError) as e:
            # Fail fast for internal errors - don't mask them
            logger.error(f"Failed to load validated splits: {e}")
            raise HTTPException(
                status_code=500, detail=f"Failed to load validated splits: {str(e)}"
            )
        except Exception as e:
            # Log but don't fail - this allows the endpoint to work even if YAML loading fails
            logger.warning(f"Non-critical error loading validated splits: {e}")

        # Data processing for actual dataset sizes (~2,500 records per month)
        brush_splits: Dict[str, Dict] = {}  # original -> split_data
        loaded_months = []
        failed_months = []
        total_records_processed = 0
        total_records_loaded = 0

        for month in months:
            file_path = Path(f"../data/matched/{month}.json")
            if not file_path.exists():
                logger.error(f"Month file not found: {file_path}")
                failed_months.append(month)
                continue

            try:
                # File reading with progress tracking
                logger.info(f"Loading data from {month}.json")
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                if not isinstance(data, dict) or "data" not in data:
                    logger.error(f"Invalid data structure in {month}.json")
                    failed_months.append(month)
                    continue

                # Process records efficiently for typical dataset sizes
                month_records = data.get("data", [])
                total_records_processed += len(month_records)

                logger.info(f"Processing {len(month_records)} records from {month}")

                for record in month_records:
                    brush_data = record.get("brush")
                    if brush_data and brush_data.get("original"):
                        original = brush_data["original"]
                        normalized = normalize_brush_string(original)
                        if normalized:
                            # Extract split information from matched data
                            matched = brush_data.get("matched")
                            if matched is None:
                                # Unmatched brush - use normalized as original, no handle/knot split
                                handle = None
                                knot = normalized  # Use normalized as knot for unmatched brushes
                                match_type = brush_data.get("match_type")
                            else:
                                # Matched brush - extract handle and knot
                                try:
                                    handle_obj = matched.get("handle")
                                    knot_obj = matched.get("knot")
                                    handle = (
                                        handle_obj.get("source_text")
                                        if handle_obj and isinstance(handle_obj, dict)
                                        else None
                                    )
                                    knot = (
                                        knot_obj.get("source_text")
                                        if knot_obj and isinstance(knot_obj, dict)
                                        else None
                                    )
                                    match_type = brush_data.get("match_type")

                                    # Handle cases where handle or knot is null in matched data
                                    if handle is None and knot is None:
                                        # No split available - use original as knot, no handle
                                        handle = None
                                        knot = normalized
                                    elif handle is None:
                                        # Only knot available - use original as handle
                                        handle = normalized
                                        knot = knot or normalized
                                    elif knot is None:
                                        # Only handle available - use original as knot
                                        handle = handle
                                        knot = normalized
                                    else:
                                        # Both handle and knot available
                                        handle = handle
                                        knot = knot
                                except Exception as e:
                                    # Fallback for any errors in extraction
                                    logger.warning(
                                        f"Error extracting handle/knot from {original}: {e}"
                                    )
                                    handle = None
                                    knot = normalized
                                    match_type = brush_data.get("match_type")

                            if normalized not in brush_splits:
                                brush_splits[normalized] = {
                                    "original": normalized,
                                    "handle": handle,
                                    "knot": knot,
                                    "match_type": match_type,
                                    "occurrences": {},  # file -> comment_ids
                                }

                            # Add comment ID to the appropriate file
                            comment_id = record.get("id", "") if record else ""
                            if comment_id:  # Only add non-empty comment IDs
                                file_key = f"{month}.json"
                                if file_key not in brush_splits[normalized]["occurrences"]:
                                    brush_splits[normalized]["occurrences"][file_key] = []
                                brush_splits[normalized]["occurrences"][file_key].append(comment_id)

                            total_records_loaded += 1

                loaded_months.append(month)
                logger.info(
                    f"Successfully processed {month}: {len(month_records)} records, "
                    f"{len(brush_splits)} unique brush strings"
                )

            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error in {month}.json: {e}")
                failed_months.append(month)
                continue
            except (OSError, IOError) as e:
                logger.error(f"File I/O error reading {month}.json: {e}")
                failed_months.append(month)
                continue
            except Exception as e:
                logger.error(f"Unexpected error processing {month}.json: {e}")
                failed_months.append(month)
                continue

        # Always return 200, even if no months could be loaded
        # This allows the frontend to handle partial failures gracefully

        # Convert to BrushSplit objects with processing
        splits = []
        logger.info(f"Converting {len(brush_splits)} unique brush strings to BrushSplit objects")

        for split_data in brush_splits.values():
            original = split_data["original"]
            handle = split_data["handle"]
            knot = split_data["knot"]
            match_type = split_data.get("match_type")
            occurrences_data = split_data["occurrences"]

            # Convert occurrences data to BrushSplitOccurrence objects
            occurrences = []
            for file_name, comment_ids in occurrences_data.items():
                if comment_ids:  # Only add occurrences with comment IDs
                    occurrences.append(
                        BrushSplitOccurrence(file=file_name, comment_ids=comment_ids)
                    )

            # Check if already validated (case-insensitive)
            existing_split = None
            for validated_key, validated_split in validator.validated_splits.items():
                if validated_key.lower() == original.lower():
                    existing_split = validated_split
                    break

            if existing_split:
                # Merge new occurrences with existing ones
                for new_occurrence in occurrences:
                    # Find existing occurrence for this file or create new one
                    existing_occurrence = None
                    for occ in existing_split.occurrences:
                        if occ.file == new_occurrence.file:
                            existing_occurrence = occ
                            break

                    if existing_occurrence:
                        # Merge comment IDs, avoiding duplicates
                        existing_comment_ids = set(existing_occurrence.comment_ids)
                        for comment_id in new_occurrence.comment_ids:
                            if comment_id not in existing_comment_ids:
                                existing_occurrence.comment_ids.append(comment_id)
                    else:
                        # Add new occurrence
                        existing_split.occurrences.append(new_occurrence)

                splits.append(existing_split)
            else:
                # Create new unvalidated split with actual split data
                split = BrushSplit(
                    original=original,
                    handle=handle,
                    knot=knot,
                    match_type=match_type,
                    corrected=False,  # Unvalidated splits are not corrected
                    validated_at=None,  # No timestamp for unvalidated splits
                    occurrences=occurrences,
                )
                splits.append(split)

        # Filter splits based on unmatched_only parameter
        if unmatched_only:
            # Show only unmatched items (where matched is None)
            filtered_splits = []
            for split in splits:
                # Check if this split is unmatched by looking at the original data
                # We need to check if the original brush had matched data
                is_unmatched = True
                for split_data in brush_splits.values():
                    if split_data["original"] == split.original:
                        # If match_type is not None, it's matched
                        if split_data.get("match_type") is not None:
                            is_unmatched = False
                        break

                if is_unmatched:
                    filtered_splits.append(split)

            splits = filtered_splits
            logger.info(f"Filtered to {len(splits)} unmatched splits")

        # Calculate statistics with split type breakdown
        logger.info(f"Calculating statistics for {len(splits)} brush splits")
        stats = calculator.calculate_comprehensive_statistics(splits, months)

        # Response with processing information
        response_data = {
            "brush_splits": [split.to_dict() for split in splits],
            "statistics": stats.to_dict(),
        }

        # Add processing information for user feedback
        processing_info = {
            "total_records_processed": total_records_processed,
            "total_records_loaded": total_records_loaded,
            "unique_brush_strings": len(brush_splits),
            "processing_efficiency": (
                (total_records_loaded / total_records_processed * 100)
                if total_records_processed > 0
                else 0.0
            ),
        }
        response_data["processing_info"] = processing_info

        if failed_months:
            response_data["errors"] = {
                "failed_months": failed_months,
                "loaded_months": loaded_months,
                "message": (
                    f"Successfully loaded {len(loaded_months)} months, "
                    f"failed to load {len(failed_months)} months"
                ),
            }

        processing_time = time.time() - start_time
        logger.info(
            f"✅ Data processing complete in {processing_time:.2f}s: {len(splits)} splits, "
            f"{len(loaded_months)} months loaded, {len(failed_months)} months failed"
        )
        return response_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in load_brush_splits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get(
    "/yaml", response_model=YAMLResponse, summary="Load existing validated splits from YAML"
)
async def load_yaml():
    """Load existing validated splits from YAML file.

    Returns:
        YAMLResponse containing validated splits and file information

    Raises:
        HTTPException: If YAML loading fails
    """
    try:
        validator.load_validated_splits()

        # Get file information
        yaml_exists = validator.yaml_path.exists()
        yaml_size = validator.yaml_path.stat().st_size if yaml_exists else 0

        return {
            "brush_splits": [split.to_dict() for split in validator.validated_splits.values()],
            "file_info": {
                "exists": yaml_exists,
                "path": str(validator.yaml_path),
                "size_bytes": yaml_size,
                "loaded_count": len(validator.validated_splits),
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/save", response_model=SaveSplitsResponse, summary="Save validated splits to YAML")
async def save_splits(data: SaveSplitsRequest):
    """Save validated brush splits to YAML file.

    Args:
        data: SaveSplitsRequest containing the brush splits to save

    Returns:
        SaveSplitsResponse with success status and save details
    """
    try:
        # Debug: Log the received data
        logger.info(f"Received {len(data.brush_splits)} brush splits for saving")

        # Check if any splits were provided
        if not data.brush_splits:
            raise HTTPException(status_code=400, detail="No brush splits provided for saving")

        for i, split in enumerate(data.brush_splits):
            logger.info(
                f"Split {i}: original='{split.original}', handle='{split.handle}', "
                f"knot='{split.knot}', should_not_split={split.should_not_split}"
            )

        validated_splits = []
        validation_errors = []

        for i, split_model in enumerate(data.brush_splits):
            try:
                # Convert Pydantic model to dict, then to BrushSplit
                split_dict = split_model.model_dump()

                # Validate required fields
                if not split_dict.get("original"):
                    validation_errors.append(f"Split {i}: missing original field")
                    continue

                # Only require knot field if should_not_split is false
                should_not_split = split_dict.get("should_not_split", False)
                if not should_not_split and not split_dict.get("knot"):
                    validation_errors.append(f"Split {i}: missing knot field")
                    continue

                # Automatically set corrected_at timestamp and corrected=True for all saved splits
                if not split_dict.get("validated_at"):
                    split_dict["validated_at"] = datetime.now().isoformat()
                split_dict["corrected"] = True

                split = BrushSplit.from_dict(split_dict)
                validated_splits.append(split)

            except (KeyError, ValueError) as e:
                validation_errors.append(f"Split {i}: invalid data structure - {e}")
                continue
            except Exception as e:
                validation_errors.append(f"Split {i}: unexpected error - {e}")
                continue

        # Fail fast for validation errors
        if validation_errors:
            raise HTTPException(
                status_code=400, detail=f"Validation errors: {'; '.join(validation_errors)}"
            )

        # Attempt to save with retry logic
        try:
            success = validator.save_validated_splits(validated_splits)
            if success:
                return {
                    "success": True,
                    "message": f"Successfully saved {len(validated_splits)} brush splits",
                    "saved_count": len(validated_splits),
                }
            else:
                raise HTTPException(status_code=500, detail="Failed to save splits to file")

        except (FileNotFoundError, DataCorruptionError, ProcessingError) as e:
            logger.error(f"Save operation failed: {e}")
            raise HTTPException(status_code=500, detail=f"Save operation failed: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in save_splits: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post(
    "/save-split", response_model=SaveSplitResponse, summary="Save a single brush split correction"
)
async def save_single_split(data: SaveSplitRequest):
    """Save a single brush split correction to YAML file.

    Args:
        data: SaveSplitRequest containing the brush split to save

    Returns:
        SaveSplitResponse with success status and correction details
    """
    try:
        # Validate input data
        if not data.original or not data.original.strip():
            raise HTTPException(status_code=400, detail="Original field cannot be empty")

        if not data.knot or not data.knot.strip():
            raise HTTPException(status_code=400, detail="Knot field cannot be empty")

        # Load existing validated splits
        validator.load_validated_splits()

        # Create the validated split
        split = validator.validate_split(
            original=data.original,
            handle=data.handle,
            knot=data.knot,
            should_not_split=data.should_not_split,
        )

        # Add occurrences if provided
        if data.occurrences:
            split.occurrences = [
                BrushSplitOccurrence(file=occ.file, comment_ids=occ.comment_ids)
                for occ in data.occurrences
            ]

        # Get all existing validated splits and add/update the new one
        all_splits = list(validator.validated_splits.values())

        # Check if this split already exists and update it, otherwise add it
        existing_found = False
        for i, existing_split in enumerate(all_splits):
            if existing_split.original.lower() == split.original.lower():
                all_splits[i] = split  # Replace existing with new
                existing_found = True
                break

        if not existing_found:
            all_splits.append(split)  # Add new split

        # Save all splits (existing + new/updated)
        success = validator.save_validated_splits(all_splits)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to save brush split")

        # Determine if this was a correction
        corrected = split.corrected
        system_handle = split.system_handle if corrected else None
        system_knot = split.system_knot if corrected else None
        system_confidence = (
            split.system_confidence.value if corrected and split.system_confidence else None
        )
        system_reasoning = split.system_reasoning if corrected else None

        return SaveSplitResponse(
            success=True,
            message=f"Successfully saved brush split: {data.original}",
            corrected=corrected,
            system_handle=system_handle,
            system_knot=system_knot,
            system_confidence=system_confidence,
            system_reasoning=system_reasoning,
        )

    except HTTPException:
        raise
    except (FileNotFoundError, DataCorruptionError, ProcessingError) as e:
        logger.error(f"Failed to save brush split: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save brush split: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error saving brush split: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while saving the brush split"
        )


@router.delete(
    "/split",
    response_model=DeleteSplitResponse,
    summary="Delete a brush split override (revert to automatic)",
)
async def delete_split(original: str = Query(..., description="Original brush string to remove")):
    """Remove a brush split override from YAML.

    Deletes both manual handle/knot splits and should_not_split entries so the
    matcher falls back to default automated parsing. Idempotent if already gone.
    """
    try:
        if not original or not original.strip():
            raise HTTPException(status_code=400, detail="Original field cannot be empty")

        success, deleted = validator.delete_validated_split(original.strip())
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete brush split")

        if deleted:
            message = f"Removed brush split override: {original.strip()}"
        else:
            message = f"No brush split override found for: {original.strip()}"

        return DeleteSplitResponse(success=True, message=message, deleted=deleted)

    except HTTPException:
        raise
    except (FileNotFoundError, DataCorruptionError, ProcessingError) as e:
        logger.error(f"Failed to delete brush split: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete brush split: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error deleting brush split: {e}")
        raise HTTPException(
            status_code=500, detail="An unexpected error occurred while deleting the brush split"
        )


@router.get("/statistics", response_model=StatisticsResponse, summary="Get validation statistics")
async def get_statistics():
    """Get validation statistics for all validated splits.

    Returns:
        StatisticsResponse containing validation progress and split type breakdown

    Raises:
        HTTPException: If statistics calculation fails
    """
    try:
        validator.load_validated_splits()

        # Calculate comprehensive statistics
        all_splits = list(validator.validated_splits.values())
        stats = calculator.calculate_comprehensive_statistics(all_splits)

        return stats.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/statistics/filtered",
    response_model=StatisticsResponse,
    summary="Get filtered validation statistics",
)
async def get_filtered_statistics(
    validated_only: bool = Query(False, description="Filter to validated splits only"),
    confidence_level: Optional[str] = Query(
        None, description="Filter by confidence level (high/medium/low)"
    ),
    split_type: Optional[str] = Query(
        None, description="Filter by split type (delimiter/fiber_hint/no_split)"
    ),
    months: Optional[List[str]] = Query(None, description="Filter by specific months"),
):
    """Get filtered validation statistics.

    Args:
        validated_only: Filter to validated splits only
        confidence_level: Filter by confidence level
        split_type: Filter by split type
        months: Filter by specific months

    Returns:
        StatisticsResponse containing filtered statistics

    Raises:
        HTTPException: If statistics calculation fails
    """
    try:
        validator.load_validated_splits()

        # Build filters
        filters = {}
        if validated_only:
            filters["validated_only"] = True
        if confidence_level:
            filters["confidence_level"] = confidence_level
        if split_type:
            filters["split_type"] = split_type
        if months:
            filters["months"] = months

        # Calculate filtered statistics
        all_splits = list(validator.validated_splits.values())
        stats = calculator.calculate_filtered_statistics(all_splits, filters)

        return stats.to_dict()

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
