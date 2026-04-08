# Advanced Spotify Playlist Tools

Playlist tools Spotify doesn't offer. Sort, export, deduplicate, compare, and expand your playlists. Access personalized playlists like Discover Weekly, daylist, and Daily Mixes.

## Try It

**Hosted version (near-instant):** [spotifyscripts-web.vercel.app](https://spotifyscripts-web.vercel.app)

> **Important:** The hosted version uses a shared Spotify Developer app that hasn't been submitted for Spotify's extended quota review. This means "Sign in with Spotify" may not work for your account unless you've been added as a tester. For the best experience, use **Bring Your Own Key (BYOK)**: enter your own Spotify Developer app credentials on the welcome screen before signing in. This takes about 2 minutes and works immediately.
>
> We don't track anything, collect data, or store anything beyond your encrypted session cookie. See the [Privacy Policy](https://spotifyscripts-web.vercel.app/privacy).

**Self-host with Docker (recommended):** See [setup instructions](#self-host-setup) below. Uses your own Spotify app credentials. Full control.

## Features

**Playlist Management**
- Expand any playlist to full albums
- Sort by popularity, release date, artist, date added, album, or track name (album track order preserved)
- Find and remove duplicate tracks (within or across playlists, with undo)
- Compare playlists with set operations (unique, shared, union, difference)
- Export playlists as CSV or JSON backup (includes owner info)

**Personalized Content**
- Access Discover Weekly, Release Radar, daylist, Daily Mixes, Blends, and all "Made for You" playlists
- Snapshot daylist before it changes (preserves the title and description)
- Accurate track counts for personalized playlists

**Artist Explorer**
- Search any artist and rank albums by popularity or release date
- Build custom collection playlists from selected albums
- Deduplicate tracks across albums (prefer first appearance, remastered, or latest version)

**Discovery**
- Browse library organized by Spotify's folder structure
- Liked Songs browser with shuffle, random load, and playlist creation

**How it works:** Uses Spotify's standard Web API for most features. For personalized playlists (which Spotify blocked from the public API in Nov 2024), uses an optional internal token from the Spotify web player. The app walks you through this in Settings.

## Self-Host Setup

### Prerequisites
- Docker and Docker Compose
- A Spotify Developer app ([create one here](https://developer.spotify.com/dashboard))

### Setup

1. Clone this repo:
   ```bash
   git clone https://github.com/jmlgr/spotifyscripts.git
   cd spotifyscripts
   ```

2. Create your `.env` file:
   ```bash
   cp .env.example .env
   ```

3. Configure your Spotify app:
   - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
   - Create a new app (any name/description)
   - Set **Redirect URI** to: `http://127.0.0.1:3000/api/auth/callback`
   - Copy **Client ID** and **Client Secret** into your `.env`
   - **Important:** Use `127.0.0.1`, not `localhost` (Spotify requires IP format)

4. Generate a session secret:
   ```bash
   openssl rand -hex 32
   ```
   Paste into `SESSION_SECRET` in your `.env`

5. Start the app:
   ```bash
   docker compose up -d
   ```

6. Open [http://127.0.0.1:3000](http://127.0.0.1:3000)

### Custom Domain

If self-hosting on a server, we recommend the subdomain `spotifyscripts`. Example: `spotifyscripts.yourdomain.com`. See [docs/SELF_HOSTING.md](docs/SELF_HOSTING.md) for nginx reverse proxy configuration.

### LAN Access (phone, other devices)

1. Find your machine's IP (e.g., `192.168.1.100`)
2. Update `.env`: `SPOTIFY_REDIRECT_URI=http://192.168.1.100:3000/api/auth/callback`
3. Add the same URI to your Spotify app's Redirect URIs
4. Restart: `docker compose restart`

### Spotify App User Limits

Spotify apps in Development Mode allow up to 25 users. Add testers by email in your app's Settings > User Management on the Developer Dashboard. To allow unlimited users, submit a quota extension request to Spotify.

## Updating

```bash
docker compose pull
docker compose up -d
```

## Contributing

The standard Spotify Web API helpers are open source in [`lib/`](lib/). These handle authentication, rate-limited fetching, playlist operations, and input validation. Contributions, bug reports, and feature ideas are welcome.

The personalized playlist access layer (used for Discover Weekly, daylist, etc.) is proprietary and distributed only in the pre-built Docker image.

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for how the app is structured.

## Questions

Open an [issue](https://github.com/jmlgr/spotifyscripts/issues) or reach out if you have questions about setup, BYOK configuration, or contributing.

## Privacy

See [Privacy Policy](https://spotifyscripts-web.vercel.app/privacy). No data is stored beyond your encrypted session cookie. No tracking, no analytics. You can revoke access anytime at [spotify.com/account/apps](https://www.spotify.com/account/apps/).

## License

Open-source components (including [`lib/`](lib/)) are licensed under [AGPL v3](LICENSE). Proprietary components (distributed only in pre-built Docker images) are covered by a [separate license](PROPRIETARY_LICENSE).
