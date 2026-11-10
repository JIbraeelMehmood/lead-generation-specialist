/**
 * LeadFinder WhatsApp Bridge — Baileys + HTTP server
 *
 * Runs on localhost:8766. LeadFinder Python calls:
 *   POST /send         { phone, message, typing_delay_ms }
 *   GET  /status       returns { status, qr, phone }
 *   POST /disconnect   logout
 *   GET  /qr           returns { qr } (base64 QR code for scan)
 *
 * On first run: a QR code is printed to terminal — scan with WhatsApp > Linked devices.
 * Session saved in .wa-auth/ — survives restarts.
 *
 * IMPORTANT: Use a dedicated business number, never your personal number.
 */
"use strict";

const http = require("http");
const path = require("path");
const { mkdir } = require("fs/promises");
const makeWASocket = require("@whiskeysockets/baileys").default;
const {
  useMultiFileAuthState,
  DisconnectReason,
  fetchLatestBaileysVersion,
  Browsers,
} = require("@whiskeysockets/baileys");
const qrcode = require("qrcode-terminal");
const pino = require("pino");

const PORT = parseInt(process.env.WA_BRIDGE_PORT || "8766");
const AUTH_DIR = path.join(__dirname, ".wa-auth");
const logger = pino({ level: "warn" });

let sock = null;
let currentQR = null;
let status = "disconnected";   // disconnected | qr | connecting | connected
let phone = null;
let reconnectAttempts = 0;
const MAX_RECONNECTS = 8;

// ── Connect / reconnect ──────────────────────────────────────────────────────

async function connect() {
  await mkdir(AUTH_DIR, { recursive: true });
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version } = await fetchLatestBaileysVersion();

  status = "connecting";
  sock = makeWASocket({
    version,
    logger,
    auth: state,
    browser: Browsers.macOS("Safari"),
    printQRInTerminal: false,
    generateHighQualityLinkPreview: false,
  });

  sock.ev.on("creds.update", saveCreds);

  sock.ev.on("connection.update", ({ connection, lastDisconnect, qr }) => {
    if (qr) {
      currentQR = qr;
      status = "qr";
      console.log("\n[WA Bridge] Scan this QR code with WhatsApp > Linked Devices:\n");
      qrcode.generate(qr, { small: true });
    }
    if (connection === "open") {
      status = "connected";
      currentQR = null;
      reconnectAttempts = 0;
      phone = sock.user?.id?.split(":")[0] || null;
      console.log("[WA Bridge] Connected:", phone);
    }
    if (connection === "close") {
      const code = lastDisconnect?.error?.output?.statusCode;
      const loggedOut = code === DisconnectReason.loggedOut;
      if (loggedOut) {
        status = "logged_out";
        console.log("[WA Bridge] Logged out. Delete .wa-auth/ and restart to re-link.");
      } else if (reconnectAttempts < MAX_RECONNECTS) {
        reconnectAttempts++;
        status = "connecting";
        const delay = Math.min(2000 * reconnectAttempts, 30000);
        console.log(`[WA Bridge] Reconnecting (attempt ${reconnectAttempts})…`);
        setTimeout(connect, delay);
      } else {
        status = "disconnected";
        console.log("[WA Bridge] Max reconnects reached.");
      }
    }
  });
}

// ── Send a message ───────────────────────────────────────────────────────────

async function sendMessage(phone, message, typingDelayMs) {
  if (!sock || status !== "connected") {
    return { ok: false, error: "Not connected. Scan QR code to link your WhatsApp." };
  }
  const jid = phone.replace(/[^0-9]/g, "") + "@s.whatsapp.net";
  try {
    // Simulate typing
    await sock.sendPresenceUpdate("composing", jid);
    await new Promise(r => setTimeout(r, typingDelayMs || 2000));
    await sock.sendPresenceUpdate("paused", jid);
    // Send
    await sock.sendMessage(jid, { text: message });
    return { ok: true, jid };
  } catch (err) {
    return { ok: false, error: err.message };
  }
}

// ── HTTP server ──────────────────────────────────────────────────────────────

function readBody(req) {
  return new Promise((resolve, reject) => {
    let data = "";
    req.on("data", c => data += c);
    req.on("end", () => {
      try { resolve(JSON.parse(data || "{}")); }
      catch (e) { resolve({}); }
    });
    req.on("error", reject);
  });
}

function send(res, code, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(code, { "Content-Type": "application/json", "Content-Length": Buffer.byteLength(body) });
  res.end(body);
}

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/status") {
    return send(res, 200, { status, qr: currentQR ? "pending" : null, phone });
  }
  if (req.method === "GET" && req.url === "/qr") {
    return send(res, 200, { qr: currentQR, status });
  }
  if (req.method === "POST" && req.url === "/send") {
    const body = await readBody(req);
    const result = await sendMessage(body.phone, body.message, body.typing_delay_ms);
    return send(res, 200, result);
  }
  if (req.method === "POST" && req.url === "/disconnect") {
    if (sock) { await sock.logout().catch(() => {}); }
    status = "disconnected"; phone = null;
    return send(res, 200, { ok: true });
  }
  send(res, 404, { error: "Not found" });
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`[WA Bridge] Listening on 127.0.0.1:${PORT}`);
  connect();
});
