#!/usr/bin/env bash
# Pipeline supervisor entrypoint: clone /app on first boot, materialize
# praw.ini, then exec the supervisor loop. A mounted praw.ini wins over
# env vars. Clone FIRST — a file-mount placed praw.ini in APP_DIR makes
# the directory non-empty, and git refuses to clone into a non-empty dir.
set -euo pipefail

APP_DIR="${APP_DIR:-/app}"
REPO_URL="${REPO_URL:-https://github.com/nmrs/sotd-pipeline.git}"
SECRETS_DIR="${PRAW_INI_DIR:-/secrets}"
export PYTHONPATH=/app

if [ ! -d "${APP_DIR}/.git" ]; then
  git clone "${REPO_URL}" "${APP_DIR}"
fi

# praw.ini: mounted file wins; else materialize from REDDIT_* env
if [ ! -f "${APP_DIR}/praw.ini" ] && [ -f "${SECRETS_DIR}/praw.ini" ]; then
  cp "${SECRETS_DIR}/praw.ini" "${APP_DIR}/praw.ini"
fi

cd "${APP_DIR}"

# The repo lives on a volume; its owner uid can differ from this process's uid
# across container recreations — mark it safe so git operations never fail
# with "dubious ownership".
git config --global --add safe.directory "${APP_DIR}"

python -m sotd.pipeline_supervisor.materialize  # writes ${APP_DIR}/praw.ini if needed
exec python -m sotd.pipeline_supervisor.loop
