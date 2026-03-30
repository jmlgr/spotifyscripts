"""
Shared Spotify authentication and client utilities.

Handles OAuth2 Authorization Code Flow for user sign-in, supporting both
local execution and Docker container environments.
"""

import os
import sys

import spotipy
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

load_dotenv()

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
        print(
            "ERROR: SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET must be set.\n"
            "Run setup.py to configure your credentials.",
            file=sys.stderr,
        )
        sys.exit(1)

    scope_str = " ".join(scopes or SCOPES)
    cache_path = f".cache-{username}" if username else ".cache"

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


def get_current_user_id(sp: spotipy.Spotify) -> str:
    """Return the current authenticated user's Spotify ID."""
    return sp.current_user()["id"]


def find_playlist_by_name(
    sp: spotipy.Spotify, name: str, exact: bool = False
) -> dict | None:
    """
    Search the current user's playlists for one matching *name*.

    Parameters
    ----------
    sp:    Authenticated Spotify client.
    name:  Playlist name to search for (case-insensitive substring match by
           default; set exact=True for a full exact match).
    exact: When True, only return a playlist whose name matches exactly.

    Returns the first matching playlist object, or None.
    """
    offset = 0
    limit = 50
    name_lower = name.lower()

    while True:
        results = sp.current_user_playlists(limit=limit, offset=offset)
        items = results.get("items", [])
        for playlist in items:
            playlist_name = playlist.get("name", "")
            if exact:
                if playlist_name.lower() == name_lower:
                    return playlist
            else:
                if name_lower in playlist_name.lower():
                    return playlist

        if results.get("next"):
            offset += limit
        else:
            break

    return None


def get_all_playlist_tracks(sp: spotipy.Spotify, playlist_id: str) -> list[dict]:
    """
    Fetch every track from a playlist, handling Spotify's pagination.

    Returns a list of track objects (the 'track' key inside each item).
    Locally-cached / unavailable tracks (None) are skipped.
    """
    tracks = []
    results = sp.playlist_tracks(playlist_id)

    while True:
        for item in results.get("items", []):
            track = item.get("track")
            if track and track.get("id"):
                tracks.append(track)
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


def get_album_track_ids(sp: spotipy.Spotify, album_id: str) -> list[str]:
    """Return all track IDs for a given album."""
    track_ids: list[str] = []
    results = sp.album_tracks(album_id, limit=50)
    while True:
        for item in results.get("items", []):
            if item.get("id"):
                track_ids.append(item["id"])
        if results.get("next"):
            results = sp.next(results)
        else:
            break
    return track_ids


def create_playlist(
    sp: spotipy.Spotify,
    user_id: str,
    name: str,
    description: str = "",
    public: bool = False,
) -> dict:
    """Create a new Spotify playlist and return the playlist object."""
    return sp.user_playlist_create(
        user=user_id,
        name=name,
        public=public,
        description=description,
    )


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
