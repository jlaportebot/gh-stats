# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""Activity heatmap module — compute contribution heatmap data from events."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any


def compute_activity_heatmap(
    events: list[dict[str, Any]],
    *,
    days: int = 365,
) -> dict[str, Any]:
    """Compute a GitHub-style activity heatmap from events.

    Produces a grid of dates with contribution counts, suitable for
    terminal rendering or HTML export.

    Args:
        events: List of event dicts with ``created_at`` field.
        days: Number of days to look back (default 365).

    Returns:
        Dict with heatmap grid, total, max, and streak data.
    """
    now = datetime.now(UTC)
    start = now - timedelta(days=days)

    # Build date -> count mapping
    date_counts: dict[str, int] = defaultdict(int)
    for event in events:
        date_str = event.get("created_at", "")[:10]  # YYYY-MM-DD
        if date_str:
            date_counts[date_str] += 1

    # Build week grid (columns = weeks, rows = days of week)
    total_contributions = 0
    max_count = 0
    grid: list[list[dict[str, Any]]] = []

    # Align to Sunday start
    current = start
    while current.weekday() != 6:  # Sunday
        current -= timedelta(days=1)

    longest_streak = 0
    current_streak = 0
    best_day = ""
    best_day_count = 0

    week: list[dict[str, Any]] = []
    while current <= now:
        date_iso = current.strftime("%Y-%m-%d")
        count = date_counts.get(date_iso, 0)
        total_contributions += count
        max_count = max(max_count, count)

        if count > best_day_count:
            best_day_count = count
            best_day = date_iso

        if count > 0:
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

        week.append({"date": date_iso, "count": count})
        if current.weekday() == 6:  # End of week
            grid.append(week)
            week = []

        current += timedelta(days=1)

    if week:
        grid.append(week)

    # Month labels for column headers
    month_labels: list[tuple[int, str]] = []
    seen_months: set[str] = set()
    for col_idx, week_data in enumerate(grid):
        for day_data in week_data:
            month = day_data["date"][:7]  # YYYY-MM
            if month not in seen_months:
                seen_months.add(month)
                month_labels.append((col_idx, month))

    # Weekly totals
    weekly_totals: list[int] = [sum(d["count"] for d in week) for week in grid]

    return {
        "grid": grid,
        "total_contributions": total_contributions,
        "max_count": max_count,
        "longest_streak": longest_streak,
        "current_streak": current_streak,
        "best_day": best_day,
        "best_day_count": best_day_count,
        "month_labels": month_labels,
        "weekly_totals": weekly_totals,
    }
