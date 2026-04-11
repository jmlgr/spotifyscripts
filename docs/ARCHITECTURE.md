# Architecture Overview

## Stack

| Layer | Technology |
|---|---|
| Framework | Next.js 16 (App Router) |
| UI | React 19, Tailwind CSS 4 |
| Session management | iron-session (encrypted, cookie-based) |
| Runtime | Node.js 20 (Docker) or Vercel (hosted) |
| Distribution | GitHub Container Registry (GHCR) |

## Authentication

The app uses **iron-session** to store encrypted session data in an HTTP-only cookie. No session data is persisted server-side.

### Dual-Token Architecture

1. **OAuth token** - Standard Spotify Authorization Code flow. Used for all Web API calls: reading playlists, creating playlists, modifying library, searching. Refreshes automatically when near expiration.

2. **Internal token (optional)** - Enables access to personalized playlists (Discover Weekly, Release Radar, daylist, Daily Mixes) that Spotify removed from the public API in November 2024. This token is derived from the session cookie that Spotify already places in your browser when you log in to the web player. The app uses this to make requests on your behalf using your existing browser authentication. It has a 2-hour TTL and cannot be refreshed programmatically.

Both tokens are stored encrypted in the session cookie. The client never sees either token directly.

## API Route Structure

All server-side logic lives in Next.js API routes under `src/app/api/`:

```
api/
  auth/
    login/          # Initiates OAuth flow
    callback/       # Handles OAuth redirect
    logout/         # Clears session
    me/             # Current user info
    internal-token/ # Internal token management
    token-status/   # Token TTL check
  playlists/
    create/         # Create playlists (expand, merge)
    discover/       # Library browser (owned, saved, personalized)
    daylist/        # Daylist view, snapshot, merge
    duplicates/     # Find and remove duplicates
    sort/           # Sort playlist tracks
    export/         # CSV/JSON export
    diff/           # Playlist comparison
    liked/          # Liked songs browser
    recommendations/ # Radio/recommendations
    tracks/         # Track details
    search/         # Playlist search
    rootlist/       # Folder structure
  artists/
    popularity/     # Album ranking, collection builder
  player/
    queue/          # Queue shuffle
```

## Component Architecture

### AppShell
Top-level layout. Renders sidebar navigation, manages active view state, handles auth context.

### Views
Each feature is a self-contained view under `src/components/views/`. Views fetch their own data via API calls and manage local state. Examples: `DashboardView`, `DaylistView`, `ArtistPopularityView`, `DiffView`.

### Contexts
`src/contexts/AppContext.tsx` provides auth state, library data, and shared handlers (login, logout, internal token management) to the component tree.

## Open Source Components

The [`lib/`](../lib/) directory in this repo contains the standard Spotify Web API helpers:

- **spotify-fetch.ts** - Fetch wrapper with automatic 429 rate-limit retry
- **spotify-api.ts** - Web API client (auth, playlists, tracks, search, artists)
- **validate.ts** - Input validation for Spotify IDs, sort fields, etc.
- **session.ts** - iron-session configuration and token refresh pattern

These are the same files used in the app. Contributions are welcome.

## Docker Image

The pre-built image at `ghcr.io/jmlgr/spotifyscripts:latest` runs `node server.js` (Next.js standalone output) on port 3000. All configuration is injected at runtime via environment variables. The image contains no credentials.

The image includes both the open-source API helpers and the proprietary personalized playlist layer. Source for the proprietary layer is not distributed.
