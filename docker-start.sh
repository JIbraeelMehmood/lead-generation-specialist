#!/bin/sh
# LeadFinder Docker start script
# Starts the WhatsApp bridge (Node.js) in background, then LeadFinder (Python)

echo "[LeadFinder] Starting..."

# Start WhatsApp bridge if Node.js is available
if command -v node >/dev/null 2>&1 && [ -f /app/whatsapp_bridge/server.js ]; then
  echo "[LeadFinder] Starting WhatsApp bridge on port 8766..."
  node /app/whatsapp_bridge/server.js &
  sleep 2
fi

# Start LeadFinder Python server
# Bind to 0.0.0.0 in Docker so it's accessible from outside the container
echo "[LeadFinder] Starting on port 8765..."
exec python3 /app/leadfinder.py --no-browser
