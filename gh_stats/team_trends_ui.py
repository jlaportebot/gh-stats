# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team trends UI rendering — Rich widgets for period-over-period trends."""

from __future__ import annotations

from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

_SPARK_CHARS = ["\u2581", "\u2582", "\u2583", "\u2584", "\u2585", "\u2586", "\u2587", "\u2588"]

_TREND_ICONS = {
    "increasing": "\U0001f4c8 Increasing",
    "decreasing": "\U0001f4c9 Decreasing",
    "stable": "\u2192 Stable",
    "new": "\U0001f195 New activity",
}


def _build_sparkline(per_period: list[int]) -> Text:
    """Build a sparkline Text object from period values.

    Args:
        per_period: List of integer values per period.

    Returns:
        Rich Text with colored sparkline characters.
    """
    max_val = max(per_period) if per_period and max(per_period) > 0 else 1
    sparkline = ""
    for v in per_period:
        idx = min(int(v / max_val * (len(_SPARK_CHARS) - 1)), len(_SPARK_CHARS) - 1)
        sparkline += _SPARK_CHARS[idx]
    if not sparkline:
        sparkline = "\u2581"

    recent = sum(per_period[-2:]) if len(per_period) >= 2 else 0
    earlier = sum(per_period[:-2]) if len(per_period) > 2 else recent
    if recent > earlier > 0:
        spark_color = "green"
    elif recent < earlier and earlier > 0:
        spark_color = "red"
    else:
        spark_color = "yellow"
    return Text(sparkline, style=spark_color)


def render_team_trends(trends: dict[str, Any]) -> Panel:
    """Render team activity trends as a Rich panel.

    Args:
        trends: Output of ``compute_team_trends``.

    Returns:
        Rich Panel with trends visualization.
    """
    period_labels = trends.get("period_labels", [])
    metrics = trends.get("metrics", {})
    trend_dirs = trends.get("trends", {})
    top_authors = trends.get("top_authors", [])

    if not period_labels:
        return Panel("No trend data available", title="\U0001f4c8 Activity Trends")

    # Build metrics table
    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Period", style="dim")
    table.add_column("Commits", justify="right")
    table.add_column("PRs Opened", justify="right")
    table.add_column("PRs Merged", justify="right")
    table.add_column("Issues Opened", justify="right")
    table.add_column("Issues Closed", justify="right")

    commits_data = metrics.get("commits", [])
    prs_opened = metrics.get("prs_opened", [])
    prs_merged = metrics.get("prs_merged", [])
    issues_opened = metrics.get("issues_opened", [])
    issues_closed = metrics.get("issues_closed", [])

    max_commits = max(commits_data) if commits_data and max(commits_data) > 0 else 1

    for i, label in enumerate(period_labels):
        c = commits_data[i] if i < len(commits_data) else 0
        po = prs_opened[i] if i < len(prs_opened) else 0
        pm = prs_merged[i] if i < len(prs_merged) else 0
        io_val = issues_opened[i] if i < len(issues_opened) else 0
        ic_val = issues_closed[i] if i < len(issues_closed) else 0

        bar_len = int(c / max_commits * 12) if max_commits > 0 else 0
        bar = "\u2588" * bar_len
        style = "green" if c > 0 else "dim"
        table.add_row(
            label,
            f"{c} {bar}" if c > 0 else "0",
            str(po),
            str(pm),
            str(io_val),
            str(ic_val),
            style=style,
        )

    # Trend summary text
    commits_trend = trend_dirs.get("commits", "stable")
    prs_trend = trend_dirs.get("prs_merged", "stable")
    issues_trend = trend_dirs.get("issues_closed", "stable")

    summary = (
        f"  Commits: {_TREND_ICONS.get(commits_trend, commits_trend)}\n"
        f"  PR Merges: {_TREND_ICONS.get(prs_trend, prs_trend)}\n"
        f"  Issue Closes: {_TREND_ICONS.get(issues_trend, issues_trend)}"
    )

    # Top authors sparklines table
    authors_content: Text | Table = Text("")
    if top_authors:
        authors_table = Table(show_header=True, header_style="bold cyan", expand=True)
        authors_table.add_column("Author", style="bold")
        authors_table.add_column("Total", justify="right")
        authors_table.add_column("Trend", justify="left")

        for author in top_authors[:8]:
            login = author.get("login", "")
            total = author.get("total", 0)
            per_period = author.get("per_period", [])
            spark = _build_sparkline(per_period)
            authors_table.add_row(f"@{login}", str(total), spark)

        authors_content = authors_table

    content = Group(table, Text(summary), authors_content)
    return Panel(content, title="\U0001f4c8 Activity Trends", border_style="cyan")
