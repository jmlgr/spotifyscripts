"""
Shared Spotify authentication and client utilities.

Handles OAuth2 Authorization Code Flow for user sign-in, supporting both
local execution and Docker container environments.
"""

import logging
import os
import sys
import time

import requests
import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

logger = logging.getLogger(__name__)

SCOPES = [
    "playlist-read-private",
    "playlist-read-collaborative",
    "playlist-modify-public",
    "playlist-modify-private",
    "user-read-private",
]

# Spotify curated playlist names
DISCOVER_WEEKLY_NAME = "Discover Weekly"
RELEASE_RADAR_NAME = "Release Radar"
DAYLIST_NAME = "daylist"

MAX_RETRIES = 3
RETRY_BACKOFF = 1.0  # seconds, doubled each retry


def _retry_on_transient(func):
    """Decorator that retries on rate limits, network errors, and server errors."""

    def wrapper(*args, **kwargs):
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except spotipy.SpotifyException as exc:
                if exc.http_status == 429:
                    retry_after = int(exc.headers.get("Retry-After", 1)) if exc.headers else 1
                    logger.warning("Rate limited. Waiting %d seconds.", retry_after)
                    time.sleep(retry_after)
                    continue
                if exc.http_status >= 500:
                    wait = RETRY_BACKOFF * (2 ** attempt)
                    logger.warning("Server error %d. Retrying in %.1fs.", exc.http_status, wait)
                    time.sleep(wait)
                    continue
                raise
            except (requests.ConnectionError, requests.Timeout) as exc:
                wait = RETRY_BACKOFF * (2 ** attempt)
                logger.warning("Network error: %s. Retrying in %.1fs.", exc, wait)
                time.sleep(wait)
                continue
        return func(*args, **kwargs)  # final attempt, let exceptions propagate

    return wrapper


def get_spotify_client(scopes: list[str] | None = None) -> spotipy.Spotify:
    """
    Create and return an authenticated Spotify client.

    Reads SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET and SPOTIPY_REDIRECT_URI
    from environment variables (or a .env file).  The OAuth token cache is
    stored in .cache (or .cache-<username> when SPOTIFY_USERNAME is set).
    """
    client_id = os.getenv("SPOTIPY_CLIENT_ID")
    client_secret = os.getenv("SPOTIPY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")
    username = os.getenv("SPOTIFY_USERNAME", "")

    if not client_id or not client_secret:
        logger.error(
            "SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set. "
            "Run setup.py to configure your credentials."
        )
        sys.exit(1)

    scope_str = " ".join(scopes or SCOPES)
    cache_path = f".cache-{username}" if username else ".cache"

    try:
        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope_str,
            username=username or None,
            cache_path=cache_path,
            open_browser=True,
        )
        return spotipy.Spotify(auth_manager=auth_manager)
    except spotipy.SpotifyException as exc:
        logger.error("Authentication failed: %s", exc)
        logger.error("Try re-running setup.py to refresh your credentials.")
        sys.exit(1)


@_retry_on_transient
def get_current_user_id(sp: spotipy.Spotify) -> str:
    """Return the current authenticated user's Spotify ID."""
    user = sp.current_user()
    if not user or "id" not in user:
        raise ValueError("Unexpected response from Spotify: missing user ID")
    return user["id"]


def find_playlist_by_name(
    sp: spotipy.Spotify,
    name: str,
    exact: bool = False,
    prefix: bool = False,
) -> dict | None:
    """
    Search the current user's playlists for one matching *name*.

    Parameters
    ----------
    sp:     Authenticated Spotify client.
    name:   Playlist name to search for.
    exact:  When True, only return a playlist whose name matches exactly
            (case-insensitive).
    prefix: When True, match playlists whose name starts with *name*
            (case-insensitive). Useful for Spotify's daylist which appends
            mood/time info.

    If neither exact nor prefix is set, uses case-insensitive substring match.
    Returns the first matching playlist object, or None.
    """
    offset = 0
    limit = 50
    name_lower = name.lower()

    while True:
        results = _fetch_user_playlists(sp, limit=limit, offset=offset)
        items = results.get("items", [])
        for playlist in items:
            playlist_name = (playlist.get("name") or "").lower()
            if exact and playlist_name == name_lower:
                return playlist
            if prefix and playlist_name.startswith(name_lower):
                return playlist
            if not exact and not prefix and name_lower in playlist_name:
                return playlist

        if results.get("next"):
            offset += limit
        else:
            break

    return None


@_retry_on_transient
def _fetch_user_playlists(sp: spotipy.Spotify, limit: int, offset: int) -> dict:
    """Fetch a page of the current user's playlists with retry support."""
    return sp.current_user_playlists(limit=limit, offset=offset)


@_retry_on_transient
def get_all_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """
    Fetch every track from a playlist, handling Spotify's pagination.

    Returns a list of track objects (the 'track' key inside each item).
    Locally-cached / unavailable tracks (None) are skipped.
    """
    tracks: list[dict] = []
    results = sp.playlist_tracks(playlist_id)

    while True:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(track)
            elif track:
                logger.warning("Skipping track without ID: %s", track.get("name", "unknown"))
        if results.get("next"):
            results = sp.next(results)
        else:
            break

    return tracks


def get_albums_from_tracks(tracks: list[dict]) -> list[dict]:
    """
    Extract unique albums from a list of tracks, preserving encounter order.

    Returns a list of album objects (deduplicated by album ID).
    """
    seen: set[str] = set()
    albums: list[dict] = []
    for track in tracks:
        album = track.get("album")
        if album and album.get("id") and album["id"] not in seen:
            seen.add(album["id"])
            albums.append(album)
    return albums


@_retry_on_transient
def get_album_track_ids(sp: spotipy.Spotify, album_id: str) -> list[str]:
    """Return all track IDs for a given album."""
    track_ids: list[str] = []
    results = sp.album_tracks(album_id, limit=50)
    while True:
        for item in results.get("items", []):
            if item.get("id"):
                track_ids.append(item["id"])
            else:
                logger.warning("Skipping album track without ID in album %s", album_id)
        if results.get("next"):
            results = sp.next(results)
        else:
            break
    return track_ids


@_retry_on_transient
def create_playlist(
    sp: spotipy.Spotify,
    user_id: str,
    name: str,
    description: str = "",
    public: bool = False,
) -> dict:
    """Create a new Spotify playlist and return the playlist object."""
    result = sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description=description,
    )
    if not result or "id" not in result:
        raise ValueError("Unexpected response from Spotify: missing playlist ID")
    return result


@_retry_on_transient
def add_tracks_to_playlist(
    sp: spotipy.Spotify, playlist_id: str, track_ids: list[str]
) -> None:
    """
    Add tracks to a playlist in batches of 100 (Spotify API limit).

    Parameters
    ----------
    sp:          Authenticated Spotify client.
    playlist_id: Target playlist ID.
    track_ids:   List of Spotify track IDs to add.
    """
    batch_size = 100
    for i in range(0, len(track_ids), batch_size):
        batch = track_ids[i : i + batch_size]
        sp.playlist_add_items(playlist_id, batch)
