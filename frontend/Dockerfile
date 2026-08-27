# CyberRakshak frontend (Next.js 16 App Router, next-intl).
#
# Build context is this directory:
#   docker build -t cyberrakshak-web --build-arg NEXT_PUBLIC_API_URL=https://api.example.com ./frontend
#
# node:22-slim rather than alpine on purpose: next/image is used without
# `unoptimized`, so sharp is needed at runtime, and glibc avoids the musl libvips
# variant dance. next@16 requires Node >= 20.9.

FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-slim AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# NEXT_PUBLIC_* values are inlined into the browser bundle at BUILD time, so this has
# to be a build arg - supplying it only at runtime produces a bundle that throws on the
# first API call. Fail loudly here instead of shipping that silently broken image.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN test -n "$NEXT_PUBLIC_API_URL" \
 || { echo "ERROR: NEXT_PUBLIC_API_URL build arg is required (it is inlined into the browser bundle)." >&2; exit 1; }
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder --chown=node:node /app/public ./public

USER node
EXPOSE 3000

# server.js honours PORT and HOSTNAME; without HOSTNAME=0.0.0.0 it binds localhost only.
CMD ["node", "server.js"]
