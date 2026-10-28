FROM ghcr.io/astral-sh/uv:0.13.0 AS uv
FROM python:3.14.8-slim-trixie AS base

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy \
    UV_SYSTEM_CERTS=true PREFECT_HOME=/home/property_platform/.prefect
WORKDIR /workspace/apps/ingestion
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates libgdal36 libgeos-c1t64 libproj25 \
    && rm -rf /var/lib/apt/lists/*
# Optional public CA already approved by the operator (e.g. local antivirus HTTPS scanning).
# TLS verification stays enabled; never pass an unverified issuer certificate.
RUN --mount=type=secret,id=platform_extra_ca \
    if [ -s /run/secrets/platform_extra_ca ]; then \
      cp /run/secrets/platform_extra_ca /usr/local/share/ca-certificates/platform-extra-ca.crt \
      && update-ca-certificates; \
    fi
COPY --from=uv /uv /usr/local/bin/uv
# PostgreSQL 18 client tools (pg_dump, pg_restore) matching the server, from the
# PGDG repository; the signing key fingerprint is checked before it is trusted.
RUN apt-get update && apt-get install -y --no-install-recommends curl gnupg     && curl -fsSL -o /tmp/pgdg.asc https://www.postgresql.org/media/keys/ACCC4CF8.asc     && gpg --show-keys --with-colons /tmp/pgdg.asc        | grep -q '^fpr:::::::::B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8:'     && install -d /usr/share/postgresql-common/pgdg     && mv /tmp/pgdg.asc /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc     && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt trixie-pgdg main"        > /etc/apt/sources.list.d/pgdg.list     && apt-get update && apt-get install -y --no-install-recommends postgresql-client-18     && apt-get purge -y curl gnupg && apt-get autoremove -y && rm -rf /var/lib/apt/lists/*
RUN useradd --create-home --uid 1000 property_platform \
    && mkdir -p /data /media /home/property_platform/.prefect \
    && chown property_platform:property_platform /data /media /home/property_platform/.prefect

FROM base AS build
COPY apps/ingestion/pyproject.toml apps/ingestion/uv.lock ./
COPY apps/api/pyproject.toml ../api/pyproject.toml
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project --no-install-package property-platform-api
COPY apps/api/src ../api/src
COPY apps/api/manage.py ../api/manage.py
COPY apps/ingestion/src ./src
COPY scripts/acquire_reem_imagery.py /workspace/scripts/acquire_reem_imagery.py
RUN --mount=type=cache,target=/root/.cache/uv uv sync --frozen --no-dev

FROM base AS runtime
# Copy once with the final ownership; no build caches or duplicated chown layer.
COPY --from=build --chown=1000:1000 /workspace /workspace
USER property_platform
ENV PATH="/workspace/apps/ingestion/.venv/bin:$PATH" INGESTION_STORAGE_DIR=/data \
    AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
CMD ["python", "-m", "property_platform_ingestion", "serve"]
