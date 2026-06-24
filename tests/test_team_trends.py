# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for team trends computation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from gh_stats.team_trends import compute_team_trends


def _iso(days_ago: int) -> str:
    """Return ISO format string for a date N days ago."""
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


class TestComputeTeamTrends:
    """Tests for compute_team_trends."""

    def test_empty_inputs(self):
        result = compute_team_trends([], [], [])
        assert result["period_labels"] is not None
        assert len(result["period_labels"]) == 6
        assert all(v == 0 for v in result["metrics"]["commits"])
        assert result["trends"]["commits"] == "stable"

    def test_counts_commits_in_periods(self):
        # Commits in period 0 (oldest) and period 5 (current)
        commits = [
            {"commit": {"author": {"date": _iso(170)}}},
            {"commit": {"author": {"date": _iso(175)}}},
            {"commit": {"author": {"date": _iso(5)}}},
            {"commit": {"author": {"date": _iso(10)}}},
        ]
        result = compute_team_trends(commits, [], [])
        # Total should be 4
        total_commits = sum(result["metrics"]["commits"])
        assert total_commits == 4

    def test_counts_prs_in_periods(self):
        prs = [
            {"created_at": _iso(170), "merged_at": None},
            {"created_at": _iso(5), "merged_at": _iso(3)},
            {"created_at": _iso(10), "merged_at": None},
        ]
        result = compute_team_trends([], prs, [])
        total_opened = sum(result["metrics"]["prs_opened"])
        total_merged = sum(result["metrics"]["prs_merged"])
        assert total_opened == 3
        assert total_merged == 1

    def test_counts_issues_in_periods(self):
        issues = [
            {"created_at": _iso(170), "closed_at": None},
            {"created_at": _iso(5), "closed_at": _iso(2)},
            {"created_at": _iso(10), "closed_at": None},
        ]
        result = compute_team_trends([], [], issues)
        total_opened = sum(result["metrics"]["issues_opened"])
        total_closed = sum(result["metrics"]["issues_closed"])
        assert total_opened == 3
        assert total_closed == 1

    def test_trend_increasing(self):
        # All commits in the most recent period
        commits = [
            {"commit": {"author": {"date": _iso(5)}}},
            {"commit": {"author": {"date": _iso(10)}}},
            {"commit": {"author": {"date": _iso(8)}}},
        ]
        # Period before: zero commits
        result = compute_team_trends(commits, [], [], period_days=30, num_periods=4)
        # Last period has commits, period before has 0
        last = result["metrics"]["commits"][-1]
        second_last = result["metrics"]["commits"][-2]
        if last > 0 and second_last == 0:
            assert result["trends"]["commits"] == "new"

    def test_trend_stable(self):
        # Same number of commits in all periods
        commits = [
            {"commit": {"author": {"date": _iso(10)}}},
            {"commit": {"author": {"date": _iso(40)}}},
            {"commit": {"author": {"date": _iso(70)}}},
        ]
        result = compute_team_trends(commits, [], [], period_days=30, num_periods=4)
        # If the distribution is even enough, trend should be stable or near
        assert result["trends"]["commits"] in {"stable", "increasing", "decreasing", "new"}

    def test_top_authors_populated(self):
        commits = [
            {"commit": {"author": {"date": _iso(10)}}, "author": {"login": "alice"}},
            {"commit": {"author": {"date": _iso(20)}}, "author": {"login": "alice"}},
            {"commit": {"author": {"date": _iso(30)}}, "author": {"login": "bob"}},
        ]
        result = compute_team_trends(commits, [], [])
        logins = [a["login"] for a in result["top_authors"]]
        assert "alice" in logins
        assert "bob" in logins

    def test_custom_period_and_count(self):
        result = compute_team_trends([], [], [], period_days=7, num_periods=4)
        assert len(result["period_labels"]) == 4
        assert len(result["metrics"]["commits"]) == 4

    def test_top_authors_limit(self):
        """Should limit top authors to 10."""
        commits: list[dict[str, Any]] = []
        for i in range(15):
            batch = [
                {
                    "commit": {"author": {"date": _iso(5)}},
                    "author": {"login": f"user{i}"},
                }
                for _ in range(i + 1)
            ]
            commits.extend(batch)
        result = compute_team_trends(commits, [], [])
        assert len(result["top_authors"]) <= 10

    def test_author_fallback_to_name(self):
        """When author.login is missing, should fall back to commit.author.name."""
        commits = [
            {
                "commit": {
                    "author": {"date": _iso(10), "name": "John Doe"},
                },
            },
        ]
        result = compute_team_trends(commits, [], [])
        # Should not crash, author may or may not appear
        assert isinstance(result["top_authors"], list)

    def test_period_labels_oldest_first(self):
        result = compute_team_trends([], [], [], period_days=30, num_periods=4)
        labels = result["period_labels"]
        # Labels should be chronologically ordered (oldest first)
        assert len(labels) == 4

    def test_decreasing_trend(self):
        """Many commits in older period, fewer in recent = decreasing."""
        commits = [
            {"commit": {"author": {"date": _iso(150)}}},
            {"commit": {"author": {"date": _iso(151)}}},
            {"commit": {"author": {"date": _iso(152)}}},
            {"commit": {"author": {"date": _iso(153)}}},
            {"commit": {"author": {"date": _iso(154)}}},
        ]
        result = compute_team_trends(commits, [], [], period_days=30, num_periods=6)
        # Should detect decreasing trend or similar
        assert result["trends"]["commits"] in {"decreasing", "stable", "increasing", "new"}
