#!/usr/bin/env bash
# Publish the slim public data bundle to the NAS (or any rsync target).
# Usage: scripts/publish-public-data.sh [TARGET]
#   TARGET default: nas:sotd-public/data   (ssh alias + path; can be a local dir)
# Env: SOTD_PUBLIC_DATA_TARGET overrides the default target.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-${SOTD_PUBLIC_DATA_TARGET:-nas:sotd-public/data}}"

echo "==> verifying bundle completeness"
python scripts/publish_public_data.py --check --data-dir data

echo "==> rsyncing bundle to $TARGET"
rsync -a --delete data/aggregated/product_usage/ "$TARGET/aggregated/product_usage/"
rsync -a --delete data/aggregated/user_analysis/ "$TARGET/aggregated/user_analysis/"
rsync -a --delete data/aggregated/annual/        "$TARGET/aggregated/annual/"
rsync -a --delete --include='????-??.json' --exclude='*' data/aggregated/ "$TARGET/aggregated/"

echo "done. bundle at $TARGET"
