# Reproducible check runners for people and AI agents, matching the CI jobs.
# Dependencies are installed from the lockfiles at build time; the repository is
# mounted at /workspace at run time. See infra/local/compose.checks.yaml.
FROM ghcr.io/astral-sh/uv:0.13.0 AS uv

FROM python:3.14.8-slim-trixie AS python
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
WORKDIR /deps/apps/ingestion
COPY apps/ingestion/pyproject.toml apps/ingestion/uv.lock ./
COPY apps/api/pyproject.toml ../api/pyproject.toml
# The API package itself comes from the mounted sources (PYTHONPATH), not the image.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-install-package property-platform-api
WORKDIR /workspace

FROM node:26.11.1-trixie-slim AS web
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
    && npm install --global pnpm@12.10.1 --allow-scripts=pnpm \
    && git config --system --add safe.directory '*'
WORKDIR /workspace
