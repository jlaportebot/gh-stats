# Copyright 2025 jlaportebot. All rights reserved.
# Use of this source code is governed by a MIT-style license that can be
# found in the LICENSE file.

"""GitHub API client — authenticates via `gh` CLI token and fetches activity data."""

from __future__ import annotations

import atexit
import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from typing import Any

import httpx

logger = logging.getLogger("gh_stats")

_client: httpx.Client | None = None


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
        result = subprocess.run(
            ["gh", "auth", "token"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    msg = "No GitHub token found. Set GH_TOKEN or install and authenticate `gh` CLI."
    raise AuthError(msg)


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
        return contributions
    except (KeyError, TypeError) as exc:
        logger.warning("Failed to parse contribution calendar: %s", exc)
        return {}


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
        try:
            _client.close()
        except Exception:  # noqa: BLE001
            pass
    _client = None


def _request(
    token: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
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
        raise ApiError(f"Request to {url} timed out: {exc}") from exc
    except httpx.ConnectError as exc:
        raise ApiError(f"Cannot connect to {url}: {exc}") from exc
    except httpx.NetworkError as exc:
        raise ApiError(f"Network error contacting {url}: {exc}") from exc

    if resp.status_code == 401:
        raise AuthError("GitHub token is invalid or expired.")
    if resp.status_code == 403:
        raise ApiError("Rate limited or forbidden.")
    if resp.status_code >= 400:
        raise ApiError(f"API error {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _graphql(token: str, query: str, *, variables: dict[str, Any] | None = None) -> Any:
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
        raise ApiError(f"GraphQL request timed out: {exc}") from exc
    except httpx.ConnectError as exc:
        raise ApiError(f"Cannot connect to GraphQL endpoint: {exc}") from exc
    except httpx.NetworkError as exc:
        raise ApiError(f"Network error on GraphQL request: {exc}") from exc

    if resp.status_code == 401:
        raise AuthError("GitHub token is invalid or expired.")
    if resp.status_code >= 400:
        raise ApiError(f"GraphQL error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    if "errors" in data:
        raise ApiError(f"GraphQL errors: {json.dumps(data['errors'])[:300]}")
    return data
