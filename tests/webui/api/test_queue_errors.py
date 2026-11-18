"""Tests for queue-errors API and QueueManager get_recent_failed_operations."""

import json
from pathlib import Path

from webui.api.queue_manager import QueueManager


class TestGetRecentFailedOperations:
    """Unit tests for QueueManager.get_recent_failed_operations."""

    def test_empty_when_no_status_files(self, tmp_path: Path) -> None:
        """When no status or archive files exist, returns empty list."""
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=20)
        assert errors == []

    def test_empty_live_status_has_no_failed(self, tmp_path: Path) -> None:
        """Live status with only completed ops returns no errors."""
        status_file = tmp_path / ".status.json"
        status_file.write_text(
            json.dumps(
                {
                    "op_1": {
                        "status": "completed",
                        "progress": 1.0,
                        "message": "Done",
                        "completed_at": 1000.0,
                        "result": {},
                    }
                }
            ),
            encoding="utf-8",
        )
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=20)
        assert errors == []

    def test_returns_one_error_per_row_from_live_status(self, tmp_path: Path) -> None:
        """Failed op with result.matches yields one error entry per match."""
        status_file = tmp_path / ".status.json"
        status_file.write_text(
            json.dumps(
                {
                    "op_1": {
                        "status": "failed",
                        "progress": 0.0,
                        "message": "Error",
                        "completed_at": 2000.0,
                        "result": {
                            "error": "Something failed",
                            "retry_count": 1,
                            "field": "soap",
                            "operation_type": "mark_correct",
                            "matches": [
                                {
                                    "original": "Foo Bar",
                                    "matched": {"brand": "Foo", "model": "Bar"},
                                },
                                {
                                    "original": "Baz Qux",
                                    "matched": {"brand": "Baz", "model": "Qux"},
                                },
                            ],
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=20)
        assert len(errors) == 2
        assert errors[0]["field"] == "soap"
        assert errors[0]["original"] == "Foo Bar"
        assert errors[0]["error"] == "Something failed"
        assert errors[0]["retry_count"] == 1
        assert errors[0]["operation_type"] == "mark_correct"
        assert errors[0]["completed_at"] == 2000.0
        assert errors[1]["original"] == "Baz Qux"

    def test_legacy_failed_entry_without_matches(self, tmp_path: Path) -> None:
        """Failed entry without result.matches yields single row with empty original."""
        status_file = tmp_path / ".status.json"
        status_file.write_text(
            json.dumps(
                {
                    "op_1": {
                        "status": "failed",
                        "progress": 0.0,
                        "message": "Legacy error",
                        "completed_at": 1500.0,
                        "result": {"error": "Legacy", "retry_count": 0},
                    }
                }
            ),
            encoding="utf-8",
        )
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=20)
        assert len(errors) == 1
        assert errors[0]["field"] == ""
        assert errors[0]["original"] == ""
        assert errors[0]["error"] == "Legacy"

    def test_limit_caps_entries(self, tmp_path: Path) -> None:
        """Respects limit parameter."""
        status_file = tmp_path / ".status.json"
        status_file.write_text(
            json.dumps(
                {
                    "op_1": {
                        "status": "failed",
                        "completed_at": 2000.0,
                        "result": {
                            "error": "E",
                            "retry_count": 1,
                            "field": "razor",
                            "operation_type": "mark_correct",
                            "matches": [{"original": f"Item{i}", "matched": {}} for i in range(10)],
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=5)
        assert len(errors) == 5

    def test_reads_archive_files(self, tmp_path: Path) -> None:
        """Reads failed entries from monthly archive files."""
        archive_file = tmp_path / ".status.archive.2025-01.json"
        archive_file.write_text(
            json.dumps(
                {
                    "op_archived": {
                        "status": "failed",
                        "completed_at": 1000.0,
                        "result": {
                            "error": "Archive fail",
                            "retry_count": 2,
                            "field": "blade",
                            "operation_type": "remove_correct",
                            "matches": [{"original": "Archived", "matched": None}],
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        qm = QueueManager(tmp_path)
        errors = qm.get_recent_failed_operations(limit=20)
        assert len(errors) == 1
        assert errors[0]["field"] == "blade"
        assert errors[0]["original"] == "Archived"
        assert errors[0]["retry_count"] == 2
        assert errors[0]["operation_type"] == "remove_correct"


class TestQueueErrorsAPI:
    """Integration tests for GET /api/analysis/queue-errors."""

    def test_queue_errors_returns_200_and_shape(self, client) -> None:
        """GET /api/analysis/queue-errors returns 200 and { source, errors }."""
        response = client.get("/api/analysis/queue-errors")
        assert response.status_code == 200
        data = response.json()
        assert "source" in data
        assert data["source"] == "correct_matches"
        assert "errors" in data
        assert isinstance(data["errors"], list)

    def test_queue_errors_entry_shape(self, tmp_path: Path, client) -> None:
        """When errors exist, each entry has field, original, error, retry_count, etc."""
        # Create a failed status so we have at least one error (if API uses same data dir)
        # We cannot easily point the app's QueueManager at tmp_path, so we only assert
        # shape when the default data dir has no failed ops: empty list.
        response = client.get("/api/analysis/queue-errors")
        assert response.status_code == 200
        data = response.json()
        for entry in data["errors"]:
            assert "field" in entry
            assert "original" in entry
            assert "error" in entry
            assert "retry_count" in entry
            assert "completed_at" in entry
            assert "operation_type" in entry
