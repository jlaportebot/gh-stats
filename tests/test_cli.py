# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for the CLI module."""

import os
from unittest.mock import patch

from click.testing import CliRunner

from gh_stats.api import ApiError, AuthError
from gh_stats.cli import main


class TestCLIVersion:
    """Tests for the --version flag."""

    def test_version_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestCLIHelp:
    """Tests for the --help flag."""

    def test_help_flag(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "GitHub" in result.output or "github" in result.output.lower()

    def test_help_shows_user_option(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "--user" in result.output


class TestCLINoToken:
    """Tests for CLI when no token is available."""

    def test_no_token_exits_with_error(self):
        runner = CliRunner()
        with (
            patch.dict(os.environ, {"GH_TOKEN": "", "GITHUB_TOKEN": ""}, clear=False),
            patch("subprocess.run", side_effect=FileNotFoundError),
        ):
            result = runner.invoke(main, ["--user", "testuser"])
            assert result.exit_code != 0


class TestCLIWithToken:
    """Tests for CLI with a valid token (mocked API calls)."""

    def test_successful_run_with_user(self):
        """Happy-path run with explicit --user."""
        mock_user = {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.png",
            "bio": "A developer",
            "public_repos": 5,
            "public_gists": 1,
            "followers": 10,
            "following": 3,
            "created_at": "2020-01-01T00:00:00Z",
        }
        mock_events = [
            {
                "id": "1",
                "type": "PushEvent",
                "repo": {"name": "testuser/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}]},
            }
        ]
        mock_repos = [
            {
                "full_name": "testuser/repo",
                "stargazers_count": 10,
                "forks_count": 2,
                "language": "Python",
                "description": "A repo",
                "fork": False,
            }
        ]

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_user_stats", return_value=mock_user),
            patch("gh_stats.cli.get_user_events", return_value=mock_events),
            patch("gh_stats.cli.get_user_repos", return_value=mock_repos),
            patch("gh_stats.cli.get_contributions", return_value={"2026-01-15": 5}),
        ):
            runner = CliRunner()
            result = runner.invoke(main, ["--user", "testuser"])
            assert result.exit_code == 0

    def test_successful_run_without_user(self):
        """Happy-path run without --user (uses authenticated user)."""
        mock_user = {
            "login": "authuser",
            "name": "Auth User",
            "avatar_url": "https://example.com/avatar.png",
            "bio": "A developer",
            "public_repos": 5,
            "public_gists": 1,
            "followers": 10,
            "following": 3,
            "created_at": "2020-01-01T00:00:00Z",
        }

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.api.get_authenticated_user", return_value=mock_user),
            patch("gh_stats.cli.get_user_stats", return_value=mock_user),
            patch("gh_stats.cli.get_user_events", return_value=[]),
            patch("gh_stats.cli.get_user_repos", return_value=[]),
            patch("gh_stats.cli.get_contributions", return_value={}),
        ):
            runner = CliRunner()
            result = runner.invoke(main, [])
            assert result.exit_code == 0

    def test_authenticated_user_reuse(self):
        """When no --user given, get_user_stats should receive authenticated_user kwarg."""
        mock_user = {
            "login": "authuser",
            "name": "Auth User",
            "avatar_url": "",
            "bio": "",
            "public_repos": 1,
            "public_gists": 0,
            "followers": 0,
            "following": 0,
            "created_at": "",
        }

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.api.get_authenticated_user", return_value=mock_user),
            patch("gh_stats.cli.get_user_stats", return_value=mock_user) as mock_stats,
            patch("gh_stats.cli.get_user_events", return_value=[]),
            patch("gh_stats.cli.get_user_repos", return_value=[]),
            patch("gh_stats.cli.get_contributions", return_value={}),
        ):
            runner = CliRunner()
            result = runner.invoke(main, [])
            assert result.exit_code == 0
            # Verify authenticated_user was passed to avoid double API call
            assert mock_stats.call_count == 1
            call_kwargs = mock_stats.call_args.kwargs
            assert call_kwargs.get("authenticated_user") is not None

    def test_auth_error_exits(self):
        """AuthError should exit non-zero."""
        with patch("gh_stats.cli.get_token", side_effect=AuthError("no token")):
            runner = CliRunner()
            result = runner.invoke(main, ["--user", "testuser"])
            assert result.exit_code != 0

    def test_api_error_exits(self):
        """ApiError should exit non-zero."""
        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_user_stats", side_effect=ApiError("API down")),
        ):
            runner = CliRunner()
            result = runner.invoke(main, ["--user", "testuser"])
            assert result.exit_code != 0


class TestCLIOrg:
    """Tests for CLI with --org flag."""

    def test_successful_run_with_org(self):
        """Happy-path run with --org."""
        mock_org = {
            "login": "testorg",
            "name": "Test Org",
            "description": "An org",
            "avatar_url": "",
            "public_repos": 20,
            "followers": 100,
            "following": 5,
            "created_at": "2020-01-01T00:00:00Z",
        }
        mock_events = [
            {
                "id": "1",
                "type": "PushEvent",
                "repo": {"name": "testorg/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}]},
            }
        ]
        mock_repos = [
            {
                "full_name": "testorg/repo",
                "stargazers_count": 50,
                "forks_count": 10,
                "language": "Python",
                "description": "An org repo",
                "fork": False,
            }
        ]
        mock_members = [
            {"login": "member1"},
            {"login": "member2"},
        ]

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_org_stats", return_value=mock_org),
            patch("gh_stats.cli.get_org_events", return_value=mock_events),
            patch("gh_stats.cli.get_org_repos", return_value=mock_repos),
            patch("gh_stats.cli.get_org_members", return_value=mock_members),
            patch("gh_stats.cli.get_org_contributions", return_value={"2026-01-15": 10}),
        ):
            runner = CliRunner()
            result = runner.invoke(main, ["--org", "testorg"])
            assert result.exit_code == 0
            assert "Test Org" in result.output
            assert "member1" in result.output

    def test_org_not_found(self):
        """Org not found should exit with error."""
        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_org_stats", return_value={}),
        ):
            runner = CliRunner()
            result = runner.invoke(main, ["--org", "nonexistentorg"])
            assert result.exit_code != 0
            assert "Organization not found" in result.output

    def test_user_and_org_mutually_exclusive(self):
        """--user and --org cannot be used together."""
        runner = CliRunner()
        result = runner.invoke(main, ["--user", "testuser", "--org", "testorg"])
        assert result.exit_code != 0
        assert "Cannot specify both" in result.output


class TestCLIExport:
    """Tests for CLI export functionality."""

    def test_json_export(self, tmp_path):
        """Export to JSON file."""
        mock_user = {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "",
            "bio": "",
            "public_repos": 1,
            "public_gists": 0,
            "followers": 0,
            "following": 0,
            "created_at": "",
        }
        output_file = tmp_path / "export.json"

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_user_stats", return_value=mock_user),
            patch("gh_stats.cli.get_user_events", return_value=[]),
            patch("gh_stats.cli.get_user_repos", return_value=[]),
            patch("gh_stats.cli.get_contributions", return_value={}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--user",
                    "testuser",
                    "--output",
                    str(output_file),
                    "--format",
                    "json",
                ],
            )
            assert result.exit_code == 0
            assert output_file.exists()
            import json

            data = json.loads(output_file.read_text())
            assert data["target_type"] == "user"
            assert data["target_name"] == "testuser"
            assert "Exported to" in result.output

    def test_html_export(self, tmp_path):
        """Export to HTML file."""
        mock_user = {
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "",
            "bio": "",
            "public_repos": 1,
            "public_gists": 0,
            "followers": 0,
            "following": 0,
            "created_at": "",
        }
        output_file = tmp_path / "export.html"

        with (
            patch("gh_stats.cli.get_token", return_value="fake_token"),
            patch("gh_stats.cli.get_user_stats", return_value=mock_user),
            patch("gh_stats.cli.get_user_events", return_value=[]),
            patch("gh_stats.cli.get_user_repos", return_value=[]),
            patch("gh_stats.cli.get_contributions", return_value={}),
        ):
            runner = CliRunner()
            result = runner.invoke(
                main,
                [
                    "--user",
                    "testuser",
                    "--output",
                    str(output_file),
                    "--format",
                    "html",
                ],
            )
            assert result.exit_code == 0
            assert output_file.exists()
            html = output_file.read_text()
            assert "<html" in html
            assert "testuser" in html
            assert "Exported to" in result.output
