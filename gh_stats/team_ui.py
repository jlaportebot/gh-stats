# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Team dashboard UI — renders team analytics components."""

from __future__ import annotations

from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Status colors
STATUS_COLORS = {
    "healthy": "green",
    "moderate": "yellow",
    "declining": "orange3",
    "stale": "red",
    "archived": "dim",
    "disabled": "dim",
}


def render_contributor_table(
    contributors: list[dict[str, Any]], *, limit: int = 15, title: str = "👥 Top Contributors"
) -> Panel:
    """Render a table of top contributors with their metrics.

    Returns:
        Rich Panel with contributor table.
    """
    if not contributors:
        return Panel(
            Text(" No contributor data available", style="dim"),
            title=title,
            border_style="white",
            padding=(1, 2),
        )

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Rank", style="dim", width=5, justify="right")
    table.add_column("Contributor", style="bright_blue", min_width=20)
    table.add_column("Score", style="bold green", justify="right", width=8)
    table.add_column("Commits", style="white", justify="right", width=8)
    table.add_column("PRs", style="bright_magenta", justify="right", width=6)
    table.add_column("Merged", style="green", justify="right", width=7)
    table.add_column("Reviews", style="bright_cyan", justify="right", width=8)
    table.add_column("Issues", style="yellow", justify="right", width=7)
    table.add_column("Lines ±", style="dim", justify="right", width=10)

    for i, c in enumerate(contributors[:limit], 1):
        login = c.get("login", "")
        # Show avatar as emoji placeholder since we can't render images in terminal
        display_name = f"@{login}"
        score = c.get("score", 0)
        commits = c.get("commits", 0)
        prs_opened = c.get("prs_opened", 0)
        prs_merged = c.get("prs_merged", 0)
        reviews = c.get("reviews_given", 0)
        issues = c.get("issues_opened", 0) + c.get("issues_closed", 0)
        lines_added = c.get("lines_added", 0)
        lines_removed = c.get("lines_removed", 0)

        table.add_row(
            str(i),
            display_name,
            f"{score:.0f}",
            str(commits),
            str(prs_opened),
            str(prs_merged),
            str(reviews),
            str(issues),
            f"+{lines_added}/-{lines_removed}",
        )

    return Panel(table, title=title, border_style="bright_blue", padding=(1, 2))


def render_bus_factor(bus_factor_data: dict[str, Any]) -> Panel:
    """Render the bus factor visualization.

    Returns:
        Rich Panel with bus factor visualization.
    """
    bf = bus_factor_data.get("bus_factor", 0)
    threshold = bus_factor_data.get("threshold_pct", 50.0)
    top_contributors = bus_factor_data.get("top_contributors", [])
    coverage = bus_factor_data.get("coverage_pct", 0.0)
    total = bus_factor_data.get("total_contributors", 0)

    if bf == 0:
        return Panel(
            Text(" Insufficient data to calculate bus factor", style="dim"),
            title="🚌 Bus Factor",
            border_style="white",
            padding=(1, 2),
        )

    text = Text()
    text.append(" Bus Factor: ", style="bold")
    text.append(f"{bf}", style="bold bright_red")
    text.append(f" (covers {threshold:.0f}% of work)\n")
    text.append(f" Coverage by top {bf}: ", style="dim")
    text.append(f"{coverage:.1f}%\n", style="bold white")
    text.append(" Total contributors: ", style="dim")
    text.append(f"{total}\n", style="white")
    text.append("\n")

    if top_contributors:
        text.append(" Top contributors:\n", style="bold")
        for i, tc in enumerate(top_contributors, 1):
            pct = tc.get("pct", 0)
            login = tc.get("login", "")
            text.append(f"  {i}. @{login} — ", style="dim")
            text.append(f"{pct:.1f}%", style="bold white")
            text.append("\n")

    # Visual indicator
    text.append("\n Risk level: ", style="bold")
    if bf <= 1:
        text.append("🔴 CRITICAL — Single point of failure", style="bold red")
    elif bf <= 2:
        text.append("🟠 HIGH — Very concentrated", style="bold orange3")
    elif bf <= 3:
        text.append("🟡 MEDIUM — Small core team", style="bold yellow")
    else:
        text.append("🟢 LOW — Well distributed", style="bold green")

    return Panel(text, title="🚌 Bus Factor", border_style="bright_red", padding=(1, 2))


def render_repo_health_matrix(
    repos: list[dict[str, Any]], *, limit: int = 15, title: str = "🏥 Repository Health"
) -> Panel:
    """Render a table of repository health scores.

    Returns:
        Rich Panel with repository health table.
    """
    if not repos:
        return Panel(
            Text(" No repository data available", style="dim"),
            title=title,
            border_style="white",
            padding=(1, 2),
        )

    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Repo", style="bright_blue", min_width=20)
    table.add_column("Score", style="bold", justify="right", width=6)
    table.add_column("Status", style="bold", width=12)
    table.add_column("Lang", style="green", width=10)
    table.add_column("⭐", style="bright_yellow", justify="right", width=5)
    table.add_column("Commits (30d)", style="white", justify="right", width=12)
    table.add_column("PRs Open", style="bright_magenta", justify="right", width=8)
    table.add_column("Merged (30d)", style="green", justify="right", width=10)
    table.add_column("Issues", style="yellow", justify="right", width=7)
    table.add_column("Contrib", style="cyan", justify="right", width=7)

    for repo in repos[:limit]:
        name = repo.get("name", "")
        score = repo.get("health_score", 0)
        status = repo.get("status", "unknown")
        lang = repo.get("language") or "—"
        stars = repo.get("stars", 0)
        commits_30d = repo.get("commits_30d", 0)
        prs_open = repo.get("prs_open", 0)
        prs_merged = repo.get("prs_merged_30d", 0)
        issues_open = repo.get("issues_open", 0)
        contrib = repo.get("contributors_count", 0)

        status_color = STATUS_COLORS.get(status, "white")

        table.add_row(
            name,
            f"{score}",
            f"[{status_color}]{status}[/{status_color}]",
            lang,
            str(stars),
            str(commits_30d),
            str(prs_open),
            str(prs_merged),
            str(issues_open),
            str(contrib),
        )

    return Panel(table, title=title, border_style="green", padding=(1, 2))


def render_collaboration_heatmap(
    collab_data: dict[str, Any], *, limit: int = 15, title: str = "🤝 Collaboration Network"
) -> Panel:
    """Render a text-based collaboration heatmap.

    Returns:
        Rich Panel with collaboration heatmap.
    """
    nodes = collab_data.get("nodes", [])
    edges = collab_data.get("edges", [])
    total = collab_data.get("total_collaborations", 0)

    if not nodes:
        return Panel(
            Text(" No collaboration data available", style="dim"),
            title=title,
            border_style="white",
            padding=(1, 2),
        )

    # Build adjacency for top contributors
    top_logins = [n["login"] for n in nodes[:limit]]
    login_to_idx = {login: i for i, login in enumerate(top_logins)}

    # Create matrix
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

    # Render as text
    text = Text()
    text.append(f" Total collaboration edges: {total}\n\n", style="dim")

    # Header row
    text.append("      ")
    for login in top_logins:
        text.append(f" {login[:4]:>4} ", style="bold cyan")
    text.append("\n")

    # Matrix rows
    for i, login in enumerate(top_logins):
        text.append(f" {login[:6]:>6} ", style="bright_blue")
        for j in range(size):
            weight = matrix[i][j]
            if weight == 0:
                text.append("  ·  ", style="dim")
            elif weight == 1:
                text.append("  ░  ", style="color(28)")
            elif weight <= 3:
                text.append("  ▒  ", style="color(34)")
            elif weight <= 6:
                text.append("  ▓  ", style="color(40)")
            else:
                text.append("  █  ", style="color(46)")
        text.append("\n")

    text.append("\n  Legend: ·=none ░=1 ▒=2-3 ▓=4-6 █=7+\n", style="dim")

    return Panel(text, title=title, border_style="magenta", padding=(1, 2))


def render_review_analytics(review_data: dict[str, Any]) -> Panel:
    """Render code review analytics.

    Returns:
        Rich Panel with review analytics.
    """
    total_prs = review_data.get("total_prs", 0)
    prs_with_reviews = review_data.get("prs_with_reviews", 0)
    pct_reviewed = review_data.get("pct_prs_reviewed", 0.0)
    avg_reviews = review_data.get("avg_reviews_per_pr", 0.0)
    approvals = review_data.get("approval_count", 0)
    changes = review_data.get("changes_requested_count", 0)
    comments = review_data.get("comment_only_count", 0)
    avg_time = review_data.get("avg_time_to_first_review_hours", 0.0)
    median_time = review_data.get("median_time_to_first_review_hours", 0.0)
    top_reviewers = review_data.get("top_reviewers", [])

    if total_prs == 0:
        return Panel(
            Text(" No PR data available for review analytics", style="dim"),
            title="👁 Code Review Analytics",
            border_style="white",
            padding=(1, 2),
        )

    text = Text()
    text.append(" Review Coverage\n", style="bold")
    text.append("  PRs with reviews: ", style="dim")
    text.append(f"{prs_with_reviews}/{total_prs}", style="bold white")
    pct_color = "green" if pct_reviewed > 80 else "yellow" if pct_reviewed > 50 else "red"
    text.append(f" ({pct_reviewed:.1f}%)\n", style=pct_color)
    text.append("  Avg reviews/PR: ", style="dim")
    text.append(f"{avg_reviews:.1f}\n", style="white")
    text.append("\n")

    text.append(" Review Outcomes\n", style="bold")
    text.append("  ✅ Approvals: ", style="dim")
    text.append(f"{approvals}\n", style="green")
    text.append("  ⚠️  Changes requested: ", style="dim")
    text.append(f"{changes}\n", style="orange3")
    text.append("  💬 Comments only: ", style="dim")
    text.append(f"{comments}\n", style="cyan")
    text.append("\n")

    text.append(" Time to First Review\n", style="bold")
    text.append("  Average: ", style="dim")
    text.append(f"{avg_time:.1f} hours\n", style="white")
    text.append("  Median: ", style="dim")
    text.append(f"{median_time:.1f} hours\n", style="white")
    text.append("\n")

    if top_reviewers:
        text.append(" Top Reviewers\n", style="bold")
        for i, tr in enumerate(top_reviewers, 1):
            text.append(f"  {i}. @{tr['login']} — ", style="dim")
            text.append(f"{tr['reviews']} reviews", style="bold white")
            text.append("\n")

    return Panel(text, title="👁 Code Review Analytics", border_style="bright_cyan", padding=(1, 2))


def render_team_summary(
    org_name: str,
    total_repos: int,
    total_contributors: int,
    total_commits: int,
    total_prs: int,
    total_issues: int,
    bus_factor: int,
    avg_health: float,
) -> Panel:
    """Render a summary panel for the team/org.

    Returns:
        Rich Panel with team summary.
    """
    text = Text()
    text.append(f" Organization: @{org_name}\n\n", style="bold bright_blue")

    # Stats grid
    stats = [
        ("📦 Repositories", str(total_repos)),
        ("👥 Contributors", str(total_contributors)),
        ("📝 Commits (30d)", str(total_commits)),
        ("🔀 Pull Requests", str(total_prs)),
        ("❗ Issues", str(total_issues)),
        ("🚌 Bus Factor", str(bus_factor)),
        ("🏥 Avg Repo Health", f"{avg_health:.0f}/100"),
    ]

    for label, value in stats:
        text.append(f" {label}: ", style="dim")
        text.append(f"{value}\n", style="bold white")

    # Health indicator
    text.append("\n Overall Health: ", style="bold")
    if avg_health >= 80:
        text.append("🟢 EXCELLENT", style="bold green")
    elif avg_health >= 60:
        text.append("🟢 GOOD", style="bold green")
    elif avg_health >= 40:
        text.append("🟡 FAIR", style="bold yellow")
    elif avg_health >= 20:
        text.append("🟠 POOR", style="bold orange3")
    else:
        text.append("🔴 CRITICAL", style="bold red")

    return Panel(text, title="📋 Team Summary", border_style="bright_blue", padding=(1, 2))
