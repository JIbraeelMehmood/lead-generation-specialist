"""
voice_agent.py — AI Voice Call Agent for LeadFinder.

Integrates with n8n-ai-call-agent (Vapi + Twilio + n8n workflow).

The n8n workflow handles all the telephony — this module is the bridge:
  1. LeadFinder calls POST /api/voice/call with lead phone + context
  2. This module POSTs to the configured n8n webhook URL with the lead data
  3. n8n creates a Vapi call, holds the conversation, writes transcript to Sheets
  4. When done, n8n POSTs back to LeadFinder /api/voice/result with call outcome
  5. LeadFinder updates the lead stage and logs the call

The n8n workflow from the repo (25 nodes) handles:
  - Calling the lead via Vapi + Twilio
  - AI conversation (the voice agent)
  - Email extraction from speech (e.g. "tugui dragos at gmail dot com")
  - Transcript + summary → Google Sheets
  - Slack notification on every call

You can also use this without n8n by calling Vapi directly (direct mode).

Setup:
  1. Import the n8n workflow from n8n-ai-call-agent/ into your n8n instance
  2. Configure n8n webhook URL in LeadFinder Settings → Voice
  3. OR set Vapi API key for direct mode

Stored in data/voice_calls.json
"""
import json, os, re, threading, time
import leadfinder as LF
import db

DATA  = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CALLS_FILE = os.path.join(DATA, "voice_calls.json")
CFG_FILE   = os.path.join(DATA, "voice_config.json")
_lock = threading.RLock()

DEFAULT_CFG = {
    "mode":          "n8n",         # "n8n" | "vapi_direct"
    "n8n_webhook":   "",            # n8n trigger webhook URL
    "vapi_api_key":  "",            # for direct Vapi mode
    "vapi_phone_id": "",            # Vapi phone number ID
    "vapi_assistant_id": "",        # pre-configured Vapi assistant ID
    "result_webhook": "",           # LeadFinder public URL for n8n to call back
    "your_name":     "",
    "your_company":  "",
    "script_tone":   "professional",  # professional | friendly | energetic
    "language":      "English",
    "enabled":       False,
}

CALL_OUTCOMES = {
    "answered_interested": "Interested",
    "answered_not_interested": "Not interested",
    "answered_callback": "Follow up",
    "no_answer": "No answer",
    "voicemail": "No answer",
    "error": "No answer",
}


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


# ── Calls log ─────────────────────────────────────────────────────────────────

def _load_calls():
    try:
        with open(CALLS_FILE, encoding="utf-8") as f: return json.load(f)
    except Exception: return []

def _save_call(call: dict):
    with _lock:
        calls = _load_calls()
        # Update if exists, else append
        updated = False
        for i, c in enumerate(calls):
            if c.get("id") == call.get("id"):
                calls[i] = call; updated = True; break
        if not updated:
            calls.insert(0, call)
        calls = calls[:500]
        with open(CALLS_FILE, "w", encoding="utf-8") as f: json.dump(calls, f, indent=2)


# ── Build call script / context ───────────────────────────────────────────────

def _build_call_context(lead: dict, cfg: dict) -> dict:
    """Build the context payload sent to n8n / Vapi with lead + script info."""
    name    = lead.get("name", "")
    phone   = lead.get("phone", "")
    email   = lead.get("email", "")
    website = lead.get("website", "")
    category = lead.get("category", "business")

    # Try to load knowledge base context
    try:
        import knowledge
        kb = knowledge.engine()
        your_co    = kb.get_company_info().get("name", "") or cfg.get("your_company", "")
        your_name  = kb.get_founder_info().get("name", "") or cfg.get("your_name", "")
        services   = ", ".join(kb.get_approved_services()[:3]) or "our services"
    except Exception:
        your_co    = cfg.get("your_company", "")
        your_name  = cfg.get("your_name", "")
        services   = "our services"

    return {
        "lead_id":        lead.get("id", ""),
        "phone":          phone,
        "lead_name":      name,
        "lead_category":  category,
        "lead_website":   website,
        "lead_email":     email,
        "your_name":      your_name,
        "your_company":   your_co,
        "services":       services,
        "language":       cfg.get("language", "English"),
        "script_tone":    cfg.get("script_tone", "professional"),
        "result_webhook": cfg.get("result_webhook", ""),
    }


# ── n8n mode: trigger the workflow via webhook ────────────────────────────────

def _call_via_n8n(lead: dict, cfg: dict) -> dict:
    """POST call context to the n8n trigger webhook."""
    webhook_url = cfg.get("n8n_webhook", "").strip()
    if not webhook_url:
        return {"error": "n8n webhook URL not configured. Add it in Settings → Voice."}

    context = _build_call_context(lead, cfg)
    call_id = f"call-{int(time.time() * 1000)}"
    context["call_id"] = call_id

    # Save pending call record
    call_record = {
        "id": call_id,
        "lead_id": lead.get("id", ""),
        "phone": lead.get("phone", ""),
        "lead_name": lead.get("name", ""),
        "status": "queued",
        "mode": "n8n",
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "transcript": "",
        "summary": "",
        "email_extracted": "",
        "outcome": "",
    }
    _save_call(call_record)
    db.publish_event("voice_call_queued", {"call_id": call_id, "lead_id": lead.get("id", "")})

    try:
        result = LF.http_json(webhook_url, context, {"Content-Type": "application/json"}, timeout=30)
        call_record["status"] = "dialing"
        _save_call(call_record)
        db.publish_event("voice_call_dialing", {"call_id": call_id})
        return {"ok": True, "call_id": call_id, "n8n_response": result}
    except Exception as ex:
        call_record["status"] = "error"
        call_record["error"] = str(ex)
        _save_call(call_record)
        return {"error": str(ex), "call_id": call_id}


# ── Vapi direct mode ──────────────────────────────────────────────────────────

def _call_via_vapi(lead: dict, cfg: dict) -> dict:
    """Call directly via Vapi API (no n8n needed)."""
    api_key    = cfg.get("vapi_api_key", "").strip()
    phone_id   = cfg.get("vapi_phone_id", "").strip()
    asst_id    = cfg.get("vapi_assistant_id", "").strip()

    if not api_key:
        return {"error": "Vapi API key not configured"}
    if not phone_id:
        return {"error": "Vapi phone number ID not configured"}

    phone = lead.get("phone", "")
    if not phone:
        return {"error": "Lead has no phone number"}

    context = _build_call_context(lead, cfg)
    call_id  = f"vapi-{int(time.time() * 1000)}"

    # Build Vapi call payload
    payload = {
        "phoneNumberId": phone_id,
        "customer": {
            "number": phone,
            "name": lead.get("name", ""),
        },
        "metadata": {"call_id": call_id, "lead_id": lead.get("id", "")},
    }
    if asst_id:
        payload["assistantId"] = asst_id
    else:
        # Build an inline assistant from knowledge base context
        payload["assistant"] = _build_vapi_assistant(context, cfg)

    call_record = {
        "id": call_id,
        "lead_id": lead.get("id", ""),
        "phone": phone,
        "lead_name": lead.get("name", ""),
        "status": "queued",
        "mode": "vapi_direct",
        "queued_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "transcript": "",
        "summary": "",
        "email_extracted": "",
        "outcome": "",
    }
    _save_call(call_record)

    try:
        result = LF.http_json(
            "https://api.vapi.ai/call",
            payload,
            {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        call_record["status"] = "dialing"
        call_record["vapi_id"] = result.get("id", "")
        _save_call(call_record)
        db.publish_event("voice_call_dialing", {"call_id": call_id, "vapi_id": result.get("id", "")})
        return {"ok": True, "call_id": call_id, "vapi_call_id": result.get("id", "")}
    except Exception as ex:
        call_record["status"] = "error"
        call_record["error"] = str(ex)
        _save_call(call_record)
        return {"error": str(ex)}

def _build_vapi_assistant(context: dict, cfg: dict) -> dict:
    """Build an inline Vapi assistant config from the knowledge base context."""
    tone_map = {
        "professional": "professional, clear and respectful",
        "friendly":     "friendly, warm and conversational",
        "energetic":    "energetic, enthusiastic and direct",
    }
    tone = tone_map.get(cfg.get("script_tone", "professional"), "professional")
    lang = context.get("language", "English")
    name = context.get("your_name", "Alex")
    co   = context.get("your_company", "our company")
    svc  = context.get("services", "digital services")
    lead = context.get("lead_name", "")

    system_prompt = f"""You are {name}, calling on behalf of {co}.
You are calling {lead} to briefly introduce our {svc} and see if they might be interested.

Tone: {tone}
Language: {lang}

Guidelines:
- Keep it under 2 minutes
- Ask one question at a time
- If they give their email, repeat it back to confirm ("so that's john at gmail dot com, correct?")
- If not interested, thank them and say goodbye
- If interested, offer to send information by email
- If they say stop/no/not interested, end the call politely immediately
- Never be pushy or robotic"""

    return {
        "name": f"{name} from {co}",
        "firstMessage": f"Hello! Am I speaking with someone from {lead}? This is {name} from {co}, I had a quick question for you.",
        "model": {"provider": "openai", "model": "gpt-4o-mini",
                  "messages": [{"role": "system", "content": system_prompt}]},
        "voice": {"provider": "openai", "voiceId": "nova"},
        "recordingEnabled": True,
        "transcriber": {"provider": "deepgram", "language": "en-US"},
    }


# ── Handle call result callback (from n8n or Vapi webhook) ───────────────────

def handle_result(payload: dict) -> dict:
    """
    Called when n8n or Vapi sends back call results.
    Updates the call record and lead pipeline stage.
    """
    call_id  = payload.get("call_id", "")
    lead_id  = payload.get("lead_id", "")
    outcome  = payload.get("outcome", "no_answer")     # answered_interested | answered_not_interested | no_answer | etc.
    transcript = payload.get("transcript", "")
    summary    = payload.get("summary", "")
    email_extracted = payload.get("email_extracted", "")

    # Extract email from speech transcript if not provided
    if not email_extracted and transcript:
        email_extracted = _extract_email_from_speech(transcript)

    # Find and update call record
    calls = _load_calls()
    for c in calls:
        if c.get("id") == call_id or (lead_id and c.get("lead_id") == lead_id):
            c["status"] = "completed"
            c["outcome"] = outcome
            c["transcript"] = transcript
            c["summary"] = summary
            c["email_extracted"] = email_extracted
            c["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            break
    with _lock:
        calls = calls[:500]
        with open(CALLS_FILE, "w", encoding="utf-8") as f: json.dump(calls, f, indent=2)

    # Update lead stage
    if lead_id:
        new_stage = CALL_OUTCOMES.get(outcome, "No answer")
        db.update_lead_field(lead_id, stage=new_stage)
        db.log_outreach(lead_id, "call", f"Call: {outcome}", transcript[:500] if transcript else "", "sent")
        if email_extracted:
            db.update_lead_field(lead_id, email=email_extracted)
        try:
            import webhooks
            lead = db.get_lead(lead_id)
            if outcome == "answered_interested" and lead:
                webhooks.deliver_async("lead_interested", lead)
        except Exception:
            pass

    db.publish_event("voice_call_completed", {
        "call_id": call_id, "lead_id": lead_id, "outcome": outcome,
        "email": email_extracted,
    })
    return {"ok": True, "outcome": outcome, "email": email_extracted}


# ── Email extraction from speech transcript ───────────────────────────────────

def _extract_email_from_speech(text: str) -> str:
    """
    Extract an email address spoken aloud.
    Handles: "john at gmail dot com", "j.smith at yahoo dot co dot uk"
    Ported from n8n-ai-call-agent Extract Email node logic.
    """
    # First try direct email pattern
    direct = re.search(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", text)
    if direct:
        return direct.group(0).lower()

    # Spoken form: "word AT word DOT word"
    spoken = re.search(
        r"([A-Za-z0-9][\w.\-]*)\s+(?:at|@)\s+([A-Za-z0-9][\w.\-]*)\s+(?:dot|\.)\s+([A-Za-z]{2,}(?:\s+dot\s+[A-Za-z]{2,})?)",
        text, re.I
    )
    if spoken:
        local  = spoken.group(1).replace(" ", "").lower()
        domain = spoken.group(2).replace(" ", "").lower()
        tld    = re.sub(r"\s+dot\s+", ".", spoken.group(3)).replace(" ", "").lower()
        return f"{local}@{domain}.{tld}"

    return ""


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/voice/call":
        lead_id = req.get("lead_id", "")
        lead = None
        if lead_id:
            lead = db.get_lead(lead_id)
        if not lead:
            lead = req.get("lead", req)   # allow passing lead dict directly

        cfg = _load_cfg()
        if not cfg.get("enabled"):
            return {"error": "Voice calling not enabled. Configure it in Settings → Voice."}

        phone = lead.get("phone", "")
        if not phone:
            return {"error": "Lead has no phone number"}

        if cfg["mode"] == "vapi_direct":
            return _call_via_vapi(lead, cfg)
        else:
            return _call_via_n8n(lead, cfg)

    if path == "/api/voice/result":
        # Callback from n8n / Vapi
        return handle_result(req)

    if path == "/api/voice/calls":
        calls = _load_calls()
        limit = int(req.get("limit", 50))
        return {"calls": calls[:limit]}

    if path == "/api/voice/config":
        if req:
            cfg = _load_cfg()
            for k in DEFAULT_CFG:
                if k in req: cfg[k] = req[k]
            _save_cfg(cfg)
            return {"ok": True, "config": cfg}
        return {"config": _load_cfg()}

    if path == "/api/voice/status":
        cfg = _load_cfg()
        calls = _load_calls()
        today = time.strftime("%Y-%m-%d")
        return {
            "enabled":     cfg.get("enabled"),
            "mode":        cfg.get("mode"),
            "n8n_configured": bool(cfg.get("n8n_webhook")),
            "vapi_configured": bool(cfg.get("vapi_api_key")),
            "calls_today": sum(1 for c in calls if c.get("queued_at", "").startswith(today)),
            "config":      cfg,
        }

    return {"error": f"Unknown voice path: {path}"}
