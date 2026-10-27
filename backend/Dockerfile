# One "box" with everything the app needs: Python, libraries, LaTeX, the embedding model, our code.
# The same image runs on your PC and on the server.
#
#   docker build -t resume-tailor .
#   docker compose up            (app + PostgreSQL, see docker-compose.yml)

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app \
    FASTEMBED_CACHE_PATH=/opt/models \
    ENVIRONMENT=prod

# 1. LaTeX, only the parts our template uses (for PDF downloads)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 2. Python libraries. Copied BEFORE our code, so Docker reuses this slow layer
#    when only our code changes.
COPY pyproject.toml .
RUN python -c "import tomllib; print('\n'.join(tomllib.load(open('pyproject.toml','rb'))['project']['dependencies']))" \
        > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

# 3. Download the embedding model now, so the server never downloads it at runtime
RUN python -c "from fastembed import TextEmbedding; TextEmbedding('BAAI/bge-small-en-v1.5')"

# 4. Our code
COPY core ./core
COPY api ./api
COPY templates ./templates
COPY migrations ./migrations
COPY alembic.ini .

# 5. Never run as root: if someone breaks in, they get a powerless user
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /app/storage && chown -R app /app/storage /opt/models
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

# Update the database tables, then start the server.
# 1 worker: background jobs and the login rate limit live in this one process.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn api.main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
