# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for the UI rendering module."""

from rich.console import Console

from gh_stats.ui import (
    _render_html,
    render_heatmap,
    render_language_chart,
    render_members_table,
    render_profile_card,
    render_repo_table,
    render_summary_bar,
)


def _render(panel) -> str:
    """Helper to render a Rich panel to a string.

    Returns:
        Rendered panel as string.
    """
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


class TestRenderMembersTable:
    """Tests for render_members_table."""

    def test_basic_members(self):
        members = [
            {"login": "user1"},
            {"login": "user2"},
            {"login": "user3"},
        ]
        output = _render(render_members_table(members, limit=10))
        assert "user1" in output
        assert "user2" in output
        assert "user3" in output

    def test_limit_respected(self):
        members = [{"login": f"user{i}"} for i in range(30)]
        output = _render(render_members_table(members, limit=5))
        # Should only show first 5
        assert "user0" in output
        assert "user4" in output
        assert "user5" not in output

    def test_empty_members(self):
        output = _render(render_members_table([], limit=10))
        assert "Organization Members" in output


class TestRenderHTML:
    """Tests for _render_html."""

    def test_basic_html_output(self):
        data = {
            "target_type": "user",
            "target_name": "testuser",
            "year": 2026,
            "stats": {
                "login": "testuser",
                "name": "Test User",
                "public_repos": 10,
                "followers": 50,
                "following": 10,
                "description": "A developer",
            },
            "total_contributions": 100,
            "contributions": {"2026-01-15": 5},
            "activities": [
                {
                    "type": "push",
                    "repo": "testuser/repo1",
                    "detail": "Pushed 2 commits",
                    "time": "2026-01-15T10:00:00",
                },
            ],
            "lang_stats": {"Python": 8, "Rust": 2},
            "repo_stats": [
                {
                    "name": "testuser/repo1",
                    "stars": 100,
                    "forks": 10,
                    "language": "Python",
                    "description": "A repo",
                },
            ],
            "activity_summary": {"push": 50, "pr": 5},
            "members": [],
        }
        html = _render_html(data)
        assert "<html" in html
        assert "testuser" in html
        assert "Test User" in html
        assert "100" in html
        assert "Python" in html
        assert "repo1" in html

    def test_org_html_output(self):
        data = {
            "target_type": "org",
            "target_name": "testorg",
            "year": 2026,
            "stats": {
                "login": "testorg",
                "name": "Test Org",
                "public_repos": 50,
                "followers": 200,
                "following": 5,
                "description": "An organization",
            },
            "total_contributions": 500,
            "contributions": {},
            "activities": [],
            "lang_stats": {},
            "repo_stats": [],
            "activity_summary": {},
            "members": [{"login": "member1"}, {"login": "member2"}],
        }
        html = _render_html(data)
        assert "<html" in html
        assert "testorg" in html
        assert "Test Org" in html
        assert "member1" in html
        assert "member2" in html
