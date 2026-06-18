# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Rich terminal UI — renders the dashboard components."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from rich.panel import Panel
from rich.table import Table
from rich.text import Text

# Weekday labels for the heatmap (Sun–Sat)
_DAY_LABELS = ["", "Mon", "", "Wed", "", "Fri", ""]
_MONTH_LABELS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]

# Block characters for contribution intensity
_HEATMAP_BLOCKS = ["░", "▒", "▓", "█"]

# Color gradient for contributions (green scale)
_HEATMAP_COLORS = [
    "",  # 0 — no contributions
    "color(28)",  # 1 — light green
    "color(34)",  # 2 — medium green
    "color(40)",  # 3 — bright green
    "color(46)",  # 4+ — intense green
]

# Constants for time calculations
SECONDS_PER_HOUR = 3600
DAYS_PER_WEEK = 7
WEEKS_PER_YEAR = 52


def _intensity_level(count: int) -> int:
    """Map a contribution count to a 0–4 intensity level.

    Returns:
        Intensity level (0-4).
    """
    if count == 0:
        return 0
    if count <= 2:
        return 1
    if count <= 5:
        return 2
    if count <= 10:
        return 3
    return 4


def render_profile_card(stats: dict[str, Any], contributions_total: int) -> Panel:
    """Render the user profile card.

    Returns:
        Rich Panel with profile information.
    """
    name = stats.get("name", stats.get("login", ""))
    login = stats.get("login", "")
    bio = stats.get("bio", "")

    content = Text()
    content.append(f" {name}", style="bold white")
    content.append(f" (@{login})\n", style="bright_cyan")
    if bio:
        content.append(f" {bio}\n", style="dim")
    content.append("\n")
    content.append(" 📦 Repos:    ", style="dim")
    content.append(f"{stats.get('public_repos', 0)}\n", style="bold white")
    content.append(" ⭐ Followers: ", style="dim")
    content.append(f"{stats.get('followers', 0)}\n", style="bold white")
    content.append(" 👥 Following: ", style="dim")
    content.append(f"{stats.get('following', 0)}\n", style="bold white")
    content.append(" 🔥 Contributions (this year): ", style="dim")
    content.append(f"{contributions_total}\n", style="bold green")

    return Panel(content, title="👤 Profile", border_style="bright_blue", padding=(1, 2))


def render_heatmap(contributions: dict[str, int], year: int | None = None) -> Panel:
    """Render a GitHub-style contribution heatmap in the terminal.

    Builds a grid of Unicode block characters with green color scaling,
    mirroring the classic GitHub contribution graph.

    Returns:
        Rich Panel with the heatmap.
    """
    now = datetime.now(UTC)
    if year is None:
        year = now.year

    # Determine date range: 52 weeks ending today (or Dec 31 for past years)
    if year == now.year:
        end_date = now.date()
    else:
        end_date = datetime(year, 12, 31).date()

    start_date = end_date - timedelta(weeks=WEEKS_PER_YEAR)
    # Align to Sunday
    start_date = start_date - timedelta(days=(start_date.weekday() + 1) % 7)

    # Build 7×53 grid (rows=days of week Sun–Sat, cols=weeks)
    rows = 7
    cols = 53
    grid: list[list[tuple[str, int]]] = [[("", 0) for _ in range(cols)] for _ in range(rows)]

    current = start_date
    week = 0
    month_starts: dict[int, str] = {}  # week_index -> month_label

    while current <= end_date and week < cols:
        dow = (current.weekday() + 1) % 7  # 0=Sun, 1=Mon, ..., 6=Sat
        date_str = current.isoformat()
        count = contributions.get(date_str, 0)
        level = _intensity_level(count)
        block = _HEATMAP_BLOCKS[level] if level > 0 else "░"
        grid[dow][week] = (block, level)

        # Track month transitions for header labels
        if current.day == 1:
            month_starts[week] = _MONTH_LABELS[current.month - 1]

        if dow == 6:
            week += 1
        current += timedelta(days=1)

    # Render the heatmap as Rich Text
    text = Text()

    # Month header row
    text.append("   ")  # space for day labels
    prev_month = ""
    for w in range(cols):
        label = month_starts.get(w, "")
        if label and label != prev_month:
            text.append(f"{label} ", style="dim")
            prev_month = label
        else:
            text.append("   ")
    text.append("\n")

    # Day rows
    for dow in range(rows):
        label = _DAY_LABELS[dow] if dow < len(_DAY_LABELS) else ""
        text.append(f"{label:3}")

        for w in range(cols):
            char, level = grid[dow][w]
            if level > 0:
                color = _HEATMAP_COLORS[level]
                text.append(char, style=color)
            else:
                text.append(char, style="color(237)")  # dark gray for empty
        text.append("\n")

    # Legend
    text.append("\n  Less ", style="dim")
    for block, color in zip(_HEATMAP_BLOCKS, _HEATMAP_COLORS[1:]):
        text.append(block, style=color)
    text.append(" More", style="dim")

    return Panel(text, title="📊 Contribution Heatmap", border_style="green", padding=(1, 2))


def render_activity_timeline(activities: list[dict[str, Any]], limit: int = 20) -> Panel:
    """Render the recent activity timeline.

    Returns:
        Rich Panel with activity table.
    """
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("When", style="dim", width=16)
    table.add_column("Type", style="bold", width=8)
    table.add_column("Repository", style="bright_blue", width=30)
    table.add_column("Detail", style="white", min_width=20)

    now = datetime.now(UTC)
    type_icons = {
        "push": "⬆ Push",
        "pr": "🔀 PR",
        "issue": "❗ Issue",
        "review": "👁 Review",
        "release": "🏷 Release",
        "star": "⭐ Star",
        "fork": "🍴 Fork",
        "create": "+ Create",
        "delete": "- Delete",
        "comment": "💬 Comment",
    }

    for activity in activities[:limit]:
        time = activity.get("time", now)
        if isinstance(time, datetime):
            delta = now - time
            if delta.days == 0:
                when = (
                    f"{delta.seconds // SECONDS_PER_HOUR}h ago"
                    if delta.seconds >= SECONDS_PER_HOUR
                    else "just now"
                )
            elif delta.days == 1:
                when = "yesterday"
            elif delta.days < DAYS_PER_WEEK:
                when = f"{delta.days}d ago"
            else:
                when = time.strftime("%b %d")
        else:
            when = str(time)

        type_label = type_icons.get(activity["type"], activity["type"])
        repo = activity.get("repo", "")
        detail = activity.get("detail", "")[:60]

        table.add_row(when, type_label, repo, detail)

    return Panel(table, title="🕐 Recent Activity", border_style="yellow", padding=(1, 2))


def render_language_chart(lang_stats: dict[str, int]) -> Panel:
    """Render language distribution as a horizontal bar chart.

    Returns:
        Rich Panel with language chart.
    """
    if not lang_stats:
        return Panel(
            Text(" No language data available", style="dim"),
            title="🔤 Languages",
            border_style="magenta",
            padding=(1, 2),
        )

    total = sum(lang_stats.values())
    max_count = max(lang_stats.values())

    # Distinct colors for languages
    lang_colors = [
        "bright_blue",
        "bright_green",
        "bright_red",
        "bright_magenta",
        "bright_cyan",
        "bright_yellow",
        "color(208)",
        "color(141)",
        "color(202)",
        "color(117)",
        "color(213)",
        "color(156)",
    ]

    text = Text()
    for i, (lang, count) in enumerate(lang_stats.items()):
        pct = count / total * 100
        bar_width = int(count / max_count * 30)
        color = lang_colors[i % len(lang_colors)]

        text.append(f" {lang:15}", style="bold")
        text.append(f" {count:3} repos ", style="dim")
        text.append("█" * bar_width, style=color)
        text.append(f" {pct:.0f}%\n", style="dim")

    return Panel(text, title="🔤 Languages", border_style="magenta", padding=(1, 2))


def render_repo_table(repo_stats: list[dict[str, Any]], limit: int = 10) -> Panel:
    """Render a table of top repositories by stars.

    Returns:
        Rich Panel with repository table.
    """
    table = Table(show_header=True, header_style="bold cyan", box=None, padding=(0, 1))
    table.add_column("Repository", style="bright_blue", min_width=25)
    table.add_column("⭐", style="bright_yellow", justify="right", width=6)
    table.add_column("🍴", style="dim", justify="right", width=6)
    table.add_column("Lang", style="green", width=10)
    table.add_column("Description", style="white", min_width=20)

    for repo in repo_stats[:limit]:
        table.add_row(
            repo["name"],
            str(repo["stars"]),
            str(repo["forks"]),
            repo["language"],
            repo["description"],
        )

    return Panel(table, title="🏆 Top Repositories", border_style="bright_cyan", padding=(1, 2))


def render_summary_bar(summary: dict[str, int]) -> Panel:
    """Render a compact summary bar of activity by type.

    Returns:
        Rich Panel with summary bar.
    """
    if not summary:
        return Panel(
            Text(" No activity data", style="dim"),
            title="📈 Activity Summary",
            border_style="white",
            padding=(1, 2),
        )

    icons = {
        "push": "⬆ Pushes",
        "pr": "🔀 PRs",
        "issue": "❗ Issues",
        "review": "👁 Reviews",
        "release": "🏷 Releases",
        "star": "⭐ Stars",
        "fork": "🍴 Forks",
        "create": "+ Creates",
        "delete": "- Deletes",
        "comment": "💬 Comments",
    }

    parts = []
    for activity_type, count in sorted(summary.items(), key=lambda x: -x[1]):
        label = icons.get(activity_type, activity_type)
        parts.append(f"{label}: [bold]{count}[/bold]")

    content = "  ".join(parts)
    return Panel(content, title="📈 Activity Summary", border_style="white", padding=(1, 2))
