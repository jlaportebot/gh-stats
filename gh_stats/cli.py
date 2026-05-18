"""CLI entry point — orchestrates API calls and renders the dashboard."""

from __future__ import annotations

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
    get_token,
    get_user_events,
    get_user_repos,
    get_user_stats,
)
from .ui import (
    render_activity_timeline,
    render_heatmap,
    render_language_chart,
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
@click.version_option(version=__version__, prog_name="gh-stats")
def main(
    username: str | None,
    year: int | None,
    limit: int,
    show_repos: bool,
    no_heatmap: bool,
    no_activity: bool,
) -> None:
    """📊 gh-stats — A beautiful terminal dashboard for your GitHub activity.

    Displays your contribution heatmap, recent activity, language distribution,
    and repository stats right in your terminal.

    Authentication: Uses `gh` CLI token or GH_TOKEN environment variable.
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

            # Resolve username
            if username is None:
                from .api import get_authenticated_user

                user_data = get_authenticated_user(token)
                username = user_data.get("login", "")
                if not username:
                    console.print("[red]Could not determine GitHub username.[/red]")
                    raise SystemExit(1)
            else:
                user_data = None

            # Fetch profile stats (reuse authenticated_user to avoid duplicate API call)
            progress.update(task, description=f"Fetching profile for [bold]{username}[/bold]...")
            stats = get_user_stats(token, username, authenticated_user=user_data)

            # Fetch contributions
            progress.update(task, description="Loading contribution data...")
            contributions = get_contributions(token, username, year=year)
            total_contributions = sum(contributions.values())

            # Fetch events
            progress.update(task, description="Loading recent activity...")
            events = get_user_events(token, username, pages=3)
            activities = categorize_events(events)

            # Fetch repos
            progress.update(task, description="Loading repositories...")
            repos = get_user_repos(token, username, pages=3)

            # Compute derived stats
            lang_stats = compute_language_stats(repos)
            repo_stats = compute_repo_stats(repos)
            activity_summary = compute_activity_summary(activities)

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
