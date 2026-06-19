# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""CLI entry point — orchestrates API calls and renders the dashboard."""

from __future__ import annotations

import json
from pathlib import Path

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from . import __version__
from .activity import (
    categorize_events,
    compute_activity_summary,
    compute_language_stats,
    compute_repo_stats,
)
from .api import (
    ApiError,
    AuthError,
    get_contributions,
    get_org_contributions,
    get_org_events,
    get_org_members,
    get_org_repos,
    get_org_stats,
    get_token,
    get_user_events,
    get_user_repos,
    get_user_stats,
)
from .ui import (
    _render_html,
    render_activity_timeline,
    render_heatmap,
    render_language_chart,
    render_members_table,
    render_profile_card,
    render_repo_table,
    render_summary_bar,
)

console = Console()


@click.command()
@click.option(
    "-u",
    "--user",
    "username",
    default=None,
    help="GitHub username (defaults to authenticated user)",
)
@click.option(
    "-o",
    "--org",
    "orgname",
    default=None,
    help="GitHub organization name (alternative to --user)",
)
@click.option(
    "-y",
    "--year",
    "year",
    default=None,
    type=int,
    help="Year for contribution heatmap (default: current year)",
)
@click.option(
    "-l",
    "--limit",
    "limit",
    default=20,
    type=int,
    help="Number of recent activities to show (default: 20)",
)
@click.option(
    "--repos",
    "show_repos",
    is_flag=True,
    default=False,
    help="Show top repositories table",
)
@click.option(
    "--no-heatmap",
    "no_heatmap",
    is_flag=True,
    default=False,
    help="Skip contribution heatmap",
)
@click.option(
    "--no-activity",
    "no_activity",
    is_flag=True,
    default=False,
    help="Skip activity timeline",
)
@click.option(
    "--output",
    "output_path",
    default=None,
    type=click.Path(path_type=Path),
    help="Export dashboard data to JSON file",
)
@click.option(
    "--format",
    "export_format",
    type=click.Choice(["json", "html"]),
    default="json",
    help="Export format (json or html)",
)
@click.version_option(version=__version__, prog_name="gh-stats")
def main(
    username: str | None,
    orgname: str | None,
    year: int | None,
    limit: int,
    show_repos: bool,
    no_heatmap: bool,
    no_activity: bool,
    output_path: Path | None,
    export_format: str,
) -> None:
    """📊 gh-stats — A beautiful terminal dashboard for your GitHub activity.

    Displays your contribution heatmap, recent activity, language distribution,
    and repository stats right in your terminal.

    Authentication: Uses `gh` CLI token or GH_TOKEN environment variable.
    """
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

            # Resolve username/orgname
            if target_name is None:
                from .api import get_authenticated_user

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
                description=(f"Fetching {target_type} profile for [bold]{target_name}[/bold]..."),
            )
            if orgname:
                stats = get_org_stats(token, orgname)
                if not stats:
                    console.print(f"[bold red]Organization not found:[/bold red] {orgname}")
                    raise SystemExit(1)
            else:
                stats = get_user_stats(token, target_name, authenticated_user=user_data)

            # Fetch contributions
            progress.update(task, description="Loading contribution data...")
            if orgname:
                contributions = get_org_contributions(token, orgname, year=year)
            else:
                contributions = get_contributions(token, target_name, year=year)
            total_contributions = sum(contributions.values())

            # Fetch events
            progress.update(task, description="Loading recent activity...")
            if orgname:
                events = get_org_events(token, orgname, pages=3)
            else:
                events = get_user_events(token, target_name, pages=3)
            activities = categorize_events(events)

            # Fetch repos
            progress.update(task, description="Loading repositories...")
            if orgname:
                repos = get_org_repos(token, orgname, pages=3)
            else:
                repos = get_user_repos(token, target_name, pages=3)

            # Fetch members (org only)
            members = []
            if orgname:
                progress.update(task, description="Loading organization members...")
                members = get_org_members(token, orgname, pages=3)

            # Compute derived stats
            lang_stats = compute_language_stats(repos)
            repo_stats = compute_repo_stats(repos)
            activity_summary = compute_activity_summary(activities)

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
        }
        if orgname:
            export_data["members"] = [{"login": m.get("login", "")} for m in members]

        # Export if requested
        if output_path:
            if export_format == "json":
                output_path.write_text(json.dumps(export_data, indent=2, default=str))
            elif export_format == "html":
                html_content = _render_html(export_data)
                output_path.write_text(html_content)
            console.print(f"[green]Exported to {output_path}[/green]")
            if not (no_heatmap and no_activity and not show_repos):
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
        if orgname and members:
            console.print(render_members_table(members))
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


if __name__ == "__main__":
    main()
