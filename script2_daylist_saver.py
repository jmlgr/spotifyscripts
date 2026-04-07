#!/usr/bin/env python3
"""
Script 2 -- Current Daylist Saver

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
import logging
import sys
from datetime import date

import spotipy

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

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

MODES = ("tracks", "albums")
TODAY = date.today().isoformat()


def run(mode: str = "tracks") -> None:
    if mode not in MODES:
        logger.error("--mode must be one of: %s", ", ".join(MODES))
        sys.exit(1)

    logger.info("Current Daylist Saver (mode=%s)", mode)

    sp = get_spotify_client()
    user_id = get_current_user_id(sp)
    logger.info("Signed in as: %s", user_id)

    logger.info("Looking for '%s' playlist...", DAYLIST_NAME)
    daylist = find_playlist_by_name(sp, DAYLIST_NAME, prefix=True)
    if not daylist:
        logger.error("Could not find a playlist starting with '%s'.", DAYLIST_NAME)
        logger.error("Make sure the Daylist appears in your Spotify library.")
        sys.exit(1)

    daylist_title = daylist.get("name", DAYLIST_NAME)
    daylist_description = daylist.get("description", "")
    logger.info("Found '%s' (%s)", daylist_title, daylist.get("id"))

    logger.info("Loading tracks...")
    tracks = get_all_playlist_tracks(sp, daylist["id"])
    logger.info("Loaded %d track(s).", len(tracks))

    if not tracks:
        logger.error("The daylist appears to be empty. Exiting.")
        sys.exit(1)

    if mode == "tracks":
        track_ids = [t["id"] for t in tracks if t.get("id")]
        playlist_name = f"{daylist_title} -- {TODAY}"
        description = (
            f"Saved daylist: {daylist_description or daylist_title} ({TODAY}). "
            "Created by spotifyscripts."
        ).strip()
        logger.info("Saving %d track(s) to new playlist...", len(track_ids))

    else:
        albums = get_albums_from_tracks(tracks)
        logger.info("Unique albums: %d", len(albums))

        track_ids: list[str] = []
        for album in albums:
            ids = get_album_track_ids(sp, album["id"])
            track_ids.extend(ids)

        playlist_name = f"{daylist_title} Albums -- {TODAY}"
        description = (
            f"Albums from daylist: {daylist_description or daylist_title} ({TODAY}). "
            "Created by spotifyscripts."
        ).strip()
        logger.info(
            "Built album playlist: %d album(s), %d track(s) total.",
            len(albums),
            len(track_ids),
        )

    if not track_ids:
        logger.error("No tracks to add. Exiting.")
        sys.exit(1)

    logger.info("Creating playlist: '%s'...", playlist_name)
    new_playlist = create_playlist(
        sp, user_id, playlist_name, description=description, public=False
    )
    playlist_id = new_playlist["id"]
    logger.info("Playlist created (id=%s)", playlist_id)

    logger.info("Adding %d track(s)...", len(track_ids))
    add_tracks_to_playlist(sp, playlist_id, track_ids)
    logger.info("Done!")

    playlist_url = new_playlist.get("external_urls", {}).get("spotify", "")
    if playlist_url:
        logger.info("Open in Spotify: %s", playlist_url)


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
