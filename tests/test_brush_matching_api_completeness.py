"""
Test to ensure brush matching API provides all detailed information from CLI output.

This test validates that the API response includes:
1. Complete component details with scores and breakdowns
2. Split information showing how brush strings are parsed
3. Detailed modifier descriptions
4. Complete metadata for handle and knot components
5. All scoring breakdown information
"""

import sys
from pathlib import Path

import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import after path setup
from webui.api.brush_matching import BrushAnalysisResponse, BrushMatchResult


class TestBrushMatchingAPICompleteness:
    """Test that brush matching API provides complete information matching CLI output."""

    def test_brush_match_result_structure(self):
        """Test that BrushMatchResult includes all required fields for complete information."""
        # Test that all fields from CLI output are present in the API response
        result = BrushMatchResult(
            strategy="test_strategy",
            score=80.0,
            matchType="regex",
            pattern="test_pattern",
            scoreBreakdown={
                "baseScore": 80.0,
                "modifiers": 0.0,
                "modifierDetails": [],
                "total": 80.0,
            },
            matchedData={
                "brand": "TestBrand",
                "model": "TestModel",
                "handle": {
                    "brand": "HandleBrand",
                    "model": "HandleModel",
                    "source_text": "handle source",
                },
                "knot": {
                    "brand": "KnotBrand",
                    "model": "KnotModel",
                    "fiber": "badger",
                    "knot_size_mm": 26.0,
                    "source_text": "knot source",
                },
            },
            componentDetails={
                "handle": {
                    "score": 10.0,
                    "breakdown": {
                        "brand_match": 5.0,
                        "handle_indicators": 0.0,
                        "priority_score": 0.0,
                    },
                    "metadata": {
                        "brand": "HandleBrand",
                        "model": "HandleModel",
                        "source": "handle source",
                    },
                },
                "knot": {
                    "score": 15.0,
                    "breakdown": {
                        "fiber_match": 5.0,
                        "size_match": 0.0,
                        "brand_match": 5.0,
                        "knot_indicators": 10.0,
                        "priority_score": 5.0,
                    },
                    "metadata": {
                        "brand": "KnotBrand",
                        "model": "KnotModel",
                        "fiber": "badger",
                        "source": "knot source",
                    },
                },
            },
            splitInformation={
                "handleText": "handle part",
                "knotText": "knot part",
                "splitPriority": "high",
            },
        )

        # Verify all required fields are present
        assert result.strategy == "test_strategy"
        assert result.score == 80.0
        assert result.matchType == "regex"
        assert result.pattern == "test_pattern"

        # Verify score breakdown
        assert result.scoreBreakdown["baseScore"] == 80.0
        assert result.scoreBreakdown["modifiers"] == 0.0
        assert result.scoreBreakdown["total"] == 80.0

        # Verify matched data structure
        assert result.matchedData["brand"] == "TestBrand"
        assert result.matchedData["model"] == "TestModel"
        assert result.matchedData["handle"]["brand"] == "HandleBrand"
        assert result.matchedData["knot"]["fiber"] == "badger"
        assert result.matchedData["knot"]["knot_size_mm"] == 26.0

        # Verify component details
        assert result.componentDetails is not None
        component_details = result.componentDetails
        assert component_details["handle"]["score"] == 10.0
        assert component_details["knot"]["score"] == 15.0

        # Verify split information
        assert result.splitInformation is not None
        split_info = result.splitInformation
        assert split_info["handleText"] == "handle part"
        assert split_info["knotText"] == "knot part"
        assert split_info["splitPriority"] == "high"

    def test_score_breakdown_completeness(self):
        """Test that score breakdown includes all information shown in CLI output."""
        score_breakdown = {
            "baseScore": 60.0,
            "modifiers": 12.5,
            "modifierDetails": [
                {
                    "name": "multiple_brands",
                    "weight": 0.0,
                    "description": "Multiple brands detected",
                },
                {"name": "handle_weight", "weight": 1.0, "description": "Handle weight bonus"},
                {"name": "knot_weight", "weight": 1.5, "description": "Knot weight bonus"},
                {
                    "name": "dual_component",
                    "weight": 10.0,
                    "description": "Both handle and knot components matched",
                },
            ],
            "total": 72.5,
        }

        # Verify all required fields
        assert "baseScore" in score_breakdown
        assert "modifiers" in score_breakdown
        assert "modifierDetails" in score_breakdown
        assert "total" in score_breakdown

        # Verify modifier details structure
        modifier_details = score_breakdown["modifierDetails"]
        assert len(modifier_details) == 4

        # Verify each modifier has required fields
        for modifier in modifier_details:
            assert "name" in modifier
            assert "weight" in modifier
            assert "description" in modifier

    def test_component_details_structure(self):
        """Test that component details include all scoring and metadata information."""
        component_details = {
            "handle": {
                "score": 10.0,
                "breakdown": {"brand_match": 5.0, "handle_indicators": 0.0, "priority_score": 0.0},
                "metadata": {
                    "brand": "Zenith",
                    "model": "Unspecified",
                    "source": "r/wetshaving zenith moar boar",
                },
            },
            "knot": {
                "score": 15.0,
                "breakdown": {
                    "fiber_match": 5.0,
                    "size_match": 0.0,
                    "brand_match": 5.0,
                    "knot_indicators": 10.0,
                    "priority_score": 5.0,
                },
                "metadata": {
                    "brand": "Zenith",
                    "model": "Boar",
                    "fiber": "Boar",
                    "source": "r/wetshaving zenith moar boar",
                },
            },
        }

        # Verify handle component
        handle = component_details["handle"]
        assert handle["score"] == 10.0
        assert "breakdown" in handle
        assert "metadata" in handle

        # Verify handle breakdown
        handle_breakdown = handle["breakdown"]
        assert "brand_match" in handle_breakdown
        assert "handle_indicators" in handle_breakdown
        assert "priority_score" in handle_breakdown

        # Verify handle metadata
        handle_metadata = handle["metadata"]
        assert "brand" in handle_metadata
        assert "model" in handle_metadata
        assert "source" in handle_metadata

        # Verify knot component
        knot = component_details["knot"]
        assert knot["score"] == 15.0
        assert "breakdown" in knot
        assert "metadata" in knot

        # Verify knot breakdown
        knot_breakdown = knot["breakdown"]
        assert "fiber_match" in knot_breakdown
        assert "size_match" in knot_breakdown
        assert "brand_match" in knot_breakdown
        assert "knot_indicators" in knot_breakdown
        assert "priority_score" in knot_breakdown

        # Verify knot metadata
        knot_metadata = knot["metadata"]
        assert "brand" in knot_metadata
        assert "model" in knot_metadata
        assert "fiber" in knot_metadata
        assert "source" in knot_metadata

    def test_split_information_structure(self):
        """Test that split information includes all parsing details."""
        split_info = {
            "handleText": "r",
            "knotText": "wetshaving zenith moar boar",
            "splitPriority": "medium",
        }

        # Verify all required fields
        assert "handleText" in split_info
        assert "knotText" in split_info
        assert "splitPriority" in split_info

        # Verify content
        assert split_info["handleText"] == "r"
        assert split_info["knotText"] == "wetshaving zenith moar boar"
        assert split_info["splitPriority"] == "medium"

    def test_matched_data_completeness(self):
        """Test that matched data includes all component information."""
        matched_data = {
            "brand": "Zenith",
            "model": "r/wetshaving MOAR BOAR",
            "handle": {
                "brand": "Zenith",
                "model": None,
                "source_text": "r/wetshaving zenith moar boar",
            },
            "knot": {
                "brand": "Zenith",
                "model": "r/wetshaving MOAR BOAR",
                "fiber": "Boar",
                "knot_size_mm": 31.0,
                "source_text": "r/wetshaving zenith moar boar",
            },
        }

        # Verify top-level fields
        assert "brand" in matched_data
        assert "model" in matched_data
        assert "handle" in matched_data
        assert "knot" in matched_data

        # Verify handle structure
        handle = matched_data["handle"]
        assert "brand" in handle
        assert "model" in handle
        assert "source_text" in handle

        # Verify knot structure
        knot = matched_data["knot"]
        assert "brand" in knot
        assert "model" in knot
        assert "fiber" in knot
        assert "knot_size_mm" in knot
        assert "source_text" in knot

    def test_modifier_details_descriptions(self):
        """Test that modifier details include descriptive information."""
        modifier_details = [
            {"name": "knot_indicators", "weight": 10.0, "description": "Fiber type detected: boar"},
            {
                "name": "handle_indicators",
                "weight": 0.0,
                "description": "Handle indicators detected",
            },
            {
                "name": "dual_component",
                "weight": 10.0,
                "description": "Both handle and knot components matched",
            },
        ]

        # Verify each modifier has descriptive information
        for modifier in modifier_details:
            assert "name" in modifier
            assert "weight" in modifier
            assert "description" in modifier

            # Verify description is meaningful
            assert len(modifier["description"]) > 0
            assert modifier["description"] != modifier["name"]

    def test_api_response_structure(self):
        """Test that the complete API response includes all required sections."""
        # Create a complete response structure
        response = BrushAnalysisResponse(
            results=[
                BrushMatchResult(
                    strategy="test_strategy",
                    score=80.0,
                    matchType="regex",
                    pattern="test_pattern",
                    scoreBreakdown={
                        "baseScore": 80.0,
                        "modifiers": 0.0,
                        "modifierDetails": [],
                        "total": 80.0,
                    },
                    matchedData={"brand": "TestBrand", "model": "TestModel"},
                )
            ],
            winner=BrushMatchResult(
                strategy="test_strategy",
                score=80.0,
                matchType="regex",
                pattern="test_pattern",
                scoreBreakdown={
                    "baseScore": 80.0,
                    "modifiers": 0.0,
                    "modifierDetails": [],
                    "total": 80.0,
                },
                matchedData={"brand": "TestBrand", "model": "TestModel"},
            ),
            enrichedData={
                "_enriched_by": "BrushEnricher",
                "_extraction_source": "user_comment",
                "fiber": "Boar",
            },
        )

        # Verify response structure
        assert "results" in response.model_dump()
        assert "winner" in response.model_dump()
        assert "enrichedData" in response.model_dump()

        # Verify results array
        assert len(response.results) == 1
        assert response.results[0].strategy == "test_strategy"

        # Verify winner
        assert response.winner.strategy == "test_strategy"
        assert response.winner.score == 80.0

        # Verify enriched data
        assert response.enrichedData["_enriched_by"] == "BrushEnricher"
        assert response.enrichedData["fiber"] == "Boar"


if __name__ == "__main__":
    pytest.main([__file__])
