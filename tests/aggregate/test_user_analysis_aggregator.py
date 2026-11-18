#!/usr/bin/env python3
"""Tests for user analysis aggregator."""

from sotd.aggregate.aggregators.user_analysis import aggregate_user_analysis


def create_test_record(
    author: str,
    comment_id: str,
    thread_title: str,
    razor: dict | None = None,
    blade: dict | None = None,
    brush: dict | None = None,
    soap: dict | None = None,
) -> dict:
    """Create a test record with specified fields."""
    record = {
        "author": author,
        "id": comment_id,
        "thread_title": thread_title,
    }
    if razor:
        record["razor"] = razor
    if blade:
        record["blade"] = blade
    if brush:
        record["brush"] = brush
    if soap:
        record["soap"] = soap
    return record


def test_aggregate_user_analysis_empty():
    """Test aggregation with empty records."""
    result = aggregate_user_analysis([])
    assert result == {}


def test_aggregate_user_analysis_basic():
    """Test basic user analysis aggregation."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
        create_test_record(
            "user1",
            "comment2",
            "SOTD - January 2, 2025",
            blade={"matched": {"brand": "Gillette", "model": "Minora"}},
        ),
    ]

    result = aggregate_user_analysis(records)

    assert "user1" in result
    user_analysis = result["user1"]
    assert user_analysis["user"] == "user1"
    assert user_analysis["posted_days"] == 2
    assert len(user_analysis["posted_dates"]) == 2
    assert "2025-01-01" in user_analysis["posted_dates"]
    assert "2025-01-02" in user_analysis["posted_dates"]
    assert len(user_analysis["comment_ids"]) == 2
    assert "comment1" in user_analysis["comment_ids"]
    assert "comment2" in user_analysis["comment_ids"]
    assert len(user_analysis["razors"]) == 1
    assert user_analysis["razors"][0]["brand"] == "Gillette"
    assert user_analysis["razors"][0]["model"] == "Tech"
    assert user_analysis["razors"][0]["count"] == 1


def test_aggregate_user_analysis_product_usage():
    """Test user analysis includes product usage data."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
            blade={"matched": {"brand": "Gillette", "model": "Minora"}},
            soap={"matched": {"brand": "Barrister", "scent": "Mann"}},
        ),
        create_test_record(
            "user1",
            "comment2",
            "SOTD - January 2, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
            brush={"matched": {"brand": "Semogue", "model": "610"}},
        ),
    ]

    result = aggregate_user_analysis(records)

    user_analysis = result["user1"]

    # Check razors
    assert len(user_analysis["razors"]) == 1
    assert user_analysis["razors"][0]["count"] == 2
    assert len(user_analysis["razors"][0]["comment_ids"]) == 2

    # Check blades
    assert len(user_analysis["blades"]) == 1
    assert user_analysis["blades"][0]["count"] == 1

    # Check brushes
    assert len(user_analysis["brushes"]) == 1
    assert user_analysis["brushes"][0]["count"] == 1

    # Check soaps
    assert len(user_analysis["soaps"]) == 1
    assert user_analysis["soaps"][0]["count"] == 1


def test_aggregate_user_analysis_multiple_users():
    """Test aggregation with multiple users."""
    records = [
        create_test_record("user1", "comment1", "SOTD - January 1, 2025"),
        create_test_record("user2", "comment2", "SOTD - January 1, 2025"),
        create_test_record("user1", "comment3", "SOTD - January 2, 2025"),
    ]

    result = aggregate_user_analysis(records)

    assert len(result) == 2
    assert "user1" in result
    assert "user2" in result
    assert result["user1"]["posted_days"] == 2
    assert result["user2"]["posted_days"] == 1


def test_aggregate_user_analysis_comments_by_date():
    """Test comments_by_date structure."""
    records = [
        create_test_record("user1", "comment1", "SOTD - January 1, 2025"),
        create_test_record("user1", "comment2", "SOTD - January 1, 2025"),
        create_test_record("user1", "comment3", "SOTD - January 2, 2025"),
    ]

    result = aggregate_user_analysis(records)

    user_analysis = result["user1"]
    assert "2025-01-01" in user_analysis["comments_by_date"]
    assert "2025-01-02" in user_analysis["comments_by_date"]
    assert len(user_analysis["comments_by_date"]["2025-01-01"]) == 2
    assert len(user_analysis["comments_by_date"]["2025-01-02"]) == 1


def test_aggregate_user_analysis_missed_days():
    """Test missed days calculation."""
    # Create records for Jan 1 and Jan 3 (missing Jan 2)
    records = [
        create_test_record("user1", "comment1", "SOTD - January 1, 2025"),
        create_test_record("user1", "comment2", "SOTD - January 3, 2025"),
    ]

    result = aggregate_user_analysis(records)

    user_analysis = result["user1"]
    # January 2025 has 31 days, user posted 2 days, so missed 29 days
    assert user_analysis["missed_days"] == 29
    assert user_analysis["posted_days"] == 2


def test_aggregate_user_analysis_comment_urls():
    """Test that comment URLs are extracted and stored."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
    ]
    # Add URL to record
    records[0]["url"] = "https://reddit.com/r/wetshaving/comments/abc123/comment1"

    result = aggregate_user_analysis(records)

    user_analysis = result["user1"]
    assert "comment_urls" in user_analysis
    assert (
        user_analysis["comment_urls"]["comment1"]
        == "https://reddit.com/r/wetshaving/comments/abc123/comment1"
    )
