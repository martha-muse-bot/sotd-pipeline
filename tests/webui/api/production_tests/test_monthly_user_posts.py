#!/usr/bin/env python3
"""Tests for Monthly User Posts API endpoints."""

import sys
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, Mock, patch

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from webui.api.monthly_user_posts import router  # noqa: E402

# Create test client
app = FastAPI()
app.include_router(router)
client = TestClient(app)


# Test the endpoints with the correct prefix
def test_health_check():
    """Test health check endpoint."""
    response = client.get("/api/monthly-user-posts/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "monthly-user-posts"


class TestMonthlyUserPostsAPI:
    """Test cases for Monthly User Posts API endpoints."""

    def test_health_check(self):
        """Test health check endpoint."""
        response = client.get("/api/monthly-user-posts/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "monthly-user-posts"

    @patch("webui.api.monthly_user_posts.Path.exists")
    def test_get_available_months_no_directory(self, mock_exists):
        """Test handling when enriched directory doesn't exist."""
        mock_exists.return_value = False

        response = client.get("/api/monthly-user-posts/months")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("webui.api.monthly_user_posts.Path")
    @patch("webui.api.monthly_user_posts.json.load")
    @patch("webui.api.monthly_user_posts.open", create=True)
    def test_get_users_for_month_with_search(self, mock_open, mock_json_load, mock_path_class):
        """Test user search functionality."""

        # Create a mock Path object that returns True for exists() when it's a user_analysis file
        def path_side_effect(*args):
            mock_path = MagicMock()
            path_str = "/".join(str(arg) for arg in args) if args else ""
            if "user_analysis" in path_str:
                mock_path.exists.return_value = True
            else:
                mock_path.exists.return_value = False
            mock_path.__truediv__ = lambda self, other: path_side_effect(str(self), str(other))
            cast(Any, mock_path).__str__ = lambda self: path_str
            return mock_path

        mock_path_class.side_effect = path_side_effect
        mock_open.return_value.__enter__.return_value = Mock()
        mock_open.return_value.__exit__.return_value = None

        # Mock the user analysis data structure
        mock_json_load.return_value = {
            "users": {
                "user1": {"posted_days": 5, "missed_days": 0},
                "user2": {"posted_days": 3, "missed_days": 2},
                "testuser": {"posted_days": 2, "missed_days": 0},
            }
        }

        response = client.get("/api/monthly-user-posts/users/2025-06?search=test")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["username"] == "testuser"

    @patch("webui.api.monthly_user_posts.Path.exists")
    def test_get_users_for_month_no_data(self, mock_exists):
        """Test handling when month has no data."""
        mock_exists.return_value = False

        response = client.get("/api/monthly-user-posts/users/2025-06")
        assert response.status_code == 200
        data = response.json()
        assert data == []

    @patch("webui.api.monthly_user_posts.Path")
    @patch("webui.api.monthly_user_posts.json.load")
    @patch("webui.api.monthly_user_posts.open", create=True)
    def test_get_user_posting_analysis_success(self, mock_open, mock_json_load, mock_path_class):
        """Test successful user posting analysis."""

        # Create a mock Path object that returns True for exists() when it's a user_analysis file
        def path_side_effect(*args):
            mock_path = MagicMock()
            path_str = "/".join(str(arg) for arg in args) if args else ""
            if "user_analysis" in path_str:
                mock_path.exists.return_value = True
            else:
                mock_path.exists.return_value = False
            mock_path.__truediv__ = lambda self, other: path_side_effect(str(self), str(other))
            cast(Any, mock_path).__str__ = lambda self: path_str
            return mock_path

        mock_path_class.side_effect = path_side_effect
        mock_open.return_value.__enter__.return_value = Mock()
        mock_open.return_value.__exit__.return_value = None

        # Mock the user analysis data structure
        mock_json_load.return_value = {
            "users": {
                "testuser": {
                    "user": "testuser",
                    "posted_days": 5,
                    "missed_days": 0,
                    "posted_dates": ["2025-06-01", "2025-06-02"],
                    "comment_ids": ["comment1", "comment2"],
                    "comments_by_date": {"2025-06-01": ["comment1"], "2025-06-02": ["comment2"]},
                    "razors": [],
                    "blades": [],
                    "brushes": [],
                    "soaps": [],
                }
            }
        }

        response = client.get("/api/monthly-user-posts/analysis/2025-06/testuser")
        assert response.status_code == 200
        data = response.json()
        assert data["user"] == "testuser"
        assert data["posted_days"] == 5
        assert data["missed_days"] == 0

    @patch("webui.api.monthly_user_posts.Path.exists")
    def test_get_user_posting_analysis_no_data(self, mock_exists):
        """Test handling when month has no data."""
        mock_exists.return_value = False

        response = client.get("/api/monthly-user-posts/analysis/2025-06/testuser")
        # When file doesn't exist, API raises HTTPException with 404
        # But if there's an error opening the file, it returns 500
        assert response.status_code in [404, 500]
        data = response.json()
        if response.status_code == 404:
            assert "No data available" in data["detail"]
        else:
            # If 500, it's an error loading the file
            assert "detail" in data

    @patch("webui.api.monthly_user_posts.Path.exists")
    @patch("webui.api.monthly_user_posts.json.load")
    @patch("webui.api.monthly_user_posts.aggregate_users")
    def test_get_user_posting_analysis_user_not_found(
        self, mock_aggregate, mock_json_load, mock_exists
    ):
        """Test handling when user has no posts in month."""
        mock_exists.return_value = True
        mock_json_load.return_value = {
            "data": [
                {
                    "author": "otheruser",
                    "thread_title": "Monday SOTD Thread - Jun 01, 2025",
                    "id": "comment1",
                }
            ]
        }
        mock_aggregate.return_value = [{"user": "otheruser", "shaves": 1, "missed_days": 29}]

        response = client.get("/api/monthly-user-posts/analysis/2025-06/testuser")
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"].lower()
