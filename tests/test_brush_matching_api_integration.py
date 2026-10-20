"""
Integration test to verify brush matching API provides complete information.

This test calls the actual API endpoint to ensure it returns all the detailed
information shown in the CLI output, including component details, split information,
and detailed modifier descriptions.
"""

import pytest
from pathlib import Path
import sys

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from webui.api.brush_matching import analyze_brush, BrushAnalysisRequest


@pytest.mark.asyncio
class TestBrushMatchingAPIIntegration:
    """Integration tests for brush matching API completeness."""

    async def test_api_provides_component_details(self):
        """Test that API provides complete component details for split strategies."""
        # Test with a brush string that should trigger component analysis
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar",
            bypass_correct_matches=True,  # Bypass to see all strategies
        )

        # Call the API function directly
        response = await analyze_brush(request)

        # Verify response structure
        assert response is not None
        assert hasattr(response, "results")
        assert hasattr(response, "winner")
        assert hasattr(response, "enrichedData")

        # Look for strategies that should have component details
        component_strategies = ["full_input_component_matching", "automated_split"]

        found_component_details = False
        for result in response.results:
            if result.strategy in component_strategies:
                if result.componentDetails:
                    found_component_details = True

                    # Verify handle component details
                    if "handle" in result.componentDetails:
                        handle = result.componentDetails["handle"]
                        assert "score" in handle
                        assert "breakdown" in handle
                        assert "metadata" in handle

                        # Verify handle breakdown has expected fields
                        breakdown = handle["breakdown"]
                        expected_fields = ["brand_match", "handle_indicators", "priority_score"]
                        for field in expected_fields:
                            if field in breakdown:
                                assert isinstance(breakdown[field], (int, float))

                    # Verify knot component details
                    if "knot" in result.componentDetails:
                        knot = result.componentDetails["knot"]
                        assert "score" in knot
                        assert "breakdown" in knot
                        assert "metadata" in knot

                        # Verify knot breakdown has expected fields
                        breakdown = knot["breakdown"]
                        expected_fields = [
                            "fiber_match",
                            "size_match",
                            "brand_match",
                            "knot_indicators",
                            "priority_score",
                        ]
                        for field in expected_fields:
                            if field in breakdown:
                                assert isinstance(breakdown[field], (int, float))

        # At least one strategy should have component details
        assert found_component_details, "No strategies provided component details"

    async def test_api_provides_meaningful_component_scoring_breakdowns(self):
        """Test that component scoring breakdowns contain actual scoring data, not just empty structures."""
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar", bypass_correct_matches=True
        )

        response = await analyze_brush(request)

        # Look for strategies that should have component details
        component_strategies = ["full_input_component_matching", "automated_split"]

        found_meaningful_breakdowns = False
        for result in response.results:
            if result.strategy in component_strategies and result.componentDetails:
                # Check handle component breakdown
                if "handle" in result.componentDetails:
                    handle = result.componentDetails["handle"]
                    if "breakdown" in handle and handle["breakdown"]:
                        breakdown = handle["breakdown"]
                        # Verify that breakdown contains actual scoring data
                        total_breakdown_score = sum(breakdown.values())
                        if total_breakdown_score > 0:
                            found_meaningful_breakdowns = True
                            print(f"✅ Handle breakdown for {result.strategy}: {breakdown}")
                            print(f"   Total breakdown score: {total_breakdown_score}")
                            print(f"   Component score: {handle['score']}")

                # Check knot component breakdown
                if "knot" in result.componentDetails:
                    knot = result.componentDetails["knot"]
                    if "breakdown" in knot and knot["breakdown"]:
                        breakdown = knot["breakdown"]
                        # Verify that breakdown contains actual scoring data
                        total_breakdown_score = sum(breakdown.values())
                        if total_breakdown_score > 0:
                            found_meaningful_breakdowns = True
                            print(f"✅ Knot breakdown for {result.strategy}: {breakdown}")
                            print(f"   Total breakdown score: {total_breakdown_score}")
                            print(f"   Component score: {knot['score']}")

        # At least one component should have meaningful scoring breakdowns
        assert found_meaningful_breakdowns, "No meaningful component scoring breakdowns found"

    async def test_api_provides_split_information(self):
        """Test that API provides split information for strategies that split brush strings."""
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar", bypass_correct_matches=True
        )

        response = await analyze_brush(request)

        # Look for strategies that should have split information
        split_strategies = ["automated_split", "full_input_component_matching"]

        found_split_info = False
        for result in response.results:
            if result.strategy in split_strategies:
                if result.splitInformation:
                    found_split_info = True

                    # Verify split information structure
                    split_info = result.splitInformation
                    assert "handleText" in split_info
                    assert "knotText" in split_info

                    # Verify content is not empty
                    assert split_info["handleText"] != ""
                    assert split_info["knotText"] != ""

                    # Verify split priority if present
                    if "splitPriority" in split_info:
                        assert split_info["splitPriority"] in ["high", "medium", "low"]

        # At least one strategy should have split information
        assert found_split_info, "No strategies provided split information"

    async def test_api_provides_detailed_modifier_descriptions(self):
        """Test that API provides detailed modifier descriptions, not just generic text."""
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar", bypass_correct_matches=True
        )

        response = await analyze_brush(request)

        # Check that at least one result has detailed modifier descriptions
        found_detailed_descriptions = False
        for result in response.results:
            if result.scoreBreakdown and "modifierDetails" in result.scoreBreakdown:
                modifier_details = result.scoreBreakdown["modifierDetails"]
                for modifier in modifier_details:
                    if "description" in modifier:
                        description = modifier["description"]
                        # Description should be more than just the modifier name
                        if description != modifier["name"] and len(description) > len(
                            modifier["name"]
                        ):
                            found_detailed_descriptions = True
                            break

        assert found_detailed_descriptions, "No detailed modifier descriptions found"

    async def test_api_provides_complete_score_breakdown(self):
        """Test that API provides complete score breakdown information."""
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar", bypass_correct_matches=True
        )

        response = await analyze_brush(request)

        # Verify all results have complete score breakdown
        for result in response.results:
            assert hasattr(result, "scoreBreakdown")
            breakdown = result.scoreBreakdown

            # Verify required fields
            assert "baseScore" in breakdown
            assert "modifiers" in breakdown
            assert "modifierDetails" in breakdown

            # Verify types
            assert isinstance(breakdown["baseScore"], (int, float))
            assert isinstance(breakdown["modifiers"], (int, float))
            assert isinstance(breakdown["modifierDetails"], list)

            # Verify modifier details structure
            for modifier in breakdown["modifierDetails"]:
                assert "name" in modifier
                assert "weight" in modifier
                assert "description" in modifier

    async def test_api_provides_enriched_data(self):
        """Test that API provides enriched data from the enrich phase."""
        request = BrushAnalysisRequest(
            brushString="r/wetshaving zenith moar boar",
            bypass_correct_matches=False,  # Use normal matching to get enrichment
        )

        response = await analyze_brush(request)

        # Debug: Print response structure
        print(f"\n=== Response Debug ===")
        print(f"Response type: {type(response)}")
        print(f"Response attributes: {dir(response)}")
        print(f"Has enrichedData: {hasattr(response, 'enrichedData')}")
        if hasattr(response, "enrichedData"):
            print(f"enrichedData value: {response.enrichedData}")
            print(f"enrichedData type: {type(response.enrichedData)}")
            if response.enrichedData:
                keys = (
                    list(response.enrichedData.keys())
                    if hasattr(response.enrichedData, "keys")
                    else "No keys"
                )
                print(f"enrichedData keys: {keys}")
        dict_method = (
            response.model_dump() if hasattr(response, "model_dump") else "No model_dump method"
        )
        print(f"Response dict: {dict_method}")

        # Verify enriched data is present
        assert hasattr(response, "enrichedData")

        # Enriched data should contain fiber information for this brush string
        if response.enrichedData:
            # Check for expected enrichment fields based on actual data structure
            # The actual enrichedData now has nested structure with handle and knot sections
            # Check for nested structure fields
            assert "handle" in response.enrichedData, "Handle section should be present in response"
            assert "knot" in response.enrichedData, "Knot section should be present in response"

            # Verify that fiber information is in the knot section
            knot_section = response.enrichedData["knot"]
            assert "fiber" in knot_section, "Fiber field should be present in knot section"
            assert (
                "knot_size_mm" in knot_section
            ), "Knot size field should be present in knot section"

            # Verify that handle information is in the handle section
            handle_section = response.enrichedData["handle"]
            assert "brand" in handle_section, "Handle brand should be present in handle section"

            # Verify that source text is at the root level
            assert (
                "source_text" in response.enrichedData
            ), "Source text field should be present in response"

    async def test_input_parsing_fiber_and_knot_size(self):
        """Parsed fiber/size come from input text, independent of catalog match."""
        request = BrushAnalysisRequest(brushString="Omega 26mm Boar")
        response = await analyze_brush(request)

        assert response.inputParsing is not None
        assert response.inputParsing.fiber == "Boar"
        assert response.inputParsing.knot_size_mm == 26.0

    async def test_input_parsing_stiff_bristle_without_size(self):
        """Stiff bristle parses as Boar; no size when none is present in the string."""
        request = BrushAnalysisRequest(brushString="unknown - stiff bristle brush")
        response = await analyze_brush(request)

        assert response.inputParsing.fiber == "Boar"
        assert response.inputParsing.knot_size_mm is None


if __name__ == "__main__":
    pytest.main([__file__])
