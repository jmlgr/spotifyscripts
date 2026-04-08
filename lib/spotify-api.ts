/**
 * Spotify Web API client.
 *
 * Handles OAuth authentication, token refresh, and standard playlist operations.
 * This file uses only Spotify's public Web API. No internal/undocumented endpoints.
 */

import { spotifyFetch } from "./spotify-fetch";

const SPOTIFY_API = "https://api.spotify.com/v1";
const SPOTIFY_ACCOUNTS = "https://accounts.spotify.com";

export const SCOPES = [
  "playlist-read-private",
  "playlist-read-collaborative",
  "playlist-modify-public",
  "playlist-modify-private",
  "user-read-private",
  "user-library-read",
  "user-read-playback-state",
  "user-modify-playback-state",
  "user-top-read",
].join(" ");

// -- OAuth --

export function getAuthUrl(state: string, clientId?: string): string {
  const params = new URLSearchParams({
    response_type: "code",
    client_id: clientId || process.env.SPOTIFY_CLIENT_ID!,
    scope: SCOPES,
    redirect_uri: process.env.SPOTIFY_REDIRECT_URI!,
    state,
  });
  return `${SPOTIFY_ACCOUNTS}/authorize?${params}`;
}

export async function exchangeCode(
  code: string,
  credentials?: { clientId: string; clientSecret: string }
): Promise<{ access_token: string; refresh_token: string; expires_at: number }> {
  const clientId = credentials?.clientId || process.env.SPOTIFY_CLIENT_ID!;
  const clientSecret = credentials?.clientSecret || process.env.SPOTIFY_CLIENT_SECRET!;
  const res = await fetch(`${SPOTIFY_ACCOUNTS}/api/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString("base64")}`,
    },
    body: new URLSearchParams({
      grant_type: "authorization_code",
      code,
      redirect_uri: process.env.SPOTIFY_REDIRECT_URI!,
    }),
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Token exchange failed: ${text}`);
  }

  const data = await res.json();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token,
    expires_at: Date.now() + data.expires_in * 1000,
  };
}

export async function refreshAccessToken(
  refreshToken: string,
  credentials?: { clientId: string; clientSecret: string }
): Promise<{ access_token: string; refresh_token: string; expires_at: number }> {
  const clientId = credentials?.clientId || process.env.SPOTIFY_CLIENT_ID!;
  const clientSecret = credentials?.clientSecret || process.env.SPOTIFY_CLIENT_SECRET!;
  const res = await fetch(`${SPOTIFY_ACCOUNTS}/api/token`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      Authorization: `Basic ${Buffer.from(`${clientId}:${clientSecret}`).toString("base64")}`,
    },
    body: new URLSearchParams({ grant_type: "refresh_token", refresh_token: refreshToken }),
  });

  if (!res.ok) throw new Error("Token refresh failed");

  const data = await res.json();
  return {
    access_token: data.access_token,
    refresh_token: data.refresh_token ?? refreshToken,
    expires_at: Date.now() + data.expires_in * 1000,
  };
}

// -- Internal fetch helper (throws on error) --

function apiFetch(accessToken: string, path: string, options?: RequestInit): Promise<Response> {
  return spotifyFetch(accessToken, path, { ...options, throwOnError: true });
}

// -- User --

export async function getCurrentUserId(accessToken: string): Promise<string> {
  const res = await apiFetch(accessToken, "/me");
  return (await res.json()).id;
}

export async function getCurrentUserName(accessToken: string): Promise<string> {
  const res = await apiFetch(accessToken, "/me");
  const data = await res.json();
  return data.display_name || data.id;
}

// -- Playlist read operations --

interface SpotifyPlaylist {
  id: string;
  name: string;
  description?: string;
  external_urls?: { spotify?: string };
  owner?: { id: string };
}

interface SpotifyTrack {
  id: string;
  name: string;
  album: { id: string; name: string };
}

export async function getPlaylistById(
  accessToken: string,
  playlistId: string
): Promise<SpotifyPlaylist | null> {
  try {
    const res = await apiFetch(accessToken, `/playlists/${playlistId}?fields=id,name,description,external_urls`);
    return res.json();
  } catch {
    return null;
  }
}

export function extractPlaylistId(urlOrId: string): string {
  const match = urlOrId.match(/playlist\/([a-zA-Z0-9]+)/);
  return match ? match[1] : urlOrId;
}

export async function getAllPlaylistTracks(
  accessToken: string,
  playlistId: string
): Promise<SpotifyTrack[]> {
  const tracks: SpotifyTrack[] = [];
  let nextUrl: string | null = `/playlists/${playlistId}/tracks`;

  while (nextUrl) {
    const fullUrl = nextUrl.startsWith("http") ? nextUrl : `${SPOTIFY_API}${nextUrl}`;
    const res = await fetch(fullUrl, {
      headers: { Authorization: `Bearer ${accessToken}` },
    });
    if (!res.ok) break;

    const data = await res.json();
    for (const item of data.items ?? []) {
      if (item.track?.id) tracks.push(item.track);
    }
    nextUrl = data.next;
  }

  return tracks;
}

export function getUniqueAlbums(tracks: SpotifyTrack[]): { id: string; name: string }[] {
  const seen = new Set<string>();
  const albums: { id: string; name: string }[] = [];
  for (const track of tracks) {
    if (track.album?.id && !seen.has(track.album.id)) {
      seen.add(track.album.id);
      albums.push({ id: track.album.id, name: track.album.name });
    }
  }
  return albums;
}

export async function getAlbumTrackIds(accessToken: string, albumId: string): Promise<string[]> {
  const ids: string[] = [];
  let nextUrl: string | null = `/albums/${albumId}/tracks?limit=50`;
  while (nextUrl) {
    const fullUrl = nextUrl.startsWith("http") ? nextUrl : `${SPOTIFY_API}${nextUrl}`;
    const res = await fetch(fullUrl, { headers: { Authorization: `Bearer ${accessToken}` } });
    if (!res.ok) break;
    const data = await res.json();
    for (const item of data.items ?? []) {
      if (item.id) ids.push(item.id);
    }
    nextUrl = data.next;
  }
  return ids;
}

// -- Playlist write operations --

export async function createPlaylist(
  accessToken: string,
  userId: string,
  name: string,
  description: string = "",
  isPublic: boolean = false
): Promise<SpotifyPlaylist> {
  const res = await apiFetch(accessToken, `/users/${userId}/playlists`, {
    method: "POST",
    body: JSON.stringify({ name, description, public: isPublic }),
  });
  return res.json();
}

export async function addTracksToPlaylist(
  accessToken: string,
  playlistId: string,
  trackIds: string[]
): Promise<void> {
  const batchSize = 100;
  for (let i = 0; i < trackIds.length; i += batchSize) {
    const batch = trackIds.slice(i, i + batchSize);
    await apiFetch(accessToken, `/playlists/${playlistId}/tracks`, {
      method: "POST",
      body: JSON.stringify({ uris: batch.map((id) => `spotify:track:${id}`) }),
    });
  }
}

export async function replacePlaylistTracks(
  accessToken: string,
  playlistId: string,
  trackIds: string[]
): Promise<void> {
  const first = trackIds.slice(0, 100);
  await apiFetch(accessToken, `/playlists/${playlistId}/tracks`, {
    method: "PUT",
    body: JSON.stringify({ uris: first.map((id) => `spotify:track:${id}`) }),
  });
  for (let i = 100; i < trackIds.length; i += 100) {
    const batch = trackIds.slice(i, i + 100);
    await apiFetch(accessToken, `/playlists/${playlistId}/tracks`, {
      method: "POST",
      body: JSON.stringify({ uris: batch.map((id) => `spotify:track:${id}`) }),
    });
  }
}
