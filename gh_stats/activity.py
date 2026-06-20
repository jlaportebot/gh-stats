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
