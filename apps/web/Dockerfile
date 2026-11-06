FROM node:26.12.1-trixie-slim@sha256:94816674c62774da0d099a947bf4613b9e1972a2733abd0d0cd80e795f8411d0 AS base
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
RUN pnpm --filter @property-platform/web typecheck \
    && pnpm --filter @property-platform/web build \
    && node scripts/prepare-web-runtime.mjs \
    && node scripts/smoke-web.mjs

# Browser journeys (`checks-e2e`, docs/engineering/E2E.md). Pinned Playwright image by
# digest; the same Node runtime and compiled server as the preview. Journey files are
# mounted at run time (excluded from this build context), so editing them never
# invalidates the Next build cache. Declared before `runtime`, which stays the default.
FROM mcr.microsoft.com/playwright:v1.65.0-noble@sha256:6e3fb709361521eb27161606e6da6d2674e5e89fa16516cb37d6fdd91372273d AS e2e
COPY --from=base /usr/local/bin/node /usr/local/bin/node
WORKDIR /repo
COPY --from=build /repo /repo
ENV NEXT_TELEMETRY_DISABLED=1 CI=1 E2E_ARTIFACTS=/artifacts
WORKDIR /repo/apps/web
CMD ["node", "node_modules/@playwright/test/cli.js", "test", "--config", "playwright.config.ts"]

FROM base AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
