# ═══════════════════════════════════════════════════════════════════════
# Dockerfile — Next.js Frontend (Multi-stage build, Railway-compatible)
# ═══════════════════════════════════════════════════════════════════════

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

# NEXT_PUBLIC_ env vars must be available at BUILD time
# Railway sets these as build-time variables
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# Stage 3: Production
FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production

# Copy only necessary files
COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

# Railway sets PORT automatically
ENV PORT=3000
EXPOSE ${PORT}

CMD ["node", "server.js"]
