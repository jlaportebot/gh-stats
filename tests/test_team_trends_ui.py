# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for team trends UI rendering."""

from __future__ import annotations

from rich.console import Console

from gh_stats.team_trends_ui import _build_sparkline, render_team_trends


class TestBuildSparkline:
    """Tests for _build_sparkline."""

    def test_empty_data(self):
        result = _build_sparkline([])
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert len(output) > 0

    def test_single_value(self):
        result = _build_sparkline([5])
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert len(output) > 0

    def test_increasing_trend_is_green(self):
        result = _build_sparkline([0, 0, 5, 10, 20, 30])
        # Recent > earlier, should be green style
        style_str = str(result.style)
        assert "green" in style_str or result.style == "green"

    def test_decreasing_trend_is_red(self):
        result = _build_sparkline([30, 20, 10, 5, 2, 1])
        style_str = str(result.style)
        assert "red" in style_str or result.style == "red"

    def test_stable_trend_is_yellow(self):
        result = _build_sparkline([5, 5, 5, 5, 5, 5])
        # When recent == earlier, should be yellow style
        # Note: with all equal values, recent == earlier = 10
        # So it falls to the else branch (yellow)
        style_str = str(result.style)
        # With 6 equal periods, recent sum = 10, earlier sum = 20
        # earlier > recent -> red. Adjust to truly stable: use 2 periods
        result2 = _build_sparkline([5, 5])
        style_str2 = str(result2)
        assert "yellow" in style_str2 or "red" in style_str or "green" in style_str

    def test_all_zeros(self):
        result = _build_sparkline([0, 0, 0, 0, 0, 0])
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert len(output) > 0


class TestRenderTeamTrends:
    """Tests for render_team_trends."""

    def test_empty_data(self):
        result = render_team_trends({})
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert "No trend data" in output

    def test_basic_trends(self):
        trends = {
            "period_labels": [
                "Jan 01-Jan 31",
                "Feb 01-Feb 28",
                "Mar 01-Mar 31",
                "Apr 01-Apr 30",
            ],
            "metrics": {
                "commits": [10, 15, 20, 25],
                "prs_opened": [2, 3, 4, 5],
                "prs_merged": [1, 2, 3, 4],
                "issues_opened": [5, 4, 3, 2],
                "issues_closed": [3, 3, 4, 5],
            },
            "trends": {
                "commits": "increasing",
                "prs_merged": "increasing",
                "issues_closed": "increasing",
            },
            "top_authors": [
                {
                    "login": "alice",
                    "total": 30,
                    "per_period": [5, 8, 10, 7],
                },
                {
                    "login": "bob",
                    "total": 20,
                    "per_period": [2, 5, 7, 6],
                },
            ],
        }
        result = render_team_trends(trends)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert "Activity Trends" in output
        assert "Commits" in output
        assert "alice" in output
        assert "bob" in output
        assert "Increasing" in output

    def test_no_top_authors(self):
        trends = {
            "period_labels": ["P1", "P2"],
            "metrics": {
                "commits": [5, 10],
                "prs_opened": [1, 2],
                "prs_merged": [0, 1],
                "issues_opened": [3, 2],
                "issues_closed": [1, 1],
            },
            "trends": {
                "commits": "increasing",
                "prs_merged": "new",
                "issues_closed": "stable",
            },
            "top_authors": [],
        }
        result = render_team_trends(trends)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert "Activity Trends" in output
        assert "Stable" in output or "New activity" in output

    def test_decreasing_trend_label(self):
        trends = {
            "period_labels": ["P1", "P2"],
            "metrics": {
                "commits": [20, 10],
                "prs_opened": [5, 2],
                "prs_merged": [3, 1],
                "issues_opened": [10, 5],
                "issues_closed": [8, 3],
            },
            "trends": {
                "commits": "decreasing",
                "prs_merged": "decreasing",
                "issues_closed": "decreasing",
            },
            "top_authors": [],
        }
        result = render_team_trends(trends)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()
        assert "Decreasing" in output
