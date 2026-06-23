# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team analytics — compute team/organization metrics from GitHub data."""

from __future__ import annotations

import logging
from collections import Counter, defaultdict
from datetime import UTC, datetime, timedelta
from operator import itemgetter
from typing import Any

logger = logging.getLogger("gh_stats")


# ---------------------------------------------------------------------------
# Contributor rankings
# ---------------------------------------------------------------------------


def compute_contributor_rankings(
    contributors: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    reviews: dict[int, list[dict[str, Any]]],
    issues: list[dict[str, Any]],
    *,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """Compute comprehensive contributor rankings from multiple data sources.

    Args:
        contributors: List from get_repo_contributors.
        commits: List from get_repo_commits.
        prs: List from get_repo_pull_requests.
        reviews: Dict mapping PR number to list of reviews from get_pull_request_reviews.
        issues: List from get_repo_issues.
        top_n: Number of top contributors to return.

    Returns:
        List of contributor dicts sorted by total score descending.
    """
    # Aggregate stats per contributor
    stats: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "login": "",
            "avatar_url": "",
            "commits": 0,
            "prs_opened": 0,
            "prs_merged": 0,
            "prs_reviewed": 0,
            "reviews_given": 0,
            "issues_opened": 0,
            "issues_closed": 0,
            "lines_added": 0,
            "lines_removed": 0,
        }
    )

    # From contributors API
    for c in contributors:
        login = c.get("login", "")
        if login:
            stats[login]["login"] = login
            stats[login]["avatar_url"] = c.get("avatar_url", "")
            stats[login]["contributor_api_count"] = c.get("contributions", 0)

    # From commits
    for commit in commits:
        author = commit.get("author") or {}
        login = author.get("login") or commit.get("commit", {}).get("author", {}).get("name", "")
        if login:
            stats[login]["login"] = login
            stats[login]["commits"] += 1
            # Commit stats (if available)
            commit_stats = commit.get("stats")
            if commit_stats:
                stats[login]["lines_added"] += commit_stats.get("additions", 0)
                stats[login]["lines_removed"] += commit_stats.get("deletions", 0)

    # From PRs
    for pr in prs:
        author = pr.get("user") or {}
        login = author.get("login", "")
        if login:
            stats[login]["login"] = login
            stats[login]["prs_opened"] += 1
            if pr.get("merged_at"):
                stats[login]["prs_merged"] += 1

    # From reviews
    for pr_reviews in reviews.values():
        for review in pr_reviews:
            reviewer = review.get("user") or {}
            login = reviewer.get("login", "")
            if login:
                stats[login]["login"] = login
                stats[login]["reviews_given"] += 1
                if review.get("state") in {"APPROVED", "CHANGES_REQUESTED", "COMMENTED"}:
                    stats[login]["prs_reviewed"] += 1

    # From issues
    for issue in issues:
        author = issue.get("user") or {}
        login = author.get("login", "")
        if login:
            stats[login]["login"] = login
            stats[login]["issues_opened"] += 1
            if issue.get("state") == "closed":
                stats[login]["issues_closed"] += 1

    # Compute composite score
    # Weight: commits=1, PRs opened=5, PRs merged=10, reviews=3, issues=2, lines=0.001
    for data in stats.values():
        score = (
            data["commits"] * 1
            + data["prs_opened"] * 5
            + data["prs_merged"] * 10
            + data["reviews_given"] * 3
            + data["issues_opened"] * 2
            + data["issues_closed"] * 2
            + (data["lines_added"] + data["lines_removed"]) * 0.001
        )
        data["score"] = round(score, 2)
        data["total_contributions"] = (
            data["commits"]
            + data["prs_opened"]
            + data["prs_merged"]
            + data["reviews_given"]
            + data["issues_opened"]
            + data["issues_closed"]
        )

    # Sort by score descending
    ranked = sorted(stats.values(), key=itemgetter("score"), reverse=True)
    return ranked[:top_n]


# ---------------------------------------------------------------------------
# Bus factor computation
# ---------------------------------------------------------------------------


def compute_bus_factor(
    contributors: list[dict[str, Any]],
    commits: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    *,
    threshold_pct: float = 50.0,
) -> dict[str, Any]:
    """Calculate the bus factor: minimum number of contributors who account for threshold% of work.

    Args:
        contributors: List from get_repo_contributors.
        commits: List from get_repo_commits.
        prs: List from get_repo_pull_requests.
        threshold_pct: Percentage of total work that defines the bus factor (default 50%).

    Returns:
        Dict with bus_factor, threshold_pct, top_contributors, and coverage_pct.
    """
    # Aggregate contributions per author
    work_counts: Counter[str] = Counter()

    # Contributors API gives contribution counts
    for c in contributors:
        login = c.get("login", "")
        if login:
            work_counts[login] += c.get("contributions", 0)

    # Commits
    for commit in commits:
        author = commit.get("author") or {}
        login = author.get("login") or commit.get("commit", {}).get("author", {}).get("name", "")
        if login:
            work_counts[login] += 1

    for pr in prs:
        author = pr.get("user") or {}
        login = author.get("login", "")
        if login:
            work_counts[login] += 1
            if pr.get("merged_at"):
                work_counts[login] += 1

    if not work_counts:
        return {
            "bus_factor": 0,
            "threshold_pct": threshold_pct,
            "top_contributors": [],
            "coverage_pct": 0.0,
            "total_contributors": 0,
        }

    total_work = sum(work_counts.values())
    sorted_contributors = work_counts.most_common()

    cumulative = 0
    bus_factor = 0
    top_contributors = []

    for login, count in sorted_contributors:
        cumulative += count
        bus_factor += 1
        pct = round(count / total_work * 100, 1)
        top_contributors.append({"login": login, "contributions": count, "pct": pct})
        if cumulative / total_work * 100 >= threshold_pct:
            break

    coverage_pct = round(cumulative / total_work * 100, 1)
    return {
        "bus_factor": bus_factor,
        "threshold_pct": threshold_pct,
        "top_contributors": top_contributors,
        "coverage_pct": coverage_pct,
        "total_contributors": len(work_counts),
    }


# ---------------------------------------------------------------------------
# Repository health scoring
# ---------------------------------------------------------------------------


def compute_repo_health_scores(
    repos: list[dict[str, Any]],
    repo_commits: dict[str, list[dict[str, Any]]],
    repo_prs: dict[str, list[dict[str, Any]]],
    repo_issues: dict[str, list[dict[str, Any]]],
    repo_contributors: dict[str, list[dict[str, Any]]],
    *,
    top_n: int = 20,
) -> list[dict[str, Any]]:
    """Score repositories by activity, maintenance, and community health.

    Args:
        repos: List of repo dicts from get_org_repos.
        repo_commits: Dict mapping repo name to commits list.
        repo_prs: Dict mapping repo name to PRs list.
        repo_issues: Dict mapping repo name to issues list.
        repo_contributors: Dict mapping repo name to contributors list.
        top_n: Number of top repos to return.

    Returns:
        List of repo health dicts sorted by health score descending.
    """
    results = []

    for repo in repos:
        name = repo.get("name", "")
        if not name:
            continue

        full_name = repo.get("full_name", name)
        is_fork = repo.get("fork", False)
        is_archived = repo.get("archived", False)
        is_disabled = repo.get("disabled", False)

        commits = repo_commits.get(name, [])
        prs = repo_prs.get(name, [])
        issues = repo_issues.get(name, [])
        contributors = repo_contributors.get(name, [])

        # Skip archived/disabled unless explicitly requested
        if is_archived or is_disabled:
            results.append({
                "name": name,
                "full_name": full_name,
                "health_score": 0,
                "status": "archived" if is_archived else "disabled",
                "is_fork": is_fork,
                "language": repo.get("language"),
                "stars": repo.get("stargazers_count", 0),
                "open_issues": repo.get("open_issues_count", 0),
                "last_push": repo.get("pushed_at", ""),
                "contributors_count": len(contributors),
                "commits_30d": 0,
                "prs_open": 0,
                "prs_merged_30d": 0,
                "issues_open": 0,
                "issues_closed_30d": 0,
            })
            continue

        # Time windows
        now = datetime.now(UTC)
        thirty_days_ago = (now - timedelta(days=30)).isoformat()

        # Recent activity
        def _is_recent_commit(c: dict[str, Any], cutoff: str) -> bool:
            return c.get("commit", {}).get("author", {}).get("date", "") >= cutoff

        recent_commits = [c for c in commits if _is_recent_commit(c, thirty_days_ago)]
        recent_prs_merged = [
            pr for pr in prs if pr.get("merged_at") and pr["merged_at"] >= thirty_days_ago
        ]
        recent_issues_closed = [
            i for i in issues if i.get("closed_at") and i["closed_at"] >= thirty_days_ago
        ]

        open_prs = [pr for pr in prs if pr.get("state") == "open"]
        open_issues = [i for i in issues if i.get("state") == "open"]

        # Health scoring (0-100)
        # Activity: recent commits (max 30), recent PRs merged (max 20),
        # recent issues closed (max 15)
        activity_score = (
            min(len(recent_commits), 30)
            + min(len(recent_prs_merged) * 2, 20)
            + min(len(recent_issues_closed), 15)
        )

        # Maintenance: low open PRs (max 15), low open issues (max 10), recent push (max 10)
        maintenance_score = max(0, 15 - len(open_prs)) + max(0, 10 - len(open_issues) // 2)
        pushed_at = repo.get("pushed_at", "")
        if pushed_at:
            try:
                push_date = datetime.fromisoformat(pushed_at)
                if (now - push_date).days <= 30:
                    maintenance_score += 10
                elif (now - push_date).days <= 90:
                    maintenance_score += 5
            except (ValueError, AttributeError):
                pass

        # Community: number of contributors (max 15), has license (5),
        # has topics (5), stars (max 10)
        community_score = min(len(contributors), 15)
        if repo.get("license"):
            community_score += 5
        if repo.get("topics"):
            community_score += 5
        community_score += min(repo.get("stargazers_count", 0) // 10, 10)

        # Size penalty for huge repos with low activity
        size = repo.get("size", 0)
        size_penalty = 0
        if size > 10000 and len(recent_commits) < 5:
            size_penalty = 10

        health_score = max(
            0, min(100, activity_score + maintenance_score + community_score - size_penalty)
        )

        # Status label
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 50:
            status = "moderate"
        elif health_score >= 25:
            status = "declining"
        else:
            status = "stale"

        results.append({
            "name": name,
            "full_name": full_name,
            "health_score": health_score,
            "status": status,
            "is_fork": is_fork,
            "language": repo.get("language"),
            "stars": repo.get("stargazers_count", 0),
            "open_issues": len(open_issues),
            "last_push": pushed_at,
            "contributors_count": len(contributors),
            "commits_30d": len(recent_commits),
            "prs_open": len(open_prs),
            "prs_merged_30d": len(recent_prs_merged),
            "issues_open": len(open_issues),
            "issues_closed_30d": len(recent_issues_closed),
        })

    # Sort by health score descending
    results.sort(key=itemgetter("health_score"), reverse=True)
    return results[:top_n]


# ---------------------------------------------------------------------------
# Collaboration matrix
# ---------------------------------------------------------------------------


def compute_collaboration_matrix(
    commits: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    reviews: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Build a collaboration network from commits, PRs, and reviews.

    Returns:
        Dict with "nodes" (contributors) and "edges" (collaboration strength).
    """
    # Count direct collaborations
    # Two people collaborate if: one reviews other's PR, or they co-author commits, etc.
    collaboration_counts: Counter[tuple[str, str]] = Counter()
    all_contributors: set[str] = set()

    # From PR reviews: reviewer -> PR author
    for pr in prs:
        pr_num = pr.get("number")
        author = pr.get("user", {}).get("login", "")
        if not author or pr_num is None:
            continue
        all_contributors.add(author)
        for review in reviews.get(pr_num, []):
            reviewer = review.get("user", {}).get("login", "")
            if reviewer and reviewer != author:
                all_contributors.add(reviewer)
                edge = tuple(sorted([author, reviewer]))
                collaboration_counts[edge] += 1

    # From commits: co-authors (GitHub doesn't expose co-authors easily via REST API)
    # We'll use commit author as a proxy - people who commit to same repo
    # This is a simplified approach
    commit_authors: list[str] = []
    for commit in commits:
        author = commit.get("author") or {}
        login = author.get("login") or commit.get("commit", {}).get("author", {}).get("name", "")
        if login:
            commit_authors.append(login)
            all_contributors.add(login)

    # Add edges for people who committed in same period (simplified)
    # In a real implementation, we'd look at co-authored-by trailers
    author_counts = Counter(commit_authors)

    # Build nodes
    nodes = [
        {
            "login": login,
            "commit_count": author_counts.get(login, 0),
            "pr_count": sum(1 for pr in prs if pr.get("user", {}).get("login") == login),
        }
        for login in sorted(all_contributors)
    ]

    # Build edges
    edges = []
    for (a, b), count in collaboration_counts.most_common():
        edges.append({"source": a, "target": b, "weight": count})

    return {
        "nodes": nodes,
        "edges": edges,
        "total_collaborations": sum(collaboration_counts.values()),
    }


# ---------------------------------------------------------------------------
# Review analytics
# ---------------------------------------------------------------------------


def compute_review_analytics(
    prs: list[dict[str, Any]],
    reviews: dict[int, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Analyze code review patterns and metrics.

    Returns:
        Dict with review statistics and patterns.
    """
    total_prs = len(prs)
    prs_with_reviews = 0
    total_reviews = 0
    approval_count = 0
    changes_requested = 0
    comment_only = 0

    review_times: list[float] = []  # hours from PR creation to first review
    reviewer_counts: Counter[str] = Counter()

    for pr in prs:
        pr_num = pr.get("number")
        created_at = pr.get("created_at", "")
        if pr_num is None:
            continue
        pr_reviews = reviews.get(pr_num, [])

        if pr_reviews:
            prs_with_reviews += 1
            total_reviews += len(pr_reviews)

            # Time to first review
            first_review = min(pr_reviews, key=lambda r: r.get("submitted_at", ""))
            first_review_time = first_review.get("submitted_at", "")
            if created_at and first_review_time:
                try:
                    created = datetime.fromisoformat(created_at)
                    reviewed = datetime.fromisoformat(first_review_time)
                    hours = (reviewed - created).total_seconds() / 3600
                    if hours >= 0:
                        review_times.append(hours)
                except (ValueError, AttributeError):
                    pass

            for review in pr_reviews:
                state = review.get("state", "")
                reviewer = review.get("user", {}).get("login", "")
                if reviewer:
                    reviewer_counts[reviewer] += 1
                if state == "APPROVED":
                    approval_count += 1
                elif state == "CHANGES_REQUESTED":
                    changes_requested += 1
                elif state == "COMMENTED":
                    comment_only += 1

    # Compute averages
    avg_reviews_per_pr = total_reviews / total_prs if total_prs > 0 else 0
    pct_prs_reviewed = (prs_with_reviews / total_prs * 100) if total_prs > 0 else 0
    avg_time_to_first_review = sum(review_times) / len(review_times) if review_times else 0
    if review_times:
        sorted_times = sorted(review_times)
        median_time_to_first_review = sorted_times[len(sorted_times) // 2]
    else:
        median_time_to_first_review = 0

    # Top reviewers
    top_reviewers = [
        {"login": login, "reviews": count} for login, count in reviewer_counts.most_common(10)
    ]

    return {
        "total_prs": total_prs,
        "prs_with_reviews": prs_with_reviews,
        "pct_prs_reviewed": round(pct_prs_reviewed, 1),
        "total_reviews": total_reviews,
        "avg_reviews_per_pr": round(avg_reviews_per_pr, 1),
        "approval_count": approval_count,
        "changes_requested_count": changes_requested,
        "comment_only_count": comment_only,
        "avg_time_to_first_review_hours": round(avg_time_to_first_review, 1),
        "median_time_to_first_review_hours": round(median_time_to_first_review, 1),
        "top_reviewers": top_reviewers,
    }
