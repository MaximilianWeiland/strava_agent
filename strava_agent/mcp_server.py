"""Local MCP server exposing Strava API as tools."""

import os
import time
from pathlib import Path
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, set_key

load_dotenv()

mcp = FastMCP("strava")

STRAVA_BASE_URL = "https://www.strava.com/api/v3"
ENV_PATH = Path(__file__).parent.parent / ".env"


def _refresh_token_if_needed() -> None:
    expires_at = int(os.environ.get("STRAVA_TOKEN_EXPIRES_AT", "0"))
    if time.time() < expires_at - 60:
        return

    r = httpx.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": os.environ["STRAVA_CLIENT_ID"],
            "client_secret": os.environ["STRAVA_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ["STRAVA_REFRESH_TOKEN"],
        },
    )
    r.raise_for_status()
    data = r.json()

    # update environment in memory
    os.environ["STRAVA_ACCESS_TOKEN"] = data["access_token"]
    os.environ["STRAVA_REFRESH_TOKEN"] = data["refresh_token"]
    os.environ["STRAVA_TOKEN_EXPIRES_AT"] = str(data["expires_at"])

    # update environment on disk
    set_key(ENV_PATH, "STRAVA_ACCESS_TOKEN", data["access_token"])
    set_key(ENV_PATH, "STRAVA_REFRESH_TOKEN", data["refresh_token"])
    set_key(ENV_PATH, "STRAVA_TOKEN_EXPIRES_AT", str(data["expires_at"]))


def _headers() -> dict[str, str]:
    _refresh_token_if_needed()
    return {"Authorization": f"Bearer {os.environ['STRAVA_ACCESS_TOKEN']}"}


@mcp.tool()
def get_athlete() -> dict:
    """Get the authenticated athlete's profile."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/athlete", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def list_activities(page: int = 1, per_page: int = 30) -> list[dict]:
    """List the authenticated athlete's activities."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/athlete/activities",
            headers=_headers(),
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_activity(activity_id: int) -> dict:
    """Get a specific activity by ID."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/activities/{activity_id}", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_athlete_stats(athlete_id: int) -> dict:
    """Get stats for the authenticated athlete."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/athletes/{athlete_id}/stats", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def list_starred_segments(page: int = 1, per_page: int = 30) -> list[dict]:
    """List the authenticated athlete's starred segments."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segments/starred",
            headers=_headers(),
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_segment(segment_id: int) -> dict:
    """Get details for a specific segment."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/segments/{segment_id}", headers=_headers())
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    mcp.run()
