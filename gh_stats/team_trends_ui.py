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


# ---------------------------------------------------------------------------
# Team comparison UI
# ---------------------------------------------------------------------------


def _trend_icon(trend: str) -> str:
    """Return icon for trend direction."""
    icons = {
        "increasing": "\U0001f4c8",
        "decreasing": "\U0001f4c9",
        "stable": "\u2192",
        "new": "\U0001f195",
    }
    return icons.get(trend, trend)


def _growth_style(growth_pct: float) -> str:
    """Return style for growth percentage."""
    if growth_pct > 5:
        return "green"
    if growth_pct < -5:
        return "red"
    return "yellow"


def _format_diff(diff: float, prefix: bool = True) -> str:
    """Format diff with sign."""
    if diff > 0:
        return f"+{diff}" if prefix else str(diff)
    return str(diff)


def render_team_comparison(comparison: dict[str, Any]) -> Panel:
    """Render team vs team comparison as a Rich panel.

    Args:
        comparison: Output of ``compute_team_comparison``.

    Returns:
        Rich Panel with comparison visualization.
    """
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")
    summary = comparison.get("summary", {})
    contributors = comparison.get("contributors", [])
    repos = comparison.get("repos", [])
    trends = comparison.get("trends", {})
    bus_factor = comparison.get("bus_factor", {})
    reviews = comparison.get("reviews", {})

    # Summary comparison table
    summary_table = Table(show_header=True, header_style="bold cyan", expand=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column(label_a, justify="right")
    summary_table.add_column(label_b, justify="right")
    summary_table.add_column("Diff", justify="right")

    for key, data in summary.items():
        label = key.replace("_", " ").title()
        a_val = data.get("a", 0)
        b_val = data.get("b", 0)
        diff = data.get("diff", 0)
        diff_style = _growth_style(
            round((diff / a_val * 100), 1) if a_val > 0 else (100 if b_val > 0 else 0)
        )
        summary_table.add_row(
            label,
            str(a_val),
            str(b_val),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
        )

    # Contributor comparison
    contrib_table = Table(show_header=True, header_style="bold cyan", expand=True)
    contrib_table.add_column("Contributor", style="bold")
    contrib_table.add_column(label_a, justify="right")
    contrib_table.add_column(label_b, justify="right")
    contrib_table.add_column("Diff", justify="right")

    for c in contributors[:10]:
        score_a = c.get("score_a", 0)
        score_b = c.get("score_b", 0)
        diff = c.get("diff", 0)
        diff_style = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
        contrib_table.add_row(
            f"@{c.get('login', '')}",
            f"{score_a:.0f}",
            f"{score_b:.0f}",
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
        )

    # Repo health comparison
    repo_table = Table(show_header=True, header_style="bold cyan", expand=True)
    repo_table.add_column("Repository", style="bold")
    repo_table.add_column(f"{label_a} Score", justify="right")
    repo_table.add_column(f"{label_b} Score", justify="right")
    repo_table.add_column("Diff", justify="right")
    repo_table.add_column("Status", justify="center")

    for r in repos[:10]:
        score_a = r.get("score_a", 0)
        score_b = r.get("score_b", 0)
        diff = r.get("diff", 0)
        status_a = r.get("status_a", "?")
        status_b = r.get("status_b", "?")
        diff_style = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
        repo_table.add_row(
            r.get("name", ""),
            str(score_a),
            str(score_b),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
            f"{status_a} | {status_b}",
        )

    # Trends comparison
    trends_table = Table(show_header=True, header_style="bold cyan", expand=True)
    trends_table.add_column("Metric", style="bold")
    trends_table.add_column(f"{label_a} Total", justify="right")
    trends_table.add_column(f"{label_b} Total", justify="right")
    trends_table.add_column("Diff", justify="right")
    trends_table.add_column(f"{label_a} Trend", justify="center")
    trends_table.add_column(f"{label_b} Trend", justify="center")

    for metric, data in trends.items():
        label = metric.replace("_", " ").title()
        total_a = data.get("total_a", 0)
        total_b = data.get("total_b", 0)
        diff = data.get("diff", 0)
        trend_a = data.get("trend_a", "stable")
        trend_b = data.get("trend_b", "stable")
        diff_style = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
        trends_table.add_row(
            label,
            str(total_a),
            str(total_b),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
            f"{_trend_icon(trend_a)} {trend_a}",
            f"{_trend_icon(trend_b)} {trend_b}",
        )

    # Bus factor comparison
    bf_table = Table(show_header=True, header_style="bold cyan", expand=True)
    bf_table.add_column("Metric", style="bold")
    bf_table.add_column(label_a, justify="right")
    bf_table.add_column(label_b, justify="right")

    bf_a = bus_factor.get("bus_factor_a", 0)
    bf_b = bus_factor.get("bus_factor_b", 0)
    coverage_a = bus_factor.get("coverage_a", 0)
    coverage_b = bus_factor.get("coverage_b", 0)
    total_contrib_a = bus_factor.get("total_contributors_a", 0)
    total_contrib_b = bus_factor.get("total_contributors_b", 0)

    bf_table.add_row("Bus Factor", str(bf_a), str(bf_b))
    bf_table.add_row("Coverage %", f"{coverage_a:.1f}%", f"{coverage_b:.1f}%")
    bf_table.add_row("Total Contributors", str(total_contrib_a), str(total_contrib_b))

    # Review analytics comparison
    rev_table = Table(show_header=True, header_style="bold cyan", expand=True)
    rev_table.add_column("Metric", style="bold")
    rev_table.add_column(label_a, justify="right")
    rev_table.add_column(label_b, justify="right")
    rev_table.add_column("Diff", justify="right")

    rev_metrics = [
        ("Total PRs", "total_prs_a", "total_prs_b"),
        ("% Reviewed", "pct_reviewed_a", "pct_reviewed_b"),
        ("Avg Reviews/PR", "avg_reviews_a", "avg_reviews_b"),
        ("Avg Time to Review (h)", "avg_time_a", "avg_time_b"),
        ("Approval Rate %", "approval_rate_a", "approval_rate_b"),
    ]

    for label, key_a, key_b in rev_metrics:
        val_a = reviews.get(key_a, 0)
        val_b = reviews.get(key_b, 0)
        diff = val_b - val_a
        diff_style = "green" if diff > 0 else ("red" if diff < 0 else "yellow")
        rev_table.add_row(
            label,
            f"{val_a:.1f}" if isinstance(val_a, float) else str(val_a),
            f"{val_b:.1f}" if isinstance(val_b, float) else str(val_b),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
        )

    # Combine all sections
    content = Group(
        Panel(summary_table, title="\U0001f4cb Summary Comparison", border_style="cyan"),
        Panel(contrib_table, title="\U0001f465 Top Contributors Comparison", border_style="cyan"),
        Panel(repo_table, title="\U0001f3e5 Repo Health Comparison", border_style="cyan"),
        Panel(trends_table, title="\U0001f4c8 Activity Trends Comparison", border_style="cyan"),
        Panel(bf_table, title="\U0001f68c Bus Factor Comparison", border_style="cyan"),
        Panel(rev_table, title="\U0001f441 Review Analytics Comparison", border_style="cyan"),
    )

    return Panel(
        content,
        title=f"\U0001f4ca Team Comparison: {label_a} vs {label_b}",
        border_style="bright_cyan",
        padding=(1, 2),
    )


def render_team_time_comparison(comparison: dict[str, Any]) -> Panel:
    """Render team time-period comparison as a Rich panel.

    Args:
        comparison: Output of ``compute_team_time_comparison``.

    Returns:
        Rich Panel with time comparison visualization.
    """
    label_current = comparison.get("label_a", "Current")
    label_previous = comparison.get("label_b", "Previous")
    summary = comparison.get("summary", {})
    trends = comparison.get("trends", {})
    reviews = comparison.get("reviews", {})

    # Summary with growth rates
    summary_table = Table(show_header=True, header_style="bold cyan", expand=True)
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column(label_current, justify="right")
    summary_table.add_column(label_previous, justify="right")
    summary_table.add_column("Change", justify="right")
    summary_table.add_column("Growth %", justify="right")

    for key, data in summary.items():
        label = key.replace("_", " ").title()
        a_val = data.get("a", 0)
        b_val = data.get("b", 0)
        diff = data.get("diff", 0)
        growth = data.get("growth_pct", 0)
        diff_style = _growth_style(growth)
        growth_style = _growth_style(growth)
        summary_table.add_row(
            label,
            str(a_val),
            str(b_val),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
            f"[{growth_style}]{_format_diff(growth, False)}%[/{growth_style}]",
        )

    # Trends with growth rates
    trends_table = Table(show_header=True, header_style="bold cyan", expand=True)
    trends_table.add_column("Metric", style="bold")
    trends_table.add_column(label_current, justify="right")
    trends_table.add_column(label_previous, justify="right")
    trends_table.add_column("Change", justify="right")
    trends_table.add_column("Growth %", justify="right")
    trends_table.add_column(f"{label_current} Trend", justify="center")
    trends_table.add_column(f"{label_previous} Trend", justify="center")

    for metric, data in trends.items():
        label = metric.replace("_", " ").title()
        total_a = data.get("total_a", 0)
        total_b = data.get("total_b", 0)
        diff = data.get("diff", 0)
        growth = data.get("growth_pct", 0)
        trend_a = data.get("trend_a", "stable")
        trend_b = data.get("trend_b", "stable")
        diff_style = _growth_style(growth)
        growth_style = _growth_style(growth)
        trends_table.add_row(
            label,
            str(total_a),
            str(total_b),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
            f"[{growth_style}]{_format_diff(growth, False)}%[/{growth_style}]",
            f"{_trend_icon(trend_a)} {trend_a}",
            f"{_trend_icon(trend_b)} {trend_b}",
        )

    # Review analytics with growth
    rev_table = Table(show_header=True, header_style="bold cyan", expand=True)
    rev_table.add_column("Metric", style="bold")
    rev_table.add_column(label_current, justify="right")
    rev_table.add_column(label_previous, justify="right")
    rev_table.add_column("Change", justify="right")
    rev_table.add_column("Growth %", justify="right")

    rev_metrics = [
        ("Total PRs", "total_prs_a", "total_prs_b", "total_prs_a_growth_pct"),
        ("% Reviewed", "pct_reviewed_a", "pct_reviewed_b", "pct_reviewed_a_growth_pct"),
        ("Avg Reviews/PR", "avg_reviews_a", "avg_reviews_b", "avg_reviews_a_growth_pct"),
        ("Avg Time to Review (h)", "avg_time_a", "avg_time_b", "avg_time_a_growth_pct"),
        ("Approval Rate %", "approval_rate_a", "approval_rate_b", "approval_rate_a_growth_pct"),
    ]

    for label, key_a, key_b, growth_key in rev_metrics:
        val_a = reviews.get(key_a, 0)
        val_b = reviews.get(key_b, 0)
        growth = reviews.get(growth_key, 0)
        diff = val_b - val_a
        diff_style = _growth_style(growth)
        growth_style = _growth_style(growth)
        rev_table.add_row(
            label,
            f"{val_a:.1f}" if isinstance(val_a, float) else str(val_a),
            f"{val_b:.1f}" if isinstance(val_b, float) else str(val_b),
            f"[{diff_style}]{_format_diff(diff)}[/{diff_style}]",
            f"[{growth_style}]{_format_diff(growth, False)}%[/{growth_style}]",
        )

    content = Group(
        Panel(summary_table, title="\U0001f4cb Summary Growth", border_style="cyan"),
        Panel(trends_table, title="\U0001f4c8 Activity Trends Growth", border_style="cyan"),
        Panel(rev_table, title="\U0001f441 Review Analytics Growth", border_style="cyan"),
    )

    return Panel(
        content,
        title=f"\U0001f4ca Team Time Comparison: {label_current} vs {label_previous}",
        border_style="bright_cyan",
        padding=(1, 2),
    )
