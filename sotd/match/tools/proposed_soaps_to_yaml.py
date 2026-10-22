"""Convert data/proposed/YYYY-MM.json soap proposals into soaps.yaml-shaped YAML."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

KEEP_TYPES = frozenset({"new_scent", "new_pattern"})
SKIP_STATUSES = frozenset({"accepted", "rejected"})


def filter_soap_proposals(proposals: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep actionable soap new_scent / new_pattern proposals."""
    kept: list[dict[str, Any]] = []
    for prop in proposals:
        if prop.get("field") != "soap":
            continue
        if prop.get("type") not in KEEP_TYPES:
            continue
        if prop.get("_status") in SKIP_STATUSES:
            continue
        brand = (prop.get("brand") or "").strip()
        model = (prop.get("model") or "").strip()
        pattern = (prop.get("suggested_pattern") or "").strip()
        if not brand or not model or not pattern:
            continue
        kept.append(prop)
    return kept


def build_catalog_fragment(proposals: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Group proposals into soaps.yaml-shaped structure:

        Brand:
          scents:
            Scent:
              patterns:
              - ...
    """
    # brand -> scent -> ordered unique patterns
    grouped: dict[str, dict[str, list[str]]] = {}
    for prop in proposals:
        brand = (prop.get("brand") or "").strip()
        scent = (prop.get("model") or "").strip()
        pattern = (prop.get("suggested_pattern") or "").strip()
        scent_map = grouped.setdefault(brand, {})
        patterns = scent_map.setdefault(scent, [])
        if pattern not in patterns:
            patterns.append(pattern)

    fragment: dict[str, Any] = {}
    for brand in sorted(grouped):
        scents_out: dict[str, Any] = {}
        for scent in sorted(grouped[brand]):
            scents_out[scent] = {"patterns": grouped[brand][scent]}
        fragment[brand] = {"scents": scents_out}
    return fragment


def convert_proposed_file(
    in_path: Path,
    out_path: Path,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Load proposed JSON, write catalog-shaped YAML, return summary stats."""
    if not in_path.exists():
        raise FileNotFoundError(f"Proposed file not found: {in_path}")
    if out_path.exists() and not force:
        raise FileExistsError(f"Output exists (use --force to overwrite): {out_path}")

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        proposals = raw
    elif isinstance(raw, dict):
        proposals = raw.get("proposals") or []
    else:
        raise ValueError(f"Unexpected proposed file shape in {in_path}")

    if not isinstance(proposals, list):
        raise ValueError(f"'proposals' must be a list in {in_path}")

    kept = filter_soap_proposals(proposals)
    fragment = build_catalog_fragment(kept)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        yaml.dump(
            fragment,
            f,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )

    scent_count = sum(len(brand_data["scents"]) for brand_data in fragment.values())
    type_counts = {"new_scent": 0, "new_pattern": 0}
    for prop in kept:
        ptype = prop.get("type")
        if ptype in type_counts:
            type_counts[ptype] += 1

    return {
        "proposals_used": len(kept),
        "brands": len(fragment),
        "scents": scent_count,
        "new_scent": type_counts["new_scent"],
        "new_pattern": type_counts["new_pattern"],
    }


def _default_paths(month: str, data_dir: Path) -> tuple[Path, Path]:
    in_path = data_dir / "proposed" / f"{month}.json"
    out_path = data_dir / "proposed" / "soaps" / f"{month}.yaml"
    return in_path, out_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert data/proposed/YYYY-MM.json soap proposals into a "
            "soaps.yaml-shaped YAML fragment for manual review and copy/paste."
        )
    )
    parser.add_argument(
        "--month",
        required=True,
        help="Month (YYYY-MM) — reads data/proposed/{month}.json by default",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Data directory root (default: data)",
    )
    parser.add_argument(
        "--in",
        dest="in_path",
        type=Path,
        default=None,
        help="Override input proposed JSON path",
    )
    parser.add_argument(
        "--out",
        dest="out_path",
        type=Path,
        default=None,
        help="Override output YAML path",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite output file if it exists",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = build_parser()
    args = parser.parse_args(argv)

    default_in, default_out = _default_paths(args.month, args.data_dir)
    in_path = args.in_path or default_in
    out_path = args.out_path or default_out

    try:
        stats = convert_proposed_file(in_path, out_path, force=args.force)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        logger.error("%s", e)
        return 1

    print(f"Wrote {out_path}")
    print(
        f"  proposals_used={stats['proposals_used']}  "
        f"brands={stats['brands']}  scents={stats['scents']}  "
        f"new_scent={stats['new_scent']}  new_pattern={stats['new_pattern']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
