# =============================================================================
# STIX Multi-Stage Dockerfile
# Builds all STIX services from monorepo
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base with dependencies
# -----------------------------------------------------------------------------
FROM node:20-alpine AS base

# Install build tools for native modules
RUN apk add --no-cache python3 make g++ curl

WORKDIR /app

# Copy workspace config
COPY package.json pnpm-lock.yaml* pnpm-workspace.yaml ./
COPY tsconfig.base.json ./

# Copy all package.json files for dependency resolution
COPY packages/shared/package.json ./packages/shared/
COPY services/enforcer/package.json ./services/enforcer/
COPY services/policy/package.json ./services/policy/
COPY services/evidence/package.json ./services/evidence/
COPY services/approvals/package.json ./services/approvals/

# Install pnpm and dependencies
RUN npm install -g pnpm
RUN pnpm install --frozen-lockfile --ignore-scripts

# -----------------------------------------------------------------------------
# Stage 2: Build
# -----------------------------------------------------------------------------
FROM base AS builder

# Copy source files
COPY packages/ ./packages/
COPY services/ ./services/

# Re-link workspace bins after source copy (COPY can replace pnpm symlinks)
RUN pnpm install --frozen-lockfile --ignore-scripts

# Build all packages
RUN pnpm --filter @stix/shared --filter @stix/enforcer --filter @stix/policy --filter @stix/evidence --filter @stix/approvals build

# -----------------------------------------------------------------------------
# Stage 3: Production - Enforcer
# -----------------------------------------------------------------------------
FROM node:20-alpine AS enforcer

WORKDIR /app

# Copy built files
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/shared/node_modules ./packages/shared/node_modules
COPY --from=builder /app/services/enforcer/node_modules ./services/enforcer/node_modules
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
COPY --from=builder /app/services/enforcer/dist ./services/enforcer/dist
COPY --from=builder /app/services/enforcer/package.json ./services/enforcer/

# Install curl for healthcheck
RUN apk add --no-cache curl

USER node
EXPOSE 3001

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3001/health || exit 1

CMD ["node", "services/enforcer/dist/index.js"]

# -----------------------------------------------------------------------------
# Stage 4: Production - Policy
# -----------------------------------------------------------------------------
FROM node:20-alpine AS policy

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/shared/node_modules ./packages/shared/node_modules
COPY --from=builder /app/services/policy/node_modules ./services/policy/node_modules
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
COPY --from=builder /app/services/policy/dist ./services/policy/dist
COPY --from=builder /app/services/policy/package.json ./services/policy/

RUN apk add --no-cache curl

USER node
EXPOSE 3002

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3002/health || exit 1

CMD ["node", "services/policy/dist/index.js"]

# -----------------------------------------------------------------------------
# Stage 5: Production - Evidence
# -----------------------------------------------------------------------------
FROM node:20-alpine AS evidence

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/shared/node_modules ./packages/shared/node_modules
COPY --from=builder /app/services/evidence/node_modules ./services/evidence/node_modules
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
COPY --from=builder /app/services/evidence/dist ./services/evidence/dist
COPY --from=builder /app/services/evidence/package.json ./services/evidence/

RUN apk add --no-cache curl

USER node
EXPOSE 3003

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3003/health || exit 1

CMD ["node", "services/evidence/dist/index.js"]

# -----------------------------------------------------------------------------
# Stage 6: Production - Approvals
# -----------------------------------------------------------------------------
FROM node:20-alpine AS approvals

WORKDIR /app

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/packages/shared/node_modules ./packages/shared/node_modules
COPY --from=builder /app/services/approvals/node_modules ./services/approvals/node_modules
COPY --from=builder /app/packages/shared/dist ./packages/shared/dist
COPY --from=builder /app/packages/shared/package.json ./packages/shared/
COPY --from=builder /app/services/approvals/dist ./services/approvals/dist
COPY --from=builder /app/services/approvals/package.json ./services/approvals/

RUN apk add --no-cache curl

USER node
EXPOSE 3004

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3004/health || exit 1

CMD ["node", "services/approvals/dist/index.js"]
