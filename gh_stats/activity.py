"""Activity analysis — process raw GitHub events into structured activity data."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any


def categorize_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Turn raw GitHub events into a clean list of categorized activities.

    Returns list of dicts:
        {
            "type": str,        # push, pr, issue, review, release, etc.
            "repo": str,        # owner/repo
            "time": datetime,
            "detail": str,      # human-readable summary
        }
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
    activities.sort(key=lambda a: a["time"], reverse=True)
    return activities


def compute_language_stats(repos: list[dict[str, Any]]) -> dict[str, int]:
    """Compute language distribution from repos.

    Returns {language: repo_count}.
    """
    counter: Counter[str] = Counter()
    for repo in repos:
        lang = repo.get("language")
        if lang and not repo.get("fork", False):
            counter[lang] += 1
    return dict(counter.most_common())


def compute_repo_stats(repos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Summarize top repos by stars/forks.

    Returns list of dicts sorted by stars desc:
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
    result.sort(key=lambda r: r["stars"], reverse=True)
    return result


def compute_activity_summary(activities: list[dict[str, Any]]) -> dict[str, int]:
    """Count activities by type.

    Returns {type: count}.
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
    """Parse a single event into a structured activity dict."""

    if event_type == "PushEvent":
        commits = payload.get("payload", {}).get("commits", [])
        count = len(commits)
        detail = f"Pushed {count} commit{'s' if count != 1 else ''}"
        return {"type": "push", "repo": repo, "time": time, "detail": detail}

    if event_type == "PullRequestEvent":
        pr = payload.get("payload", {}).get("pull_request", {})
        action = payload.get("payload", {}).get("action", "")
        title = pr.get("title", "")
        number = pr.get("number", "")
        if number:
            detail = f"{action.capitalize()} PR #{number}: {title}"
        else:
            detail = f"{action.capitalize()} PR: {title}"
        return {"type": "pr", "repo": repo, "time": time, "detail": detail}

    if event_type == "IssuesEvent":
        issue = payload.get("payload", {}).get("issue", {})
        action = payload.get("payload", {}).get("action", "")
        title = issue.get("title", "")
        number = issue.get("number", "")
        if number:
            detail = f"{action.capitalize()} issue #{number}: {title}"
        else:
            detail = f"{action.capitalize()} issue: {title}"
        return {"type": "issue", "repo": repo, "time": time, "detail": detail}

    if event_type == "PullRequestReviewEvent":
        pr = payload.get("payload", {}).get("pull_request", {})
        title = pr.get("title", "")
        detail = f"Reviewed PR: {title}"
        return {"type": "review", "repo": repo, "time": time, "detail": detail}

    if event_type == "ReleaseEvent":
        release = payload.get("payload", {}).get("release", {})
        tag = release.get("tag_name", "")
        detail = f"Published release {tag}"
        return {"type": "release", "repo": repo, "time": time, "detail": detail}

    if event_type == "WatchEvent":
        return {"type": "star", "repo": repo, "time": time, "detail": "Starred repository"}

    if event_type == "ForkEvent":
        return {"type": "fork", "repo": repo, "time": time, "detail": "Forked repository"}

    if event_type == "CreateEvent":
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

    if event_type == "DeleteEvent":
        ref_type = payload.get("payload", {}).get("ref_type", "")
        ref = payload.get("payload", {}).get("ref", "")
        detail = f"Deleted {ref_type} {ref}" if ref else f"Deleted {ref_type}"
        return {"type": "delete", "repo": repo, "time": time, "detail": detail}

    if event_type == "IssueCommentEvent":
        issue = payload.get("payload", {}).get("issue", {})
        title = issue.get("title", "")
        number = issue.get("number", "")
        if number:
            detail = f"Commented on issue #{number}: {title}"
        else:
            detail = f"Commented on issue: {title}"
        return {"type": "comment", "repo": repo, "time": time, "detail": detail}

    if event_type == "CommitCommentEvent":
        return {"type": "comment", "repo": repo, "time": time, "detail": "Commented on commit"}

    # Skip MemberEvent, PublicEvent, GollumEvent, etc.
    return None


def _parse_dt(dt_str: str) -> datetime:
    """Parse an ISO 8601 datetime string."""
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return datetime.now(timezone.utc)
