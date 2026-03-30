FROM python:3.12-slim

LABEL description="Spotify Scripts – interact with Spotify on behalf of a single user"

# Working directory inside the container
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source files
COPY spotify_client.py setup.py \
     script1_discover_release.py \
     script2_daylist_saver.py \
     ./

# Mount point for the .env file and the OAuth token cache
VOLUME ["/app"]

# Signal Docker environment so setup.py adjusts its behaviour
ENV RUNNING_IN_DOCKER=1

# Default: show help. Override CMD when running a specific script.
CMD ["python", "-c", "\
import textwrap; \
print(textwrap.dedent('''\n\
  Spotify Scripts Container\n\
  ─────────────────────────\n\
  Mount your working directory and run one of:\n\n\
    docker run -it -v \"$(pwd):/app\" spotify-scripts python setup.py\n\
    docker run -it -v \"$(pwd):/app\" spotify-scripts python script1_discover_release.py --mode combined\n\
    docker run -it -v \"$(pwd):/app\" spotify-scripts python script2_daylist_saver.py --mode tracks\n\
'''))"]
