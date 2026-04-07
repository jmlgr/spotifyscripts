"""
Unit tests for spotify_client.py helper functions and both script entry points.
These tests mock all Spotify API calls so no credentials are needed.
"""

import unittest
from unittest.mock import MagicMock, patch

import requests
import spotipy

# ---------------------------------------------------------------------------
# Helpers to build fake Spotify API objects
# ---------------------------------------------------------------------------

def make_track(track_id: str, album_id: str) -> dict:
    return {
        "id": track_id,
        "name": f"Track {track_id}",
        "album": {"id": album_id, "name": f"Album {album_id}"},
    }


def make_playlist(playlist_id: str, name: str, description: str = "") -> dict:
    return {
        "id": playlist_id,
        "name": name,
        "description": description,
        "external_urls": {"spotify": f"https://open.spotify.com/playlist/{playlist_id}"},
    }


def paged(items: list, has_next: bool = False) -> dict:
    return {"items": items, "next": "url" if has_next else None}


# ---------------------------------------------------------------------------
# Tests for spotify_client helpers
# ---------------------------------------------------------------------------

class TestGetAlbumsFromTracks(unittest.TestCase):
    def test_returns_unique_albums_in_order(self):
        from spotify_client import get_albums_from_tracks

        tracks = [
            make_track("t1", "a1"),
            make_track("t2", "a2"),
            make_track("t3", "a1"),  # duplicate album
            make_track("t4", "a3"),
        ]
        albums = get_albums_from_tracks(tracks)
        self.assertEqual([a["id"] for a in albums], ["a1", "a2", "a3"])

    def test_empty_list(self):
        from spotify_client import get_albums_from_tracks

        self.assertEqual(get_albums_from_tracks([]), [])

    def test_tracks_without_album_id_are_skipped(self):
        from spotify_client import get_albums_from_tracks

        tracks = [
            {"id": "t1", "album": None},
            {"id": "t2", "album": {"id": "", "name": "Empty"}},
            make_track("t3", "a1"),
        ]
        albums = get_albums_from_tracks(tracks)
        self.assertEqual([a["id"] for a in albums], ["a1"])


class TestGetAllPlaylistTracks(unittest.TestCase):
    def test_paginates_correctly(self):
        from spotify_client import get_all_playlist_tracks

        sp = MagicMock()
        page1 = paged([{"track": make_track("t1", "a1")}, {"track": make_track("t2", "a2")}], has_next=True)
        page2 = paged([{"track": make_track("t3", "a3")}], has_next=False)
        sp.playlist_tracks.return_value = page1
        sp.next.return_value = page2

        tracks = get_all_playlist_tracks(sp, "pid")
        self.assertEqual([t["id"] for t in tracks], ["t1", "t2", "t3"])

    def test_skips_none_tracks(self):
        from spotify_client import get_all_playlist_tracks

        sp = MagicMock()
        sp.playlist_tracks.return_value = paged(
            [{"track": None}, {"track": make_track("t1", "a1")}]
        )
        tracks = get_all_playlist_tracks(sp, "pid")
        self.assertEqual(len(tracks), 1)
        self.assertEqual(tracks[0]["id"], "t1")


class TestFindPlaylistByName(unittest.TestCase):
    def test_finds_by_substring(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged(
            [make_playlist("p1", "Discover Weekly"), make_playlist("p2", "Release Radar")]
        )
        result = find_playlist_by_name(sp, "Discover")
        self.assertIsNotNone(result)
        self.assertEqual(result["id"], "p1")

    def test_returns_none_when_not_found(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged(
            [make_playlist("p1", "My Playlist")]
        )
        result = find_playlist_by_name(sp, "Daylist")
        self.assertIsNone(result)

    def test_exact_match(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged(
            [make_playlist("p1", "daylist - evening vibes - monday"), make_playlist("p2", "daylist")]
        )
        result = find_playlist_by_name(sp, "daylist", exact=True)
        self.assertEqual(result["id"], "p2")

    def test_prefix_match(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged([
            make_playlist("p1", "my daylist backup"),
            make_playlist("p2", "daylist - chill morning monday"),
        ])
        result = find_playlist_by_name(sp, "daylist", prefix=True)
        # Should match p2 (starts with "daylist"), not p1 ("my daylist...")
        self.assertEqual(result["id"], "p2")

    def test_prefix_match_no_result(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged([
            make_playlist("p1", "my daylist backup"),
        ])
        result = find_playlist_by_name(sp, "daylist", prefix=True)
        self.assertIsNone(result)

    def test_exact_match_rejects_substring(self):
        from spotify_client import find_playlist_by_name

        sp = MagicMock()
        sp.current_user_playlists.return_value = paged([
            make_playlist("p1", "My Discover Weekly Extended"),
        ])
        result = find_playlist_by_name(sp, "Discover Weekly", exact=True)
        self.assertIsNone(result)


class TestAddTracksToPlaylist(unittest.TestCase):
    def test_batches_correctly(self):
        from spotify_client import add_tracks_to_playlist

        sp = MagicMock()
        track_ids = [f"t{i}" for i in range(250)]
        add_tracks_to_playlist(sp, "pid", track_ids)

        # Expect 3 calls: 100 + 100 + 50
        self.assertEqual(sp.playlist_add_items.call_count, 3)
        calls = sp.playlist_add_items.call_args_list
        self.assertEqual(len(calls[0][0][1]), 100)
        self.assertEqual(len(calls[1][0][1]), 100)
        self.assertEqual(len(calls[2][0][1]), 50)

    def test_empty_list_makes_no_call(self):
        from spotify_client import add_tracks_to_playlist

        sp = MagicMock()
        add_tracks_to_playlist(sp, "pid", [])
        sp.playlist_add_items.assert_not_called()


class TestGetAlbumTrackIds(unittest.TestCase):
    def test_returns_ids(self):
        from spotify_client import get_album_track_ids

        sp = MagicMock()
        sp.album_tracks.return_value = paged([{"id": "t1"}, {"id": "t2"}])
        ids = get_album_track_ids(sp, "album1")
        self.assertEqual(ids, ["t1", "t2"])


class TestGetCurrentUserId(unittest.TestCase):
    def test_returns_user_id(self):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser", "display_name": "Test"}
        self.assertEqual(get_current_user_id(sp), "testuser")

    def test_raises_on_missing_id(self):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        sp.current_user.return_value = {}
        with self.assertRaises(ValueError):
            get_current_user_id(sp)


class TestCreatePlaylist(unittest.TestCase):
    def test_creates_and_returns(self):
        from spotify_client import create_playlist

        sp = MagicMock()
        sp.user_playlist_create.return_value = make_playlist("new_id", "Test")
        result = create_playlist(sp, "user1", "Test")
        self.assertEqual(result["id"], "new_id")

    def test_raises_on_bad_response(self):
        from spotify_client import create_playlist

        sp = MagicMock()
        sp.user_playlist_create.return_value = {}
        with self.assertRaises(ValueError):
            create_playlist(sp, "user1", "Test")


# ---------------------------------------------------------------------------
# Tests for retry logic
# ---------------------------------------------------------------------------

class TestRetryOnTransient(unittest.TestCase):
    @patch("spotify_client.time.sleep")
    def test_retries_on_rate_limit(self, mock_sleep):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        rate_limit_exc = spotipy.SpotifyException(429, -1, "rate limited")
        rate_limit_exc.headers = {"Retry-After": "1"}
        sp.current_user.side_effect = [
            rate_limit_exc,
            {"id": "testuser"},
        ]
        result = get_current_user_id(sp)
        self.assertEqual(result, "testuser")
        self.assertEqual(sp.current_user.call_count, 2)

    @patch("spotify_client.time.sleep")
    def test_retries_on_server_error(self, mock_sleep):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        server_exc = spotipy.SpotifyException(500, -1, "server error")
        server_exc.headers = {}
        sp.current_user.side_effect = [
            server_exc,
            {"id": "testuser"},
        ]
        result = get_current_user_id(sp)
        self.assertEqual(result, "testuser")

    @patch("spotify_client.time.sleep")
    def test_retries_on_connection_error(self, mock_sleep):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        sp.current_user.side_effect = [
            requests.ConnectionError("connection refused"),
            {"id": "testuser"},
        ]
        result = get_current_user_id(sp)
        self.assertEqual(result, "testuser")

    def test_does_not_retry_on_client_error(self):
        from spotify_client import get_current_user_id

        sp = MagicMock()
        client_exc = spotipy.SpotifyException(404, -1, "not found")
        client_exc.headers = {}
        sp.current_user.side_effect = client_exc
        with self.assertRaises(spotipy.SpotifyException):
            get_current_user_id(sp)
        # Should fail immediately, no retries
        self.assertEqual(sp.current_user.call_count, 1)


# ---------------------------------------------------------------------------
# Tests for error paths in scripts
# ---------------------------------------------------------------------------

class TestScript1ErrorPaths(unittest.TestCase):
    @patch("script1_discover_release.get_spotify_client")
    def test_missing_playlist_exits(self, mock_client):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser"}
        sp.current_user_playlists.return_value = paged([
            make_playlist("p1", "Some Other Playlist"),
        ])
        mock_client.return_value = sp

        import script1_discover_release as s1
        with self.assertRaises(SystemExit):
            s1.run(mode="discover")


class TestScript2ErrorPaths(unittest.TestCase):
    @patch("script2_daylist_saver.get_spotify_client")
    def test_empty_daylist_exits(self, mock_client):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser"}
        sp.current_user_playlists.return_value = paged([
            make_playlist("dl_id", "daylist - morning vibes"),
        ])
        sp.playlist_tracks.return_value = paged([])
        mock_client.return_value = sp

        import script2_daylist_saver as s2
        with self.assertRaises(SystemExit):
            s2.run(mode="tracks")


# ---------------------------------------------------------------------------
# Integration-style tests for script1 and script2 (mocked API)
# ---------------------------------------------------------------------------

class TestScript1Run(unittest.TestCase):
    def _make_sp(self):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser"}

        discover_playlist = make_playlist("dw_id", "Discover Weekly")
        release_playlist = make_playlist("rr_id", "Release Radar")

        def current_user_playlists(**kwargs):
            return paged([discover_playlist, release_playlist])

        sp.current_user_playlists.side_effect = current_user_playlists

        sp.playlist_tracks.side_effect = lambda pid, **kw: paged(
            [
                {"track": make_track("t1", "a1")},
                {"track": make_track("t2", "a2")},
            ]
        )
        sp.album_tracks.return_value = paged([{"id": "t1"}, {"id": "t2"}])
        sp.user_playlist_create.return_value = make_playlist("new_id", "Test")
        return sp

    @patch("script1_discover_release.get_spotify_client")
    def test_combined_creates_playlist(self, mock_client):
        mock_client.return_value = self._make_sp()
        import script1_discover_release as s1
        s1.run(mode="combined")
        sp = mock_client.return_value
        sp.user_playlist_create.assert_called_once()
        args = sp.user_playlist_create.call_args
        self.assertIn("Discover + Release Albums", args[1]["name"])

    @patch("script1_discover_release.get_spotify_client")
    def test_discover_mode(self, mock_client):
        mock_client.return_value = self._make_sp()
        import script1_discover_release as s1
        s1.run(mode="discover")
        sp = mock_client.return_value
        args = sp.user_playlist_create.call_args
        self.assertIn("Discover Weekly Albums", args[1]["name"])

    @patch("script1_discover_release.get_spotify_client")
    def test_release_mode(self, mock_client):
        mock_client.return_value = self._make_sp()
        import script1_discover_release as s1
        s1.run(mode="release")
        sp = mock_client.return_value
        args = sp.user_playlist_create.call_args
        self.assertIn("Release Radar Albums", args[1]["name"])

    @patch("script1_discover_release.get_spotify_client")
    def test_invalid_mode_exits(self, mock_client):
        import script1_discover_release as s1
        with self.assertRaises(SystemExit):
            s1.run(mode="invalid")


class TestScript2Run(unittest.TestCase):
    def _make_sp(self, daylist_title="daylist - morning vibes - monday"):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser"}

        daylist = make_playlist("dl_id", daylist_title, description="chill morning beats")

        sp.current_user_playlists.return_value = paged([daylist])
        sp.playlist_tracks.return_value = paged(
            [{"track": make_track("t1", "a1")}, {"track": make_track("t2", "a2")}]
        )
        sp.album_tracks.return_value = paged([{"id": "t1"}, {"id": "t2"}])
        sp.user_playlist_create.return_value = make_playlist("new_id", "Test")
        return sp

    @patch("script2_daylist_saver.get_spotify_client")
    def test_tracks_mode_creates_playlist(self, mock_client):
        mock_client.return_value = self._make_sp()
        import script2_daylist_saver as s2
        s2.run(mode="tracks")
        sp = mock_client.return_value
        sp.user_playlist_create.assert_called_once()
        args = sp.user_playlist_create.call_args
        self.assertIn("daylist", args[1]["name"].lower())

    @patch("script2_daylist_saver.get_spotify_client")
    def test_albums_mode_expands_albums(self, mock_client):
        mock_client.return_value = self._make_sp()
        import script2_daylist_saver as s2
        s2.run(mode="albums")
        sp = mock_client.return_value
        self.assertGreater(sp.album_tracks.call_count, 0)
        args = sp.user_playlist_create.call_args
        self.assertIn("Albums", args[1]["name"])

    @patch("script2_daylist_saver.get_spotify_client")
    def test_daylist_not_found_exits(self, mock_client):
        sp = MagicMock()
        sp.current_user.return_value = {"id": "testuser"}
        sp.current_user_playlists.return_value = paged([make_playlist("p1", "Some Other Playlist")])
        mock_client.return_value = sp

        import script2_daylist_saver as s2
        with self.assertRaises(SystemExit):
            s2.run(mode="tracks")

    @patch("script2_daylist_saver.get_spotify_client")
    def test_invalid_mode_exits(self, mock_client):
        import script2_daylist_saver as s2
        with self.assertRaises(SystemExit):
            s2.run(mode="badmode")


if __name__ == "__main__":
    unittest.main()
