"""Tests for the UI rendering module."""

from rich.console import Console

from gh_stats.ui import (
    render_heatmap,
    render_language_chart,
    render_profile_card,
    render_repo_table,
    render_summary_bar,
)


def _render(panel) -> str:
    """Helper to render a Rich panel to a string."""
    c = Console(width=120, force_terminal=True)
    c.begin_capture()
    c.print(panel)
    return c.end_capture()


class TestRenderProfileCard:
    """Tests for render_profile_card."""

    def test_basic_profile(self):
        stats = {
            "login": "testuser",
            "name": "Test User",
            "bio": "A developer",
            "public_repos": 42,
            "followers": 100,
            "following": 50,
        }
        output = _render(render_profile_card(stats, contributions_total=500))
        assert "Test User" in output
        assert "testuser" in output

    def test_no_name_falls_back_to_login(self):
        stats = {
            "login": "testuser",
            "name": "",
            "bio": "",
            "public_repos": 0,
            "followers": 0,
            "following": 0,
        }
        output = _render(render_profile_card(stats, contributions_total=0))
        assert "testuser" in output


class TestRenderHeatmap:
    """Tests for render_heatmap."""

    def test_empty_contributions(self):
        panel = render_heatmap({}, year=2026)
        assert panel.title  # Panel has a title

    def test_with_contributions(self):
        contributions = {
            "2026-01-15": 3,
            "2026-01-16": 10,
            "2026-03-20": 1,
        }
        output = _render(render_heatmap(contributions, year=2026))
        assert "Heatmap" in output


class TestRenderLanguageChart:
    """Tests for render_language_chart."""

    def test_empty_stats(self):
        output = _render(render_language_chart({}))
        assert "No language data" in output

    def test_with_languages(self):
        lang_stats = {"Python": 15, "Rust": 8, "Go": 5}
        output = _render(render_language_chart(lang_stats))
        assert "Python" in output
        assert "Rust" in output


class TestRenderRepoTable:
    """Tests for render_repo_table."""

    def test_basic_table(self):
        repos = [
            {
                "name": "user/popular",
                "stars": 1000,
                "forks": 100,
                "language": "Rust",
                "description": "A popular project",
            },
            {
                "name": "user/small",
                "stars": 5,
                "forks": 0,
                "language": "Python",
                "description": "A small project",
            },
        ]
        output = _render(render_repo_table(repos, limit=10))
        assert "popular" in output
        assert "1000" in output


class TestRenderSummaryBar:
    """Tests for render_summary_bar."""

    def test_empty_summary(self):
        output = _render(render_summary_bar({}))
        assert "No activity data" in output

    def test_with_summary(self):
        summary = {"push": 50, "pr": 10, "issue": 5}
        output = _render(render_summary_bar(summary))
        assert "Push" in output
