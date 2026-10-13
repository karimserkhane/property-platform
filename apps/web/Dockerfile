FROM node:26.11.1-trixie-slim AS base
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*
# Optional public CA already approved by the operator; TLS verification stays enabled.
RUN --mount=type=secret,id=platform_extra_ca \
    if [ -s /run/secrets/platform_extra_ca ]; then \
      cp /run/secrets/platform_extra_ca /usr/local/share/ca-certificates/platform-extra-ca.crt \
      && update-ca-certificates; \
    fi
ENV NODE_USE_SYSTEM_CA=1 SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

FROM base AS build
WORKDIR /repo
RUN npm install --global npm@12.2.0
RUN npm install --global pnpm@12.10.1 --allow-scripts=pnpm
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json ./apps/web/package.json
COPY packages/contracts/package.json ./packages/contracts/package.json
COPY packages/branding/package.json ./packages/branding/package.json
RUN pnpm install --frozen-lockfile
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
COPY packages/branding ./packages/branding
COPY scripts ./scripts
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @property-platform/web build && node scripts/prepare-web-runtime.mjs

FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
