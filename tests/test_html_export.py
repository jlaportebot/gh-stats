# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for HTML export functionality."""

from gh_stats.html_export import _render_comparison_html


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
