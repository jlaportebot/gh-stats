# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team comparison UI rendering — Rich widgets for team comparison views."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _growth_style(growth: float) -> str:
    """Return color style for growth percentage."""
    if growth > 0:
        return "green"
    if growth < 0:
        return "red"
    return "yellow"


def _growth_str(growth: float | None) -> str:
    """Format growth percentage with sign."""
    if growth is None:
        return "N/A"
    sign = "+" if growth > 0 else ""
    return f"{sign}{growth:.1f}%"


def render_team_comparison_summary(comparison: dict[str, Any]) -> Panel:
    """Render team summary comparison table."""
    summary = comparison.get("summary", {})
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Metric", style="bold")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("Growth", justify="right")

    for key, val in summary.items():
        a = val.get("a", 0)
        b = val.get("b", 0)
        diff = val.get("diff", 0)
        growth = val.get("growth_pct")

        # Format values
        a_str = f"{a:,.1f}" if isinstance(a, float) else f"{a:,}"
        b_str = f"{b:,.1f}" if isinstance(b, float) else f"{b:,}"
        diff_str = f"{diff:+,.1f}" if isinstance(diff, float) else f"{diff:+,}"
        growth_str = _growth_str(growth)
        growth_style = _growth_style(growth) if growth is not None else "yellow"

        # Human-readable key
        display_key = key.replace("_", " ").title()

        table.add_row(
            display_key,
            a_str,
            b_str,
            diff_str,
            Text(growth_str, style=growth_style),
        )

    return Panel(table, title="📈 Summary Comparison", border_style="cyan")


def render_team_contributor_comparison(comparison: dict[str, Any]) -> Panel:
    """Render contributor comparison table."""
    contributors = comparison.get("contributors", [])
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Contributor", style="bold")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Diff", justify="right")

    for contrib in contributors:
        login = contrib.get("login", "")
        score_a = contrib.get("score_a", 0)
        score_b = contrib.get("score_b", 0)
        diff = contrib.get("diff", 0)

        table.add_row(
            f"@{login}",
            f"{score_a:,}",
            f"{score_b:,}",
            f"{diff:+,}",
        )

    if not contributors:
        table.add_row("No contributors found", "", "", "")

    return Panel(table, title="👥 Contributor Comparison", border_style="bright_magenta")


def render_team_repo_comparison(comparison: dict[str, Any]) -> Panel:
    """Render repo health comparison table."""
    repos = comparison.get("repos", [])
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Repository", style="bold")
    table.add_column(f"{label_a} Score", justify="right")
    table.add_column(f"{label_b} Score", justify="right")
    table.add_column("Diff", justify="right")

    for repo in repos:
        name = repo.get("name", "")
        score_a = repo.get("score_a", 0)
        score_b = repo.get("score_b", 0)
        diff = repo.get("diff", 0)

        # Color based on diff
        diff_style = "green" if diff > 0 else "red" if diff < 0 else "yellow"
        diff_str = f"{diff:+,}"

        table.add_row(
            name,
            f"{score_a}",
            f"{score_b}",
            Text(diff_str, style=diff_style),
        )

    if not repos:
        table.add_row("No repositories found", "", "", "")

    return Panel(table, title="📦 Repository Health Comparison", border_style="bright_green")


def render_team_trends_comparison(comparison: dict[str, Any]) -> Panel:
    """Render trends comparison table."""
    trends = comparison.get("trends", {})
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Metric", style="bold")
    table.add_column(f"{label_a} Total", justify="right")
    table.add_column(f"{label_b} Total", justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("Growth", justify="right")
    table.add_column(f"{label_a} Trend", justify="center")
    table.add_column(f"{label_b} Trend", justify="center")

    for metric_name, trend in trends.items():
        total_a = trend.get("total_a", 0)
        total_b = trend.get("total_b", 0)
        diff = trend.get("diff", 0)
        growth = trend.get("growth_pct")
        trend_a = trend.get("trend_a", "stable")
        trend_b = trend.get("trend_b", "stable")

        growth_str = _growth_str(growth)
        growth_style = _growth_style(growth) if growth is not None else "yellow"

        # Trend icons
        trend_icons = {
            "increasing": "📈",
            "decreasing": "📉",
            "stable": "➡️",
            "new": "✨",
        }
        icon_a = trend_icons.get(trend_a, trend_a)
        icon_b = trend_icons.get(trend_b, trend_b)

        table.add_row(
            metric_name.replace("_", " ").title(),
            f"{total_a:,}",
            f"{total_b:,}",
            f"{diff:+,}",
            Text(growth_str, style=growth_style),
            icon_a,
            icon_b,
        )

    if not trends:
        table.add_row("No trend data available", "", "", "", "", "", "")

    return Panel(table, title="📊 Activity Trends Comparison", border_style="bright_blue")


def render_team_bus_factor_comparison(comparison: dict[str, Any]) -> Panel:
    """Render bus factor comparison."""
    bf = comparison.get("bus_factor", {})
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    bf_a = bf.get("bus_factor_a", 0)
    bf_b = bf.get("bus_factor_b", 0)
    cov_a = bf.get("coverage_a", 0.0)
    cov_b = bf.get("coverage_b", 0.0)
    contrib_a = bf.get("total_contributors_a", 0)
    contrib_b = bf.get("total_contributors_b", 0)

    # Bus factor status
    def bf_status(bf_val: int) -> tuple[str, str]:
        if bf_val <= 1:
            return "🔴 Critical", "red"
        if bf_val <= 2:
            return "🟠 High Risk", "orange3"
        if bf_val <= 3:
            return "🟡 Medium", "yellow"
        if bf_val <= 5:
            return "🟢 Low Risk", "green"
        return "🟢 Healthy", "bright_green"

    status_a, style_a = bf_status(bf_a)
    status_b, style_b = bf_status(bf_b)

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Metric", style="bold")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")

    table.add_row("Bus Factor", Text(str(bf_a), style=style_a), Text(str(bf_b), style=style_b))
    table.add_row("Status", Text(status_a, style=style_a), Text(status_b, style=style_b))
    table.add_row("Coverage %", f"{cov_a:.1f}%", f"{cov_b:.1f}%")
    table.add_row("Total Contributors", f"{contrib_a:,}", f"{contrib_b:,}")

    return Panel(table, title="🚌 Bus Factor Comparison", border_style="orange3")


def render_team_review_comparison(comparison: dict[str, Any]) -> Panel:
    """Render code review comparison."""
    reviews = comparison.get("reviews", {})
    label_a = comparison.get("label_a", "Team A")
    label_b = comparison.get("label_b", "Team B")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Metric", style="bold")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Growth", justify="right")

    metrics = [
        ("Total PRs", "total_prs_a", "total_prs_b", None),
        ("% Reviewed", "pct_reviewed_a", "pct_reviewed_b", "pct_reviewed_a_growth_pct"),
        ("Avg Reviews/PR", "avg_reviews_a", "avg_reviews_b", "avg_reviews_a_growth_pct"),
        ("Avg Time to Review (h)", "avg_time_a", "avg_time_b", "avg_time_a_growth_pct"),
        ("Approval Rate %", "approval_rate_a", "approval_rate_b", "approval_rate_a_growth_pct"),
    ]

    for display_name, key_a, key_b, growth_key in metrics:
        val_a = reviews.get(key_a, 0)
        val_b = reviews.get(key_b, 0)
        growth = reviews.get(growth_key) if growth_key else None

        a_str = f"{val_a:,.1f}" if isinstance(val_a, float) else f"{val_a:,}"
        b_str = f"{val_b:,.1f}" if isinstance(val_b, float) else f"{val_b:,}"
        growth_str = _growth_str(growth)
        growth_style = _growth_style(growth) if growth is not None else "yellow"

        table.add_row(
            display_name,
            a_str,
            b_str,
            Text(growth_str, style=growth_style),
        )

    return Panel(table, title="🔍 Code Review Comparison", border_style="bright_cyan")


def render_team_time_comparison_summary(comparison: dict[str, Any]) -> Panel:
    """Render time comparison summary with growth rates highlighted."""
    summary = comparison.get("summary", {})
    label_a = comparison.get("label_a", "Previous")
    label_b = comparison.get("label_b", "Current")

    table = Table(show_header=True, header_style="bold cyan", expand=True)
    table.add_column("Metric", style="bold")
    table.add_column(label_a, justify="right")
    table.add_column(label_b, justify="right")
    table.add_column("Diff", justify="right")
    table.add_column("Growth", justify="right", style="bold")

    for key, val in summary.items():
        a = val.get("a", 0)
        b = val.get("b", 0)
        diff = val.get("diff", 0)
        growth = val.get("growth_pct")

        a_str = f"{a:,.1f}" if isinstance(a, float) else f"{a:,}"
        b_str = f"{b:,.1f}" if isinstance(b, float) else f"{b:,}"
        diff_str = f"{diff:+,.1f}" if isinstance(diff, float) else f"{diff:+,}"
        growth_str = _growth_str(growth)
        growth_style = _growth_style(growth) if growth is not None else "yellow"

        display_key = key.replace("_", " ").title()

        table.add_row(
            display_key,
            a_str,
            b_str,
            diff_str,
            Text(growth_str, style=growth_style),
        )

    return Panel(
        table, title=f"📈 Time Comparison: {label_a} → {label_b}", border_style="bright_green"
    )
