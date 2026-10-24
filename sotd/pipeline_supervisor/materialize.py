"""Entrypoint helper: materialize /app/praw.ini from env (no-op if present)."""

import os
from pathlib import Path

from sotd.pipeline_supervisor.secrets import materialize_praw_ini

if __name__ == "__main__":
    materialize_praw_ini(dict(os.environ), Path("/app"))
