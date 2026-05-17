"""Tests for the API client module."""

import os
from unittest.mock import MagicMock, patch

import pytest

from gh_stats.api import AuthError, get_token


class TestGetToken:
    """Tests for get_token."""

    def test_gh_token_env_var(self):
        with patch.dict(os.environ, {"GH_TOKEN": "test_token_123"}, clear=False):
            # Clear GITHUB_TOKEN too to avoid interference
            with patch.dict(os.environ, {"GITHUB_TOKEN": ""}, clear=False):
                token = get_token()
                assert token == "test_token_123"

    def test_github_token_env_var(self):
        env = {"GH_TOKEN": "", "GITHUB_TOKEN": "gh_test_token"}
        with patch.dict(os.environ, env, clear=False):
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
