"""Soap mashup enricher: sets is_mashup from catalog countable or text detection."""

from pathlib import Path
from typing import Any, Dict, Optional

from sotd.utils.data_dir import get_data_dir
from sotd.utils.soap_extraction import detect_soap_mashup
from sotd.utils.yaml_loader import load_yaml_with_nfc

from .enricher import BaseEnricher


def get_default_soaps_path() -> Path:
    """Default soaps.yaml: ``<data dir>/soaps.yaml``.

    The data dir is the run's data dir (``get_data_dir()``: ``--data-dir`` >
    ``SOTD_DATA_DIR`` env var > ``"data"``). A relative data dir is anchored
    at the repo root so the path does not depend on the process working
    directory — previously the enricher defaulted to a bare CWD-relative
    ``Path("data/soaps.yaml")``, so constructing it from any directory but
    the repo root silently loaded no catalog and the countable lookup never
    fired (the loop runs from ``/app`` with ``SOTD_DATA_DIR=/data``).
    """
    data_dir = get_data_dir()
    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parent.parent.parent / data_dir
    return data_dir / "soaps.yaml"


class SoapMashupEnricher(BaseEnricher):
    """Enricher that sets soap.enriched.is_mashup for mashup usage reporting.

    Two sources (union):
    1. Catalog: scent has countable === false. Uses soap.matched.countable when present
       (regex match), or looks up soaps.yaml by brand+scent when matched has no countable
       (e.g. exact match from correct_matches), so catalog remains single source of truth.
    2. Text: soap original/normalized contains "mashup", "mash up", or "mash-up" (catches
       unbranded entries like "soap mashup", "Sample mashup" even when matched is null).

    All mashup aggregators and metrics key off soap.enriched.is_mashup only.
    """

    def __init__(self, soaps_path: Optional[Path] = None):
        self.soaps_path = soaps_path or get_default_soaps_path()
        self._soaps_catalog: Optional[Dict[str, Any]] = None

    def _get_soaps_catalog(self) -> Dict[str, Any]:
        if self._soaps_catalog is None and self.soaps_path.exists():
            self._soaps_catalog = load_yaml_with_nfc(self.soaps_path) or {}
        return self._soaps_catalog or {}

    def _catalog_countable_for_scent(self, brand: str, scent: str) -> Optional[bool]:
        """Return catalog countable for brand+scent, or None if not found."""
        catalog = self._get_soaps_catalog()
        brand_entry = catalog.get(brand)
        if not isinstance(brand_entry, dict):
            return None
        scents = brand_entry.get("scents", {})
        if not isinstance(scents, dict):
            return None
        scent_data = scents.get(scent)
        if not isinstance(scent_data, dict) or "countable" not in scent_data:
            return None
        return scent_data["countable"]

    @property
    def target_field(self) -> str:
        """Target soap field for enrichment."""
        return "soap"

    def applies_to(self, record: Dict[str, Any]) -> bool:
        """Apply when record has a soap field (even if matched is null)."""
        return "soap" in record and record["soap"] is not None

    def enrich(
        self,
        field_data: Dict[str, Any],
        original_comment: str,
        record: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Set is_mashup from matched.countable, catalog lookup by brand+scent, or text."""
        is_mashup = False

        # (a) Catalog: matched has countable === false, or we look up by brand+scent
        matched = field_data.get("matched")
        if matched is not None and isinstance(matched, dict):
            if matched.get("countable") is False:
                is_mashup = True
            elif "countable" not in matched:
                # e.g. exact match from correct_matches: look up current catalog
                brand = matched.get("brand")
                scent = matched.get("scent")
                if brand and scent:
                    catalog_countable = self._catalog_countable_for_scent(brand, scent)
                    if catalog_countable is False:
                        is_mashup = True

        # (b) Text: original or normalized contains mashup indicator (e.g. "soap mashup")
        if not is_mashup:
            original = field_data.get("original") or ""
            normalized = field_data.get("normalized") or ""
            if detect_soap_mashup(original) or detect_soap_mashup(normalized):
                is_mashup = True

        return {"is_mashup": is_mashup}
