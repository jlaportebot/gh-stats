"""GitHub API client — authenticates via `gh` CLI token and fetches activity data."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from typing import Any

import httpx


class AuthError(Exception):
    """Raised when GitHub authentication fails."""


class ApiError(Exception):
    """Raised when a GitHub API call fails."""


def get_token() -> str:
    """Get a GitHub API token.

    Priority:
    1. GH_TOKEN / GITHUB_TOKEN env var
    2. `gh auth token` output
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
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass

    raise AuthError(
        "No GitHub token found. Set GH_TOKEN or install and authenticate `gh` CLI."
    )


def get_authenticated_user(token: str) -> dict[str, Any]:
    """Fetch the authenticated user's profile."""
    resp = _request(token, "GET", "https://api.github.com/user")
    return resp


def get_user_events(
    token: str, username: str, *, per_page: int = 100, pages: int = 3
) -> list[dict[str, Any]]:
    """Fetch recent public events for a user (paginated)."""
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
    """Fetch repos owned by the user, sorted by updated date."""
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
    """
    now = datetime.now(timezone.utc)
    if year is None:
        year = now.year

    # Query from Jan 1 of the year to today (or Dec 31 if past year)
    from_date = f"{year}-01-01T00:00:00Z"
    if year == now.year:
        to_date = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    else:
        to_date = f"{year}-12-31T23:59:59Z"

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
    except (KeyError, TypeError):
        return {}


def get_user_stats(token: str, username: str) -> dict[str, Any]:
    """Fetch aggregate stats for the user profile card."""
    user = get_authenticated_user(token) if username == _get_current_login(token) else _request(
        token, "GET", f"https://api.github.com/users/{username}"
    )
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


def _get_current_login(token: str) -> str:
    """Get the login of the authenticated user from the token."""
    user = get_authenticated_user(token)
    return user.get("login", "")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_client = httpx.Client(timeout=30.0)


def _request(
    token: str,
    method: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    resp = _client.request(method, url, headers=headers, params=params)
    if resp.status_code == 401:
        raise AuthError("GitHub token is invalid or expired.")
    if resp.status_code == 403:
        raise ApiError(f"Rate limited or forbidden: {resp.status_code}")
    if resp.status_code >= 400:
        raise ApiError(f"API error {resp.status_code}: {resp.text[:200]}")
    return resp.json()


def _graphql(token: str, query: str, *, variables: dict[str, Any] | None = None) -> Any:
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    payload: dict[str, Any] = {"query": query}
    if variables:
        payload["variables"] = variables
    resp = _client.post(
        "https://api.github.com/graphql",
        headers=headers,
        json=payload,
    )
    if resp.status_code == 401:
        raise AuthError("GitHub token is invalid or expired.")
    if resp.status_code >= 400:
        raise ApiError(f"GraphQL error {resp.status_code}: {resp.text[:200]}")
    data = resp.json()
    if "errors" in data:
        raise ApiError(f"GraphQL errors: {json.dumps(data['errors'])[:300]}")
    return data
