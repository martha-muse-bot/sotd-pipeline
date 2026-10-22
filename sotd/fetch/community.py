"""Fetch the full r/wetshaving community record for one or more months.

Every post in the target month (SOTD daily threads included) plus its full
comment tree is stored to ``data/community/YYYY-MM.json``::

    {"meta": {...}, "data": {"posts": [...], "comments": [...]}}

This is a sidecar to the 6-phase pipeline: nothing in extract..report consumes
this data. The ``community_query`` CLI is its access surface (agent consumption
is a later project). The pipeline's own ``data/comments/`` store (top-level SOTD
comments only) is never reused here — everything is fetched fresh from Reddit.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import time
import urllib.request
from datetime import datetime, timezone
from itertools import islice
from typing import List, Optional, Sequence, Set, Tuple
from urllib.error import HTTPError

from praw.models import Comment
from tqdm import tqdm

from sotd.cli_utils.base_parser import BaseCLIParser
from sotd.cli_utils.date_span import month_span
from sotd.fetch.merge import merge_records
from sotd.fetch.reddit import RETRY_429_DELAYS, _429_wait, get_reddit, safe_call
from sotd.fetch.save import load_month_file
from sotd.utils.data_dir import get_data_dir
from sotd.utils.file_io import load_json_data, save_json_data
from sotd.utils.logging_config import setup_pipeline_logging, should_disable_tqdm

logger = logging.getLogger(__name__)

# Discovery stops here even if the month boundary was never reached
# (30 batches x 100 posts; a target month needs ~4).
PAGINATION_CAP = 3000

# Reddit's /new listing and its timestamp search cannot reach months older
# than the ~1000-item window: as of 2026-09 the window ends inside Dec 2025
# (verified live: 0 search hits for 2025-12; the listing walk died mid-month).
# Months before this floor skip Reddit-side discovery entirely; bump the floor
# as the horizon advances.
REDDIT_HORIZON_FLOOR = "2026-01"


# --------------------------------------------------------------------------- #
# record building                                                             #
# --------------------------------------------------------------------------- #
def _iso(created_utc: float) -> str:
    return datetime.fromtimestamp(created_utc, tz=timezone.utc).isoformat().replace("+00:00", "Z")


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
def write_community_file(path, meta: dict, posts: list[dict], comments: list[dict]) -> None:
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


# --------------------------------------------------------------------------- #
# shared Reddit ID resolution                                                  #
# --------------------------------------------------------------------------- #
RESOLVE_BATCH = 100  # reddit.info accepts up to 100 fullnames per request
COMMENT_WORKERS = 10  # parallel comment-tree fetchers (same as the SOTD fetch)


def _resolve_ids(reddit, ids: Set[str]) -> List:
    """Resolve bare submission IDs to hydrated Reddit submissions.

    ``reddit.info(fullnames=...)`` fetches up to ``RESOLVE_BATCH`` submissions
    per request — one ``reddit.submission(id=...)`` round-trip per ID cost
    ~99s for a 205-ID month (profiled 2026-09-07). The info endpoint returns
    submission attributes only (comment trees are fetched separately);
    unmatched (dead) IDs are silently omitted by Reddit, so no per-ID title
    check is needed. A chunk that fails after safe_call's retries is skipped
    with a warning, matching the per-ID best-effort behavior it replaces.
    """
    sorted_ids = sorted(ids)
    out: List = []
    for start in range(0, len(sorted_ids), RESOLVE_BATCH):
        chunk = sorted_ids[start : start + RESOLVE_BATCH]
        batch = safe_call(lambda _c=chunk: list(reddit.info(fullnames=[f"t3_{i}" for i in _c])))
        if batch is None:
            logger.warning(f"resolve chunk failed; {len(chunk)} ids skipped")
            continue
        out.extend(batch)
    return out


# --------------------------------------------------------------------------- #
# forward discovery                                                            #
# --------------------------------------------------------------------------- #
def discover_month_posts(subreddit, year: int, month: int) -> Tuple[List, bool]:
    """Pull ``subreddit.new()`` until posts older than the month appear.

    Returns (in_month_posts, boundary_reached). ``in_month_posts`` is
    newest-first. ``boundary_reached`` is False when the pagination cap trips
    before the boundary — the caller must treat that month as partial.
    """
    month_str = f"{year:04d}-{month:02d}"
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end_exclusive = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )

    def _listing():
        # lazy generator so the listing's HTTP calls stay inside safe_call;
        # logs a heartbeat every 1000 items so long silent stretches are visible
        for i, sub in enumerate(subreddit.new(limit=None), 1):
            if i % 1000 == 0:
                logger.info(f"{month_str}: listing pulled {i} items…")
            yield sub

    pulled = safe_call(lambda: list(islice(_listing(), PAGINATION_CAP)))
    in_month: List = []
    boundary_reached = False
    for sub in pulled or []:
        dt = datetime.fromtimestamp(sub.created_utc, tz=timezone.utc)
        if dt < start:
            # listings are newest-first: seeing a post OLDER than the month is
            # the only proof the walk enumerated the whole month (a listing
            # that merely ends is not — Reddit serves only ~1000 items)
            boundary_reached = True
            break
        if dt < end_exclusive:
            in_month.append(sub)
    logger.info(
        f"{month_str}: listing discovered {len(in_month)} posts "
        f"(boundary {'reached' if boundary_reached else 'not reached'})"
    )
    return in_month, boundary_reached


def fetch_all_comments(submission) -> List:
    """Return every comment under *submission* at all depths.

    Unlike the SOTD fetch (top-level shaves only), community context needs the
    nested replies — that is where the conversation lives. MoreComment stubs
    that survive a failed replace_more are dropped.
    """
    safe_call(submission.comments.replace_more, limit=None)
    return [c for c in submission.comments.list() if isinstance(c, Comment)]


def _thread_comment_records(sub) -> List[dict]:
    return [build_comment_record(c, sub.id, sub.title) for c in fetch_all_comments(sub) or []]


def _fetch_thread_with_retry(sub) -> List[dict]:
    """Fetch one thread's comment tree, retrying 429s with exponential backoff.

    Parts of the tree path run outside ``safe_call`` (``comments.list()``,
    record building), where a 429 would otherwise escape straight to the
    per-future skip. Detection is by HTTP status — any exception wrapping a
    429 response is retried, regardless of its class. Delays are the
    exponential floor 1s/2s/4s; Reddit's Retry-After can only raise them.
    """
    for attempt, floor in enumerate(RETRY_429_DELAYS, start=1):
        try:
            return _thread_comment_records(sub)
        except Exception as exc:
            header_wait = _429_wait(exc)
            if header_wait is None:
                raise
            delay = max(floor, header_wait)
            logger.warning(
                f"429 fetching comments for {sub.id} "
                f"(attempt {attempt}/{len(RETRY_429_DELAYS)}); waiting {delay:g}s…"
            )
            time.sleep(delay)
    return _thread_comment_records(sub)  # final attempt; 429 propagates


def _fetch_comment_records(posts: List) -> tuple[List[dict], List[str]]:
    """Fetch full comment trees for every post, parallel across posts.

    Unlike the SOTD fetch's ``fetch_top_level_comments_parallel`` there is no
    total-batch timeout: its ``as_completed(timeout=...)`` is a budget for the
    entire batch, and exceeding it discards completed work and re-fetches
    everything sequentially. Containment is per-future instead — a tree that
    fails contributes nothing but never aborts the month, and its id is
    returned so the month can be marked incomplete rather than silently
    partial.
    """
    out: List[dict] = []
    failed: List[str] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=COMMENT_WORKERS) as pool:
        futures = {pool.submit(_fetch_thread_with_retry, sub): sub for sub in posts}
        for fut in tqdm(
            concurrent.futures.as_completed(futures),
            total=len(futures),
            desc="Threads",
            unit="thread",
            disable=should_disable_tqdm(),
        ):
            try:
                out.extend(fut.result())
            except Exception as e:
                failed.append(futures[fut].id)
                logger.warning(f"comment tree fetch failed for {futures[fut].id}: {e}")
    return out, failed


# --------------------------------------------------------------------------- #
# archive discovery (PullPush / Arctic Shift: IDs only; Reddit is the content  #
# source)                                                                     #
# --------------------------------------------------------------------------- #
PULLPUSH_UA = "sotd-pipeline-community-fetch/1.0 (personal research tool)"
PULLPUSH_SLEEP = 4.0  # seconds between archive requests; PullPush 429s hot callers
ARCTIC_SHIFT_UA = "sotd-pipeline-community-fetch/1.0 (personal research tool)"
ARCTIC_SHIFT_SLEEP = 1.0  # Arctic Shift tolerates far more; stay polite anyway


def _archive_get(url: str, ua: str, source: str) -> Optional[List]:
    """GET one archive search page (PullPush or Arctic Shift), returning its ``data`` array.

    Retries a 429 twice (the archives rate-limit hot callers hard); returns None
    on any failure so callers treat the archive as best-effort.
    """
    for attempt in range(3):
        req = urllib.request.Request(url, headers={"User-Agent": ua})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                obj = json.load(resp)
        except HTTPError as exc:
            if exc.code == 429 and attempt < 2:
                logger.warning(f"{source} rate limit hit (429); cooling off…")
                time.sleep(15)
                continue
            logger.warning(f"{source} request failed: {exc}")
            return None
        except Exception as exc:
            logger.warning(f"{source} request failed: {exc}")
            return None
        data = obj.get("data") if isinstance(obj, dict) else None
        return data if isinstance(data, list) else None
    return None


def _pullpush_get(url: str) -> Optional[List]:
    return _archive_get(url, PULLPUSH_UA, "PullPush")


def _arctic_shift_get(url: str) -> Optional[List]:
    return _archive_get(url, ARCTIC_SHIFT_UA, "Arctic Shift")


def _page_archive_ids(
    *, url_for_page, get_page, start: int, end: int, source: str, sleep_s: float
) -> Set[str]:
    """Walk an archive's 100-row pages backward from the month end, collecting IDs.

    ``url_for_page(cursor)`` builds the request; ``get_page(url)`` returns the
    page's ``data`` array or None. Stops on the month boundary, a short page, a
    page already seen (stale archive), or a fetch failure.
    """
    ids: Set[str] = set()
    cursor = end
    page_no = 0
    while True:
        page_no += 1
        data = get_page(url_for_page(cursor))
        if not data:
            break
        page_ids = {s["id"] for s in data if s.get("id") and start <= int(s["created_utc"]) < end}
        if page_ids <= ids:
            break  # archive served a page we already have; stop instead of looping
        ids |= page_ids
        oldest = min(int(s["created_utc"]) for s in data)
        logger.info(
            f"{source}: page {page_no}: {len(data)} ids "
            f"(oldest {datetime.fromtimestamp(oldest, tz=timezone.utc):%Y-%m-%d})"
        )
        if oldest <= start or len(data) < 100:
            break
        cursor = oldest
        time.sleep(sleep_s)
    logger.info(f"{source}: {len(ids)} archive ids across {page_no} pages")
    return ids


def pullpush_submission_ids(year: int, month: int) -> Set[str]:
    """Submission IDs the PullPush archive holds for the month (IDs only).

    The archive is a *discovery* source: the caller converts each ID via
    ``reddit.submission(id=...)`` — not subject to the ~1000-item listing
    limit — and fetches comment trees fresh from Reddit.
    """
    start = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())
    end_dt = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    end = int(end_dt.timestamp())

    def url_for(cursor: int) -> str:
        return (
            "https://api.pullpush.io/reddit/search/submission/"
            f"?subreddit=wetshaving&after={start}&before={cursor}&size=100&sort=desc"
        )

    return _page_archive_ids(
        url_for_page=url_for,
        get_page=_pullpush_get,
        start=start,
        end=end,
        source="pullpush",
        sleep_s=PULLPUSH_SLEEP,
    )


def arctic_shift_submission_ids(year: int, month: int) -> Set[str]:
    """Submission IDs the Arctic Shift archive holds for the month (IDs only).

    Same discovery semantics as the PullPush strategy; Arctic Shift is the
    primary archive (no auth, generous rate limits, full 2025 coverage measured
    — e.g. 2025-12: 150 posts, 31/31 known SOTD ids, in 2 requests).
    """
    start = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp())
    end_dt = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    end = int(end_dt.timestamp())

    def url_for(cursor: int) -> str:
        return (
            "https://arctic-shift.photon-reddit.com/api/posts/search"
            f"?subreddit=wetshaving&after={start}&before={cursor}&limit=100&sort=desc"
        )

    return _page_archive_ids(
        url_for_page=url_for,
        get_page=_arctic_shift_get,
        start=start,
        end=end,
        source="arctic_shift",
        sleep_s=ARCTIC_SHIFT_SLEEP,
    )


def _resolve_archive_posts(reddit, ids: Set[str], year: int, month: int, source: str) -> List:
    """Convert archive IDs to fresh Reddit submissions; dead IDs are skipped.

    The shared ID-only invariant: the archive discovers, Reddit supplies
    content (IDs resolve via the bulk ``reddit.info`` fetch — not subject to
    the ~1000-item listing limit — and comment trees are fetched separately).
    """
    out = _resolve_ids(reddit, ids)
    logger.info(
        f"{year:04d}-{month:02d}: {source}: resolved {len(out)} of {len(ids)} archive ids on Reddit"
    )
    return out


def discover_via_pullpush(reddit, year: int, month: int) -> List:
    """PullPush archive-discovered posts (IDs only; Reddit supplies content)."""
    ids = pullpush_submission_ids(year, month)
    return _resolve_archive_posts(reddit, ids, year, month, "pullpush")


def discover_via_arctic_shift(reddit, year: int, month: int) -> List:
    """Arctic Shift archive-discovered posts (IDs only; Reddit supplies content)."""
    ids = arctic_shift_submission_ids(year, month)
    return _resolve_archive_posts(reddit, ids, year, month, "arctic_shift")


# --------------------------------------------------------------------------- #
# backfill discovery (months .new() cannot reach)                             #
# --------------------------------------------------------------------------- #
def discover_via_search(subreddit, start_ts: int, end_ts: int) -> List:
    """Reddit search over a UTC timestamp window (lucene ``timestamp:`` syntax).

    Returns [] when the search fails for any reason (unsupported/unindexed
    syntax, rate limit, iteration error) — the recorded discovery meta then
    simply shows no contribution from this strategy.
    """
    query = f"timestamp:{start_ts}..{end_ts}"
    search_fn = getattr(subreddit, "search", None)
    if search_fn is None:
        return []
    try:
        # praw's search() is lazy: the HTTP call happens during iteration, so
        # list() must run inside safe_call to keep failures contained
        raw = safe_call(
            lambda: list(search_fn(query, sort="new", syntax="lucene", time_filter="all"))
        )
    except Exception as e:
        logger.warning(f"timestamp search unavailable: {e}")
        return []
    return list(raw) if raw else []


def _backfill_posts(reddit, subreddit, year: int, month: int, sotd_ids, data_dir):
    """Escalation ladder for months ``new_listing`` cannot confirm.

    thread_seed resolves every known SOTD thread ID fresh from Reddit (full
    trees are fetched later; the pipeline's top-level-only comment store is
    never reused), timestamp search runs only from TIMESTAMP_SEARCH_FLOOR
    (Reddit's search returns nothing below the listing horizon), then the
    archive ladder escalates: Arctic Shift first, PullPush only if the Arctic
    Shift results do not already contain every known SOTD thread. Containment
    — an archive result set holding every known SOTD thread — is treated as
    month completeness; author-submission scanning was removed (it pulled in
    other subreddits and never earned confidence).
    A strategy is listed only when it contributed at least one post.
    Returns (posts, strategies_used, per_strategy_raw_counts, archive_confident).
    """
    month_str = f"{year:04d}-{month:02d}"
    start_dt = datetime(year, month, 1, tzinfo=timezone.utc)
    end_dt = (
        datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        if month == 12
        else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    )
    start_ts, end_ts = int(start_dt.timestamp()), int(end_dt.timestamp())
    known: Set[str] = sotd_ids or set()

    found: dict = {}
    strategies: List[str] = []
    per_strategy: dict = {}

    if sotd_ids:
        logger.info(f"{month_str}: thread_seed: resolving {len(sotd_ids)} known SOTD threads…")
        found = {sub.id: sub for sub in _resolve_ids(reddit, sotd_ids)}
        per_strategy["thread_seed"] = len(found)
        logger.info(f"{month_str}: thread_seed: resolved {len(found)} of {len(sotd_ids)}")
        if found:
            strategies.append("thread_seed")

    if month_str >= REDDIT_HORIZON_FLOOR:
        search_posts = discover_via_search(subreddit, start_ts, end_ts)
        per_strategy["timestamp_search"] = len(search_posts)
        logger.info(f"{month_str}: timestamp_search: found {len(search_posts)} posts")
        if search_posts:
            strategies.append("timestamp_search")
        for sub in search_posts:
            found.setdefault(sub.id, sub)
    else:
        logger.info(
            f"{month_str}: timestamp_search: skipped (month before {REDDIT_HORIZON_FLOOR} floor)"
        )

    def containment(status: str) -> bool:
        if not known:
            return False
        present = len(known & archive_result_ids)
        if present == len(known):
            logger.info(
                f"{month_str}: archive containment: all {len(known)} known SOTD threads "
                f"present in archive results — month complete"
            )
            return True
        logger.info(
            f"{month_str}: archive containment: {present} of {len(known)} known SOTD threads "
            f"present — {status}"
        )
        return False

    archive_result_ids: Set[str] = set()
    archive_confident = False

    arctic_posts = discover_via_arctic_shift(reddit, year, month)
    per_strategy["arctic_shift"] = len(arctic_posts)
    if arctic_posts:
        strategies.append("arctic_shift")
    for sub in arctic_posts:
        found.setdefault(sub.id, sub)
    archive_result_ids |= {s.id for s in arctic_posts}
    if containment("engaging pullpush fallback"):
        archive_confident = True
    else:
        pullpush_posts = discover_via_pullpush(reddit, year, month)
        per_strategy["pullpush"] = len(pullpush_posts)
        if pullpush_posts:
            strategies.append("pullpush")
        for sub in pullpush_posts:
            found.setdefault(sub.id, sub)
        archive_result_ids |= {s.id for s in pullpush_posts}
        if containment("month incomplete"):
            archive_confident = True

    logger.info(
        f"{month_str}: backfill discovery: {len(found)} unique posts via strategies: "
        f"{', '.join(strategies) if strategies else '(none)'}"
    )
    return list(found.values()), strategies, per_strategy, archive_confident


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
    boundary_reached = False
    posts_new: List = []
    archive_confident = False
    ran_listing = month_str >= REDDIT_HORIZON_FLOOR
    if ran_listing:
        posts_new, boundary_reached = discover_month_posts(subreddit, year, month)
        # A listing that ENDED (rather than breaking at the boundary) is not proof
        # the month is complete: Reddit serves only ~1000 listing items, so for
        # months older than ~8 listings-worth the listing dies mid-history. Cross-
        # check against the known SOTD thread IDs — any missing means the month was
        # never fully enumerated, and the backfill strategies must engage.
        if boundary_reached and sotd_ids:
            missing_sotd = sotd_ids - {s.id for s in posts_new}
            if missing_sotd:
                logger.warning(
                    f"{month_str}: listing ended without reaching the month boundary; "
                    f"{len(missing_sotd)} known SOTD threads missing — engaging backfill discovery"
                )
                boundary_reached = False
        strategies_used = ["new_listing"]
        per_strategy = {"new_listing": len(posts_new)}
    else:
        logger.info(
            f"{month_str}: /new listing skipped (month older than {REDDIT_HORIZON_FLOOR}; "
            "Reddit's listing cannot reach it)"
        )
        strategies_used = []
        per_strategy = {}
    if not boundary_reached:
        if ran_listing:
            logger.warning(
                f"{month_str}: listing could not confirm the month boundary; "
                "engaging backfill discovery"
            )
        backfill_posts, strategies, backfill_counts, archive_confident = _backfill_posts(
            reddit, subreddit, year, month, sotd_ids, args.data_dir
        )
        by_id = {s.id: s for s in posts_new}
        for s in backfill_posts:
            by_id.setdefault(s.id, s)
        posts_new = sorted(by_id.values(), key=lambda s: s.created_utc, reverse=True)
        strategies_used = strategies_used + [s for s in strategies if s not in strategies_used]
        per_strategy.update(backfill_counts)

    new_posts = [
        build_post_record(s, in_pipeline=None if sotd_ids is None else s.id in sotd_ids)
        for s in posts_new
    ]

    logger.info(f"{month_str}: fetching comment trees for {len(posts_new)} threads…")
    new_comments, fetch_failed_ids = _fetch_comment_records(posts_new)

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

    # completeness: the listing enumerated the month, OR the archive results
    # contained every known SOTD thread (the backfill ladder's success signal);
    # AND every comment tree actually fetched (a 429 that survives retries
    # leaves the month incomplete rather than silently partial)
    comment_fetch = {"complete": not fetch_failed_ids, "failed_thread_ids": fetch_failed_ids}
    complete = (boundary_reached or archive_confident) and not fetch_failed_ids
    meta = {
        "month": month_str,
        "extracted_at": datetime.now(timezone.utc).isoformat(),
        "post_count": len(posts),
        "comment_count": len(comments),
        "in_pipeline_post_count": sum(1 for p in posts if p.get("in_pipeline")),
        "discovery": {
            "strategies": strategies_used,
            "complete": boundary_reached or archive_confident,
            "per_strategy": per_strategy,
        },
        "comment_fetch": comment_fetch,
    }
    write_community_file(out_path, meta, posts, comments)
    fetch_note = (
        ""
        if comment_fetch["complete"]
        else (
            f"; comment fetch INCOMPLETE: {len(fetch_failed_ids)} threads "
            f"({', '.join(fetch_failed_ids[:5])}{'…' if len(fetch_failed_ids) > 5 else ''})"
        )
    )
    logger.info(
        f"{month_str}: wrote {len(posts)} posts / {len(comments)} comments "
        f"(discovery: {', '.join(strategies_used)}, "
        f"{'complete' if boundary_reached or archive_confident else 'INCOMPLETE'}"
        f"{fetch_note})"
    )
    return {
        "year": year,
        "month": month,
        "posts": len(posts),
        "comments": len(comments),
        "complete": complete,
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

        if results:
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
