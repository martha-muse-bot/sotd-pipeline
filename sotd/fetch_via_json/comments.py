"""Comment fetching functionality via JSON API.

Comment retrieval using Reddit's public JSON endpoints.
"""

from __future__ import annotations

import html
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sotd.fetch_via_json.json_scraper import get_reddit_cookies, get_reddit_json, get_reddit_session


def parse_comment_from_json(json_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Parse a Reddit comment from JSON API response.

    Reddit's JSON API returns comments in this structure:
    {
        "kind": "t1",
        "data": {
            "id": "abc123",
            "author": "username",
            "created_utc": 1704067200.0,
            "body": "comment text",
            "permalink": "/r/wetshaving/comments/thread_id/...",
            ...
        }
    }

    Args:
        json_data: Dictionary from Reddit JSON API (either direct data or wrapped)

    Returns:
        Dictionary with comment fields matching existing format, or None if invalid
    """
    # Handle both direct data and wrapped responses
    if "data" in json_data and isinstance(json_data["data"], dict):
        data = json_data["data"]
    elif "kind" in json_data and json_data["kind"] == "t1":
        data = json_data.get("data", {})
    else:
        data = json_data

    # Extract required fields
    comment_id = data.get("id")
    if not comment_id:
        return None

    # Handle permalink - ensure it starts with /r/
    permalink = data.get("permalink", "")
    if permalink and not permalink.startswith("/r/"):
        # Sometimes permalink is relative, sometimes absolute
        if permalink.startswith("http"):
            # Extract path from URL
            from urllib.parse import urlparse

            parsed = urlparse(permalink)
            permalink = parsed.path

    # Build URL
    if permalink:
        url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink
    else:
        # Fallback: construct URL from thread permalink and comment ID
        # This is less ideal but works if permalink is missing
        url = f"https://www.reddit.com/comments/{comment_id}/"

    # Parse created_utc timestamp
    created_utc = data.get("created_utc", 0)
    if isinstance(created_utc, (int, float)):
        created_dt = datetime.utcfromtimestamp(created_utc).replace(tzinfo=timezone.utc)
        created_utc_iso = created_dt.isoformat().replace("+00:00", "Z")
    else:
        created_utc_iso = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    # Get author (handle deleted users)
    author = data.get("author")
    if author is None or author == "[deleted]":
        author = "[deleted]"
    else:
        author = str(author)

    # Get body (comment text) and decode HTML entities
    # Reddit's JSON API returns HTML-encoded entities (e.g., &amp; for &)
    # PRAW decodes these, so we need to match that behavior
    body = data.get("body", "")
    if body is None:
        body = ""
    else:
        # Decode HTML entities to match PRAW's behavior
        body = html.unescape(body)

    return {
        "id": comment_id,
        "author": author,
        "created_utc": created_utc_iso,
        "body": body,
        "url": url,
    }


def fetch_more_comments(
    thread_id: str,
    comment_ids: List[str],
    *,
    cookies: Optional[dict] = None,
    session: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Fetch additional comments using Reddit's morechildren API.

    Reddit's morechildren endpoint: https://www.reddit.com/api/morechildren.json
    Parameters:
        link_id: t3_{thread_id}
        children: comma-separated comment IDs
        api_type: json

    Args:
        thread_id: Reddit thread ID (without t3_ prefix)
        comment_ids: List of comment IDs to fetch (without t1_ prefix)
        cookies: Optional cookies for authentication
        session: Optional requests.Session

    Returns:
        List of comment dictionaries
    """
    if not comment_ids:
        return []

    if session is None:
        if cookies is None:
            cookies = get_reddit_cookies()
        session = get_reddit_session(cookies=cookies)

    # Build API URL
    api_url = "https://www.reddit.com/api/morechildren.json"

    # Build parameters
    link_id = f"t3_{thread_id}"
    children_param = ",".join(comment_ids)

    params = {
        "link_id": link_id,
        "children": children_param,
        "api_type": "json",
    }

    # Build query string
    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{api_url}?{query_string}"

    try:
        # Fetch JSON
        json_data = get_reddit_json(url, cookies=cookies, session=session)

        # Reddit's morechildren response structure:
        # {"json": {"data": {"things": [{"kind": "t1", "data": {...}}, ...]}}}
        if isinstance(json_data, dict):
            if "json" in json_data and "data" in json_data["json"]:
                things = json_data["json"]["data"].get("things", [])
            elif "data" in json_data and "things" in json_data["data"]:
                things = json_data["data"]["things"]
            else:
                things = []
        else:
            things = []

        comments = []
        for thing in things:
            if thing.get("kind") == "t1":
                # Only include root comments (parent_id starts with t3_)
                data = thing.get("data", {})
                parent_id = data.get("parent_id", "")
                if parent_id.startswith("t3_"):
                    parsed = parse_comment_from_json(thing)
                    if parsed:
                        comments.append(parsed)

        return comments
    except Exception as e:
        print(f"[WARN] Failed to fetch more comments: {e}")
        return []


def extract_top_level_comments(
    json_data: List[Dict[str, Any]],
    thread_id: str,
    *,
    cookies: Optional[dict] = None,
    session: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Extract top-level comments from Reddit's JSON response, including "more" comments.

    Reddit's comment thread JSON structure:
    [
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {"kind": "t3", "data": {...}}  # The thread itself
                ]
            }
        },
        {
            "kind": "Listing",
            "data": {
                "children": [
                    {"kind": "t1", "data": {...}},  # Top-level comment
                    {"kind": "more", "data": {"count": 10, "children": ["id1", "id2", ...]}},  # More comments
                    ...
                ]
            }
        }
    ]

    We only want top-level comments (t1), not replies (which are nested).
    We also fetch "more" comments using the morechildren API.

    Args:
        json_data: List of listings from Reddit JSON API
        thread_id: Reddit thread ID (for fetching more comments)
        cookies: Optional cookies for authentication
        session: Optional requests.Session

    Returns:
        List of top-level comment dictionaries
    """
    if not isinstance(json_data, list) or len(json_data) < 2:
        return []

    # Second element contains comments
    comments_listing = json_data[1]
    if "data" not in comments_listing or "children" not in comments_listing["data"]:
        return []

    children = comments_listing["data"]["children"]
    top_level_comments = []
    more_comment_ids = []

    for child in children:
        kind = child.get("kind")

        if kind == "t1":
            # Top-level comment - verify it's actually root (parent_id starts with t3_)
            data = child.get("data", {})
            parent_id = data.get("parent_id", "")
            if parent_id.startswith("t3_"):
                parsed = parse_comment_from_json(child)
                if parsed:
                    top_level_comments.append(parsed)
        elif kind == "more":
            # "More" object - indicates additional comments to fetch
            more_data = child.get("data", {})
            # Only fetch top-level "more" comments (depth=0 or parent_id starts with t3_)
            if more_data.get("depth", 1) == 0 or more_data.get("parent_id", "").startswith("t3_"):
                more_ids = more_data.get("children", [])
                # Remove t1_ prefix if present
                more_ids = [id.replace("t1_", "") for id in more_ids if id]
                more_comment_ids.extend(more_ids)

    # Fetch "more" comments if any
    if more_comment_ids:
        more_comments = fetch_more_comments(
            thread_id, more_comment_ids, cookies=cookies, session=session
        )
        top_level_comments.extend(more_comments)

    return top_level_comments


def fetch_thread_comments_json(
    thread_id: str,
    thread_title: str,
    thread_url: str,
    *,
    cookies: Optional[dict] = None,
    session: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    """Fetch top-level comments for a thread using JSON API.

    Args:
        thread_id: Reddit thread ID
        thread_title: Thread title (for comment records)
        thread_url: Thread URL (for comment records)
        cookies: Optional cookies for authentication
        session: Optional requests.Session

    Returns:
        List of comment dictionaries with thread_id and thread_title added
    """
    # Build JSON URL: https://www.reddit.com/r/wetshaving/comments/{thread_id}/.json
    # Extract subreddit from thread_url if possible, or use default
    if "/r/" in thread_url:
        # Extract subreddit from URL
        parts = thread_url.split("/r/")
        if len(parts) > 1:
            subreddit = parts[1].split("/")[0]
        else:
            subreddit = "wetshaving"
    else:
        subreddit = "wetshaving"

    json_url = f"https://www.reddit.com/r/{subreddit}/comments/{thread_id}/.json?limit=100&depth=1"

    try:
        # Fetch JSON
        json_data = get_reddit_json(json_url, cookies=cookies, session=session)
        assert isinstance(json_data, list)  # comment-thread endpoints return a two-list JSON shape

        # Extract top-level comments (including "more" comments)
        comments = extract_top_level_comments(
            json_data, thread_id, cookies=cookies, session=session
        )

        # Add thread context to each comment
        for comment in comments:
            comment["thread_id"] = thread_id
            comment["thread_title"] = thread_title

        return comments
    except Exception as e:
        print(f"[WARN] Failed to fetch comments for thread {thread_id}: {e}")
        return []


def fetch_comments_for_threads_json(
    threads: List[Dict[str, Any]],
    *,
    cookies: Optional[dict] = None,
    session: Optional[Any] = None,
    verbose: bool = False,
    parallel: bool = False,
    max_workers: int = 5,
    skip_unchanged: bool = False,
    existing_threads: Optional[List[Dict[str, Any]]] = None,
    existing_comments: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Fetch top-level comments for multiple threads.

    Args:
        threads: List of thread dictionaries (must have 'id', 'title', 'url', 'num_comments')
        cookies: Optional cookies for authentication
        session: Optional requests.Session (not used in parallel mode - each thread gets its own session)
        verbose: Enable verbose output
        parallel: If True, use parallel processing (default: False)
        max_workers: Number of worker threads for parallel processing (default: 5)
        skip_unchanged: If True, skip fetching comments for threads where num_comments hasn't increased
        existing_threads: Optional list of existing thread dictionaries for comparison
        existing_comments: Optional list of existing comment dictionaries to reuse for skipped threads

    Returns:
        List of all comment dictionaries (flattened across all threads)
    """
    if not threads:
        return []

    # Build lookup map for existing threads (thread_id -> thread object)
    existing_thread_map: Dict[str, Dict[str, Any]] = {}
    if existing_threads:
        for thread in existing_threads:
            thread_id = thread.get("id")
            if thread_id:
                existing_thread_map[thread_id] = thread

    # Build lookup map for existing comments (thread_id -> list of comments)
    existing_comments_map: Dict[str, List[Dict[str, Any]]] = {}
    if existing_comments:
        for comment in existing_comments:
            thread_id = comment.get("thread_id")
            if thread_id:
                if thread_id not in existing_comments_map:
                    existing_comments_map[thread_id] = []
                existing_comments_map[thread_id].append(comment)

    # Filter threads based on skip_unchanged logic
    threads_to_fetch = []
    skipped_threads = []
    skipped_comments_count = 0

    for thread in threads:
        thread_id = thread.get("id")
        if not thread_id:
            continue

        current_num_comments = thread.get("num_comments", 0)
        existing_thread = existing_thread_map.get(thread_id)

        if skip_unchanged and existing_thread is not None:
            # Thread exists in existing data - compare num_comments
            existing_num_comments = existing_thread.get("num_comments", 0)
            if current_num_comments > existing_num_comments:
                # num_comments increased - fetch comments
                threads_to_fetch.append(thread)
            else:
                # num_comments unchanged or decreased - skip fetching
                skipped_threads.append(thread)
                # Add existing comments for this thread
                if thread_id in existing_comments_map:
                    skipped_comments_count += len(existing_comments_map[thread_id])
        else:
            # Thread doesn't exist in existing data or skip_unchanged is False - always fetch
            threads_to_fetch.append(thread)

    # Print statistics if skip_unchanged is enabled
    if skip_unchanged and verbose:
        print(
            f"[INFO] Skip-unchanged optimization: "
            f"{len(threads_to_fetch)} threads to fetch, "
            f"{len(skipped_threads)} threads skipped ({skipped_comments_count} comments reused)"
        )

    # Fetch comments for threads that need fetching
    fetched_comments = []
    if threads_to_fetch:
        if parallel:
            fetched_comments = _fetch_comments_parallel(
                threads_to_fetch, cookies=cookies, verbose=verbose, max_workers=max_workers
            )
        else:
            fetched_comments = _fetch_comments_sequential(
                threads_to_fetch, cookies=cookies, session=session, verbose=verbose
            )

    # Add existing comments for skipped threads
    all_comments = list(fetched_comments)
    for skipped_thread in skipped_threads:
        thread_id = skipped_thread.get("id")
        if thread_id and thread_id in existing_comments_map:
            # Ensure comments have proper thread context
            thread_title = skipped_thread.get("title", "")
            for comment in existing_comments_map[thread_id]:
                comment_copy = dict(comment)
                comment_copy["thread_id"] = thread_id
                comment_copy["thread_title"] = thread_title
                all_comments.append(comment_copy)

    return all_comments


def _fetch_comments_sequential(
    threads: List[Dict[str, Any]],
    *,
    cookies: Optional[dict] = None,
    session: Optional[Any] = None,
    verbose: bool = False,
) -> List[Dict[str, Any]]:
    """Fetch comments sequentially (original implementation)."""
    if session is None:
        if cookies is None:
            cookies = get_reddit_cookies()
        session = get_reddit_session(cookies=cookies)

    all_comments = []

    if verbose:
        print(f"[INFO] Fetching comments for {len(threads)} threads (sequential)...")

    for i, thread in enumerate(threads, 1):
        thread_id = thread.get("id")
        thread_title = thread.get("title", "")
        thread_url = thread.get("url", "")

        if not thread_id:
            continue

        try:
            comments = fetch_thread_comments_json(
                thread_id, thread_title, thread_url, cookies=cookies, session=session
            )
            all_comments.extend(comments)

            if verbose and (i % 10 == 0 or i == len(threads)):
                print(
                    f"[INFO] Fetched comments for {i}/{len(threads)} threads ({len(all_comments)} total comments)"
                )
        except Exception as e:
            print(f"[WARN] Failed to fetch comments for thread {thread_id}: {e}")
            continue

    return all_comments


def _fetch_comments_parallel(
    threads: List[Dict[str, Any]],
    *,
    cookies: Optional[dict] = None,
    verbose: bool = False,
    max_workers: int = 5,
) -> List[Dict[str, Any]]:
    """Fetch comments in parallel using ThreadPoolExecutor.

    Note: Each thread gets its own session to avoid thread-safety issues.
    Rate limiting delays are still applied per request.

    Args:
        threads: List of thread dictionaries
        cookies: Optional cookies for authentication
        verbose: Enable verbose output
        max_workers: Number of worker threads

    Returns:
        List of all comment dictionaries
    """
    import concurrent.futures

    if cookies is None:
        cookies = get_reddit_cookies()

    if verbose:
        print(
            f"[INFO] Fetching comments for {len(threads)} threads (parallel, {max_workers} workers)..."
        )

    def fetch_single_thread(thread: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch comments for a single thread (used by parallel executor)."""
        thread_id = thread.get("id")
        thread_title = thread.get("title", "")
        thread_url = thread.get("url", "")

        if not thread_id:
            return []

        # Create a new session for this thread (thread-safe)
        thread_session = get_reddit_session(cookies=cookies)

        try:
            comments = fetch_thread_comments_json(
                thread_id, thread_title, thread_url, cookies=cookies, session=thread_session
            )
            return comments
        except Exception as e:
            if verbose:
                print(f"[WARN] Failed to fetch comments for thread {thread_id}: {e}")
            return []

    all_comments: List[Dict[str, Any]] = []
    completed = 0

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_thread = {
            executor.submit(fetch_single_thread, thread): thread for thread in threads
        }

        # Process completed tasks
        for future in concurrent.futures.as_completed(future_to_thread):
            completed += 1
            try:
                comments = future.result()
                all_comments.extend(comments)

                if verbose and (completed % 10 == 0 or completed == len(threads)):
                    print(
                        f"[INFO] Fetched comments for {completed}/{len(threads)} threads ({len(all_comments)} total comments)"
                    )
            except Exception as e:
                thread = future_to_thread[future]
                thread_id = thread.get("id", "unknown")
                print(f"[WARN] Error fetching comments for thread {thread_id}: {e}")

    return all_comments
