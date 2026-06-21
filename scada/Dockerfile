# =============================================================================
# SCADA Dockerfile — NVIDIA AI Factory Controls
# =============================================================================
# Multi-stage build:
#   Stage 1: Build the frontend (Vite/React)
#   Stage 2: Serve frontend + run backend API
#
# Ports:
#   4000 — Backend API (Express/Node.js, subscribes to NATS)
#   3001 — Frontend UI (nginx serving built assets)
#
# Build: docker build -t aifactory-scada ./scada
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Build Frontend
# ---------------------------------------------------------------------------
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install frontend dependencies
COPY frontend/package*.json ./
RUN npm ci --production=false

# Build frontend assets
COPY frontend/ ./
RUN npm run build

# ---------------------------------------------------------------------------
# Stage 2: Runtime (Backend + serve Frontend)
# ---------------------------------------------------------------------------
FROM node:20-alpine AS runtime

LABEL maintainer="NVIDIA AI Factory Controls"
LABEL description="SCADA backend API + frontend UI"

WORKDIR /app

# Install backend dependencies
COPY backend/package*.json ./backend/
RUN cd backend && npm ci --production

# Copy backend source
COPY backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Install nginx for serving frontend
RUN apk add --no-cache nginx && \
    mkdir -p /run/nginx

# Nginx config to serve frontend on port 3001 and proxy API
COPY nginx.conf /etc/nginx/http.d/default.conf

# Environment defaults
ENV NATS_URL=nats://nats:4222
ENV PORT=4000
ENV FRONTEND_PORT=3001
ENV NODE_ENV=production

# Expose ports
EXPOSE 4000 3001

# Start script: run backend + nginx
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]
