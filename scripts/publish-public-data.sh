#!/usr/bin/env bash
# Publish the slim public data bundle to the NAS (or any rsync target).
# Usage: scripts/publish-public-data.sh [TARGET]
#   TARGET default: nas:/volume1/docker/sotd-public/data  (ABSOLUTE — a relative
#   path resolves to the ssh login's HOME on the NAS, which is not the share)
# Env: SOTD_PUBLIC_DATA_TARGET overrides the default target.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-${SOTD_PUBLIC_DATA_TARGET:-nas:/volume1/docker/sotd-public/data}}"

echo "==> precomputing home overview"
./.venv/bin/python scripts/precompute_home_overview.py --data-dir data

echo "==> verifying bundle completeness"
./.venv/bin/python scripts/publish_public_data.py --check --data-dir data

echo "==> rsyncing bundle to $TARGET"
rsync -a --delete data/aggregated/product_usage/ "$TARGET/aggregated/product_usage/"
rsync -a --delete data/aggregated/user_analysis/ "$TARGET/aggregated/user_analysis/"
rsync -a --delete data/aggregated/annual/        "$TARGET/aggregated/annual/"
rsync -a --delete data/aggregated/rankings/      "$TARGET/aggregated/rankings/"
rsync -a --delete --include='????-??.json' --include='home_overview.json' --include='monthly_user_posts_months.json' --exclude='*' data/aggregated/ "$TARGET/aggregated/"

echo "done. bundle at $TARGET"
