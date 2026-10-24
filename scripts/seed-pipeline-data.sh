#!/usr/bin/env bash
# One-time seed of the NAS pipeline data volume from the Mac's data/ tree.
# Excludes non-pipeline inputs (backups, logs, raw scrape cache) per spec 2026-10-24.
set -euo pipefail
cd "$(dirname "$0")/.."

TARGET="${1:-nas:/volume1/docker/sotd-pipeline/data}"

echo "==> verifying no stray files (post-2026-10-24 audit)"
find data -name '.DS_Store' -o -name '*.backup' -o -name '*.bak' -o -name '*.bk' | grep . && {
  echo "stray files found — clean first"; exit 1; } || true

echo "==> creating remote dirs"
ssh nas 'mkdir -p /volume1/docker/sotd-pipeline/data /volume1/docker/sotd-pipeline/repo'

echo "==> seeding $TARGET"
rsync -a \
  --exclude='.DS_Store' \
  --exclude='*.backup' --exclude='*.bak' --exclude='*.bk' \
  --exclude='backup/' --exclude='logs/' --exclude='learning/' \
  --exclude='report_archive/_reddit_raw/' \
  data/ "$TARGET/"

echo "done. seed at $TARGET"
