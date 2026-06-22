# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""HTML export for comparison reports."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def _render_comparison_html(data: dict[str, Any]) -> str:
    """Render comparison data as HTML.

    Args:
        data: Comparison export data dict.

    Returns:
        HTML string for the comparison report.
    """
    target_a = data.get("target_a", "A")
    target_b = data.get("target_b", "B")
    comparison_mode = data.get("comparison_mode", "side_by_side")

    css = (
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; "
        "background: #0d1117; color: #c9d1d9; } "
        "h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; } "
        "h2 { color: #58a6ff; margin-top: 30px; } "
        ".comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; } "
        ".card { background: #161b22; border: 1px solid #30363d; "
        "border-radius: 8px; padding: 20px; margin: 0; } "
        ".card h3 { margin-top: 0; color: #58a6ff; } "
        ".stat-grid { display: grid; "
        "grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; } "
        ".stat { text-align: center; } "
        ".stat-value { font-size: 1.8em; font-weight: bold; color: #58a6ff; } "
        ".stat-label { color: #8b949e; font-size: 0.85em; } "
        ".growth-positive { color: #3fb950; font-weight: bold; } "
        ".growth-negative { color: #f85149; font-weight: bold; } "
        ".growth-neutral { color: #8b949e; } "
        "table { width: 100%; border-collapse: collapse; margin-top: 10px; } "
        "th, td { padding: 8px; text-align: left; border-bottom: 1px solid #30363d; } "
        "th { color: #58a6ff; } "
        ".bar { height: 16px; "
        "background: linear-gradient(90deg, #238636, #2ea043); "
        "border-radius: 3px; display: inline-block; } "
        ".bar-container { height: 16px; background: #21262d; "
        "border-radius: 3px; overflow: hidden; margin: 4px 0; } "
        ".verdict { font-size: 1.2em; margin: 15px 0; padding: 10px; "
        "background: #161b22; border-radius: 8px; border: 1px solid #30363d; } "
        ".weekday-row { display: flex; align-items: center; margin: 2px 0; } "
        ".weekday-label { width: 35px; font-weight: bold; } "
        ".month-label { width: 35px; font-weight: bold; }"
    )

    stats_a = data.get("stats_a", {})
    stats_b = data.get("stats_b", {})
    total_a = data.get("total_contributions_a", 0)
    total_b = data.get("total_contributions_b", 0)
    summary_a = data.get("activity_summary_a", {})
    summary_b = data.get("activity_summary_b", {})
    streaks_a = data.get("streaks_a", {})
    streaks_b = data.get("streaks_b", {})
    patterns_a = data.get("patterns_a", {})
    patterns_b = data.get("patterns_b", {})
    growth = data.get("growth_metrics", {})

    mode_label = "Time Period" if comparison_mode == "time_period" else "Side by Side"
    now_iso = datetime.now(UTC).isoformat()

    html = (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        "  <meta charset='UTF-8'>\n"
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"  <title>gh-stats — {target_a} vs {target_b}</title>\n"
        f"  <style>{css}</style>\n"
        "</head>\n<body>\n"
        f"  <h1>\U0001f4ca gh-stats — {target_a} vs {target_b}</h1>\n"
        f"  <p style='color:#8b949e'>Mode: {mode_label} | "
        f"Generated: {now_iso}</p>\n"
    )

    # Profile cards
    html += _html_profile_cards(
        target_a,
        target_b,
        total_a,
        total_b,
        stats_a,
        stats_b,
        streaks_a,
        streaks_b,
    )

    # Growth metrics
    if growth:
        html += _html_growth_section(growth)

    # Contribution patterns
    html += _html_patterns_section(
        target_a,
        target_b,
        patterns_a,
        patterns_b,
    )

    # Activity summary
    html += _html_summary_section(target_a, target_b, summary_a, summary_b)

    html += "\n</body>\n</html>"
    return html


def _html_stat_div(value: int | str, label: str) -> str:
    """Generate a single stat-value/stat-label div.

    Args:
        value: The stat value to display.
        label: The stat label text.

    Returns:
        HTML string for one stat cell.
    """
    return (
        f"<div class='stat'><div class='stat-value'>{value}</div>"
        f"<div class='stat-label'>{label}</div></div>"
    )


def _html_profile_cards(
    target_a: str,
    target_b: str,
    total_a: int,
    total_b: int,
    stats_a: dict[str, Any],
    stats_b: dict[str, Any],
    streaks_a: dict[str, Any],
    streaks_b: dict[str, Any],
) -> str:
    """Generate HTML for side-by-side profile cards.

    Args:
        target_a: Label for target A.
        target_b: Label for target B.
        total_a: Total contributions for A.
        total_b: Total contributions for B.
        stats_a: Profile stats dict for A.
        stats_b: Profile stats dict for B.
        streaks_a: Streaks dict for A.
        streaks_b: Streaks dict for B.

    Returns:
        HTML string with profile cards.
    """
    return (
        "<div class='comparison'>\n"
        f"  <div class='card'><h3>\U0001f464 {target_a}</h3>"
        f"<div class='stat-grid'>"
        f"{_html_stat_div(total_a, 'Contributions')}"
        f"{_html_stat_div(stats_a.get('public_repos', 0), 'Repos')}"
        f"{_html_stat_div(stats_a.get('followers', 0), 'Followers')}"
        f"{_html_stat_div(streaks_a.get('current_streak', 0), 'Current Streak')}"
        f"</div></div>\n"
        f"  <div class='card'><h3>\U0001f464 {target_b}</h3>"
        f"<div class='stat-grid'>"
        f"{_html_stat_div(total_b, 'Contributions')}"
        f"{_html_stat_div(stats_b.get('public_repos', 0), 'Repos')}"
        f"{_html_stat_div(stats_b.get('followers', 0), 'Followers')}"
        f"{_html_stat_div(streaks_b.get('current_streak', 0), 'Current Streak')}"
        f"</div></div>\n"
        "</div>\n"
    )


def _growth_class(val: float) -> str:
    """Return CSS class name based on growth direction.

    Args:
        val: Growth percentage value.

    Returns:
        CSS class string.
    """
    if val > 5:
        return "growth-positive"
    if val < -5:
        return "growth-negative"
    return "growth-neutral"


def _html_growth_section(growth: dict[str, Any]) -> str:
    """Generate HTML for growth metrics section.

    Args:
        growth: Growth metrics dict.

    Returns:
        HTML string with growth metrics table.
    """
    verdict = growth.get("verdict", "")
    total_growth = growth.get("total_growth_pct", 0.0)
    active_growth = growth.get("active_days_growth_pct", 0.0)
    consistency_change = growth.get("consistency_change_pct", 0.0)

    return (
        "<h2>\U0001f4ca Growth Metrics</h2>\n"
        f"<div class='verdict'>{verdict}</div>\n"
        "<table><tr><th>Metric</th><th>Change</th></tr>\n"
        f"<tr><td>Total Contributions</td>"
        f"<td class='{_growth_class(total_growth)}'>"
        f"{total_growth:+.1f}%</td></tr>\n"
        f"<tr><td>Active Days</td>"
        f"<td class='{_growth_class(active_growth)}'>"
        f"{active_growth:+.1f}%</td></tr>\n"
        f"<tr><td>Consistency</td>"
        f"<td class='{_growth_class(consistency_change)}'>"
        f"{consistency_change:+.1f}pp</td></tr>\n"
        "</table>\n"
    )


def _html_pattern_rows(patterns: dict[str, Any]) -> str:
    """Generate HTML table rows for weekday patterns.

    Args:
        patterns: Pattern analysis dict with by_weekday key.

    Returns:
        HTML string with weekday bar rows.
    """
    by_weekday = patterns.get("by_weekday", {})
    rows = ""
    for day in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
        count = by_weekday.get(day, 0)
        max_wd = max(by_weekday.values()) if by_weekday else 1
        width = int(count / max_wd * 100) if max_wd > 0 else 0
        rows += (
            f"<div class='weekday-row'>"
            f"<span class='weekday-label'>{day}</span>"
            f"<div class='bar-container' style='flex:1'>"
            f"<div class='bar' style='width:{width}%'></div></div>"
            f"<span style='margin-left:8px'>{count}</span></div>\n"
        )
    return rows


def _html_patterns_section(
    target_a: str,
    target_b: str,
    patterns_a: dict[str, Any],
    patterns_b: dict[str, Any],
) -> str:
    """Generate HTML for contribution patterns comparison.

    Args:
        target_a: Label for target A.
        target_b: Label for target B.
        patterns_a: Pattern analysis dict for A.
        patterns_b: Pattern analysis dict for B.

    Returns:
        HTML string with patterns comparison.
    """
    most_a = patterns_a.get("most_active_day", "\u2014")
    peak_a = patterns_a.get("peak_month", "\u2014")
    cons_a = patterns_a.get("consistency_pct", 0)
    most_b = patterns_b.get("most_active_day", "\u2014")
    peak_b = patterns_b.get("peak_month", "\u2014")
    cons_b = patterns_b.get("consistency_pct", 0)

    return (
        "<h2>\U0001f4c5 Contribution Patterns</h2>\n"
        "<div class='comparison'>\n"
        f"  <div class='card'><h3>{target_a}</h3>\n"
        f"    {_html_pattern_rows(patterns_a)}\n"
        f"    <p style='margin-top:10px'>"
        f"Most active: <b>{most_a}</b> | "
        f"Peak month: <b>{peak_a}</b> | "
        f"Consistency: <b>{cons_a}%</b></p></div>\n"
        f"  <div class='card'><h3>{target_b}</h3>\n"
        f"    {_html_pattern_rows(patterns_b)}\n"
        f"    <p style='margin-top:10px'>"
        f"Most active: <b>{most_b}</b> | "
        f"Peak month: <b>{peak_b}</b> | "
        f"Consistency: <b>{cons_b}%</b></p></div>\n"
        "</div>\n"
    )


def _html_summary_rows(summary: dict[str, int]) -> str:
    """Generate HTML table rows for activity summary.

    Args:
        summary: Activity summary dict mapping type to count.

    Returns:
        HTML table rows string.
    """
    rows = ""
    for activity_type, count in sorted(summary.items(), key=lambda x: -x[1]):
        rows += f"<tr><td>{activity_type}</td><td>{count}</td></tr>\n"
    return rows


def _html_summary_section(
    target_a: str,
    target_b: str,
    summary_a: dict[str, int],
    summary_b: dict[str, int],
) -> str:
    """Generate HTML for activity summary comparison.

    Args:
        target_a: Label for target A.
        target_b: Label for target B.
        summary_a: Activity summary dict for A.
        summary_b: Activity summary dict for B.

    Returns:
        HTML string with summary tables.
    """
    return (
        "<h2>\U0001f4c8 Activity Summary</h2>\n"
        "<div class='comparison'>\n"
        f"  <div class='card'><h3>{target_a}</h3>"
        f"<table>{_html_summary_rows(summary_a)}</table></div>\n"
        f"  <div class='card'><h3>{target_b}</h3>"
        f"<table>{_html_summary_rows(summary_b)}</table></div>\n"
        "</div>\n"
    )
