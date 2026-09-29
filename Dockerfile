# Container image for the pipeline.
#   Build:  docker compose build pipeline
#   Run:    docker compose run --rm pipeline

# "slim" = Debian with only the essentials: ~150 MB instead of ~1 GB for the full image.
FROM python:3.12-slim

# Don't write .pyc files; don't buffer stdout, so logs appear immediately in `docker logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Layer caching: Docker reuses a layer if its inputs haven't changed.
# Dependencies change rarely and code changes often, so install dependencies first,
# from pyproject.toml alone with an empty stub package. Code edits then rebuild in
# seconds instead of reinstalling every library.
COPY pyproject.toml ./
RUN mkdir -p src/market_pipeline && touch src/market_pipeline/__init__.py \
    && pip install . \
    && rm -rf src

COPY src ./src
RUN pip install --no-deps .

# Don't run as root: if the process is ever compromised, it can't take over the container.
RUN useradd --create-home --uid 1000 pipeline \
    && mkdir -p /data/raw && chown -R pipeline /data
USER pipeline

ENV RAW_DATA_DIR=/data/raw

# ENTRYPOINT is fixed; CMD is the default argument and can be overridden, e.g.
#   docker compose run --rm pipeline market_pipeline.load
ENTRYPOINT ["python", "-m"]
CMD ["market_pipeline.pipeline"]
