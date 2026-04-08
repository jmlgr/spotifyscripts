/**
 * Session management using iron-session.
 *
 * Stores all auth state in an encrypted HTTP-only cookie.
 * No server-side session storage needed.
 */

import { getIronSession, type SessionOptions } from "iron-session";
import { cookies } from "next/headers";

if (!process.env.SESSION_SECRET || process.env.SESSION_SECRET.length < 32) {
  throw new Error(
    "SESSION_SECRET environment variable must be at least 32 characters. Generate with: openssl rand -hex 32"
  );
}

export interface SessionData {
  accessToken?: string;
  refreshToken?: string;
  expiresAt?: number;
  userName?: string;
  customClientId?: string;
  customClientSecret?: string;
  oauthState?: string;
}

const sessionOptions: SessionOptions = {
  password: process.env.SESSION_SECRET!,
  cookieName: "spotify-session",
  cookieOptions: {
    secure: process.env.NODE_ENV === "production",
    httpOnly: true,
    sameSite: "lax",
  },
};

export async function getSession() {
  const cookieStore = await cookies();
  return getIronSession<SessionData>(cookieStore, sessionOptions);
}

/**
 * Returns a valid access token, refreshing if needed.
 * Returns null if no session exists.
 */
export async function getValidAccessToken(): Promise<string | null> {
  const session = await getSession();

  if (!session.accessToken || !session.refreshToken) {
    return null;
  }

  // Refresh if token expires within 5 minutes
  if (session.expiresAt && Date.now() > session.expiresAt - 5 * 60 * 1000) {
    try {
      // Import dynamically to avoid circular dependency
      const { refreshAccessToken } = await import("./spotify-api");
      const credentials = session.customClientId
        ? { clientId: session.customClientId, clientSecret: session.customClientSecret! }
        : undefined;
      const refreshed = await refreshAccessToken(session.refreshToken, credentials);
      session.accessToken = refreshed.access_token;
      session.refreshToken = refreshed.refresh_token;
      session.expiresAt = refreshed.expires_at;
      await session.save();
    } catch {
      session.destroy();
      return null;
    }
  }

  return session.accessToken;
}
