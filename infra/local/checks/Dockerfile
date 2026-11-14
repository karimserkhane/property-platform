# Reproducible check runners for people and AI agents, matching the CI jobs.
# Dependencies are installed from the lockfiles at build time; the repository is
# mounted at /workspace at run time. See infra/local/compose.checks.yaml.
FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv

FROM python:3.14.10-slim-trixie@sha256:af8a5aa14780025dbfbcfbc81bd8a91ebd87711dd5b0f48ed71090949dd7cb1d AS python
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_SYSTEM_CERTS=true \
    UV_PROJECT_ENVIRONMENT=/opt/venv PATH=/opt/venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libgdal36 libgeos-c1t64 libproj25 \
    && rm -rf /var/lib/apt/lists/*
# Optional public CA already approved by the operator; TLS verification stays enabled.
RUN --mount=type=secret,id=platform_extra_ca \
    if [ -s /run/secrets/platform_extra_ca ]; then \
      cp /run/secrets/platform_extra_ca /usr/local/share/ca-certificates/platform-extra-ca.crt \
      && update-ca-certificates; \
    fi
COPY --from=uv /uv /usr/local/bin/uv

FROM python AS api
WORKDIR /deps/apps/api
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-install-project
WORKDIR /workspace

FROM python AS ingestion
# Same pinned age as apps/ingestion/Dockerfile: the backup copy tests encrypt for real.
RUN apt-get update && apt-get install -y --no-install-recommends age=1.2.1-1+b5 \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /deps/apps/ingestion
COPY apps/ingestion/pyproject.toml apps/ingestion/uv.lock ./
COPY apps/api/pyproject.toml ../api/pyproject.toml
# The API package itself comes from the mounted sources (PYTHONPATH), not the image.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-install-package property-platform-api
WORKDIR /workspace

FROM node:26.13.0-trixie-slim@sha256:5adad64f9a1fca2d51972caa65983634c8a774eb300d72b20f7f2a0f60368072 AS web
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates git \
    && rm -rf /var/lib/apt/lists/*
RUN --mount=type=secret,id=platform_extra_ca \
    if [ -s /run/secrets/platform_extra_ca ]; then \
      cp /run/secrets/platform_extra_ca /usr/local/share/ca-certificates/platform-extra-ca.crt \
      && update-ca-certificates; \
    fi
ENV NODE_USE_SYSTEM_CA=1 SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    NEXT_TELEMETRY_DISABLED=1 npm_config_store_dir=/pnpm-store
RUN npm install --global npm@12.2.0 \
    && npm install --global pnpm@12.18.0 --allow-scripts=pnpm \
    && git config --system --add safe.directory '*'
WORKDIR /workspace
