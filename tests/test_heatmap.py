# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for activity heatmap computation."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from gh_stats.heatmap import compute_activity_heatmap


def _iso(days_ago: int) -> str:
    """Return ISO format string for a date N days ago."""
    return (datetime.now(UTC) - timedelta(days=days_ago)).isoformat()


class TestComputeActivityHeatmap:
    """Tests for compute_activity_heatmap."""

    def test_empty_events(self):
        result = compute_activity_heatmap([])
        assert result["total_contributions"] == 0
        assert result["max_count"] == 0
        assert result["longest_streak"] == 0
        assert len(result["grid"]) > 0

    def test_single_event(self):
        events = [{"created_at": _iso(5)}]
        result = compute_activity_heatmap(events, days=30)
        assert result["total_contributions"] == 1
        assert result["max_count"] == 1

    def test_multiple_events_same_day(self):
        today = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
        events = [{"created_at": today}] * 5
        result = compute_activity_heatmap(events, days=30)
        assert result["total_contributions"] == 5
        assert result["max_count"] == 5

    def test_streak_computation(self):
        # 5 consecutive days of events
        events = [{"created_at": _iso(i)} for i in range(5)]
        result = compute_activity_heatmap(events, days=30)
        assert result["longest_streak"] >= 4  # At least 4 days in a row

    def test_best_day(self):
        # 1 event at day 10, 5 events at day 5
        events = [{"created_at": _iso(10)}] + [{"created_at": _iso(5)}] * 5
        result = compute_activity_heatmap(events, days=30)
        assert result["best_day_count"] == 5

    def test_month_labels(self):
        events = [{"created_at": _iso(i)} for i in range(0, 90, 5)]
        result = compute_activity_heatmap(events, days=120)
        assert len(result["month_labels"]) >= 2

    def test_weekly_totals(self):
        events = [{"created_at": _iso(i)} for i in range(30)]
        result = compute_activity_heatmap(events, days=60)
        assert len(result["weekly_totals"]) == len(result["grid"])
        assert sum(result["weekly_totals"]) == result["total_contributions"]

    def test_grid_structure(self):
        events = [{"created_at": _iso(i)} for i in range(14)]
        result = compute_activity_heatmap(events, days=30)
        # Each week should have up to 7 entries
        for week in result["grid"]:
            assert len(week) <= 7
            for day in week:
                assert "date" in day
                assert "count" in day

    def test_custom_days_parameter(self):
        events = [{"created_at": _iso(i)} for i in range(10)]
        result = compute_activity_heatmap(events, days=10)
        assert result["total_contributions"] >= 1

    def test_current_streak(self):
        # Events on last 3 days
        events = [
            {"created_at": _iso(0)},
            {"created_at": _iso(1)},
            {"created_at": _iso(2)},
        ]
        result = compute_activity_heatmap(events, days=30)
        assert result["current_streak"] >= 2
