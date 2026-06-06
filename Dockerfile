# ═══════════════════════════════════════════════════════════
# Dockerfile — Next.js Frontend (Multi-stage build)
# ═══════════════════════════════════════════════════════════

# Stage 1: Dependencies
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# Stage 2: Build
FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
# Remove backend & model files from frontend build context
RUN rm -rf backend/ *.pkl catboost_info/
RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# CRITICAL: Next.js standalone MUST bind to 0.0.0.0
# otherwise Railway/Docker proxy cannot reach the server
ENV HOSTNAME=0.0.0.0

# Do NOT hardcode PORT — Railway injects PORT at runtime.
# Next.js standalone server.js reads process.env.PORT automatically.

# Copy only necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

CMD ["node", "server.js"]
