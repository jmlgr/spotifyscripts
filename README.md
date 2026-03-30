# spotifyscripts

A collection of Python scripts that interact with Spotify on behalf of a single
user via the Spotify Web API and OAuth "Sign in with Spotify".

Scripts can be run **locally** (plain Python) or inside a **Docker container**.

---

## Contents

| File | Description |
|---|---|
| `setup.py` | Interactive setup wizard – configure credentials & sign in |
| `script1_discover_release.py` | Discover Weekly + Release Radar Album Playlist Maker |
| `script2_daylist_saver.py` | Current Daylist Saver |
| `spotify_client.py` | Shared authentication & Spotify API helpers |
| `requirements.txt` | Python dependencies |
| `Dockerfile` | Container image definition |
| `docker-compose.yml` | Convenience compose services |
| `.env.example` | Template for your credentials |

---

## Prerequisites

- Python 3.12+ **or** Docker
- A [Spotify Developer](https://developer.spotify.com/dashboard) account with
  an app registered

---

## Quick Start (local)

### 1. Clone and install dependencies

```bash
git clone https://github.com/jmlgr/spotifyscripts.git
cd spotifyscripts
pip install -r requirements.txt
```

### 2. Run the setup wizard

```bash
python setup.py
```

The wizard will:

1. Guide you to the Spotify Developer Dashboard to create/locate your app.
2. Collect your **Client ID**, **Client Secret**, and **Redirect URI**.
3. Open your browser for OAuth sign-in to verify the credentials.
4. Write a `.env` file with your configuration.

> **Redirect URI**: Set `http://localhost:8888/callback` in your Spotify app's
> settings and accept the default in the wizard.

### 3. Run a script

```bash
# Script 1 – combined (Discover Weekly + Release Radar)
python script1_discover_release.py --mode combined

# Script 1 – Discover Weekly only
python script1_discover_release.py --mode discover

# Script 1 – Release Radar only
python script1_discover_release.py --mode release

# Script 2 – save daylist tracks as-is
python script2_daylist_saver.py --mode tracks

# Script 2 – save daylist as full albums
python script2_daylist_saver.py --mode albums
```

---

## Quick Start (Docker)

### Build the image

```bash
docker build -t spotify-scripts .
```

### Run the setup wizard

```bash
docker run -it -v "$(pwd):/app" spotify-scripts python setup.py
```

The wizard detects it is running in Docker and prints the authorization URL
instead of opening a browser.  Copy the URL, open it in your host browser,
approve the request, then paste the resulting redirect URL back into the
terminal.

### Run a script

```bash
docker run -it -v "$(pwd):/app" spotify-scripts \
  python script1_discover_release.py --mode combined

docker run -it -v "$(pwd):/app" spotify-scripts \
  python script2_daylist_saver.py --mode albums
```

### Using Docker Compose

```bash
docker compose run setup       # interactive setup wizard
docker compose run script1     # Discover + Release combined (default)
docker compose run script2     # Daylist saver – tracks mode (default)
```

To override the mode, append the arguments:

```bash
docker compose run script1 --mode discover
docker compose run script2 --mode albums
```

---

## Script Details

### Script 1 – Discover Weekly & Release Radar Album Playlist Maker

Reads the tracks from **Discover Weekly** and/or **Release Radar**, extracts
the unique albums in the order they appear, then creates a new private playlist
containing all the tracks from those albums.

| `--mode` | Playlist name |
|---|---|
| `combined` *(default)* | `Discover + Release Albums YYYY-MM-DD` |
| `discover` | `Discover Weekly Albums YYYY-MM-DD` |
| `release` | `Release Radar Albums YYYY-MM-DD` |

### Script 2 – Current Daylist Saver

Finds the Spotify **daylist** in your library and saves it as a new private
playlist.

| `--mode` | Behaviour |
|---|---|
| `tracks` *(default)* | Copies daylist tracks as-is; name mirrors the daylist title |
| `albums` | Expands each track to its full album; creates an album playlist |

---

## Configuration

Credentials are read from a `.env` file (written by `setup.py`) or from
environment variables:

| Variable | Description |
|---|---|
| `SPOTIPY_CLIENT_ID` | Your Spotify app's Client ID |
| `SPOTIPY_CLIENT_SECRET` | Your Spotify app's Client Secret |
| `SPOTIPY_REDIRECT_URI` | OAuth redirect URI (default: `http://localhost:8888/callback`) |
| `SPOTIFY_USERNAME` | *(optional)* Your Spotify username |

Copy `.env.example` to `.env` and fill in the values as an alternative to
running the setup wizard.

---

## Required Spotify Scopes

The scripts request the following OAuth scopes:

- `playlist-read-private`
- `playlist-read-collaborative`
- `playlist-modify-public`
- `playlist-modify-private`
- `user-read-private`
