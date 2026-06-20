# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Tests for the activity analysis module."""

import logging
from datetime import UTC, datetime

from gh_stats.activity import (
    _parse_dt,
    categorize_events,
    compute_activity_summary,
    compute_language_stats,
    compute_repo_stats,
)


class TestCategorizeEvents:
    """Tests for categorize_events."""

    def test_push_event(self):
        events = [
            {
                "id": "1",
                "type": "PushEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}, {"sha": "def"}]},
            }
        ]
        result = categorize_events(events)
        assert len(result) == 1
        assert result[0]["type"] == "push"
        assert result[0]["repo"] == "user/repo"
        assert "2 commits" in result[0]["detail"]

    def test_pr_event(self):
        events = [
            {
                "id": "2",
                "type": "PullRequestEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {
                    "action": "opened",
                    "pull_request": {"title": "Add feature", "number": 42},
                },
            }
        ]
        result = categorize_events(events)
        assert len(result) == 1
        assert result[0]["type"] == "pr"
        assert "#42" in result[0]["detail"]
        assert "Add feature" in result[0]["detail"]

    def test_issue_event(self):
        events = [
            {
                "id": "3",
                "type": "IssuesEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {
                    "action": "closed",
                    "issue": {"title": "Bug report", "number": 7},
                },
            }
        ]
        result = categorize_events(events)
        assert len(result) == 1
        assert result[0]["type"] == "issue"
        assert "Closed" in result[0]["detail"]

    def test_star_event(self):
        events = [
            {
                "id": "4",
                "type": "WatchEvent",
                "repo": {"name": "other/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"action": "started"},
            }
        ]
        result = categorize_events(events)
        assert len(result) == 1
        assert result[0]["type"] == "star"

    def test_release_event(self):
        events = [
            {
                "id": "5",
                "type": "ReleaseEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {
                    "release": {"tag_name": "v1.0.0"},
                },
            }
        ]
        result = categorize_events(events)
        assert len(result) == 1
        assert result[0]["type"] == "release"
        assert "v1.0.0" in result[0]["detail"]

    def test_skips_unknown_events(self):
        events = [
            {
                "id": "6",
                "type": "MemberEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {},
            }
        ]
        result = categorize_events(events)
        assert len(result) == 0

    def test_deduplication(self):
        events = [
            {
                "id": "7",
                "type": "PushEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}]},
            },
            {
                "id": "7",  # duplicate
                "type": "PushEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}]},
            },
        ]
        result = categorize_events(events)
        assert len(result) == 1

    def test_sorted_newest_first(self):
        events = [
            {
                "id": "8",
                "type": "PushEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-10T10:00:00Z",
                "payload": {"commits": [{"sha": "abc"}]},
            },
            {
                "id": "9",
                "type": "PushEvent",
                "repo": {"name": "user/repo"},
                "created_at": "2026-01-15T10:00:00Z",
                "payload": {"commits": [{"sha": "def"}]},
            },
        ]
        result = categorize_events(events)
        assert result[0]["time"] > result[1]["time"]


class TestComputeLanguageStats:
    """Tests for compute_language_stats."""

    def test_counts_non_fork_languages(self):
        repos = [
            {"language": "Python", "fork": False},
            {"language": "Python", "fork": False},
            {"language": "Rust", "fork": False},
            {"language": "Python", "fork": True},  # fork, should be excluded
            {"language": None, "fork": False},
        ]
        result = compute_language_stats(repos)
        assert result == {"Python": 2, "Rust": 1}

    def test_empty_repos(self):
        assert compute_language_stats([]) == {}


class TestComputeRepoStats:
    """Tests for compute_repo_stats."""

    def test_excludes_forks(self):
        repos = [
            {
                "full_name": "user/proj",
                "stargazers_count": 100,
                "forks_count": 20,
                "language": "Go",
                "description": "A project",
                "fork": False,
            },
            {
                "full_name": "user/forked",
                "stargazers_count": 50,
                "forks_count": 10,
                "language": "Python",
                "description": "A fork",
                "fork": True,
            },
        ]
        result = compute_repo_stats(repos)
        assert len(result) == 1
        assert result[0]["name"] == "user/proj"
        assert result[0]["stars"] == 100

    def test_sorted_by_stars(self):
        repos = [
            {
                "full_name": "user/small",
                "stargazers_count": 5,
                "forks_count": 0,
                "language": "Python",
                "description": "",
                "fork": False,
            },
            {
                "full_name": "user/big",
                "stargazers_count": 500,
                "forks_count": 50,
                "language": "Rust",
                "description": "Popular",
                "fork": False,
            },
        ]
        result = compute_repo_stats(repos)
        assert result[0]["name"] == "user/big"
        assert result[1]["name"] == "user/small"


class TestComputeActivitySummary:
    """Tests for compute_activity_summary."""

    def test_counts_by_type(self):
        activities = [
            {"type": "push", "repo": "a/b", "time": datetime.now(UTC), "detail": ""},
            {"type": "push", "repo": "a/b", "time": datetime.now(UTC), "detail": ""},
            {"type": "pr", "repo": "c/d", "time": datetime.now(UTC), "detail": ""},
        ]
        result = compute_activity_summary(activities)
        assert result == {"push": 2, "pr": 1}

    def test_empty_activities(self):
        assert compute_activity_summary([]) == {}


class TestParseDt:
    """Tests for _parse_dt."""

    def test_valid_iso_string(self):
        result = _parse_dt("2026-01-15T10:30:00Z")
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 15

    def test_valid_iso_with_offset(self):
        result = _parse_dt("2026-01-15T10:30:00+05:00")
        assert result.year == 2026

    def test_invalid_string_falls_back_to_now(self):
        result = _parse_dt("not-a-date")
        # Should return a datetime (current UTC), not raise
        assert isinstance(result, datetime)

    def test_invalid_string_logs_warning(self, caplog):
        with caplog.at_level(logging.WARNING, logger="gh_stats"):
            _parse_dt("garbage")
        assert "Failed to parse datetime" in caplog.text

    def test_empty_string_falls_back(self):
        result = _parse_dt("")
        assert isinstance(result, datetime)


class TestComputeStreaks:
    """Tests for compute_streaks."""

    def test_current_streak_empty(self):
        from gh_stats.activity import compute_streaks

        contributions = {}
        result = compute_streaks(contributions)
        assert result["current_streak"] == 0
        assert result["longest_streak"] == 0

    def test_current_streak_single_day(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date().isoformat()
        contributions = {today: 5}
        result = compute_streaks(contributions)
        assert result["current_streak"] == 1
        assert result["longest_streak"] == 1

    def test_current_streak_consecutive_days(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date()
        contributions = {
            (today - timedelta(days=0)).isoformat(): 3,
            (today - timedelta(days=1)).isoformat(): 2,
            (today - timedelta(days=2)).isoformat(): 1,
        }
        result = compute_streaks(contributions)
        assert result["current_streak"] == 3
        assert result["longest_streak"] == 3

    def test_current_streak_broken_by_gap(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date()
        contributions = {
            (today - timedelta(days=0)).isoformat(): 3,
            (today - timedelta(days=1)).isoformat(): 2,
            (today - timedelta(days=3)).isoformat(): 1,  # gap at day 2
        }
        result = compute_streaks(contributions)
        assert result["current_streak"] == 2  # today + yesterday
        assert result["longest_streak"] == 2

    def test_longest_streak_historical(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date()
        contributions = {
            # Current streak: 2 days
            (today - timedelta(days=0)).isoformat(): 3,
            (today - timedelta(days=1)).isoformat(): 2,
            # Gap
            # Historical streak: 5 days
            (today - timedelta(days=10)).isoformat(): 1,
            (today - timedelta(days=11)).isoformat(): 2,
            (today - timedelta(days=12)).isoformat(): 1,
            (today - timedelta(days=13)).isoformat(): 3,
            (today - timedelta(days=14)).isoformat(): 1,
        }
        result = compute_streaks(contributions)
        assert result["current_streak"] == 2
        assert result["longest_streak"] == 5

    def test_streak_ends_at_today(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date()
        # Streak ending yesterday (today has no contributions)
        contributions = {
            (today - timedelta(days=1)).isoformat(): 3,
            (today - timedelta(days=2)).isoformat(): 2,
            (today - timedelta(days=3)).isoformat(): 1,
        }
        result = compute_streaks(contributions)
        assert result["current_streak"] == 0  # broken today
        assert result["longest_streak"] == 3

    def test_multiple_streaks_same_length(self):
        from datetime import UTC, datetime, timedelta

        from gh_stats.activity import compute_streaks

        today = datetime.now(UTC).date()
        contributions = {
            # Streak 1: 3 days
            (today - timedelta(days=0)).isoformat(): 1,
            (today - timedelta(days=1)).isoformat(): 1,
            (today - timedelta(days=2)).isoformat(): 1,
            # Gap
            # Streak 2: 3 days
            (today - timedelta(days=10)).isoformat(): 1,
            (today - timedelta(days=11)).isoformat(): 1,
            (today - timedelta(days=12)).isoformat(): 1,
        }
        result = compute_streaks(contributions)
        assert result["current_streak"] == 3
        assert result["longest_streak"] == 3
