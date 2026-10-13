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
RUN useradd --create-home --uid 1000 property_platform \
    && mkdir -p /data /home/property_platform/.prefect \
    && chown property_platform:property_platform /data /home/property_platform/.prefect

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
ENV PATH="/workspace/apps/ingestion/.venv/bin:$PATH" INGESTION_STORAGE_DIR=/data
CMD ["python", "-m", "property_platform_ingestion", "serve"]
