"""
whatsapp_bridge.py — Real WhatsApp Sending via Baileys for LeadFinder.

Architecture: LeadFinder (Python) ↔ Local HTTP bridge ↔ Node.js Baileys process

The Baileys Node.js process runs as a child process managed by this module.
It exposes a tiny HTTP API on localhost:8766 that LeadFinder calls.

Send policy (ported from Prospex send-policy.ts):
  - Hourly limit: 10 messages/hour (configurable)
  - Daily limit: 80 messages/day (configurable)
  - Quiet hours: 22:00–08:00 local time (configurable)
  - Human approval: every message queued for review before send
  - STOP handling: opt-out detected → permanent suppression
  - Typing delay: proportional to message length (human-like)
  - Random gap between sends (0.6x–1.4x of hourly interval)

The Node.js bridge is in whatsapp_bridge/server.js — installed with:
  cd whatsapp_bridge && npm install && node server.js

Usage:
  import whatsapp_bridge as WA
  WA.start_bridge()   # start the Node.js process (called at server startup)
  WA.queue_message(lead_id, phone, message)
  WA.handle(path, req)  # API handler
"""
import json, os, re, subprocess, threading, time, urllib.request
import db

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
BRIDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "whatsapp_bridge")
QUEUE_FILE  = os.path.join(DATA, "wa_queue.json")
LOG_FILE    = os.path.join(DATA, "wa_log.json")
CFG_FILE    = os.path.join(DATA, "wa_config.json")
BRIDGE_PORT = 8766
BRIDGE_URL  = f"http://127.0.0.1:{BRIDGE_PORT}"

_lock = threading.RLock()
_bridge_proc = None
_send_thread = None
_running = False

# ── Default config (mirrors Prospex send-policy.ts) ───────────────────────────

DEFAULT_CFG = {
    "enabled":      False,       # must be explicitly enabled after linking device
    "hourly_limit": 10,
    "daily_limit":  80,
    "quiet_start":  22,          # 10 PM local
    "quiet_end":    8,           # 8 AM local
    "timezone":     "UTC",
    "auto_approve": False,       # True = send without manual approval (use cautiously)
    "paused":       False,
    "your_name":    "",
    "opt_out_hint": "If you'd rather not hear from me, reply STOP.",
}

OPT_OUT_PATTERNS = re.compile(
    r"\bstop\b|\bunsubscribe\b|\bdo not (contact|message|whatsapp)\b|"
    r"\bremove me\b|\bopt.?out\b|\bjangan\s+(hubungi|chat)\b|\bberhenti\b",
    re.I
)


# ── Config helpers ────────────────────────────────────────────────────────────

def _load_cfg():
    os.makedirs(DATA, exist_ok=True)
    try:
        with open(CFG_FILE, encoding="utf-8") as f:
            d = json.load(f)
        out = dict(DEFAULT_CFG); out.update(d); return out
    except Exception:
        return dict(DEFAULT_CFG)

def _save_cfg(cfg):
    os.makedirs(DATA, exist_ok=True)
    with _lock:
        tmp = CFG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(cfg, f, indent=2)
        os.replace(tmp, CFG_FILE)


# ── Queue helpers ─────────────────────────────────────────────────────────────

def _load_queue():
    try:
        with open(QUEUE_FILE, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def _save_queue(q):
    with _lock:
        tmp = QUEUE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(q, f, indent=2)
        os.replace(tmp, QUEUE_FILE)

def _load_log():
    try:
        with open(LOG_FILE, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def _append_log(entry):
    with _lock:
        log = _load_log()
        log.insert(0, entry)
        log = log[:500]  # keep last 500
        with open(LOG_FILE, "w", encoding="utf-8") as f: json.dump(log, f, indent=2)


# ── Send policy (ported from Prospex send-policy.ts) ─────────────────────────

def _local_hour(tz: str) -> int:
    """Get current local hour in a given timezone."""
    try:
        import datetime
        # Python 3.9+ has zoneinfo; fall back to UTC offset for older versions
        try:
            from zoneinfo import ZoneInfo
            now = datetime.datetime.now(ZoneInfo(tz))
        except Exception:
            now = datetime.datetime.utcnow()
        return now.hour
    except Exception:
        return time.localtime().tm_hour

def _in_quiet_hours(hour: int, start: int, end: int) -> bool:
    if start == end: return False
    if start < end: return start <= hour < end
    return hour >= start or hour < end

def _count_sent_today(log: list) -> int:
    today = time.strftime("%Y-%m-%d")
    return sum(1 for e in log if e.get("sent_at", "").startswith(today) and e.get("status") == "sent")

def _count_sent_last_hour(log: list) -> int:
    cutoff = time.time() - 3600
    return sum(1 for e in log if e.get("ts", 0) >= cutoff and e.get("status") == "sent")

def _can_send(cfg: dict) -> dict:
    """Returns {ok: bool, reason: str}."""
    if not cfg.get("enabled"):
        return {"ok": False, "reason": "WhatsApp bridge not enabled — scan QR code first"}
    if cfg.get("paused"):
        return {"ok": False, "reason": "paused"}
    hour = _local_hour(cfg.get("timezone", "UTC"))
    if _in_quiet_hours(hour, cfg["quiet_start"], cfg["quiet_end"]):
        return {"ok": False, "reason": f"quiet hours ({cfg['quiet_start']}:00–{cfg['quiet_end']}:00 local)"}
    log = _load_log()
    if _count_sent_today(log) >= cfg["daily_limit"]:
        return {"ok": False, "reason": f"daily limit reached ({cfg['daily_limit']}/day)"}
    if _count_sent_last_hour(log) >= cfg["hourly_limit"]:
        return {"ok": False, "reason": f"hourly limit reached ({cfg['hourly_limit']}/hour)"}
    return {"ok": True, "reason": ""}

def _typing_delay_ms(msg_len: int) -> int:
    import random
    ms = 800 + msg_len * 35 + random.random() * 700
    return int(min(9000, max(1500, ms)))

def _next_gap_ms(hourly_limit: int) -> int:
    import random
    base = 3_600_000 / max(1, hourly_limit)
    return int(base * (0.6 + random.random() * 0.8))


# ── Queue a message ───────────────────────────────────────────────────────────

def queue_message(lead_id: str, phone: str, message: str,
                  campaign_id: str = "", auto_approve: bool = False) -> dict:
    """
    Add a message to the approval queue.
    Returns the queue entry dict.
    """
    cfg = _load_cfg()
    if not phone:
        return {"error": "Phone number required"}
    # Normalise phone: strip spaces/dashes, ensure starts with +
    phone_clean = re.sub(r"[\s\-().]", "", phone)
    if not phone_clean.startswith("+"):
        phone_clean = "+" + phone_clean.lstrip("0")

    # Append opt-out hint to first contact
    if cfg.get("opt_out_hint") and cfg["opt_out_hint"] not in message:
        message = message.rstrip() + "\n\n" + cfg["opt_out_hint"]

    entry = {
        "id": f"wa-{int(time.time() * 1000)}",
        "lead_id": lead_id,
        "phone": phone_clean,
        "message": message,
        "campaign_id": campaign_id,
        "status": "pending" if not (cfg.get("auto_approve") or auto_approve) else "approved",
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "sent_at": "",
        "ts": time.time(),
    }
    q = _load_queue()
    q.append(entry)
    _save_queue(q)
    db.publish_event("wa_queued", {"id": entry["id"], "phone": phone_clean, "lead_id": lead_id})

    # Auto-start sender loop if not running
    _ensure_sender_running()
    return entry


def approve_message(msg_id: str) -> dict:
    """Approve a queued message for sending."""
    q = _load_queue()
    for m in q:
        if m["id"] == msg_id:
            m["status"] = "approved"
            break
    _save_queue(q)
    return {"ok": True}

def reject_message(msg_id: str) -> dict:
    """Reject/cancel a queued message."""
    q = _load_queue()
    for m in q:
        if m["id"] == msg_id:
            m["status"] = "rejected"
            break
    _save_queue(q)
    return {"ok": True}


# ── Bridge HTTP client ────────────────────────────────────────────────────────

def _bridge_post(path: str, body: dict) -> dict:
    """POST to the Node.js Baileys bridge."""
    url = BRIDGE_URL + path
    data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data,
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read().decode())
    except Exception as ex:
        return {"error": str(ex)}

def _bridge_get(path: str) -> dict:
    try:
        with urllib.request.urlopen(BRIDGE_URL + path, timeout=10) as r:
            return json.loads(r.read().decode())
    except Exception as ex:
        return {"error": str(ex)}

def _bridge_alive() -> bool:
    try:
        result = _bridge_get("/status")
        return "status" in result
    except Exception:
        return False


# ── Sender loop ───────────────────────────────────────────────────────────────

def _sender_loop():
    global _running
    _running = True
    while _running:
        try:
            cfg = _load_cfg()
            q = _load_queue()
            approved = [m for m in q if m["status"] == "approved"]

            if approved and _bridge_alive():
                policy = _can_send(cfg)
                if policy["ok"]:
                    msg = approved[0]
                    # Send via bridge
                    result = _bridge_post("/send", {
                        "phone": msg["phone"],
                        "message": msg["message"],
                        "typing_delay_ms": _typing_delay_ms(len(msg["message"])),
                    })
                    # Update queue entry
                    q2 = _load_queue()
                    for m2 in q2:
                        if m2["id"] == msg["id"]:
                            if result.get("ok"):
                                m2["status"] = "sent"
                                m2["sent_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                                m2["ts"] = time.time()
                            else:
                                m2["status"] = "failed"
                                m2["error"] = result.get("error", "")
                            break
                    _save_queue(q2)
                    _append_log({**msg, **result,
                                 "sent_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                 "ts": time.time()})
                    if result.get("ok"):
                        db.publish_event("wa_sent", {"id": msg["id"], "phone": msg["phone"], "lead_id": msg.get("lead_id", "")})
                        if msg.get("lead_id"):
                            db.update_lead_field(msg["lead_id"], stage="Contacted",
                                                 contacted_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
                            db.log_outreach(msg["lead_id"], "whatsapp", "", msg["message"], "sent")
                        # Wait the random gap before next send
                        time.sleep(_next_gap_ms(cfg["hourly_limit"]) / 1000)
                    else:
                        db.publish_event("wa_failed", {"id": msg["id"], "error": result.get("error", "")})
        except Exception:
            pass
        time.sleep(5)

def _ensure_sender_running():
    global _send_thread
    if _send_thread and _send_thread.is_alive():
        return
    _send_thread = threading.Thread(target=_sender_loop, daemon=True, name="wa-sender")
    _send_thread.start()


# ── Node.js bridge process management ─────────────────────────────────────────

def start_bridge():
    """
    Start the Node.js WhatsApp Baileys bridge process.
    If Node.js is not installed or the bridge dir is missing, logs a warning.
    """
    global _bridge_proc
    server_js = os.path.join(BRIDGE_DIR, "server.js")
    if not os.path.isfile(server_js):
        _scaffold_bridge()
    if _bridge_alive():
        _ensure_sender_running()
        return
    try:
        node_path = _find_node()
        if not node_path:
            db.publish_event("wa_bridge_unavailable",
                             {"reason": "Node.js not found. Install it to enable WhatsApp sending."})
            return
        nm = os.path.join(BRIDGE_DIR, "node_modules")
        if not os.path.isdir(nm):
            # npm install first
            subprocess.run(["npm", "install", "--prefix", BRIDGE_DIR],
                           capture_output=True, timeout=120)
        _bridge_proc = subprocess.Popen(
            [node_path, server_js],
            cwd=BRIDGE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2)
        if _bridge_alive():
            db.publish_event("wa_bridge_started", {"port": BRIDGE_PORT})
            _ensure_sender_running()
        else:
            db.publish_event("wa_bridge_unavailable", {"reason": "Bridge started but not responding"})
    except Exception as ex:
        db.publish_event("wa_bridge_unavailable", {"reason": str(ex)})

def _find_node() -> str:
    for cmd in ["node", "/usr/bin/node", "/usr/local/bin/node"]:
        try:
            r = subprocess.run([cmd, "--version"], capture_output=True, timeout=5)
            if r.returncode == 0: return cmd
        except Exception:
            pass
    return ""

def stop_bridge():
    global _bridge_proc, _running
    _running = False
    if _bridge_proc:
        try: _bridge_proc.terminate()
        except Exception: pass
        _bridge_proc = None


# ── Scaffold the Node.js bridge files ────────────────────────────────────────

def _scaffold_bridge():
    """Create the whatsapp_bridge/ Node.js project if it doesn't exist."""
    os.makedirs(BRIDGE_DIR, exist_ok=True)

    pkg = {
        "name": "leadfinder-whatsapp-bridge",
        "version": "1.0.0",
        "description": "WhatsApp Baileys bridge for LeadFinder",
        "main": "server.js",
        "scripts": {"start": "node server.js"},
        "dependencies": {
            "@whiskeysockets/baileys": "^6.7.5",
            "qrcode-terminal": "^0.12.0",
            "pino": "^9.0.0"
        }
    }
    pkg_path = os.path.join(BRIDGE_DIR, "package.json")
    if not os.path.exists(pkg_path):
        with open(pkg_path, "w") as f: json.dump(pkg, f, indent=2)

    server_path = os.path.join(BRIDGE_DIR, "server.js")
    if not os.path.exists(server_path):
        server_js = r'''/**
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
'''
        with open(server_path, "w", encoding="utf-8") as f:
            f.write(server_js)

    readme_path = os.path.join(BRIDGE_DIR, "README.md")
    if not os.path.exists(readme_path):
        with open(readme_path, "w") as f:
            f.write("""# LeadFinder WhatsApp Bridge

This folder contains the Node.js Baileys bridge that enables real WhatsApp sending.

## Setup (one-time)

```bash
cd whatsapp_bridge
npm install
node server.js
```

Then scan the QR code that appears in the terminal with **WhatsApp → Settings → Linked Devices → Link a Device**.

After scanning, the bridge is connected. LeadFinder picks it up automatically.

## Important

- Use a **dedicated business number** — never your personal WhatsApp account.
- Session is saved in `.wa-auth/` — survives restarts.
- Messages must be approved in LeadFinder's WhatsApp tab before sending (unless auto-approve is enabled).

## Rate limits (default)

- 10 messages / hour
- 80 messages / day
- Quiet hours: 22:00–08:00 (configurable)
""")


# ── Inbound message handler (called by bridge via POST /api/whatsapp/inbound) ─

def handle_inbound(phone: str, message: str) -> dict:
    """
    Process an inbound WhatsApp reply.
    Checks for opt-out, classifies reply, updates lead stage.
    """
    # Opt-out detection (ported from Prospex opt-out.ts)
    if OPT_OUT_PATTERNS.search(message.strip()[:300]):
        try:
            import pipeline
            pipeline.handle("/api/suppression/add", {"email": phone, "phone": phone})
        except Exception:
            pass
        db.publish_event("wa_optout", {"phone": phone})
        return {"action": "opted_out"}

    # Try to match phone to a lead in the DB
    leads = db.get_leads(search=phone, limit=5)
    matched = next((l for l in leads if phone in (l.get("phone", ""), l.get("social", ""))), None)
    if matched:
        db.log_outreach(matched["id"], "whatsapp", "", message, "replied", "in")
        db.update_lead_field(matched["id"], stage="Interested")
        try:
            import webhooks
            webhooks.deliver_async("lead_interested", matched)
        except Exception:
            pass
        db.publish_event("wa_reply", {"phone": phone, "lead_id": matched["id"], "message": message[:200]})

    return {"action": "logged"}


# ── Status ────────────────────────────────────────────────────────────────────

def get_status() -> dict:
    bridge = _bridge_get("/status") if _bridge_alive() else {"status": "bridge_offline"}
    q = _load_queue()
    log = _load_log()
    cfg = _load_cfg()
    today = time.strftime("%Y-%m-%d")
    sent_today = sum(1 for e in log if e.get("sent_at", "").startswith(today) and e.get("status") == "sent")
    return {
        "bridge": bridge,
        "bridge_alive": _bridge_alive(),
        "config": cfg,
        "queue": {
            "pending":  sum(1 for m in q if m["status"] == "pending"),
            "approved": sum(1 for m in q if m["status"] == "approved"),
            "sent":     sum(1 for m in q if m["status"] == "sent"),
            "failed":   sum(1 for m in q if m["status"] == "failed"),
        },
        "sent_today": sent_today,
        "daily_limit": cfg["daily_limit"],
        "policy": _can_send(cfg),
        "bridge_dir": BRIDGE_DIR,
        "node_found": bool(_find_node()),
        "setup_instructions": (
            "1. Install Node.js (nodejs.org)\n"
            "2. Run: cd whatsapp_bridge && npm install && node server.js\n"
            "3. Scan the QR code with WhatsApp → Linked Devices\n"
            "4. Enable WhatsApp in LeadFinder Settings"
        ) if not _bridge_alive() else "",
    }


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/whatsapp/status":
        return get_status()

    if path == "/api/whatsapp/queue":
        lead_id    = req.get("lead_id", "")
        phone      = req.get("phone", "")
        message    = req.get("message", "")
        campaign   = req.get("campaign_id", "")
        auto_ok    = bool(req.get("auto_approve", False))
        return queue_message(lead_id, phone, message, campaign, auto_ok)

    if path == "/api/whatsapp/approve":
        return approve_message(req.get("id", ""))

    if path == "/api/whatsapp/reject":
        return reject_message(req.get("id", ""))

    if path == "/api/whatsapp/queue/list":
        q = _load_queue()
        status_filter = req.get("status")
        if status_filter:
            q = [m for m in q if m["status"] == status_filter]
        return {"messages": q[-100:]}

    if path == "/api/whatsapp/log":
        return {"log": _load_log()[:100]}

    if path == "/api/whatsapp/config":
        if req:
            cfg = _load_cfg()
            for k in DEFAULT_CFG:
                if k in req: cfg[k] = req[k]
            _save_cfg(cfg)
            return {"ok": True, "config": cfg}
        return {"config": _load_cfg()}

    if path == "/api/whatsapp/inbound":
        return handle_inbound(req.get("phone", ""), req.get("message", ""))

    if path == "/api/whatsapp/start_bridge":
        start_bridge()
        return get_status()

    if path == "/api/whatsapp/stop_bridge":
        stop_bridge()
        return {"ok": True}

    if path == "/api/whatsapp/scaffold":
        _scaffold_bridge()
        return {"ok": True, "bridge_dir": BRIDGE_DIR}

    if path == "/api/whatsapp/qr":
        if _bridge_alive():
            return _bridge_get("/qr")
        return {"error": "Bridge not running"}

    return {"error": f"Unknown whatsapp path: {path}"}
