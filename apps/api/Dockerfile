FROM ghcr.io/astral-sh/uv:0.13.8@sha256:5cc1805e2426484abca4ad46ea783bab281fdb225fd82d8ce6d66a81254bac85 AS uv
FROM python:3.14.10-slim-trixie@sha256:af8a5aa14780025dbfbcfbc81bd8a91ebd87711dd5b0f48ed71090949dd7cb1d

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy UV_SYSTEM_CERTS=true
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates libgdal36 libgeos-c1t64 libproj25 && rm -rf /var/lib/apt/lists/*
# Optional public CA already approved by the operator; TLS verification stays enabled.
RUN --mount=type=secret,id=platform_extra_ca \
    if [ -s /run/secrets/platform_extra_ca ]; then \
      cp /run/secrets/platform_extra_ca /usr/local/share/ca-certificates/platform-extra-ca.crt \
      && update-ca-certificates; \
    fi
COPY --from=uv /uv /usr/local/bin/uv
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
COPY apps/api/manage.py ./manage.py
RUN uv sync --frozen --no-dev && useradd --create-home --uid 1000 property_platform \
    && mkdir -p /app/staticfiles /media && chown property_platform:property_platform /media \
    && chown -R property_platform:property_platform /app
USER property_platform
ENV PATH="/app/.venv/bin:$PATH" AWS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
EXPOSE 8000
# Idle connections stay open longer than the web server's fetch keeps them (undici: 4 s),
# so the client always closes first. At gunicorn's 2 s default, a read sent on an expired
# connection just as the worker closed it was reset before reaching Django (A31).
CMD ["gunicorn", "property_platform.config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--keep-alive", "30", "--access-logfile", "-"]
