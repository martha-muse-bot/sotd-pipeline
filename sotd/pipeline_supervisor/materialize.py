"""Entrypoint helper: materialize praw.ini into APP_DIR from env (no-op if present)."""

import os
from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

if __name__ == "__main__":
    materialize_praw_ini(dict(os.environ), Path(os.environ.get("APP_DIR", "/app")))
