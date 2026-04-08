/**
 * Shared Spotify API fetch utility with automatic 429 rate-limit retry.
 * All API routes should use this instead of raw fetch() calls to Spotify.
 */

const SPOTIFY_API = "https://api.spotify.com/v1";

export interface SpotifyFetchOptions extends RequestInit {
  /** Maximum number of times to retry on a 429 rate-limit response (default 3). */
  maxRetries?: number;
  /** When true, non-2xx responses throw an error instead of being returned. */
  throwOnError?: boolean;
}

/**
 * Fetch a Spotify API endpoint with automatic retry on 429 rate-limit responses.
 *
 * @param accessToken - Bearer token for the Spotify Web API
 * @param path - Path relative to the API base (e.g. "/me/playlists") or a full URL
 * @param options - Standard RequestInit options plus optional maxRetries / throwOnError
 */
export async function spotifyFetch(
  accessToken: string,
  path: string,
  options?: SpotifyFetchOptions
): Promise<Response> {
  const maxRetries = options?.maxRetries ?? 3;
  const throwOnError = options?.throwOnError ?? false;
  const url = path.startsWith("http") ? path : `${SPOTIFY_API}${path}`;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    const res = await fetch(url, {
      ...options,
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
        ...options?.headers,
      },
    });

    if (res.status === 429) {
      const retryAfter = parseInt(res.headers.get("Retry-After") || "1", 10);
      await new Promise((r) => setTimeout(r, retryAfter * 1000));
      continue;
    }

    if (throwOnError && !res.ok) {
      const text = await res.text();
      throw new Error(`Spotify API error ${res.status}: ${text}`);
    }

    return res;
  }

  throw new Error("Max retries exceeded for Spotify API");
}
