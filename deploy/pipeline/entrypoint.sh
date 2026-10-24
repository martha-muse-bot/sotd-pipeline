#!/usr/bin/env bash
# Pipeline supervisor entrypoint: materialize praw.ini, clone /app on first
# boot, then exec the supervisor loop. A mounted praw.ini wins over env vars.
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
REPO_URL="${REPO_URL:-https://github.com/nmrs/sotd-pipeline.git}"
SECRETS_DIR="${PRAW_INI_DIR:-/secrets}"
export PYTHONPATH=/app

# praw.ini: mounted file wins; else materialize from REDDIT_* env
mkdir -p "${APP_DIR}"
if [ ! -f "${APP_DIR}/praw.ini" ] && [ -f "${SECRETS_DIR}/praw.ini" ]; then
  cp "${SECRETS_DIR}/praw.ini" "${APP_DIR}/praw.ini"
fi

if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
fi
cd "${APP_DIR}"

python -m sotd.pipeline_supervisor.materialize  # writes /app/praw.ini if needed
exec python -m sotd.pipeline_supervisor.loop
