# WHY Python 3.13-slim: Matches .python-version, slim reduces image size by ~800MB
FROM python:3.13-slim

# WHY: psycopg2-binary needs libpq-dev to connect to PostgreSQL
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl \
    && rm -rf /var/lib/apt/lists/*

# WHY uv: Fast dependency installation, matches local dev tooling
# WHY pinned: :latest means builds are non-reproducible if uv ships a breaking change
COPY --from=ghcr.io/astral-sh/uv:0.6 /uv /usr/local/bin/uv

WORKDIR /app

# WHY: Layer caching — dependencies change less often than app code
# WHY uv.lock included: enables --frozen for deterministic, reproducible installs
COPY pyproject.toml .python-version uv.lock ./
RUN uv sync --no-dev --frozen

# Copy application code
COPY . .

# WHY non-root: if the app is compromised, attacker doesn't have root in the container
RUN addgroup --system app && adduser --system --ingroup app app
USER app

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
    "--limit-request-line", "8190", \
    "--limit-request-fields", "100", \
    "--access-logfile", "-", \
    "--access-logformat", "{\"timestamp\":\"%(t)s\",\"remote_addr\":\"%(h)s\",\"method\":\"%(m)s\",\"path\":\"%(U)s\",\"query\":\"%(q)s\",\"status\":\"%(s)s\",\"response_length\":\"%(B)s\",\"duration_us\":\"%(D)s\",\"user_agent\":\"%(a)s\",\"request_id\":\"%({X-Request-ID}i)s\"}", \
    "--error-logfile", "-", \
    "run:app"]
