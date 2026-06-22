# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for CLI comparison command."""

from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from gh_stats.cli import main


class TestCLICompare:
    """Tests for the compare command."""

    def test_compare_help(self):
        runner = CliRunner()
        result = runner.invoke(main, ["compare", "--help"])
        assert result.exit_code == 0
        assert "Compare two users" in result.output
        assert "--user-a" in result.output
        assert "--user-b" in result.output
        assert "--org-a" in result.output
        assert "--org-b" in result.output
        assert "--year-a" in result.output
        assert "--year-b" in result.output

    def test_compare_requires_two_targets(self):
        runner = CliRunner()
        result = runner.invoke(main, ["compare"])
        assert result.exit_code != 0
        assert "Must specify either two users or two organizations" in result.output

    def test_compare_user_and_org_mutually_exclusive(self):
        runner = CliRunner()
        result = runner.invoke(main, ["compare", "--user-a", "user1", "--org-b", "org1"])
        assert result.exit_code != 0
        assert "Cannot mix --user-* and --org-* options" in result.output

    def test_compare_time_period_requires_target(self):
        runner = CliRunner()
        result = runner.invoke(main, ["compare", "--year-a", "2023", "--year-b", "2024"])
        assert result.exit_code != 0
        assert "Must specify --user-a or --org-a" in result.output

    def test_compare_time_period_requires_different_years(self):
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--user-a",
                "user1",
                "--year-a",
                "2023",
                "--year-b",
                "2023",
            ],
        )
        assert result.exit_code != 0
        assert "--year-a and --year-b must be different years" in result.output

    @patch("gh_stats.cli.get_token")
    @patch("gh_stats.cli.fetch_target_data")
    @patch("gh_stats.cli.compute_all_stats")
    @patch("gh_stats.cli.compute_comparison_summary")
    @patch("gh_stats.cli.compute_contribution_patterns")
    @patch("gh_stats.cli.compute_growth_metrics")
    def test_compare_users_success(
        self,
        mock_growth,
        mock_patterns,
        mock_comparison,
        mock_compute_all,
        mock_fetch,
        mock_token,
    ):
        mock_token.return_value = "test-token"
        mock_fetch.return_value = (
            {"login": "user_a", "public_repos": 10, "followers": 100},
            {"2024-01-01": 5},
            [
                {
                    "type": "push",
                    "repo": "a/b",
                    "time": "2024-01-01T10:00:00Z",
                    "detail": "pushed",
                }
            ],
            [
                {
                    "full_name": "a/repo1",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "language": "Python",
                    "description": "Desc",
                    "fork": False,
                }
            ],
            None,
            {"login": "user_a"},
        )
        mock_compute_all.return_value = (
            {"Python": 5},
            [
                {
                    "name": "a/repo1",
                    "stars": 100,
                    "forks": 10,
                    "language": "Python",
                    "description": "Desc",
                }
            ],
            {"push": 10},
            {"current_streak": 5, "longest_streak": 10},
        )
        mock_comparison.return_value = {"a": {"push": 10}, "b": {"push": 5}}
        mock_patterns.return_value = {
            "by_weekday": {"Mon": 5},
            "most_active_day": "Mon",
            "least_active_day": "Sun",
            "by_month": {"Jan": 10},
            "peak_month": "Jan",
            "active_days": 2,
            "total_days": 7,
            "consistency_pct": 28.6,
            "avg_per_active_day": 5.0,
            "max_daily": 5,
        }
        mock_growth.return_value = {
            "total_growth_pct": 50.0,
            "active_days_growth_pct": 25.0,
            "consistency_change_pct": 10.0,
            "avg_daily_change_pct": 20.0,
            "peak_month_a": "Jan",
            "peak_month_b": "Jan",
            "verdict": "📈 Moderate growth",
        }

        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--user-a",
                "user_a",
                "--user-b",
                "user_b",
            ],
        )
        assert result.exit_code == 0
        output = result.output
        assert "Comparing user user_a vs user_b" in output or "Comparing user" in output

    @patch("gh_stats.cli.get_token")
    def test_compare_auth_error(self, mock_token):
        from gh_stats.api import AuthError

        mock_token.side_effect = AuthError("No token")

        runner = CliRunner()
        result = runner.invoke(main, ["compare", "--user-a", "user_a", "--user-b", "user_b"])
        assert result.exit_code == 1
        assert "Authentication error" in result.output


class TestCLIExport:
    """Tests for export functionality in compare command."""

    @patch("gh_stats.cli.get_token")
    @patch("gh_stats.cli.fetch_target_data")
    @patch("gh_stats.cli.compute_all_stats")
    @patch("gh_stats.cli.compute_comparison_summary")
    @patch("gh_stats.cli.compute_contribution_patterns")
    @patch("gh_stats.cli.compute_growth_metrics")
    def test_compare_json_export(
        self,
        mock_growth,
        mock_patterns,
        mock_comparison,
        mock_compute_all,
        mock_fetch,
        mock_token,
        tmp_path,
    ):
        mock_token.return_value = "test-token"
        mock_fetch.return_value = (
            {"login": "user_a", "public_repos": 10},
            {"2024-01-01": 5},
            [
                {
                    "type": "push",
                    "repo": "a/b",
                    "time": "2024-01-01T10:00:00Z",
                    "detail": "pushed",
                }
            ],
            [
                {
                    "full_name": "a/repo1",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "language": "Python",
                    "description": "Desc",
                    "fork": False,
                }
            ],
            None,
            {"login": "user_a"},
        )
        mock_compute_all.return_value = (
            {"Python": 5},
            [
                {
                    "name": "a/repo1",
                    "stars": 100,
                    "forks": 10,
                    "language": "Python",
                    "description": "Desc",
                }
            ],
            {"push": 10},
            {"current_streak": 5, "longest_streak": 10},
        )
        mock_comparison.return_value = {"a": {"push": 10}, "b": {"push": 5}}
        mock_patterns.return_value = {
            "by_weekday": {"Mon": 5},
            "most_active_day": "Mon",
            "least_active_day": "Sun",
            "by_month": {"Jan": 10},
            "peak_month": "Jan",
            "active_days": 2,
            "total_days": 7,
            "consistency_pct": 28.6,
            "avg_per_active_day": 5.0,
            "max_daily": 5,
        }
        mock_growth.return_value = {
            "total_growth_pct": 50.0,
            "active_days_growth_pct": 25.0,
            "consistency_change_pct": 10.0,
            "avg_daily_change_pct": 20.0,
            "peak_month_a": "Jan",
            "peak_month_b": "Jan",
            "verdict": "📈 Moderate growth",
        }

        output_file = tmp_path / "comparison.json"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--user-a",
                "user_a",
                "--user-b",
                "user_b",
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
        assert data["comparison_mode"] == "side_by_side"
        assert data["target_a"] == "user_a"
        assert data["target_b"] == "user_b"

    @patch("gh_stats.cli.get_token")
    @patch("gh_stats.cli.fetch_target_data")
    @patch("gh_stats.cli.compute_all_stats")
    @patch("gh_stats.cli.compute_comparison_summary")
    @patch("gh_stats.cli.compute_contribution_patterns")
    @patch("gh_stats.cli.compute_growth_metrics")
    def test_compare_html_export(
        self,
        mock_growth,
        mock_patterns,
        mock_comparison,
        mock_compute_all,
        mock_fetch,
        mock_token,
        tmp_path,
    ):
        mock_token.return_value = "test-token"
        mock_fetch.return_value = (
            {"login": "user_a", "public_repos": 10, "followers": 100},
            {"2024-01-01": 5},
            [
                {
                    "type": "push",
                    "repo": "a/b",
                    "time": "2024-01-01T10:00:00Z",
                    "detail": "pushed",
                }
            ],
            [
                {
                    "full_name": "a/repo1",
                    "stargazers_count": 100,
                    "forks_count": 10,
                    "language": "Python",
                    "description": "Desc",
                    "fork": False,
                }
            ],
            None,
            {"login": "user_a"},
        )
        mock_compute_all.return_value = (
            {"Python": 5},
            [
                {
                    "name": "a/repo1",
                    "stars": 100,
                    "forks": 10,
                    "language": "Python",
                    "description": "Desc",
                }
            ],
            {"push": 10},
            {"current_streak": 5, "longest_streak": 10},
        )
        mock_comparison.return_value = {"a": {"push": 10}, "b": {"push": 5}}
        mock_patterns.return_value = {
            "by_weekday": {"Mon": 5},
            "most_active_day": "Mon",
            "least_active_day": "Sun",
            "by_month": {"Jan": 10},
            "peak_month": "Jan",
            "active_days": 2,
            "total_days": 7,
            "consistency_pct": 28.6,
            "avg_per_active_day": 5.0,
            "max_daily": 5,
        }
        mock_growth.return_value = {
            "total_growth_pct": 50.0,
            "active_days_growth_pct": 25.0,
            "consistency_change_pct": 10.0,
            "avg_daily_change_pct": 20.0,
            "peak_month_a": "Jan",
            "peak_month_b": "Jan",
            "verdict": "📈 Moderate growth",
        }

        output_file = tmp_path / "comparison.html"
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "compare",
                "--user-a",
                "user_a",
                "--user-b",
                "user_b",
                "--output",
                str(output_file),
                "--format",
                "html",
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        html = output_file.read_text()
        assert "<!DOCTYPE html>" in html
        assert "user_a vs user_b" in html
