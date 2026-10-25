#!/usr/bin/env python3
"""Precompute the public home-overview payload into the aggregated bundle.

Writes data/aggregated/home_overview.json (the exact payload /api/home/overview
serves) so the public dashboard reads one small file instead of parsing ~100MB
of monthly slices per page view. Runs in the publish flow — the bundle only
changes when the pipeline re-aggregates, so the payload is safe to precompute.
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webui.api.home_overview_builder import build_overview, write_precomputed  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="pipeline data dir (default: data)")
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    out = write_precomputed(data_dir)
    payload = build_overview(data_dir)
    latest = payload.get("latest_month")
    pulse_months = len(payload.get("pulse") or [])
    print(f"wrote {out} (latest_month={latest}, pulse_months={pulse_months})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
