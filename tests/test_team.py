# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for the team analytics module."""

from __future__ import annotations

import math

import pytest

from gh_stats.team import (
    compute_bus_factor,
    compute_collaboration_matrix,
    compute_contributor_rankings,
    compute_repo_health_scores,
    compute_review_analytics,
)


class TestComputeContributorRankings:
    """Tests for compute_contributor_rankings."""

    def test_empty_inputs(self):
        """Should return empty list for empty inputs."""
        result = compute_contributor_rankings([], [], [], {}, [])
        assert result == []

    def test_single_contributor(self):
        """Should rank single contributor correctly."""
        contributors = [{"login": "user1", "contributions": 10, "avatar_url": "url"}]
        commits = [{"author": {"login": "user1"}, "stats": {"additions": 100, "deletions": 50}}]
        prs = [{"user": {"login": "user1"}, "merged_at": "2024-01-01T00:00:00Z"}]
        reviews = {1: [{"user": {"login": "user1"}, "state": "APPROVED"}]}
        issues = [{"user": {"login": "user1"}, "state": "closed"}]

        result = compute_contributor_rankings(contributors, commits, prs, reviews, issues, top_n=10)

        assert len(result) == 1
        assert result[0]["login"] == "user1"
        assert result[0]["commits"] == 1
        assert result[0]["prs_opened"] == 1
        assert result[0]["prs_merged"] == 1
        assert result[0]["reviews_given"] == 1
        assert result[0]["issues_opened"] == 1
        assert result[0]["issues_closed"] == 1
        assert result[0]["lines_added"] == 100
        assert result[0]["lines_removed"] == 50
        assert result[0]["score"] > 0

    def test_multiple_contributors_sorted_by_score(self):
        """Should sort contributors by score descending."""
        contributors = [
            {"login": "user1", "contributions": 5},
            {"login": "user2", "contributions": 10},
        ]
        commits = [
            {"author": {"login": "user1"}},
            {"author": {"login": "user1"}},
            {"author": {"login": "user2"}},
        ]
        prs = [{"user": {"login": "user2"}, "merged_at": "2024-01-01T00:00:00Z"}]
        reviews = {}
        issues = []

        result = compute_contributor_rankings(contributors, commits, prs, reviews, issues, top_n=10)

        assert len(result) == 2
        # user2 has more contributions + PR merged
        assert result[0]["login"] == "user2"
        assert result[1]["login"] == "user1"


class TestComputeBusFactor:
    """Tests for compute_bus_factor."""

    def test_empty_inputs(self):
        """Should return zero bus factor for empty inputs."""
        result = compute_bus_factor([], [], [])
        assert result["bus_factor"] == 0
        assert math.isclose(result["coverage_pct"], 0.0)
        assert result["total_contributors"] == 0

    def test_single_contributor(self):
        """Should return bus factor 1 for single contributor."""
        contributors = [{"login": "user1", "contributions": 10}]
        commits = [{"author": {"login": "user1"}}]
        prs = [{"user": {"login": "user1"}, "merged_at": "2024-01-01T00:00:00Z"}]

        result = compute_bus_factor(contributors, commits, prs)

        assert result["bus_factor"] == 1
        assert math.isclose(result["coverage_pct"], 100.0)
        assert result["total_contributors"] == 1

    def test_multiple_contributors_threshold(self):
        """Should calculate bus factor based on threshold."""
        contributors = [
            {"login": "user1", "contributions": 100},
            {"login": "user2", "contributions": 50},
            {"login": "user3", "contributions": 25},
            {"login": "user4", "contributions": 10},
        ]
        commits = []
        prs = []

        result = compute_bus_factor(contributors, commits, prs, threshold_pct=50.0)

        # user1 alone has 100/185 = 54% > 50%
        assert result["bus_factor"] == 1
        assert result["coverage_pct"] > 50.0

    def test_custom_threshold(self):
        """Should respect custom threshold percentage."""
        contributors = [
            {"login": "user1", "contributions": 60},
            {"login": "user2", "contributions": 40},
        ]
        commits = []
        prs = []

        result = compute_bus_factor(contributors, commits, prs, threshold_pct=80.0)

        # Need both to reach 80%
        assert result["bus_factor"] == 2
        assert math.isclose(result["coverage_pct"], 100.0)


class TestComputeRepoHealthScores:
    """Tests for compute_repo_health_scores."""

    def test_empty_repos(self):
        """Should return empty list for empty repos."""
        result = compute_repo_health_scores([], {}, {}, {}, {})
        assert result == []

    def test_archived_repo_gets_zero_score(self):
        """Archived repos should get health score 0."""
        repos = [{"name": "repo1", "archived": True, "disabled": False, "fork": False}]
        result = compute_repo_health_scores(repos, {}, {}, {}, {})

        assert len(result) == 1
        assert result[0]["health_score"] == 0
        assert result[0]["status"] == "archived"

    def test_disabled_repo_gets_zero_score(self):
        """Disabled repos should get health score 0."""
        repos = [{"name": "repo1", "archived": False, "disabled": True, "fork": False}]
        result = compute_repo_health_scores(repos, {}, {}, {}, {})

        assert len(result) == 1
        assert result[0]["health_score"] == 0
        assert result[0]["status"] == "disabled"

    def test_active_repo_gets_score(self):
        """Active repos should get a health score."""
        from datetime import UTC, datetime, timedelta

        now = datetime.now(UTC)
        recent = (now - timedelta(days=5)).isoformat()

        repos = [
            {
                "name": "repo1",
                "archived": False,
                "disabled": False,
                "fork": False,
                "stargazers_count": 100,
                "open_issues_count": 5,
                "pushed_at": recent,
                "license": {"name": "MIT"},
                "topics": ["python"],
                "size": 1000,
            }
        ]
        commits = [{"commit": {"author": {"date": recent}}}]
        prs = [{"state": "closed", "merged_at": recent}]
        issues = [{"state": "closed", "closed_at": recent}]
        contributors = [{"login": "user1"}]

        result = compute_repo_health_scores(
            repos, {"repo1": commits}, {"repo1": prs}, {"repo1": issues}, {"repo1": contributors}
        )

        assert len(result) == 1
        assert result[0]["health_score"] > 0
        assert result[0]["status"] in {"healthy", "moderate", "declining", "stale"}


class TestComputeCollaborationMatrix:
    """Tests for compute_collaboration_matrix."""

    def test_empty_inputs(self):
        """Should return empty nodes and edges for empty inputs."""
        result = compute_collaboration_matrix([], [], {})

        assert result["nodes"] == []
        assert result["edges"] == []
        assert result["total_collaborations"] == 0

    def test_pr_review_creates_edge(self):
        """PR review should create collaboration edge."""
        prs = [
            {"number": 1, "user": {"login": "author1"}},
            {"number": 2, "user": {"login": "author2"}},
        ]
        reviews = {
            1: [{"user": {"login": "reviewer1"}, "state": "APPROVED"}],
            2: [],
        }
        commits = []

        result = compute_collaboration_matrix(commits, prs, reviews)

        assert len(result["nodes"]) >= 2
        assert result["total_collaborations"] >= 1
        # Check edge between author1 and reviewer1
        edges = result["edges"]
        assert any(
            (e["source"] == "author1" and e["target"] == "reviewer1")
            or (e["source"] == "reviewer1" and e["target"] == "author1")
            for e in edges
        )

    def test_commits_add_contributors(self):
        """Commit authors should be added as nodes."""
        prs = []
        reviews = {}
        commits = [
            {"author": {"login": "committer1"}},
            {"author": {"login": "committer2"}},
        ]

        result = compute_collaboration_matrix(commits, prs, reviews)

        logins = {n["login"] for n in result["nodes"]}
        assert "committer1" in logins
        assert "committer2" in logins


class TestComputeReviewAnalytics:
    """Tests for compute_review_analytics."""

    def test_empty_prs(self):
        """Should return zeros for empty PR list."""
        result = compute_review_analytics([], {})

        assert result["total_prs"] == 0
        assert result["prs_with_reviews"] == 0
        assert math.isclose(result["pct_prs_reviewed"], 0.0)
        assert result["total_reviews"] == 0

    def test_prs_without_reviews(self):
        """Should handle PRs with no reviews."""
        prs = [
            {"number": 1, "created_at": "2024-01-01T00:00:00Z"},
            {"number": 2, "created_at": "2024-01-02T00:00:00Z"},
        ]
        reviews = {}

        result = compute_review_analytics(prs, reviews)

        assert result["total_prs"] == 2
        assert result["prs_with_reviews"] == 0
        assert math.isclose(result["pct_prs_reviewed"], 0.0)

    def test_prs_with_reviews(self):
        """Should calculate review stats correctly."""
        prs = [
            {"number": 1, "created_at": "2024-01-01T00:00:00Z"},
            {"number": 2, "created_at": "2024-01-02T00:00:00Z"},
        ]
        reviews = {
            1: [
                {
                    "user": {"login": "reviewer1"},
                    "state": "APPROVED",
                    "submitted_at": "2024-01-01T01:00:00Z",
                },
                {
                    "user": {"login": "reviewer2"},
                    "state": "CHANGES_REQUESTED",
                    "submitted_at": "2024-01-01T02:00:00Z",
                },
            ],
            2: [
                {
                    "user": {"login": "reviewer1"},
                    "state": "COMMENTED",
                    "submitted_at": "2024-01-02T01:00:00Z",
                },
            ],
        }

        result = compute_review_analytics(prs, reviews)

        assert result["total_prs"] == 2
        assert result["prs_with_reviews"] == 2
        assert math.isclose(result["pct_prs_reviewed"], 100.0)
        assert result["total_reviews"] == 3
        assert math.isclose(result["avg_reviews_per_pr"], 1.5)
        assert result["approval_count"] == 1
        assert result["changes_requested_count"] == 1
        assert result["comment_only_count"] == 1
        assert math.isclose(result["avg_time_to_first_review_hours"], 1.0)  # 1 hour for PR #1
        assert len(result["top_reviewers"]) == 2
        assert result["top_reviewers"][0]["login"] == "reviewer1"
        assert result["top_reviewers"][0]["reviews"] == 2

    def test_ignores_pr_without_number(self):
        """Should skip PRs without a number."""
        prs = [{"created_at": "2024-01-01T00:00:00Z"}]  # No number
        reviews = {}

        result = compute_review_analytics(prs, reviews)

        assert result["total_prs"] == 1
        assert result["prs_with_reviews"] == 0


class TestRenderContributorTable:
    """Tests for render_contributor_table."""

    def test_empty_contributors(self):
        """Should return panel with empty message for empty contributors."""
        from rich.console import Console

        from gh_stats.team_ui import render_contributor_table

        result = render_contributor_table([])
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "No contributor data available" in output

    def test_single_contributor(self):
        """Should render single contributor correctly."""
        from rich.console import Console

        from gh_stats.team_ui import render_contributor_table

        contributors = [
            {
                "login": "user1",
                "score": 100.5,
                "commits": 10,
                "prs_opened": 5,
                "prs_merged": 4,
                "reviews_given": 3,
                "issues_opened": 2,
                "issues_closed": 1,
                "lines_added": 500,
                "lines_removed": 100,
            }
        ]
        result = render_contributor_table(contributors, limit=10)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "user1" in output
        assert "100" in output  # score rounded (100.5 -> 100, rounds to even)
        assert "10" in output
        assert "5" in output
        assert "+500/-100" in output

    def test_multiple_contributors_sorted(self):
        """Should render multiple contributors."""
        from rich.console import Console

        from gh_stats.team_ui import render_contributor_table

        contributors = [
            {
                "login": "user1",
                "score": 50,
                "commits": 5,
                "prs_opened": 2,
                "prs_merged": 1,
                "reviews_given": 1,
                "issues_opened": 1,
                "issues_closed": 0,
                "lines_added": 100,
                "lines_removed": 20,
            },
            {
                "login": "user2",
                "score": 100,
                "commits": 10,
                "prs_opened": 4,
                "prs_merged": 3,
                "reviews_given": 2,
                "issues_opened": 2,
                "issues_closed": 1,
                "lines_added": 200,
                "lines_removed": 50,
            },
        ]
        result = render_contributor_table(contributors, limit=10)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "user1" in output
        assert "user2" in output

    def test_limit_respected(self):
        """Should respect limit parameter."""
        from rich.console import Console

        from gh_stats.team_ui import render_contributor_table

        contributors = [
            {
                "login": f"user{i}",
                "score": i * 10,
                "commits": i,
                "prs_opened": 0,
                "prs_merged": 0,
                "reviews_given": 0,
                "issues_opened": 0,
                "issues_closed": 0,
                "lines_added": 0,
                "lines_removed": 0,
            }
            for i in range(20)
        ]
        result = render_contributor_table(contributors, limit=5)
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # Should only show top 5
        assert "user19" not in output


class TestRenderBusFactor:
    """Tests for render_bus_factor."""

    def test_empty_data(self):
        """Should return panel with message for empty data."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({})
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Insufficient data" in output

    def test_bus_factor_zero(self):
        """Should handle bus factor of 0."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({
            "bus_factor": 0,
            "threshold_pct": 50.0,
            "top_contributors": [],
            "coverage_pct": 0.0,
            "total_contributors": 0,
        })
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        # bus_factor 0 shows insufficient data message
        assert "Insufficient data" in output

    def test_bus_factor_critical(self):
        """Should show critical risk for bus factor <= 1."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({
            "bus_factor": 1,
            "threshold_pct": 50.0,
            "top_contributors": [{"login": "user1", "pct": 60.0}],
            "coverage_pct": 60.0,
            "total_contributors": 5,
        })
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "Bus Factor: 1" in output
        assert "CRITICAL" in output
        assert "user1" in output

    def test_bus_factor_high(self):
        """Should show high risk for bus factor == 2."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({
            "bus_factor": 2,
            "threshold_pct": 50.0,
            "top_contributors": [
                {"login": "user1", "pct": 40.0},
                {"login": "user2", "pct": 30.0},
            ],
            "coverage_pct": 70.0,
            "total_contributors": 5,
        })
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "HIGH" in output

    def test_bus_factor_medium(self):
        """Should show medium risk for bus factor == 3."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({
            "bus_factor": 3,
            "threshold_pct": 50.0,
            "top_contributors": [],
            "coverage_pct": 60.0,
            "total_contributors": 10,
        })
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "MEDIUM" in output

    def test_bus_factor_low(self):
        """Should show low risk for bus factor >= 4."""
        from rich.console import Console

        from gh_stats.team_ui import render_bus_factor

        result = render_bus_factor({
            "bus_factor": 4,
            "threshold_pct": 50.0,
            "top_contributors": [],
            "coverage_pct": 55.0,
            "total_contributors": 20,
        })
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "LOW" in output


class TestRenderRepoHealthMatrix:
    """Tests for render_repo_health_matrix."""

    def test_empty_repos(self):
        """Should return panel with message for empty repos."""
        from rich.console import Console

        from gh_stats.team_ui import render_repo_health_matrix

        result = render_repo_health_matrix([])
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "No repository data available" in output

    def test_single_repo(self):
        """Should render single repo correctly."""
        from rich.console import Console

        from gh_stats.team_ui import render_repo_health_matrix

        repos = [
            {
                "name": "repo1",
                "health_score": 85,
                "status": "healthy",
                "language": "Python",
                "stars": 100,
                "commits_30d": 20,
                "prs_open": 3,
                "prs_merged_30d": 10,
                "issues_open": 5,
                "contributors_count": 8,
            }
        ]
        result = render_repo_health_matrix(repos, limit=10)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "repo1" in output
        assert "85" in output
        assert "healthy" in output
        assert "Python" in output

    def test_multiple_repos_with_status_colors(self):
        """Should render multiple repos with different statuses."""
        from rich.console import Console

        from gh_stats.team_ui import render_repo_health_matrix

        repos = [
            {
                "name": "repo1",
                "health_score": 90,
                "status": "healthy",
                "language": "Python",
                "stars": 100,
                "commits_30d": 20,
                "prs_open": 3,
                "prs_merged_30d": 10,
                "issues_open": 5,
                "contributors_count": 8,
            },
            {
                "name": "repo2",
                "health_score": 45,
                "status": "moderate",
                "language": "Rust",
                "stars": 50,
                "commits_30d": 5,
                "prs_open": 1,
                "prs_merged_30d": 2,
                "issues_open": 10,
                "contributors_count": 3,
            },
            {
                "name": "repo3",
                "health_score": 10,
                "status": "stale",
                "language": "Go",
                "stars": 10,
                "commits_30d": 0,
                "prs_open": 0,
                "prs_merged_30d": 0,
                "issues_open": 20,
                "contributors_count": 1,
            },
        ]
        result = render_repo_health_matrix(repos, limit=10)
        console = Console(width=200)
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "repo1" in output
        assert "repo2" in output
        assert "repo3" in output

    def test_limit_respected(self):
        """Should respect limit parameter."""
        from rich.console import Console

        from gh_stats.team_ui import render_repo_health_matrix

        repos = [
            {
                "name": f"repo{i}",
                "health_score": 50,
                "status": "moderate",
                "language": "Python",
                "stars": 10,
                "commits_30d": 5,
                "prs_open": 1,
                "prs_merged_30d": 2,
                "issues_open": 3,
                "contributors_count": 2,
            }
            for i in range(20)
        ]
        result = render_repo_health_matrix(repos, limit=5)
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "repo19" not in output


class TestRenderCollaborationHeatmap:
    """Tests for render_collaboration_heatmap."""

    def test_empty_data(self):
        """Should return panel with message for empty data."""
        from rich.console import Console

        from gh_stats.team_ui import render_collaboration_heatmap

        result = render_collaboration_heatmap({})
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "No collaboration data available" in output

    def test_with_nodes_and_edges(self):
        """Should render heatmap with nodes and edges."""
        from rich.console import Console

        from gh_stats.team_ui import render_collaboration_heatmap

        collab_data = {
            "nodes": [
                {"login": "user1"},
                {"login": "user2"},
                {"login": "user3"},
            ],
            "edges": [
                {"source": "user1", "target": "user2", "weight": 5},
                {"source": "user2", "target": "user3", "weight": 2},
            ],
            "total_collaborations": 7,
        }
        result = render_collaboration_heatmap(collab_data, limit=10)
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "user1" in output
        assert "user2" in output
        assert "Total collaboration edges: 7" in output

    def test_limit_respected(self):
        """Should respect limit parameter for nodes."""
        from rich.console import Console

        from gh_stats.team_ui import render_collaboration_heatmap

        nodes = [{"login": f"user{i}"} for i in range(20)]
        edges = [{"source": "user0", "target": "user1", "weight": 1}]
        result = render_collaboration_heatmap(
            {"nodes": nodes, "edges": edges, "total_collaborations": 1}, limit=5
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "user19" not in output


class TestRenderReviewAnalytics:
    """Tests for render_review_analytics."""

    def test_empty_prs(self):
        """Should return panel with message for empty PRs."""
        from rich.console import Console

        from gh_stats.team_ui import render_review_analytics

        result = render_review_analytics({})
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "No PR data available" in output

    def test_with_review_data(self):
        """Should render review analytics correctly."""
        from rich.console import Console

        from gh_stats.team_ui import render_review_analytics

        review_data = {
            "total_prs": 10,
            "prs_with_reviews": 8,
            "pct_prs_reviewed": 80.0,
            "avg_reviews_per_pr": 1.5,
            "approval_count": 12,
            "changes_requested_count": 3,
            "comment_only_count": 2,
            "avg_time_to_first_review_hours": 24.5,
            "median_time_to_first_review_hours": 12.0,
            "top_reviewers": [
                {"login": "reviewer1", "reviews": 5},
                {"login": "reviewer2", "reviews": 3},
            ],
        }
        result = render_review_analytics(review_data)
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "10" in output
        assert "8" in output
        assert "80.0" in output
        assert "reviewer1" in output
        assert "Approvals" in output


class TestRenderTeamSummary:
    """Tests for render_team_summary."""

    def test_basic_summary(self):
        """Should render basic team summary."""
        from rich.console import Console

        from gh_stats.team_ui import render_team_summary

        result = render_team_summary(
            org_name="testorg",
            total_repos=10,
            total_contributors=25,
            total_commits=500,
            total_prs=100,
            total_issues=50,
            bus_factor=3,
            avg_health=75.5,
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "testorg" in output
        assert "10" in output
        assert "25" in output
        assert "500" in output
        assert "100" in output
        assert "50" in output
        assert "3" in output
        assert "76" in output  # rounded from 75.5
        assert "GOOD" in output

    def test_excellent_health(self):
        """Should show EXCELLENT for avg_health >= 80."""
        from rich.console import Console

        from gh_stats.team_ui import render_team_summary

        result = render_team_summary(
            org_name="testorg",
            total_repos=5,
            total_contributors=10,
            total_commits=100,
            total_prs=20,
            total_issues=5,
            bus_factor=4,
            avg_health=85.0,
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "EXCELLENT" in output

    def test_fair_health(self):
        """Should show FAIR for avg_health >= 40."""
        from rich.console import Console

        from gh_stats.team_ui import render_team_summary

        result = render_team_summary(
            org_name="testorg",
            total_repos=5,
            total_contributors=10,
            total_commits=100,
            total_prs=20,
            total_issues=5,
            bus_factor=2,
            avg_health=50.0,
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "FAIR" in output

    def test_poor_health(self):
        """Should show POOR for avg_health >= 20."""
        from rich.console import Console

        from gh_stats.team_ui import render_team_summary

        result = render_team_summary(
            org_name="testorg",
            total_repos=5,
            total_contributors=10,
            total_commits=100,
            total_prs=20,
            total_issues=5,
            bus_factor=1,
            avg_health=30.0,
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "POOR" in output

    def test_critical_health(self):
        """Should show CRITICAL for avg_health < 20."""
        from rich.console import Console

        from gh_stats.team_ui import render_team_summary

        result = render_team_summary(
            org_name="testorg",
            total_repos=5,
            total_contributors=10,
            total_commits=100,
            total_prs=20,
            total_issues=5,
            bus_factor=1,
            avg_health=10.0,
        )
        console = Console()
        with console.capture() as capture:
            console.print(result)
        output = capture.get()

        assert "CRITICAL" in output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
