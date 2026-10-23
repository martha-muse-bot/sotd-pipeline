#!/usr/bin/env python3
"""Verify the slim public data bundle before publishing.

Bundle = aggregated slices the public routers read:
  aggregated/{YYYY-MM}.json, aggregated/user_analysis/, aggregated/product_usage/,
  aggregated/annual/ (optional). enriched/ must NOT be present in the target.
"""

import argparse
import re
import sys
from pathlib import Path

MONTH_RE = re.compile(r"^\d{4}-\d{2}$")


def _months_in(dir_path: Path) -> set:
    if not dir_path.is_dir():
        return set()
    return {p.stem for p in dir_path.glob("*.json") if MONTH_RE.match(p.stem)}


def check_bundle(data_dir: Path) -> list:
    """Return a list of human-readable problems; empty list = bundle is publishable."""
    problems = []
    agg = data_dir / "aggregated"
    month_files = _months_in(agg)
    ua = _months_in(agg / "user_analysis")
    pu = _months_in(agg / "product_usage")

    # Guard: an empty/missing aggregated dir would make the wrapper's --delete
    # rsyncs wipe every published month on the target. Refuse to publish.
    if not (month_files | ua | pu):
        problems.append(
            "aggregated/ is empty or missing — refusing to publish an empty bundle "
            "(would --delete the target)"
        )

    for m in sorted(month_files | ua | pu):
        if m not in month_files:
            problems.append(f"{m}: missing aggregated/{m}.json (rank tables)")
        if m not in ua:
            problems.append(f"{m}: missing aggregated/user_analysis/{m}.json")
        if m not in pu:
            problems.append(f"{m}: missing aggregated/product_usage/{m}.json")

    # Tripwire: a stray enriched/ inside the bundle tree would mean enriched data
    # leaked into the published set. (The pipeline's data root legitimately has a
    # top-level enriched/ sibling next to aggregated/ — that one is never published
    # by the rsync selection, so it must not block the check.)
    if (agg / "enriched").exists():
        problems.append("aggregated/enriched present in bundle source — must never be published")

    return problems


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data-dir", type=Path, default=Path("data"))
    ap.add_argument("--check", action="store_true", help="verify only; no copying")
    args = ap.parse_args()
    problems = check_bundle(args.data_dir)
    for p in problems:
        print(f"PROBLEM: {p}", file=sys.stderr)
    if problems:
        return 1
    print("bundle complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
