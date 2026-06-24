# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""HTML export for comparison reports and team analytics."""

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
        f"<td class '{_growth_class(consistency_change)}'>"
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


# ---------------------------------------------------------------------------
# Team HTML export
# ---------------------------------------------------------------------------

_TEAM_CSS_EXTRA = (
    ".health-bar { height: 16px; background: #21262d; border-radius: 3px; "
    "overflow: hidden; margin: 4px 0; } "
    ".health-bar-fill { height: 16px; border-radius: 3px; display: inline-block; } "
    ".health-healthy { background: linear-gradient(90deg, #238636, #2ea043); } "
    ".health-moderate { background: linear-gradient(90deg, #9e6a03, #bb8009); } "
    ".health-declining { background: linear-gradient(90deg, #9a6700, #d29922); } "
    ".health-stale { background: linear-gradient(90deg, #da3633, #f85149); } "
    ".health-archived { background: #484f58; } "
    ".risk-critical { color: #f85149; font-weight: bold; } "
    ".risk-high { color: #d29922; font-weight: bold; } "
    ".risk-medium { color: #bb8009; font-weight: bold; } "
    ".risk-low { color: #3fb950; font-weight: bold; } "
    ".collab-cell { text-align: center; padding: 4px 6px; font-size: 0.85em; } "
    ".collab-none { color: #484f58; } "
    ".collab-low { color: #238636; } "
    ".collab-med { color: #2ea043; } "
    ".collab-high { color: #58a6ff; } "
    ".collab-max { color: #d2a8ff; font-weight: bold; } "
    "td.num { text-align: right; } "
)


def _health_class(status: str) -> str:
    """Return CSS class for health status bar fill."""
    if status in {"healthy", "moderate", "declining", "stale", "archived"}:
        return f"health-{status}"
    return "health-stale"


def _risk_class(bus_factor: int) -> str:
    """Return CSS class for bus factor risk level."""
    if bus_factor <= 1:
        return "risk-critical"
    if bus_factor <= 2:
        return "risk-high"
    if bus_factor <= 3:
        return "risk-medium"
    return "risk-low"


def _risk_label(bus_factor: int) -> str:
    """Return human-readable risk label for bus factor."""
    if bus_factor <= 1:
        return "CRITICAL"
    if bus_factor <= 2:
        return "HIGH"
    if bus_factor <= 3:
        return "MEDIUM"
    return "LOW"


def _collab_class(weight: int) -> str:
    """Return CSS class for collaboration heatmap cell weight."""
    if weight == 0:
        return "collab-none"
    if weight <= 1:
        return "collab-low"
    if weight <= 3:
        return "collab-med"
    if weight <= 6:
        return "collab-high"
    return "collab-max"


def _collab_symbol(weight: int) -> str:
    """Return Unicode symbol for collaboration weight."""
    if weight == 0:
        return "\u00b7"
    if weight <= 1:
        return "\u2591"
    if weight <= 3:
        return "\u2592"
    if weight <= 6:
        return "\u2593"
    return "\u2588"


def _render_team_html(data: dict[str, Any]) -> str:
    """Render team analytics data as HTML.

    Args:
        data: Team export data dict from the team CLI command.

    Returns:
        HTML string for the team analytics report.
    """
    target_name = data.get("target_name", "Organization")
    summary = data.get("summary", {})
    contributor_rankings = data.get("contributor_rankings", [])
    bus_factor_data = data.get("bus_factor", {})
    repo_health = data.get("repo_health", [])
    collab_data = data.get("collaboration", {})
    review_data = data.get("review_analytics", {})
    year = data.get("year")
    now_iso = datetime.now(UTC).isoformat()

    css = (
        "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
        "sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; "
        "background: #0d1117; color: #c9d1d9; } "
        "h1 { color: #58a6ff; border-bottom: 1px solid #30363d; padding-bottom: 10px; } "
        "h2 { color: #58a6ff; margin-top: 30px; } "
        "h3 { color: #58a6ff; margin-top: 15px; } "
        ".card { background: #161b22; border: 1px solid #30363d; "
        "border-radius: 8px; padding: 20px; margin: 15px 0; } "
        ".stat-grid { display: grid; "
        "grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: 10px; } "
        ".stat { text-align: center; } "
        ".stat-value { font-size: 1.8em; font-weight: bold; color: #58a6ff; } "
        ".stat-label { color: #8b949e; font-size: 0.85em; } "
        "table { width: 100%; border-collapse: collapse; margin-top: 10px; } "
        "th, td { padding: 8px; text-align: left; border-bottom: 1px solid #30363d; } "
        "th { color: #58a6ff; } " + _TEAM_CSS_EXTRA
    )

    year_label = f" ({year})" if year else ""
    html = (
        "<!DOCTYPE html>\n<html lang='en'>\n<head>\n"
        "  <meta charset='UTF-8'>\n"
        "  <meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"  <title>gh-stats — Team: {target_name}</title>\n"
        f"  <style>{css}</style>\n"
        "</head>\n<body>\n"
        f"  <h1>\U0001f4ca gh-stats — Team Analytics: {target_name}{year_label}</h1>\n"
        f"  <p style='color:#8b949e'>Generated: {now_iso}</p>\n"
    )

    # Summary card
    total_repos = summary.get("total_repos", 0)
    total_contributors = summary.get("total_contributors", 0)
    total_commits = summary.get("total_commits", 0)
    total_prs = summary.get("total_prs", 0)
    total_issues = summary.get("total_issues", 0)
    bus_factor = bus_factor_data.get("bus_factor", 0)
    avg_health = summary.get("avg_health", 0)

    html += (
        "<h2>\U0001f4cb Team Summary</h2>\n"
        "<div class='card'><div class='stat-grid'>\n"
        f"  {_html_stat_div(total_repos, 'Repositories')}\n"
        f"  {_html_stat_div(total_contributors, 'Contributors')}\n"
        f"  {_html_stat_div(total_commits, 'Commits (30d)')}\n"
        f"  {_html_stat_div(total_prs, 'Pull Requests')}\n"
        f"  {_html_stat_div(total_issues, 'Issues')}\n"
        f"  {_html_stat_div(bus_factor, 'Bus Factor')}\n"
        f"  {_html_stat_div(f'{avg_health:.0f}/100', 'Avg Health')}\n"
        "</div></div>\n"
    )

    # Contributor rankings
    html += _html_contributor_section(contributor_rankings)

    # Bus factor
    html += _html_bus_factor_section(bus_factor_data)

    # Repo health
    html += _html_repo_health_section(repo_health)

    # Collaboration
    html += _html_collaboration_section(collab_data)

    # Review analytics
    html += _html_review_section(review_data)

    # Activity trends
    trends = data.get("trends", {})
    html += _html_trends_section(trends)

    html += "\n</body>\n</html>"
    return html


def _html_contributor_section(contributors: list[dict[str, Any]]) -> str:
    """Generate HTML for contributor rankings table.

    Args:
        contributors: List of contributor dicts with rankings.

    Returns:
        HTML string with contributor rankings section.
    """
    html = "<h2>\U0001f465 Top Contributors</h2>\n"
    if not contributors:
        html += "<div class='card'><p>No contributor data available.</p></div>\n"
        return html

    html += (
        "<div class='card'><table>\n"
        "<tr><th>#</th><th>Contributor</th><th>Score</th>"
        "<th>Commits</th><th>PRs</th><th>Merged</th>"
        "<th>Reviews</th><th>Issues</th><th>Lines \u00b1</th></tr>\n"
    )
    for i, c in enumerate(contributors[:20], 1):
        login = c.get("login", "")
        score = c.get("score", 0)
        commits = c.get("commits", 0)
        prs_opened = c.get("prs_opened", 0)
        prs_merged = c.get("prs_merged", 0)
        reviews_given = c.get("reviews_given", 0)
        issues = c.get("issues_opened", 0) + c.get("issues_closed", 0)
        lines_added = c.get("lines_added", 0)
        lines_removed = c.get("lines_removed", 0)
        html += (
            f"<tr><td>{i}</td><td>@{login}</td>"
            f"<td class='num'>{score:.0f}</td>"
            f"<td class='num'>{commits}</td>"
            f"<td class='num'>{prs_opened}</td>"
            f"<td class='num'>{prs_merged}</td>"
            f"<td class='num'>{reviews_given}</td>"
            f"<td class='num'>{issues}</td>"
            f"<td class='num'>+{lines_added}/-{lines_removed}</td></tr>\n"
        )
    html += "</table></div>\n"
    return html


def _html_bus_factor_section(bus_factor_data: dict[str, Any]) -> str:
    """Generate HTML for bus factor section.

    Args:
        bus_factor_data: Bus factor computation results.

    Returns:
        HTML string with bus factor analysis.
    """
    bf = bus_factor_data.get("bus_factor", 0)
    if bf == 0:
        return (
            "<h2>\U0001f68c Bus Factor</h2>\n"
            "<div class='card'><p>Insufficient data to calculate bus factor.</p></div>\n"
        )

    threshold = bus_factor_data.get("threshold_pct", 50.0)
    coverage = bus_factor_data.get("coverage_pct", 0.0)
    total = bus_factor_data.get("total_contributors", 0)
    top = bus_factor_data.get("top_contributors", [])

    risk_css = _risk_class(bf)
    risk_label = _risk_label(bf)

    html = (
        "<h2>\U0001f68c Bus Factor</h2>\n"
        "<div class='card'>\n"
        f"  <p>Bus Factor: <b style='font-size:1.5em'>{bf}</b> "
        f"<span class='{risk_css}'>({risk_label} RISK)</span></p>\n"
        f"  <p>Covers {threshold:.0f}% of work | "
        f"Coverage by top {bf}: {coverage:.1f}% | "
        f"Total contributors: {total}</p>\n"
    )
    if top:
        html += "<h3>Top Contributors</h3><table>\n"
        html += "<tr><th>#</th><th>Contributor</th><th>Contributions</th><th>%</th></tr>\n"
        for i, tc in enumerate(top, 1):
            login = tc.get("login", "")
            contrib = tc.get("contributions", 0)
            pct = tc.get("pct", 0)
            html += (
                f"<tr><td>{i}</td><td>@{login}</td>"
                f"<td class='num'>{contrib}</td>"
                f"<td class='num'>{pct:.1f}%</td></tr>\n"
            )
        html += "</table>\n"
    html += "</div>\n"
    return html


def _html_repo_health_section(repos: list[dict[str, Any]]) -> str:
    """Generate HTML for repository health matrix.

    Args:
        repos: List of repo health dicts.

    Returns:
        HTML string with repo health section.
    """
    html = "<h2>\U0001f3e5 Repository Health</h2>\n"
    if not repos:
        html += "<div class='card'><p>No repository data available.</p></div>\n"
        return html

    html += (
        "<div class='card'><table>\n"
        "<tr><th>Repo</th><th>Score</th><th>Status</th><th>Lang</th>"
        "<th>\u2b50</th><th>Commits (30d)</th><th>PRs Open</th>"
        "<th>Merged (30d)</th><th>Issues</th><th>Contributors</th></tr>\n"
    )
    for repo in repos[:20]:
        name = repo.get("name", "")
        score = repo.get("health_score", 0)
        status = repo.get("status", "unknown")
        lang = repo.get("language") or "\u2014"
        stars = repo.get("stars", 0)
        commits_30d = repo.get("commits_30d", 0)
        prs_open = repo.get("prs_open", 0)
        prs_merged = repo.get("prs_merged_30d", 0)
        issues_open = repo.get("issues_open", 0)
        contrib = repo.get("contributors_count", 0)

        health_css = _health_class(status)
        bar_width = max(score, 0)
        html += (
            f"<tr><td>{name}</td>"
            f"<td class='num'>{score} "
            f"<div class='health-bar'>"
            f"<div class='health-bar-fill {health_css}' "
            f"style='width:{bar_width}%'></div></div></td>"
            f"<td>{status}</td><td>{lang}</td>"
            f"<td class='num'>{stars}</td>"
            f"<td class='num'>{commits_30d}</td>"
            f"<td class='num'>{prs_open}</td>"
            f"<td class='num'>{prs_merged}</td>"
            f"<td class='num'>{issues_open}</td>"
            f"<td class='num'>{contrib}</td></tr>\n"
        )
    html += "</table></div>\n"
    return html


def _html_collaboration_section(collab_data: dict[str, Any]) -> str:
    """Generate HTML for collaboration heatmap.

    Args:
        collab_data: Collaboration matrix results.

    Returns:
        HTML string with collaboration section.
    """
    nodes = collab_data.get("nodes", [])
    edges = collab_data.get("edges", [])
    total = collab_data.get("total_collaborations", 0)

    html = "<h2>\U0001f91d Collaboration Network</h2>\n"
    if not nodes:
        html += "<div class='card'><p>No collaboration data available.</p></div>\n"
        return html

    top_logins = [n["login"] for n in nodes[:15]]
    login_to_idx = {login: i for i, login in enumerate(top_logins)}

    size = len(top_logins)
    matrix = [[0] * size for _ in range(size)]
    for edge in edges:
        src = edge.get("source", "")
        tgt = edge.get("target", "")
        weight = edge.get("weight", 0)
        if src in login_to_idx and tgt in login_to_idx:
            i, j = login_to_idx[src], login_to_idx[tgt]
            matrix[i][j] = weight
            matrix[j][i] = weight

    html += f"<div class='card'><p>Total collaboration edges: {total}</p>\n<table><tr><th></th>\n"
    for login in top_logins:
        html += f"<th class='collab-cell'>{login[:6]}</th>\n"
    html += "</tr>\n"

    for i, login in enumerate(top_logins):
        html += f"<tr><th>{login[:6]}</th>\n"
        for j in range(size):
            weight = matrix[i][j]
            cell_css = _collab_class(weight)
            symbol = _collab_symbol(weight)
            html += f"<td class='collab-cell {cell_css}'>{symbol}</td>\n"
        html += "</tr>\n"
    html += "</table></div>\n"
    return html


def _html_review_section(review_data: dict[str, Any]) -> str:
    """Generate HTML for review analytics section.

    Args:
        review_data: Review analytics computation results.

    Returns:
        HTML string with review analytics section.
    """
    total_prs = review_data.get("total_prs", 0)
    if total_prs == 0:
        return (
            "<h2>\U0001f441 Code Review Analytics</h2>\n"
            "<div class='card'><p>No PR data available for review analytics.</p></div>\n"
        )

    prs_with_reviews = review_data.get("prs_with_reviews", 0)
    pct_reviewed = review_data.get("pct_prs_reviewed", 0.0)
    avg_reviews = review_data.get("avg_reviews_per_pr", 0.0)
    approvals = review_data.get("approval_count", 0)
    changes = review_data.get("changes_requested_count", 0)
    comments = review_data.get("comment_only_count", 0)
    avg_time = review_data.get("avg_time_to_first_review_hours", 0.0)
    median_time = review_data.get("median_time_to_first_review_hours", 0.0)
    top_reviewers = review_data.get("top_reviewers", [])

    html = (
        "<h2>\U0001f441 Code Review Analytics</h2>\n"
        "<div class='card'>\n"
        "  <div class='stat-grid'>\n"
        f"    {_html_stat_div(f'{prs_with_reviews}/{total_prs}', 'PRs Reviewed')}\n"
        f"    {_html_stat_div(f'{pct_reviewed:.1f}%', 'Coverage')}\n"
        f"    {_html_stat_div(f'{avg_reviews:.1f}', 'Avg Reviews/PR')}\n"
        f"    {_html_stat_div(f'{avg_time:.1f}h', 'Avg Time')}\n"
        f"    {_html_stat_div(f'{median_time:.1f}h', 'Median Time')}\n"
        "  </div>\n"
        "  <h3>Review Outcomes</h3>\n"
        "  <table><tr><th>Outcome</th><th>Count</th></tr>\n"
        f"    <tr><td>\u2705 Approvals</td><td class='num'>{approvals}</td></tr>\n"
        f"    <tr><td>\u26a0\ufe0f Changes Requested</td><td class='num'>{changes}</td></tr>\n"
        f"    <tr><td>\U0001f4ac Comments Only</td><td class='num'>{comments}</td></tr>\n"
        "  </table>\n"
    )
    if top_reviewers:
        html += "  <h3>Top Reviewers</h3>\n"
        html += "  <table><tr><th>#</th><th>Reviewer</th><th>Reviews</th></tr>\n"
        for i, tr in enumerate(top_reviewers, 1):
            html += (
                f"<tr><td>{i}</td><td>@{tr['login']}</td>"
                f"<td class='num'>{tr['reviews']}</td></tr>\n"
            )
        html += "</table>\n"
    html += "</div>\n"
    return html


def _html_trends_section(trends: dict[str, Any]) -> str:
    """Generate HTML for activity trends section.

    Args:
        trends: Team trends computation results.

    Returns:
        HTML string with activity trends.
    """
    period_labels = trends.get("period_labels", [])
    metrics = trends.get("metrics", {})
    trend_dirs = trends.get("trends", {})
    top_authors = trends.get("top_authors", [])

    if not period_labels:
        return (
            "<h2>\U0001f4c8 Activity Trends</h2>\n"
            "<div class='card'><p>No trend data available.</p></div>\n"
        )

    commits_data = metrics.get("commits", [])
    prs_opened = metrics.get("prs_opened", [])
    prs_merged = metrics.get("prs_merged", [])
    issues_opened = metrics.get("issues_opened", [])
    issues_closed = metrics.get("issues_closed", [])

    html = "<h2>\U0001f4c8 Activity Trends</h2>\n"

    commits_dir = trend_dirs.get("commits", "stable")
    prs_dir = trend_dirs.get("prs_merged", "stable")
    issues_dir = trend_dirs.get("issues_closed", "stable")

    dir_icons = {
        "increasing": "\u2191 Increasing",
        "decreasing": "\u2193 Decreasing",
        "stable": "\u2192 Stable",
        "new": "\U0001f195 New",
    }

    html += (
        "<div class='card' style='display:grid;"
        "grid-template-columns:1fr 1fr 1fr;gap:10px'>\n"
        f"  <div class='stat'><div class='stat-value'>"
        f"{dir_icons.get(commits_dir, commits_dir)}</div>"
        f"<div class='stat-label'>Commits</div></div>\n"
        f"  <div class='stat'><div class='stat-value'>"
        f"{dir_icons.get(prs_dir, prs_dir)}</div>"
        f"<div class='stat-label'>PR Merges</div></div>\n"
        f"  <div class='stat'><div class='stat-value'>"
        f"{dir_icons.get(issues_dir, issues_dir)}</div>"
        f"<div class='stat-label'>Issue Closes</div></div>\n"
        "</div>\n"
    )

    html += (
        "<div class='card'><table>\n"
        "<tr><th>Period</th><th>Commits</th><th>PRs Opened</th>"
        "<th>PRs Merged</th><th>Issues Opened</th>"
        "<th>Issues Closed</th></tr>\n"
    )
    for i, label in enumerate(period_labels):
        c = commits_data[i] if i < len(commits_data) else 0
        po = prs_opened[i] if i < len(prs_opened) else 0
        pm = prs_merged[i] if i < len(prs_merged) else 0
        io = issues_opened[i] if i < len(issues_opened) else 0
        ic = issues_closed[i] if i < len(issues_closed) else 0
        html += (
            f"<tr><td>{label}</td>"
            f"<td class='num'>{c}</td>"
            f"<td class='num'>{po}</td>"
            f"<td class='num'>{pm}</td>"
            f"<td class='num'>{io}</td>"
            f"<td class='num'>{ic}</td></tr>\n"
        )
    html += "</table></div>\n"

    if top_authors:
        html += "<div class='card'><h3>Top Authors Over Time</h3>\n"
        html += "<table><tr><th>Author</th><th>Total</th><th>Per Period</th></tr>\n"
        for author in top_authors[:8]:
            login = author.get("login", "")
            total = author.get("total", 0)
            per_period = author.get("per_period", [])
            max_val = max(per_period) if per_period and max(per_period) > 0 else 1
            bars = ""
            for v in per_period:
                width = int(v / max_val * 100) if max_val > 0 else 0
                color = "#238636" if v > 0 else "#484f58"
                bars += (
                    f"<span style='display:inline-block;"
                    f"height:12px;background:{color};"
                    f"border-radius:2px;margin-right:2px;"
                    f"width:{max(width, 5)}%' title='{v}'></span>"
                )
            html += f"<tr><td>@{login}</td><td class='num'>{total}</td><td>{bars}</td></tr>\n"
        html += "</table></div>\n"

    return html
