"""Materialize praw.ini from REDDIT_* env vars (komodo resource env).

A mounted praw.ini wins over env materialization (operator override path).
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

PRAW_INI_TEMPLATE = """[app]
client_id={client_id}
client_secret={client_secret}
username={username}
password={password}
"""

REQUIRED = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
    "REDDIT_USERNAME",
    "REDDIT_PASSWORD",
)


def materialize_praw_ini(env: Mapping[str, str], target_dir: Path) -> Path | None:
    existing = target_dir / "praw.ini"
    if existing.exists():
        return existing
    if not all(env.get(k) for k in REQUIRED):
        return None
    existing.write_text(
        PRAW_INI_TEMPLATE.format(
            client_id=env["REDDIT_CLIENT_ID"],
            client_secret=env["REDDIT_CLIENT_SECRET"],
            username=env["REDDIT_USERNAME"],
            password=env["REDDIT_PASSWORD"],
        )
    )
    return existing
