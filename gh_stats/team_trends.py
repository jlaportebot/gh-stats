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
