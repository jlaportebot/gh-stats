# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for the API client module."""

import os
from unittest.mock import MagicMock, patch

import httpx
import pytest

import gh_stats.api as api_mod
from gh_stats.api import ApiError, AuthError, _close_client, get_token, get_user_stats


class TestGetToken:
    """Tests for get_token."""

    def test_gh_token_env_var(self):
        with patch.dict(
            os.environ, {"GH_TOKEN": "test_token_123", "GITHUB_TOKEN": ""}, clear=False
        ):
            token = get_token()
            assert token == "test_token_123"

    def test_github_token_env_var(self):
        with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": "gh_test_token"}, clear=False):
            token = get_token()
            assert token == "gh_test_token"

    def test_no_token_raises_auth_error(self):
        with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=False):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                with pytest.raises(AuthError, match="No GitHub token"):
                    get_token()

    def test_gh_cli_token(self):
        with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=False):
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "cli_token_xyz\n"
            with patch("subprocess.run", return_value=mock_result):
                token = get_token()
                assert token == "cli_token_xyz"

    def test_gh_cli_nonzero_exit_raises(self):
        with patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=False):
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            with patch("subprocess.run", return_value=mock_result):
                with pytest.raises(AuthError):
                    get_token()


class TestGetUserStats:
    """Tests for get_user_stats with authenticated_user reuse."""

    def test_reuses_authenticated_user_when_matching(self):
        """When username matches the authenticated user, should NOT make another API call."""
        auth_user = {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.png",
            "bio": "Hello",
            "public_repos": 5,
            "public_gists": 1,
            "followers": 10,
            "following": 3,
            "created_at": "2020-01-01T00:00:00Z",
        }
        # Patch out get_authenticated_user to prove it's NOT called
        with patch("gh_stats.api.get_authenticated_user") as mock_auth:
            result = get_user_stats("fake_token", "testuser", authenticated_user=auth_user)
            mock_auth.assert_not_called()
            assert result["login"] == "testuser"
            assert result["public_repos"] == 5

    def test_fetches_other_user(self):
        """When username differs, should call _request for the other user."""
        auth_user = {"login": "me", "name": "Me"}
        other_user_data = {
            "login": "other",
            "name": "Other",
            "avatar_url": "",
            "bio": "",
            "public_repos": 1,
            "public_gists": 0,
            "followers": 0,
            "following": 0,
            "created_at": "",
        }
        with patch("gh_stats.api._request", return_value=other_user_data) as mock_req:
            result = get_user_stats("fake_token", "other", authenticated_user=auth_user)
            mock_req.assert_called_once()
            assert result["login"] == "other"


class TestNetworkErrors:
    """Tests for network error handling in _request and _graphql."""

    def test_request_timeout_raises_api_error(self):
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.TimeoutException("timeout")
        with patch("gh_stats.api._get_client", return_value=mock_client):
            with pytest.raises(ApiError, match="timed out"):
                api_mod._request("tok", "GET", "https://api.github.com/test")

    def test_request_connect_error_raises_api_error(self):
        mock_client = MagicMock()
        mock_client.request.side_effect = httpx.ConnectError("connection refused")
        with patch("gh_stats.api._get_client", return_value=mock_client):
            with pytest.raises(ApiError, match="Cannot connect"):
                api_mod._request("tok", "GET", "https://api.github.com/test")

    def test_request_401_raises_auth_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            with pytest.raises(AuthError, match="invalid or expired"):
                api_mod._request("tok", "GET", "https://api.github.com/test")

    def test_request_403_raises_api_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_client = MagicMock()
        mock_client.request.return_value = mock_resp
        with patch("gh_stats.api._get_client", return_value=mock_client):
            with pytest.raises(ApiError, match="Rate limited"):
                api_mod._request("tok", "GET", "https://api.github.com/test")

    def test_graphql_timeout_raises_api_error(self):
        mock_client = MagicMock()
        mock_client.post.side_effect = httpx.TimeoutException("timeout")
        with patch("gh_stats.api._get_client", return_value=mock_client):
            with pytest.raises(ApiError, match="GraphQL request timed out"):
                api_mod._graphql("tok", "query { }")


class TestCloseClient:
    """Tests for _close_client."""

    def test_close_client_resets_global(self):
        mock = MagicMock()
        api_mod._client = mock
        _close_client()
        mock.close.assert_called_once()
        assert api_mod._client is None

    def test_close_client_noop_when_none(self):
        api_mod._client = None
        _close_client()  # should not raise
        assert api_mod._client is None
