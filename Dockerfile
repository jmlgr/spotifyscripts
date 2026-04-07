FROM python:3.12-slim

LABEL description="Spotify Scripts -- interact with Spotify on behalf of a single user"

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m appuser
USER appuser

# Copy source files
COPY spotify_client.py setup.py \
     script1_discover_release.py \
     script2_daylist_saver.py \
     ./

# Mount point for the .env file and the OAuth token cache
VOLUME ["/app"]

# Signal Docker environment so setup.py adjusts its behaviour
ENV RUNNING_IN_DOCKER=1

# Default: show usage info
CMD ["python", "-c", "print('Spotify Scripts Container\\n\\nRun one of:\\n  docker compose run setup\\n  docker compose run script1 --mode combined\\n  docker compose run script2 --mode tracks')"]
