#!/usr/bin/env python3
"""Precompute the public API's pre-derived payloads into the aggregated bundle.

Writes (all served as fast paths by the public API, all safe to precompute
because the bundle only changes when the pipeline re-aggregates):
  - aggregated/home_overview.json            (dashboard: pulse/tiles/movers)
  - aggregated/monthly_user_posts_months.json (monthly-user-posts month list)
  - aggregated/rankings/<table>.json          (rankings rows per table, all months)

Runs in the publish flow (scripts/publish-public-data.sh) and in the nightly
supervisor before its publish step.
"""

import argparse
import sys
from pathlib import Path

# Allow running as a plain script from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from webui.api.home_overview_builder import (  # noqa: E402
    write_months_list,
    write_precomputed,
    write_rankings_rows,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="pipeline data dir (default: data)")
    parser.add_argument(
        "--skip-rankings",
        action="store_true",
        help="skip the (slowest) per-table rankings rows precompute",
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)

    out = write_precomputed(data_dir)
    payload = __import__(
        "webui.api.home_overview_builder", fromlist=["build_overview"]
    ).build_overview(data_dir)
    print(f"wrote {out} (latest_month={payload.get('latest_month')})")

    out = write_months_list(data_dir)
    print(f"wrote {out}")

    if not args.skip_rankings:
        out = write_rankings_rows(data_dir)
        tables = sorted(p.stem for p in out.glob("*.json"))
        print(
            f"wrote {out}/ ({len(tables)} tables: {', '.join(tables[:5])}{'…' if len(tables) > 5 else ''})"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
