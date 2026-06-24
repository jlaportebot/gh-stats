# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for HTML export functionality."""

from gh_stats.html_export import _render_comparison_html, _render_team_html


class TestRenderComparisonHTML:
    """Tests for _render_comparison_html."""

    def test_renders_basic_comparison(self):
        data = {
            "target_a": "user_a",
            "target_b": "user_b",
            "comparison_mode": "side_by_side",
            "stats_a": {"public_repos": 10, "followers": 100},
            "stats_b": {"public_repos": 5, "followers": 50},
            "total_contributions_a": 500,
            "total_contributions_b": 250,
            "activity_summary_a": {"push": 100, "pr": 20},
            "activity_summary_b": {"push": 50, "issue": 30},
            "streaks_a": {"current_streak": 10, "longest_streak": 30},
            "streaks_b": {"current_streak": 5, "longest_streak": 20},
            "patterns_a": {
                "by_weekday": {
                    "Mon": 10,
                    "Tue": 5,
                    "Wed": 3,
                    "Thu": 2,
                    "Fri": 8,
                    "Sat": 1,
                    "Sun": 0,
                },
                "most_active_day": "Mon",
                "peak_month": "Jan",
                "consistency_pct": 70.0,
            },
            "patterns_b": {
                "by_weekday": {
                    "Mon": 5,
                    "Tue": 3,
                    "Wed": 2,
                    "Thu": 1,
                    "Fri": 4,
                    "Sat": 0,
                    "Sun": 0,
                },
                "most_active_day": "Fri",
                "peak_month": "Feb",
                "consistency_pct": 50.0,
            },
            "growth_metrics": {
                "verdict": "📈 Moderate growth",
                "total_growth_pct": 25.0,
                "active_days_growth_pct": 15.0,
                "consistency_change_pct": 5.0,
            },
        }
        html = _render_comparison_html(data)
        assert "<!DOCTYPE html>" in html
        assert "user_a vs user_b" in html
        assert "gh-stats" in html
        assert "500" in html
        assert "250" in html
        assert "Moderate growth" in html
        assert "Total Contributions" in html
        assert "Contribution Patterns" in html
        assert "Activity Summary" in html

    def test_renders_time_period_mode(self):
        data = {
            "target_a": "octocat (2023)",
            "target_b": "octocat (2024)",
            "comparison_mode": "time_period",
            "stats_a": {"public_repos": 10},
            "stats_b": {"public_repos": 15},
            "total_contributions_a": 300,
            "total_contributions_b": 450,
            "activity_summary_a": {"push": 50},
            "activity_summary_b": {"push": 80},
            "streaks_a": {"current_streak": 5},
            "streaks_b": {"current_streak": 10},
            "patterns_a": {
                "by_weekday": {"Mon": 10},
                "most_active_day": "Mon",
                "peak_month": "Jan",
                "consistency_pct": 50.0,
            },
            "patterns_b": {
                "by_weekday": {"Mon": 15},
                "most_active_day": "Mon",
                "peak_month": "Jan",
                "consistency_pct": 70.0,
            },
            "growth_metrics": {
                "verdict": "🚀 Significant growth",
                "total_growth_pct": 50.0,
                "active_days_growth_pct": 20.0,
                "consistency_change_pct": 20.0,
            },
        }
        html = _render_comparison_html(data)
        assert "Time Period" in html
        assert "octocat (2023)" in html
        assert "octocat (2024)" in html
        assert "Significant growth" in html

    def test_renders_with_empty_data(self):
        data = {
            "target_a": "A",
            "target_b": "B",
            "comparison_mode": "side_by_side",
            "stats_a": {},
            "stats_b": {},
            "total_contributions_a": 0,
            "total_contributions_b": 0,
            "activity_summary_a": {},
            "activity_summary_b": {},
            "streaks_a": {},
            "streaks_b": {},
            "patterns_a": {},
            "patterns_b": {},
            "growth_metrics": {},
        }
        html = _render_comparison_html(data)
        assert "<!DOCTYPE html>" in html
        assert "A vs B" in html

    def test_renders_growth_classes(self):
        data = {
            "target_a": "A",
            "target_b": "B",
            "comparison_mode": "side_by_side",
            "stats_a": {"public_repos": 0, "followers": 0},
            "stats_b": {"public_repos": 0, "followers": 0},
            "total_contributions_a": 0,
            "total_contributions_b": 0,
            "activity_summary_a": {},
            "activity_summary_b": {},
            "streaks_a": {"current_streak": 0, "longest_streak": 0},
            "streaks_b": {"current_streak": 0, "longest_streak": 0},
            "patterns_a": {},
            "patterns_b": {},
            "growth_metrics": {
                "verdict": "⬇️ Significant decline",
                "total_growth_pct": -50.0,
                "active_days_growth_pct": -30.0,
                "consistency_change_pct": -10.0,
            },
        }
        html = _render_comparison_html(data)
        assert "growth-negative" in html
        assert "-50.0%" in html or "-50%" in html

    def test_includes_css_styles(self):
        data = {
            "target_a": "A",
            "target_b": "B",
            "comparison_mode": "side_by_side",
            "stats_a": {"public_repos": 1},
            "stats_b": {"public_repos": 1},
            "total_contributions_a": 1,
            "total_contributions_b": 1,
            "activity_summary_a": {},
            "activity_summary_b": {},
            "streaks_a": {"current_streak": 0, "longest_streak": 0},
            "streaks_b": {"current_streak": 0, "longest_streak": 0},
            "patterns_a": {},
            "patterns_b": {},
            "growth_metrics": {},
        }
        html = _render_comparison_html(data)
        assert "<style>" in html
        assert "font-family" in html
        assert "#0d1117" in html  # dark background
        assert "#58a6ff" in html  # accent color


class TestRenderTeamHTML:
    """Tests for _render_team_html."""

    def test_renders_basic_team_report(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 10,
                "total_contributors": 25,
                "total_commits": 500,
                "total_prs": 100,
                "total_issues": 50,
                "bus_factor": 3,
                "avg_health": 75.0,
            },
            "contributor_rankings": [
                {
                    "login": "user1",
                    "score": 150.0,
                    "commits": 50,
                    "prs_opened": 10,
                    "prs_merged": 8,
                    "reviews_given": 5,
                    "issues_opened": 3,
                    "issues_closed": 2,
                    "lines_added": 1000,
                    "lines_removed": 200,
                }
            ],
            "bus_factor": {
                "bus_factor": 3,
                "threshold_pct": 50.0,
                "top_contributors": [
                    {"login": "user1", "contributions": 100, "pct": 40.0},
                    {"login": "user2", "contributions": 50, "pct": 20.0},
                    {"login": "user3", "contributions": 40, "pct": 16.0},
                ],
                "coverage_pct": 76.0,
                "total_contributors": 10,
            },
            "repo_health": [
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
            ],
            "collaboration": {
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
            },
            "review_analytics": {
                "total_prs": 20,
                "prs_with_reviews": 15,
                "pct_prs_reviewed": 75.0,
                "avg_reviews_per_pr": 1.5,
                "approval_count": 10,
                "changes_requested_count": 3,
                "comment_only_count": 5,
                "avg_time_to_first_review_hours": 12.0,
                "median_time_to_first_review_hours": 8.0,
                "top_reviewers": [
                    {"login": "reviewer1", "reviews": 8},
                    {"login": "reviewer2", "reviews": 5},
                ],
            },
        }
        html = _render_team_html(data)
        assert "<!DOCTYPE html>" in html
        assert "Team Analytics: myorg" in html
        assert "10" in html  # repos
        assert "25" in html  # contributors
        assert "75.0" in html  # avg health
        assert "user1" in html
        assert "150" in html  # score
        assert "Bus Factor" in html
        assert "3" in html  # bus factor value
        assert "MEDIUM" in html  # risk level for bf=3
        assert "repo1" in html
        assert "healthy" in html
        assert "Collaboration Network" in html
        assert "Code Review Analytics" in html

    def test_renders_with_year(self):
        data = {
            "target_name": "myorg",
            "year": 2024,
            "summary": {
                "total_repos": 5,
                "total_contributors": 10,
                "total_commits": 100,
                "total_prs": 20,
                "total_issues": 10,
                "bus_factor": 2,
                "avg_health": 60.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 2, "threshold_pct": 50.0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
        }
        html = _render_team_html(data)
        assert "2024" in html

    def test_empty_bus_factor(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 0,
                "total_contributors": 0,
                "total_commits": 0,
                "total_prs": 0,
                "total_issues": 0,
                "bus_factor": 0,
                "avg_health": 0.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 0, "threshold_pct": 50.0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
        }
        html = _render_team_html(data)
        assert "Insufficient data" in html

    def test_includes_team_css(self):
        data = {
            "target_name": "x",
            "year": None,
            "summary": {
                "total_repos": 0,
                "total_contributors": 0,
                "total_commits": 0,
                "total_prs": 0,
                "total_issues": 0,
                "bus_factor": 0,
                "avg_health": 0.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
        }
        html = _render_team_html(data)
        assert "<style>" in html
        assert "health-bar" in html
        assert "risk-critical" in html or "risk-low" in html  # CSS classes present

    def test_critical_bus_factor(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 1,
                "total_contributors": 1,
                "total_commits": 10,
                "total_prs": 0,
                "total_issues": 0,
                "bus_factor": 1,
                "avg_health": 50.0,
            },
            "contributor_rankings": [],
            "bus_factor": {
                "bus_factor": 1,
                "threshold_pct": 50.0,
                "top_contributors": [{"login": "user1", "contributions": 10, "pct": 100.0}],
                "coverage_pct": 100.0,
                "total_contributors": 1,
            },
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
        }
        html = _render_team_html(data)
        assert "CRITICAL" in html

    def test_review_outcomes(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 1,
                "total_contributors": 1,
                "total_commits": 10,
                "total_prs": 5,
                "total_issues": 0,
                "bus_factor": 1,
                "avg_health": 50.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 1, "threshold_pct": 50.0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {
                "total_prs": 5,
                "prs_with_reviews": 4,
                "pct_prs_reviewed": 80.0,
                "avg_reviews_per_pr": 2.0,
                "approval_count": 5,
                "changes_requested_count": 2,
                "comment_only_count": 1,
                "avg_time_to_first_review_hours": 6.0,
                "median_time_to_first_review_hours": 4.0,
                "top_reviewers": [{"login": "rev1", "reviews": 3}],
            },
        }
        html = _render_team_html(data)
        assert "Approvals" in html
        assert "Changes Requested" in html
        assert "Comments Only" in html
        assert "rev1" in html

    def test_trends_section_included(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 1,
                "total_contributors": 1,
                "total_commits": 10,
                "total_prs": 5,
                "total_issues": 0,
                "bus_factor": 1,
                "avg_health": 50.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 1, "threshold_pct": 50.0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
            "trends": {
                "period_labels": ["P1", "P2", "P3"],
                "metrics": {
                    "commits": [5, 10, 15],
                    "prs_opened": [1, 2, 3],
                    "prs_merged": [0, 1, 2],
                    "issues_opened": [3, 2, 1],
                    "issues_closed": [1, 1, 2],
                },
                "trends": {
                    "commits": "increasing",
                    "prs_merged": "increasing",
                    "issues_closed": "stable",
                },
                "top_authors": [
                    {"login": "alice", "total": 20, "per_period": [5, 8, 7]},
                ],
            },
        }
        html = _render_team_html(data)
        assert "Activity Trends" in html
        assert "Increasing" in html
        assert "P1" in html
        assert "alice" in html

    def test_empty_trends_section(self):
        data = {
            "target_name": "myorg",
            "year": None,
            "summary": {
                "total_repos": 0,
                "total_contributors": 0,
                "total_commits": 0,
                "total_prs": 0,
                "total_issues": 0,
                "bus_factor": 0,
                "avg_health": 0.0,
            },
            "contributor_rankings": [],
            "bus_factor": {"bus_factor": 0},
            "repo_health": [],
            "collaboration": {"nodes": [], "edges": [], "total_collaborations": 0},
            "review_analytics": {"total_prs": 0},
            "trends": {},
        }
        html = _render_team_html(data)
        assert "No trend data" in html
