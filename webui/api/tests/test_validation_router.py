"""Tests for the validation router — agent output review endpoints."""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_data_dir(tmp_path):
    """Create a temporary data directory with verified/proposed subdirectories."""
    # verified/
    verified_dir = tmp_path / "verified"
    verified_dir.mkdir()
    verified_data = [
        {
            "field": "soap",
            "original": "mammoth tobacconist",
            "matched": {"brand": "House of Mammoth", "scent": "Tobacconist"},
            "verdict": "correct",
            "confidence": 0.95,
        },
        {
            "field": "razor",
            "original": "karve cb",
            "matched": {"brand": "Karve", "model": "Christopher Bradley"},
            "verdict": "incorrect",
            "confidence": 0.3,
        },
    ]
    (verified_dir / "2026-02.json").write_text(json.dumps(verified_data, indent=2))

    # proposed/
    proposed_dir = tmp_path / "proposed"
    proposed_dir.mkdir()
    proposed_data = [
        {
            "type": "new_scent",
            "field": "soap",
            "brand": "House of Mammoth",
            "model": "Cerulean",
            "suggested_pattern": "mammoth.*cerulean",
            "confidence": 0.9,
        },
        {
            "type": "new_pattern",
            "field": "razor",
            "brand": "Karve",
            "model": "Christopher Bradley",
            "suggested_pattern": "karve.*cb.*sb",
            "confidence": 0.85,
        },
    ]
    (proposed_dir / "2026-02.json").write_text(json.dumps(proposed_data, indent=2))

    # validation/ for rejections
    validation_dir = tmp_path / "validation"
    validation_dir.mkdir()

    # correct_matches/ for bulk-approve
    correct_matches_dir = tmp_path / "correct_matches"
    correct_matches_dir.mkdir()

    # Catalog files for CatalogUpdater
    import yaml

    soaps = {
        "House of Mammoth": {
            "patterns": ["(?:house of )?mammoth"],
            "scents": {
                "Tobacconist": {"patterns": ["mammoth.*tobacconist"]},
            },
        }
    }
    (tmp_path / "soaps.yaml").write_text(yaml.dump(soaps, default_flow_style=False))

    razors = {"Karve": {"Christopher Bradley": {"patterns": ["karve.*(?:christopher|cb)"]}}}
    (tmp_path / "razors.yaml").write_text(yaml.dump(razors, default_flow_style=False))

    blades = {
        "DE": {"Astra": {"Superior Platinum": {"patterns": ["astra.*(?:superior|sp|green)"]}}}
    }
    (tmp_path / "blades.yaml").write_text(yaml.dump(blades, default_flow_style=False))

    brushes = {
        "known_brushes": {
            "Chisel & Hound": {
                "V21 Fanchurian": {
                    "fiber": "Badger",
                    "knot_size_mm": 28,
                    "patterns": ["chisel.*hound.*v21.*fanchurian"],
                }
            }
        }
    }
    (tmp_path / "brushes.yaml").write_text(yaml.dump(brushes, default_flow_style=False))

    return tmp_path


@pytest.fixture
def client(tmp_data_dir):
    """Create a TestClient wired to the tmp data directory."""
    import webui.api.validation as validation_mod

    validation_mod.configure(tmp_data_dir)

    from webui.api.validation import router

    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/validation/verified/{month}
# ---------------------------------------------------------------------------
class TestGetVerified:
    def test_returns_data_for_existing_month(self, client):
        resp = client.get("/api/validation/verified/2026-02")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["field"] == "soap"
        assert data[0]["verdict"] == "correct"

    def test_returns_404_for_missing_month(self, client):
        resp = client.get("/api/validation/verified/2099-01")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/validation/proposed/{month}
# ---------------------------------------------------------------------------
class TestGetProposed:
    def test_returns_data_for_existing_month(self, client):
        resp = client.get("/api/validation/proposed/2026-02")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) == 2
        assert data[0]["type"] == "new_scent"
        assert data[0]["brand"] == "House of Mammoth"

    def test_returns_404_for_missing_month(self, client):
        resp = client.get("/api/validation/proposed/2099-01")
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"].lower()


# ---------------------------------------------------------------------------
# GET /api/validation/months
# ---------------------------------------------------------------------------
class TestGetMonths:
    def test_returns_list_of_validated_months(self, client):
        resp = client.get("/api/validation/months")
        assert resp.status_code == 200
        data = resp.json()
        assert "months" in data
        assert "2026-02" in data["months"]

    def test_includes_months_from_both_directories(self, client, tmp_data_dir):
        """A month that only exists in verified/ should still appear."""
        (tmp_data_dir / "verified" / "2025-12.json").write_text("[]")
        resp = client.get("/api/validation/months")
        months = resp.json()["months"]
        assert "2025-12" in months
        assert "2026-02" in months

    def test_deduplicates_months(self, client):
        """2026-02 exists in both verified/ and proposed/ but should appear once."""
        resp = client.get("/api/validation/months")
        months = resp.json()["months"]
        assert months.count("2026-02") == 1

    def test_months_sorted_descending(self, client, tmp_data_dir):
        """Most recent month first."""
        (tmp_data_dir / "proposed" / "2025-06.json").write_text("[]")
        resp = client.get("/api/validation/months")
        months = resp.json()["months"]
        assert months == sorted(months, reverse=True)


# ---------------------------------------------------------------------------
# POST /api/validation/accept-proposal
# ---------------------------------------------------------------------------
class TestAcceptProposal:
    def test_applies_proposal_to_catalog(self, client, tmp_data_dir):
        """Accepting a proposal should write to the catalog via CatalogUpdater."""
        import yaml

        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        # Verify catalog was updated
        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Cerulean" in catalog["House of Mammoth"]["scents"]

    def test_marks_proposal_as_accepted_in_file(self, client, tmp_data_dir):
        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        assert resp.status_code == 200

        proposed = json.loads((tmp_data_dir / "proposed" / "2026-02.json").read_text())
        assert proposed[0]["_status"] == "accepted"
        assert "_accepted_at" in proposed[0]

    def test_returns_404_for_missing_month(self, client):
        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2099-01", "proposal_index": 0},
        )
        assert resp.status_code == 404

    def test_returns_400_for_invalid_index(self, client):
        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 99},
        )
        assert resp.status_code == 400

    def test_uses_edited_proposal_when_provided(self, client, tmp_data_dir):
        """If the user edited the proposal before accepting, use the edited version."""
        import yaml

        edited = {
            "type": "new_scent",
            "field": "soap",
            "brand": "House of Mammoth",
            "model": "Cerulean (Edited)",
            "suggested_pattern": "mammoth.*cerulean.*edited",
            "confidence": 0.95,
        }
        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 0, "edited_proposal": edited},
        )
        assert resp.status_code == 200

        catalog = yaml.safe_load((tmp_data_dir / "soaps.yaml").read_text())
        assert "Cerulean (Edited)" in catalog["House of Mammoth"]["scents"]

    def test_rejects_already_accepted_proposal(self, client):
        """Cannot accept a proposal that is already accepted."""
        # Accept first
        client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        # Try again
        resp = client.post(
            "/api/validation/accept-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        assert resp.status_code == 409


# ---------------------------------------------------------------------------
# POST /api/validation/reject-proposal
# ---------------------------------------------------------------------------
class TestRejectProposal:
    def test_appends_to_rejections_file(self, client, tmp_data_dir):
        resp = client.post(
            "/api/validation/reject-proposal",
            json={
                "month": "2026-02",
                "proposal_index": 0,
                "reason": "Not a real product",
            },
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

        rejections_path = tmp_data_dir / "validation" / "rejections.json"
        rejections = json.loads(rejections_path.read_text())
        assert len(rejections) == 1
        assert rejections[0]["reason"] == "Not a real product"
        assert rejections[0]["month"] == "2026-02"

    def test_marks_proposal_as_rejected_in_file(self, client, tmp_data_dir):
        client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 1},
        )
        proposed = json.loads((tmp_data_dir / "proposed" / "2026-02.json").read_text())
        assert proposed[1]["_status"] == "rejected"
        assert "_rejected_at" in proposed[1]

    def test_returns_404_for_missing_month(self, client):
        resp = client.post(
            "/api/validation/reject-proposal",
            json={"month": "2099-01", "proposal_index": 0},
        )
        assert resp.status_code == 404

    def test_returns_400_for_invalid_index(self, client):
        resp = client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 99},
        )
        assert resp.status_code == 400

    def test_reason_is_optional(self, client, tmp_data_dir):
        resp = client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        assert resp.status_code == 200

        rejections_path = tmp_data_dir / "validation" / "rejections.json"
        rejections = json.loads(rejections_path.read_text())
        assert rejections[0].get("reason") is None

    def test_rejects_already_rejected_proposal(self, client):
        """Cannot reject a proposal that is already rejected."""
        client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        resp = client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 0},
        )
        assert resp.status_code == 409

    def test_appends_to_existing_rejections_file(self, client, tmp_data_dir):
        """Multiple rejections append to the same file."""
        client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 0, "reason": "first"},
        )
        client.post(
            "/api/validation/reject-proposal",
            json={"month": "2026-02", "proposal_index": 1, "reason": "second"},
        )
        rejections_path = tmp_data_dir / "validation" / "rejections.json"
        rejections = json.loads(rejections_path.read_text())
        assert len(rejections) == 2


# ---------------------------------------------------------------------------
# POST /api/validation/bulk-approve
# ---------------------------------------------------------------------------
class TestBulkApprove:
    def test_delegates_to_queue_manager(self, client, tmp_data_dir):
        """bulk-approve should call QueueManager.add_operation for correct_matches."""
        with patch("webui.api.validation.QueueManager") as MockQM:
            mock_instance = MagicMock()
            mock_instance.add_operation.return_value = "op_12345"
            MockQM.return_value = mock_instance

            matches = [
                {"original": "mammoth tobacconist", "matched": {"brand": "House of Mammoth"}},
            ]
            resp = client.post(
                "/api/validation/bulk-approve",
                json={"field": "soap", "matches": matches},
            )
            assert resp.status_code == 200
            result = resp.json()
            assert result["success"] is True
            assert result["operation_id"] == "op_12345"

            mock_instance.add_operation.assert_called_once_with("mark_correct", "soap", matches)

    def test_returns_400_for_empty_matches(self, client):
        resp = client.post(
            "/api/validation/bulk-approve",
            json={"field": "soap", "matches": []},
        )
        assert resp.status_code == 400

    def test_returns_400_for_invalid_field(self, client):
        resp = client.post(
            "/api/validation/bulk-approve",
            json={
                "field": "invalid_field",
                "matches": [{"original": "x", "matched": {}}],
            },
        )
        assert resp.status_code == 400
