# Spotify Web API Helpers

Open-source TypeScript utilities for working with Spotify's Web API. These are the same helpers used in the app.

## Files

| File | Purpose |
|------|---------|
| `spotify-api.ts` | OAuth flow, playlist CRUD, track operations, search |
| `spotify-fetch.ts` | Fetch wrapper with automatic 429 rate-limit retry |
| `validate.ts` | Input validation for Spotify IDs, sort fields, diff operations |
| `session.ts` | iron-session configuration and automatic token refresh |

## Usage

These files are designed for Next.js API routes but the core functions (`spotify-fetch.ts`, `spotify-api.ts`, `validate.ts`) work in any Node.js/TypeScript environment.

```typescript
import { spotifyFetch } from "./spotify-fetch";
import { createPlaylist, addTracksToPlaylist } from "./spotify-api";
import { isValidSpotifyId } from "./validate";
```

## What's NOT here

The personalized playlist access layer (Discover Weekly, daylist, Daily Mixes) is proprietary and not included in this repo. It's distributed only in the pre-built Docker image.

## Contributing

Bug fixes, improvements, and new standard API helpers are welcome. Please open a PR or issue.
