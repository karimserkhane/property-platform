FROM ghcr.io/astral-sh/uv:0.13.0 AS uv
FROM python:3.14.8-slim-trixie

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 UV_LINK_MODE=copy
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends libgdal36 libgeos-c1t64 libproj25 && rm -rf /var/lib/apt/lists/*
COPY --from=uv /uv /usr/local/bin/uv
COPY apps/api/pyproject.toml apps/api/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY apps/api/src ./src
COPY apps/api/manage.py ./manage.py
RUN uv sync --frozen --no-dev && useradd --create-home liwa && mkdir /app/staticfiles && chown -R liwa:liwa /app
USER liwa
ENV PATH="/app/.venv/bin:$PATH"
EXPOSE 8000
CMD ["gunicorn", "liwa.config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "1", "--threads", "4", "--access-logfile", "-"]
