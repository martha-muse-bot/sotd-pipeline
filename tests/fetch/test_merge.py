from datetime import datetime, timezone

from sotd.fetch.merge import merge_records


def iso(ts: str) -> str:
    return datetime.fromisoformat(ts).replace(tzinfo=timezone.utc).isoformat()


def test_merge_records_latest_wins() -> None:
    old = [
        {"id": "a", "created_utc": iso("2025-05-01T00:00:00Z"), "x": 1},
        {"id": "b", "created_utc": iso("2025-05-02T00:00:00Z"), "x": 2},
    ]
    new = [
        {"id": "b", "created_utc": iso("2025-05-02T01:00:00Z"), "x": 3},
        {"id": "c", "created_utc": iso("2025-05-03T00:00:00Z"), "x": 4},
    ]
    merged = merge_records(old, new)

    assert [r["id"] for r in merged] == ["a", "b", "c"]
    assert next(r for r in merged if r["id"] == "b")["x"] == 3


def test_merge_records_equal_timestamp_new_wins() -> None:
    """Re-fetch of an edited record has the same created_utc: the new record must win."""
    old = [
        {"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "original body"},
    ]
    new = [
        {"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "edited body"},
    ]
    merged = merge_records(old, new)

    assert len(merged) == 1
    assert merged[0]["body"] == "edited body"


def test_merge_records_earlier_timestamp_new_loses() -> None:
    """A re-fetched record older than the stored one must not clobber it."""
    old = [
        {"id": "c1", "created_utc": iso("2025-05-02T00:00:00Z"), "body": "newer"},
    ]
    new = [
        {"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "older"},
    ]
    merged = merge_records(old, new)

    assert len(merged) == 1
    assert merged[0]["body"] == "newer"


def test_merge_records_malformed_timestamp_quarantined() -> None:
    """A malformed created_utc on a duplicate must not raise and must not win."""
    old = [
        {"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "good"},
    ]
    new = [
        {"id": "c1", "created_utc": "not-a-timestamp", "body": "bad"},
    ]
    merged = merge_records(old, new)

    assert len(merged) == 1
    assert merged[0]["body"] == "good"

    # ... while a valid re-fetch still replaces a malformed stored record.
    merged = merge_records(
        [{"id": "c1", "created_utc": "not-a-timestamp", "body": "bad"}],
        [{"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "good"}],
    )
    assert len(merged) == 1
    assert merged[0]["body"] == "good"

    # ... and a missing created_utc is quarantined, not fatal.
    merged = merge_records(
        [{"id": "c1", "created_utc": iso("2025-05-01T00:00:00Z"), "body": "good"}],
        [{"id": "c1", "body": "no-timestamp"}],
    )
    assert len(merged) == 1
    assert merged[0]["body"] == "good"
