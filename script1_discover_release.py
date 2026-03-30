#!/usr/bin/env python3
"""
Script 1 – Discover Weekly and Release Radar Album Playlist Maker

Loads the current user's "Discover Weekly" and/or "Release Radar" playlists
and creates a new playlist containing every full album represented by those
tracks, in order of first appearance.

Usage
-----
    python script1_discover_release.py [--mode MODE]

Options
-------
    --mode combined   (default) One playlist with Discover Weekly albums
                      followed by Release Radar albums.
    --mode discover   Playlist from Discover Weekly tracks only.
    --mode release    Playlist from Release Radar tracks only.

The resulting playlist is named with today's date stamp, e.g.:
    "Discover + Release Albums 2025-01-15"
    "Discover Weekly Albums 2025-01-15"
    "Release Radar Albums 2025-01-15"
"""

import argparse
import sys
from datetime import date

from spotify_client import (
    DISCOVER_WEEKLY_NAME,
    RELEASE_RADAR_NAME,
    add_tracks_to_playlist,
    create_playlist,
    find_playlist_by_name,
    get_album_track_ids,
    get_albums_from_tracks,
    get_all_playlist_tracks,
    get_current_user_id,
    get_spotify_client,
)

MODES = ("combined", "discover", "release")
TODAY = date.today().isoformat()


def build_album_track_list(
    sp,
    playlist_name: str,
) -> tuple[list[str], int]:
    """
    Given a source playlist name, fetch its tracks, derive unique albums in
    order, then return the full ordered list of track IDs from those albums
    together with the count of albums found.

    Returns (track_ids, album_count).
    Exits with an error message if the playlist cannot be found.
    """
    playlist = find_playlist_by_name(sp, playlist_name)
    if not playlist:
        print(f"ERROR: Could not find playlist '{playlist_name}'.", file=sys.stderr)
        print(
            "  Make sure it appears in your Spotify library and try again.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"  ✓ Found '{playlist['name']}' ({playlist['id']})")
    tracks = get_all_playlist_tracks(sp, playlist["id"])
    print(f"    Loaded {len(tracks)} track(s).")

    albums = get_albums_from_tracks(tracks)
    print(f"    Unique albums: {len(albums)}")

    track_ids: list[str] = []
    for album in albums:
        ids = get_album_track_ids(sp, album["id"])
        track_ids.extend(ids)

    return track_ids, len(albums)


def run(mode: str = "combined") -> None:
    if mode not in MODES:
        print(f"ERROR: --mode must be one of: {', '.join(MODES)}", file=sys.stderr)
        sys.exit(1)

    print(f"\n── Discover Weekly & Release Radar Album Playlist Maker (mode={mode}) ──\n")

    sp = get_spotify_client()
    user_id = get_current_user_id(sp)
    print(f"Signed in as: {user_id}\n")

    discover_tracks: list[str] = []
    release_tracks: list[str] = []

    if mode in ("combined", "discover"):
        print(f"Loading {DISCOVER_WEEKLY_NAME}…")
        discover_tracks, n_dw = build_album_track_list(sp, DISCOVER_WEEKLY_NAME)
        print(f"  → {n_dw} album(s), {len(discover_tracks)} track(s) total.\n")

    if mode in ("combined", "release"):
        print(f"Loading {RELEASE_RADAR_NAME}…")
        release_tracks, n_rr = build_album_track_list(sp, RELEASE_RADAR_NAME)
        print(f"  → {n_rr} album(s), {len(release_tracks)} track(s) total.\n")

    all_track_ids = discover_tracks + release_tracks

    if not all_track_ids:
        print("No tracks to add. Exiting.", file=sys.stderr)
        sys.exit(1)

    # Choose playlist name based on mode
    if mode == "combined":
        playlist_name = f"Discover + Release Albums {TODAY}"
        description = (
            f"Albums from Discover Weekly and Release Radar – {TODAY}. "
            "Created by spotifyscripts."
        )
    elif mode == "discover":
        playlist_name = f"Discover Weekly Albums {TODAY}"
        description = (
            f"Albums from Discover Weekly – {TODAY}. Created by spotifyscripts."
        )
    else:
        playlist_name = f"Release Radar Albums {TODAY}"
        description = (
            f"Albums from Release Radar – {TODAY}. Created by spotifyscripts."
        )

    print(f"Creating playlist: '{playlist_name}'…")
    new_playlist = create_playlist(
        sp, user_id, playlist_name, description=description, public=False
    )
    playlist_id = new_playlist["id"]
    print(f"  ✓ Playlist created (id={playlist_id})")

    print(f"Adding {len(all_track_ids)} track(s)…")
    add_tracks_to_playlist(sp, playlist_id, all_track_ids)
    print("  ✓ Done!")

    playlist_url = new_playlist.get("external_urls", {}).get("spotify", "")
    if playlist_url:
        print(f"\nOpen in Spotify: {playlist_url}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--mode",
        choices=MODES,
        default="combined",
        help="Which source playlists to use (default: combined).",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(mode=args.mode)
