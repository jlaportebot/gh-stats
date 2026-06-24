# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""CLI entry point — orchestrates API calls and renders the dashboard."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TaskID, TextColumn

if TYPE_CHECKING:
    from collections.abc import Callable

from . import __version__
from .activity import (
    categorize_events,
    compute_activity_summary,
    compute_comparison_summary,
    compute_contribution_patterns,
    compute_growth_metrics,
    compute_language_stats,
    compute_repo_stats,
    compute_streaks,
)
from .api import (
    ApiError,
    AuthError,
    get_authenticated_user,
    get_contributions,
    get_org_contributions,
    get_org_events,
    get_org_members,
    get_org_repos,
    get_org_stats,
    get_pull_request_reviews,
    get_repo_commits,
    get_repo_contributors,
    get_repo_issues,
    get_repo_pull_requests,
    get_token,
    get_user_events,
    get_user_repos,
    get_user_stats,
)
from .html_export import _render_comparison_html
from .team import (
    compute_bus_factor,
    compute_collaboration_matrix,
    compute_contributor_rankings,
    compute_repo_health_scores,
    compute_review_analytics,
)
from .team_ui import (
    render_bus_factor,
    render_collaboration_heatmap,
    render_contributor_table,
    render_repo_health_matrix,
    render_review_analytics,
    render_team_summary,
)
from .ui import (
    _render_html,
    render_activity_timeline,
    render_comparison_activity_timelines,
    render_comparison_heatmap,
    render_comparison_language_charts,
    render_comparison_patterns,
    render_comparison_profile_cards,
    render_comparison_repo_tables,
    render_comparison_streaks,
    render_comparison_summary_bars,
    render_growth_metrics,
    render_heatmap,
    render_language_chart,
    render_members_table,
    render_profile_card,
    render_repo_table,
    render_streaks,
    render_summary_bar,
)

console = Console()


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------


def common_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to add common options to subcommands (show, compare).

    Returns:
        The decorated command with common options added.
    """
    func = click.option(
        "-y",
        "--year",
        "year",
        default=None,
        type=int,
        help="Year for contribution heatmap (default: current year)",
    )(func)
    func = click.option(
        "-l",
        "--limit",
        "limit",
        default=20,
        type=int,
        help="Number of recent activities to show (default: 20)",
    )(func)
    func = click.option(
        "--repos",
        "show_repos",
        is_flag=True,
        default=False,
        help="Show top repositories table",
    )(func)
    func = click.option(
        "--no-heatmap",
        "no_heatmap",
        is_flag=True,
        default=False,
        help="Skip contribution heatmap",
    )(func)
    func = click.option(
        "--no-streaks",
        "no_streaks",
        is_flag=True,
        default=False,
        help="Skip contribution streaks",
    )(func)
    func = click.option(
        "--no-activity",
        "no_activity",
        is_flag=True,
        default=False,
        help="Skip activity timeline",
    )(func)
    func = click.option(
        "--output",
        "output_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Export dashboard data to JSON file",
    )(func)
    return click.option(
        "--format",
        "export_format",
        type=click.Choice(["json", "html"]),
        default="json",
        help="Export format (json or html)",
    )(func)


def team_common_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to add common options to the team subcommand.

    Returns:
        The decorated command with team-relevant common options added.
    """
    func = click.option(
        "-y",
        "--year",
        "year",
        default=None,
        type=int,
        help="Year for contribution analysis (default: current year)",
    )(func)
    func = click.option(
        "--output",
        "output_path",
        default=None,
        type=click.Path(path_type=Path),
        help="Export team data to JSON file",
    )(func)
    return click.option(
        "--format",
        "export_format",
        type=click.Choice(["json", "html"]),
        default="json",
        help="Export format (json or html)",
    )(func)


def target_options(func: Callable[..., Any]) -> Callable[..., Any]:
    """Decorator to add target (user/org) options.

    Returns:
        The decorated command with target options added.
    """
    func = click.option(
        "-u",
        "--user",
        "username",
        default=None,
        help="GitHub username (defaults to authenticated user)",
    )(func)
    return click.option(
        "-o",
        "--org",
        "orgname",
        default=None,
        help="GitHub organization name (alternative to --user)",
    )(func)


# ---------------------------------------------------------------------------
# Data fetching helpers
# ---------------------------------------------------------------------------


def fetch_target_data(
    token: str,
    target_name: str | None,
    target_type: str,
    year: int | None,
    progress: Progress,
    task: TaskID,
) -> tuple[
    dict[str, Any],
    dict[str, int],
    list[dict[str, Any]],
    list[dict[str, Any]],
    list[dict[str, Any]] | None,
    dict[str, Any] | None,
]:
    """Fetch all data for a single target (user or org).

    Returns:
        Tuple of (stats, contributions, activities, repos, members, user_data).
    """
    # Resolve username/orgname
    if target_name is None:
        user_data = get_authenticated_user(token)
        target_name = user_data.get("login", "")
        if not target_name:
            console.print("[red]Could not determine GitHub username.[/red]")
            raise SystemExit(1)
    else:
        user_data = None

    # Fetch profile stats
    progress.update(
        task,
        description=f"Fetching {target_type} profile for [bold]{target_name}[/bold]...",
    )
    if target_type == "org":
        stats = get_org_stats(token, target_name)
        if not stats:
            console.print(f"[bold red]Organization not found:[/bold red] {target_name}")
            raise SystemExit(1)
    else:
        stats = get_user_stats(token, target_name, authenticated_user=user_data)

    # Fetch contributions
    progress.update(task, description="Loading contribution data...")
    if target_type == "org":
        contributions = get_org_contributions(token, target_name, year=year)
    else:
        contributions = get_contributions(token, target_name, year=year)

    # Fetch events
    progress.update(task, description="Loading recent activity...")
    if target_type == "org":
        events = get_org_events(token, target_name, pages=3)
    else:
        events = get_user_events(token, target_name, pages=3)
    activities = categorize_events(events)

    # Fetch repos
    progress.update(task, description="Loading repositories...")
    if target_type == "org":
        repos = get_org_repos(token, target_name, pages=3)
    else:
        repos = get_user_repos(token, target_name, pages=3)

    # Fetch members (org only)
    members = None
    if target_type == "org":
        progress.update(task, description="Loading organization members...")
        members = get_org_members(token, target_name, pages=3)

    return stats, contributions, activities, repos, members, user_data


def compute_all_stats(
    contributions: dict[str, int],
    activities: list[dict[str, Any]],
    repos: list[dict[str, Any]],
) -> tuple[dict[str, int], list[dict[str, Any]], dict[str, int], dict[str, int]]:
    """Compute derived statistics from raw data.

    Returns:
        Tuple of (lang_stats, repo_stats, activity_summary, streaks).
    """
    lang_stats = compute_language_stats(repos)
    repo_stats = compute_repo_stats(repos)
    activity_summary = compute_activity_summary(activities)
    streaks = compute_streaks(contributions)
    return lang_stats, repo_stats, activity_summary, streaks


def render_dashboard(
    stats: dict[str, Any],
    total_contributions: int,
    contributions: dict[str, int],
    activities: list[dict[str, Any]],
    lang_stats: dict[str, int],
    repo_stats: list[dict[str, Any]],
    activity_summary: dict[str, int],
    streaks: dict[str, int],
    members: list[dict[str, Any]] | None,
    target_type: str,
    target_name: str,
    year: int | None,
    limit: int,
    show_repos: bool,
    no_heatmap: bool,
    no_streaks: bool,
    no_activity: bool,
    output_path: Path | None,
    export_format: str,
) -> None:
    """Render the full dashboard for a single target."""
    # Prepare export data
    export_data = {
        "target_type": target_type,
        "target_name": target_name,
        "year": year,
        "stats": stats,
        "total_contributions": total_contributions,
        "contributions": contributions,
        "activities": activities[:limit],
        "lang_stats": lang_stats,
        "repo_stats": repo_stats[:10],
        "activity_summary": activity_summary,
        "streaks": streaks,
    }
    if target_type == "org" and members:
        export_data["members"] = [{"login": m.get("login", "")} for m in members]

    # Export if requested
    if output_path:
        if export_format == "json":
            output_path.write_text(json.dumps(export_data, indent=2, default=str))
        elif export_format == "html":
            html_content = _render_html(export_data)
            output_path.write_text(html_content)
        console.print(f"[green]Exported to {output_path}[/green]")
        if not (no_heatmap and no_streaks and no_activity and not show_repos):
            console.print()

    # ── Render the dashboard ──────────────────────────────────────
    console.print()

    # Profile card
    console.print(render_profile_card(stats, total_contributions))
    console.print()

    # Contribution heatmap
    if not no_heatmap:
        console.print(render_heatmap(contributions, year=year))
        console.print()

    # Contribution streaks
    if not no_streaks:
        console.print(render_streaks(streaks))
        console.print()

    # Activity summary bar
    console.print(render_summary_bar(activity_summary))
    console.print()

    # Activity timeline
    if not no_activity:
        console.print(render_activity_timeline(activities, limit=limit))
        console.print()

    # Language chart
    console.print(render_language_chart(lang_stats))
    console.print()

    # Top repos
    if show_repos:
        console.print(render_repo_table(repo_stats))
        console.print()

    # Org members (if org)
    if target_type == "org" and members:
        console.print(render_members_table(members))
        console.print()


# ---------------------------------------------------------------------------
# CLI Commands
# ---------------------------------------------------------------------------


@click.group()
@click.version_option(version=__version__, prog_name="gh-stats")
def main() -> None:
    """📊 gh-stats — A beautiful terminal dashboard for your GitHub activity.

    Displays your contribution heatmap, recent activity, language distribution,
    and repository stats right in your terminal.

    Authentication: Uses `gh` CLI token or GH_TOKEN environment variable.
    """


@main.command()
@target_options
@common_options
def show(
    username: str | None,
    orgname: str | None,
    year: int | None,
    limit: int,
    show_repos: bool,
    no_heatmap: bool,
    no_streaks: bool,
    no_activity: bool,
    output_path: Path | None,
    export_format: str,
) -> None:
    """Show dashboard for a single user or organization."""
    if username and orgname:
        console.print("[bold red]Error:[/bold red] Cannot specify both --user and --org")
        raise SystemExit(1)

    target_type = "org" if orgname else "user"
    target_name = orgname or username

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Authenticate
            task = progress.add_task("Authenticating with GitHub...", total=None)
            token = get_token()

            stats, contributions, activities, repos, members, user_data = fetch_target_data(
                token, target_name, target_type, year, progress, task
            )

            # Use resolved target_name from user_data if not provided
            resolved_target_name = target_name or (user_data or {}).get("login", "")
            total_contributions = sum(contributions.values())
            lang_stats, repo_stats, activity_summary, streaks = compute_all_stats(
                contributions, activities, repos
            )

        render_dashboard(
            stats=stats,
            total_contributions=total_contributions,
            contributions=contributions,
            activities=activities,
            lang_stats=lang_stats,
            repo_stats=repo_stats,
            activity_summary=activity_summary,
            streaks=streaks,
            members=members,
            target_type=target_type,
            target_name=resolved_target_name,
            year=year,
            limit=limit,
            show_repos=show_repos,
            no_heatmap=no_heatmap,
            no_streaks=no_streaks,
            no_activity=no_activity,
            output_path=output_path,
            export_format=export_format,
        )

    except AuthError as e:
        console.print(f"[bold red]Authentication error:[/bold red] {e}")
        console.print("\n[yellow]Tips:[/yellow]")
        console.print("  • Install [bold]gh[/bold] CLI and run [bold]gh auth login[/bold]")
        console.print("  • Or set [bold]GH_TOKEN[/bold] environment variable")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[bold red]API error:[/bold red] {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        raise SystemExit(0)


@main.command()
@click.option(
    "-u",
    "--user-a",
    "user_a",
    default=None,
    help="First GitHub username to compare",
)
@click.option(
    "-U",
    "--user-b",
    "user_b",
    default=None,
    help="Second GitHub username to compare",
)
@click.option(
    "-o",
    "--org-a",
    "org_a",
    default=None,
    help="First GitHub organization to compare",
)
@click.option(
    "-O",
    "--org-b",
    "org_b",
    default=None,
    help="Second GitHub organization to compare",
)
@click.option(
    "--year-a",
    "year_a",
    default=None,
    type=int,
    help="Year for first target (enables time-period comparison for same user/org)",
)
@click.option(
    "--year-b",
    "year_b",
    default=None,
    type=int,
    help="Year for second target (enables time-period comparison for same user/org)",
)
@common_options
def compare(
    user_a: str | None,
    user_b: str | None,
    org_a: str | None,
    org_b: str | None,
    year: int | None,
    year_a: int | None,
    year_b: int | None,
    limit: int,
    show_repos: bool,
    no_heatmap: bool,
    no_streaks: bool,
    no_activity: bool,
    output_path: Path | None,
    export_format: str,
) -> None:
    """Compare two users or two organizations side by side.

    Provide either two users (--user-a/--user-b) or two organizations
    (--org-a/--org-b). Mixing user and org is not supported.

    For time-period comparison, provide a single user or org with different
    years: e.g. ``--user-a octocat --year-a 2023 --year-b 2024``.
    """
    # Validate arguments
    if (user_a or user_b) and (org_a or org_b):
        console.print("[bold red]Error:[/bold red] Cannot mix --user-* and --org-* options")
        raise SystemExit(1)

    target_name = ""
    # Time-period comparison: same target, different years
    time_period_mode = (year_a is not None or year_b is not None) and (
        user_b is None and org_b is None
    )

    if time_period_mode:
        target_name = user_a or org_a
        if not target_name:
            msg = "Must specify --user-a or --org-a for time-period comparison"
            console.print(f"[bold red]Error:[/bold red] {msg}")
            raise SystemExit(1)
        target_type = "org" if org_a else "user"
        target_a = target_name
        target_b = target_name
        effective_year_a = year_a or year
        effective_year_b = year_b or year
        if effective_year_a is None or effective_year_b is None:
            msg = "Must specify --year-a and --year-b for time-period comparison"
            console.print(f"[bold red]Error:[/bold red] {msg}")
            raise SystemExit(1)
        if effective_year_a == effective_year_b:
            msg = "--year-a and --year-b must be different years"
            console.print(f"[bold red]Error:[/bold red] {msg}")
            raise SystemExit(1)
        compare_label_a = f"{target_name} ({effective_year_a})"
        compare_label_b = f"{target_name} ({effective_year_b})"
    elif user_a and user_b:
        target_type = "user"
        target_a, target_b = user_a, user_b
        effective_year_a = year
        effective_year_b = year
        compare_label_a = target_a
        compare_label_b = target_b
    elif org_a and org_b:
        target_type = "org"
        target_a, target_b = org_a, org_b
        effective_year_a = year
        effective_year_b = year
        compare_label_a = target_a
        compare_label_b = target_b
    else:
        console.print(
            "[bold red]Error:[/bold red] Must specify either two users or two organizations"
        )
        console.print("  Use --user-a/--user-b for users, or --org-a/--org-b for organizations")
        raise SystemExit(1)

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Authenticate
            task = progress.add_task("Authenticating with GitHub...", total=None)
            token = get_token()

            # Fetch data for target A
            progress.update(
                task, description=f"Fetching {target_type} A: [bold]{compare_label_a}[/bold]..."
            )
            stats_a, contrib_a, activities_a, repos_a, members_a, _ = fetch_target_data(
                token, target_a, target_type, effective_year_a, progress, task
            )
            total_a = sum(contrib_a.values())
            lang_a, repo_a, summary_a, streaks_a = compute_all_stats(
                contrib_a, activities_a, repos_a
            )

            # Fetch data for target B
            progress.update(
                task, description=f"Fetching {target_type} B: [bold]{compare_label_b}[/bold]..."
            )
            stats_b, contrib_b, activities_b, repos_b, members_b, _ = fetch_target_data(
                token, target_b, target_type, effective_year_b, progress, task
            )
            total_b = sum(contrib_b.values())
            lang_b, repo_b, summary_b, streaks_b = compute_all_stats(
                contrib_b, activities_b, repos_b
            )

            # Compute comparison summary
            comparison = compute_comparison_summary(activities_a, activities_b)

            # Compute contribution patterns

            patterns_a = compute_contribution_patterns(contrib_a)
            patterns_b = compute_contribution_patterns(contrib_b)

            # Compute growth rates

            growth = compute_growth_metrics(contrib_a, contrib_b)

        # ── Prepare export data ──────────────────────────────────────
        export_data = {
            "comparison_mode": "time_period" if time_period_mode else "side_by_side",
            "target_type": target_type,
            "target_a": compare_label_a,
            "target_b": compare_label_b,
            "year_a": effective_year_a,
            "year_b": effective_year_b,
            "stats_a": stats_a,
            "stats_b": stats_b,
            "total_contributions_a": total_a,
            "total_contributions_b": total_b,
            "contributions_a": contrib_a,
            "contributions_b": contrib_b,
            "activities_a": activities_a[:limit],
            "activities_b": activities_b[:limit],
            "lang_stats_a": lang_a,
            "lang_stats_b": lang_b,
            "repo_stats_a": repo_a[:10],
            "repo_stats_b": repo_b[:10],
            "activity_summary_a": summary_a,
            "activity_summary_b": summary_b,
            "streaks_a": streaks_a,
            "streaks_b": streaks_b,
            "comparison_summary": comparison,
            "patterns_a": patterns_a,
            "patterns_b": patterns_b,
            "growth_metrics": growth,
        }

        # ── Export if requested ──────────────────────────────────────
        if output_path:
            if export_format == "json":
                output_path.write_text(json.dumps(export_data, indent=2, default=str))
            elif export_format == "html":
                html_content = _render_comparison_html(export_data)
                output_path.write_text(html_content)
            console.print(f"[green]Comparison exported to {output_path}[/green]")
            if not (no_heatmap and no_streaks and no_activity and not show_repos):
                console.print()

        # ── Render comparison dashboard ────────────────────────────────
        console.print()
        if time_period_mode:
            console.print(
                f"[bold]📊 gh-stats — Comparing {target_type} {target_name}: "
                f"{effective_year_a} vs {effective_year_b}[/bold]"
            )
        else:
            console.print(
                f"[bold]📊 gh-stats — Comparing {target_type} {target_a} vs {target_b}[/bold]"
            )
        console.print()

        # Profile comparison
        console.print(
            render_comparison_profile_cards(
                stats_a, stats_b, total_a, total_b, compare_label_a, compare_label_b
            )
        )
        console.print()

        # Heatmap comparison
        if not no_heatmap:
            console.print(
                render_comparison_heatmap(
                    contrib_a, contrib_b, effective_year_a, compare_label_a, compare_label_b
                )
            )
            console.print()

        # Streaks comparison
        if not no_streaks:
            console.print(
                render_comparison_streaks(streaks_a, streaks_b, compare_label_a, compare_label_b)
            )
            console.print()

        # Summary comparison
        console.print(
            render_comparison_summary_bars(summary_a, summary_b, compare_label_a, compare_label_b)
        )
        console.print()

        # Activity timeline comparison
        if not no_activity:
            console.print(render_comparison_activity_timelines(activities_a, activities_b, limit))
            console.print()

        # Language comparison
        console.print(
            render_comparison_language_charts(lang_a, lang_b, compare_label_a, compare_label_b)
        )
        console.print()

        # Repo comparison (only if not time-period or both are different targets)
        if show_repos and not time_period_mode:
            console.print(
                render_comparison_repo_tables(repo_a, repo_b, compare_label_a, compare_label_b)
            )
            console.print()

        # Members comparison (org only, not time-period)
        if target_type == "org" and members_a and members_b and not time_period_mode:
            console.print(
                render_comparison_members_tables(
                    members_a, members_b, compare_label_a, compare_label_b
                )
            )
            console.print()

        # Contribution patterns comparison
        console.print(
            render_comparison_patterns(patterns_a, patterns_b, compare_label_a, compare_label_b)
        )
        console.print()

        # Growth metrics
        console.print(render_growth_metrics(growth, compare_label_a, compare_label_b))
        console.print()

    except AuthError as e:
        console.print(f"[bold red]Authentication error:[/bold red] {e}")
        console.print("\n[yellow]Tips:[/yellow]")
        console.print("  • Install [bold]gh[/bold] CLI and run [bold]gh auth login[/bold]")
        console.print("  • Or set [bold]GH_TOKEN[/bold] environment variable")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[bold red]API error:[/bold red] {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        raise SystemExit(0)


# ---------------------------------------------------------------------------
# Team Analytics Command
# ---------------------------------------------------------------------------


@main.command()
@click.option(
    "-o",
    "--org",
    "orgname",
    default=None,
    help="GitHub organization name (defaults to authenticated user's orgs)",
)
@click.option(
    "--repo-limit",
    "repo_limit",
    default=20,
    type=int,
    help="Number of repositories to analyze (default: 20)",
)
@click.option(
    "--contributors",
    "contributor_limit",
    default=20,
    type=int,
    help="Number of top contributors to show (default: 20)",
)
@click.option(
    "--no-health",
    "no_health",
    is_flag=True,
    default=False,
    help="Skip repository health matrix",
)
@click.option(
    "--no-bus-factor",
    "no_bus_factor",
    is_flag=True,
    default=False,
    help="Skip bus factor analysis",
)
@click.option(
    "--no-collab",
    "no_collab",
    is_flag=True,
    default=False,
    help="Skip collaboration network",
)
@click.option(
    "--no-reviews",
    "no_reviews",
    is_flag=True,
    default=False,
    help="Skip code review analytics",
)
@team_common_options
def team(
    orgname: str | None,
    year: int | None,
    repo_limit: int,
    contributor_limit: int,
    no_health: bool,
    no_bus_factor: bool,
    no_collab: bool,
    no_reviews: bool,
    output_path: Path | None,
    export_format: str,
) -> None:
    """Show team/organization analytics dashboard.

    Analyzes repository health, contributor rankings, bus factor,
    collaboration patterns, and code review metrics for an organization.
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            # Authenticate
            task = progress.add_task("Authenticating with GitHub...", total=None)
            token = get_token()

            # Determine organization
            if orgname is None:
                # Try to get user's orgs
                get_authenticated_user(token)
                msg = (
                    "[yellow]No organization specified. "
                    "Use --org to specify an organization.[/yellow]"
                )
                console.print(msg)
                console.print(
                    "[dim]Your organizations can be found at https://github.com/orgs[/dim]"
                )
                raise SystemExit(1)

            target_name = orgname

            # Fetch org profile
            progress.update(
                task, description=f"Fetching organization profile for [bold]{target_name}[/bold]..."
            )
            stats = get_org_stats(token, target_name)
            if not stats:
                console.print(f"[bold red]Organization not found:[/bold red] {target_name}")
                raise SystemExit(1)

            # Fetch org repos
            progress.update(task, description="Loading organization repositories...")
            repos = get_org_repos(token, target_name, pages=5)
            repos = repos[:repo_limit] if repo_limit else repos

            # Fetch contributors, commits, PRs, issues for each repo
            all_contributors: list[dict[str, Any]] = []
            all_commits: list[dict[str, Any]] = []
            all_prs: list[dict[str, Any]] = []
            all_issues: list[dict[str, Any]] = []
            all_reviews: dict[int, list[dict[str, Any]]] = {}

            repo_commits: dict[str, list[dict[str, Any]]] = {}
            repo_prs: dict[str, list[dict[str, Any]]] = {}
            repo_issues: dict[str, list[dict[str, Any]]] = {}
            repo_contributors: dict[str, list[dict[str, Any]]] = {}

            since_date = None
            if year:
                since_date = f"{year}-01-01T00:00:00Z"

            for i, repo in enumerate(repos):
                repo_name = repo.get("name", "")
                if not repo_name:
                    continue
                full_name = repo.get("full_name", f"{target_name}/{repo_name}")

                progress.update(
                    task,
                    description=f"Analyzing repo {i + 1}/{len(repos)}: [bold]{full_name}[/bold]...",
                )

                # Fetch repo data
                contributors = get_repo_contributors(token, target_name, repo_name, pages=3)
                commits = get_repo_commits(token, target_name, repo_name, pages=3, since=since_date)
                prs = get_repo_pull_requests(token, target_name, repo_name, pages=3)
                issues = get_repo_issues(token, target_name, repo_name, pages=3)

                # Fetch reviews for each PR
                reviews: dict[int, list[dict[str, Any]]] = {}
                for pr in prs:
                    pr_num = pr.get("number")
                    if pr_num:
                        pr_reviews = get_pull_request_reviews(token, target_name, repo_name, pr_num)
                        reviews[pr_num] = pr_reviews
                        all_reviews[pr_num] = pr_reviews

                all_contributors.extend(contributors)
                all_commits.extend(commits)
                all_prs.extend(prs)
                all_issues.extend(issues)

                repo_contributors[repo_name] = contributors
                repo_commits[repo_name] = commits
                repo_prs[repo_name] = prs
                repo_issues[repo_name] = issues

            # Compute analytics
            progress.update(task, description="Computing team analytics...")

            # Contributor rankings
            contributor_rankings = compute_contributor_rankings(
                all_contributors,
                all_commits,
                all_prs,
                all_reviews,
                all_issues,
                top_n=contributor_limit,
            )

            # Bus factor
            bus_factor_data = compute_bus_factor(all_contributors, all_commits, all_prs)

            # Repo health
            repo_health = compute_repo_health_scores(
                repos,
                repo_commits,
                repo_prs,
                repo_issues,
                repo_contributors,
                top_n=repo_limit,
            )

            # Collaboration matrix
            collab_data = compute_collaboration_matrix(all_commits, all_prs, all_reviews)

            # Review analytics
            review_data = compute_review_analytics(all_prs, all_reviews)

            # Team summary stats
            active_repos = [
                r for r in repos if not r.get("archived", False) and not r.get("disabled", False)
            ]
            total_repos = len(active_repos)
            total_contributors = len({
                c.get("login", "") for c in all_contributors if c.get("login")
            })
            cutoff_date = since_date or "1970-01-01T00:00:00Z"
            total_commits = len([
                c
                for c in all_commits
                if c.get("commit", {}).get("author", {}).get("date", "") >= cutoff_date
            ])
            total_prs_count = len(all_prs)
            total_issues_count = len(all_issues)
            bus_factor = bus_factor_data.get("bus_factor", 0)
            avg_health = (
                sum(r.get("health_score", 0) for r in repo_health) / len(repo_health)
                if repo_health
                else 0
            )

            # Prepare export data
            export_data = {
                "target_type": "org",
                "target_name": target_name,
                "year": year,
                "stats": stats,
                "contributor_rankings": contributor_rankings,
                "bus_factor": bus_factor_data,
                "repo_health": repo_health,
                "collaboration": collab_data,
                "review_analytics": review_data,
                "summary": {
                    "total_repos": total_repos,
                    "total_contributors": total_contributors,
                    "total_commits": total_commits,
                    "total_prs": total_prs_count,
                    "total_issues": total_issues_count,
                    "bus_factor": bus_factor,
                    "avg_health": avg_health,
                },
            }

            # Export if requested
            if output_path:
                if export_format == "json":
                    output_path.write_text(json.dumps(export_data, indent=2, default=str))
                elif export_format == "html":
                    # HTML export not yet implemented for team view
                    msg = (
                        "[yellow]HTML export for team view not yet implemented, "
                        "exporting JSON[/yellow]"
                    )
                    console.print(msg)
                    output_path.write_text(json.dumps(export_data, indent=2, default=str))
                console.print(f"[green]Exported to {output_path}[/green]")
                console.print()

        # ── Render team dashboard ──────────────────────────────────────
        console.print()
        console.print(f"[bold]📊 gh-stats — Team Analytics: {target_name}[/bold]")
        console.print()

        # Team summary
        console.print(
            render_team_summary(
                target_name,
                total_repos,
                total_contributors,
                total_commits,
                total_prs_count,
                total_issues_count,
                bus_factor,
                avg_health,
            )
        )
        console.print()

        # Contributor rankings
        console.print(render_contributor_table(contributor_rankings, limit=contributor_limit))
        console.print()

        # Bus factor
        if not no_bus_factor:
            console.print(render_bus_factor(bus_factor_data))
            console.print()

        # Repo health
        if not no_health:
            console.print(render_repo_health_matrix(repo_health, limit=repo_limit))
            console.print()

        # Collaboration network
        if not no_collab:
            console.print(render_collaboration_heatmap(collab_data, limit=contributor_limit))
            console.print()

        # Review analytics
        if not no_reviews:
            console.print(render_review_analytics(review_data))
            console.print()

    except AuthError as e:
        console.print(f"[bold red]Authentication error:[/bold red] {e}")
        console.print("\n[yellow]Tips:[/yellow]")
        console.print("  • Install [bold]gh[/bold] CLI and run [bold]gh auth login[/bold]")
        console.print("  • Or set [bold]GH_TOKEN[/bold] environment variable")
        raise SystemExit(1)
    except ApiError as e:
        console.print(f"[bold red]API error:[/bold red] {e}")
        raise SystemExit(1)
    except KeyboardInterrupt:
        console.print("\n[dim]Interrupted.[/dim]")
        raise SystemExit(0)


def render_comparison_members_tables(
    members_a: list[dict[str, Any]],
    members_b: list[dict[str, Any]],
    target_type_a: str,
    target_type_b: str,
    limit: int = 20,
) -> Panel:
    """Render two member tables side by side for comparison.

    Returns:
        Rich Panel with two member tables.
    """
    from rich.columns import Columns

    table_a = render_members_table(members_a, limit)
    table_b = render_members_table(members_b, limit)

    table_a.title = f"👥 Members A ({target_type_a})"
    table_b.title = f"👥 Members B ({target_type_b})"

    return Panel(
        Columns([table_a, table_b], equal=True, expand=True),
        title="👥 Organization Members Comparison",
        border_style="bright_cyan",
        padding=(1, 2),
    )


if __name__ == "__main__":
    main()
