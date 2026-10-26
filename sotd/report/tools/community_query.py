"""Point-query CLI for community context data.

Answers the questions agents and shell debugging need about ``data/community/``
without loading whole month files into context:
thread listings, one thread with its reconstructed comment tree (top-level
and tail views), bounded body slices for chosen post or comment ids
("body reads"), keyword/author search across a bounded month window, and
a census of deleted/removed/authorless records. The ``full`` subcommand
streams the *entire* month record — every post body plus every thread's
complete comment tree, no truncation — in deterministic bounded parts
for agents whose context can hold a whole month.

Month/window arguments are always explicit — this structurally enforces the
"never see future months" rule (same mechanism as --end on history queries).

Exit codes: 0 success, 1 on query errors (missing/malformed month file,
unknown thread ID, bad window).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path


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
    reverse: bool = False,
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

    rows.sort(key=keymap_for(sort), reverse=reverse)

    if as_json:
        return json.dumps(
            [{k: v for k, v in r.items() if k != "_comments"} for r in rows[:top]], indent=2
        )

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
        description="Query data/community JSON files (meta, thread listings, thread trees, search, gaps).",
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
        "--reverse",
        action="store_true",
        help="Reverse the sort (e.g. newest first with --sort date)",
    )
    threads.add_argument(
        "--sort", choices=["comments", "score", "date"], default="comments", help="Sort key"
    )
    threads.add_argument(
        "--filter",
        choices=["sotd", "non-sotd", "all"],
        default="all",
        help="Key off the in_pipeline flag (default all)",
    )

    thread = sub.add_parser("thread", help="One thread with its reconstructed comment tree")
    thread.add_argument("--month", required=True, help="Month (YYYY-MM)")
    thread.add_argument("--id", required=True, help="Thread ID (with or without t3_ prefix)")
    thread.add_argument(
        "--top-level",
        action="store_true",
        help="Render only top-level comments, each with its direct-reply count",
    )
    slice_group = thread.add_mutually_exclusive_group()
    slice_group.add_argument("--max-comments", type=int, default=50, help="Max comments rendered")
    slice_group.add_argument("--tail", type=int, help="Render the last N comments by time")

    bodies = sub.add_parser("bodies", help="Bounded body slices for chosen post or comment ids")
    bodies.add_argument("--month", required=True, help="Month (YYYY-MM)")
    bodies.add_argument(
        "--ids",
        "--id",
        required=True,
        help="Comma-separated post or comment ids (t3_/t1_ prefix optional)",
    )
    bodies.add_argument(
        "--max-chars", type=int, default=1000, help="Slice each body to this many chars"
    )

    schema = sub.add_parser("schema", help="Show meta keys, counts, and post/comment record keys")
    posts_lookup = sub.add_parser(
        "posts", help="Post metadata (id/author/title/date/selftext-head) for chosen ids"
    )
    posts_lookup.add_argument("--month", required=True, help="Month (YYYY-MM)")
    posts_lookup.add_argument(
        "--ids",
        "--id",
        required=True,
        help="Comma-separated post ids (t3_ prefix optional)",
    )
    full = sub.add_parser(
        "full", help="Stream the entire month record (all posts + full comment trees) in parts"
    )
    full.add_argument("month", help="Month to render, YYYY-MM (explicit, never inferred)")
    full.add_argument("--part", type=int, default=1, help="Which part to render (1-based)")
    full.add_argument(
        "--chars-per-part",
        type=int,
        default=600_000,
        help="Approximate part size in characters (~4 chars/token)",
    )
    schema.add_argument("--month", required=True, help="Month (YYYY-MM)")

    search = sub.add_parser("search", help="Keyword/author search across a bounded window")
    search.add_argument("--months", required=True, help="Window YYYY-MM:YYYY-MM (inclusive)")
    search.add_argument("--query", required=True, help="Case-insensitive substring")
    search.add_argument("--author", help="Exact author name (case-insensitive)")
    search.add_argument("--top", type=int, default=20, help="Max results (default 20)")

    gaps = sub.add_parser("gaps", help="Census of deleted/removed/authorless posts and comments")
    gaps.add_argument("--month", required=True, help="Month (YYYY-MM)")
    gaps.add_argument(
        "--summary",
        action="store_true",
        help="Headline counts + per-thread hotspot ranking instead of the full id list",
    )

    verify = sub.add_parser(
        "verify-ids",
        help="Check every t1_/t3_ id cited in a text file against a month's record",
    )
    verify.add_argument("--month", required=True, help="Month (YYYY-MM) to check ids against")
    verify.add_argument("file", help="Text file (e.g. a summary) whose ids should be validated")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "search":
            parts = args.months.split(":")
            if len(parts) != 2:
                raise QueryError(f"Window must be YYYY-MM:YYYY-MM (got: {args.months})")
            start, end = parts
            months = month_iter(parse_month(start), parse_month(end))
            docs, missing = _search_docs(args.data_dir, months)
            print(
                cmd_search(
                    docs,
                    query=args.query,
                    author=args.author,
                    top=args.top,
                    as_json=args.json,
                    missing=missing,
                )
            )
        else:
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
                        reverse=args.reverse,
                        thread_filter=args.filter,
                        as_json=args.json,
                    )
                )
            elif args.command == "thread":
                print(
                    cmd_thread(
                        doc,
                        args.id,
                        max_comments=args.max_comments,
                        as_json=args.json,
                        top_level=args.top_level,
                        tail=args.tail,
                    )
                )
            elif args.command == "schema":
                print(cmd_schema(doc, as_json=args.json))
            elif args.command == "full":
                print(cmd_full(doc, part=args.part, chars_per_part=args.chars_per_part))
            elif args.command == "bodies":
                ids = [s for s in (i.strip() for i in args.ids.split(",")) if s]
                if not ids:
                    raise QueryError("No ids given (--ids is comma-separated)")
                print(cmd_bodies(doc, ids, max_chars=args.max_chars, as_json=args.json))
            elif args.command == "posts":
                ids = [s for s in (i.strip() for i in args.ids.split(",")) if s]
                if not ids:
                    raise QueryError("No ids given (--ids is comma-separated)")
                print(cmd_posts(doc, ids))
            elif args.command == "gaps":
                print(cmd_gaps(doc, as_json=args.json, summary=args.summary))
            elif args.command == "verify-ids":
                print(cmd_verify_ids(doc, args.file))
            else:
                raise QueryError(f"Unknown command: {args.command}")
        return 0
    except QueryError as e:
        print(str(e), file=sys.stderr)
        return 1


def _flatten_body(body: str) -> str:
    return " / ".join(line.strip() for line in (body or "").splitlines() if line.strip())


def cmd_full(doc: dict, *, part: int = 1, chars_per_part: int = 600_000) -> str:
    """Render the entire month record — every post, every comment, full bodies.

    Deterministic parting: part 1 carries all posts (id/date/author/score/title/
    body) plus the first threads' full comment trees; later parts continue at
    thread boundaries. ~600k chars ≈ ~150k tokens per part. The same month,
    same args → same output, so an agent can resume at `--part 2` after reading
    part 1. Gapped records render their markers ([deleted]/[removed]) as-is.
    """
    if part < 1:
        raise QueryError("--part must be a positive integer")
    if chars_per_part < 100:
        raise QueryError("--chars-per-part must be >= 100")

    counts = comment_counts(doc)
    posts = doc["data"].get("posts", [])
    comments = doc["data"].get("comments", [])
    by_thread: dict = {}
    for c in comments:
        by_thread.setdefault(c["thread_id"], []).append(c)

    # Token trims: (1) no URL lines — the id is the permalink's key part; (2)
    # exact-duplicate post bodies (AutoModerator daily templates) render once
    # in full, repeats as a one-line pointer. Dedupe is by exact selftext hash
    # in post order; only identical bodies collapse.
    body_seen: dict[int, str] = {}

    # Render units: one block per post (header + body), then per-thread trees.
    # Posts without comments render in the posts section; thread blocks follow.
    post_blocks: list[str] = []
    thread_blocks: list[str] = []
    commented: set = set()
    for p in posts:
        pid = p["id"]
        lines = [
            f"{pid}  {p['created_utc'][:10]}  u/{p.get('author')}  "
            f"{counts.get(pid, 0)} comments  score {p['score']}"
            + (f"  flair={p['flair']}" if p.get("flair") else ""),
            p["title"],
        ]
        st = p.get("selftext") or ""
        # Dedupe only real, substantive bodies. Deletion markers ("[deleted]",
        # "[removed]") repeat across posts by nature — collapsing them would
        # misreport genuine gaps as shared content.
        if st and st not in _CONTENT_MARKERS:
            key = hash(st)
            first = body_seen.get(key)
            if first is None:
                body_seen[key] = pid
                lines.append("--- body ---")
                lines.append(st)
            else:
                lines.append(f"--- body: identical to {first} ---")
        elif st:
            lines.append("--- body ---")
            lines.append(st)
        n = by_thread.get(pid)
        if n:
            commented.add(pid)
            cmts = sorted(n, key=lambda c: c["created_utc"])
            children: dict = {}
            for c in cmts:
                children.setdefault(c["parent_id"].removeprefix("t1_"), []).append(c)

            def walk(parent: str, depth: int) -> None:
                prev: tuple | None = None  # (author, body) of the last rendered sibling
                run_ids: list[str] = []
                for c in sorted(children.get(parent, []), key=lambda x: x["created_utc"]):
                    body = _flatten_body(c["body"])
                    key = (c.get("author"), body)
                    if key == prev and body:
                        # Consecutive identical comment from the same author under
                        # the same parent — LatherBot confirmation spam renders as
                        # one line plus a pointer that keeps the collapsed ids.
                        run_ids.append(c["id"])
                        walk(c["id"], depth + 1)
                        continue
                    if run_ids:
                        lines.append(
                            f"{'  ' * depth}(+{len(run_ids)} identical: "
                            f"{', '.join(f't1_{i}' for i in run_ids)})"
                        )
                        run_ids = []
                    prev = key
                    op = " (OP)" if c.get("is_submitter") else ""
                    lines.append(
                        f"{'  ' * depth}[{c['id']}] u/{c['author']} {c['created_utc'][:10]}{op}: {body}"
                    )
                    walk(c["id"], depth + 1)
                if run_ids:
                    lines.append(
                        f"{'  ' * depth}(+{len(run_ids)} identical: "
                        f"{', '.join(f't1_{i}' for i in run_ids)})"
                    )

            lines.append(f"--- {len(cmts)} comments ---")
            walk(f"t3_{pid}", 0)
        thread_blocks.append("\n".join(lines))
    # Posts with zero fetched comments render in the posts section only.
    post_blocks = [b for b, p in zip(thread_blocks, posts) if p["id"] not in commented]
    thread_blocks = [b for b, p in zip(thread_blocks, posts) if p["id"] in commented]

    header = (
        f"# {doc['meta'].get('month')} full record — {len(posts)} posts, {len(comments)} comments\n"
    )

    # Pack blocks into parts at block boundaries.
    parts: list[list[str]] = [[]]
    size = 0
    for block in post_blocks + thread_blocks:
        bsize = len(block)
        if size and size + bsize > chars_per_part:
            parts.append([])
            size = 0
        parts[-1].append(block)
        size += bsize

    idx = part - 1
    if idx >= len(parts):
        raise QueryError(f"Part {part} does not exist ({len(parts)} parts total)")
    out = [header, f"(part {part} of {len(parts)})"]
    out.extend(parts[idx])
    return "\n".join(out)


def cmd_thread(
    doc: dict,
    thread_id: str,
    *,
    max_comments: int = 50,
    as_json: bool = False,
    top_level: bool = False,
    tail: int | None = None,
) -> str:
    if tail is not None and tail < 1:
        raise QueryError("--tail must be a positive integer")
    pid = thread_id.removeprefix("t3_")
    posts = {p["id"]: p for p in doc["data"].get("posts", [])}
    post = posts.get(pid)
    if post is None:
        raise QueryError(f"Unknown thread: {thread_id} (month {doc['meta'].get('month')})")
    comments = [c for c in doc["data"].get("comments", []) if c["thread_id"] == pid]
    comments.sort(key=lambda c: c["created_utc"])

    # --top-level narrows the pool to direct replies to the post; --tail selects
    # the last N of the pool by time instead of the first --max-comments.
    pool = comments
    direct_replies: Counter | None = None
    if top_level:
        pool = [c for c in comments if c["parent_id"].startswith("t3_")]
        direct_replies = Counter(
            c["parent_id"].removeprefix("t1_")
            for c in comments
            if not c["parent_id"].startswith("t3_")
        )
    selected = pool[-tail:] if tail is not None else pool[:max_comments]

    if as_json:
        payload_comments = selected
        if direct_replies is not None:
            payload_comments = [{**c, "direct_replies": direct_replies[c["id"]]} for c in selected]
        payload = {"post": post, "comments": payload_comments}
        if len(pool) > len(selected):
            payload["truncated"] = True
        return json.dumps(payload, indent=2)

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

    if top_level or tail is not None:
        for c in selected:
            body = _flatten_body(c["body"])[:200]
            op = " (OP)" if c.get("is_submitter") else ""
            line = f"[{c['id']}] u/{c['author']} {c['created_utc'][:10]}{op}: {body}"
            if direct_replies is not None:
                line += f" (+{direct_replies[c['id']]} replies)"
            lines.append(line)
    else:
        children: dict = {}
        for c in comments:
            # Key replies by bare parent id (Reddit stores t1_<id>) so the tree can be
            # walked by bare comment id; top-level t3_<pid> parents match the walk seed.
            children.setdefault(c["parent_id"].removeprefix("t1_"), []).append(c)

        rendered = 0

        def walk(parent: str, depth: int) -> None:
            nonlocal rendered
            for c in sorted(children.get(parent, []), key=lambda x: x["created_utc"]):
                if rendered >= max_comments:
                    return
                body = _flatten_body(c["body"])[:200]
                op = " (OP)" if c.get("is_submitter") else ""
                lines.append(
                    f"{'  ' * depth}[{c['id']}] u/{c['author']} {c['created_utc'][:10]}{op}: {body}"
                )
                rendered += 1
                walk(c["id"], depth + 1)

        walk(f"t3_{pid}", 0)

    if len(pool) > len(selected):
        if tail is None:
            lines.append(f"(comments after the first {len(selected)} not shown)")
        else:
            lines.append(f"(last {len(selected)} of {len(pool)} comments)")
    if top_level:
        lines.append(f"(top-level only: {len(pool)} of {len(comments)} comments)")
    return "\n".join(lines)


_AUTHOR_MARKERS = {None, "", "[deleted]", "[removed]"}
# Reddit base36 ids cited with their t3_/t1_ prefix (the summary contract
# requires the prefix, so verification matches prefixed citations). Lower
# bound 2: any prefixed token is an id by contract.
_ID_RE = re.compile(r"\b(?:t[13]_[a-z0-9]{2,8})\b")
_CONTENT_MARKERS = ("[deleted]", "[removed]")


def _plural(count: int, noun: str) -> str:
    """Count + noun with correct plurality (1 gapped post, 3 gapped comments)."""
    return f"{count} {noun}{'s' if count != 1 else ''}"


def _gap_reasons(record: dict, content_key: str) -> list:
    """Return why a post/comment is gapped — [] when it is healthy.

    An author gap is a null/blank/``[deleted]``/``[removed]`` author; a content
    gap is a ``[deleted]``/``[removed]`` body — empty bodies are legitimate
    and never count.
    """
    reasons = []
    if record.get("author") in _AUTHOR_MARKERS:
        reasons.append("author missing")
    value = record.get(content_key)
    if value == "[deleted]":
        reasons.append(f"{content_key} deleted")
    elif value == "[removed]":
        reasons.append(f"{content_key} removed")
    return reasons


def cmd_gaps(doc: dict, *, as_json: bool = False, summary: bool = False) -> str:
    """Census of deleted/removed/authorless posts and comments, with ids and titles.

    --summary renders headline counts plus a per-thread hotspot ranking instead
    of the full id list — the Open-questions digest in one call.
    """
    posts = doc["data"].get("posts", [])
    comments = doc["data"].get("comments", [])
    gapped_posts = [(p, reasons) for p in posts if (reasons := _gap_reasons(p, "selftext"))]
    gapped_comments = [(c, reasons) for c in comments if (reasons := _gap_reasons(c, "body"))]
    month = doc["meta"].get("month")

    # Overwrite-pattern comments: author intact but body is a mass-deletion
    # placeholder (Redact.dev wipes, "Fuck u/spez" edits, collapse stubs). The
    # classic gap census misses these — the author looks healthy — yet the real
    # text is gone. Detected by pattern, reported per author.
    _OVERWRITE_PATTERNS = (
        "edited to remove comments",
        "fuck u/spez",
        "[removed by reddit]",
        "removed by reddit's",
        "redact",
    )

    def _is_overwrite(body: str) -> str | None:
        low = (body or "").lower()
        for pat in _OVERWRITE_PATTERNS:
            if pat in low:
                return pat
        return None

    overwrites = {}
    for c in comments:
        author = c.get("author")
        if author in _AUTHOR_MARKERS:
            continue
        pat = _is_overwrite(c.get("body", ""))
        if pat:
            key = (author, pat)
            overwrites.setdefault(key, []).append(c["id"])

    if as_json:
        return json.dumps(
            {
                "month": month,
                "post_count": len(posts),
                "comment_count": len(comments),
                "gapped_posts": len(gapped_posts),
                "gapped_comments": len(gapped_comments),
                "overwrite_comments": sum(len(v) for v in overwrites.values()),
                "overwrites": {
                    f"{author} ({pat})": ids for (author, pat), ids in overwrites.items()
                },
                "posts": [
                    {
                        "id": p["id"],
                        "title": p.get("title"),
                        "author": p.get("author"),
                        "selftext": p.get("selftext"),
                        "reasons": reasons,
                    }
                    for p, reasons in gapped_posts
                ],
                "comments": [
                    {
                        "id": c["id"],
                        "thread_id": c.get("thread_id"),
                        "thread_title": c.get("thread_title"),
                        "author": c.get("author"),
                        "body": c.get("body"),
                        "reasons": reasons,
                    }
                    for c, reasons in gapped_comments
                ],
            },
            indent=2,
        )

    lines = [
        f"{month}  gaps: {_plural(len(gapped_posts), 'gapped post')}, "
        f"{_plural(len(gapped_comments), 'gapped comment')} "
        f"(of {_plural(len(posts), 'post')} / {_plural(len(comments), 'comment')})"
    ]
    if summary:
        # Hotspot digest: gap concentration per thread, ranked. Posts and
        # comments are counted separately; thread titles give the context.
        post_hot = Counter((p["id"], (p.get("title") or "")[:50]) for p, _r in gapped_posts)
        cmt_hot = Counter(
            (c.get("thread_id"), (c.get("thread_title") or "")[:50]) for c, _r in gapped_comments
        )
        if overwrites:
            lines.append(
                "overwrites (author intact, body is a mass-deletion placeholder — "
                "invisible to the classic census):"
            )
            for (author, pat), ids in sorted(overwrites.items(), key=lambda kv: -len(kv[1])):
                lines.append(f"  u/{author} [{pat}]: {len(ids)} comments")
        if post_hot:
            lines.append("gapped-post hotspots:")
            for (pid, title), n in post_hot.most_common(10):
                lines.append(f"  t3_{pid}  {n}  {title}")
        if cmt_hot:
            lines.append("gapped-comment hotspots:")
            for (tid, title), n in cmt_hot.most_common(10):
                lines.append(f"  t3_{tid}  {n}  {title}")
        if not post_hot and not cmt_hot and not overwrites:
            lines.append("no deleted, removed, or authorless records")
        return "\n".join(lines)
    if overwrites:
        lines.append(
            "overwrites (author intact, body is a mass-deletion placeholder — "
            "invisible to the classic census):"
        )
        for (author, pat), ids in sorted(overwrites.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"  u/{author} [{pat}]: {len(ids)} comments")
    if not gapped_posts and not gapped_comments and not overwrites:
        lines.append("no deleted, removed, or authorless records")
        return "\n".join(lines)
    if gapped_posts:
        lines.append("posts:")
        for p, _reasons in gapped_posts:
            parts = [f"t3_{p['id']}", f"author={p.get('author')}"]
            if p.get("selftext") in _CONTENT_MARKERS:
                parts.append(f"selftext={p.get('selftext')}")
            parts.append(str(p.get("title")))
            lines.append("  " + "  ".join(parts))
    if gapped_comments:
        lines.append("comments:")
        for c, _reasons in gapped_comments:
            parts = [
                f"t1_{c['id']}",
                f'in t3_{c.get("thread_id")} ("{c.get("thread_title")}")',
                f"author={c.get('author')}",
            ]
            if c.get("body") in _CONTENT_MARKERS:
                parts.append(f"body={c.get('body')}")
            lines.append("  " + "  ".join(parts))
    return "\n".join(lines)


def cmd_verify_ids(doc: dict, file_path: str) -> str:
    """Post-write provenance gate: validate ids cited in a text file.

    Extracts every t1_/t3_ id from the file (ids appear bare too — e.g. inside
    `posts` output or notebook lines) and checks each against the month's
    posts/comments. Ids spanning multiple months are out of scope: only the
    named month's record is consulted, so an id from another month reports as
    unknown (that is correct behavior for a per-month summary).
    """
    path = Path(file_path)
    if not path.exists():
        raise QueryError(f"No such file: {file_path}")
    text = path.read_text(encoding="utf-8", errors="replace")
    cited = set(_ID_RE.findall(text))
    if not cited:
        return f"{path.name}: no t1_/t3_ ids cited"

    post_ids = {p["id"] for p in doc["data"].get("posts", [])}
    comment_ids = {c["id"] for c in doc["data"].get("comments", [])}
    known = post_ids | comment_ids

    unknown = sorted(i for i in cited if i.removeprefix("t1_").removeprefix("t3_") not in known)
    n_posts = sum(1 for i in cited if i.startswith("t3_") and i.removeprefix("t3_") in post_ids)
    n_cmts = sum(1 for i in cited if i.startswith("t1_") and i.removeprefix("t1_") in comment_ids)
    lines = [
        f"{path.name}: {len(cited)} ids cited — {n_posts} t3_ (post) verified, "
        f"{n_cmts} t1_ (comment) verified"
    ]
    if unknown:
        lines.append(f"UNKNOWN ({len(unknown)}):")
        for i in unknown:
            lines.append(f"  {i}")
        lines.append("unknown ids must be fixed or removed before shipping")
    else:
        lines.append("all cited ids verified against the month record")
    return "\n".join(lines)


def cmd_posts(doc: dict, ids: list) -> str:
    """Post metadata for chosen ids — id/author/date/title/selftext head.

    The id→author/title lookup agents otherwise hand-roll; bodies are sliced
    to 200 chars (full bodies go through `bodies` or `full`).
    """
    posts = {p["id"]: p for p in doc["data"].get("posts", [])}
    lines = []
    unknown = []
    for raw in ids:
        pid = raw.removeprefix("t3_").removeprefix("t1_")
        p = posts.get(pid)
        if p is None:
            unknown.append(raw)
            continue
        head = (p.get("selftext") or "")[:200]
        lines.append(
            f"t3_{pid}  {p['created_utc'][:10]}  u/{p.get('author')}  "
            f"{p.get('num_comments')} comments  score {p['score']}"
            + (f"  flair={p['flair']}" if p.get("flair") else "")
            + f"\n  {p.get('title')}"
            + (f"\n  {head}" if head else "")
        )
    if not lines:
        raise QueryError(f"Unknown ids: {', '.join(unknown)}")
    if unknown:
        lines.append(f"(unknown ids: {', '.join(unknown)})")
    return "\n".join(lines)


def cmd_bodies(doc: dict, ids: list, *, max_chars: int = 1000, as_json: bool = False) -> str:
    posts = {p["id"]: p for p in doc["data"].get("posts", [])}
    comments = {c["id"]: c for c in doc["data"].get("comments", [])}
    found = []
    unknown = []
    for raw in ids:
        bare = raw.removeprefix("t3_").removeprefix("t1_")
        post = posts.get(bare)
        if post is not None:
            found.append(("post", bare, post))
            continue
        comment = comments.get(bare)
        if comment is not None:
            found.append(("comment", bare, comment))
        else:
            unknown.append(raw)
    if not found:
        raise QueryError(
            f"None of the requested ids exist in {doc['meta'].get('month')}: "
            f"{', '.join(unknown or ids)}"
        )

    if as_json:
        payload = []
        for kind, rid, rec in found:
            if kind == "post":
                body = rec.get("selftext") or ""
                payload.append(
                    {
                        "kind": kind,
                        "id": rid,
                        "title": rec.get("title"),
                        "author": rec.get("author"),
                        "created_utc": rec["created_utc"],
                        "selftext": body[:max_chars],
                        "truncated": len(body) > max_chars,
                    }
                )
            else:
                body = rec.get("body") or ""
                payload.append(
                    {
                        "kind": kind,
                        "id": rid,
                        "thread_id": rec.get("thread_id"),
                        "thread_title": rec.get("thread_title"),
                        "author": rec.get("author"),
                        "created_utc": rec["created_utc"],
                        "body": body[:max_chars],
                        "truncated": len(body) > max_chars,
                    }
                )
        return json.dumps({"bodies": payload, "unknown_ids": unknown}, indent=2)

    lines = []
    for kind, rid, rec in found:
        if kind == "post":
            lines.append(
                f"t3_{rid}  {rec['created_utc'][:10]}  u/{rec.get('author')}  {rec.get('title')}"
            )
            body = rec.get("selftext") or ""
        else:
            lines.append(
                f"t1_{rid}  {rec['created_utc'][:10]}  u/{rec.get('author')}  "
                f"in t3_{rec.get('thread_id')}: {rec.get('thread_title')}"
            )
            body = rec.get("body") or ""
        if body:
            lines.append(body[:max_chars])
            if len(body) > max_chars:
                lines.append(f"(truncated at {max_chars} chars)")
        else:
            lines.append("(no selftext)" if kind == "post" else "(no body)")
        lines.append("")
    if unknown:
        lines.append(f"(unknown ids: {', '.join(unknown)})")
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines)


def cmd_schema(doc: dict, *, as_json: bool = False) -> str:
    """Show meta keys and record shapes so agents don't probe the JSON by hand."""
    meta = doc["meta"]
    posts = doc["data"].get("posts", [])
    comments = doc["data"].get("comments", [])
    post_keys = sorted({k for p in posts for k in p})
    comment_keys = sorted({k for c in comments for k in c})
    if as_json:
        return json.dumps(
            {
                "month": meta.get("month"),
                "post_count": len(posts),
                "comment_count": len(comments),
                "meta_keys": sorted(meta),
                "post_keys": post_keys,
                "comment_keys": comment_keys,
            },
            indent=2,
        )
    return "\n".join(
        [
            f"{meta.get('month')}  posts={len(posts)}  comments={len(comments)}",
            f"meta keys:    {', '.join(sorted(meta))}",
            f"post keys:    {', '.join(post_keys)}",
            f"comment keys: {', '.join(comment_keys)}",
        ]
    )


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
                        "title": p.get("title"),
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
                        "thread_title": c.get("thread_title"),
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
        title = h.get("thread_title") or h.get("title") or ""
        if h["kind"] == "post":
            lines.append(f"{h['created_utc'][:10]}  [post]     t3_{h['thread_id']}{who}")
        else:
            lines.append(
                f"{h['created_utc'][:10]}  [comment]  t3_{h['thread_id']}  "
                f"t1_{h['comment_id']}{who}"
            )
        if title:
            lines.append(f"           thread: {title[:60]}")
        lines.append(f'           "{h["snippet"]}"')
    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(main())
