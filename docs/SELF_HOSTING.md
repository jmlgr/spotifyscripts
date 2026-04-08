# Self-Hosting Guide

## Requirements

- Docker 24+ and Docker Compose v2
- A machine with at least 512MB free RAM
- A Spotify Developer app with a registered redirect URI

## Initial Setup

### 1. Clone the repo

```bash
git clone https://github.com/jmlgr/spotifyscripts.git
cd spotifyscripts
```

### 2. Create your `.env` file

```bash
cp .env.example .env
```

Open `.env` and fill in all four values before proceeding.

### 3. Create a Spotify app

1. Go to [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard)
2. Click "Create app"
3. Fill in any name and description
4. Set "Redirect URIs" to exactly: `http://127.0.0.1:3000/api/auth/callback`
5. Save, then copy the **Client ID** and **Client Secret** into your `.env`

### 4. Generate a session secret

```bash
openssl rand -hex 32
```

Paste the output as `SESSION_SECRET` in your `.env`.

### 5. Start the app

```bash
docker compose up -d
```

Open [http://127.0.0.1:3000](http://127.0.0.1:3000) and sign in with Spotify.

## Updating

Pull the latest image and restart:

```bash
docker compose pull
docker compose up -d
```

## LAN Access

To reach the app from phones or other machines on your network:

1. Find your host machine's local IP:
   ```bash
   # macOS
   ipconfig getifaddr en0
   # Linux
   hostname -I | awk '{print $1}'
   ```

2. Edit `.env`:
   ```
   SPOTIFY_REDIRECT_URI=http://192.168.1.100:3000/api/auth/callback
   ```
   Replace `192.168.1.100` with your actual IP.

3. Add that same URI to your Spotify app's Redirect URIs in the Developer Dashboard.

4. Restart:
   ```bash
   docker compose restart
   ```

5. Access the app at `http://192.168.1.100:3000` from any device on your network.

## Running Behind a Reverse Proxy (nginx)

If you want HTTPS or a custom domain, put nginx in front:

**nginx config (`/etc/nginx/sites-available/spotify`):**

```nginx
server {
    listen 80;
    server_name spotifyscripts.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name spotifyscripts.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/spotify.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/spotify.yourdomain.com/privkey.pem;

    location / {
        proxy_pass         http://127.0.0.1:3000;
        proxy_http_version 1.1;
        proxy_set_header   Upgrade $http_upgrade;
        proxy_set_header   Connection 'upgrade';
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
    }
}
```

Then update your `.env` and Spotify app's redirect URI to use `https://spotifyscripts.yourdomain.com/api/auth/callback`.

## Environment Variable Reference

| Variable | Required | Description |
|---|---|---|
| `SPOTIFY_CLIENT_ID` | Yes | Client ID from Spotify Developer Dashboard |
| `SPOTIFY_CLIENT_SECRET` | Yes | Client Secret from Spotify Developer Dashboard |
| `SPOTIFY_REDIRECT_URI` | Yes | Must match exactly what is set in the Spotify app |
| `SESSION_SECRET` | Yes | 64-character hex string for encrypting sessions |

## Troubleshooting

### "INVALID_CLIENT: Invalid redirect URI"

The redirect URI in your `.env` must match the one registered in the Spotify Developer Dashboard character for character, including the protocol (`http` vs `https`) and port.

Common mistakes:
- Using `localhost` instead of `127.0.0.1`
- Missing the trailing path `/api/auth/callback`
- Port mismatch (e.g., `:3000` vs `:3001`)

### Personalized playlists (Discover Weekly, daylist) are empty or missing

Personalized playlists require an internal token from the Spotify web player. Go to Settings in the app and follow the instructions to add your token. The token lasts about 2 hours and needs to be refreshed manually when it expires.

### "Session expired" or constant redirects to login

Your `SESSION_SECRET` may have changed between container restarts, invalidating all existing sessions. Set a stable value in `.env` rather than generating a new one each time.

### Port 3000 already in use

Change the host port in `docker-compose.yml`:

```yaml
ports:
  - "3001:3000"   # Use 3001 on the host
```

Then update `SPOTIFY_REDIRECT_URI` to use port `3001` as well.

### Container crashes on startup

Check logs:

```bash
docker compose logs spotify-tools
```

The most common causes are missing environment variables or an invalid `SESSION_SECRET` (must be a hex string, not arbitrary text).

### Checking container status

```bash
docker compose ps
docker compose logs -f spotify-tools
```
