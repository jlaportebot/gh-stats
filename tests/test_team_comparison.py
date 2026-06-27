# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for team comparison computation."""

from __future__ import annotations

from typing import Any

from gh_stats.team_trends import compute_team_comparison, compute_team_time_comparison


class TestComputeTeamComparison:
    """Tests for compute_team_comparison."""

    def _make_team_data(
        self,
        total_repos: int = 10,
        total_contributors: int = 20,
        total_commits: int = 100,
        total_prs: int = 50,
        total_issues: int = 30,
        bus_factor: int = 3,
        avg_health: float = 75.0,
    ) -> dict[str, Any]:
        return {
            "summary": {
                "total_repos": total_repos,
                "total_contributors": total_contributors,
                "total_commits": total_commits,
                "total_prs": total_prs,
                "total_issues": total_issues,
                "bus_factor": bus_factor,
                "avg_health": avg_health,
            },
            "contributor_rankings": [
                {"login": "alice", "score": 100},
                {"login": "bob", "score": 80},
                {"login": "charlie", "score": 60},
            ],
            "repo_health": [
                {"name": "repo1", "health_score": 80, "status": "healthy"},
                {"name": "repo2", "health_score": 60, "status": "moderate"},
            ],
            "trends": {
                "metrics": {
                    "commits": [10, 20, 30],
                    "prs_opened": [5, 10, 15],
                    "prs_merged": [3, 6, 9],
                    "issues_opened": [8, 6, 4],
                    "issues_closed": [2, 4, 6],
                },
                "trends": {
                    "commits": "increasing",
                    "prs_opened": "increasing",
                    "prs_merged": "increasing",
                    "issues_opened": "decreasing",
                    "issues_closed": "increasing",
                },
                "period_labels": ["P1", "P2", "P3"],
            },
            "bus_factor": {
                "bus_factor": bus_factor,
                "coverage_pct": 70.0,
                "total_contributors": total_contributors,
            },
            "review_analytics": {
                "total_prs": total_prs,
                "pct_prs_reviewed": 80.0,
                "avg_reviews_per_pr": 2.5,
                "avg_time_to_first_review_hours": 24.0,
                "approval_count": 30,
                "changes_requested_count": 5,
                "comment_only_count": 15,
                "total_reviews": 125,
            },
        }

    def test_basic_comparison(self):
        team_a = self._make_team_data(
            total_repos=10,
            total_contributors=20,
            total_commits=100,
            total_prs=50,
            total_issues=30,
            bus_factor=3,
            avg_health=75.0,
        )
        team_b = self._make_team_data(
            total_repos=15,
            total_contributors=25,
            total_commits=150,
            total_prs=75,
            total_issues=40,
            bus_factor=4,
            avg_health=80.0,
        )

        result = compute_team_comparison(team_a, team_b, label_a="Team A", label_b="Team B")

        assert result["label_a"] == "Team A"
        assert result["label_b"] == "Team B"
        assert result["summary"]["total_repos"]["a"] == 10
        assert result["summary"]["total_repos"]["b"] == 15
        assert result["summary"]["total_repos"]["diff"] == 5
        assert result["summary"]["total_contributors"]["diff"] == 5
        assert result["summary"]["total_commits"]["diff"] == 50
        assert result["summary"]["total_prs"]["diff"] == 25
        assert result["summary"]["total_issues"]["diff"] == 10
        assert result["summary"]["bus_factor"]["diff"] == 1
        assert result["summary"]["avg_health"]["diff"] == 5.0

    def test_contributor_comparison(self):
        team_a = self._make_team_data()
        team_b = self._make_team_data()
        # Bob only in team_b
        team_b["contributor_rankings"].append({"login": "bob", "score": 90})
        # Alice higher in team_b
        team_b["contributor_rankings"][0]["score"] = 120

        result = compute_team_comparison(team_a, team_b)

        contributors = result["contributors"]
        # Should include alice, bob, charlie
        logins = [c["login"] for c in contributors]
        assert "alice" in logins
        assert "bob" in logins
        assert "charlie" in logins

        # Alice diff should be positive (120 - 100)
        alice = next(c for c in contributors if c["login"] == "alice")
        assert alice["score_a"] == 100
        assert alice["score_b"] == 120
        assert alice["diff"] == 20.0

    def test_repo_health_comparison(self):
        team_a = self._make_team_data()
        team_b = self._make_team_data()
        # Team B has better repo1
        team_b["repo_health"][0]["health_score"] = 90
        # Team B has extra repo3
        team_b["repo_health"].append({"name": "repo3", "health_score": 70, "status": "moderate"})

        result = compute_team_comparison(team_a, team_b)

        repos = result["repos"]
        names = [r["name"] for r in repos]
        assert "repo1" in names
        assert "repo2" in names
        assert "repo3" in names

        repo1 = next(r for r in repos if r["name"] == "repo1")
        assert repo1["score_a"] == 80
        assert repo1["score_b"] == 90
        assert repo1["diff"] == 10

        repo3 = next(r for r in repos if r["name"] == "repo3")
        assert repo3["score_a"] == 0
        assert repo3["score_b"] == 70
        assert repo3["diff"] == 70

    def test_trends_comparison(self):
        team_a = self._make_team_data()
        team_b = self._make_team_data()
        team_b["trends"]["metrics"]["commits"] = [20, 30, 40]  # higher

        result = compute_team_comparison(team_a, team_b)

        trends = result["trends"]
        assert "commits" in trends
        assert trends["commits"]["total_a"] == 60  # 10+20+30
        assert trends["commits"]["total_b"] == 90  # 20+30+40
        assert trends["commits"]["diff"] == 30
        assert trends["commits"]["trend_a"] == "increasing"
        assert trends["commits"]["trend_b"] == "increasing"

    def test_bus_factor_comparison(self):
        team_a = self._make_team_data(bus_factor=2, total_contributors=15)
        team_b = self._make_team_data(bus_factor=5, total_contributors=30)

        result = compute_team_comparison(team_a, team_b)

        bf = result["bus_factor"]
        assert bf["bus_factor_a"] == 2
        assert bf["bus_factor_b"] == 5
        assert bf["coverage_a"] == 70.0
        assert bf["coverage_b"] == 70.0
        assert bf["total_contributors_a"] == 15
        assert bf["total_contributors_b"] == 30

    def test_review_comparison(self):
        team_a = self._make_team_data(total_prs=50)
        team_b = self._make_team_data(total_prs=100)
        team_b["review_analytics"]["pct_prs_reviewed"] = 90.0
        team_b["review_analytics"]["avg_reviews_per_pr"] = 3.0
        team_b["review_analytics"]["avg_time_to_first_review_hours"] = 12.0
        team_b["review_analytics"]["approval_count"] = 60
        team_b["review_analytics"]["total_reviews"] = 300

        result = compute_team_comparison(team_a, team_b)

        reviews = result["reviews"]
        assert reviews["total_prs_a"] == 50
        assert reviews["total_prs_b"] == 100
        assert reviews["pct_reviewed_a"] == 80.0
        assert reviews["pct_reviewed_b"] == 90.0
        assert reviews["avg_reviews_a"] == 2.5
        assert reviews["avg_reviews_b"] == 3.0
        assert reviews["avg_time_a"] == 24.0
        assert reviews["avg_time_b"] == 12.0
        # Approval rate = approval_count / total_reviews * 100
        assert reviews["approval_rate_a"] == round(30 / 125 * 100, 1)
        assert reviews["approval_rate_b"] == round(60 / 300 * 100, 1)

    def test_empty_team_data(self):
        team_a = {}
        team_b = {}

        result = compute_team_comparison(team_a, team_b)

        assert result["summary"]["total_repos"]["a"] == 0
        assert result["summary"]["total_repos"]["b"] == 0
        assert result["contributors"] == []
        assert result["repos"] == []
        assert result["trends"] == {}


class TestComputeTeamTimeComparison:
    """Tests for compute_team_time_comparison."""

    def _make_team_data(
        self,
        total_repos: int = 10,
        total_contributors: int = 20,
        total_commits: int = 100,
        total_prs: int = 50,
        total_issues: int = 30,
        bus_factor: int = 3,
        avg_health: float = 75.0,
    ) -> dict[str, Any]:
        return {
            "summary": {
                "total_repos": total_repos,
                "total_contributors": total_contributors,
                "total_commits": total_commits,
                "total_prs": total_prs,
                "total_issues": total_issues,
                "bus_factor": bus_factor,
                "avg_health": avg_health,
            },
            "contributor_rankings": [
                {"login": "alice", "score": 100},
            ],
            "repo_health": [
                {"name": "repo1", "health_score": 80, "status": "healthy"},
            ],
            "trends": {
                "metrics": {
                    "commits": [10, 20, 30],
                    "prs_opened": [5, 10, 15],
                    "prs_merged": [3, 6, 9],
                    "issues_opened": [8, 6, 4],
                    "issues_closed": [2, 4, 6],
                },
                "trends": {
                    "commits": "increasing",
                    "prs_opened": "increasing",
                    "prs_merged": "increasing",
                    "issues_opened": "decreasing",
                    "issues_closed": "increasing",
                },
                "period_labels": ["P1", "P2", "P3"],
            },
            "bus_factor": {
                "bus_factor": bus_factor,
                "coverage_pct": 70.0,
                "total_contributors": total_contributors,
            },
            "review_analytics": {
                "total_prs": total_prs,
                "pct_prs_reviewed": 80.0,
                "avg_reviews_per_pr": 2.5,
                "avg_time_to_first_review_hours": 24.0,
                "approval_count": 30,
                "changes_requested_count": 5,
                "comment_only_count": 15,
                "total_reviews": 125,
            },
        }

    def test_time_comparison_adds_growth_rates(self):
        team_previous = self._make_team_data(
            total_repos=8,
            total_contributors=15,
            total_commits=80,
            total_prs=40,
        )
        team_current = self._make_team_data(
            total_repos=10,
            total_contributors=20,
            total_commits=100,
            total_prs=50,
        )

        result = compute_team_time_comparison(
            team_current,
            team_previous,
            label_current="Current",
            label_previous="Previous",
        )

        summary = result["summary"]
        # Growth rates should be present
        assert "growth_pct" in summary["total_repos"]
        assert "growth_pct" in summary["total_contributors"]
        assert "growth_pct" in summary["total_commits"]
        assert "growth_pct" in summary["total_prs"]

        # total_repos: (10-8)/8*100 = 25%
        assert summary["total_repos"]["growth_pct"] == 25.0
        # total_contributors: (20-15)/15*100 = 33.3...%
        assert summary["total_contributors"]["growth_pct"] == 33.3
        # total_commits: (100-80)/80*100 = 25%
        assert summary["total_commits"]["growth_pct"] == 25.0
        # total_prs: (50-40)/40*100 = 25%
        assert summary["total_prs"]["growth_pct"] == 25.0

    def test_time_comparison_trends_growth(self):
        team_previous = self._make_team_data()
        team_previous["trends"]["metrics"]["commits"] = [10, 20, 30]  # total 60

        team_current = self._make_team_data()
        team_current["trends"]["metrics"]["commits"] = [20, 30, 40]  # total 90

        result = compute_team_time_comparison(team_current, team_previous)

        trends = result["trends"]
        assert "growth_pct" in trends["commits"]
        # (90-60)/60*100 = 50%
        assert trends["commits"]["growth_pct"] == 50.0

    def test_time_comparison_review_growth(self):
        team_current = self._make_team_data(total_prs=100)
        team_current["review_analytics"]["pct_prs_reviewed"] = 90.0
        team_current["review_analytics"]["avg_reviews_per_pr"] = 3.0
        team_current["review_analytics"]["total_reviews"] = 300
        team_current["review_analytics"]["approval_count"] = 60

        team_previous = self._make_team_data(total_prs=50)
        team_previous["review_analytics"]["pct_prs_reviewed"] = 80.0
        team_previous["review_analytics"]["avg_reviews_per_pr"] = 2.5
        team_previous["review_analytics"]["total_reviews"] = 125
        team_previous["review_analytics"]["approval_count"] = 30

        result = compute_team_time_comparison(team_current, team_previous)

        reviews = result["reviews"]
        # Check growth keys exist
        assert "pct_reviewed_a_growth_pct" in reviews
        assert "avg_reviews_a_growth_pct" in reviews
        assert "avg_time_a_growth_pct" in reviews
        assert "approval_rate_a_growth_pct" in reviews

    def test_time_comparison_zero_base(self):
        team_current = self._make_team_data(total_commits=100)
        team_previous = self._make_team_data(total_commits=0)

        result = compute_team_time_comparison(team_current, team_previous)

        summary = result["summary"]
        # 100% growth when base is 0
        assert summary["total_commits"]["growth_pct"] == 100.0

    def test_time_comparison_same_values(self):
        team = self._make_team_data()

        result = compute_team_time_comparison(team, team)

        summary = result["summary"]
        for key in summary:
            assert summary[key]["growth_pct"] == 0.0
