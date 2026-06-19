# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Extended API tests for organization support."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from gh_stats import api as api_mod
from gh_stats.api import ApiError, AuthError


class TestGetOrgEvents:
    """Tests for get_org_events."""

    def test_fetches_org_events_paginated(self):
        """Should fetch events from org endpoint."""
        org_events = [
            {"id": "1", "type": "PushEvent", "repo": {"name": "org/repo1"}},
            {"id": "2", "type": "PullRequestEvent", "repo": {"name": "org/repo2"}},
        ]
        with patch("gh_stats.api._request", side_effect=[org_events, []]) as mock_req:
            result = api_mod.get_org_events("fake_token", "testorg", pages=2)
            assert len(result) == 2
            assert result[0]["id"] == "1"
            mock_req.assert_any_call(
                "fake_token",
                "GET",
                "https://api.github.com/orgs/testorg/events",
                params={"per_page": 100, "page": 1},
            )

    def test_returns_empty_list_on_404(self):
        """Should return empty list when org not found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            result = api_mod.get_org_events("fake_token", "nonexistentorg")
            assert result == []

    def test_raises_auth_error_on_401(self):
        """Should raise AuthError on invalid token."""
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with (
            patch("gh_stats.api._get_client", return_value=mock_client),
            pytest.raises(AuthError),
        ):
            api_mod.get_org_events("fake_token", "testorg")


class TestGetOrgRepos:
    """Tests for get_org_repos."""

    def test_fetches_org_repos_paginated(self):
        """Should fetch repos from org endpoint."""
        org_repos = [
            {"name": "repo1", "stargazers_count": 10, "forks_count": 2},
            {"name": "repo2", "stargazers_count": 5, "forks_count": 1},
        ]
        with patch("gh_stats.api._request", side_effect=[org_repos, []]) as mock_req:
            result = api_mod.get_org_repos("fake_token", "testorg", pages=2)
            assert len(result) == 2
            assert result[0]["name"] == "repo1"
            mock_req.assert_any_call(
                "fake_token",
                "GET",
                "https://api.github.com/orgs/testorg/repos",
                params={
                    "per_page": 100,
                    "page": 1,
                    "type": "all",
                    "sort": "updated",
                    "direction": "desc",
                },
            )

    def test_returns_empty_list_on_404(self):
        """Should return empty list when org not found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            result = api_mod.get_org_repos("fake_token", "nonexistentorg")
            assert result == []


class TestGetOrgMembers:
    """Tests for get_org_members."""

    def test_fetches_org_members(self):
        """Should fetch members from org endpoint."""
        members = [
            {"login": "user1", "id": 1},
            {"login": "user2", "id": 2},
        ]
        with patch("gh_stats.api._request", side_effect=[members, []]) as mock_req:
            result = api_mod.get_org_members("fake_token", "testorg", pages=2)
            assert len(result) == 2
            assert result[0]["login"] == "user1"
            mock_req.assert_any_call(
                "fake_token",
                "GET",
                "https://api.github.com/orgs/testorg/members",
                params={"per_page": 100, "page": 1},
            )

    def test_returns_empty_list_on_404(self):
        """Should return empty list when org not found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            result = api_mod.get_org_members("fake_token", "nonexistentorg")
            assert result == []


class TestGetOrgStats:
    """Tests for get_org_stats."""

    def test_fetches_org_profile(self):
        """Should fetch org profile from API."""
        org_data = {
            "login": "testorg",
            "name": "Test Organization",
            "description": "A test org",
            "public_repos": 42,
            "followers": 100,
            "following": 5,
            "created_at": "2020-01-01T00:00:00Z",
        }
        with patch("gh_stats.api._request", return_value=org_data):
            result = api_mod.get_org_stats("fake_token", "testorg")
            assert result["login"] == "testorg"
            assert result["public_repos"] == 42

    def test_returns_empty_on_404(self):
        """Should return empty dict when org not found."""
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            result = api_mod.get_org_stats("fake_token", "nonexistentorg")
            assert result == {}


class TestGetOrgContributions:
    """Tests for get_org_contributions."""

    def test_fetches_org_contributions_via_graphql(self):
        """Should fetch contributions using GraphQL."""
        mock_data = {
            "data": {
                "organization": {
                    "membersWithRepositories": {
                        "totalCount": 5,
                        "nodes": [
                            {
                                "login": "user1",
                                "contributionsCollection": {
                                    "contributionCalendar": {
                                        "totalContributions": 10,
                                        "weeks": [],
                                    }
                                },
                            },
                        ],
                    }
                }
            }
        }
        with patch("gh_stats.api._graphql", return_value=mock_data):
            result = api_mod.get_org_contributions("fake_token", "testorg", 2024)
            assert isinstance(result, dict)

    def test_returns_empty_on_graphql_error(self):
        """Should return empty dict on GraphQL error."""
        with patch("gh_stats.api._graphql", side_effect=ApiError("GraphQL error")):
            result = api_mod.get_org_contributions("fake_token", "testorg", 2024)
            assert result == {}


# Need to add the functions to api.py first - this test file documents expected behavior
# The actual implementation will be added in the next step
