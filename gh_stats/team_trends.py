# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team trends — compute period-over-period activity trends for orgs."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


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


# ---------------------------------------------------------------------------
# Team comparison
# ---------------------------------------------------------------------------


def compute_team_comparison(
    team_a_data: dict[str, Any],
    team_b_data: dict[str, Any],
    *,
    label_a: str = "Team A",
    label_b: str = "Team B",
) -> dict[str, Any]:
    """Compare two teams (organizations) side by side.

    Args:
        team_a_data: Team analytics data for team A (output of team CLI computation).
        team_b_data: Team analytics data for team B.
        label_a: Display label for team A.
        label_b: Display label for team B.

    Returns:
        Dict with comparison metrics and differences.
    """
    # Compare summary stats
    summary_a = team_a_data.get("summary", {})
    summary_b = team_b_data.get("summary", {})

    summary_comparison = {
        "total_repos": {
            "a": summary_a.get("total_repos", 0),
            "b": summary_b.get("total_repos", 0),
            "diff": summary_b.get("total_repos", 0) - summary_a.get("total_repos", 0),
        },
        "total_contributors": {
            "a": summary_a.get("total_contributors", 0),
            "b": summary_b.get("total_contributors", 0),
            "diff": summary_b.get("total_contributors", 0) - summary_a.get("total_contributors", 0),
        },
        "total_commits": {
            "a": summary_a.get("total_commits", 0),
            "b": summary_b.get("total_commits", 0),
            "diff": summary_b.get("total_commits", 0) - summary_a.get("total_commits", 0),
        },
        "total_prs": {
            "a": summary_a.get("total_prs", 0),
            "b": summary_b.get("total_prs", 0),
            "diff": summary_b.get("total_prs", 0) - summary_a.get("total_prs", 0),
        },
        "total_issues": {
            "a": summary_a.get("total_issues", 0),
            "b": summary_b.get("total_issues", 0),
            "diff": summary_b.get("total_issues", 0) - summary_a.get("total_issues", 0),
        },
        "bus_factor": {
            "a": summary_a.get("bus_factor", 0),
            "b": summary_b.get("bus_factor", 0),
            "diff": summary_b.get("bus_factor", 0) - summary_a.get("bus_factor", 0),
        },
        "avg_health": {
            "a": round(summary_a.get("avg_health", 0), 1),
            "b": round(summary_b.get("avg_health", 0), 1),
            "diff": round(summary_b.get("avg_health", 0) - summary_a.get("avg_health", 0), 1),
        },
    }

    # Compare contributor rankings
    contributors_a = team_a_data.get("contributor_rankings", [])
    contributors_b = team_b_data.get("contributor_rankings", [])

    top_a = {c.get("login", ""): c.get("score", 0) for c in contributors_a[:10]}
    top_b = {c.get("login", ""): c.get("score", 0) for c in contributors_b[:10]}

    all_contributors = set(top_a.keys()) | set(top_b.keys())
    contributor_comparison = []
    for login in sorted(all_contributors):
        score_a = top_a.get(login, 0)
        score_b = top_b.get(login, 0)
        contributor_comparison.append({
            "login": login,
            "score_a": score_a,
            "score_b": score_b,
            "diff": round(score_b - score_a, 1),
        })
    contributor_comparison.sort(key=lambda x: abs(x["diff"]), reverse=True)

    # Compare repo health
    repo_health_a = {r.get("name", ""): r for r in team_a_data.get("repo_health", [])}
    repo_health_b = {r.get("name", ""): r for r in team_b_data.get("repo_health", [])}

    all_repos = set(repo_health_a.keys()) | set(repo_health_b.keys())
    repo_comparison = []
    for name in sorted(all_repos):
        ra = repo_health_a.get(name)
        rb = repo_health_b.get(name)
        score_a = ra.get("health_score", 0) if ra else 0
        score_b = rb.get("health_score", 0) if rb else 0
        status_a = ra.get("status", "missing") if ra else "missing"
        status_b = rb.get("status", "missing") if rb else "missing"
        repo_comparison.append({
            "name": name,
            "score_a": score_a,
            "score_b": score_b,
            "diff": score_b - score_a,
            "status_a": status_a,
            "status_b": status_b,
        })
    repo_comparison.sort(key=lambda x: abs(x["diff"]), reverse=True)

    # Compare trends
    trends_a = team_a_data.get("trends", {})
    trends_b = team_b_data.get("trends", {})

    metrics_a = trends_a.get("metrics", {})
    metrics_b = trends_b.get("metrics", {})

    period_labels_a = trends_a.get("period_labels", [])
    period_labels_b = trends_b.get("period_labels", [])
    period_labels = (
        period_labels_a if len(period_labels_a) >= len(period_labels_b) else period_labels_b
    )

    # Return empty trends if both teams have no metrics data
    if not metrics_a and not metrics_b:
        trend_comparison = {}
    else:
        trend_comparison = {}
        for metric in ["commits", "prs_opened", "prs_merged", "issues_opened", "issues_closed"]:
            data_a = metrics_a.get(metric, [])
            data_b = metrics_b.get(metric, [])
            total_a = sum(data_a)
            total_b = sum(data_b)
            trend_comparison[metric] = {
                "total_a": total_a,
                "total_b": total_b,
                "diff": total_b - total_a,
                "trend_a": trends_a.get("trends", {}).get(metric, "stable"),
                "trend_b": trends_b.get("trends", {}).get(metric, "stable"),
            }

    # Compare bus factor
    bus_factor_a = team_a_data.get("bus_factor", {})
    bus_factor_b = team_b_data.get("bus_factor", {})

    bus_factor_comparison = {
        "bus_factor_a": bus_factor_a.get("bus_factor", 0),
        "bus_factor_b": bus_factor_b.get("bus_factor", 0),
        "coverage_a": bus_factor_a.get("coverage_pct", 0),
        "coverage_b": bus_factor_b.get("coverage_pct", 0),
        "total_contributors_a": bus_factor_a.get("total_contributors", 0),
        "total_contributors_b": bus_factor_b.get("total_contributors", 0),
    }

    # Compare review analytics
    review_a = team_a_data.get("review_analytics", {})
    review_b = team_b_data.get("review_analytics", {})

    review_comparison = {
        "total_prs_a": review_a.get("total_prs", 0),
        "total_prs_b": review_b.get("total_prs", 0),
        "pct_reviewed_a": review_a.get("pct_prs_reviewed", 0),
        "pct_reviewed_b": review_b.get("pct_prs_reviewed", 0),
        "avg_reviews_a": review_a.get("avg_reviews_per_pr", 0),
        "avg_reviews_b": review_b.get("avg_reviews_per_pr", 0),
        "avg_time_a": review_a.get("avg_time_to_first_review_hours", 0),
        "avg_time_b": review_b.get("avg_time_to_first_review_hours", 0),
        "approval_rate_a": round(
            review_a.get("approval_count", 0) / max(review_a.get("total_reviews", 1), 1) * 100, 1
        ),
        "approval_rate_b": round(
            review_b.get("approval_count", 0) / max(review_b.get("total_reviews", 1), 1) * 100, 1
        ),
    }

    return {
        "label_a": label_a,
        "label_b": label_b,
        "summary": summary_comparison,
        "contributors": contributor_comparison[:15],
        "repos": repo_comparison[:15],
        "trends": trend_comparison,
        "bus_factor": bus_factor_comparison,
        "reviews": review_comparison,
        "period_labels": period_labels if trend_comparison else [],
    }


def compute_team_time_comparison(
    team_current: dict[str, Any],
    team_previous: dict[str, Any],
    *,
    label_current: str = "Current Period",
    label_previous: str = "Previous Period",
) -> dict[str, Any]:
    """Compare the same team across two time periods.

    Args:
        team_current: Team analytics data for current period.
        team_previous: Team analytics data for previous period.
        label_current: Display label for current period.
        label_previous: Display label for previous period.

    Returns:
        Dict with comparison metrics showing growth/decline.
    """
    # Reuse the side-by-side comparison logic
    # Note: we pass previous as 'a' and current as 'b' so diff = current - previous
    comparison = compute_team_comparison(
        team_previous,
        team_current,
        label_a=label_previous,
        label_b=label_current,
    )

    # Add growth rates for key metrics
    summary = comparison["summary"]
    for key in summary:
        val_a = summary[key]["a"]  # previous
        val_b = summary[key]["b"]  # current
        if val_a > 0:
            summary[key]["growth_pct"] = round((val_b - val_a) / val_a * 100, 1)
        else:
            summary[key]["growth_pct"] = 100.0 if val_b > 0 else 0.0

    # Add growth rates for trends
    for metric in comparison["trends"]:
        total_a = comparison["trends"][metric]["total_a"]  # previous
        total_b = comparison["trends"][metric]["total_b"]  # current
        if total_a > 0:
            comparison["trends"][metric]["growth_pct"] = round(
                (total_b - total_a) / total_a * 100, 1
            )
        else:
            comparison["trends"][metric]["growth_pct"] = 100.0 if total_b > 0 else 0.0

    # Review analytics growth
    reviews = comparison["reviews"]
    for key in [
        "total_prs_a",
        "total_prs_b",
        "pct_reviewed_a",
        "pct_reviewed_b",
        "avg_reviews_a",
        "avg_reviews_b",
        "avg_time_a",
        "avg_time_b",
        "approval_rate_a",
        "approval_rate_b",
    ]:
        if key.endswith("_a"):
            a_key = key
            b_key = key[:-2] + "_b"
            if a_key in reviews and b_key in reviews:
                val_a = reviews[a_key]
                val_b = reviews[b_key]
                if val_a > 0:
                    reviews[f"{a_key}_growth_pct"] = round((val_b - val_a) / val_a * 100, 1)
                else:
                    reviews[f"{a_key}_growth_pct"] = 100.0 if val_b > 0 else 0.0

    return comparison
