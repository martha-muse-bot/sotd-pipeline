"""Tests for error handling across the fetch pipeline."""

import os
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from sotd.fetch.reddit import get_reddit, safe_call
from sotd.fetch.save import load_month_file, write_month_file


# --------------------------------------------------------------------------- #
# Reddit API Error Handling                                                   #
# --------------------------------------------------------------------------- #
def test_reddit_connection_timeout():
    """Test handling of network timeouts during Reddit API calls."""
    with patch("praw.Reddit") as mock_reddit:
        mock_reddit.side_effect = ConnectionError("Network timeout")

        with pytest.raises(ConnectionError, match="Network timeout"):
            get_reddit()


def test_reddit_authentication_failure():
    """Test handling of Reddit authentication failures."""
    with patch("praw.Reddit") as mock_reddit:
        mock_reddit.side_effect = Exception("Invalid credentials")

        with pytest.raises(Exception, match="Invalid credentials"):
            get_reddit()


def test_safe_call_network_error():
    """Test that safe_call returns None on non-rate-limit network errors."""

    def failing_function():
        raise ConnectionError("Network unreachable")

    result = safe_call(failing_function)
    assert result is None


def test_safe_call_reddit_server_error():
    """Test that safe_call returns None on Reddit server errors."""

    def failing_function():
        raise RuntimeError("Reddit is down")

    result = safe_call(failing_function)
    assert result is None


# --------------------------------------------------------------------------- #
# File System Error Handling                                                  #
# --------------------------------------------------------------------------- #
def test_load_month_file_permission_denied(tmp_path):
    """Test handling of permission errors when loading files."""
    file_path = tmp_path / "restricted.json"
    file_path.write_text('{"meta": {}, "data": []}')

    # Make file unreadable (permission denied)
    os.chmod(file_path, 0o000)

    try:
        with pytest.raises(PermissionError):
            load_month_file(file_path)
    finally:
        # Restore permissions for cleanup
        os.chmod(file_path, 0o644)


def test_load_month_file_corrupted_json(tmp_path):
    """Test handling of corrupted JSON files."""
    file_path = tmp_path / "corrupted.json"
    file_path.write_text("invalid json content {")

    result = load_month_file(file_path)
    assert result is None


def test_load_month_file_empty_file(tmp_path):
    """Test handling of empty files."""
    file_path = tmp_path / "empty.json"
    file_path.touch()  # Create empty file

    result = load_month_file(file_path)
    assert result is None


def test_write_month_file_permission_denied(tmp_path):
    """Test handling of permission errors when writing files."""
    # Create directory without write permissions
    restricted_dir = tmp_path / "restricted"
    restricted_dir.mkdir()
    os.chmod(restricted_dir, 0o555)  # Read and execute only

    file_path = restricted_dir / "test.json"

    try:
        with pytest.raises(PermissionError):
            write_month_file(file_path, {"test": "meta"}, [])
    finally:
        # Restore permissions for cleanup
        os.chmod(restricted_dir, 0o755)


def test_write_month_file_disk_full_simulation(tmp_path):
    """Test handling of disk full scenarios."""
    file_path = tmp_path / "test.json"

    # Mock Path.open to raise OSError (disk full) - this is what save_json_data actually uses
    with patch.object(Path, "open", side_effect=OSError("No space left on device")):
        with pytest.raises(OSError, match="No space left on device"):
            write_month_file(file_path, {"test": "meta"}, [])


def test_write_month_file_directory_creation_error(tmp_path):
    """Test handling of directory creation failures."""
    # Try to write to a path where parent directory creation would fail
    file_path = tmp_path / "nonexistent" / "deep" / "path" / "test.json"

    # Mock mkdir to fail
    with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
        with pytest.raises(OSError, match="Permission denied"):
            write_month_file(file_path, {"test": "meta"}, [])


# --------------------------------------------------------------------------- #
# Memory and Resource Error Handling                                          #
# --------------------------------------------------------------------------- #
def test_large_dataset_memory_handling(tmp_path):
    """Test handling of very large datasets that might cause memory issues."""
    # Create a large dataset (simulate memory pressure)
    large_meta = {"month": "2025-05", "count": 100000}
    large_data = [{"id": f"comment_{i}", "body": "x" * 1000} for i in range(1000)]

    file_path = tmp_path / "large.json"

    # This should complete without memory errors
    write_month_file(file_path, large_meta, large_data)

    # Verify it can be read back
    result = load_month_file(file_path)
    if result is not None:
        assert result[0]["count"] == 100000
        assert len(result[1]) == 1000
    else:
        assert False, "Expected result to be a list, got None"


def test_unicode_handling_in_files(tmp_path):
    """Test handling of Unicode content in JSON files."""
    meta = {"month": "2025-05", "note": "测试 émojis 🧔‍♂️"}
    data = [
        {"id": "1", "body": "Shaved with 日本 razor"},
        {"id": "2", "body": "Great shave! 🪒✨"},
        {"id": "3", "body": "Здравствуйте from Russia"},
    ]

    file_path = tmp_path / "unicode.json"

    # Should handle Unicode without errors
    write_month_file(file_path, meta, data)

    result = load_month_file(file_path)
    if result is not None:
        assert "测试" in result[0]["note"]
        assert "🧔‍♂️" in result[0]["note"]
        assert "日本" in result[1][0]["body"]
        assert "🪒✨" in result[1][1]["body"]
        assert "Здравствуйте" in result[1][2]["body"]
    else:
        assert False, "Expected result to be a list, got None"


# --------------------------------------------------------------------------- #
# Concurrent Access Error Handling                                            #
# --------------------------------------------------------------------------- #
def test_concurrent_file_access(tmp_path):
    """Test handling of concurrent file access scenarios."""
    file_path = tmp_path / "concurrent.json"

    # Write initial file
    write_month_file(file_path, {"version": 1}, [{"id": "1"}])

    # Simulate concurrent modification by changing file between load and write
    def modify_file_during_operation():
        # This would happen if another process modifies the file
        write_month_file(file_path, {"version": 2}, [{"id": "2"}])
        return {"version": 1}, [{"id": "1"}]

    # The system should handle this gracefully (last write wins)
    with patch("sotd.fetch.save.load_month_file", side_effect=modify_file_during_operation):
        write_month_file(file_path, {"version": 3}, [{"id": "3"}])

    # Verify final state
    result = load_month_file(file_path)
    if result is not None:
        assert result[0]["version"] == 3
        assert result[1][0]["id"] == "3"
    else:
        assert False, "Expected result to be a list, got None"


def mock_open_with_content(content):
    """Helper function to create a mock open that returns specific content."""
    return mock_open(read_data=content)


# --------------------------------------------------------------------------- #
# Integration Error Scenarios                                                 #
# --------------------------------------------------------------------------- #
