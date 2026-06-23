# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""GitHub API client — authenticates via `gh` CLI token and fetches activity data."""

from __future__ import annotations

import atexit
import contextlib
import json
import logging
import os
import shutil
import subprocess  # noqa: S404
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("gh_stats")

_client: httpx.Client | None = None

# Type alias for JSON-serializable data
JSONValue = dict[str, Any] | list[Any] | str | int | float | bool | None

# HTTP status code constants
HTTP_UNAUTHORIZED = 401
HTTP_FORBIDDEN = 403
HTTP_BAD_REQUEST = 400


class AuthError(Exception):
    """Raised when GitHub authentication fails."""


class ApiError(Exception):
    """Raised when a GitHub API call fails."""


def get_token() -> str:
    """Get a GitHub API token.

    Priority:
    1. GH_TOKEN / GITHUB_TOKEN env var
    2. `gh auth token` output

    Returns:
        GitHub API token string.

    Raises:
        AuthError: If no token can be found.
    """
    env_token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if env_token:
        return env_token

    try:
        gh_path = _get_gh_path()
    except FileNotFoundError:
        msg = "No GitHub token found. Set GH_TOKEN or install and authenticate `gh` CLI."
        raise AuthError(msg) from None

    result = subprocess.run(  # noqa: S603
        [gh_path, "auth", "token"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if result.returncode == 0 and result.stdout.strip():
        return result.stdout.strip()

    msg = "No GitHub token found. Set GH_TOKEN or install and authenticate `gh` CLI."
    raise AuthError(msg)


def _get_gh_path() -> str:
    """Get the full path to the gh CLI executable.

    Returns:
        Full path to gh executable.

    Raises:
        FileNotFoundError: If gh CLI is not found in PATH.
    """
    gh_path = shutil.which("gh")
    if gh_path is None:
        msg = "gh CLI not found in PATH"
        raise FileNotFoundError(msg)
    return gh_path


def get_authenticated_user(token: str) -> dict[str, Any]:
    """Fetch the authenticated user's profile.

    Returns:
        User profile dict from GitHub API.
    """
    return _request(token, "GET", "https://api.github.com/user")


def get_user_events(
    token: str, username: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch recent public events for a user (paginated).

    Returns:
        List of event dicts from GitHub API.
    """
    events: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        resp = _request(
            token,
            "GET",
            f"https://api.github.com/users/{username}/events",
            params={"per_page": per_page, "page": page},
        )
        if not resp:
            break
        events.extend(resp)
    return events


def get_user_repos(
    token: str, username: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch repos owned by the user, sorted by updated date.

    Returns:
        List of repo dicts from GitHub API.
    """
    repos: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        resp = _request(
            token,
            "GET",
            f"https://api.github.com/users/{username}/repos",
            params={
                "per_page": per_page,
                "page": page,
                "sort": "updated",
                "direction": "desc",
            },
        )
        if not resp:
            break
        repos.extend(resp)
    return repos


def get_contributions(token: str, username: str, year: int | None = None) -> dict[str, int]:
    """Fetch contribution count per day via the contributions graph API.

    Uses the GitHub GraphQL API to get the contribution calendar.
    Returns {YYYY-MM-DD: count} for each day with activity.

    Returns:
        Dict mapping date strings to contribution counts.
    """
    now = datetime.now(UTC)
    if year is None:
        year = now.year

    # Query from Jan 1 of the year to today (or Dec 31 if past year)
    from_date = f"{year}-01-01T00:00:00Z"
    to_date = now.strftime("%Y-%m-%dT%H:%M:%SZ") if year == now.year else f"{year}-12-31T23:59:59Z"

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                date
                contributionCount
                color
              }
            }
          }
        }
      }
    }
    """

    resp = _graphql(
        token,
        query,
        variables={"login": username, "from": from_date, "to": to_date},
    )

    try:
        calendar = resp["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        contributions: dict[str, int] = {}
        for week in calendar["weeks"]:
            for day in week["contributionDays"]:
                if day["contributionCount"] > 0:
                    contributions[day["date"]] = day["contributionCount"]
    except (KeyError, TypeError) as exc:
        logger.warning("Failed to parse contribution calendar: %s", exc)
        return {}
    else:
        return contributions


def get_user_stats(
    token: str, username: str, *, authenticated_user: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Fetch aggregate stats for the user profile card.

    If ``authenticated_user`` is provided (from a prior ``get_authenticated_user``
    call), it will be reused when *username* matches the current login, avoiding a
    duplicate API round-trip.

    Returns:
        Dict with user stats for the profile card.
    """
    current_login = (authenticated_user or get_authenticated_user(token)).get("login", "")
    if username == current_login and authenticated_user is not None:
        user = authenticated_user
    elif username == current_login:
        user = authenticated_user or get_authenticated_user(token)
    else:
        user = _request(token, "GET", f"https://api.github.com/users/{username}")
    return {
        "login": user.get("login", username),
        "name": user.get("name") or user.get("login", username),
        "avatar_url": user.get("avatar_url", ""),
        "bio": user.get("bio", ""),
        "public_repos": user.get("public_repos", 0),
        "public_gists": user.get("public_gists", 0),
        "followers": user.get("followers", 0),
        "following": user.get("following", 0),
        "created_at": user.get("created_at", ""),
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _get_client() -> httpx.Client:
    """Lazy-initialised HTTP client (created once, closed at process exit).

    Returns:
        Shared httpx.Client instance.
    """
    global _client  # noqa: PLW0603
    if _client is None:
        _client = httpx.Client(timeout=30.0)
        atexit.register(_close_client)
    return _client


def _close_client() -> None:
    """Shut down the shared HTTP client gracefully."""
    global _client  # noqa: PLW0603
    if _client is not None:
        with contextlib.suppress(Exception):
            _client.close()
    _client = None


def _request(
    token: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:  # noqa: ANN401
    """Make an authenticated HTTP request to GitHub REST API.

    Args:
        token: GitHub API token.
        method: HTTP method (GET, POST, etc.).
        url: Request URL.
        params: Optional query parameters.

    Returns:
        Parsed JSON response.

    Raises:
        AuthError: If token is invalid (401).
        ApiError: If request fails or returns error status.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        resp = _get_client().request(method, url, headers=headers, params=params)
    except httpx.TimeoutException as exc:
        msg = f"Request to {url} timed out: {exc}"
        raise ApiError(msg) from exc
    except httpx.ConnectError as exc:
        msg = f"Cannot connect to {url}: {exc}"
        raise ApiError(msg) from exc
    except httpx.NetworkError as exc:
        msg = f"Network error contacting {url}: {exc}"
        raise ApiError(msg) from exc

    if resp.status_code == HTTP_UNAUTHORIZED:
        msg = "GitHub token is invalid or expired."
        raise AuthError(msg)
    if resp.status_code == HTTP_FORBIDDEN:
        msg = "Rate limited or forbidden."
        raise ApiError(msg)
    if resp.status_code >= HTTP_BAD_REQUEST:
        msg = f"API error {resp.status_code}: {resp.text[:200]}"
        raise ApiError(msg)
    return resp.json()


def _graphql(token: str, query: str, *, variables: dict[str, Any] | None = None) -> Any:  # noqa: ANN401
    """Execute a GraphQL query against GitHub API.

    Args:
        token: GitHub API token.
        query: GraphQL query string.
        variables: Optional variables for the query.

    Returns:
        Parsed JSON response data.

    Raises:
        AuthError: If token is invalid (401).
        ApiError: If request fails or GraphQL returns errors.
    """
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    try:
        resp = _get_client().post(
            "https://api.github.com/graphql",
            headers=headers,
            json=payload,
        )
    except httpx.TimeoutException as exc:
        msg = f"GraphQL request timed out: {exc}"
        raise ApiError(msg) from exc
    except httpx.ConnectError as exc:
        msg = f"Cannot connect to GraphQL endpoint: {exc}"
        raise ApiError(msg) from exc
    except httpx.NetworkError as exc:
        msg = f"Network error on GraphQL request: {exc}"
        raise ApiError(msg) from exc

    if resp.status_code == HTTP_UNAUTHORIZED:
        msg = "GitHub token is invalid or expired."
        raise AuthError(msg)
    if resp.status_code >= HTTP_BAD_REQUEST:
        msg = f"GraphQL error {resp.status_code}: {resp.text[:200]}"
        raise ApiError(msg)
    data = resp.json()
    if "errors" in data:
        errors_json = json.dumps(data["errors"])[:300]
        msg = f"GraphQL errors: {errors_json}"
        raise ApiError(msg)
    return data


# ---------------------------------------------------------------------------
# Organization API
# ---------------------------------------------------------------------------


def get_org_events(
    token: str, org: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch recent public events for an organization (paginated).

    Returns:
        List of event dicts from GitHub API.
    """
    events: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/orgs/{org}/events",
                params={"per_page": per_page, "page": page},
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        events.extend(resp)
    return events


def get_org_repos(
    token: str, org: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch repos owned by the organization, sorted by updated date.

    Returns:
        List of repo dicts from GitHub API.
    """
    repos: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/orgs/{org}/repos",
                params={
                    "per_page": per_page,
                    "page": page,
                    "type": "all",
                    "sort": "updated",
                    "direction": "desc",
                },
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        repos.extend(resp)
    return repos


def get_org_members(
    token: str, org: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch members of the organization (paginated).

    Returns:
        List of member dicts from GitHub API.
    """
    members: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/orgs/{org}/members",
                params={"per_page": per_page, "page": page},
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        members.extend(resp)
    return members


def get_org_stats(token: str, org: str) -> dict[str, Any]:
    """Fetch aggregate stats for the organization profile.

    Returns:
        Dict with org stats for the profile card.
    """
    try:
        org_data = _request(token, "GET", f"https://api.github.com/orgs/{org}")
    except ApiError as e:
        if "404" in str(e):
            return {}
        raise
    return {
        "login": org_data.get("login", org),
        "name": org_data.get("name") or org_data.get("login", org),
        "description": org_data.get("description", ""),
        "avatar_url": org_data.get("avatar_url", ""),
        "public_repos": org_data.get("public_repos", 0),
        "followers": org_data.get("followers", 0),
        "following": org_data.get("following", 0),
        "created_at": org_data.get("created_at", ""),
    }


def get_org_contributions(token: str, org: str, year: int | None = None) -> dict[str, int]:
    """Fetch contribution counts for organization members via GraphQL.

    Note: GitHub's GraphQL API doesn't provide a direct org-level contribution
    calendar. This fetches top members' contributions as a proxy.

    Returns:
        Dict mapping date strings to aggregate contribution counts.
    """
    now = datetime.now(UTC)
    if year is None:
        year = now.year

    from_date = f"{year}-01-01T00:00:00Z"
    to_date = now.strftime("%Y-%m-%dT%H:%M:%SZ") if year == now.year else f"{year}-12-31T23:59:59Z"

    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      organization(login: $login) {
        membersWithRepositories(first: 20) {
          nodes {
            login
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  contributionDays {
                    date
                    contributionCount
                  }
                }
              }
            }
          }
        }
      }
    }
    """

    try:
        resp = _graphql(
            token,
            query,
            variables={"login": org, "from": from_date, "to": to_date},
        )
    except ApiError:
        return {}

    contributions: dict[str, int] = {}
    try:
        members = resp["data"]["organization"]["membersWithRepositories"]["nodes"]
        for member in members:
            calendar = member["contributionsCollection"]["contributionCalendar"]
            for week in calendar["weeks"]:
                for day in week["contributionDays"]:
                    if day["contributionCount"] > 0:
                        date = day["date"]
                        contributions[date] = contributions.get(date, 0) + day["contributionCount"]
    except (KeyError, TypeError) as exc:
        logger.warning("Failed to parse org contribution calendar: %s", exc)
        return {}

    return contributions


# ---------------------------------------------------------------------------
# Team Analytics API
# ---------------------------------------------------------------------------


def get_repo_contributors(
    token: str, owner: str, repo: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch contributors for a repository (paginated).

    Returns:
        List of contributor dicts with login, contributions, avatar_url.
    """
    contributors: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/repos/{owner}/{repo}/contributors",
                params={"per_page": per_page, "page": page, "anon": "true"},
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        contributors.extend(resp)
    return contributors


def get_repo_commits(
    token: str,
    owner: str,
    repo: str,
    *,
    per_page: int = 100,
    pages: int = 3,
    since: str | None = None,
    until: str | None = None,
) -> list[dict[str, Any]]:
    """Fetch commits for a repository (paginated).

    Args:
        since: ISO 8601 date string to filter commits after this date.
        until: ISO 8601 date string to filter commits before this date.

    Returns:
        List of commit dicts with author, date, message, stats.
    """
    params: dict[str, Any] = {"per_page": per_page, "page": 1}
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    commits: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        params["page"] = page
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/repos/{owner}/{repo}/commits",
                params=params,
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        commits.extend(resp)
    return commits


def get_repo_pull_requests(
    token: str,
    owner: str,
    repo: str,
    *,
    state: str = "all",
    per_page: int = 100,
    pages: int = 3,
) -> list[dict[str, Any]]:
    """Fetch pull requests for a repository (paginated).

    Args:
        state: "open", "closed", or "all".

    Returns:
        List of PR dicts with author, state, created_at, merged_at, reviews.
    """
    prs: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/repos/{owner}/{repo}/pulls",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        prs.extend(resp)
    return prs


def get_repo_issues(
    token: str,
    owner: str,
    repo: str,
    *,
    state: str = "all",
    per_page: int = 100,
    pages: int = 3,
) -> list[dict[str, Any]]:
    """Fetch issues for a repository (paginated).

    Note: GitHub API returns both issues and PRs. Filter by 'pull_request' key to separate.

    Args:
        state: "open", "closed", or "all".

    Returns:
        List of issue dicts (excluding PRs).
    """
    issues: list[dict[str, Any]] = []
    for page in range(1, pages + 1):
        try:
            resp = _request(
                token,
                "GET",
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                params={
                    "state": state,
                    "per_page": per_page,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                },
            )
        except ApiError as e:
            if "404" in str(e):
                return []
            raise
        if not resp:
            break
        # Filter out PRs (issues that have a 'pull_request' key)
        issues.extend([item for item in resp if "pull_request" not in item])
    return issues


def get_pull_request_reviews(
    token: str, owner: str, repo: str, pr_number: int, *, per_page: int = 100
) -> list[dict[str, Any]]:
    """Fetch reviews for a specific pull request.

    Returns:
        List of review dicts with reviewer, state, submitted_at, body.
    """
    try:
        resp = _request(
            token,
            "GET",
            f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews",
            params={"per_page": per_page},
        )
    except ApiError as e:
        if "404" in str(e):
            return []
        raise
    return resp


def get_repo_details(token: str, owner: str, repo: str) -> dict[str, Any] | None:
    """Fetch detailed repository information.

    Returns:
        Dict with repo details or None if not found.
    """
    try:
        resp = _request(token, "GET", f"https://api.github.com/repos/{owner}/{repo}")
    except ApiError as e:
        if "404" in str(e):
            return None
        raise
    return {
        "name": resp.get("name", ""),
        "full_name": resp.get("full_name", ""),
        "description": resp.get("description", ""),
        "language": resp.get("language"),
        "stargazers_count": resp.get("stargazers_count", 0),
        "forks_count": resp.get("forks_count", 0),
        "watchers_count": resp.get("watchers_count", 0),
        "open_issues_count": resp.get("open_issues_count", 0),
        "size": resp.get("size", 0),
        "default_branch": resp.get("default_branch", ""),
        "created_at": resp.get("created_at", ""),
        "updated_at": resp.get("updated_at", ""),
        "pushed_at": resp.get("pushed_at", ""),
        "license": resp.get("license", {}).get("name") if resp.get("license") else None,
        "topics": resp.get("topics", []),
        "archived": resp.get("archived", False),
        "disabled": resp.get("disabled", False),
        "fork": resp.get("fork", False),
    }
