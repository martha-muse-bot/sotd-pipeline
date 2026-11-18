#!/usr/bin/env python3
"""Tests for product usage aggregator."""

from sotd.aggregate.aggregators.product_usage import aggregate_product_usage


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


def test_aggregate_product_usage_empty():
    """Test aggregation with empty records."""
    result = aggregate_product_usage([])
    assert result == {"razors": {}, "blades": {}, "brushes": {}, "soaps": {}}


def test_aggregate_product_usage_basic():
    """Test basic product usage aggregation."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
        create_test_record(
            "user2",
            "comment2",
            "SOTD - January 2, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
    ]

    result = aggregate_product_usage(records)

    assert "razors" in result
    assert "Gillette|Tech" in result["razors"]

    product_analysis = result["razors"]["Gillette|Tech"]
    assert product_analysis["product"]["brand"] == "Gillette"
    assert product_analysis["product"]["model"] == "Tech"
    assert product_analysis["total_usage"] == 2
    assert product_analysis["unique_users"] == 2
    assert len(product_analysis["users"]) == 2


def test_aggregate_product_usage_razor_brand_only():
    """Razors with brand but no model are included so manufacturer totals match the report."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Filarmonica"}},
        ),
        create_test_record(
            "user2",
            "comment2",
            "SOTD - January 2, 2025",
            razor={"matched": {"brand": "Filarmonica", "model": ""}},
        ),
    ]
    result = aggregate_product_usage(records)
    assert "razors" in result
    # Key uses empty model; display model is "—"
    assert "Filarmonica|" in result["razors"]
    product_analysis = result["razors"]["Filarmonica|"]
    assert product_analysis["product"]["brand"] == "Filarmonica"
    assert product_analysis["product"]["model"] == "—"
    assert product_analysis["total_usage"] == 2
    assert product_analysis["unique_users"] == 2


def test_aggregate_product_usage_multiple_products():
    """Test aggregation with multiple products."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
            blade={"matched": {"brand": "Gillette", "model": "Minora"}},
        ),
        create_test_record(
            "user1",
            "comment2",
            "SOTD - January 2, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
            soap={"matched": {"brand": "Barrister", "scent": "Mann"}},
        ),
    ]

    result = aggregate_product_usage(records)

    # Check razors
    assert "Gillette|Tech" in result["razors"]
    assert result["razors"]["Gillette|Tech"]["total_usage"] == 2

    # Check blades
    assert "Gillette|Minora" in result["blades"]
    assert result["blades"]["Gillette|Minora"]["total_usage"] == 1

    # Check soaps
    assert "Barrister|Mann" in result["soaps"]
    assert result["soaps"]["Barrister|Mann"]["total_usage"] == 1


def test_aggregate_product_usage_user_data():
    """Test product usage includes user breakdown."""
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
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
        create_test_record(
            "user2",
            "comment3",
            "SOTD - January 3, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
    ]

    result = aggregate_product_usage(records)

    product_analysis = result["razors"]["Gillette|Tech"]
    assert len(product_analysis["users"]) == 2

    # Find user1
    user1_data = next((u for u in product_analysis["users"] if u["username"] == "user1"), None)
    assert user1_data is not None
    assert user1_data["usage_count"] == 2
    assert len(user1_data["comment_ids"]) == 2
    assert len(user1_data["usage_dates"]) == 2


def test_aggregate_product_usage_comments_by_date():
    """Test comments_by_date structure."""
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
            "SOTD - January 1, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
        create_test_record(
            "user1",
            "comment3",
            "SOTD - January 2, 2025",
            razor={"matched": {"brand": "Gillette", "model": "Tech"}},
        ),
    ]

    result = aggregate_product_usage(records)

    product_analysis = result["razors"]["Gillette|Tech"]
    assert "2025-01-01" in product_analysis["comments_by_date"]
    assert "2025-01-02" in product_analysis["comments_by_date"]
    assert len(product_analysis["comments_by_date"]["2025-01-01"]) == 2
    assert len(product_analysis["comments_by_date"]["2025-01-02"]) == 1
    assert "usage_by_date" in product_analysis
    assert product_analysis["usage_by_date"] == product_analysis["comments_by_date"]


def test_aggregate_product_usage_soap_scent():
    """Test soap aggregation uses scent as model."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            soap={"matched": {"brand": "Barrister", "scent": "Mann"}},
        ),
    ]

    result = aggregate_product_usage(records)

    assert "Barrister|Mann" in result["soaps"]
    product_analysis = result["soaps"]["Barrister|Mann"]
    assert product_analysis["product"]["brand"] == "Barrister"
    assert product_analysis["product"]["model"] == "Mann"  # scent used as model


def test_aggregate_product_usage_excludes_mashup_soaps():
    """Mashup soaps should not appear as distinct products in usage analysis."""
    records = [
        create_test_record(
            "user1",
            "comment1",
            "SOTD - January 1, 2025",
            soap={
                "matched": {"brand": "Stirling Soap Co.", "scent": "Sample Mash Up"},
                "enriched": {"is_mashup": True},
            },
        ),
        create_test_record(
            "user1",
            "comment2",
            "SOTD - January 2, 2025",
            soap={
                "matched": {"brand": "Barrister", "scent": "Seville"},
                "enriched": {},
            },
        ),
    ]

    result = aggregate_product_usage(records)

    assert len(result["soaps"]) == 1
    assert "Barrister|Seville" in result["soaps"]
    assert "Stirling Soap Co.|Sample Mash Up" not in result["soaps"]


def test_aggregate_product_usage_comment_urls():
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

    result = aggregate_product_usage(records)

    product_analysis = result["razors"]["Gillette|Tech"]
    assert "comment_urls" in product_analysis
    assert (
        product_analysis["comment_urls"]["comment1"]
        == "https://reddit.com/r/wetshaving/comments/abc123/comment1"
    )
