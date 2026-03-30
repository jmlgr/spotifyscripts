#!/usr/bin/env python3
"""
Setup Script – Spotify Scripts Configuration Wizard

Walks the user through:
  1. Registering a Spotify Developer application (or using an existing one).
  2. Entering their Client ID, Client Secret, and Redirect URI.
  3. Performing an OAuth sign-in to confirm credentials work.
  4. Writing the configuration to a .env file for use by the other scripts.

Supports both local execution and Docker container environments.
"""

import os
import sys
import webbrowser

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(BASE_DIR, ".env")
ENV_EXAMPLE = os.path.join(BASE_DIR, ".env.example")

BANNER = r"""
╔══════════════════════════════════════════════╗
║          Spotify Scripts – Setup             ║
╚══════════════════════════════════════════════╝
"""

DASHBOARD_URL = "https://developer.spotify.com/dashboard"


def print_step(step: int, title: str) -> None:
    print(f"\n── Step {step}: {title} ──")


def ask(prompt: str, default: str = "") -> str:
    """Prompt the user for input, optionally showing a default value."""
    if default:
        display = f"{prompt} [{default}]: "
    else:
        display = f"{prompt}: "
    value = input(display).strip()
    return value or default


def detect_docker() -> bool:
    """Return True when running inside a Docker container."""
    return os.path.exists("/.dockerenv") or os.getenv("RUNNING_IN_DOCKER") == "1"


def main() -> None:
    print(BANNER)
    print("This wizard will help you configure the Spotify Scripts.")
    print("You will need a Spotify Developer account and an application.\n")

    in_docker = detect_docker()

    # ── Step 1: Create / locate Spotify app ──────────────────────────────────
    print_step(1, "Spotify Developer Application")
    print(f"  Open the Spotify Developer Dashboard: {DASHBOARD_URL}")
    print("  - Click 'Create app'")
    print("  - Give it a name, e.g. 'My Spotify Scripts'")
    print("  - Set the Redirect URI to: http://localhost:8888/callback")
    print("    (You can change this later – just keep it consistent.)")

    if not in_docker:
        open_browser = ask(
            "  Open the dashboard in your browser now? (y/n)", default="y"
        )
        if open_browser.lower() == "y":
            webbrowser.open(DASHBOARD_URL)

    input("\n  Press Enter once you have your app's Client ID and Secret ready…")

    # ── Step 2: Enter credentials ─────────────────────────────────────────────
    print_step(2, "Enter Your Credentials")

    existing_id = os.getenv("SPOTIPY_CLIENT_ID", "")
    existing_secret = os.getenv("SPOTIPY_CLIENT_SECRET", "")
    existing_uri = os.getenv("SPOTIPY_REDIRECT_URI", "http://localhost:8888/callback")

    client_id = ask("  Client ID", default=existing_id)
    client_secret = ask("  Client Secret", default=existing_secret)
    redirect_uri = ask("  Redirect URI", default=existing_uri)

    if not client_id or not client_secret:
        print(
            "\nERROR: Client ID and Client Secret are required. Exiting.",
            file=sys.stderr,
        )
        sys.exit(1)

    # ── Step 3: Test authentication ───────────────────────────────────────────
    print_step(3, "Sign in with Spotify")

    # Set env vars before importing the client (so it picks them up)
    os.environ["SPOTIPY_CLIENT_ID"] = client_id
    os.environ["SPOTIPY_CLIENT_SECRET"] = client_secret
    os.environ["SPOTIPY_REDIRECT_URI"] = redirect_uri

    if in_docker:
        print(
            "  Running in Docker – the sign-in URL will be printed below.\n"
            "  Open it in your browser, approve the request, then paste the\n"
            "  resulting URL (which starts with the Redirect URI) back here."
        )
    else:
        print("  Your browser will open for Spotify sign-in.")
        print("  Approve the request and you will be redirected back.")

    try:
        # Imported here (after env vars are set) so SpotifyOAuth picks up
        # the credentials we just placed in os.environ.
        import spotipy  # noqa: PLC0415
        from spotipy.oauth2 import SpotifyOAuth  # noqa: PLC0415

        auth_manager = SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope="user-read-private",
            cache_path=os.path.join(BASE_DIR, ".cache"),
            open_browser=not in_docker,
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        user = sp.current_user()
        display_name = user.get("display_name") or user.get("id", "Unknown")
        username = user.get("id", "")
        print(f"\n  ✓ Signed in successfully as: {display_name} ({username})")
    except Exception as exc:
        print(f"\n  ✗ Authentication failed: {exc}", file=sys.stderr)
        print("  Please check your credentials and try again.", file=sys.stderr)
        sys.exit(1)

    # ── Step 4: Write .env file ───────────────────────────────────────────────
    print_step(4, "Save Configuration")

    env_lines = [
        "# Spotify API credentials\n",
        f"SPOTIPY_CLIENT_ID={client_id}\n",
        f"SPOTIPY_CLIENT_SECRET={client_secret}\n",
        f"SPOTIPY_REDIRECT_URI={redirect_uri}\n",
        f"SPOTIFY_USERNAME={username}\n",
    ]

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(env_lines)

    print(f"  ✓ Configuration saved to {ENV_FILE}")

    # ── Done ──────────────────────────────────────────────────────────────────
    print(
        "\n╔══════════════════════════════════════════════╗\n"
        "║  Setup complete! You can now run:            ║\n"
        "║    python script1_discover_release.py        ║\n"
        "║    python script2_daylist_saver.py           ║\n"
        "╚══════════════════════════════════════════════╝"
    )


if __name__ == "__main__":
    main()
