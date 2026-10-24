"""Content hash over operator-authored match inputs.

Scope (spec 2026-10-24): data/*.yaml catalogs, correct_matches/*.yaml, the
three overrides files, intentionally_unmatched.yaml. Everything else —
aggregated output, .status* working files, wsdb — is excluded so code-only
git pulls never trigger the all-months catch-up.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

CATALOG_HASH_INPUTS = (
    "*.yaml",
    "correct_matches/*.yaml",
    "thread_overrides.yaml",
    "extract_overrides.yaml",
    "enrichment_overrides.yaml",
    "intentionally_unmatched.yaml",
)


def catalog_hash(data_dir: Path) -> str:
    digest = hashlib.sha256()
    for rel in sorted(_hashable_files(data_dir)):
        fhash = hashlib.sha256((data_dir / rel).read_bytes()).hexdigest()
        digest.update(f"{rel}:{fhash}\n".encode())
    return digest.hexdigest()


def _hashable_files(data_dir: Path) -> list[str]:
    seen: set[str] = set()
    for pattern in CATALOG_HASH_INPUTS:
        for p in sorted(data_dir.glob(pattern)):
            if p.is_file():
                seen.add(p.relative_to(data_dir).as_posix())
    return sorted(seen)
