# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Activity analysis — process raw GitHub events into structured activity data."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime, timedelta
from operator import itemgetter
from typing import Any

logger = logging.getLogger("gh_stats")


def categorize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn raw GitHub events into a clean list of categorized activities.

    Returns:
        List of activity dicts with keys:
            "type": str  # push, pr, issue, review, release, etc.
            "repo": str  # owner/repo
            "time": datetime
            "detail": str  # human-readable summary
    """
    activities: list[dict[str, Any]] = []
    seen = set()

    for event in events:
        event_id = event.get("id", "")
        if event_id in seen:
            continue
        seen.add(event_id)

        event_type = event.get("type", "")
        repo_name = event.get("repo", {}).get("name", "unknown")
        created_at = _parse_dt(event.get("created_at", ""))

        activity = _parse_event(event_type, repo_name, created_at, event)
        if activity:
            activities.append(activity)

    # Sort newest first
    activities.sort(key=itemgetter("time"), reverse=True)
    return activities


def compute_language_stats(repos: list[dict[str, Any]]) -> dict[str, int]:
    """Compute language distribution from repos.

    Returns:
        {language: repo_count}.
    """
    counter: Counter[str] = Counter()
    for repo in repos:
        lang = repo.get("language")
        if lang and not repo.get("fork", False):
            counter[lang] += 1
    return dict(counter.most_common())


def compute_repo_stats(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize top repos by stars/forks.

    Returns:
        list of dicts sorted by stars desc:
        {
            "name": str,
            "stars": int,
            "forks": int,
            "language": str,
            "description": str,
        }
    """
    result = []
    for repo in repos:
        if repo.get("fork", False):
            continue
        result.append({
            "name": repo.get("full_name", repo.get("name", "")),
            "stars": repo.get("stargazers_count", 0),
            "forks": repo.get("forks_count", 0),
            "language": repo.get("language") or "—",
            "description": (repo.get("description") or "")[:80],
        })
    result.sort(key=itemgetter("stars"), reverse=True)
    return result


def compute_activity_summary(activities: list[dict[str, Any]]) -> dict[str, int]:
    """Count activities by type.

    Returns:
        {type: count}.
    """
    counter: Counter[str] = Counter()
    for a in activities:
        counter[a["type"]] += 1
    return dict(counter)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _parse_event(
    event_type: str, repo: str, time: datetime, payload: dict[str, Any]
) -> dict[str, Any] | None:
    """Parse a single event into a structured activity dict.

    Returns:
        Activity dict or None if event type is not recognized.
    """
    handlers = {
        "PushEvent": _parse_push_event,
        "PullRequestEvent": _parse_pr_event,
        "IssuesEvent": _parse_issues_event,
        "PullRequestReviewEvent": _parse_review_event,
        "ReleaseEvent": _parse_release_event,
        "WatchEvent": _parse_watch_event,
        "ForkEvent": _parse_fork_event,
        "CreateEvent": _parse_create_event,
        "DeleteEvent": _parse_delete_event,
        "IssueCommentEvent": _parse_issue_comment_event,
        "CommitCommentEvent": _parse_commit_comment_event,
    }

    handler = handlers.get(event_type)
    if handler:
        return handler(repo, time, payload)
    return None


def _parse_push_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    commits = payload.get("payload", {}).get("commits", [])
    count = len(commits)
    detail = f"Pushed {count} commit{'s' if count != 1 else ''}"
    return {"type": "push", "repo": repo, "time": time, "detail": detail}


def _parse_pr_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("payload", {}).get("pull_request", {})
    action = payload.get("payload", {}).get("action", "")
    title = pr.get("title", "")
    number = pr.get("number", "")
    if number:
        detail = f"{action.capitalize()} PR #{number}: {title}"
    else:
        detail = f"{action.capitalize()} PR: {title}"
    return {"type": "pr", "repo": repo, "time": time, "detail": detail}


def _parse_issues_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    issue = payload.get("payload", {}).get("issue", {})
    action = payload.get("payload", {}).get("action", "")
    title = issue.get("title", "")
    number = issue.get("number", "")
    if number:
        detail = f"{action.capitalize()} issue #{number}: {title}"
    else:
        detail = f"{action.capitalize()} issue: {title}"
    return {"type": "issue", "repo": repo, "time": time, "detail": detail}


def _parse_review_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    pr = payload.get("payload", {}).get("pull_request", {})
    title = pr.get("title", "")
    detail = f"Reviewed PR: {title}"
    return {"type": "review", "repo": repo, "time": time, "detail": detail}


def _parse_release_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    release = payload.get("payload", {}).get("release", {})
    tag = release.get("tag_name", "")
    detail = f"Published release {tag}"
    return {"type": "release", "repo": repo, "time": time, "detail": detail}


def _parse_watch_event(repo: str, time: datetime, _payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "star", "repo": repo, "time": time, "detail": "Starred repository"}


def _parse_fork_event(repo: str, time: datetime, _payload: dict[str, Any]) -> dict[str, Any]:
    return {"type": "fork", "repo": repo, "time": time, "detail": "Forked repository"}


def _parse_create_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    ref_type = payload.get("payload", {}).get("ref_type", "")
    ref = payload.get("payload", {}).get("ref", "")
    if ref_type == "repository":
        detail = "Created repository"
    elif ref_type == "branch":
        detail = f"Created branch {ref}"
    elif ref_type == "tag":
        detail = f"Created tag {ref}"
    else:
        detail = f"Created {ref_type}"
    return {"type": "create", "repo": repo, "time": time, "detail": detail}


def _parse_delete_event(repo: str, time: datetime, payload: dict[str, Any]) -> dict[str, Any]:
    ref_type = payload.get("payload", {}).get("ref_type", "")
    ref = payload.get("payload", {}).get("ref", "")
    detail = f"Deleted {ref_type} {ref}" if ref else f"Deleted {ref_type}"
    return {"type": "delete", "repo": repo, "time": time, "detail": detail}


def _parse_issue_comment_event(
    repo: str, time: datetime, payload: dict[str, Any]
) -> dict[str, Any]:
    issue = payload.get("payload", {}).get("issue", {})
    title = issue.get("title", "")
    number = issue.get("number", "")
    detail = f"Commented on issue #{number}: {title}" if number else f"Commented on issue: {title}"
    return {"type": "comment", "repo": repo, "time": time, "detail": detail}


def _parse_commit_comment_event(
    repo: str, time: datetime, _payload: dict[str, Any]
) -> dict[str, Any]:
    return {"type": "comment", "repo": repo, "time": time, "detail": "Commented on commit"}


def _parse_dt(dt_str: str) -> datetime:
    """Parse an ISO 8601 datetime string.

    Returns:
        Parsed datetime in UTC.
    """
    try:
        return datetime.fromisoformat(dt_str)
    except (ValueError, AttributeError):
        logger.warning("Failed to parse datetime %r, using current UTC time", dt_str)
        return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Streak computation
# ---------------------------------------------------------------------------


def compute_streaks(contributions: dict[str, int]) -> dict[str, int]:
    """Compute contribution streaks from daily contribution counts.

    Args:
        contributions: Dict mapping date strings (YYYY-MM-DD) to contribution counts.

    Returns:
        Dict with keys:
            - "current_streak": Consecutive days with contributions ending today.
            - "longest_streak": Longest consecutive streak in the history.
    """
    if not contributions:
        return {"current_streak": 0, "longest_streak": 0}

    # Parse dates and filter to only days with contributions
    contrib_dates = {
        datetime.fromisoformat(date_str).date()
        for date_str, count in contributions.items()
        if count > 0
    }

    if not contrib_dates:
        return {"current_streak": 0, "longest_streak": 0}

    today = datetime.now(UTC).date()
    sorted_dates = sorted(contrib_dates)

    # Compute all streaks
    streaks: list[int] = []
    current_streak_len = 1

    for i in range(1, len(sorted_dates)):
        if (sorted_dates[i] - sorted_dates[i - 1]).days == 1:
            current_streak_len += 1
        else:
            streaks.append(current_streak_len)
            current_streak_len = 1
    streaks.append(current_streak_len)

    longest_streak = max(streaks)

    # Compute current streak (must include today or yesterday)
    # Start from today and go backwards
    current_streak = 0
    check_date = today
    while check_date in contrib_dates:
        current_streak += 1
        check_date -= timedelta(days=1)

    return {"current_streak": current_streak, "longest_streak": longest_streak}


# ---------------------------------------------------------------------------
# Comparison computation
# ---------------------------------------------------------------------------


def compute_comparison_summary(
    activities_a: list[dict[str, Any]], activities_b: list[dict[str, Any]]
) -> dict[str, dict[str, int]]:
    """Compute side-by-side activity summaries for two targets.

    Args:
        activities_a: Activities for target A.
        activities_b: Activities for target B.

    Returns:
        Dict with keys "a" and "b", each mapping activity type to count.
    """
    counter_a: Counter[str] = Counter()
    counter_b: Counter[str] = Counter()

    for activity in activities_a:
        counter_a[activity["type"]] += 1
    for activity in activities_b:
        counter_b[activity["type"]] += 1

    return {"a": dict(counter_a), "b": dict(counter_b)}


# ---------------------------------------------------------------------------
# Contribution pattern analysis
# ---------------------------------------------------------------------------

_DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def compute_contribution_patterns(
    contributions: dict[str, int],
) -> dict[str, Any]:
    """Analyze contribution patterns by day-of-week and monthly distribution.

    Args:
        contributions: Dict mapping date strings (YYYY-MM-DD) to contribution counts.

    Returns:
        Dict with keys:
            - "by_weekday": { weekday_name: total_count }
            - "most_active_day": weekday name with highest total
            - "least_active_day": weekday name with lowest total
            - "by_month": { month_number: total_count }
            - "peak_month": month with highest total
            - "active_days": number of days with at least 1 contribution
            - "total_days": total number of days in contributions dict
            - "consistency_pct": percentage of days with contributions
            - "avg_per_active_day": average contributions on active days
            - "max_daily": maximum contributions on a single day
    """
    if not contributions:
        return {
            "by_weekday": {},
            "most_active_day": "",
            "least_active_day": "",
            "by_month": {},
            "peak_month": "",
            "active_days": 0,
            "total_days": 0,
            "consistency_pct": 0.0,
            "avg_per_active_day": 0.0,
            "max_daily": 0,
        }

    weekday_counts: dict[int, int] = {}
    month_counts: dict[int, int] = {}
    active_days = 0
    total_contrib = 0
    max_daily = 0

    for date_str, count in contributions.items():
        try:
            dt = datetime.fromisoformat(date_str)
        except (ValueError, AttributeError):
            continue

        # weekday(): 0=Mon, 6=Sun — matches _DAY_NAMES
        wd = dt.weekday()
        weekday_counts[wd] = weekday_counts.get(wd, 0) + count

        month = dt.month
        month_counts[month] = month_counts.get(month, 0) + count

        if count > 0:
            active_days += 1
            total_contrib += count
        max_daily = max(max_daily, count)

    total_days = len(contributions)
    consistency_pct = (active_days / total_days * 100) if total_days > 0 else 0.0
    avg_per_active = (total_contrib / active_days) if active_days > 0 else 0.0

    # Find most/least active days
    by_weekday = {_DAY_NAMES[wd]: count for wd, count in weekday_counts.items()}
    most_active = max(by_weekday, key=lambda k: by_weekday[k]) if by_weekday else ""
    least_active = min(by_weekday, key=lambda k: by_weekday[k]) if by_weekday else ""

    # Format months
    month_names = {
        1: "Jan",
        2: "Feb",
        3: "Mar",
        4: "Apr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Aug",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dec",
    }
    by_month = {month_names.get(m, str(m)): count for m, count in month_counts.items()}
    peak_month = max(by_month, key=lambda k: by_month[k]) if by_month else ""

    return {
        "by_weekday": by_weekday,
        "most_active_day": most_active,
        "least_active_day": least_active,
        "by_month": by_month,
        "peak_month": peak_month,
        "active_days": active_days,
        "total_days": total_days,
        "consistency_pct": round(consistency_pct, 1),
        "avg_per_active_day": round(avg_per_active, 1),
        "max_daily": max_daily,
    }


def compute_growth_metrics(
    contributions_a: dict[str, int],
    contributions_b: dict[str, int],
) -> dict[str, Any]:
    """Compute year-over-year growth metrics for two contribution periods.

    Compares total contributions, active days, peak month, and consistency
    between two periods (typically different years for the same target).

    Args:
        contributions_a: Earlier period contributions.
        contributions_b: Later period contributions.

    Returns:
        Dict with keys:
            - "total_growth_pct": percentage change in total contributions
            - "active_days_growth_pct": percentage change in active days
            - "consistency_change_pct": percentage point change in consistency
            - "avg_daily_change_pct": percentage change in avg per active day
            - "peak_month_a": peak month name for period A
            - "peak_month_b": peak month name for period B
            - "verdict": human-readable comparison verdict
    """
    patterns_a = compute_contribution_patterns(contributions_a)
    patterns_b = compute_contribution_patterns(contributions_b)

    total_a = sum(contributions_a.values())
    total_b = sum(contributions_b.values())

    def _pct_change(old: float, new: float) -> float:
        """Compute percentage change from old to new, avoiding division by zero.

        Returns:
            The percentage change as a float, or 0.0 / 100.0 if old is zero.
        """
        if old == 0:
            return 100.0 if new > 0 else 0.0
        return round((new - old) / old * 100, 1)

    total_growth = _pct_change(total_a, total_b)
    active_growth = _pct_change(float(patterns_a["active_days"]), float(patterns_b["active_days"]))
    consistency_change = round(patterns_b["consistency_pct"] - patterns_a["consistency_pct"], 1)
    avg_daily_change = _pct_change(
        patterns_a["avg_per_active_day"], patterns_b["avg_per_active_day"]
    )

    # Determine verdict
    if total_growth > 50:
        verdict = "🚀 Significant growth"
    elif total_growth > 10:
        verdict = "📈 Moderate growth"
    elif total_growth > -10:
        verdict = "➡️ Steady activity"
    elif total_growth > -30:
        verdict = "📉 Slight decline"
    else:
        verdict = "⬇️ Significant decline"

    return {
        "total_growth_pct": total_growth,
        "active_days_growth_pct": active_growth,
        "consistency_change_pct": consistency_change,
        "avg_daily_change_pct": avg_daily_change,
        "peak_month_a": patterns_a["peak_month"],
        "peak_month_b": patterns_b["peak_month"],
        "verdict": verdict,
    }
