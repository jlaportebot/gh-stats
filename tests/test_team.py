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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
