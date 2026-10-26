"""Tests for the community_query CLI tool."""

import json
import subprocess
import sys
from pathlib import Path

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

    def test_json_output_hides_internal_comment_key(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "--json", "threads", "--month", "2026-08"]
        )
        assert code == 0
        rows = json.loads(out)
        assert rows
        assert all("_comments" not in r for r in rows)

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "threads", "--month", "2025-01"])
        assert code == 1


class TestThreadReverseSort:
    def test_reverse_sort_date_lists_newest_first(self, data_dir, capsys):
        # ascending date is sotd (Aug 01) -> disc (Aug 05) -> quiet (Aug 10)
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "threads",
                "--month",
                "2026-08",
                "--sort",
                "date",
                "--reverse",
            ],
        )
        assert code == 0
        assert out.index("quiet") < out.index("disc") < out.index("sotd")

    def test_reverse_sort_comments_flips_ranking(self, data_dir, capsys):
        # desc by comments is disc (3) -> quiet (2) -> sotd (1); --reverse flips it
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "threads", "--month", "2026-08", "--reverse"],
        )
        assert code == 0
        assert out.index("sotd") < out.index("quiet") < out.index("disc")


class TestThread:
    def test_renders_tree_indented(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "thread", "--month", "2026-08", "--id", "quiet"],
        )
        assert code == 0
        assert "Quiet question" in out
        lines = out.splitlines()
        c2_line = next(line for line in lines if "[c2]" in line)
        c3_line = next(line for line in lines if "[c3]" in line)
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

    def test_json_output_caps_comments_and_marks_truncated(self, data_dir, capsys):
        # disc has 3 comments; cap to 1 and expect the truncated marker
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
                "disc",
                "--max-comments",
                "1",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert [c["id"] for c in doc["comments"]] == ["c4"]
        assert doc["truncated"] is True


@pytest.fixture
def busy_dir(tmp_path):
    """A month with one thread: three top-level comments and one reply to the second."""
    comm = tmp_path / "community"
    comm.mkdir()
    posts = [
        {
            "id": "busy",
            "title": "Contest thread",
            "selftext": "rules",
            "author": "host",
            "created_utc": "2026-07-01T00:00:00Z",
            "score": 5,
            "num_comments": 4,
            "flair": None,
            "url": "u",
            "locked": False,
            "stickied": False,
            "in_pipeline": False,
        }
    ]
    base = {
        "thread_id": "busy",
        "thread_title": "Contest thread",
        "score": 1,
        "is_submitter": False,
    }
    comments = [
        {
            **base,
            "id": "p1",
            "parent_id": "t3_busy",
            "author": "a1",
            "created_utc": "2026-07-01T01:00:00Z",
            "body": "first entry",
        },
        {
            **base,
            "id": "p2",
            "parent_id": "t3_busy",
            "author": "a2",
            "created_utc": "2026-07-01T02:00:00Z",
            "body": "second entry",
        },
        {
            **base,
            "id": "p3",
            "parent_id": "t3_busy",
            "author": "a3",
            "created_utc": "2026-07-01T03:00:00Z",
            "body": "third entry",
        },
        {
            **base,
            "id": "r1",
            "parent_id": "t1_p2",
            "author": "a1",
            "created_utc": "2026-07-01T04:00:00Z",
            "body": "a reply",
        },
    ]
    make_community_file(comm / "2026-07.json", "2026-07", posts, comments)
    return tmp_path


class TestThreadTopLevel:
    """thread --top-level: only top-level comments, each with its direct-reply count."""

    def test_top_level_renders_only_top_level_comments(self, data_dir, capsys):
        # disc: c4 is top-level; c5 and c6 are replies to it
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "disc",
                "--top-level",
            ],
        )
        assert code == 0
        assert "[c4]" in out
        assert "[c5]" not in out
        assert "[c6]" not in out
        assert "top-level only: 1 of 3 comments" in out

    def test_top_level_shows_direct_reply_counts(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "disc",
                "--top-level",
            ],
        )
        assert code == 0
        assert "(+2 replies)" in out

    def test_top_level_respects_max_comments(self, busy_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(busy_dir),
                "thread",
                "--month",
                "2026-07",
                "--id",
                "busy",
                "--top-level",
                "--max-comments",
                "2",
            ],
        )
        assert code == 0
        assert "[p1]" in out and "[p2]" in out
        assert "[p3]" not in out
        assert "not shown" in out

    def test_top_level_tail_selects_last_top_level_comments(self, busy_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(busy_dir),
                "thread",
                "--month",
                "2026-07",
                "--id",
                "busy",
                "--top-level",
                "--tail",
                "2",
            ],
        )
        assert code == 0
        assert "[p2]" in out and "[p3]" in out
        assert "[p1]" not in out
        assert "[r1]" not in out

    def test_top_level_json_carries_direct_replies(self, data_dir, capsys):
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
                "disc",
                "--top-level",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert len(doc["comments"]) == 1
        assert doc["comments"][0]["id"] == "c4"
        assert doc["comments"][0]["direct_replies"] == 2


class TestThreadTail:
    """thread --tail N: the last N comments by time instead of the first --max-comments."""

    def test_tail_renders_last_comments_chronologically(self, data_dir, capsys):
        # disc comments in time order: c4 (11:00), c5 (12:00), c6 (13:00)
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "disc",
                "--tail",
                "2",
            ],
        )
        assert code == 0
        assert "[c5]" in out and "[c6]" in out
        assert "[c4]" not in out
        assert out.index("[c5]") < out.index("[c6]")
        assert "(last 2 of 3 comments)" in out

    def test_tail_beyond_count_renders_all(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "disc",
                "--tail",
                "99",
            ],
        )
        assert code == 0
        assert "[c4]" in out and "[c5]" in out and "[c6]" in out
        assert "(last" not in out

    def test_tail_json(self, data_dir, capsys):
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
                "disc",
                "--tail",
                "2",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert [c["id"] for c in doc["comments"]] == ["c5", "c6"]
        # the tail slice is partial (c4 omitted) and says so, like max-comments slices
        assert doc["truncated"] is True

    def test_tail_must_be_positive(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "thread",
                "--month",
                "2026-08",
                "--id",
                "disc",
                "--tail",
                "0",
            ],
        )
        assert code == 1
        assert "positive integer" in err

    def test_tail_rejects_max_comments(self, data_dir):
        # both slice selectors at once is meaningless -> argparse usage error
        with pytest.raises(SystemExit) as exc:
            main(
                [
                    "--data-dir",
                    str(data_dir),
                    "thread",
                    "--month",
                    "2026-08",
                    "--id",
                    "disc",
                    "--tail",
                    "2",
                    "--max-comments",
                    "10",
                ]
            )
        assert exc.value.code == 2


@pytest.fixture
def gappy_dir(tmp_path):
    """A month with one deleted post and three gapped comments among healthy records."""
    comm = tmp_path / "community"
    comm.mkdir()
    post_base = {
        "created_utc": "2026-06-01T00:00:00Z",
        "score": 1,
        "num_comments": 0,
        "flair": None,
        "url": "u",
        "locked": False,
        "stickied": False,
        "in_pipeline": False,
    }
    posts = [
        {
            **post_base,
            "id": "ok",
            "title": "Discussion thread",
            "selftext": "rules",
            "author": "mod",
        },
        {
            **post_base,
            "id": "dead",
            "title": "Gone thread",
            "selftext": "[removed]",
            "author": "[deleted]",
        },
    ]
    comment_base = {
        "thread_id": "ok",
        "thread_title": "Discussion thread",
        "created_utc": "2026-06-01T01:00:00Z",
        "score": 1,
        "is_submitter": False,
    }
    comments = [
        {
            **comment_base,
            "id": "delc",
            "parent_id": "t3_ok",
            "author": "[deleted]",
            "body": "[deleted]",
        },
        {**comment_base, "id": "modc", "parent_id": "t3_ok", "author": "mod", "body": "[removed]"},
        {
            **comment_base,
            "id": "orphanc",
            "parent_id": "t3_ok",
            "author": None,
            "body": "some content",
        },
        {
            **comment_base,
            "id": "healthyc",
            "parent_id": "t3_ok",
            "author": "user",
            "body": "all good",
        },
    ]
    make_community_file(comm / "2026-06.json", "2026-06", posts, comments)
    return tmp_path


class TestGaps:
    """gaps: census of deleted/removed/authorless posts and comments with ids."""

    def test_no_gaps_reports_clean(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "gaps", "--month", "2026-08"])
        assert code == 0
        assert "0 gapped posts, 0 gapped comments" in out
        assert "no deleted, removed, or authorless records" in out

    def test_overwrite_pattern_reported(self, tmp_path, capsys):
        """Author-intact comments whose bodies are mass-deletion placeholders
        (Redact/'Fuck u/spez') are real gaps invisible to the classic census."""
        comm = tmp_path / "community"
        comm.mkdir()
        posts = [
            {
                "id": "ok",
                "title": "Thread",
                "selftext": "",
                "author": "a",
                "created_utc": "2026-06-01T00:00:00Z",
                "score": 1,
                "num_comments": 3,
                "flair": None,
                "url": "u",
                "locked": False,
                "stickied": False,
                "in_pipeline": False,
            }
        ]
        base = {
            "thread_id": "ok",
            "thread_title": "Thread",
            "created_utc": "2026-06-01T01:00:00Z",
            "score": 1,
            "is_submitter": False,
        }
        comments = [
            {
                **base,
                "id": "ow1",
                "parent_id": "t3_ok",
                "author": "redacted_user",
                "body": "Edited to remove comments. Fuck u/spez",
            },
            {
                **base,
                "id": "ow2",
                "parent_id": "t3_ok",
                "author": "redacted_user",
                "body": "redact.dev removed this comment",
            },
            {
                **base,
                "id": "healthyc",
                "parent_id": "t3_ok",
                "author": "user",
                "body": "I am fine and this mentions nothing weird",
            },
        ]
        make_community_file(comm / "2026-06.json", "2026-06", posts, comments)
        code, out, _ = run(capsys, ["--data-dir", str(tmp_path), "gaps", "--month", "2026-06"])
        assert code == 0
        assert "overwrites" in out
        # grouped by (author, pattern) — the two placeholder bodies use different patterns
        assert "u/redacted_user [edited to remove comments]: 1 comment" in out
        assert "u/redacted_user [redact]: 1 comment" in out
        # healthy comment must not be counted as an overwrite
        assert "u/user [" not in out

    def test_overwrite_json(self, tmp_path, capsys):
        comm = tmp_path / "community"
        comm.mkdir()
        posts = [
            {
                "id": "ok",
                "title": "Thread",
                "selftext": "",
                "author": "a",
                "created_utc": "2026-06-01T00:00:00Z",
                "score": 1,
                "num_comments": 1,
                "flair": None,
                "url": "u",
                "locked": False,
                "stickied": False,
                "in_pipeline": False,
            }
        ]
        comments = [
            {
                "id": "ow1",
                "thread_id": "ok",
                "thread_title": "Thread",
                "parent_id": "t3_ok",
                "author": "wiper",
                "created_utc": "2026-06-01T01:00:00Z",
                "body": "Fuck u/spez",
                "score": 1,
                "is_submitter": False,
            },
        ]
        make_community_file(comm / "2026-06.json", "2026-06", posts, comments)
        code, out, _ = run(
            capsys, ["--json", "--data-dir", str(tmp_path), "gaps", "--month", "2026-06"]
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["overwrite_comments"] == 1
        assert doc["overwrites"]["wiper (fuck u/spez)"] == ["ow1"]

    def test_lists_gapped_records_with_context(self, gappy_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(gappy_dir), "gaps", "--month", "2026-06"])
        assert code == 0
        assert "1 gapped post, 3 gapped comments" in out
        # the deleted post
        assert "t3_dead" in out
        assert "Gone thread" in out
        assert "author=[deleted]" in out
        assert "selftext=[removed]" in out
        # the three gapped comments: author-deleted, body-removed, authorless
        assert "t1_delc" in out
        assert "t1_modc" in out
        assert "t1_orphanc" in out
        assert "author=None" in out
        assert "body=[removed]" in out
        # comments carry thread context
        assert 'in t3_ok ("Discussion thread")' in out
        # healthy records are not listed
        assert "t1_healthyc" not in out

    def test_healthy_post_not_listed(self, gappy_dir, capsys):
        # the healthy thread "ok" appears only as comment context, never as a gapped post
        code, out, _ = run(capsys, ["--data-dir", str(gappy_dir), "gaps", "--month", "2026-06"])
        assert code == 0
        posts_section = out.split("posts:", 1)[1].split("comments:", 1)[0]
        assert "t3_dead" in posts_section
        assert "t3_ok" not in posts_section

    def test_json(self, gappy_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(gappy_dir), "--json", "gaps", "--month", "2026-06"]
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["month"] == "2026-06"
        assert doc["post_count"] == 2
        assert doc["comment_count"] == 4
        assert doc["gapped_posts"] == 1
        assert doc["gapped_comments"] == 3
        assert doc["posts"][0]["id"] == "dead"
        assert "author missing" in doc["posts"][0]["reasons"]
        assert "selftext removed" in doc["posts"][0]["reasons"]
        assert [c["id"] for c in doc["comments"]] == ["delc", "modc", "orphanc"]
        assert doc["comments"][0]["reasons"] == ["author missing", "body deleted"]
        assert doc["comments"][1]["reasons"] == ["body removed"]
        assert doc["comments"][2]["reasons"] == ["author missing"]

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "gaps", "--month", "2025-01"])
        assert code == 1

    def test_summary_hotspots(self, gappy_dir, capsys):
        """--summary renders headline + per-thread hotspot ranking, no id list."""
        code, out, _ = run(
            capsys, ["--data-dir", str(gappy_dir), "gaps", "--month", "2026-06", "--summary"]
        )
        assert code == 0
        assert "1 gapped post, 3 gapped comments" in out
        assert "gapped-comment hotspots:" in out
        assert "t3_ok" in out  # all 3 gapped comments sit in the healthy thread
        # full id list must NOT appear in summary mode
        assert "t1_delc" not in out
        assert "posts:" not in out or "gapped-post hotspots:" in out


class TestVerifyIds:
    """verify-ids: post-write provenance gate for summary files."""

    def test_all_ids_valid(self, data_dir, tmp_path, capsys):
        f = tmp_path / "summary.md"
        f.write_text("Thread t3_disc said (t1_c4): final verdict (t1_c5).", encoding="utf-8")
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "verify-ids", "--month", "2026-08", str(f)]
        )
        assert code == 0
        assert "all cited ids verified" in out

    def test_unknown_ids_listed(self, data_dir, tmp_path, capsys):
        f = tmp_path / "summary.md"
        f.write_text(
            "Thread t3_disc and the phantom t3_zzzzz9 comment t1_nope00.", encoding="utf-8"
        )
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "verify-ids", "--month", "2026-08", str(f)]
        )
        assert code == 0
        assert "UNKNOWN (2)" in out
        assert "t3_zzzzz9" in out
        assert "t1_nope00" in out

    def test_missing_file_exits_1(self, data_dir, tmp_path, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "verify-ids",
                "--month",
                "2026-08",
                str(tmp_path / "no.md"),
            ],
        )
        assert code == 1

    def test_no_ids_cited(self, data_dir, tmp_path, capsys):
        f = tmp_path / "summary.md"
        f.write_text("No ids in this prose at all.", encoding="utf-8")
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "verify-ids", "--month", "2026-08", str(f)]
        )
        assert code == 0
        assert "no t1_/t3_ ids cited" in out


    def test_bare_renderer_ids_recognized(self, tmp_path, capsys):
        """The renderer emits bare ids ([hjx6b1v]); verify-ids validates them when
        they exist in the record and ignores unknown bare tokens (prose)."""
        comm = tmp_path / "community"
        comm.mkdir()
        make_community_file(
            comm / "2026-08.json",
            "2026-08",
            posts=[
                {
                    "id": "sotdab1",
                    "title": "T",
                    "selftext": "",
                    "author": "a",
                    "created_utc": "2026-08-01T00:00:00Z",
                    "score": 1,
                    "num_comments": 1,
                    "flair": None,
                    "url": "u",
                    "locked": False,
                    "stickied": False,
                    "in_pipeline": False,
                }
            ],
            comments=[
                {
                    "id": "hjx6b1v",
                    "thread_id": "sotdab1",
                    "thread_title": "T",
                    "parent_id": "t3_sotdab1",
                    "author": "b",
                    "created_utc": "2026-08-01T01:00:00Z",
                    "body": "nice shave",
                    "score": 1,
                    "is_submitter": False,
                }
            ],
        )
        f = tmp_path / "summary.md"
        f.write_text(
            "SOTD daily [sotdab1] got a reply (hjx6b1v) and prose like 'part2'.", encoding="utf-8"
        )
        code, out, _ = run(
            capsys, ["--data-dir", str(tmp_path), "verify-ids", "--month", "2026-08", str(f)]
        )
        assert code == 0
        assert "all cited ids verified" in out
        assert "bare ids matched" in out

class TestResolve:
    """resolve: comment lookup by author/phrase/thread for the verify-ids fix loop."""

    def test_lookup_by_author(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "resolve", "--month", "2026-08", "--author", "bigcheese"],
        )
        assert code == 0
        assert "t1_c2" in out
        assert "t1_c5" in out
        assert "t1_c1" not in out  # shaver1's comment not included

    def test_lookup_by_phrase_and_thread(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "resolve",
                "--month",
                "2026-08",
                "--thread",
                "t3_disc",
                "--text",
                "verdict",
            ],
        )
        assert code == 0
        assert "t1_c4" in out
        assert "t1_c2" not in out  # different thread

    def test_no_matches(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "resolve", "--month", "2026-08", "--author", "nobody"],
        )
        assert code == 0
        assert "no matching comments" in out


class TestPosts:
    """posts: post metadata lookup for chosen ids."""

    def test_looks_up_id_with_metadata(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "posts", "--month", "2026-08", "--ids", "disc"]
        )
        assert code == 0
        assert "t3_disc" in out
        assert "u/bigcheese" in out
        assert "Lather Games wrap-up" in out
        assert "the final standings" in out  # selftext head

    def test_accepts_prefix_and_lists_unknown(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "posts", "--month", "2026-08", "--ids", "t3_sotd,zzzz9"],
        )
        assert code == 0
        assert "t3_sotd" in out
        assert "unknown ids: zzzz9" in out

    def test_all_unknown_exits_1(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "posts", "--month", "2026-08", "--ids", "zzzz9"]
        )
        assert code == 1


class TestBodies:
    def test_renders_bounded_bodies_for_chosen_ids(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "disc,quiet"],
        )
        assert code == 0
        assert "t3_disc" in out
        assert "the final standings" in out
        assert "(no selftext)" in out  # quiet has an empty body

    def test_accepts_t3_prefix_in_ids(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "t3_disc"],
        )
        assert code == 0
        assert "the final standings" in out

    def test_max_chars_slices_long_body_and_marks_truncated(self, data_dir, capsys):
        make_community_file(
            data_dir / "community" / "2026-07.json",
            "2026-07",
            posts=[
                {
                    "id": "longpost",
                    "title": "Austere August rules",
                    "selftext": "x" * 2500,
                    "author": "mod",
                    "created_utc": "2026-07-01T06:00:00Z",
                    "score": 5,
                    "num_comments": 0,
                    "flair": None,
                    "url": "u9",
                    "locked": False,
                    "stickied": False,
                    "in_pipeline": False,
                }
            ],
            comments=[],
        )
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "bodies",
                "--month",
                "2026-07",
                "--ids",
                "longpost",
                "--max-chars",
                "500",
            ],
        )
        assert code == 0
        assert "x" * 500 in out
        assert "x" * 501 not in out
        assert "(truncated at 500 chars)" in out

    def test_unknown_ids_listed_while_found_ones_render(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "disc,nope"],
        )
        assert code == 0
        assert "the final standings" in out
        assert "(unknown ids: nope)" in out

    def test_all_unknown_ids_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys, ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "nope"]
        )
        assert code == 1
        assert "nope" in err

    def test_empty_ids_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys, ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", " , "]
        )
        assert code == 1
        assert "No ids" in err

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(
            capsys, ["--data-dir", "/nonexistent", "bodies", "--month", "2025-01", "--ids", "x"]
        )
        assert code == 1
        assert "No community file" in err

    def test_json_output_carries_sliced_selftext_and_unknown_ids(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "--json",
                "bodies",
                "--month",
                "2026-08",
                "--ids",
                "disc,quiet,nope",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert [b["id"] for b in doc["bodies"]] == ["disc", "quiet"]
        assert doc["bodies"][0]["selftext"] == "the final standings"
        assert doc["bodies"][1]["selftext"] == ""
        assert doc["unknown_ids"] == ["nope"]

    def test_comment_ids_render_with_thread_context(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "c4"]
        )
        assert code == 0
        assert "t1_c4" in out
        assert "final verdict posted" in out
        assert "Lather Games wrap-up" in out

    def test_accepts_t1_prefix_in_ids(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "t1_c4"]
        )
        assert code == 0
        assert "final verdict posted" in out

    def test_mixed_post_and_comment_ids_render_in_order(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--ids", "c4,disc"],
        )
        assert code == 0
        assert out.index("t1_c4") < out.index("t3_disc")

    def test_comment_json_output_carries_thread_fields(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "--json",
                "bodies",
                "--month",
                "2026-08",
                "--ids",
                "c4,disc",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["bodies"][0]["kind"] == "comment"
        assert doc["bodies"][0]["id"] == "c4"
        assert doc["bodies"][0]["thread_id"] == "disc"
        assert doc["bodies"][0]["body"] == "final verdict posted"
        assert doc["bodies"][1]["kind"] == "post"
        assert doc["bodies"][1]["selftext"] == "the final standings"

    def test_id_alias_is_accepted(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--data-dir", str(data_dir), "bodies", "--month", "2026-08", "--id", "c4"]
        )
        assert code == 0
        assert "final verdict posted" in out


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
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08:2026-07",
                "--query",
                "x",
            ],
        )
        assert code == 1

    def test_comment_hit_shows_thread_title(self, data_dir, capsys):
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
            ],
        )
        assert code == 0
        assert "[comment]" in out
        assert "thread: Lather Games wrap-up" in out

    def test_json_hits_carry_titles(self, data_dir, capsys):
        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "--json",
                "search",
                "--months",
                "2026-08:2026-08",
                "--query",
                "verdict",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        comment_hits = [m for m in doc["matches"] if m["kind"] == "comment"]
        assert comment_hits
        assert comment_hits[0]["thread_title"] == "Lather Games wrap-up"

        code, out, _ = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "--json",
                "search",
                "--months",
                "2026-08:2026-08",
                "--query",
                "quiet question",
            ],
        )
        assert code == 0
        doc = json.loads(out)
        post_hits = [m for m in doc["matches"] if m["kind"] == "post"]
        assert post_hits
        assert post_hits[0]["title"] == "Quiet question"

    def test_months_without_colon_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08",
                "--query",
                "x",
            ],
        )
        assert code == 1
        assert "YYYY-MM:YYYY-MM" in err

    def test_months_with_extra_colons_exits_1(self, data_dir, capsys):
        code, _, err = run(
            capsys,
            [
                "--data-dir",
                str(data_dir),
                "search",
                "--months",
                "2026-08:2026-08:2026-08",
                "--query",
                "x",
            ],
        )
        assert code == 1
        assert "YYYY-MM:YYYY-MM" in err


class TestMonthIter:
    def test_december_rolls_over_into_next_year(self):
        from sotd.report.tools.community_query import month_iter

        assert month_iter("2026-12", "2027-01") == ["2026-12", "2027-01"]


class TestModuleEntrypoint:
    def test_python_m_invocation_exits_1_on_missing_month(self, tmp_path):
        """Pins the documented `python -m sotd.report.tools.community_query` invocation."""
        repo_root = Path(__file__).resolve().parents[3]
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "sotd.report.tools.community_query",
                "--data-dir",
                str(tmp_path),
                "meta",
                "--month",
                "2099-01",
            ],
            capture_output=True,
            text=True,
            cwd=repo_root,
        )
        assert proc.returncode == 1
        assert "No community file" in proc.stderr


class TestSchema:
    def test_schema_shows_meta_and_counts(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "schema", "--month", "2026-08"])
        assert code == 0
        assert "2026-08" in out
        assert "posts=3" in out
        assert "comments=6" in out
        assert "extracted_at" in out

    def test_schema_shows_post_and_comment_keys(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "schema", "--month", "2026-08"])
        assert code == 0
        assert "title" in out
        assert "selftext" in out
        assert "thread_id" in out
        assert "parent_id" in out

    def test_json_output(self, data_dir, capsys):
        code, out, _ = run(
            capsys, ["--json", "--data-dir", str(data_dir), "schema", "--month", "2026-08"]
        )
        assert code == 0
        doc = json.loads(out)
        assert doc["post_count"] == 3
        assert doc["comment_count"] == 6
        assert "selftext" in doc["post_keys"]
        assert "body" in doc["comment_keys"]

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "schema", "--month", "2025-01"])
        assert code == 1
        assert "No community file" in err


class TestFull:
    """The full-record subcommand: whole month, no truncation, deterministic parts."""

    def test_renders_all_posts_and_full_bodies(self, data_dir, capsys):
        code, out, _ = run(capsys, ["--data-dir", str(data_dir), "full", "2026-08"])
        assert code == 0
        for pid in ("sotd", "disc", "quiet"):
            assert pid in out
        assert "the final standings" in out  # post selftext
        assert "final verdict posted" in out
        assert "(part 1 of " in out

    def test_deleted_bodies_not_deduped(self, tmp_path, capsys):
        """[deleted]/[removed] selftexts repeat across posts by nature — they must
        render as markers, never as 'identical to <id>' (a real bug found by the
        2018-02 summarizer)."""
        comm = tmp_path / "community"
        comm.mkdir()
        posts = [
            {
                "id": f"del{i}",
                "title": f"T{i}",
                "selftext": "[deleted]",
                "author": "a",
                "created_utc": f"2026-05-0{i + 1}T00:00:00Z",
                "score": 1,
                "num_comments": 0,
                "flair": None,
                "url": "u",
                "locked": False,
                "stickied": False,
                "in_pipeline": False,
            }
            for i in range(2)
        ]
        make_community_file(comm / "2026-05.json", "2026-05", posts, [])
        code, out, _ = run(capsys, ["--data-dir", str(tmp_path), "full", "2026-05"])
        assert code == 0
        assert out.count("identical to") == 0
        assert out.count("[deleted]") >= 2

    def test_no_comment_truncation(self, tmp_path, capsys):
        comm = tmp_path / "community"
        comm.mkdir()
        long_body = "x" * 500
        make_community_file(
            comm / "2026-07.json",
            "2026-07",
            posts=[
                {
                    "id": "t1post",
                    "title": "T",
                    "selftext": "",
                    "author": "a",
                    "created_utc": "2026-07-01T00:00:00Z",
                    "score": 1,
                    "num_comments": 1,
                    "flair": None,
                    "url": "u",
                    "locked": False,
                    "stickied": False,
                    "in_pipeline": False,
                }
            ],
            comments=[
                {
                    "id": "lc",
                    "thread_id": "t1post",
                    "thread_title": "T",
                    "parent_id": "t3_t1post",
                    "author": "b",
                    "created_utc": "2026-07-01T01:00:00Z",
                    "body": long_body,
                    "score": 1,
                    "is_submitter": False,
                }
            ],
        )
        _, out, _ = run(capsys, ["--data-dir", str(tmp_path), "full", "2026-07"])
        assert long_body in out  # `thread` cuts at 200 chars; full must not

    def test_deterministic_parts_cover_everything(self, data_dir, capsys):
        parts = []
        n = None
        part = 1
        while True:
            code, out, _ = run(
                capsys, ["--data-dir", str(data_dir), "full", "2026-08", "--part", str(part)]
            )
            if code != 0:
                break
            parts.append(out)
            if n is None:
                n = int(out.split("(part 1 of ")[1].split(")")[0])
            part += 1
        assert part - 1 == n
        joined = "".join(parts)
        for cid in ("c1", "c2", "c4", "c5", "c6"):
            assert cid in joined

    def test_part_out_of_range_exits_1(self, data_dir, capsys):
        code, _, err = run(capsys, ["--data-dir", str(data_dir), "full", "2026-08", "--part", "99"])
        assert code == 1
        assert "does not exist" in err

    def test_chars_per_part_splits_threads(self, tmp_path, capsys):
        comm = tmp_path / "community"
        comm.mkdir()
        make_community_file(
            comm / "2026-06.json",
            "2026-06",
            posts=[
                {
                    "id": f"p{i}",
                    "title": f"T{i}",
                    "selftext": "y" * 50,
                    "author": "a",
                    "created_utc": f"2026-06-0{i + 1}T00:00:00Z",
                    "score": 1,
                    "num_comments": 1,
                    "flair": None,
                    "url": "u",
                    "locked": False,
                    "stickied": False,
                    "in_pipeline": False,
                }
                for i in range(1, 4)
            ],
            comments=[
                {
                    "id": f"c{i}",
                    "thread_id": f"p{i}",
                    "thread_title": f"T{i}",
                    "parent_id": f"t3_p{i}",
                    "author": "b",
                    "created_utc": f"2026-06-0{i + 1}T01:00:00Z",
                    "body": "z" * 50,
                    "score": 1,
                    "is_submitter": False,
                }
                for i in range(1, 4)
            ],
        )
        code, out, _ = run(
            capsys,
            ["--data-dir", str(tmp_path), "full", "2026-06", "--chars-per-part", "400"],
        )
        assert code == 0
        assert "(part 1 of " in out
        n = int(out.split("(part 1 of ")[1].split(")")[0])
        assert n >= 2  # 3 thread blocks at ~150 chars each must split into >=2 parts

    def test_consecutive_duplicates_collapsed(self, tmp_path, capsys):
        """Consecutive identical comments (LatherBot confirmation spam) collapse
        to one line plus a pointer that keeps the collapsed ids; a non-consecutive
        repeat stays rendered in full."""
        comm = tmp_path / "community"
        comm.mkdir()
        comments = [
            {
                "id": "b1",
                "thread_id": "p1",
                "thread_title": "T1",
                "parent_id": "t3_p1",
                "author": "LatherBot",
                "created_utc": "2026-04-01T01:00:00Z",
                "body": "Entry confirmed",
                "score": 1,
                "is_submitter": False,
            },
            {
                "id": "b2",
                "thread_id": "p1",
                "thread_title": "T1",
                "parent_id": "t3_p1",
                "author": "LatherBot",
                "created_utc": "2026-04-01T01:01:00Z",
                "body": "Entry confirmed",
                "score": 1,
                "is_submitter": False,
            },
            {
                "id": "u1",
                "thread_id": "p1",
                "thread_title": "T1",
                "parent_id": "t3_p1",
                "author": "human",
                "created_utc": "2026-04-01T02:00:00Z",
                "body": "great lather",
                "score": 1,
                "is_submitter": False,
            },
            {
                "id": "u2",
                "thread_id": "p1",
                "thread_title": "T1",
                "parent_id": "t3_p1",
                "author": "other",
                "created_utc": "2026-04-01T03:00:00Z",
                "body": "great lather",
                "score": 1,
                "is_submitter": False,
            },
        ]
        make_community_file(
            comm / "2026-04.json",
            "2026-04",
            posts=[
                {
                    "id": "p1",
                    "title": "T1",
                    "selftext": "",
                    "author": "a",
                    "created_utc": "2026-04-01T00:00:00Z",
                    "score": 1,
                    "num_comments": 4,
                    "flair": None,
                    "url": "u",
                    "locked": False,
                    "stickied": False,
                    "in_pipeline": False,
                }
            ],
            comments=comments,
        )
        code, out, _ = run(capsys, ["--data-dir", str(tmp_path), "full", "2026-04"])
        assert code == 0
        assert "(+1 identical: t1_b2)" in out
        assert out.count("great lather") == 2  # both human repeats render in full

    def test_missing_month_exits_1(self, capsys):
        code, _, err = run(capsys, ["--data-dir", "/nonexistent", "full", "2025-01"])
        assert code == 1
        assert "No community file" in err
