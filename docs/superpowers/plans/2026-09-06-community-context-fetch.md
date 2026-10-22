# Community Context Fetch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fetch the complete r/wetshaving community record for each month (all posts + full comment trees) into `data/community/` and expose it via a `community_query` CLI. Consumption (summarizer agent, observations-drafter wiring) is deferred to a later project.

**Architecture:** A sidecar fetch module (`sotd/fetch/community.py`, wired into `run.py` like the existing `fetch_json` sidecar) stores one JSON file per month under `data/community/`; a fourth report-tools CLI (`community_query`) renders that record into bounded slices (listings, thread trees, windowed search) for shell use and future agent consumers. The deterministic 6-phase pipeline is untouched.

**Tech Stack:** Python 3.14, PRAW (Reddit API), pytest, argparse, existing `sotd.cli_utils` / `sotd.utils` helpers.

**Spec:** `docs/superpowers/specs/2026-09-06-community-context-fetch-design.md` — read it first; this plan argues from it.

## Global Constraints

- Python venv: run everything with `.venv/bin/python` (repo Makefile targets assume it is activated; use `.venv/bin/python -m pytest tests/… -x -q` in steps).
- Python 3.14 (enforced by `pyrightconfig.json`); Black formatting at 100 chars; Ruff rules E, F, I; Pyright recommended settings.
- `--force` is MANDATORY for overwrite-capable pipeline operations (project rule).
- Follow `sotd/fetch/run.py` conventions: `datetime.utcfromtimestamp(...).replace(tzinfo=timezone.utc).isoformat().replace("+00:00", "Z")` for timestamps; authors `"[deleted]"` when None; `merge_records` for non-force re-runs; `safe_call` for all Reddit calls.
- Community data is context-only: nothing in extract→report consumes it; `data/comments/` (top-level-only) is never reused by this fetch.
- `in_pipeline` is enrichment (a filter aid), never an exclusion mechanism; missing threads file → warning only, flag omitted.
- `[removed]`/`[deleted]` bodies and null authors are preserved as-is.
- CLI tools exit 0 on success, 1 on query errors; month/window arguments are always explicit.
- Reddit scores are fuzzed — stored for ranking only, never quoted as facts.

---

## File Structure

| File | Responsibility |
|------|----------------|
| `sotd/fetch/community.py` (create) | Sidecar fetch: discovery (new_listing + backfill strategies), full-tree comments, record building, save/load, month orchestration, CLI entry |
| `run.py` (modify) | Phase dispatch wiring: `community` in `phase_modules` + `all_available_phases` + epilog (fetch_json sidecar pattern) |
| `sotd/report/tools/community_query.py` (create) | Point-query CLI: `meta`, `threads`, `thread`, `search` over `data/community/` |
| `CLAUDE.md` (modify) | Community command + artifact layout + operations runbook |
| `tests/fetch/test_community_fetch.py` (create) | Unit tests for the fetch module (fake PRAW objects, mirroring `tests/fetch/test_fetch.py`) |
| `tests/test_run_phase_range.py` (create) | Dispatch wiring tests for the `community` phase name |
| `tests/report/tools/test_community_query.py` (create) | CLI tests (fixture month files, mirroring `tests/report/tools/test_aggregate_query.py`) |

---

### Task 1: Community storage helpers + record builders

**Files:**
- Create: `sotd/fetch/community.py`
- Test: `tests/fetch/test_community_fetch.py`

**Interfaces:**
- Consumes: `sotd.fetch.save.load_month_file(path) -> (meta, list) | None`; `sotd.fetch.save.write_month_file(path, meta, data)`; `sotd.utils.data_dir.get_data_dir(data_dir) -> Path`; `sotd.utils.file_io.save_json_data(payload, path, indent=2)` / `load_json_data(path) -> dict`.
- Produces (used by Tasks 4, 6, and the CLI): `load_sotd_ids(data_dir, year: int, month: int) -> set[str] | None`, `build_post_record(sub, *, in_pipeline: bool | None) -> dict`, `build_comment_record(c, thread_id: str, thread_title: str) -> dict`, `write_community_file(path: Path, meta: dict, posts: list, comments: list) -> None`, `load_community_file(path: Path) -> tuple[dict, dict] | None`.

- [ ] **Step 1: Write the failing tests**

Create `tests/fetch/test_community_fetch.py`:

```python
"""Tests for the community context fetch module."""

import json
from datetime import datetime, timezone
from pathlib import Path

from sotd.fetch import community
from sotd.fetch.save import write_month_file


def ts(*parts: int) -> int:
    """Epoch seconds for a UTC datetime given as (year, month, day[, h, m, s])."""
    return int(datetime(*parts, tzinfo=timezone.utc).timestamp())


class FakeSub:
    """Duck-typed praw Submission with every field build_post_record reads."""

    def __init__(
        self,
        _id,
        title,
        created_utc,
        *,
        selftext="",
        author="tester",
        score=5,
        num_comments=0,
        flair=None,
        permalink="/p",
        locked=False,
        stickied=False,
    ):
        self.id = _id
        self.title = title
        self.created_utc = created_utc
        self.selftext = selftext
        self.author = author
        self.score = score
        self.num_comments = num_comments
        self.link_flair_text = flair
        self.permalink = permalink
        self.locked = locked
        self.stickied = stickied


class FakeComment:
    def __init__(
        self, _id, body, created_utc, *, parent_id="t3_t1", author="u1", score=1, is_submitter=False
    ):
        self.id = _id
        self.body = body
        self.created_utc = created_utc
        self.parent_id = parent_id
        self.author = author
        self.score = score
        self.is_submitter = is_submitter


class TestBuildPostRecord:
    def test_full_record(self):
        sub = FakeSub(
            "abc123",
            "Hello",
            ts(2026, 9, 1, 6, 0, 9),
            selftext="body text",
            author="someone",
            score=12,
            num_comments=3,
            flair="Discussion",
            permalink="/r/wetshaving/comments/abc123/x/",
        )
        rec = community.build_post_record(sub, in_pipeline=False)
        assert rec == {
            "id": "abc123",
            "title": "Hello",
            "selftext": "body text",
            "author": "someone",
            "created_utc": "2026-09-01T06:00:09Z",
            "score": 12,
            "num_comments": 3,
            "flair": "Discussion",
            "url": "https://www.reddit.com/r/wetshaving/comments/abc123/x/",
            "locked": False,
            "stickied": False,
            "in_pipeline": False,
        }

    def test_deleted_author_and_no_flag_when_unknown(self):
        sub = FakeSub("abc", "T", ts(2026, 9, 1), author=None)
        rec = community.build_post_record(sub, in_pipeline=None)
        assert rec["author"] == "[deleted]"
        assert "in_pipeline" not in rec


class TestBuildCommentRecord:
    def test_full_record(self):
        c = FakeComment(
            "c1",
            "nice shave",
            ts(2026, 9, 2),
            parent_id="t3_abc",
            author="bob",
            score=2,
            is_submitter=True,
        )
        rec = community.build_comment_record(c, "abc", "Thread Title")
        assert rec == {
            "id": "c1",
            "thread_id": "abc",
            "thread_title": "Thread Title",
            "parent_id": "t3_abc",
            "author": "bob",
            "created_utc": "2026-09-02T00:00:00Z",
            "body": "nice shave",
            "score": 2,
            "is_submitter": True,
        }

    def test_deleted_comment_author(self):
        c = FakeComment("c2", "[removed]", ts(2026, 9, 2), author=None)
        assert community.build_comment_record(c, "abc", "T")["author"] == "[deleted]"


class TestCommunityFileRoundTrip:
    def test_write_then_load(self, tmp_path):
        path = tmp_path / "2026-09.json"
        meta = {"month": "2026-09", "post_count": 1, "comment_count": 1}
        posts = [{"id": "abc", "created_utc": "2026-09-01T00:00:00Z"}]
        comments = [{"id": "c1", "created_utc": "2026-09-01T00:00:01Z"}]
        community.write_community_file(path, meta, posts, comments)
        loaded = community.load_community_file(path)
        assert loaded is not None
        assert loaded[0]["month"] == "2026-09"
        assert loaded[1] == {"posts": posts, "comments": comments}
        # on-disk shape is {"meta": ..., "data": {"posts": [...], "comments": [...]}}
        raw = json.loads(path.read_text())
        assert set(raw["data"].keys()) == {"posts", "comments"}

    def test_load_missing_returns_none(self, tmp_path):
        assert community.load_community_file(tmp_path / "nope.json") is None


class TestLoadSotdIds:
    def test_ids_from_threads_file(self, tmp_path):
        write_month_file(
            tmp_path / "threads" / "2026-08.json",
            {"month": "2026-08"},
            [{"id": "t1"}, {"id": "t2"}],
        )
        ids = community.load_sotd_ids(tmp_path, 2026, 8)
        assert ids == {"t1", "t2"}

    def test_none_when_file_missing(self, tmp_path):
        assert community.load_sotd_ids(tmp_path, 2026, 8) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sotd.fetch.community'` (or ImportError on the missing functions).

- [ ] **Step 3: Write the minimal implementation**

Create `sotd/fetch/community.py`:

```python
"""Fetch the full r/wetshaving community record for one or more months.

Every post in the target month (SOTD daily threads included) plus its full
comment tree is stored to ``data/community/YYYY-MM.json``::

    {"meta": {...}, "data": {"posts": [...], "comments": [...]}}

This is a sidecar to the 6-phase pipeline: nothing in extract..report consumes
this data. The ``community_query`` CLI is its access surface (agent consumption
is a later project). The pipeline's own ``data/comments/`` store (top-level SOTD
comments only) is never reused here — everything is fetched fresh from Reddit.
"""

# ruff: noqa: E402  # keep imports after docstring for clarity
from __future__ import annotations

import logging
from datetime import datetime, timezone
from itertools import islice
from typing import List, Optional, Sequence, Set, Tuple

from praw.models import Comment

from sotd.cli_utils.base_parser import BaseCLIParser
from sotd.cli_utils.date_span import month_span
from sotd.fetch.merge import merge_records
from sotd.fetch.reddit import get_reddit, safe_call
from sotd.fetch.save import load_month_file
from sotd.utils.data_dir import get_data_dir
from sotd.utils.file_io import load_json_data, save_json_data
from sotd.utils.logging_config import setup_pipeline_logging, should_disable_tqdm

logger = logging.getLogger(__name__)

# Discovery stops here even if the month boundary was never reached
# (30 batches x 100 posts; a target month needs ~4).
PAGINATION_CAP = 3000


# --------------------------------------------------------------------------- #
# record building                                                             #
# --------------------------------------------------------------------------- #
def _iso(created_utc: float) -> str:
    return (
        datetime.utcfromtimestamp(created_utc)
        .replace(tzinfo=timezone.utc)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_post_record(sub, *, in_pipeline: Optional[bool]) -> dict:
    rec = {
        "id": sub.id,
        "title": sub.title,
        "selftext": getattr(sub, "selftext", "") or "",
        "author": str(sub.author) if sub.author else "[deleted]",
        "created_utc": _iso(sub.created_utc),
        "score": int(getattr(sub, "score", 0) or 0),
        "num_comments": int(getattr(sub, "num_comments", 0) or 0),
        "flair": sub.link_flair_text,
        "url": f"https://www.reddit.com{sub.permalink}",
        "locked": bool(getattr(sub, "locked", False)),
        "stickied": bool(getattr(sub, "stickied", False)),
    }
    if in_pipeline is not None:
        rec["in_pipeline"] = in_pipeline
    return rec


def build_comment_record(c, thread_id: str, thread_title: str) -> dict:
    return {
        "id": c.id,
        "thread_id": thread_id,
        "thread_title": thread_title,
        "parent_id": c.parent_id,
        "author": str(c.author) if c.author else "[deleted]",
        "created_utc": _iso(c.created_utc),
        "body": c.body,
        "score": int(getattr(c, "score", 0) or 0),
        "is_submitter": bool(getattr(c, "is_submitter", False)),
    }


# --------------------------------------------------------------------------- #
# file I/O                                                                    #
# --------------------------------------------------------------------------- #
def write_community_file(path, meta: dict, posts: List[dict], comments: List[dict]) -> None:
    save_json_data({"meta": meta, "data": {"posts": posts, "comments": comments}}, path, indent=2)


def load_community_file(path):
    """Return (meta, {"posts": [...], "comments": [...]}) if the file exists, else None."""
    if not path.is_file():
        return None
    try:
        obj = load_json_data(path)
        return obj["meta"], obj["data"]
    except (KeyError, ValueError):
        return None


def load_sotd_ids(data_dir, year: int, month: int) -> Optional[Set[str]]:
    """Return SOTD thread IDs for the month, or None when the threads file is absent."""
    path = get_data_dir(data_dir) / "threads" / f"{year:04d}-{month:02d}.json"
    existing = load_month_file(path)
    if existing is None:
        return None
    return {t["id"] for t in existing[1]}
```

(Some imports — `month_span`, `merge_records`, `get_reddit`, `BaseCLIParser`,
`setup_pipeline_logging`, `tqdm`, `Comment` — are added now but only used by Tasks
2–4; they would trigger Ruff F401 at this point. If the linter complains after this
task, add the unused ones incrementally in Tasks 2–4 instead. `Comment` is imported
here so tests can monkeypatch `sotd.fetch.community.Comment`; it is used by
`fetch_all_comments` in Task 3.)

To keep Task 1 lint-clean, only these imports are needed NOW; extend the import
block in later tasks as each function lands:

```python
import logging
from datetime import datetime, timezone
from typing import Optional, Set

from sotd.fetch.save import load_month_file
from sotd.utils.data_dir import get_data_dir
from sotd.utils.file_io import load_json_data, save_json_data
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: PASS (all tests in the file).

- [ ] **Step 5: Lint and typecheck the new files**

Run: `.venv/bin/python -m ruff check sotd/fetch/community.py tests/fetch/test_community_fetch.py && .venv/bin/python -m black --check sotd/fetch/community.py tests/fetch/test_community_fetch.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/fetch/community.py tests/fetch/test_community_fetch.py
git commit -m "feat(fetch): community record builders + file I/O helpers"
```

---

### Task 2: Forward discovery — `discover_month_posts`

**Files:**
- Modify: `sotd/fetch/community.py` (append; extend imports)
- Test: `tests/fetch/test_community_fetch.py` (append)

**Interfaces:**
- Consumes: `sotd.fetch.reddit.safe_call(fn, *args, **kwargs)` (rate-limit wrapper; returns None on non-rate-limit failure).
- Produces: `discover_month_posts(subreddit, year: int, month: int) -> tuple[list, bool]` — returns (in-month submissions newest-first, boundary_reached). Task 4 consumes this.

- [ ] **Step 1: Write the failing tests**

Append to `tests/fetch/test_community_fetch.py`:

```python
class FakeSubreddit:
    """new() yields submissions newest-first (Reddit listing order)."""

    def __init__(self, submissions):
        self._subs = submissions

    def new(self, *args, **kwargs):
        yield from self._subs


class TestDiscoverMonthPosts:
    def test_filters_to_month_and_stops_at_boundary(self):
        subs = [
            FakeSub("sep2", "Later", ts(2026, 9, 20)),
            FakeSub("sep1", "First", ts(2026, 9, 1, 0, 0, 5)),
            FakeSub("aug31", "Before", ts(2026, 8, 31, 23, 59, 59)),
        ]
        subreddit = FakeSubreddit(subs)
        in_month, reached = community.discover_month_posts(subreddit, 2026, 9)
        assert [s.id for s in in_month] == ["sep2", "sep1"]
        assert reached is True

    def test_exhausted_listing_counts_as_boundary(self):
        # a young sub whose entire history is inside the month
        subreddit = FakeSubreddit([FakeSub("a", "A", ts(2026, 9, 5))])
        in_month, reached = community.discover_month_posts(subreddit, 2026, 9)
        assert len(in_month) == 1
        assert reached is True

    def test_cap_before_boundary_is_incomplete(self, monkeypatch):
        monkeypatch.setattr(community, "PAGINATION_CAP", 3)
        subs = [FakeSub(f"p{i:03d}", f"P{i}", ts(2026, 9, 15)) for i in range(5)]
        in_month, reached = community.discover_month_posts(FakeSubreddit(subs), 2026, 9)
        assert len(in_month) == 3
        assert reached is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py::TestDiscoverMonthPosts -x -q`
Expected: FAIL with `AttributeError: module 'sotd.fetch.community' has no attribute 'discover_month_posts'`.

- [ ] **Step 3: Write the minimal implementation**

Add to the import block: `from itertools import islice` and `from sotd.fetch.reddit import safe_call`; extend the typing import to `from typing import List, Optional, Set, Tuple`.

Append to `sotd/fetch/community.py`:

```python
def discover_month_posts(subreddit, year: int, month: int) -> Tuple[List, bool]:
    """Pull ``subreddit.new()`` until posts older than the month appear.

    Returns (in_month_posts, boundary_reached). ``in_month_posts`` is
    newest-first. ``boundary_reached`` is False when the pagination cap trips
    before the boundary — the caller must treat that month as partial.
    """
    start = datetime(year, month, 1)
    end_exclusive = datetime(year + 1, 1, 1) if month == 12 else datetime(year, month + 1, 1)

    pulled = safe_call(lambda: list(islice(subreddit.new(limit=None), PAGINATION_CAP)))
    in_month: List = []
    boundary_reached = False
    for sub in pulled or []:
        dt = datetime.utcfromtimestamp(sub.created_utc)
        if dt < start:
            # listings are newest-first: everything after this is older
            boundary_reached = True
            break
        if dt < end_exclusive:
            in_month.append(sub)
    if not boundary_reached and pulled is not None and len(pulled) < PAGINATION_CAP:
        # listing exhausted without crossing the boundary
        boundary_reached = True
    return in_month, boundary_reached
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: PASS (all prior tests too).

- [ ] **Step 5: Lint**

Run: `.venv/bin/python -m ruff check sotd/fetch/community.py tests/fetch/test_community_fetch.py && .venv/bin/python -m black --check sotd/fetch/community.py tests/fetch/test_community_fetch.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/fetch/community.py tests/fetch/test_community_fetch.py
git commit -m "feat(fetch): community discovery via subreddit.new pagination"
```

---

### Task 3: Full-tree comment fetch — `fetch_all_comments`

**Files:**
- Modify: `sotd/fetch/community.py` (append)
- Test: `tests/fetch/test_community_fetch.py` (append)

**Interfaces:**
- Consumes: `praw.models.Comment` (imported in Task 1 — tests monkeypatch it), `safe_call`.
- Produces: `fetch_all_comments(submission) -> list` — every comment at all depths, flattened. Task 4 consumes this.

- [ ] **Step 1: Write the failing tests**

Append to `tests/fetch/test_community_fetch.py`:

```python
class NotComment:
    """Stand-in for praw's MoreComment stubs that survive a failed replace_more."""


class FakeCommentForest:
    def __init__(self, items):
        self._items = items
        self.replace_called = False

    def replace_more(self, limit=None):
        self.replace_called = True

    def list(self):
        return self._items


class TestFetchAllComments:
    def test_walks_full_tree_and_drops_non_comments(self, monkeypatch):
        monkeypatch.setattr(community, "Comment", FakeComment)
        c1 = FakeComment("t1_a", "root", ts(2026, 9, 2), parent_id="t3_abc")
        c2 = FakeComment("t1_b", "reply", ts(2026, 9, 2, 1), parent_id="t1_a")
        more = NotComment()
        sub = FakeSub("abc", "T", ts(2026, 9, 1))
        sub.comments = FakeCommentForest([c1, more, c2])
        result = community.fetch_all_comments(sub)
        assert [c.id for c in result] == ["t1_a", "t1_b"]

    def test_removed_bodies_preserved(self, monkeypatch):
        monkeypatch.setattr(community, "Comment", FakeComment)
        c = FakeComment("t1_x", "[removed]", ts(2026, 9, 2), author=None)
        sub = FakeSub("abc", "T", ts(2026, 9, 1))
        sub.comments = FakeCommentForest([c])
        result = community.fetch_all_comments(sub)
        assert result[0].body == "[removed]"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py::TestFetchAllComments -x -q`
Expected: FAIL with `AttributeError: ... no attribute 'fetch_all_comments'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `sotd/fetch/community.py`:

```python
def fetch_all_comments(submission) -> List:
    """Return every comment under *submission* at all depths.

    Unlike the SOTD fetch (top-level shaves only), community context needs the
    nested replies — that is where the conversation lives. MoreComment stubs
    that survive a failed replace_more are dropped.
    """
    safe_call(submission.comments.replace_more, limit=None)
    return [c for c in submission.comments.list() if isinstance(c, Comment)]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: PASS.

- [ ] **Step 5: Lint**

Run: `.venv/bin/python -m ruff check sotd/fetch/community.py tests/fetch/test_community_fetch.py && .venv/bin/python -m black --check sotd/fetch/community.py tests/fetch/test_community_fetch.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/fetch/community.py tests/fetch/test_community_fetch.py
git commit -m "feat(fetch): full-tree comment collection for community fetch"
```

---

### Task 4: Month orchestration + CLI entry (`_process_month`, `main`)

**Files:**
- Modify: `sotd/fetch/community.py` (append; extend imports)
- Test: `tests/fetch/test_community_fetch.py` (append)

**Interfaces:**
- Consumes: everything from Tasks 1–3; `sotd.cli_utils.base_parser.BaseCLIParser`; `sotd.cli_utils.date_span.month_span(args) -> list[tuple[int, int]]`; `sotd.fetch.merge.merge_records(existing, new) -> list`; `sotd.fetch.reddit.get_reddit()`; `sotd.utils.logging_config.setup_pipeline_logging / should_disable_tqdm`; `tqdm`.
- Produces: `_process_month(year: int, month: int, args, *, reddit) -> dict` (keys: year, month, posts, comments, complete) and `main(argv=None) -> int`. Task 6 extends `_process_month` with the backfill path; `run.py` wiring (Task 5) invokes `main`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/fetch/test_community_fetch.py`:

```python
import logging


def write_threads_fixture(tmp_path, month_ids):
    (tmp_path / "threads").mkdir(exist_ok=True)
    (tmp_path / "threads" / "2026-08.json").write_text(
        json.dumps({"meta": {"month": "2026-08"}, "data": [{"id": i} for i in month_ids]})
    )


class FakeArgs:
    def __init__(self, data_dir, force=True, debug=False, verbose=False):
        self.data_dir = str(data_dir)
        self.force = force
        self.debug = debug
        self.verbose = verbose


class FakeReddit:
    def subreddit(self, _name):
        return FakeSubreddit([])


class TestProcessMonth:
    def test_writes_month_file_with_in_pipeline_flags(self, tmp_path, monkeypatch):
        write_threads_fixture(tmp_path, ["sotd1"])
        posts = [
            FakeSub("sotd1", "SOTD Thread", ts(2026, 8, 1)),
            FakeSub("other1", "Discussion", ts(2026, 8, 2)),
        ]

        def fake_discover(subreddit, year, month):
            return posts, True

        def fake_comments(sub):
            return [
                FakeComment("c1", "body", ts(2026, 8, 2), parent_id=f"t3_{sub.id}"),
                FakeComment("c2", "[removed]", ts(2026, 8, 2, 1), parent_id="t1_c1", author=None),
            ]

        monkeypatch.setattr(community, "discover_month_posts", fake_discover)
        monkeypatch.setattr(community, "fetch_all_comments", fake_comments)
        result = community._process_month(2026, 8, FakeArgs(tmp_path), reddit=FakeReddit())
        assert result == {"year": 2026, "month": 8, "posts": 2, "comments": 4, "complete": True}
        meta, data = community.load_community_file(tmp_path / "community" / "2026-08.json")
        assert meta["month"] == "2026-08"
        assert meta["post_count"] == 2
        assert meta["comment_count"] == 4
        assert meta["in_pipeline_post_count"] == 1
        assert meta["discovery"] == {
            "strategies": ["new_listing"],
            "complete": True,
            "per_strategy": {"new_listing": 2},
        }
        flags = {p["id"]: p["in_pipeline"] for p in data["posts"]}
        assert flags == {"sotd1": True, "other1": False}

    def test_missing_threads_file_warns_and_omits_flag(self, tmp_path, monkeypatch, caplog):
        posts = [FakeSub("solo", "Solo", ts(2026, 8, 3))]
        monkeypatch.setattr(community, "discover_month_posts", lambda s, y, m: (posts, True))
        monkeypatch.setattr(community, "fetch_all_comments", lambda s: [])
        with caplog.at_level(logging.WARNING):
            community._process_month(2026, 8, FakeArgs(tmp_path), reddit=FakeReddit())
        assert "threads file" in caplog.text
        _, data = community.load_community_file(tmp_path / "community" / "2026-08.json")
        assert "in_pipeline" not in data["posts"][0]

    def test_incomplete_boundary_recorded(self, tmp_path, monkeypatch):
        write_threads_fixture(tmp_path, [])
        monkeypatch.setattr(
            community,
            "discover_month_posts",
            lambda s, y, m: ([FakeSub("x", "X", ts(2026, 8, 5))], False),
        )
        monkeypatch.setattr(community, "fetch_all_comments", lambda s: [])
        community._process_month(2026, 8, FakeArgs(tmp_path), reddit=FakeReddit())
        meta, _ = community.load_community_file(tmp_path / "community" / "2026-08.json")
        assert meta["discovery"]["complete"] is False

    def test_empty_month_writes_no_file(self, tmp_path, monkeypatch):
        write_threads_fixture(tmp_path, [])
        monkeypatch.setattr(community, "discover_month_posts", lambda s, y, m: ([], True))
        monkeypatch.setattr(community, "fetch_all_comments", lambda s: [])
        result = community._process_month(2026, 8, FakeArgs(tmp_path), reddit=FakeReddit())
        assert result["posts"] == 0
        assert not (tmp_path / "community" / "2026-08.json").exists()

    def test_rerun_without_force_merges(self, tmp_path, monkeypatch):
        write_threads_fixture(tmp_path, [])
        monkeypatch.setattr(community, "fetch_all_comments", lambda s: [])
        monkeypatch.setattr(
            community,
            "discover_month_posts",
            lambda s, y, m: ([FakeSub("a", "A", ts(2026, 8, 1))], True),
        )
        community._process_month(2026, 8, FakeArgs(tmp_path), reddit=FakeReddit())
        # second run: post "a" moved to a later timestamp, plus new post "b"
        posts = [FakeSub("a", "A edited", ts(2026, 8, 1, 12)), FakeSub("b", "B", ts(2026, 8, 2))]
        monkeypatch.setattr(community, "discover_month_posts", lambda s, y, m: (posts, True))
        community._process_month(2026, 8, FakeArgs(tmp_path, force=False), reddit=FakeReddit())
        _, data = community.load_community_file(tmp_path / "community" / "2026-08.json")
        by_id = {p["id"]: p for p in data["posts"]}
        assert set(by_id) == {"a", "b"}
        assert by_id["a"]["title"] == "A edited"


class TestMain:
    def test_main_runs_months(self, tmp_path, monkeypatch):
        calls = []

        def fake_process(y, m, args, *, reddit):
            calls.append((y, m))
            return {"year": y, "month": m, "posts": 1, "comments": 0, "complete": True}

        monkeypatch.setattr(community, "_process_month", fake_process)
        monkeypatch.setattr(community, "get_reddit", lambda: FakeReddit())
        code = community.main(["--month", "2026-08", "--force", "--data-dir", str(tmp_path)])
        assert code == 0
        assert calls == [(2026, 8)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py::TestProcessMonth tests/fetch/test_community_fetch.py::TestMain -x -q`
Expected: FAIL with `AttributeError: ... no attribute '_process_month'`.

- [ ] **Step 3: Write the minimal implementation**

Extend the import block: `from typing import List, Optional, Sequence, Set, Tuple`; add `from tqdm import tqdm`; add `from sotd.cli_utils.base_parser import BaseCLIParser`; add `from sotd.cli_utils.date_span import month_span`; add `from sotd.fetch.merge import merge_records`; add `from sotd.fetch.reddit import get_reddit` (extend the existing safe_call import line); add `from sotd.utils.logging_config import setup_pipeline_logging, should_disable_tqdm`.

Append to `sotd/fetch/community.py`:

```python
# --------------------------------------------------------------------------- #
# month orchestration                                                         #
# --------------------------------------------------------------------------- #
def _process_month(year: int, month: int, args, *, reddit) -> dict:
    """Fetch + merge + save the community record for one calendar month."""
    month_str = f"{year:04d}-{month:02d}"
    data_dir = get_data_dir(args.data_dir)
    out_path = data_dir / "community" / f"{month_str}.json"

    sotd_ids = load_sotd_ids(args.data_dir, year, month)
    if sotd_ids is None:
        logger.warning(f"No threads file for {month_str}; posts will lack the in_pipeline flag")

    if args.force and out_path.exists():
        out_path.unlink()

    subreddit = reddit.subreddit("wetshaving")
    posts_new, boundary_reached = discover_month_posts(subreddit, year, month)
    if not boundary_reached:
        logger.warning(
            f"{month_str}: pagination cap reached before month boundary; discovery incomplete"
        )

    new_posts = [
        build_post_record(s, in_pipeline=None if sotd_ids is None else s.id in sotd_ids)
        for s in posts_new
    ]

    new_comments: List[dict] = []
    for sub in tqdm(posts_new, desc="Threads", unit="thread", disable=should_disable_tqdm()):
        for c in fetch_all_comments(sub) or []:
            new_comments.append(build_comment_record(c, sub.id, sub.title))

    existing = None if args.force else load_community_file(out_path)
    if existing is not None:
        _existing_meta, existing_data = existing
        posts = merge_records(existing_data["posts"], new_posts)
        comments = merge_records(existing_data["comments"], new_comments)
    else:
        posts = sorted(new_posts, key=lambda r: r["created_utc"])
        comments = sorted(new_comments, key=lambda r: r["created_utc"])

    if not posts and not comments and existing is None:
        logger.warning(f"No community data found for {month_str}; skipping file write.")
        return {
            "year": year,
            "month": month,
            "posts": 0,
            "comments": 0,
            "complete": boundary_reached,
        }

    meta = {
        "month": month_str,
        "extracted_at": datetime.utcnow().replace(tzinfo=timezone.utc).isoformat(),
        "post_count": len(posts),
        "comment_count": len(comments),
        "in_pipeline_post_count": sum(1 for p in posts if p.get("in_pipeline")),
        "discovery": {
            "strategies": ["new_listing"],
            "complete": boundary_reached,
            "per_strategy": {"new_listing": len(posts_new)},
        },
    }
    write_community_file(out_path, meta, posts, comments)
    if getattr(args, "verbose", False):
        logger.info(
            f"Community fetch complete for {month_str}: "
            f"{len(posts)} posts, {len(comments)} comments"
        )
    return {
        "year": year,
        "month": month,
        "posts": len(posts),
        "comments": len(comments),
        "complete": boundary_reached,
    }


# --------------------------------------------------------------------------- #
# CLI                                                                         #
# --------------------------------------------------------------------------- #
def get_parser() -> BaseCLIParser:
    return BaseCLIParser(
        description="Fetch the full community record (all posts + full comment trees)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    setup_pipeline_logging(level=logging.INFO)
    try:
        parser = get_parser()
        args = parser.parse_args(argv)
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)

        months = month_span(args)
        reddit = get_reddit()

        results = []
        for year, month in tqdm(months, desc="Months", unit="month", disable=should_disable_tqdm()):
            results.append(_process_month(year, month, args, reddit=reddit))

        if results and getattr(args, "verbose", False):
            total_posts = sum(r["posts"] for r in results)
            total_comments = sum(r["comments"] for r in results)
            incomplete = [f"{r['year']:04d}-{r['month']:02d}" for r in results if not r["complete"]]
            logger.info(
                f"Community fetch complete: {total_posts} posts, {total_comments} comments"
                + (f"; incomplete discovery: {', '.join(incomplete)}" if incomplete else "")
            )
        return 0
    except KeyboardInterrupt:
        logger.info("Community fetch interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Community fetch failed: {e}")
        import traceback

        traceback.print_exc()
        return 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: PASS.

- [ ] **Step 5: Lint and typecheck**

Run: `.venv/bin/python -m ruff check sotd/fetch/community.py tests/fetch/test_community_fetch.py && .venv/bin/python -m black --check sotd/fetch/community.py tests/fetch/test_community_fetch.py`
Expected: no findings. (Pyright: duck-typed `args`/`reddit` params match the existing `sotd/fetch/run.py` pattern.)

- [ ] **Step 6: Commit**

```bash
git add sotd/fetch/community.py tests/fetch/test_community_fetch.py
git commit -m "feat(fetch): community month orchestration + CLI entry"
```

---

### Task 5: Wire `community` into `run.py` (fetch_json sidecar pattern)

**Files:**
- Modify: `run.py:468-476` (phase_modules), `run.py:766-777` (all_available_phases), `run.py:873-910` (epilog)
- Test: `tests/test_run_phase_range.py` (create)

**Interfaces:**
- Consumes: `run.py`'s existing `parse_phase_range` and `run_phase` machinery (no signature changes).
- Produces: `python run.py community --month YYYY-MM --force` dispatches to `sotd.fetch.community.main`. `community` is single-phase only — ranges like `fetch:community` raise ValueError by design (sidecar, not part of the phase chain); the default `""` phase list still excludes it.

- [ ] **Step 1: Write the failing test**

Create `tests/test_run_phase_range.py`:

```python
"""Tests for community-phase wiring in the root run.py dispatch."""

import pytest

from run import parse_phase_range


def test_community_single_phase():
    assert parse_phase_range("community") == ["community"]


def test_default_pipeline_excludes_community():
    assert parse_phase_range("") == ["fetch", "extract", "match", "enrich", "aggregate", "report"]


def test_fetch_json_still_excluded_from_default():
    assert "fetch_json" not in parse_phase_range("")


def test_ranges_involving_community_are_rejected():
    with pytest.raises(ValueError):
        parse_phase_range("fetch:community")
    with pytest.raises(ValueError):
        parse_phase_range("community:report")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_run_phase_range.py -x -q`
Expected: FAIL — `test_community_single_phase` raises `ValueError: Invalid phase: community`.

- [ ] **Step 3: Implement the wiring**

Three edits in `run.py`:

1. `phase_modules` map (line ~468): add after the `"fetch_json"` entry:

```python
        "community": "sotd.fetch.community",  # community context sidecar (not a pipeline phase)
```

2. `all_available_phases` (line ~768): add `"community"` as the LAST element (after `"report"`):

```python
    all_available_phases = [
        "fetch",
        "fetch_json",
        "extract",
        "match",
        "enrich",
        "aggregate",
        "report",
        "community",
    ]
```

   (Appending last keeps `fetch:community` ranges invalid — for non-fetch_json ranges `phases_for_range` is `all_phases`, which stays the 6 pipeline phases, so `fetch:community` raises "Invalid end phase: community" with a clear message. Single-phase `community` works because the single-phase branch checks `all_available_phases`.)

3. Epilog (line ~873): add one line to the "Pipeline Phases:" block after `report`:

```
  community  - Fetch all posts + full comment trees (community context sidecar)
```

and one example line under the examples:

```
  python run.py community --month 2025-05 --force  # Fetch community context
```

Note: `run_phase` passes date args, `--data-dir`, `--debug`, and `--force` through automatically (the "Pass through all other arguments" branch), so no argument-filtering changes are needed.

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/test_run_phase_range.py -x -q`
Expected: PASS.

- [ ] **Step 5: Smoke-test dispatch (no Reddit call)**

Run: `.venv/bin/python run.py community --help 2>&1 | head -5`
Expected: prints usage for "Fetch the full community record (all posts + full comment trees)".

- [ ] **Step 6: Commit**

```bash
git add run.py tests/test_run_phase_range.py
git commit -m "feat(run): wire community sidecar command into phase dispatch"
```

---

### Task 6: Backfill discovery strategies (thread-seed, timestamp search, author histories)

**Files:**
- Modify: `sotd/fetch/community.py` (append; extend `_process_month`)
- Test: `tests/fetch/test_community_fetch.py` (append)

**Interfaces:**
- Consumes: `discover_month_posts` (Task 2), `load_sotd_ids` (Task 1), `safe_call`, `reddit.submission(id=...)` / `reddit.redditor(name)` / `subreddit.search(...)`, `load_month_file` (for era authors).
- Produces: `discover_via_search(subreddit, start_ts: int, end_ts: int) -> list`; `era_authors(data_dir, months: Sequence[str], top_n: int = 100) -> list[str]`; `discover_via_authors(reddit, authors: Sequence[str], start_ts: int, end_ts: int) -> list`; `_backfill_posts(reddit, subreddit, year: int, month: int, sotd_ids: set | None, data_dir) -> tuple[list, list[str], dict]` — (posts, strategies_used, per_strategy_raw_counts). `_process_month` calls `_backfill_posts` when `discover_month_posts` reports `boundary_reached=False`, unions the results, and merges `per_strategy` into `meta.discovery`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/fetch/test_community_fetch.py`:

```python
class FakeRedditor:
    def __init__(self, submissions):
        self.submissions = self  # exposes .submissions.new(limit=...)
        self._subs = submissions

    def new(self, limit=None):
        yield from self._subs


class SearchSubreddit(FakeSubreddit):
    """search() parses the lucene timestamp: query and filters by it."""

    def search(self, query, sort=None, syntax=None, time_filter=None):
        import re

        m = re.search(r"timestamp:(\d+)\.\.(\d+)", query)
        lo, hi = int(m.group(1)), int(m.group(2))
        for s in self._subs:
            if lo <= s.created_utc <= hi:
                yield s


class BadSub:
    def search(self, *a, **k):
        raise RuntimeError("unsupported")


class TestDiscoverViaSearch:
    def test_timestamp_window_query(self):
        subs = [
            FakeSub("in1", "In", ts(2025, 7, 10)),
            FakeSub("out", "Out", ts(2025, 6, 10)),
        ]
        subreddit = SearchSubreddit(subs)
        result = community.discover_via_search(subreddit, ts(2025, 7, 1), ts(2025, 8, 1))
        assert [s.id for s in result] == ["in1"]

    def test_empty_on_unsupported_syntax(self):
        # safe_call swallows RuntimeError -> None -> []
        assert community.discover_via_search(BadSub(), 0, 1) == []


class TestEraAuthors:
    def test_ranks_by_comment_count(self, tmp_path):
        (tmp_path / "comments").mkdir()
        comments = [
            {"id": "x1", "author": "busy", "created_utc": "2025-07-01T00:00:00Z"},
            {"id": "x2", "author": "busy", "created_utc": "2025-07-02T00:00:00Z"},
            {"id": "x3", "author": "quiet", "created_utc": "2025-07-03T00:00:00Z"},
            {"id": "x4", "author": "[deleted]", "created_utc": "2025-07-04T00:00:00Z"},
        ]
        (tmp_path / "comments" / "2025-07.json").write_text(
            json.dumps({"meta": {"month": "2025-07"}, "data": comments})
        )
        authors = community.era_authors(tmp_path, ["2025-07"])
        assert authors == ["busy", "quiet"]


class TestDiscoverViaAuthors:
    def test_filters_window_and_dedupes(self):
        a1 = FakeSub("a1", "A1", ts(2025, 7, 5))
        a2 = FakeSub("a2", "A2", ts(2025, 7, 20))
        old = FakeSub("old", "Old", ts(2025, 5, 1))

        class FakeReddit:
            def __init__(self):
                self._people = {"alice": FakeRedditor([a1, old]), "bob": FakeRedditor([a2])}

            def redditor(self, name):
                return self._people[name]

        reddit = FakeReddit()
        result = community.discover_via_authors(
            reddit, ["alice", "alice", "bob"], ts(2025, 7, 1), ts(2025, 8, 1)
        )
        assert sorted(s.id for s in result) == ["a1", "a2"]


class TestBackfillPosts:
    def test_union_seeds_search_and_authors(self, monkeypatch, tmp_path):
        sotd_sub = FakeSub("sotd1", "SOTD Thread", ts(2025, 7, 4))
        search_hit = FakeSub("sr1", "From search", ts(2025, 7, 11))
        author_hit = FakeSub("au1", "From author", ts(2025, 7, 21))

        write_threads_fixture(tmp_path, ["sotd1"])

        class FakeReddit:
            def submission(self, **kwargs):
                assert kwargs.get("id") == "sotd1"
                return sotd_sub

            def subreddit(self, _name):
                return SearchSubreddit([search_hit])

            def redditor(self, name):
                return FakeRedditor([author_hit])

        monkeypatch.setattr(community, "era_authors", lambda d, months, top_n=100: ["alice"])
        posts, strategies, per_strategy = community._backfill_posts(
            FakeReddit(), FakeSubreddit([]), 2025, 7, {"sotd1"}, tmp_path
        )
        assert {s.id for s in posts} == {"sotd1", "sr1", "au1"}
        assert strategies == ["thread_seed", "timestamp_search", "author_histories"]
        assert per_strategy == {"thread_seed": 1, "timestamp_search": 1, "author_histories": 1}

    def test_strategy_omitted_when_empty(self, monkeypatch, tmp_path):
        write_threads_fixture(tmp_path, [])

        class EmptyReddit:
            def submission(self, **kwargs):
                raise RuntimeError("none")

            def subreddit(self, _name):
                return SearchSubreddit([])

            def redditor(self, name):
                return FakeRedditor([])

        monkeypatch.setattr(community, "era_authors", lambda d, m, top_n=100: [])
        posts, strategies, per_strategy = community._backfill_posts(
            EmptyReddit(), FakeSubreddit([]), 2025, 7, set(), tmp_path
        )
        assert posts == []
        assert strategies == []
        assert per_strategy == {"timestamp_search": 0, "author_histories": 0}


class TestProcessMonthBackfill:
    def test_backfill_path_used_when_boundary_unreached(self, tmp_path, monkeypatch):
        write_threads_fixture(tmp_path, ["sotd1"])
        sotd_sub = FakeSub("sotd1", "SOTD Thread", ts(2025, 7, 4))

        monkeypatch.setattr(community, "discover_month_posts", lambda s, y, m: ([], False))

        class FakeReddit:
            def submission(self, **kwargs):
                return sotd_sub

            def subreddit(self, _name):
                return SearchSubreddit([FakeSub("sr1", "S", ts(2025, 7, 11))])

            def redditor(self, name):
                return FakeRedditor([])

        monkeypatch.setattr(community, "era_authors", lambda d, m, top_n=100: [])
        monkeypatch.setattr(community, "fetch_all_comments", lambda s: [])
        result = community._process_month(2025, 7, FakeArgs(tmp_path), reddit=FakeReddit())
        assert result["posts"] == 2 and result["complete"] is False
        meta, data = community.load_community_file(tmp_path / "community" / "2025-07.json")
        assert set(meta["discovery"]["strategies"]) == {"thread_seed", "timestamp_search"}
        assert data["posts"][0]["in_pipeline"] is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py::TestDiscoverViaSearch tests/fetch/test_community_fetch.py::TestEraAuthors tests/fetch/test_community_fetch.py::TestDiscoverViaAuthors tests/fetch/test_community_fetch.py::TestBackfillPosts tests/fetch/test_community_fetch.py::TestProcessMonthBackfill -x -q`
Expected: FAIL with `AttributeError: ... no attribute 'discover_via_search'`.

- [ ] **Step 3: Write the minimal implementation**

Append to `sotd/fetch/community.py`:

```python
# --------------------------------------------------------------------------- #
# backfill discovery (months .new() cannot reach)                             #
# --------------------------------------------------------------------------- #
def discover_via_search(subreddit, start_ts: int, end_ts: int) -> List:
    """Reddit search over a UTC timestamp window (lucene ``timestamp:`` syntax).

    Returns [] when the syntax is unsupported/unindexed — the recorded
    discovery meta then simply shows no contribution from this strategy.
    """
    query = f"timestamp:{start_ts}..{end_ts}"
    raw = safe_call(subreddit.search, query, sort="new", syntax="lucene", time_filter="all")
    if raw is None:
        return []
    return list(raw)


def era_authors(data_dir, months: Sequence[str], top_n: int = 100) -> List[str]:
    """Most active comment authors across *months* (from the pipeline's SOTD comments)."""
    counts: dict = {}
    for m in months:
        existing = load_month_file(get_data_dir(data_dir) / "comments" / f"{m}.json")
        if existing is None:
            continue
        for c in existing[1]:
            a = c.get("author")
            if a and a != "[deleted]":
                counts[a] = counts.get(a, 0) + 1
    return [a for a, _ in sorted(counts.items(), key=lambda kv: -kv[1])[:top_n]]


def discover_via_authors(reddit, authors: Sequence[str], start_ts: int, end_ts: int) -> List:
    """Submission histories of active authors, filtered to the month window."""
    out: List = []
    seen: Set[str] = set()
    for name in authors:
        redditor = safe_call(reddit.redditor, name)
        if redditor is None:
            continue
        stream = safe_call(lambda _r=redditor: list(islice(_r.submissions.new(limit=1000), 1000)))
        for sub in stream or []:
            if start_ts <= sub.created_utc <= end_ts and sub.id not in seen:
                seen.add(sub.id)
                out.append(sub)
    return out


def _backfill_posts(reddit, subreddit, year: int, month: int, sotd_ids, data_dir):
    """Best-effort discovery union for months ``new_listing`` cannot reach.

    Strategies: known SOTD thread IDs (IDs seeded from data/threads/ — full
    trees are fetched fresh later; the pipeline's top-level-only comment store
    is never reused), timestamp search, and active-author submission
    histories. A strategy is listed only when it contributed at least one post.
    Returns (posts, strategies_used, per_strategy_raw_counts).
    """
    start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    end_dt = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    start_ts, end_ts = int(start_dt.timestamp()), int(end_dt.timestamp())

    found: dict = {}
    strategies: List[str] = []
    per_strategy: dict = {}

    if sotd_ids:
        for sid in sotd_ids:
            sub = safe_call(lambda _sid=sid: reddit.submission(id=_sid))
            if sub is not None and getattr(sub, "title", None):
                found[sub.id] = sub
        per_strategy["thread_seed"] = len(found)
        if found:
            strategies.append("thread_seed")

    search_posts = discover_via_search(subreddit, start_ts, end_ts)
    per_strategy["timestamp_search"] = len(search_posts)
    if search_posts:
        strategies.append("timestamp_search")
    for sub in search_posts:
        found.setdefault(sub.id, sub)

    author_posts = discover_via_authors(
        reddit, era_authors(data_dir, [f"{year:04d}-{month:02d}"]), start_ts, end_ts
    )
    per_strategy["author_histories"] = len(author_posts)
    if author_posts:
        strategies.append("author_histories")
    for sub in author_posts:
        found.setdefault(sub.id, sub)

    return list(found.values()), strategies, per_strategy
```

Then extend `_process_month` — replace the discovery + meta sections:

Replace:

```python
posts_new, boundary_reached = discover_month_posts(subreddit, year, month)
if not boundary_reached:
    logger.warning(
        f"{month_str}: pagination cap reached before month boundary; discovery incomplete"
    )
```

with:

```python
    posts_new, boundary_reached = discover_month_posts(subreddit, year, month)
    strategies_used = ["new_listing"]
    per_strategy = {"new_listing": len(posts_new)}
    if not boundary_reached:
        logger.warning(
            f"{month_str}: pagination cap reached before month boundary; "
            "falling back to backfill discovery"
        )
        backfill_posts, strategies, backfill_counts = _backfill_posts(
            reddit, subreddit, year, month, sotd_ids, args.data_dir
        )
        by_id = {s.id: s for s in posts_new}
        for s in backfill_posts:
            by_id.setdefault(s.id, s)
        posts_new = sorted(by_id.values(), key=lambda s: s.created_utc, reverse=True)
        strategies_used = strategies_used + [s for s in strategies if s not in strategies_used]
        per_strategy.update(backfill_counts)
```

and replace the meta `discovery` block:

```python
        "discovery": {
            "strategies": ["new_listing"],
            "complete": boundary_reached,
            "per_strategy": {"new_listing": len(posts_new)},
        },
```

with:

```python
        "discovery": {
            "strategies": strategies_used,
            "complete": boundary_reached,
            "per_strategy": per_strategy,
        },
```

(Task 4's tests already assert `per_strategy: {"new_listing": 2}` for the forward path,
which this preserves — `per_strategy` starts as `{"new_listing": len(posts_new)}` before
any backfill, and `len(posts_new)` is unchanged at meta-build time for forward months.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/fetch/test_community_fetch.py -x -q`
Expected: PASS (all tasks so far).

- [ ] **Step 5: Lint**

Run: `.venv/bin/python -m ruff check sotd/fetch/community.py tests/fetch/test_community_fetch.py && .venv/bin/python -m black --check sotd/fetch/community.py tests/fetch/test_community_fetch.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/fetch/community.py tests/fetch/test_community_fetch.py
git commit -m "feat(fetch): backfill discovery strategies (thread seed, timestamp search, author histories)"
```

---

### Task 7: `community_query` CLI — loader, `meta`, `threads`

**Files:**
- Create: `sotd/report/tools/community_query.py`
- Test: `tests/report/tools/test_community_query.py` (create)

**Interfaces:**
- Consumes: `data/community/YYYY-MM.json` files (shape from Task 1).
- Produces: `default_data_dir() -> str`, `class QueryError(Exception)`, `parse_month(s) -> str`, `month_iter(start: str, end: str) -> list[str]`, `load_month(data_dir: str, month: str) -> dict` (raises QueryError), `comment_counts(doc) -> Counter`, `cmd_meta(doc, *, as_json) -> str`, `cmd_threads(doc, *, min_comments, author, flair, top, sort, thread_filter, as_json) -> str`, `build_parser() -> argparse.ArgumentParser`, `main(argv) -> int`. Task 8 adds the `thread` and `search` subcommands to the same parser/main.

- [ ] **Step 1: Write the failing tests**

Create `tests/report/tools/test_community_query.py`:

```python
"""Tests for the community_query CLI tool."""

import json

import pytest

from sotd.report.tools.community_query import main


def make_community_file(path, month, posts, comments, discovery=None):
    meta = {
        "month": month,
        "extracted_at": "2026-09-06T00:00:00Z",
        "post_count": len(posts),
        "comment_count": len(comments),
        "in_pipeline_post_count": sum(1 for p in posts if p.get("in_pipeline")),
        "discovery": discovery or {"strategies": ["new_listing"], "complete": True},
    }
    doc = {"meta": meta, "data": {"posts": posts, "comments": comments}}
    path.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def data_dir(tmp_path):
    comm = tmp_path / "community"
    comm.mkdir()
    make_community_file(
        comm / "2026-08.json",
        "2026-08",
        posts=[
            {
                "id": "sotd",
                "title": "Saturday SOTD Thread - Aug 01, 2026",
                "selftext": "",
                "author": "AutoModerator",
                "created_utc": "2026-08-01T06:00:00Z",
                "score": 10,
                "num_comments": 2,
                "flair": "SOTD",
                "url": "u1",
                "locked": False,
                "stickied": True,
                "in_pipeline": True,
            },
            {
                "id": "disc",
                "title": "Lather Games wrap-up",
                "selftext": "the final standings",
                "author": "bigcheese",
                "created_utc": "2026-08-05T10:00:00Z",
                "score": 88,
                "num_comments": 40,
                "flair": "Discussion",
                "url": "u2",
                "locked": False,
                "stickied": False,
                "in_pipeline": False,
            },
            {
                "id": "quiet",
                "title": "Quiet question",
                "selftext": "",
                "author": "newbie",
                "created_utc": "2026-08-10T10:00:00Z",
                "score": 2,
                "num_comments": 1,
                "flair": None,
                "url": "u3",
                "locked": False,
                "stickied": False,
                "in_pipeline": False,
            },
        ],
        comments=[
            {
                "id": "c1",
                "thread_id": "sotd",
                "thread_title": "Saturday SOTD Thread - Aug 01, 2026",
                "parent_id": "t3_sotd",
                "author": "shaver1",
                "created_utc": "2026-08-01T07:00:00Z",
                "body": "great lather",
                "score": 3,
                "is_submitter": False,
            },
            {
                "id": "c4",
                "thread_id": "disc",
                "thread_title": "Lather Games wrap-up",
                "parent_id": "t3_disc",
                "author": "judge1",
                "created_utc": "2026-08-05T11:00:00Z",
                "body": "final verdict posted",
                "score": 5,
                "is_submitter": False,
            },
            {
                "id": "c5",
                "thread_id": "disc",
                "thread_title": "Lather Games wrap-up",
                "parent_id": "t1_c4",
                "author": "bigcheese",
                "created_utc": "2026-08-05T12:00:00Z",
                "body": "thanks judges",
                "score": 2,
                "is_submitter": True,
            },
            {
                "id": "c6",
                "thread_id": "disc",
                "thread_title": "Lather Games wrap-up",
                "parent_id": "t1_c4",
                "author": "rival",
                "created_utc": "2026-08-05T13:00:00Z",
                "body": "rematch next year?",
                "score": 1,
                "is_submitter": False,
            },
            {
                "id": "c2",
                "thread_id": "quiet",
                "thread_title": "Quiet question",
                "parent_id": "t3_quiet",
                "author": "bigcheese",
                "created_utc": "2026-08-10T11:00:00Z",
                "body": "good question",
                "score": 1,
                "is_submitter": False,
            },
            {
                "id": "c3",
                "thread_id": "quiet",
                "thread_title": "Quiet question",
                "parent_id": "t1_c2",
                "author": "newbie",
                "created_utc": "2026-08-10T12:00:00Z",
                "body": "thanks",
                "score": 0,
                "is_submitter": True,
            },
        ],
    )
    return tmp_path


def run(capsys, argv):
    code = main(argv)
    captured = capsys.readouterr()
    return code, captured.out, captured.err


class TestMeta:
    def test_meta(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "meta", "--month", "2026-08"])
        assert code == 0
        assert "post_count" in out

    def test_meta_json(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "--json", "meta", "--month", "2026-08"]
        )
        assert code == 0
        assert '"discovery"' in out

    def test_meta_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "meta", "--month", "2025-01"])
        assert code == 1
        assert "No community file" in err


class TestThreads:
    def test_lists_all_sorted_by_comments_desc(self, data_dir, capsys):
        # counts: disc=3 (c4,c5,c6), quiet=2 (c2,c3), sotd=1 (c1)
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "threads", "--month", "2026-08"])
        assert code == 0
        assert out.index("disc") < out.index("quiet") < out.index("sotd")

    def test_filter_non_sotd(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--filter", "non-sotd"],
        )
        assert code == 0
        assert "Lather Games wrap-up" in out
        assert "Saturday SOTD Thread" not in out

    def test_filter_sotd(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--filter", "sotd"],
        )
        assert code == 0
        assert "Saturday SOTD Thread" in out
        assert "Lather Games wrap-up" not in out

    def test_min_comments(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--min-comments", "3"],
        )
        assert code == 0
        assert "Lather Games wrap-up" in out
        assert "Quiet question" not in out

    def test_author_filter(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--author", "newbie"],
        )
        assert code == 0
        assert "Quiet question" in out
        assert "Lather Games wrap-up" not in out

    def test_top_limit(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--top", "1"]
        )
        assert code == 0
        assert "Lather Games wrap-up" in out
        assert "Saturday SOTD Thread" not in out

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "threads", "--month", "2025-01"])
        assert code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/report/tools/test_community_query.py -x -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'sotd.report.tools.community_query'`.

- [ ] **Step 3: Write the minimal implementation**

Create `sotd/report/tools/community_query.py`:

```python
"""Point-query CLI for community context data.

Answers the questions agents and shell debugging need about ``data/community/``
without loading whole month files into context:
thread listings, one thread with its reconstructed comment tree, and
keyword/author search across a bounded month window.

Month/window arguments are always explicit — this structurally enforces the
"never see future months" rule (same mechanism as --end on history queries).

Exit codes: 0 success, 1 on query errors (missing/malformed month file,
unknown thread ID, bad window).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any


class QueryError(Exception):
    """Raised for deterministic, user-facing query failures."""


def default_data_dir() -> str:
    """Return the artifact root from the environment or the repo default."""
    return os.environ.get("SOTD_DATA_DIR", "data")


def parse_month(s: str) -> str:
    try:
        datetime.strptime(s.strip(), "%Y-%m")
    except ValueError as exc:
        raise QueryError(f"Invalid YYYY-MM format: {s}") from exc
    return s.strip()


def month_iter(start: str, end: str) -> list:
    """Inclusive list of YYYY-MM strings from start to end."""
    a = datetime.strptime(start, "%Y-%m")
    b = datetime.strptime(end, "%Y-%m")
    if a > b:
        raise QueryError(f"Window start {start} is after end {end}")
    months = []
    cur = a
    while cur <= b:
        months.append(cur.strftime("%Y-%m"))
        cur = datetime(cur.year + (cur.month == 12), 1 if cur.month == 12 else cur.month + 1, 1)
    return months


def load_month(data_dir: str, month: str) -> dict:
    path = Path(data_dir) / "community" / f"{month}.json"
    if not path.is_file():
        raise QueryError(f"No community file for {month}: {path}")
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise QueryError(f"Unreadable community file for {month}: {exc}") from exc
    if not isinstance(doc, dict) or "meta" not in doc or "data" not in doc:
        raise QueryError(f"Malformed community file for {month}: missing meta/data")
    return doc


def comment_counts(doc: dict) -> Counter:
    return Counter(c["thread_id"] for c in doc["data"].get("comments", []))


def cmd_meta(doc: dict, *, as_json: bool) -> str:
    meta = doc["meta"]
    if as_json:
        return json.dumps(meta, indent=2)
    discovery = meta.get("discovery", {})
    return "\n".join(
        [
            f"month:                    {meta.get('month')}",
            f"extracted_at:             {meta.get('extracted_at')}",
            f"post_count:               {meta.get('post_count')}",
            f"comment_count:            {meta.get('comment_count')}",
            f"in_pipeline_post_count:   {meta.get('in_pipeline_post_count')}",
            f"discovery.strategies:     {', '.join(discovery.get('strategies', []))}",
            f"discovery.complete:       {discovery.get('complete')}",
        ]
    )


def keymap_for(sort: str):
    return {
        "comments": lambda r: (-r["_comments"], r["created_utc"]),
        "score": lambda r: (-r["score"], r["created_utc"]),
        "date": lambda r: r["created_utc"],
    }[sort]


def cmd_threads(
    doc: dict,
    *,
    min_comments: int = 0,
    author: str | None = None,
    flair: str | None = None,
    top: int = 10,
    sort: str = "comments",
    thread_filter: str = "all",
    as_json: bool = False,
) -> str:
    counts = comment_counts(doc)
    rows = []
    for p in doc["data"].get("posts", []):
        if thread_filter == "sotd" and not p.get("in_pipeline"):
            continue
        if thread_filter == "non-sotd" and p.get("in_pipeline"):
            continue
        if author and (p.get("author") or "").lower() != author.lower():
            continue
        if flair and (p.get("flair") or "") != flair:
            continue
        n_comments = counts.get(p["id"], 0)
        if n_comments < min_comments:
            continue
        rows.append({**p, "_comments": n_comments})

    rows.sort(key=keymap_for(sort))

    if as_json:
        return json.dumps(rows[:top], indent=2)

    lines = [
        f"{'id':<12} {'date':<10} {'flag':<5} {'cmts':>4} {'score':>5}  {'author':<20} {'title'}"
    ]
    for r in rows[:top]:
        flag = ("SOTD" if r.get("in_pipeline") else "-") if "in_pipeline" in r else "n/a"
        title = (r.get("title") or "")[:60]
        lines.append(
            f"{r['id']:<12} {r['created_utc'][:10]:<10} {flag:<5} {r['_comments']:>4} "
            f"{r['score']:>5}  {(r.get('author') or '')[:20]:<20} {title}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="community_query",
        description="Query data/community JSON files (meta, thread listings, thread trees, search).",
    )
    parser.add_argument("--data-dir", default=default_data_dir(), help="Artifact root directory")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of aligned text")

    sub = parser.add_subparsers(dest="command", required=True)

    meta = sub.add_parser("meta", help="Print the meta block for a month")
    meta.add_argument("--month", required=True, help="Month (YYYY-MM)")

    threads = sub.add_parser("threads", help="List posts for a month with filters")
    threads.add_argument("--month", required=True, help="Month (YYYY-MM)")
    threads.add_argument("--min-comments", type=int, default=0, help="Minimum comment count")
    threads.add_argument("--author", help="Exact author name (case-insensitive)")
    threads.add_argument("--flair", help="Exact link flair text")
    threads.add_argument("--top", type=int, default=10, help="Max rows (default 10)")
    threads.add_argument(
        "--sort", choices=["comments", "score", "date"], default="comments", help="Sort key"
    )
    threads.add_argument(
        "--filter",
        choices=["sotd", "non-sotd", "all"],
        default="all",
        help="Key off the in_pipeline flag (default all)",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        doc = load_month(args.data_dir, parse_month(args.month))
        if args.command == "meta":
            print(cmd_meta(doc, as_json=args.json))
        elif args.command == "threads":
            print(
                cmd_threads(
                    doc,
                    min_comments=args.min_comments,
                    author=args.author,
                    flair=args.flair,
                    top=args.top,
                    sort=args.sort,
                    thread_filter=args.filter,
                    as_json=args.json,
                )
            )
        else:
            raise QueryError(f"Unknown command: {args.command}")
        return 0
    except QueryError as e:
        print(str(e), file=sys.stderr)
        return 1
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/report/tools/test_community_query.py -x -q`
Expected: PASS.

- [ ] **Step 5: Lint**

Run: `.venv/bin/python -m ruff check sotd/report/tools/community_query.py tests/report/tools/test_community_query.py && .venv/bin/python -m black --check sotd/report/tools/community_query.py tests/report/tools/test_community_query.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/report/tools/community_query.py tests/report/tools/test_community_query.py
git commit -m "feat(report): community_query CLI — meta and threads subcommands"
```

---

### Task 8: `community_query` CLI — `thread` tree + `search`

**Files:**
- Modify: `sotd/report/tools/community_query.py` (append subcommands)
- Test: `tests/report/tools/test_community_query.py` (append)

**Interfaces:**
- Consumes: `load_month`, `QueryError`, `month_iter`, `parse_month`, `comment_counts` (Task 7).
- Produces: `cmd_thread(doc, thread_id: str, *, max_comments: int, as_json: bool) -> str` and `cmd_search(docs: list, *, query: str, author: str | None, top: int, as_json: bool, missing: list | None) -> str`. These are the access surfaces for shell debugging and future agent consumers.

- [ ] **Step 1: Write the failing tests**

Append to `tests/report/tools/test_community_query.py`:

```python
class TestThread:
    def test_renders_tree_indented(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "thread", "--month", "2026-08", "--id", "quiet"]
        )
        assert code == 0
        assert "Quiet question" in out
        lines = out.splitlines()
        c2_line = next(l for l in lines if "[c2]" in l)
        c3_line = next(l for l in lines if "[c3]" in l)
        assert lines.index(c3_line) > lines.index(c2_line)
        assert c3_line.startswith("  ") and not c2_line.startswith(" ")
        assert "(OP)" in c3_line  # c3 has is_submitter=True

    def test_accepts_t3_prefix(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "thread", "--month", "2026-08", "--id", "t3_quiet"],
        )
        assert code == 0

    def test_unknown_id_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys, ["--data-dir", str(data_dir), "thread", "--month", "2026-08", "--id", "nope"]
        )
        assert code == 1
        assert "Unknown thread" in err

    def test_max_comments_caps_render(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "quiet",
                "--max-comments",
                "1",
            ],
        )
        assert code == 0
        assert "[c3]" not in out
        assert "not shown" in out

    def test_json_output(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "--json",
                "thread",
                "--month",
                "2026-08",
                "--id",
                "quiet",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["post"]["id"] == "quiet"
        assert len(doc["comments"]) == 2


class TestSearch:
    def test_finds_post_and_comment_across_window(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08:2026-08",
                "--query",
                "question",
            ],
        )
        assert code == 0
        assert "[post]" in out and "[comment]" in out

    def test_author_filter(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08:2026-08",
                "--query",
                "verdict",
                "--author",
                "judge1",
            ],
        )
        assert code == 0
        assert "[comment]" in out
        assert "[post]" not in out  # the disc post is authored by bigcheese

    def test_no_hits_reports(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08:2026-08",
                "--query",
                "zzznotfound",
            ],
        )
        assert code == 0
        assert "No matches" in out

    def test_skips_missing_months_with_note(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-07:2026-08",
                "--query",
                "question",
            ],
        )
        assert code == 0
        assert "no community file" in out.lower()

    def test_window_start_after_end_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            ["--data-dir", str(data_dir), "search", "--months", "2026-08:2026-07", "--query", "x"],
        )
        assert code == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `.venv/bin/python -m pytest tests/report/tools/test_community_query.py::TestThread tests/report/tools/test_community_query.py::TestSearch -x -q`
Expected: FAIL — argparse error `invalid choice: 'thread'` (SystemExit 2; the subcommand does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

Append to `sotd/report/tools/community_query.py`:

```python
def _flatten_body(body: str) -> str:
    return " / ".join(line.strip() for line in (body or "").splitlines() if line.strip())


def cmd_thread(doc: dict, thread_id: str, *, max_comments: int = 50, as_json: bool = False) -> str:
    pid = thread_id.removeprefix("t3_")
    posts = {p["id"]: p for p in doc["data"].get("posts", [])}
    post = posts.get(pid)
    if post is None:
        raise QueryError(f"Unknown thread: {thread_id} (month {doc['meta'].get('month')})")
    comments = [c for c in doc["data"].get("comments", []) if c["thread_id"] == pid]
    comments.sort(key=lambda c: c["created_utc"])

    if as_json:
        return json.dumps({"post": post, "comments": comments}, indent=2)

    lines = [
        f"{post['id']}  {post['created_utc'][:10]}  u/{post.get('author')}  "
        f"{comment_counts(doc).get(pid, 0)} comments  score {post['score']}"
        + (f"  flair={post['flair']}" if post.get("flair") else ""),
        post["url"],
        post["title"],
    ]
    if post.get("selftext"):
        lines.append("--- body ---")
        lines.append(post["selftext"])
    lines.append(f"--- {len(comments)} comments ---")

    children: dict = {}
    for c in comments:
        children.setdefault(c["parent_id"], []).append(c)

    rendered = 0
    truncated = False

    def walk(parent: str, depth: int) -> None:
        nonlocal rendered, truncated
        for c in sorted(children.get(parent, []), key=lambda x: x["created_utc"]):
            if rendered >= max_comments:
                truncated = True
                return
            body = _flatten_body(c["body"])[:200]
            op = " (OP)" if c.get("is_submitter") else ""
            lines.append(
                f"{'  ' * depth}[{c['id']}] u/{c['author']} {c['created_utc'][:10]}{op}: {body}"
            )
            rendered += 1
            walk(c["id"], depth + 1)

    walk(f"t3_{pid}", 0)
    if truncated:
        lines.append(f"(comments after the first {max_comments} not shown)")
    return "\n".join(lines)


def _search_docs(data_dir: str, months: list):
    """Load available months; skip missing ones (reported in output, not an error)."""
    docs = []
    missing = []
    for m in months:
        try:
            docs.append((m, load_month(data_dir, m)))
        except QueryError:
            missing.append(m)
    return docs, missing


def _snippet(text: str, needle: str, width: int = 160) -> str:
    flat = _flatten_body(text)
    idx = flat.lower().find(needle.lower())
    if idx < 0:
        return flat[:width]
    start = max(0, idx - 30)
    return flat[start : start + width]


def cmd_search(
    docs: list,
    *,
    query: str,
    author: str | None = None,
    top: int = 20,
    as_json: bool = False,
    missing: list | None = None,
) -> str:
    hits = []
    for _month, doc in docs:
        for p in doc["data"].get("posts", []):
            haystack = f"{p.get('title', '')}\n{p.get('selftext', '')}"
            if query.lower() in haystack.lower():
                if author and (p.get("author") or "").lower() != author.lower():
                    continue
                hits.append(
                    {
                        "created_utc": p["created_utc"],
                        "kind": "post",
                        "thread_id": p["id"],
                        "author": p.get("author"),
                        "snippet": _snippet(p.get("title", ""), query),
                    }
                )
        for c in doc["data"].get("comments", []):
            if query.lower() in (c.get("body") or "").lower():
                if author and (c.get("author") or "").lower() != author.lower():
                    continue
                hits.append(
                    {
                        "created_utc": c["created_utc"],
                        "kind": "comment",
                        "thread_id": c["thread_id"],
                        "comment_id": c["id"],
                        "author": c.get("author"),
                        "snippet": _snippet(c.get("body") or "", query),
                    }
                )
    hits.sort(key=lambda h: h["created_utc"])
    hits = hits[:top]

    if as_json:
        return json.dumps({"matches": hits, "missing_months": missing or []}, indent=2)

    lines = [f"(no community file for {m})" for m in missing or []]
    if not hits:
        lines.append("No matches for the query in the given window.")
        return "\n".join(lines)
    for h in hits:
        who = f" u/{h['author']}" if h.get("author") else ""
        if h["kind"] == "post":
            lines.append(f"{h['created_utc'][:10]}  [post]     t3_{h['thread_id']}{who}")
        else:
            lines.append(
                f"{h['created_utc'][:10]}  [comment]  t3_{h['thread_id']}  "
                f"t1_{h['comment_id']}{who}"
            )
        lines.append(f'           "{h["snippet"]}"')
    return "\n".join(lines)
```

Parser additions (inside `build_parser`, after the `threads` block):

```python
    thread = sub.add_parser("thread", help="One thread with its reconstructed comment tree")
    thread.add_argument("--month", required=True, help="Month (YYYY-MM)")
    thread.add_argument("--id", required=True, help="Thread ID (with or without t3_ prefix)")
    thread.add_argument("--max-comments", type=int, default=50, help="Max comments rendered")

    search = sub.add_parser("search", help="Keyword/author search across a bounded window")
    search.add_argument("--months", required=True, help="Window YYYY-MM:YYYY-MM (inclusive)")
    search.add_argument("--query", required=True, help="Case-insensitive substring")
    search.add_argument("--author", help="Exact author name (case-insensitive)")
    search.add_argument("--top", type=int, default=20, help="Max results (default 20)")
```

and extend the `main` dispatch (before the final `else`):

```python
        elif args.command == "thread":
            print(cmd_thread(doc, args.id, max_comments=args.max_comments, as_json=args.json))
        elif args.command == "search":
            start, end = args.months.split(":")
            months = month_iter(parse_month(start), parse_month(end))
            docs, missing = _search_docs(args.data_dir, months)
            print(
                cmd_search(
                    docs, query=args.query, author=args.author, top=args.top,
                    as_json=args.json, missing=missing,
                )
            )
```

(The `thread` subcommand has no `--json` of its own — the global `--json` flag applies.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `.venv/bin/python -m pytest tests/report/tools/test_community_query.py -x -q`
Expected: PASS.

- [ ] **Step 5: Lint**

Run: `.venv/bin/python -m ruff check sotd/report/tools/community_query.py tests/report/tools/test_community_query.py && .venv/bin/python -m black --check sotd/report/tools/community_query.py tests/report/tools/test_community_query.py`
Expected: no findings.

- [ ] **Step 6: Commit**

```bash
git add sotd/report/tools/community_query.py tests/report/tools/test_community_query.py
git commit -m "feat(report): community_query thread tree + windowed search"
```

### Task 9: Docs, operational runbook, and agent-memory vault

**Files:**
- Modify: `CLAUDE.md` (Pipeline Execution + artifact layout + operations subsection)

**Interfaces:**
- Consumes: everything above (documented surfaces).
- Produces: operator-facing docs; vault record.

- [ ] **Step 1: Add the command to CLAUDE.md Pipeline Execution**

In the `#### Individual Phases` code block, after the `report` lines, add:

```bash
python run.py community --month 2025-05 --force   # Fetch all posts + full comment trees (community context)
```

- [ ] **Step 2: Add the artifact-layout bullet**

In the artifact layout list (after the Report bullet), add:

```markdown
- **Community fetch (sidecar)**: `data/community/YYYY-MM.json` (all posts + full comment trees, `in_pipeline` flags); consumed via the `community_query` CLI
```

- [ ] **Step 3: Add an operations subsection** (end of the Pipeline Execution section)

```markdown
#### Community context operations

The `community` sidecar is run when needed (sooner after month end = fewer
lost-to-deletion posts); the author explores the record via the CLI:

```bash
# 1. Fetch the month's full community record
python run.py community --month 2026-09 --force

# 2. (Author) explore — the CLI renders bounded slices
python -m sotd.report.tools.community_query threads --month 2026-09 --top 20
python -m sotd.report.tools.community_query search --months 2026-08:2026-09 --query "group buy"
```

Consumption (summarizer agent → observations-drafter) is a later project — see the
spec's Future work section.

Backfill notes: months `.new()` cannot reach fall back to best-effort discovery
(SOTD-thread seeding from `data/threads/` + timestamp search + active-author
histories); each month's `meta.discovery` records what ran and how complete it is.
Run the voice-era backfill with `python run.py community --range 2025-07:2026-08 --force`.
```

- [ ] **Step 4: Update the AgentMemory vault**

Per repo CLAUDE.md protocol — in `../agent-memory`: `git pull --rebase` first; append
to `projects/sotd-pipeline/status.md` a dated entry (agent-id: claude-code, date
2026-09-06) recording: community context fetch shipped (sidecar `run.py community`),
storage `data/community/`, `community_query` CLI as the access surface; consumption
(summarizer agent, drafter wiring) deliberately deferred to a later project.
Commit with attribution. `git push` is **not** automatic — ask the author.

- [ ] **Step 5: Full test suite**

Run: `.venv/bin/python -m pytest tests/ -x -q`
Expected: all tests pass (baseline 3988 + new community tests).

- [ ] **Step 6: Commit docs**

```bash
git add CLAUDE.md
git commit -m "docs: community context fetch command, layout, and operations runbook"
```

---

## Operational follow-up (post-implementation, author-supervised — not pytest tasks)

These require live Reddit API access (`praw.ini`) and produce real data files; run
them after Tasks 1–9 are green, in this order:

1. **Coverage probe** (before committing to backfill): run
   `python run.py community --month 2025-07 --force`, `--month 2026-01 --force`,
   `--month 2026-06 --force`, then inspect `meta.discovery` in each
   `data/community/YYYY-MM.json` — `per_strategy` counts show whether timestamp
   search contributed anything and how much author histories cover. 2026-06 should
   come out `complete: true` via `new_listing` alone (reachable), serving as the
   sanity check. Record findings before running the full backfill.
2. **Voice-era backfill**: `python run.py community --range 2025-07:2026-08 --force`
   (long-running; months are processed sequentially).
3. **Exploration sanity check**: spot-check a couple of months via
   `community_query threads` / `search` to confirm the CLI surfaces work against
   real data (this is also the raw material the future consumption project will
   design against).

## Out of scope (unchanged from spec)

- Consumption: community-summarizer agent and all observations-drafter changes
  (deferred to a later project).
- Deterministic pipeline phases untouched; no LLM steps inside the pipeline.
- WebUI integration.
- Full-history backfill to 2016-05 (voice era only).