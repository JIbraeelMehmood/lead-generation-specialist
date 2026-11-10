"""
inbound.py — Inbound Lead Capture & Personalized Onboarding for LeadFinder.

Ported from AI-Lead-Capture-Onboarding (n8n + Groq + Gmail workflow).

The n8n workflow's 4 nodes are replicated here as pure Python:
  Node 1: Form Trigger        → POST /api/inbound/capture  (any channel: form, webhook, chat)
  Node 2: Google Sheets log   → db.py upsert_lead()  +  optional sheets_export append
  Node 3: AI Agent (Groq LLM) → ai_pool.complete()  with identical system prompt
  Node 4: Gmail send          → nichefinder.send_email() via your SMTP config

Extra: inbound now also handles webhook POSTs from external forms (Typeform, Tally,
Webflow, GoHighLevel, etc.) by normalising their field names.

Stored in db.py leads table with source="inbound".
"""
import json, os, re, time, threading
import leadfinder as LF
import db

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
INBOUND_CFG_FILE = os.path.join(DATA, "inbound_config.json")
_lock = threading.RLock()


# ── Config helpers ────────────────────────────────────────────────────────────

DEFAULT_CFG = {
    "enabled": True,
    "auto_reply": True,
    "smtp": {},          # same schema as nichefinder SMTP config
    "welcome_subject": "Welcome! We received your message",
    "your_name": "",
    "your_company": "",
    "your_service": "",
    "tone": "professional",   # professional | friendly | energetic
    "reply_categories": {
        "interested": True,
        "referral": True,
        "objection": True,
        "unsubscribe": True,
        "ooo": False,
        "bounce": False,
    },
}

def _load_cfg():
    os.makedirs(DATA, exist_ok=True)
    try:
        with open(INBOUND_CFG_FILE, encoding="utf-8") as f:
            d = json.load(f)
            out = dict(DEFAULT_CFG)
            out.update(d)
            return out
    except Exception:
        return dict(DEFAULT_CFG)

def _save_cfg(cfg: dict):
    os.makedirs(DATA, exist_ok=True)
    with _lock:
        tmp = INBOUND_CFG_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        os.replace(tmp, INBOUND_CFG_FILE)


# ── Field normaliser — maps common webhook field names to our schema ──────────

FIELD_ALIASES = {
    # name variations
    "full_name": "name", "fullname": "name", "first_name": "name",
    "your_name": "name", "contact_name": "name",
    # email variations
    "email_address": "email", "contact_email": "email", "e_mail": "email",
    # phone
    "phone_number": "phone", "mobile": "phone", "tel": "phone",
    "whatsapp": "phone", "mobile_number": "phone",
    # profession / job title
    "job_title": "profession", "title": "profession", "role": "profession",
    "occupation": "profession", "position": "profession",
    # goal / message
    "learning_goal": "goal", "learning goal / project idea": "goal",
    "project_idea": "goal", "message": "goal", "how_can_we_help": "goal",
    "inquiry": "goal", "question": "goal", "notes": "goal",
    # company
    "company_name": "company", "organisation": "company", "organization": "company",
    "business": "company", "business_name": "company",
    # website
    "url": "website", "website_url": "website", "site": "website",
}

def _normalise_fields(raw: dict) -> dict:
    """Normalise arbitrary webhook / form field names to our canonical schema."""
    out = {}
    for k, v in raw.items():
        clean = k.lower().strip().replace(" ", "_").replace("-", "_")
        canonical = FIELD_ALIASES.get(clean, clean)
        out[canonical] = v
    # Fallback: use first non-empty string field as name if name not found
    if not out.get("name"):
        for v in raw.values():
            if isinstance(v, str) and len(v) > 1:
                out["name"] = v
                break
    return out


# ── AI welcome email generation ───────────────────────────────────────────────

def _generate_welcome_email(fields: dict, cfg: dict) -> dict:
    """
    Generate a personalized welcome / onboarding email using the AI pool.
    Directly mirrors the n8n workflow's AI Agent system prompt logic.
    """
    name       = fields.get("name", "there")
    profession = fields.get("profession", fields.get("title", "professional"))
    goal       = fields.get("goal", fields.get("message", "get started"))
    company    = fields.get("company", "")
    your_name  = cfg.get("your_name", "The Team")
    your_co    = cfg.get("your_company", "our company")
    your_svc   = cfg.get("your_service", "our services")
    tone       = cfg.get("tone", "professional")

    tone_instruction = {
        "professional": "professional, warm, and concise",
        "friendly":     "friendly, conversational, and encouraging",
        "energetic":    "energetic, exciting, and tech-forward — treat them like a future superstar",
    }.get(tone, "professional and warm")

    system = f"""You are an expert copywriter for {your_co}. Write a highly personalized welcome email
to a new lead or customer who just reached out.

Your writing style: {tone_instruction}
Your company: {your_co}
Your service/product: {your_svc}
Sign-off: {your_name}

Guidelines:
1. Use their name "{name}" in the opening
2. Acknowledge their background as a {profession or "professional"}
3. Validate their goal: "{goal}" — explain how {your_svc} helps them achieve it
4. Include ONE clear call-to-action (e.g. "Book a free call", "Reply with any questions")
5. Keep it under 130 words — crisp and actionable
6. Never use jargon or generic phrases like "hope this email finds you well"
7. Sign off exactly as: Best regards,\\n{your_name}"""

    user_msg = f"""Name: {name}
Profession: {profession}
Company: {company}
Goal/Message: {goal}

Write the welcome email now."""

    subject_default = cfg.get("welcome_subject", f"Welcome, {name}!")

    try:
        import ai_pool, assistant
        result = ai_pool.complete(user_msg, assistant.cfg().get("pool"), max_tokens=400,
                                  system=system)
        body = result.get("text", "").strip()
        # Try to extract subject from first line if AI wrote "Subject: ..."
        lines = body.split("\n", 2)
        subject = subject_default
        if lines and re.match(r"^(subject|subj)[:\s]", lines[0], re.I):
            subject = re.sub(r"^(subject|subj)[:\s]+", "", lines[0], flags=re.I).strip()
            body = "\n".join(lines[1:]).strip()
        return {"subject": subject, "body": body, "ok": True}
    except Exception as ex:
        # Fallback: minimal template
        body = (f"Hi {name},\n\nThank you for reaching out! We've received your message "
                f"about \"{goal}\" and will be in touch shortly.\n\nBest regards,\n{your_name}")
        return {"subject": subject_default, "body": body, "ok": False, "error": str(ex)}


# ── SMTP send ─────────────────────────────────────────────────────────────────

def _send_welcome(to_email: str, subject: str, body: str, cfg: dict) -> dict:
    """Send the welcome email via the configured SMTP."""
    smtp_cfg = cfg.get("smtp") or {}
    if not smtp_cfg.get("host") or not smtp_cfg.get("user"):
        return {"sent": False, "error": "SMTP not configured — go to Settings > Outreach SMTP"}
    try:
        import nichefinder as NF
        NF.send_email(smtp_cfg, to_email, subject, body)
        return {"sent": True}
    except Exception as ex:
        return {"sent": False, "error": str(ex)}


# ── Main capture function ─────────────────────────────────────────────────────

def capture(raw_fields: dict, source_label: str = "inbound") -> dict:
    """
    Process an inbound lead:
      1. Normalise field names
      2. Save to SQLite (db.py)
      3. Generate AI welcome email
      4. Send via SMTP (if enabled)
      5. Return result dict

    raw_fields: any dict of form/webhook fields
    source_label: e.g. "inbound:form", "inbound:webhook", "inbound:typeform"
    """
    cfg = _load_cfg()
    fields = _normalise_fields(raw_fields)

    name     = fields.get("name", "Unknown")
    email    = fields.get("email", "")
    phone    = fields.get("phone", "")
    company  = fields.get("company", "")
    website  = fields.get("website", "")
    goal     = fields.get("goal", "")
    profession = fields.get("profession", "")

    # Build a lead record compatible with db.py schema
    import hashlib
    lid = "inbound:" + hashlib.md5(
        (email or name + str(time.time())).encode()
    ).hexdigest()[:10]

    lead = {
        "id": lid,
        "name": name,
        "source": source_label,
        "category": profession or "Inbound Lead",
        "phone": phone,
        "email": email,
        "website": website,
        "notes": goal,
        "owner_name": name,
        "stage": "New",
        "priority": "high",
        "tags": ["inbound", "auto-captured"],
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "social": "",
        "address": fields.get("address", ""),
        "search_query": source_label,
    }
    if company:
        lead["name"] = company
        lead["owner_name"] = name

    # Persist to SQLite
    saved = db.upsert_lead(lead)
    db.publish_event("inbound_lead_captured", {
        "lead_id": lid, "name": name, "email": email, "source": source_label
    })

    result = {
        "lead_id": lid,
        "lead": saved,
        "email_sent": False,
        "email_result": {},
        "welcome_email": {},
    }

    # Generate and send welcome email
    if email and cfg.get("auto_reply"):
        email_data = _generate_welcome_email(fields, cfg)
        result["welcome_email"] = email_data
        if cfg.get("smtp", {}).get("host"):
            send_result = _send_welcome(email, email_data["subject"], email_data["body"], cfg)
            result["email_sent"] = send_result.get("sent", False)
            result["email_result"] = send_result
            if send_result.get("sent"):
                db.log_outreach(lid, "email", email_data["subject"],
                                email_data["body"], "sent", "out")
                db.update_lead_field(lid, stage="Contacted",
                                     contacted_at=time.strftime("%Y-%m-%dT%H:%M:%S"))

    return result


# ── Reply classifier ──────────────────────────────────────────────────────────
# From Free-email-outreach-tool methodology: 6 reply categories

REPLY_KEYWORDS = {
    "interested": re.compile(
        r"\b(interested|yes|sure|sounds good|tell me more|when can|let's talk|"
        r"book|schedule|call|demo|pricing|how much|quote|proposal)\b", re.I),
    "referral": re.compile(
        r"\b(not the right person|forward|refer|colleague|contact|"
        r"speak with|my manager|our team|not my area)\b", re.I),
    "objection": re.compile(
        r"\b(not interested|no thanks|don't need|already have|using another|"
        r"budget|too expensive|not right now|maybe later)\b", re.I),
    "unsubscribe": re.compile(
        r"\b(unsubscribe|remove|stop|opt.?out|don't (email|contact)|"
        r"take me off|no more emails)\b", re.I),
    "ooo": re.compile(
        r"\b(out of office|on leave|away from|back on|returning|"
        r"auto.?reply|automatic reply)\b", re.I),
    "bounce": re.compile(
        r"\b(delivery failure|mailer.daemon|undeliverable|"
        r"does not exist|no such user|invalid address)\b", re.I),
}

def classify_reply(text: str) -> str:
    """
    Classify an inbound reply into one of 6 categories.
    Used by IMAP monitor to auto-update lead stages.
    Returns: "interested" | "referral" | "objection" | "unsubscribe" | "ooo" | "bounce" | "unknown"
    """
    if not text:
        return "unknown"
    t = text[:2000]
    for category, pattern in REPLY_KEYWORDS.items():
        if pattern.search(t):
            return category
    return "unknown"


# ── Inbound log ────────────────────────────────────────────────────────────────

def list_inbound(limit: int = 100) -> list:
    """Return recent inbound leads from the SQLite DB."""
    return db.get_leads(search=None, limit=limit, offset=0)


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:

    if path == "/api/inbound/capture":
        # Main capture endpoint — accepts any form/webhook POST
        source = req.pop("_source", "inbound:form")
        return capture(req, source_label=source)

    if path == "/api/inbound/webhook":
        # Generic webhook receiver — normalises whatever fields are sent
        source = req.pop("_source", "inbound:webhook")
        return capture(req, source_label=source)

    if path == "/api/inbound/classify":
        text = req.get("text", "")
        category = classify_reply(text)
        return {"category": category}

    if path == "/api/inbound/config":
        if req:
            cfg = _load_cfg()
            cfg.update({k: v for k, v in req.items() if k in DEFAULT_CFG})
            _save_cfg(cfg)
            return {"ok": True, "config": cfg}
        return {"config": _load_cfg()}

    if path == "/api/inbound/list":
        return {"leads": list_inbound(int(req.get("limit", 100)))}

    if path == "/api/inbound/preview":
        # Generate a preview welcome email without sending or saving
        cfg = _load_cfg()
        cfg_override = req.get("config", {})
        cfg.update(cfg_override)
        fields = _normalise_fields(req.get("fields", req))
        email_data = _generate_welcome_email(fields, cfg)
        return email_data

    return {"error": f"Unknown inbound path: {path}"}
