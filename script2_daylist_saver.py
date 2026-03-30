#!/usr/bin/env python3
"""
Script 2 – Current Daylist Saver

Finds the current user's "daylist" playlist and saves it as a new playlist
using one of two modes:

Usage
-----
    python script2_daylist_saver.py [--mode MODE]

Options
-------
    --mode tracks   (default) Save the daylist tracks as-is into a new
                    standalone playlist.  The playlist name and description
                    mirror the original daylist title, suffixed with today's
                    date stamp.

    --mode albums   For each track in the daylist, find its full album and
                    add every song from those albums (in order) to a new
                    playlist.  Duplicate albums are deduplicated while
                    preserving encounter order.

Examples
--------
    python script2_daylist_saver.py
    python script2_daylist_saver.py --mode albums
"""

import argparse
import sys
from datetime import date

from spotify_client import (
    DAYLIST_NAME,
    add_tracks_to_playlist,
    create_playlist,
    find_playlist_by_name,
    get_album_track_ids,
    get_albums_from_tracks,
    get_all_playlist_tracks,
    get_current_user_id,
    get_spotify_client,
)

MODES = ("tracks", "albums")
TODAY = date.today().isoformat()


def run(mode: str = "tracks") -> None:
    if mode not in MODES:
        print(f"ERROR: --mode must be one of: {', '.join(MODES)}", file=sys.stderr)
        sys.exit(1)

    print(f"\n── Current Daylist Saver (mode={mode}) ──\n")

    sp = get_spotify_client()
    user_id = get_current_user_id(sp)
    print(f"Signed in as: {user_id}\n")

    print(f"Looking for '{DAYLIST_NAME}' playlist…")
    daylist = find_playlist_by_name(sp, DAYLIST_NAME)
    if not daylist:
        print(
            f"ERROR: Could not find a playlist named '{DAYLIST_NAME}'.",
            file=sys.stderr,
        )
        print(
            "  Make sure the Daylist appears in your Spotify library.",
            file=sys.stderr,
        )
        sys.exit(1)

    daylist_title = daylist.get("name", DAYLIST_NAME)
    daylist_description = daylist.get("description", "")
    print(f"  ✓ Found '{daylist_title}' ({daylist['id']})")

    print("  Loading tracks…")
    tracks = get_all_playlist_tracks(sp, daylist["id"])
    print(f"  Loaded {len(tracks)} track(s).")

    if not tracks:
        print("  The daylist appears to be empty. Exiting.", file=sys.stderr)
        sys.exit(1)

    if mode == "tracks":
        # Save the daylist tracks as-is
        track_ids = [t["id"] for t in tracks if t.get("id")]
        playlist_name = f"{daylist_title} – {TODAY}"
        description = (
            f"Saved daylist: {daylist_description or daylist_title} ({TODAY}). "
            "Created by spotifyscripts."
        ).strip()
        print(f"\nSaving {len(track_ids)} track(s) to new playlist…")

    else:
        # Build full albums from the daylist tracks
        albums = get_albums_from_tracks(tracks)
        print(f"  Unique albums: {len(albums)}")

        track_ids: list[str] = []
        for album in albums:
            ids = get_album_track_ids(sp, album["id"])
            track_ids.extend(ids)

        playlist_name = f"{daylist_title} Albums – {TODAY}"
        description = (
            f"Albums from daylist: {daylist_description or daylist_title} ({TODAY}). "
            "Created by spotifyscripts."
        ).strip()
        print(
            f"\nBuilt album playlist: {len(albums)} album(s), "
            f"{len(track_ids)} track(s) total."
        )

    if not track_ids:
        print("No tracks to add. Exiting.", file=sys.stderr)
        sys.exit(1)

    print(f"Creating playlist: '{playlist_name}'…")
    new_playlist = create_playlist(
        sp, user_id, playlist_name, description=description, public=False
    )
    playlist_id = new_playlist["id"]
    print(f"  ✓ Playlist created (id={playlist_id})")

    print(f"Adding {len(track_ids)} track(s)…")
    add_tracks_to_playlist(sp, playlist_id, track_ids)
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
        default="tracks",
        help="Save the daylist as tracks (default) or as full albums.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run(mode=args.mode)
