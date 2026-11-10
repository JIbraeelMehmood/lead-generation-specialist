# ── LeadFinder Dockerfile ─────────────────────────────────────────────────────
# Multi-stage: Stage 1 builds the optional WhatsApp bridge (Node.js)
#              Stage 2 is the Python app

# ── Stage 1: WhatsApp bridge (optional) ──────────────────────────────────────
FROM node:20-alpine AS wa-bridge
WORKDIR /app/whatsapp_bridge
COPY whatsapp_bridge/package.json ./
RUN npm install --production --no-fund --no-audit 2>/dev/null || true
COPY whatsapp_bridge/ ./

# ── Stage 2: Python app ────────────────────────────────────────────────────────
FROM python:3.11-slim

# System deps (Playwright needs these if you install it)
RUN apt-get update && apt-get install -y --no-install-recommends \
    nodejs npm curl ca-certificates \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Optional: install Playwright for deep scan
# Uncomment if you want deep scanning:
# RUN pip install --no-cache-dir playwright && playwright install chromium --with-deps

WORKDIR /app

# Copy Python source
COPY *.py ./
COPY app.html ./
COPY static/ ./static/
COPY .gitignore ./

# Copy WhatsApp bridge from stage 1
COPY --from=wa-bridge /app/whatsapp_bridge ./whatsapp_bridge/

# Copy knowledge base template (not actual user data)
RUN mkdir -p .leadfinder/knowledge data

# Expose LeadFinder + WhatsApp bridge ports
EXPOSE 8765 8766

# Start script: launch WA bridge in background, then start LeadFinder
COPY docker-start.sh ./
RUN chmod +x docker-start.sh

CMD ["./docker-start.sh"]
