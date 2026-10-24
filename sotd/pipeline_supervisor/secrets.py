"""Materialize praw.ini from REDDIT_* env vars (komodo resource env).

A mounted praw.ini wins over env materialization (operator override path).

praw.Reddit() with no site_name reads the DEFAULT section (a named section
like [app] is silently ignored -> MissingRequiredAttributeException), and
praw hard-requires user_agent — so the template writes [DEFAULT] with
client_id/client_secret/user_agent. username/password are optional extras
(fetch is read-only); they are written only when their env vars are set.
The ini text is assembled line-by-line (no str.format template), so braces
in secret values stay literal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Mapping

DEFAULT_USER_AGENT = "sotd-pipeline-supervisor"

REQUIRED = (
    "REDDIT_CLIENT_ID",
    "REDDIT_CLIENT_SECRET",
)


def _render(
    client_id: str,
    client_secret: str,
    user_agent: str,
    username: str | None = None,
    password: str | None = None,
) -> str:
    lines = [
        "[DEFAULT]",
        f"client_id={client_id}",
        f"client_secret={client_secret}",
        f"user_agent={user_agent}",
    ]
    if username is not None:
        lines.append(f"username={username}")
    if password is not None:
        lines.append(f"password={password}")
    return "\n".join(lines) + "\n"


def materialize_praw_ini(env: Mapping[str, str], target_dir: Path) -> Path | None:
    existing = target_dir / "praw.ini"
    if existing.exists():
        return existing
    if not all(env.get(k) for k in REQUIRED):
        return None
    user_agent = env.get("REDDIT_USER_AGENT") or DEFAULT_USER_AGENT
    text = _render(
        env["REDDIT_CLIENT_ID"],
        env["REDDIT_CLIENT_SECRET"],
        user_agent,
        env.get("REDDIT_USERNAME") or None,
        env.get("REDDIT_PASSWORD") or None,
    )
    existing.write_text(text)
    return existing
