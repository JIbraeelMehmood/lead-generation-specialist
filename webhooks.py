"""
webhooks.py — CRM Webhook Delivery for LeadFinder.

Ported from intent-engine/backend/app/webhook_delivery.py + webhook_store.py.

When a lead reaches a configured pipeline stage (default: "Interested"),
LeadFinder POSTs a structured payload to your configured webhook URL.

Compatible with: Zapier, Make (Integromat), n8n, GoHighLevel, HubSpot,
Salesforce, Pipedrive, Slack, Discord, or any HTTP endpoint.

Storage: webhook URLs saved in data/webhooks.json (one per trigger event,
no Redis needed — stays zero-dependency).
"""
import json, os, re, threading, time, urllib.request, urllib.error

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
WEBHOOKS_FILE = os.path.join(DATA, "webhooks.json")
_lock = threading.RLock()

# Delivery log — last 200 delivery attempts kept in memory
_delivery_log = []
_log_lock = threading.Lock()

# ── Default config ────────────────────────────────────────────────────────────

DEFAULT_WEBHOOKS = {
    # trigger_name -> { url, enabled, label, last_fired, fire_count }
    "lead_interested":    {"url": "", "enabled": True,  "label": "Lead → Interested"},
    "lead_won":           {"url": "", "enabled": True,  "label": "Lead → Won"},
    "lead_new":           {"url": "", "enabled": False, "label": "New lead captured"},
    "inbound_captured":   {"url": "", "enabled": False, "label": "Inbound form submission"},
    "sequence_sent":      {"url": "", "enabled": False, "label": "Email sequence step sent"},
    "b2b_hunt_done":      {"url": "", "enabled": False, "label": "B2B hunt completed"},
    "custom":             {"url": "", "enabled": False, "label": "Custom (manual trigger)"},
}

# Stage → trigger name mapping
STAGE_TRIGGERS = {
    "Interested":    "lead_interested",
    "Won":           "lead_won",
    "New":           "lead_new",
}


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load() -> dict:
    os.makedirs(DATA, exist_ok=True)
    try:
        with open(WEBHOOKS_FILE, encoding="utf-8") as f:
            saved = json.load(f)
        # Merge with defaults so new trigger keys always exist
        out = json.loads(json.dumps(DEFAULT_WEBHOOKS))
        for trigger, cfg in saved.items():
            if trigger in out:
                out[trigger].update(cfg)
            else:
                out[trigger] = cfg
        return out
    except Exception:
        return json.loads(json.dumps(DEFAULT_WEBHOOKS))

def _save(data: dict):
    os.makedirs(DATA, exist_ok=True)
    with _lock:
        tmp = WEBHOOKS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, WEBHOOKS_FILE)

def get_webhook(trigger: str) -> dict:
    """Return config for one trigger. Returns {} if not found."""
    return _load().get(trigger, {})

def set_webhook(trigger: str, url: str, enabled: bool = True, label: str = ""):
    data = _load()
    if trigger not in data:
        data[trigger] = {"label": label or trigger}
    data[trigger]["url"] = url.strip()
    data[trigger]["enabled"] = enabled
    _save(data)

def clear_webhook(trigger: str):
    data = _load()
    if trigger in data:
        data[trigger]["url"] = ""
        data[trigger]["enabled"] = False
    _save(data)


# ── Payload builder ───────────────────────────────────────────────────────────

def _build_payload(trigger: str, lead: dict = None, extra: dict = None) -> dict:
    """
    Build the standard webhook payload.
    Schema matches intent-engine's ScrapeResult output — compatible with
    Zapier/Make/HubSpot field mapping.
    """
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = {
        "event": trigger,
        "triggered_at": now,
        "source": "LeadFinder",
    }

    if lead:
        # Flatten common fields to top level for easy Zapier/Make field mapping
        payload["lead"] = {
            "id":                  lead.get("id", ""),
            "company_name":        lead.get("name", ""),
            "website":             lead.get("website", ""),
            "phone":               lead.get("phone", ""),
            "email":               lead.get("email", ""),
            "address":             lead.get("address", ""),
            "category":            lead.get("category", ""),
            "stage":               lead.get("stage", ""),
            "score":               lead.get("score", 0),
            "decision_maker_name": (lead.get("decision_maker") or {}).get("name", lead.get("owner_name", "")),
            "decision_maker_title":(lead.get("decision_maker") or {}).get("title", ""),
            "tech_stack":          lead.get("tech_stack", ""),
            "social_handles":      lead.get("social_handles", {}),
            "tags":                lead.get("tags", []),
            "notes":               lead.get("notes", ""),
            "follow_up":           lead.get("follow_up", ""),
            "added_at":            lead.get("added_at", ""),
            "source":              lead.get("source", ""),
        }
        # CRM-style flat fields (HubSpot / Salesforce prefer flat)
        payload.update({
            "company_name":  lead.get("name", ""),
            "email":         lead.get("email", ""),
            "phone":         lead.get("phone", ""),
            "website":       lead.get("website", ""),
            "pipeline_stage": lead.get("stage", ""),
            "lead_score":    lead.get("score", 0),
        })

    if extra:
        payload.update(extra)

    return payload


# ── Delivery ──────────────────────────────────────────────────────────────────

def _log_delivery(trigger: str, url: str, success: bool, status_code: int = 0, error: str = ""):
    with _log_lock:
        _delivery_log.insert(0, {
            "trigger": trigger,
            "url": url[:60] + "..." if len(url) > 60 else url,
            "success": success,
            "status_code": status_code,
            "error": error,
            "at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
        if len(_delivery_log) > 200:
            del _delivery_log[200:]

def deliver(trigger: str, lead: dict = None, extra: dict = None) -> bool:
    """
    POST the payload to the configured webhook URL for this trigger.
    Fire-and-forget: failure is logged but never raises.

    Returns True if delivered successfully, False otherwise.
    """
    cfg = get_webhook(trigger)
    url = cfg.get("url", "").strip()
    if not url or not cfg.get("enabled"):
        return False

    payload = _build_payload(trigger, lead, extra)
    body = json.dumps(payload).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "LeadFinder/2.0",
                "X-LeadFinder-Event": trigger,
            },
            method="POST",
        )
        import ssl
        ctx = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            status = resp.status
            success = 200 <= status < 300
            _log_delivery(trigger, url, success, status)
            # Update fire count
            data = _load()
            if trigger in data:
                data[trigger]["last_fired"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                data[trigger]["fire_count"] = data[trigger].get("fire_count", 0) + 1
            _save(data)
            return success
    except Exception as ex:
        _log_delivery(trigger, url, False, error=str(ex))
        return False


def deliver_async(trigger: str, lead: dict = None, extra: dict = None):
    """Non-blocking webhook delivery — runs in a background thread."""
    threading.Thread(
        target=deliver, args=(trigger, lead, extra),
        daemon=True, name=f"webhook-{trigger}"
    ).start()


def on_stage_change(lead: dict, new_stage: str):
    """
    Called whenever a lead's pipeline stage changes.
    Fires the matching webhook trigger asynchronously.
    """
    trigger = STAGE_TRIGGERS.get(new_stage)
    if trigger:
        deliver_async(trigger, lead)


# ── Test delivery ─────────────────────────────────────────────────────────────

def test_delivery(trigger: str) -> dict:
    """Send a test payload to the configured webhook URL."""
    cfg = get_webhook(trigger)
    url = cfg.get("url", "").strip()
    if not url:
        return {"ok": False, "error": "No URL configured for this trigger"}

    test_lead = {
        "id": "test-001",
        "name": "Test Business Inc.",
        "website": "https://example.com",
        "email": "owner@example.com",
        "phone": "+1 555 000 0000",
        "address": "123 Main St, Anytown",
        "category": "Restaurant",
        "stage": "Interested",
        "score": 82,
        "owner_name": "Jane Smith",
        "decision_maker": {"name": "Jane Smith", "title": "Owner"},
        "tech_stack": "WordPress, Mailchimp",
        "tags": ["test", "leadfinder"],
        "notes": "This is a test payload from LeadFinder webhook test",
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "source": "Google Maps",
    }
    success = deliver(trigger, test_lead, {"_test": True})
    return {"ok": success, "url": url, "trigger": trigger}


# ── Patch db.update_lead_field to auto-fire webhooks on stage changes ─────────

def patch_db_for_webhooks():
    """
    Monkey-patch db.update_lead_field so stage changes auto-fire webhooks.
    Called once at startup by leadfinder.py.
    """
    import db as _db
    original = _db.update_lead_field

    def patched(lid, **kwargs):
        result = original(lid, **kwargs)
        new_stage = kwargs.get("stage") or (result or {}).get("stage")
        if new_stage and result:
            on_stage_change(result, new_stage)
        return result

    _db.update_lead_field = patched


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:

    if path == "/api/webhooks/list":
        return {"webhooks": _load()}

    if path == "/api/webhooks/configure":
        trigger = req.get("trigger", "")
        url     = req.get("url", "")
        enabled = bool(req.get("enabled", True))
        label   = req.get("label", "")
        if not trigger:
            return {"error": "trigger is required"}
        # Validate URL
        if url and not re.match(r"^https?://", url):
            return {"error": "URL must start with http:// or https://"}
        set_webhook(trigger, url, enabled, label)
        return {"ok": True, "trigger": trigger, "url": url}

    if path == "/api/webhooks/clear":
        clear_webhook(req.get("trigger", ""))
        return {"ok": True}

    if path == "/api/webhooks/test":
        return test_delivery(req.get("trigger", "custom"))

    if path == "/api/webhooks/deliver":
        # Manual trigger from frontend
        trigger = req.get("trigger", "custom")
        lead_id = req.get("lead_id", "")
        lead = None
        if lead_id:
            import db as _db
            lead = _db.get_lead(lead_id)
        success = deliver(trigger, lead, req.get("extra"))
        return {"ok": success}

    if path == "/api/webhooks/log":
        with _log_lock:
            return {"log": _delivery_log[:50]}

    return {"error": f"Unknown webhooks path: {path}"}
