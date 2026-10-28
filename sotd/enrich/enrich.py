"""Main enrich module that coordinates all enrichers."""

from typing import Optional

from .blackbird_plate_enricher import BlackbirdPlateEnricher
from .blade_enricher import BladeCountEnricher
from .brush_enricher import BrushEnricher
from .christopher_bradley_enricher import ChristopherBradleyEnricher
from .game_changer_enricher import GameChangerEnricher
from .override_manager import EnrichmentOverrideManager
from .razor_format_enricher import RazorFormatEnricher
from .registry import enricher_registry
from .soap_mashup_enricher import SoapMashupEnricher
from .soap_sample_enricher import SoapSampleEnricher
from .straight_razor_enricher import StraightRazorEnricher
from .super_speed_variant_enricher import SuperSpeedVariantEnricher

# Track if enrichers have been set up to avoid repeated setup
_enrichers_setup = False

# Global override manager (updated per month)
_current_override_manager: Optional[EnrichmentOverrideManager] = None


def setup_enrichers(override_manager: Optional[EnrichmentOverrideManager] = None):
    """Set up all enrichers in the registry.

    Args:
        override_manager: Optional enrichment override manager for forcing catalog values
    """
    global _enrichers_setup, _current_override_manager

    # Update current override manager (can change per month)
    _current_override_manager = override_manager

    if _enrichers_setup:
        # Enrichers already registered, just update the override manager on
        # every enricher that accepts one. Previously only BrushEnricher was
        # updated here, so StraightRazorEnricher kept override_manager=None
        # on repeat calls (the production path: run.py calls setup_enrichers()
        # once with no manager, then per month with the month's manager) and
        # its grind/width/point/steel overrides never applied.
        for enricher in enricher_registry.get_all_enrichers():
            if hasattr(enricher, "override_manager"):
                enricher.override_manager = override_manager
        return

    # Get data_path from first enricher if it exists (for consistency)
    # For now, we'll use None and let enrichers use default paths
    data_path = None

    # Register all enrichers with override manager
    enricher_registry.register(BladeCountEnricher())
    enricher_registry.register(
        BrushEnricher(data_path=data_path, override_manager=override_manager)
    )
    enricher_registry.register(StraightRazorEnricher(override_manager=override_manager))
    enricher_registry.register(GameChangerEnricher())
    enricher_registry.register(ChristopherBradleyEnricher())
    enricher_registry.register(BlackbirdPlateEnricher())
    enricher_registry.register(SoapSampleEnricher())
    enricher_registry.register(SoapMashupEnricher())
    enricher_registry.register(SuperSpeedVariantEnricher())
    enricher_registry.register(RazorFormatEnricher())

    _enrichers_setup = True


def enrich_comments(comments: list[dict], original_comments: list[str]) -> list[dict]:
    """Enrich a list of comments with all applicable enrichers.

    Args:
        comments: List of comment records with matched product data
        original_comments: List of original user comment texts

    Returns:
        List of enriched comment records

    Note:
        setup_enrichers() must be called before this function to register enrichers
        and set up the override manager.
    """
    # Enrich all comments
    return enricher_registry.enrich_records(comments, original_comments)
