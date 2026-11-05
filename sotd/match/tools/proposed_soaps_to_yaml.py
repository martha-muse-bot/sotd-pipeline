"""Convert data/proposed/YYYY-MM.json soap proposals into soaps.yaml-shaped YAML."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from sotd.cli_utils.date_span import iter_months, parse_ym

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


def load_proposals(in_path: Path) -> list[dict[str, Any]]:
    """Load proposal list from a proposed JSON file."""
    if not in_path.exists():
        raise FileNotFoundError(f"Proposed file not found: {in_path}")

    raw = json.loads(in_path.read_text(encoding="utf-8"))
    if isinstance(raw, list):
        proposals = raw
    elif isinstance(raw, dict):
        proposals = raw.get("proposals") or []
    else:
        raise ValueError(f"Unexpected proposed file shape in {in_path}")

    if not isinstance(proposals, list):
        raise ValueError(f"'proposals' must be a list in {in_path}")
    return proposals


def write_catalog_yaml(fragment: dict[str, Any], out_path: Path, *, force: bool = False) -> None:
    """Write catalog fragment YAML, respecting --force overwrite rules."""
    if out_path.exists() and not force:
        raise FileExistsError(f"Output exists (use --force to overwrite): {out_path}")
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


def _stats_for(kept: list[dict[str, Any]], fragment: dict[str, Any]) -> dict[str, int]:
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


def convert_proposed_file(
    in_path: Path,
    out_path: Path,
    *,
    force: bool = False,
) -> dict[str, int]:
    """Load proposed JSON, write catalog-shaped YAML, return summary stats."""
    kept = filter_soap_proposals(load_proposals(in_path))
    fragment = build_catalog_fragment(kept)
    write_catalog_yaml(fragment, out_path, force=force)
    return _stats_for(kept, fragment)


def convert_proposed_months(
    months: list[str],
    data_dir: Path,
    out_path: Path,
    *,
    force: bool = False,
) -> tuple[dict[str, int], list[str]]:
    """
    Merge proposals from multiple months into one soaps.yaml-shaped file.

    Returns (stats, missing_months). Writes output if at least one month loaded.
    """
    kept_all: list[dict[str, Any]] = []
    missing: list[str] = []
    for month in months:
        in_path = data_dir / "proposed" / f"{month}.json"
        try:
            kept_all.extend(filter_soap_proposals(load_proposals(in_path)))
        except FileNotFoundError:
            missing.append(month)

    if not kept_all and missing:
        raise FileNotFoundError(
            "No proposed files found for months: " + ", ".join(missing)
        )

    fragment = build_catalog_fragment(kept_all)
    write_catalog_yaml(fragment, out_path, force=force)
    return _stats_for(kept_all, fragment), missing


def parse_month_range(range_str: str) -> list[str]:
    """Expand YYYY-MM:YYYY-MM (inclusive) into month strings."""
    if ":" not in range_str:
        raise ValueError("Date range must be in YYYY-MM:YYYY-MM format")
    parts = range_str.split(":")
    if len(parts) != 2:
        raise ValueError("Date range must be in YYYY-MM:YYYY-MM format")
    start = parse_ym(parts[0])
    end = parse_ym(parts[1])
    if start > end:
        raise ValueError("Start month must be on or before end month")
    return [f"{y:04d}-{m:02d}" for y, m in iter_months(start, end)]


def months_for_args(*, month: str | None, range_str: str | None) -> list[str]:
    """Resolve --month or --range into an ordered list of YYYY-MM strings."""
    if month and range_str:
        raise ValueError("Provide only one of --month or --range")
    if month:
        return [month]
    if range_str:
        return parse_month_range(range_str)
    raise ValueError("Must provide --month or --range")


def _default_month_paths(month: str, data_dir: Path) -> tuple[Path, Path]:
    in_path = data_dir / "proposed" / f"{month}.json"
    out_path = data_dir / "proposed" / "soaps" / f"{month}.yaml"
    return in_path, out_path


def _default_range_out_path(data_dir: Path) -> Path:
    return data_dir / "proposed" / "soaps.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Convert data/proposed/YYYY-MM.json soap proposals into a "
            "soaps.yaml-shaped YAML fragment for manual review and copy/paste. "
            "--month writes data/proposed/soaps/{month}.yaml; "
            "--range merges into data/proposed/soaps.yaml."
        )
    )
    date_group = parser.add_mutually_exclusive_group(required=True)
    date_group.add_argument(
        "--month",
        help="Month (YYYY-MM) — writes data/proposed/soaps/{month}.yaml by default",
    )
    date_group.add_argument(
        "--range",
        dest="range_str",
        help="Inclusive month range (YYYY-MM:YYYY-MM) — merges into data/proposed/soaps.yaml",
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
        help="Override input proposed JSON path (single --month only)",
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
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.range_str and args.in_path is not None:
        print("--in is only valid with --month, not --range", file=sys.stderr)
        return 2

    try:
        months = months_for_args(month=args.month, range_str=args.range_str)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    if args.range_str:
        out_path = args.out_path or _default_range_out_path(args.data_dir)
        try:
            stats, missing = convert_proposed_months(
                months,
                args.data_dir,
                out_path,
                force=args.force,
            )
        except (FileNotFoundError, FileExistsError, ValueError) as e:
            print(str(e), file=sys.stderr)
            return 1

        for month in missing:
            print(f"Proposed file not found: data/proposed/{month}.json", file=sys.stderr)
        print(f"Wrote {out_path}")
        print(
            f"  proposals_used={stats['proposals_used']}  "
            f"brands={stats['brands']}  scents={stats['scents']}  "
            f"new_scent={stats['new_scent']}  new_pattern={stats['new_pattern']}"
        )
        return 1 if missing else 0

    # Single --month
    month = months[0]
    default_in, default_out = _default_month_paths(month, args.data_dir)
    in_path = args.in_path or default_in
    out_path = args.out_path or default_out
    try:
        stats = convert_proposed_file(in_path, out_path, force=args.force)
    except (FileNotFoundError, FileExistsError, ValueError) as e:
        print(str(e), file=sys.stderr)
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
