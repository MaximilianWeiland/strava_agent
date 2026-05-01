import os
import time
from pathlib import Path
import httpx
from datetime import datetime
from typing import Literal, Optional
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv, set_key

load_dotenv()

mcp = FastMCP("strava")

STRAVA_BASE_URL = "https://www.strava.com/api/v3"
ENV_PATH = Path(__file__).parent.parent.parent / ".env"


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


@mcp.prompt()
def system_prompt() -> str:
    """Instructions for the Strava agent"""
    script_dir = os.path.dirname(__file__)
    prompt_path = os.path.join(script_dir, "prompts", "system_instructions.md")
    with open(prompt_path, "r") as file:
        return file.read()


@mcp.tool()
def get_athlete_stats() -> dict:
    """Get the activity stats of the authenticated athlete. Returns statistics about recent and total activities."""
    with httpx.Client() as client:
        athlete = client.get(f"{STRAVA_BASE_URL}/athlete", headers=_headers()).json()
        r = client.get(
            f"{STRAVA_BASE_URL}/athletes/{athlete['id']}/stats", headers=_headers()
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_athlete() -> dict:
    """Get the authenticated athlete's profile. Returns basic personal information, the athlete ID as well as the athlete's equipment."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/athlete", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_athlete_zones() -> list[dict]:
    """Get the authenticated athlete's heart rate and power zones. Returns the zone information in distribution buckets."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/athlete/zones", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_segment(id: int) -> dict:
    """Get general information about the specified segments, such as the segment ID, as well as athlete-specific segment information, such as personal records on this segment."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segments/{id}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_segments_starred(page: int = 1, per_page: int = 30) -> list[dict]:
    """List the authenticated athlete's starred segments. Returns a list of the starred segments."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segments/starred",
            headers=_headers(),
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def explore_segments(
    bounds: list[float],
    activity_type: Literal["running", "riding"],
    min_cat: int = 0,
    max_cat: int = 5,
) -> dict:
    """Get the top 10 segments matching within a specified geographic bounding box, ranked by popularity.

    bounds: [sw_lat, sw_lng, ne_lat, ne_lng]
    """
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segments/explore",
            headers=_headers(),
            params={
                "bounds": ",".join(str(b) for b in bounds),
                "activity_type": activity_type,
                "min_cat": min_cat,
                "max_cat": max_cat,
            },
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_all_segment_efforts(
    segment_id: int,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    per_page: int = 30,
) -> list[dict]:
    """List efforts on a segment for the authenticated athlete, optionally filtered by date range.
    Returns the segment effort ID, specific information of the effort, such as the athlete's personal and overall ranking on it, as well as general information on the segment.
    """
    params: dict = {"segment_id": segment_id, "per_page": per_page}
    if start_date:
        params["start_date_local"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
    if end_date:
        params["end_date_local"] = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")

    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segment_efforts",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_specific_segment_effort(
    segment_effort_id: int,
) -> dict:
    """Get information about a specific segment effort specified by segment effort ID of the authenticated athlete.
    Returns specific information of the effort, such as the athlete's personal and overall ranking on it, as well as general information on the segment.
    """
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segment_efforts/{segment_effort_id}",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def explore_activity(id: int, include_all_efforts: bool = False) -> dict:
    """Explore an activity of the authenticated athlete specified by the activity ID.
    Returns general information on the activity (distance, elevation, latlng), all segment efforts, split and laps data."""
    params = {"include_all_efforts": str(include_all_efforts).lower()}
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{id}",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def list_activities(
    before: Optional[datetime] = None,
    after: Optional[datetime] = None,
    page: int = 1,
    per_page: int = 30,
) -> list[dict]:
    """List the authenticated athlete's activities."""
    params: dict = {"page": page, "per_page": per_page}
    if before:
        params["before"] = int(before.timestamp())
    if after:
        params["after"] = int(after.timestamp())

    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/athlete/activities",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_activity_laps(activity_id: int) -> list[dict]:
    """Get information about the laps of an activity specified by activity ID."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{activity_id}/laps",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_activity_zones(activity_id: int) -> list[dict]:
    """Get information about the zones of an activity specified by activity ID."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{activity_id}/zones",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_activity_comments(
    activity_id: int, page_size: int = 30, after_cursor: Optional[str] = None
) -> list[dict]:
    """Get all comments of an activity specified by activity ID."""
    params = {"page_size": page_size}
    if after_cursor:
        params["after_cursor"] = after_cursor

    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{activity_id}/comments",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_activity_kudos(
    activity_id: int, page: int = 1, per_page: int = 30
) -> list[dict]:
    """Get information about the kudos given for an activity specified by activity ID."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{activity_id}/kudos",
            headers=_headers(),
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_route(route_id: int) -> dict:
    """Get information about a route specified by route ID."""
    with httpx.Client() as client:
        r = client.get(f"{STRAVA_BASE_URL}/routes/{route_id}", headers=_headers())
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_all_routes(page: int = 1, per_page: int = 30) -> list[dict]:
    """Get all routes created by the authenticated athlete."""
    with httpx.Client() as client:
        athlete = client.get(f"{STRAVA_BASE_URL}/athlete", headers=_headers()).json()
        r = client.get(
            f"{STRAVA_BASE_URL}/athletes/{athlete['id']}/routes",
            headers=_headers(),
            params={"page": page, "per_page": per_page},
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def export_gpx(route_id: int) -> str:
    """Export the GPX file of a route specified by route ID."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/routes/{route_id}/export_gpx",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.text


@mcp.tool()
def get_activity_stream(
    activity_id: int,
    keys: list[
        Literal[
            "time",
            "distance",
            "latlng",
            "altitude",
            "velocity_smooth",
            "heartrate",
            "cadence",
            "watts",
            "temp",
            "moving",
            "grade_smooth",
        ]
    ],
    key_by_type: bool = True,
) -> list[dict]:
    """Get the stream of a specific activity. Available streams are: time, distance, latlng, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth."""
    params = {"keys": ",".join(keys), "key_by_type": str(key_by_type).lower()}
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/activities/{activity_id}/streams",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_segment_effort_stream(
    segment_effort_id: int,
    keys: list[
        Literal[
            "time",
            "distance",
            "latlng",
            "altitude",
            "velocity_smooth",
            "heartrate",
            "cadence",
            "watts",
            "temp",
            "moving",
            "grade_smooth",
        ]
    ],
    key_by_type: bool = True,
) -> list[dict]:
    """Get the stream of a specific segment effort by the authenticated athlete. Available streams are: time, distance, latlng, altitude, velocity_smooth, heartrate, cadence, watts, temp, moving, grade_smooth."""
    params = {"keys": ",".join(keys), "key_by_type": str(key_by_type).lower()}
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segment_efforts/{segment_effort_id}/streams",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_segment_stream(
    segment_id: int,
    keys: list[Literal["distance", "latlng", "altitude"]],
    key_by_type: bool = True,
) -> list[dict]:
    """Get the stream of a specific segment. Available streams are: distance, latlng, altitude."""
    params = {"keys": ",".join(keys), "key_by_type": str(key_by_type).lower()}

    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/segments/{segment_id}/streams",
            headers=_headers(),
            params=params,
        )
        r.raise_for_status()
        return r.json()


@mcp.tool()
def get_route_stream(route_id: int) -> list[dict]:
    """Get the stream of a specific route specified by route ID. Returns streams on latlng, distance and altitude."""
    with httpx.Client() as client:
        r = client.get(
            f"{STRAVA_BASE_URL}/routes/{route_id}/streams",
            headers=_headers(),
        )
        r.raise_for_status()
        return r.json()


if __name__ == "__main__":
    mcp.run(transport="stdio")
