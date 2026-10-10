FROM node:26.11.1-trixie-slim AS build
WORKDIR /repo
RUN npm install --global npm@12.2.0
RUN npm install --global pnpm@12.10.1 --allow-scripts=pnpm
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web ./apps/web
COPY packages/contracts ./packages/contracts
COPY scripts ./scripts
RUN pnpm install --frozen-lockfile
ENV NEXT_TELEMETRY_DISABLED=1
RUN pnpm --filter @liwa/web build && node scripts/prepare-web-runtime.mjs

FROM node:26.11.1-trixie-slim AS runtime
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000
COPY --from=build --chown=node:node /repo/apps/web/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "apps/web/server.js"]
