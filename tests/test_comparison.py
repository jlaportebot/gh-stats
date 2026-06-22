# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for comparison mode functionality."""

from unittest.mock import MagicMock, patch

import pytest

from gh_stats.activity import compute_comparison_summary
from gh_stats.ui import (
    render_comparison_activity_timelines,
    render_comparison_heatmap,
    render_comparison_language_charts,
    render_comparison_profile_cards,
    render_comparison_repo_tables,
    render_comparison_streaks,
    render_comparison_summary_bars,
)


class TestComputeComparisonSummary:
    """Tests for compute_comparison_summary."""

    def test_compares_two_users_activities(self):
        """Should compute side-by-side activity counts for two users."""
        activities_a = [
            {"type": "push", "repo": "a/repo1", "time": "2024-01-01", "detail": "pushed"},
            {"type": "push", "repo": "a/repo2", "time": "2024-01-02", "detail": "pushed"},
            {"type": "pr", "repo": "a/repo1", "time": "2024-01-03", "detail": "opened PR"},
        ]
        activities_b = [
            {"type": "push", "repo": "b/repo1", "time": "2024-01-01", "detail": "pushed"},
            {"type": "issue", "repo": "b/repo1", "time": "2024-01-02", "detail": "opened issue"},
            {"type": "issue", "repo": "b/repo2", "time": "2024-01-03", "detail": "opened issue"},
            {"type": "issue", "repo": "b/repo3", "time": "2024-01-04", "detail": "opened issue"},
        ]
        result = compute_comparison_summary(activities_a, activities_b)
        assert result["a"]["push"] == 2
        assert result["a"]["pr"] == 1
        assert result["b"]["push"] == 1
        assert result["b"]["issue"] == 3

    def test_handles_empty_activities(self):
        """Should handle empty activity lists gracefully."""
        result = compute_comparison_summary([], [])
        assert result == {"a": {}, "b": {}}

    def test_handles_one_empty_side(self):
        """Should handle one side having no activities."""
        activities_a = [
            {"type": "push", "repo": "a/repo1", "time": "2024-01-01", "detail": "pushed"}
        ]
        result = compute_comparison_summary(activities_a, [])
        assert result["a"]["push"] == 1
        assert result["b"] == {}


class TestRenderComparisonProfileCards:
    """Tests for render_comparison_profile_cards."""

    def test_renders_two_profiles_side_by_side(self):
        """Should render two profile cards side by side."""
        stats_a = {
            "login": "user_a",
            "name": "User A",
            "avatar_url": "https://example.com/a.png",
            "bio": "Bio A",
            "public_repos": 10,
            "public_gists": 2,
            "followers": 100,
            "following": 50,
            "created_at": "2020-01-01T00:00:00Z",
        }
        stats_b = {
            "login": "user_b",
            "name": "User B",
            "avatar_url": "https://example.com/b.png",
            "bio": "Bio B",
            "public_repos": 5,
            "public_gists": 0,
            "followers": 50,
            "following": 25,
            "created_at": "2021-01-01T00:00:00Z",
        }
        panel = render_comparison_profile_cards(stats_a, stats_b, 500, 250, "user", "user")
        assert panel is not None
        # Render the panel to check content
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "user_a" in output
        assert "user_b" in output
        assert "500" in output
        assert "250" in output

    def test_renders_org_profiles(self):
        """Should render org profiles when target_type is org."""
        stats_a = {"login": "org_a", "name": "Org A", "public_repos": 20}
        stats_b = {"login": "org_b", "name": "Org B", "public_repos": 15}
        panel = render_comparison_profile_cards(stats_a, stats_b, 1000, 500, "org", "org")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "org_a" in output
        assert "org_b" in output


class TestRenderComparisonHeatmap:
    """Tests for render_comparison_heatmap."""

    def test_renders_two_heatmaps_side_by_side(self):
        """Should render two contribution heatmaps side by side."""
        contrib_a = {"2024-01-01": 5, "2024-01-02": 3}
        contrib_b = {"2024-01-01": 2, "2024-01-03": 4}
        panel = render_comparison_heatmap(contrib_a, contrib_b, 2024, "user", "user")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "Heatmap" in output

    def test_handles_empty_contributions_empty(self):
        """Should handle empty contribution data."""
        panel = render_comparison_heatmap({}, {}, 2024, "user", "user")
        assert panel is not None


class TestRenderComparisonLanguageCharts:
    """Tests for render_comparison_language_charts."""

    def test_renders_two_language_charts_side_by_side(self):
        """Should render two language distribution charts side by side."""
        lang_a = {"Python": 10, "JavaScript": 5}
        lang_b = {"Go": 8, "Rust": 3}
        panel = render_comparison_language_charts(lang_a, lang_b, "user", "user")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "Python" in output
        assert "Go" in output


class TestRenderComparisonRepoTables:
    """Tests for render_comparison_repo_tables."""

    def test_renders_two_repo_tables_side_by_side(self):
        """Should render two repository tables side by side."""
        repos_a = [
            {
                "name": "a/repo1",
                "stars": 100,
                "forks": 10,
                "language": "Python",
                "description": "Desc",
            }
        ]
        repos_b = [
            {"name": "b/repo1", "stars": 50, "forks": 5, "language": "Go", "description": "Desc"}
        ]
        panel = render_comparison_repo_tables(repos_a, repos_b, "user", "user")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "a/repo1" in output
        assert "b/repo1" in output


class TestRenderComparisonActivityTimelines:
    """Tests for render_comparison_activity_timelines."""

    def test_renders_two_timelines_side_by_side(self):
        """Should render two activity timelines side by side."""
        activities_a = [
            {"type": "push", "repo": "a/repo1", "time": "2024-01-01T10:00:00Z", "detail": "pushed"}
        ]
        activities_b = [
            {"type": "pr", "repo": "b/repo1", "time": "2024-01-01T11:00:00Z", "detail": "opened PR"}
        ]
        panel = render_comparison_activity_timelines(activities_a, activities_b, limit=10)
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        # Check for rendered icons (⬆ for push, 🔀 for PR)
        assert "Push" in output or "push" in output.lower()
        assert "PR" in output or "pr" in output.lower()


class TestRenderComparisonStreaks:
    """Tests for render_comparison_streaks."""

    def test_renders_two_streaks_side_by_side(self):
        """Should render two streak panels side by side."""
        streaks_a = {"current_streak": 10, "longest_streak": 30}
        streaks_b = {"current_streak": 5, "longest_streak": 20}
        panel = render_comparison_streaks(streaks_a, streaks_b, "user", "user")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        assert "10" in output
        assert "5" in output


class TestRenderComparisonSummaryBars:
    """Tests for render_comparison_summary_bars."""

    def test_renders_two_summary_bars_side_by_side(self):
        """Should render two summary bars side by side."""
        summary_a = {"push": 10, "pr": 5}
        summary_b = {"push": 3, "issue": 8}
        panel = render_comparison_summary_bars(summary_a, summary_b, "user", "user")
        assert panel is not None
        from rich.console import Console

        console = Console(record=True)
        console.print(panel)
        output = console.export_text()
        # Check for rendered icons (⬆ for pushes, 🔀 for PRs, ❗ for issues)
        assert "Push" in output or "push" in output.lower()
        assert "Issue" in output or "issue" in output.lower()
