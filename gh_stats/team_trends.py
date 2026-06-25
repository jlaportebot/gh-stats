# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team trends — compute period-over-period activity trends and comparisons for orgs."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


def compute_team_comparison(
    team_a: dict[str, Any],
    team_b: dict[str, Any],
    *,
    label_a: str = "Team A",
    label_b: str = "Team B",
) -> dict[str, Any]:
    """Compare two teams side by side.

    Args:
        team_a: Team data dict from team analytics (summary,
            contributor_rankings, repo_health, trends, bus_factor,
            review_analytics)
        team_b: Team data dict for second team
        label_a: Label for team A in output
        label_b: Label for team B in output

    Returns:
        Dict with comparison results including summary, contributors, repos,
        trends, bus_factor, reviews
    """
    summary_a = team_a.get("summary", {})
    summary_b = team_b.get("summary", {})

    # Summary comparison
    summary_keys = [
        "total_repos",
        "total_contributors",
        "total_commits",
        "total_prs",
        "total_issues",
        "bus_factor",
        "avg_health",
    ]
    summary_comparison = {}
    for key in summary_keys:
        val_a = summary_a.get(key, 0)
        val_b = summary_b.get(key, 0)
        if isinstance(val_a, float) or isinstance(val_b, float):
            diff = round(float(val_b) - float(val_a), 1)
        else:
            diff = int(val_b) - int(val_a)
        summary_comparison[key] = {"a": val_a, "b": val_b, "diff": diff}

    # Contributor comparison
    contributors_a = {c["login"]: c["score"] for c in team_a.get("contributor_rankings", [])}
    contributors_b = {c["login"]: c["score"] for c in team_b.get("contributor_rankings", [])}
    all_logins = set(contributors_a.keys()) | set(contributors_b.keys())
    contributors_comparison = []
    for login in sorted(all_logins):
        score_a = contributors_a.get(login, 0)
        score_b = contributors_b.get(login, 0)
        contributors_comparison.append({
            "login": login,
            "score_a": score_a,
            "score_b": score_b,
            "diff": score_b - score_a,
        })

    # Repo health comparison
    repos_a = {r["name"]: r["health_score"] for r in team_a.get("repo_health", [])}
    repos_b = {r["name"]: r["health_score"] for r in team_b.get("repo_health", [])}
    all_repo_names = set(repos_a.keys()) | set(repos_b.keys())
    repos_comparison = []
    for name in sorted(all_repo_names):
        score_a = repos_a.get(name, 0)
        score_b = repos_b.get(name, 0)
        repos_comparison.append({
            "name": name,
            "score_a": score_a,
            "score_b": score_b,
            "diff": score_b - score_a,
        })

    # Trends comparison
    trends_a = team_a.get("trends", {}).get("metrics", {})
    trends_b = team_b.get("trends", {}).get("metrics", {})
    all_metric_names = set(trends_a.keys()) | set(trends_b.keys())
    trends_comparison = {}
    for metric_name in all_metric_names:
        values_a = trends_a.get(metric_name, [])
        values_b = trends_b.get(metric_name, [])
        total_a = sum(values_a)
        total_b = sum(values_b)
        trend_a = team_a.get("trends", {}).get("trends", {}).get(metric_name, "stable")
        trend_b = team_b.get("trends", {}).get("trends", {}).get(metric_name, "stable")
        trends_comparison[metric_name] = {
            "total_a": total_a,
            "total_b": total_b,
            "diff": total_b - total_a,
            "trend_a": trend_a,
            "trend_b": trend_b,
        }

    # Bus factor comparison
    bf_a = team_a.get("bus_factor", {})
    bf_b = team_b.get("bus_factor", {})
    bus_factor_comparison = {
        "bus_factor_a": bf_a.get("bus_factor", 0),
        "bus_factor_b": bf_b.get("bus_factor", 0),
        "coverage_a": bf_a.get("coverage_pct", 0.0),
        "coverage_b": bf_b.get("coverage_pct", 0.0),
        "total_contributors_a": bf_a.get("total_contributors", 0),
        "total_contributors_b": bf_b.get("total_contributors", 0),
    }

    # Review comparison
    reviews_a = team_a.get("review_analytics", {})
    reviews_b = team_b.get("review_analytics", {})
    total_reviews_a = reviews_a.get("total_reviews", 1)
    total_reviews_b = reviews_b.get("total_reviews", 1)
    reviews_comparison = {
        "total_prs_a": reviews_a.get("total_prs", 0),
        "total_prs_b": reviews_b.get("total_prs", 0),
        "pct_reviewed_a": reviews_a.get("pct_prs_reviewed", 0.0),
        "pct_reviewed_b": reviews_b.get("pct_prs_reviewed", 0.0),
        "avg_reviews_a": reviews_a.get("avg_reviews_per_pr", 0.0),
        "avg_reviews_b": reviews_b.get("avg_reviews_per_pr", 0.0),
        "avg_time_a": reviews_a.get("avg_time_to_first_review_hours", 0.0),
        "avg_time_b": reviews_b.get("avg_time_to_first_review_hours", 0.0),
        "approval_rate_a": round(reviews_a.get("approval_count", 0) / total_reviews_a * 100, 1),
        "approval_rate_b": round(reviews_b.get("approval_count", 0) / total_reviews_b * 100, 1),
    }

    return {
        "label_a": label_a,
        "label_b": label_b,
        "summary": summary_comparison,
        "contributors": contributors_comparison,
        "repos": repos_comparison,
        "trends": trends_comparison,
        "bus_factor": bus_factor_comparison,
        "reviews": reviews_comparison,
    }


def compute_team_time_comparison(
    team_current: dict[str, Any],
    team_previous: dict[str, Any],
    *,
    label_current: str = "Current",
    label_previous: str = "Previous",
) -> dict[str, Any]:
    """Compare same team across two time periods.

    Args:
        team_current: Team data for current period
        team_previous: Team data for previous period
        label_current: Label for current period
        label_previous: Label for previous period

    Returns:
        Dict with growth rates and period-over-period comparison
    """
    # Start with side-by-side comparison
    comparison = compute_team_comparison(
        team_previous, team_current, label_a=label_previous, label_b=label_current
    )

    # Add growth rates to summary
    for val in comparison["summary"].values():
        a = val["a"]
        b = val["b"]
        if a == 0:
            growth = 100.0 if b > 0 else 0.0
        else:
            growth = round((b - a) / a * 100, 1)
        val["growth_pct"] = growth

    # Add growth rates to trends
    for trend in comparison["trends"].values():
        total_a = trend["total_a"]
        total_b = trend["total_b"]
        if total_a == 0:
            growth = 100.0 if total_b > 0 else 0.0
        else:
            growth = round((total_b - total_a) / total_a * 100, 1)
        trend["growth_pct"] = growth

    # Add review growth rates
    reviews = comparison["reviews"]
    pct_a = reviews["pct_reviewed_a"]
    pct_b = reviews["pct_reviewed_b"]
    reviews["pct_reviewed_a_growth_pct"] = (
        round((pct_b - pct_a) / pct_a * 100, 1) if pct_a != 0 else (100.0 if pct_b > 0 else 0.0)
    )

    avg_reviews_a = reviews["avg_reviews_a"]
    avg_reviews_b = reviews["avg_reviews_b"]
    reviews["avg_reviews_a_growth_pct"] = (
        round((avg_reviews_b - avg_reviews_a) / avg_reviews_a * 100, 1)
        if avg_reviews_a != 0
        else (100.0 if avg_reviews_b > 0 else 0.0)
    )

    avg_time_a = reviews["avg_time_a"]
    avg_time_b = reviews["avg_time_b"]
    reviews["avg_time_a_growth_pct"] = (
        round((avg_time_b - avg_time_a) / avg_time_a * 100, 1)
        if avg_time_a != 0
        else (100.0 if avg_time_b > 0 else 0.0)
    )

    approval_a = reviews["approval_rate_a"]
    approval_b = reviews["approval_rate_b"]
    reviews["approval_rate_a_growth_pct"] = (
        round((approval_b - approval_a) / approval_a * 100, 1)
        if approval_a != 0
        else (100.0 if approval_b > 0 else 0.0)
    )

    return comparison


def compute_team_trends(
    commits: list[dict[str, Any]],
    prs: list[dict[str, Any]],
    issues: list[dict[str, Any]],
    *,
    period_days: int = 30,
    num_periods: int = 6,
) -> dict[str, Any]:
    """Compute period-over-period activity trends for a team.

    Divides the time range into equal periods and counts activity in each.

    Args:
        commits: List of commit dicts with ``commit.author.date``.
        prs: List of PR dicts with ``created_at`` and ``merged_at``.
        issues: List of issue dicts with ``created_at`` and ``closed_at``.
        period_days: Length of each period in days (default 30).
        num_periods: Number of periods to analyze (default 6).

    Returns:
        Dict with periods list, metric counts per period, and trend direction.
    """
    now = datetime.now(UTC)
    periods: list[dict[str, Any]] = []
    period_labels: list[str] = []

    for i in range(num_periods):
        end = now - timedelta(days=i * period_days)
        start = now - timedelta(days=(i + 1) * period_days)
        periods.append({"start": start.isoformat(), "end": end.isoformat()})
        start_label = start.strftime("%b %d")
        end_label = end.strftime("%b %d")
        period_labels.append(f"{start_label}-{end_label}")

    # Reverse so oldest period is first
    periods.reverse()
    period_labels.reverse()

    # Count metrics per period
    commits_per: list[int] = [0] * num_periods
    prs_opened_per: list[int] = [0] * num_periods
    prs_merged_per: list[int] = [0] * num_periods
    issues_opened_per: list[int] = [0] * num_periods
    issues_closed_per: list[int] = [0] * num_periods

    for i, period in enumerate(periods):
        start_iso = period["start"]
        end_iso = period["end"]

        for commit in commits:
            date_str = commit.get("commit", {}).get("author", {}).get("date", "")
            if start_iso <= date_str < end_iso:
                commits_per[i] += 1

        for pr in prs:
            created = pr.get("created_at", "")
            if start_iso <= created < end_iso:
                prs_opened_per[i] += 1
            merged = pr.get("merged_at") or ""
            if merged and start_iso <= merged < end_iso:
                prs_merged_per[i] += 1

        for issue in issues:
            created = issue.get("created_at", "")
            if start_iso <= created < end_iso:
                issues_opened_per[i] += 1
            closed = issue.get("closed_at") or ""
            if closed and start_iso <= closed < end_iso:
                issues_closed_per[i] += 1

    # Compute per-author breakdowns
    author_commits_per: dict[str, list[int]] = defaultdict(lambda: [0] * num_periods)

    for i, period in enumerate(periods):
        start_iso = period["start"]
        end_iso = period["end"]

        for commit in commits:
            date_str = commit.get("commit", {}).get("author", {}).get("date", "")
            if start_iso <= date_str < end_iso:
                author = commit.get("author") or {}
                login = author.get("login") or commit.get("commit", {}).get("author", {}).get(
                    "name", ""
                )
                if login:
                    author_commits_per[login][i] += 1

    # Top authors by total commits across all periods
    author_totals = {login: sum(counts) for login, counts in author_commits_per.items()}
    sorted_authors = sorted(author_totals.items(), key=lambda x: x[1], reverse=True)
    top_authors = sorted_authors[:10]

    # Trend direction: compare last 2 periods
    def _trend_direction(current: int, previous: int) -> str:
        if previous == 0:
            return "new" if current > 0 else "stable"
        change_pct = (current - previous) / previous * 100
        if change_pct > 10:
            return "increasing"
        if change_pct < -10:
            return "decreasing"
        return "stable"

    # Overall trend
    if num_periods >= 2:
        overall_trend = _trend_direction(commits_per[-1], commits_per[-2])
        pr_trend = _trend_direction(prs_merged_per[-1], prs_merged_per[-2])
        issue_trend = _trend_direction(issues_closed_per[-1], issues_closed_per[-2])
    else:
        overall_trend = "stable"
        pr_trend = "stable"
        issue_trend = "stable"

    return {
        "period_labels": period_labels,
        "periods": periods,
        "metrics": {
            "commits": commits_per,
            "prs_opened": prs_opened_per,
            "prs_merged": prs_merged_per,
            "issues_opened": issues_opened_per,
            "issues_closed": issues_closed_per,
        },
        "trends": {
            "commits": overall_trend,
            "prs_merged": pr_trend,
            "issues_closed": issue_trend,
        },
        "top_authors": [
            {
                "login": login,
                "total": total,
                "per_period": author_commits_per[login],
            }
            for login, total in top_authors
        ],
    }
