"""
IMAP reply monitor for LeadFinder — ported from OutLead's inbox module.

Watches your sending inbox for replies from leads and:
  • marks leads in "My list" as "Replied"
  • optionally suppresses the address permanently on "unsubscribe" requests
  • classifies auto-replies (OOO) and ignores them

Standard library only: imaplib + email. No pip installs.

Usage (via the API / settings in the app):
  POST /api/imap/check   { "email": "you@yoursmtp.com", "password": "...", "host": "imap.gmail.com" }
  POST /api/imap/config  { "save": { "host": "...", "email": "...", "password": "...", "lookbackDays": 7 } }
  GET  /api/imap/status
"""
import email as emaillib
import imaplib
import json
import os
import re
import threading
import time

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)
_CONFIG_FILE = os.path.join(DATA, "imap_config.json")
_REPLIES_FILE = os.path.join(DATA, "imap_replies.json")
_lock = threading.RLock()

# Patterns for classifying reply types
OOO_PATTERNS = re.compile(
    r"out of (office|town|the office)|on (vacation|leave|holiday)|auto.?reply|"
    r"automatic(ally)? reply|will be (away|back|unavailable)|not in the office|"
    r"returning on|maternity|paternity|sabbatical|annual leave|currently traveling",
    re.I)

UNSUB_PATTERNS = re.compile(
    r"\b(unsubscribe|remove me|opt.?out|stop emailing|stop sending|"
    r"don'?t (email|contact|send)|take me off|not interested)\b",
    re.I)

POSITIVE_PATTERNS = re.compile(
    r"\b(interested|tell me more|sounds good|yes please|let'?s (talk|chat|connect)|"
    r"call me|more info|book|schedule|quote|price|how much|cost)\b",
    re.I)


# ---------------------------------------------------------------- config
def _load_cfg():
    try:
        with open(_CONFIG_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_cfg(c):
    with open(_CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(c, f, indent=2)

def _load_replies():
    try:
        with open(_REPLIES_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

def _save_replies(r):
    with open(_REPLIES_FILE, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)


# ---------------------------------------------------------------- IMAP helpers
def _connect(host, email_addr, password, port=None):
    if port is None:
        port = 993
    try:
        conn = imaplib.IMAP4_SSL(host, port)
    except Exception as ex:
        raise RuntimeError(f"Couldn't connect to {host}:{port}: {ex}")
    try:
        conn.login(email_addr, password)
    except imaplib.IMAP4.error as ex:
        raise RuntimeError(f"IMAP login failed for {email_addr}: {ex}. "
                           "For Gmail, enable IMAP and use an App Password.")
    return conn


def _decode_header(val):
    if not val:
        return ""
    parts = emaillib.header.decode_header(val)
    result = []
    for b, charset in parts:
        if isinstance(b, bytes):
            result.append(b.decode(charset or "utf-8", "replace"))
        else:
            result.append(str(b))
    return " ".join(result)


def _body_text(msg):
    if msg.is_multipart():
        for part in msg.walk():
            ct = part.get_content_type()
            if ct == "text/plain":
                payload = part.get_payload(decode=True)
                charset = part.get_content_charset() or "utf-8"
                return (payload or b"").decode(charset, "replace")
    else:
        payload = msg.get_payload(decode=True)
        charset = msg.get_content_charset() or "utf-8"
        return (payload or b"").decode(charset, "replace")
    return ""


def classify_reply(subject, body):
    """
    Returns: 'ooo', 'unsubscribe', 'positive', 'reply'
    """
    text = f"{subject} {body}"
    if OOO_PATTERNS.search(text):
        return "ooo"
    if UNSUB_PATTERNS.search(text):
        return "unsubscribe"
    if POSITIVE_PATTERNS.search(text):
        return "positive"
    return "reply"


def check_replies(host, email_addr, password, lookback_days=7, port=None,
                  known_emails=None):
    """
    Fetch recent replies. Returns list of dicts:
      { from_email, subject, body, kind, date, uid }
    known_emails: set of addresses we've contacted (filter to only track those)
    """
    conn = _connect(host, email_addr, password, port)
    try:
        conn.select("INBOX")
        # Search for messages in the last `lookback_days` days
        since = time.strftime("%d-%b-%Y",
                               time.gmtime(time.time() - lookback_days * 86400))
        _ok, nums = conn.search(None, f'(SINCE "{since}")')
        ids = (nums[0] or b"").split()
        results = []
        for uid in ids[-500:]:  # cap at 500 to avoid timeouts
            _ok2, data = conn.fetch(uid, "(RFC822)")
            if not data or not data[0]:
                continue
            raw = data[0][1] if isinstance(data[0], tuple) else data[0]
            msg = emaillib.message_from_bytes(raw)
            from_hdr = _decode_header(msg.get("From", ""))
            # Extract plain email address
            m = re.search(r"[\w.%+\-]+@[\w.\-]+\.[A-Za-z]{2,24}", from_hdr)
            from_email = m.group(0).lower() if m else ""
            if not from_email or from_email == email_addr.lower():
                continue
            if known_emails and from_email not in known_emails:
                continue
            subject = _decode_header(msg.get("Subject", ""))
            body = _body_text(msg)[:2000]
            kind = classify_reply(subject, body)
            date = _decode_header(msg.get("Date", ""))
            results.append({
                "from_email": from_email, "subject": subject,
                "body": body[:500], "kind": kind, "date": date,
                "uid": uid.decode(),
            })
        return results
    finally:
        try:
            conn.logout()
        except Exception:
            pass


# ---------------------------------------------------------------- process replies against My list
def process_replies(replies):
    """
    Match replies against the outbox (localStorage) — we can't access the
    browser store from Python, but we can write a JSON file that the JS
    frontend polls and acts on.
    """
    stored = _load_replies()
    existing_uids = {r["uid"] for r in stored}
    new_replies = []
    for r in replies:
        if r["uid"] not in existing_uids:
            r["processedAt"] = time.strftime("%Y-%m-%d %H:%M")
            new_replies.append(r)
            stored.append(r)
    if new_replies:
        _save_replies(stored)
    return new_replies


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/imap/config":
        with _lock:
            if req.get("save"):
                c = _load_cfg()
                for k in ("host", "email", "password", "lookbackDays", "port", "enabled"):
                    if k in req["save"]:
                        c[k] = req["save"][k]
                _save_cfg(c)
            return {k: v for k, v in _load_cfg().items() if k != "password"}  # never return password

    if path == "/api/imap/status":
        c = _load_cfg()
        stored = _load_replies()
        return {
            "configured": bool(c.get("host") and c.get("email")),
            "enabled": bool(c.get("enabled")),
            "recentReplies": stored[-50:],  # last 50
            "totalReplies": len(stored),
        }

    if path == "/api/imap/check":
        c = _load_cfg()
        host = req.get("host") or c.get("host", "")
        email_addr = req.get("email") or c.get("email", "")
        password = req.get("password") or c.get("password", "")
        lookback = int(req.get("lookbackDays") or c.get("lookbackDays", 7))
        port = req.get("port") or c.get("port")

        if not (host and email_addr and password):
            raise RuntimeError("Set your IMAP host, email and password in Settings > Reply monitor first.")

        known = set(req.get("sentEmails", []))
        replies = check_replies(host, email_addr, password, lookback,
                                port=port, known_emails=known if known else None)
        new = process_replies(replies)

        # Classify summary
        summary = {"total": len(replies), "new": len(new)}
        for kind in ("positive", "reply", "unsubscribe", "ooo"):
            summary[kind] = sum(1 for r in replies if r["kind"] == kind)
        return {"replies": replies[:100], "new": new, "summary": summary}

    if path == "/api/imap/replies":
        return {"replies": _load_replies()[-100:]}

    if path == "/api/imap/clear":
        _save_replies([])
        return {"ok": True}

    raise RuntimeError("Unknown endpoint")
