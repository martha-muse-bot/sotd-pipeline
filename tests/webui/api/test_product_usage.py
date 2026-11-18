#!/usr/bin/env python3
"""Tests for Product Usage API endpoints."""

import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from webui.api.product_usage import router  # noqa: E402

# Create test client
app = FastAPI()
app.include_router(router)
client = TestClient(app)


class TestProductUsageAPI:
    """Test cases for Product Usage API endpoints."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/product-usage/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "product-usage"

    def test_get_products_invalid_product_type(self):
        """Test handling of invalid product type."""
        response = client.get("/api/product-usage/products/2025-06/invalid")
        assert response.status_code == 400
        assert "Invalid product type" in response.json()["detail"]

    @patch("webui.api.product_usage.Path.exists")
    def test_get_products_for_month_no_data(self, mock_exists):
        """Test handling when month has no data."""
        mock_exists.return_value = False

        response = client.get("/api/product-usage/products/2025-06/razor")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("webui.api.product_usage.Path.open")
    def test_get_products_for_month_razor(self, mock_open):
        """Test getting products for razor type."""
        # Patch Path.exists directly on the class
        original_exists = Path.exists

        def exists_side_effect(self):
            # product_usage_file path should not exist
            if "product_usage" in str(self):
                return False
            # enriched_file path should exist
            if "enriched" in str(self):
                return True
            return original_exists(self)

        Path.exists = exists_side_effect

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
                {
                    "author": "user2",
                    "id": "2",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
                {
                    "author": "user1",
                    "id": "3",
                    "razor": {
                        "matched": {"brand": "Merkur", "model": "34C"},
                    },
                },
            ]
        }

        try:
            with patch("webui.api.product_usage.json.load", return_value=enriched_data):
                response = client.get("/api/product-usage/products/2025-06/razor")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 2
                # Should be sorted by usage count
                assert data[0]["brand"] == "Gillette"
                assert data[0]["model"] == "Tech"
                assert data[0]["usage_count"] == 2
                assert data[0]["unique_users"] == 2
        finally:
            # Restore original exists method
            Path.exists = original_exists

    @patch("webui.api.product_usage.Path.open")
    def test_get_products_for_month_with_search(self, mock_open):
        """Test product search functionality."""
        # Patch Path.exists directly on the class
        original_exists = Path.exists

        def exists_side_effect(self):
            if "product_usage" in str(self):
                return False
            if "enriched" in str(self):
                return True
            return original_exists(self)

        Path.exists = exists_side_effect

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
                {
                    "author": "user2",
                    "id": "2",
                    "razor": {
                        "matched": {"brand": "Merkur", "model": "34C"},
                    },
                },
            ]
        }

        try:
            with patch("webui.api.product_usage.json.load", return_value=enriched_data):
                response = client.get("/api/product-usage/products/2025-06/razor?search=Gillette")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["brand"] == "Gillette"
        finally:
            Path.exists = original_exists

    @patch("webui.api.product_usage.Path.open")
    def test_get_products_for_month_soap(self, mock_open):
        """Test getting products for soap type."""
        # Patch Path.exists directly on the class
        original_exists = Path.exists

        def exists_side_effect(self):
            if "product_usage" in str(self):
                return False
            if "enriched" in str(self):
                return True
            return original_exists(self)

        Path.exists = exists_side_effect

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "soap": {
                        "matched": {"brand": "Grooming Dept", "scent": "Laundry II"},
                    },
                },
            ]
        }

        try:
            with patch("webui.api.product_usage.json.load", return_value=enriched_data):
                response = client.get("/api/product-usage/products/2025-06/soap")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["brand"] == "Grooming Dept"
                assert data[0]["model"] == "Laundry II"
        finally:
            Path.exists = original_exists

    @patch("webui.api.product_usage.Path.open")
    def test_get_product_usage_analysis_success(self, mock_open):
        """Test successful product usage analysis."""
        # Patch Path.exists directly on the class
        original_exists = Path.exists

        def exists_side_effect(self):
            if "product_usage" in str(self):
                return False
            if "enriched" in str(self):
                return True
            return original_exists(self)

        Path.exists = exists_side_effect

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "thread_title": "Monday SOTD Thread - Jun 01, 2025",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
                {
                    "author": "user2",
                    "id": "2",
                    "thread_title": "Monday SOTD Thread - Jun 01, 2025",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
                {
                    "author": "user1",
                    "id": "3",
                    "thread_title": "Tuesday SOTD Thread - Jun 02, 2025",
                    "razor": {
                        "matched": {"brand": "Gillette", "model": "Tech"},
                    },
                },
            ]
        }

        try:
            with patch("webui.api.product_usage.json.load", return_value=enriched_data):
                # Patch where date extraction is used (product_usage_aggregator imports it)
                with patch(
                    "sotd.aggregate.aggregators.product_usage.product_usage_aggregator._extract_date_from_thread_title"
                ) as mock_extract:
                    # Mock date extraction
                    from datetime import datetime

                    def extract_date(title):
                        if "Jun 01" in title:
                            return datetime(2025, 6, 1)
                        elif "Jun 02" in title:
                            return datetime(2025, 6, 2)
                        return datetime(2025, 6, 1)

                    mock_extract.side_effect = extract_date

                    response = client.get("/api/product-usage/analysis/2025-06/razor/Gillette/Tech")
                    assert response.status_code == 200
                    data = response.json()
                    assert data["product"]["brand"] == "Gillette"
                    assert data["product"]["model"] == "Tech"
                    assert data["total_usage"] == 3
                    assert data["unique_users"] == 2
                    assert len(data["users"]) == 2
                    # user1 should have higher usage count
                    assert data["users"][0]["username"] == "user1"
                    assert data["users"][0]["usage_count"] == 2
        finally:
            Path.exists = original_exists

    @patch("webui.api.product_usage.Path.exists")
    def test_get_product_usage_analysis_no_data(self, mock_exists):
        """Test handling when month has no data."""
        mock_exists.return_value = False

        response = client.get("/api/product-usage/analysis/2025-06/razor/Gillette/Tech")
        assert response.status_code == 404

    @patch("webui.api.product_usage.Path.exists")
    @patch("webui.api.product_usage.Path.open")
    def test_get_product_usage_analysis_product_not_found(self, mock_open, mock_exists):
        """Test handling when product is not found."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "razor": {
                        "matched": {"brand": "Merkur", "model": "34C"},
                    },
                },
            ]
        }

        with patch("webui.api.product_usage.json.load", return_value=enriched_data):
            response = client.get("/api/product-usage/analysis/2025-06/razor/Gillette/Tech")
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    @patch("webui.api.product_usage.Path.open")
    def test_get_products_for_month_brush(self, mock_open):
        """Test getting products for brush type."""
        # Patch Path.exists directly on the class
        original_exists = Path.exists

        def exists_side_effect(self):
            if "product_usage" in str(self):
                return False
            if "enriched" in str(self):
                return True
            return original_exists(self)

        Path.exists = exists_side_effect

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_file.read.return_value = ""
        mock_open.return_value = mock_file

        enriched_data = {
            "data": [
                {
                    "author": "user1",
                    "id": "1",
                    "brush": {
                        "matched": {
                            "brand": "Semogue",
                            "model": "610",
                            "handle": {"brand": "Semogue", "model": "610"},
                            "knot": {"brand": "Semogue", "model": "610", "fiber": "Boar"},
                        },
                    },
                },
            ]
        }

        try:
            with patch("webui.api.product_usage.json.load", return_value=enriched_data):
                response = client.get("/api/product-usage/products/2025-06/brush")
                assert response.status_code == 200
                data = response.json()
                assert len(data) == 1
                assert data[0]["brand"] == "Semogue"
                assert data[0]["model"] == "610"
        finally:
            Path.exists = original_exists

    @patch("webui.api.product_usage.Path.exists")
    @patch("webui.api.product_usage.Path.open")
    def test_get_product_yearly_summary_success(self, mock_open, mock_exists):
        """Test successful yearly summary retrieval."""
        # Mock Path.exists to return True for all months
        mock_exists.return_value = True

        # Mock aggregated data
        aggregated_data = {
            "data": {
                "razors": [
                    {"rank": 1, "name": "Gillette Tech", "shaves": 55, "unique_users": 6},
                ]
            }
        }

        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_open.return_value = mock_file

        with patch("webui.api.product_usage.json.load", return_value=aggregated_data):
            response = client.get("/api/product-usage/yearly-summary/2025-11/razor/Gillette/Tech")
            assert response.status_code == 200
            data = response.json()
            assert data["product"]["brand"] == "Gillette"
            assert data["product"]["model"] == "Tech"
            assert len(data["months"]) == 12
            # Check that months are in chronological order
            months = [m["month"] for m in data["months"]]
            assert months == sorted(months)
            # Check that at least one month has data
            months_with_data = [m for m in data["months"] if m["has_data"]]
            assert len(months_with_data) > 0

    @patch("webui.api.product_usage.Path.exists")
    def test_get_product_yearly_summary_missing_months(self, mock_exists):
        """Test yearly summary with missing months."""
        # Return False for all months (no aggregated files)
        mock_exists.return_value = False

        response = client.get("/api/product-usage/yearly-summary/2025-11/razor/Gillette/Tech")
        assert response.status_code == 200
        data = response.json()
        assert len(data["months"]) == 12
        # All months should have has_data: false
        for month_data in data["months"]:
            assert month_data["has_data"] is False
            assert month_data["shaves"] == 0
            assert month_data["unique_users"] == 0
            assert month_data["rank"] is None

    @patch("webui.api.product_usage.Path.exists")
    @patch("webui.api.product_usage.Path.open")
    def test_get_product_yearly_summary_product_not_found(self, mock_open, mock_exists):
        """Test yearly summary when product is not found in some months."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_open.return_value = mock_file

        # Mock aggregated data without the product
        aggregated_data = {
            "data": {
                "razors": [
                    {"rank": 1, "name": "Other Razor", "shaves": 10, "unique_users": 5},
                ]
            }
        }

        with patch("webui.api.product_usage.json.load", return_value=aggregated_data):
            response = client.get("/api/product-usage/yearly-summary/2025-11/razor/Gillette/Tech")
            assert response.status_code == 200
            data = response.json()
            assert len(data["months"]) == 12
            # All months should have has_data: false (product not found)
            for month_data in data["months"]:
                assert month_data["has_data"] is False
                assert month_data["rank"] is None

    def test_get_product_yearly_summary_invalid_month_format(self):
        """Test yearly summary with invalid month format."""
        response = client.get("/api/product-usage/yearly-summary/invalid/razor/Gillette/Tech")
        assert response.status_code == 400
        assert "Invalid month format" in response.json()["detail"]

    @patch("webui.api.product_usage.Path.exists")
    @patch("webui.api.product_usage.Path.open")
    def test_get_product_yearly_summary_soap_format(self, mock_open, mock_exists):
        """Test yearly summary for soap with correct name format."""
        mock_exists.return_value = True
        mock_file = Mock()
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=False)
        mock_open.return_value = mock_file

        aggregated_data = {
            "data": {
                "soaps": [
                    {
                        "rank": 1,
                        "name": "Grooming Dept - After The Fire",
                        "shaves": 10,
                        "unique_users": 5,
                    },
                ]
            }
        }

        with patch("webui.api.product_usage.json.load", return_value=aggregated_data):
            response = client.get(
                "/api/product-usage/yearly-summary/2025-11/soap/Grooming%20Dept/After%20The%20Fire"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["product"]["type"] == "soap"
            assert data["product"]["brand"] == "Grooming Dept"
            assert data["product"]["model"] == "After The Fire"
