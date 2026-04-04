# WHY Python 3.13-slim: Matches .python-version, slim reduces image size by ~800MB
FROM python:3.13-slim

# WHY: psycopg2-binary needs libpq-dev to connect to PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# WHY uv: Fast dependency installation, matches local dev tooling
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# WHY: Layer caching — dependencies change less often than app code
COPY pyproject.toml .python-version ./
RUN uv sync --no-dev --frozen 2>/dev/null || uv sync --no-dev

# Copy application code
COPY . .

EXPOSE 5000

# WHY Gunicorn: Multi-worker WSGI server for concurrent request handling.
# Flask dev server is single-threaded — can't handle load testing.
# 4 workers = 2 * CPU cores + 1 (standard formula for I/O-bound apps).
# 30s timeout prevents slow requests from blocking workers.
# Reference: DECISIONS.md #5
CMD ["uv", "run", "gunicorn", \
    "--bind", "0.0.0.0:5000", \
    "--workers", "4", \
    "--timeout", "30", \
    "--access-logfile", "-", \
    "--error-logfile", "-", \
    "run:app"]
