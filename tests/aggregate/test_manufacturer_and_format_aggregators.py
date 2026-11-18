"""Tests for manufacturer and format aggregators."""

from sotd.aggregate.aggregators.formats import aggregate_razor_formats
from sotd.aggregate.aggregators.manufacturers import (
    aggregate_blade_manufacturers,
    aggregate_razor_manufacturers,
    aggregate_soap_makers,
)


def test_aggregate_razor_manufacturers():
    records = [
        {"author": "user1", "razor": {"matched": {"brand": "Gillette"}}},
        {"author": "user2", "razor": {"matched": {"brand": "Gillette"}}},
        {"author": "user1", "razor": {"matched": {"brand": "Fatip"}}},
    ]
    result = aggregate_razor_manufacturers(records)
    assert len(result) == 2
    assert result[0]["brand"] == "Gillette"
    assert result[0]["shaves"] == 2
    assert result[0]["unique_users"] == 2
    assert result[0]["rank"] == 1
    assert result[1]["brand"] == "Fatip"
    assert result[1]["shaves"] == 1
    assert result[1]["unique_users"] == 1
    assert result[1]["rank"] == 2


def test_aggregate_blade_manufacturers():
    records = [
        {"author": "user1", "blade": {"matched": {"brand": "Gillette"}}},
        {"author": "user2", "blade": {"matched": {"brand": "Gillette"}}},
        {"author": "user1", "blade": {"matched": {"brand": "Personna"}}},
    ]
    result = aggregate_blade_manufacturers(records)
    assert len(result) == 2
    assert result[0]["brand"] == "Gillette"
    assert result[0]["shaves"] == 2
    assert result[0]["unique_users"] == 2
    assert result[0]["rank"] == 1
    assert result[1]["brand"] == "Personna"
    assert result[1]["shaves"] == 1
    assert result[1]["unique_users"] == 1
    assert result[1]["rank"] == 2


def test_aggregate_soap_makers():
    records = [
        {"author": "user1", "soap": {"matched": {"brand": "Grooming Dept"}}},
        {"author": "user2", "soap": {"matched": {"brand": "Grooming Dept"}}},
        {"author": "user1", "soap": {"matched": {"brand": "Declaration Grooming"}}},
    ]
    result = aggregate_soap_makers(records)
    assert len(result) == 2
    assert result[0]["brand"] == "Grooming Dept"
    assert result[0]["shaves"] == 2
    assert result[0]["unique_users"] == 2
    assert result[0]["rank"] == 1
    assert result[1]["brand"] == "Declaration Grooming"
    assert result[1]["shaves"] == 1
    assert result[1]["unique_users"] == 1
    assert result[1]["rank"] == 2


def test_aggregate_razor_formats_basic():
    """Test basic razor format aggregation."""
    records = [
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "Straight"}}},
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 2
    assert result[0]["format"] == "DE"
    assert result[0]["shaves"] == 2
    assert result[0]["unique_users"] == 2
    assert result[0]["rank"] == 1
    assert result[0]["avg_shaves_per_user"] == 1.0
    assert result[0]["median_shaves_per_user"] == 1.0
    assert result[1]["format"] == "Straight"
    assert result[1]["shaves"] == 1
    assert result[1]["unique_users"] == 1
    assert result[1]["rank"] == 2
    assert result[1]["avg_shaves_per_user"] == 1.0
    assert result[1]["median_shaves_per_user"] == 1.0


def test_aggregate_razor_formats_shavette_ac():
    """Test shavette with AC blade format combination - uses enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (AC)"},
            },
            "blade": {"matched": {"format": "AC"}},
        },
        {
            "author": "user2",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (AC)"},
            },
            "blade": {"matched": {"format": "AC"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "Shavette (AC)"
    assert result[0]["shaves"] == 2
    assert result[0]["unique_users"] == 2


def test_aggregate_razor_formats_shavette_de():
    """Test shavette with DE blade format (should become Half DE) - uses enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (Half DE)"},
            },
            "blade": {"matched": {"format": "DE"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "Shavette (Half DE)"
    assert result[0]["shaves"] == 1


def test_aggregate_razor_formats_shavette_unspecified():
    """Test shavette with no blade format - uses enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (Unspecified)"},
            },
            "blade": {"matched": {}},  # No format
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "Shavette (Unspecified)"
    assert result[0]["shaves"] == 1


def test_aggregate_razor_formats_shavette_predefined():
    """Test shavette with predefined format (should use as-is)."""
    records = [
        {
            "author": "user1",
            "razor": {"matched": {"format": "Shavette (AC)"}},
            "blade": {"matched": {"format": "DE"}},  # Should be ignored
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "Shavette (AC)"
    assert result[0]["shaves"] == 1


def test_aggregate_razor_formats_half_de_detection():
    """Test Half DE detection logic."""
    records = [
        {
            "author": "user1",
            "razor": {"matched": {"format": "Half DE (multi-blade)"}},
            "blade": {"matched": {"format": "DE"}},
        },
        {
            "author": "user2",
            "razor": {"matched": {"format": "Half DE"}},
            "blade": {"matched": {"format": "DE"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 2
    formats = {r["format"] for r in result}
    assert "Half DE (multi-blade)" in formats
    assert "Half DE" in formats


def test_aggregate_razor_formats_blade_format_fallback():
    """Test blade format fallback when no razor format - uses enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {},  # No format
                "enriched": {"format": "GEM"},
            },
            "blade": {"matched": {"format": "GEM"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "GEM"
    assert result[0]["shaves"] == 1


def test_aggregate_razor_formats_default_de():
    """Test default to DE when no formats available - uses enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {},  # No format
                "enriched": {"format": "DE"},
            },
            "blade": {"matched": {}},  # No format
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "DE"
    assert result[0]["shaves"] == 1


def test_aggregate_razor_formats_no_razor_match():
    """Test handling when no razor match exists."""
    records = [
        {
            "author": "user1",
            "razor": {"original": "Unknown Razor", "matched": None},
            "blade": {"matched": {"format": "DE"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 0  # Should skip records with no razor match


def test_aggregate_razor_formats_avg_shaves_per_user():
    """Test average shaves per user calculation."""
    records = [
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "DE"
    assert result[0]["shaves"] == 5
    assert result[0]["unique_users"] == 2
    assert result[0]["avg_shaves_per_user"] == 2.5
    assert result[0]["median_shaves_per_user"] == 2.5  # Median of [3, 2] = 2.5


def test_aggregate_razor_formats_median_shaves_per_user():
    """Test median shaves per user calculation with odd number of users."""
    records = [
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
        {"author": "user3", "razor": {"matched": {"format": "DE"}}},
        {"author": "user3", "razor": {"matched": {"format": "DE"}}},
        {"author": "user3", "razor": {"matched": {"format": "DE"}}},
        {"author": "user3", "razor": {"matched": {"format": "DE"}}},
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "DE"
    assert result[0]["shaves"] == 8
    assert result[0]["unique_users"] == 3
    assert result[0]["avg_shaves_per_user"] == round(8 / 3, 1)
    # Median of [3, 1, 4] = 3.0
    assert result[0]["median_shaves_per_user"] == 3.0


def test_aggregate_razor_formats_avg_shaves_per_user_single_user():
    """Test average shaves per user with single user."""
    records = [
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "DE"
    assert result[0]["shaves"] == 3
    assert result[0]["unique_users"] == 1
    assert result[0]["avg_shaves_per_user"] == 3.0
    assert result[0]["median_shaves_per_user"] == 3.0


def test_aggregate_razor_formats_avg_shaves_per_user_multiple_formats():
    """Test average and median calculations across multiple formats."""
    records = [
        # Format 1: DE - user1 has 3 shaves, user2 has 2 shaves
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user1", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
        {"author": "user2", "razor": {"matched": {"format": "DE"}}},
        # Format 2: Straight - user3 has 1 shave
        {"author": "user3", "razor": {"matched": {"format": "Straight"}}},
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 2

    # Check DE format
    de_result = next(r for r in result if r["format"] == "DE")
    assert de_result["shaves"] == 5
    assert de_result["unique_users"] == 2
    assert de_result["avg_shaves_per_user"] == 2.5
    assert de_result["median_shaves_per_user"] == 2.5  # Median of [3, 2] = 2.5

    # Check Straight format
    straight_result = next(r for r in result if r["format"] == "Straight")
    assert straight_result["shaves"] == 1
    assert straight_result["unique_users"] == 1
    assert straight_result["avg_shaves_per_user"] == 1.0
    assert straight_result["median_shaves_per_user"] == 1.0


def test_aggregate_razor_formats_complex_scenario():
    """Test complex scenario with multiple format types - uses enriched format."""
    records = [
        # Regular DE razor
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "DE"},
                "enriched": {"format": "DE"},
            },
        },
        # Shavette with AC blade
        {
            "author": "user2",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (AC)"},
            },
            "blade": {"matched": {"format": "AC"}},
        },
        # Shavette with DE blade (should become Half DE)
        {
            "author": "user3",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (Half DE)"},
            },
            "blade": {"matched": {"format": "DE"}},
        },
        # Straight razor
        {
            "author": "user4",
            "razor": {
                "matched": {"format": "Straight"},
                "enriched": {"format": "Straight"},
            },
        },
        # Half DE razor
        {
            "author": "user5",
            "razor": {
                "matched": {"format": "Half DE"},
                "enriched": {"format": "Half DE"},
            },
            "blade": {"matched": {"format": "DE"}},
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 5

    # Check all expected formats are present
    formats = [r["format"] for r in result]
    assert "DE" in formats
    assert "Shavette (AC)" in formats
    assert "Shavette (Half DE)" in formats
    assert "Straight" in formats
    assert "Half DE" in formats


def test_aggregate_razor_formats_uses_enriched_when_available():
    """Test that aggregate uses enriched format when available."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "Shavette"},
                "enriched": {"format": "Shavette (AC)"},
            },
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "Shavette (AC)"


def test_aggregate_razor_formats_fallback_to_matched():
    """Test that aggregate falls back to matched format when no enriched format."""
    records = [
        {
            "author": "user1",
            "razor": {
                "matched": {"format": "DE"},
                # No enriched format
            },
        },
    ]
    result = aggregate_razor_formats(records)
    assert len(result) == 1
    assert result[0]["format"] == "DE"
