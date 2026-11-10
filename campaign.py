"""
campaign.py — Campaign Optimization & Feedback Loop for LeadFinder.

Built from scratch based on the Free-email-outreach-tool methodology (CogWorkLabs).
That repo is documentation-only; this is the actual implementation.

The methodology's 7 steps → what this module implements:
  Step 1 Define      → stored in strategy.py profiles
  Step 2 Research    → leadfinder.py / b2b.py / indeed.py
  Step 3 Validate    → emailverify.py / pipeline.py suppression
  Step 4 Personalize → ai_pool.py / outreach tab
  Step 5 Launch      → nichefinder.send_email() / db.py sequences
  Step 6 Route       → THIS MODULE: reply classification + auto-stage
  Step 7 Optimize    → THIS MODULE: metrics dashboard

Key features:
  - Campaign tracking (send / open / reply / meeting / won per campaign)
  - Reply classification: interested / referral / objection / unsubscribe / ooo / bounce
  - Auto-stop sequence on reply (matches OutLead philosophy)
  - Per-segment and per-copy-variant performance comparison
  - Campaign-level dashboard metrics
  - Webhook integration on positive replies

Storage: data/campaigns.json
"""
import json, os, re, threading, time, hashlib
import db

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
CAMPAIGNS_FILE = os.path.join(DATA, "campaigns.json")
_lock = threading.RLock()

# ── Reply categories (from Free-email-outreach-tool methodology) ──────────────
REPLY_CATEGORIES = ["interested", "referral", "objection", "unsubscribe", "ooo", "bounce", "unknown"]

# Stages that auto-stop sequence delivery
STOP_CATEGORIES = {"interested", "unsubscribe", "bounce"}

# Stage updates per reply category
CATEGORY_TO_STAGE = {
    "interested":  "Interested",
    "unsubscribe": "Not interested",
    "bounce":      "Not interested",
    "referral":    "Follow up",
    "objection":   "Follow up",
}

# ── Reply classifier (keyword + LLM fallback) ─────────────────────────────────

REPLY_PATTERNS = {
    "interested": re.compile(
        r"\b(interested|yes please|sounds good|tell me more|when can|let.?s talk|"
        r"book a call|schedule|demo|pricing|how much|quote|proposal|i.?d like to|"
        r"can you send|please send|would love|definitely|absolutely|great idea)\b", re.I),
    "referral": re.compile(
        r"\b(not the right person|forward|refer you to|colleague|contact|"
        r"speak with|my manager|our team|not my area|pass you on|cc.?ing)\b", re.I),
    "objection": re.compile(
        r"\b(not interested|no thanks|don.?t need|already have|using another|"
        r"budget|too expensive|not right now|maybe later|happy with|not a fit)\b", re.I),
    "unsubscribe": re.compile(
        r"\b(unsubscribe|remove me|opt.?out|stop emailing|don.?t (email|contact)|"
        r"take me off|no more emails|please stop|cease)\b", re.I),
    "ooo": re.compile(
        r"\b(out of office|on leave|away from (the )?office|back on|returning|"
        r"auto.?reply|automatic reply|will be back|on vacation|maternity)\b", re.I),
    "bounce": re.compile(
        r"\b(delivery failure|mailer.daemon|undeliverable|does not exist|"
        r"no such user|invalid address|address rejected|user unknown|"
        r"550|551|552|553|554)\b", re.I),
}

def classify_reply(subject: str, body: str) -> str:
    """
    Classify a reply email into one of 6 categories.
    Uses keyword patterns first; falls back to AI for ambiguous replies.
    """
    text = (subject + " " + body)[:3000]

    # Keyword pass
    for category, pattern in REPLY_PATTERNS.items():
        if pattern.search(text):
            return category

    # AI pass for ambiguous replies
    if len(text.strip()) > 20:
        try:
            import ai_pool, assistant
            prompt = f"""Classify this email reply into ONE of these categories:
interested | referral | objection | unsubscribe | ooo | bounce | unknown

Reply subject: {subject[:200]}
Reply body: {body[:800]}

Return ONLY the category name, nothing else."""
            result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=20)
            category = result.get("text", "").strip().lower()
            if category in REPLY_CATEGORIES:
                return category
        except Exception:
            pass

    return "unknown"


# ── Campaign storage ──────────────────────────────────────────────────────────

def _load_campaigns() -> dict:
    os.makedirs(DATA, exist_ok=True)
    try:
        with open(CAMPAIGNS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def _save_campaigns(data: dict):
    os.makedirs(DATA, exist_ok=True)
    with _lock:
        tmp = CAMPAIGNS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, CAMPAIGNS_FILE)

def _default_campaign(name: str, description: str = "") -> dict:
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    return {
        "name": name,
        "description": description,
        "created_at": now,
        "updated_at": now,
        "status": "active",   # active | paused | completed
        "metrics": {
            "sends":           0,
            "opens":           0,   # unreliable due to privacy protections — track anyway
            "replies":         0,
            "interested":      0,
            "referrals":       0,
            "objections":      0,
            "unsubscribes":    0,
            "bounces":         0,
            "ooo":             0,
            "meetings_booked": 0,
            "won":             0,
        },
        "variants": {},     # variant_name -> {sends, replies, interested}
        "segments": {},     # segment_name -> {sends, replies, interested}
        "lead_ids": [],
    }


# ── Campaign CRUD ─────────────────────────────────────────────────────────────

def create_campaign(name: str, description: str = "") -> dict:
    if not name:
        raise ValueError("Campaign name required")
    cid = hashlib.md5((name + time.strftime("%Y%m%d%H%M%S")).encode()).hexdigest()[:10]
    data = _load_campaigns()
    campaign = _default_campaign(name, description)
    campaign["id"] = cid
    data[cid] = campaign
    _save_campaigns(data)
    return campaign

def get_campaign(cid: str):
    return _load_campaigns().get(cid)

def list_campaigns() -> list:
    data = _load_campaigns()
    return sorted(data.values(), key=lambda c: c.get("created_at", ""), reverse=True)

def delete_campaign(cid: str):
    data = _load_campaigns()
    data.pop(cid, None)
    _save_campaigns(data)


# ── Metric recording ──────────────────────────────────────────────────────────

def record_send(cid: str, lead_id: str = "", variant: str = "", segment: str = ""):
    """Record that an email was sent in this campaign."""
    _increment(cid, "sends", lead_id, variant, segment)
    db.publish_event("campaign_send", {"campaign_id": cid, "lead_id": lead_id})

def record_open(cid: str, lead_id: str = ""):
    """Record an email open (tracking pixel fired)."""
    _increment(cid, "opens", lead_id)

def record_reply(cid: str, lead_id: str, subject: str, body: str,
                 variant: str = "", segment: str = "") -> str:
    """
    Record a reply, classify it, update lead stage, stop sequence if needed.
    Returns the reply category.
    """
    category = classify_reply(subject, body)
    _increment(cid, "replies", lead_id, variant, segment)

    # Increment category-specific counter
    metric_map = {
        "interested":  "interested",
        "referral":    "referrals",
        "objection":   "objections",
        "unsubscribe": "unsubscribes",
        "bounce":      "bounces",
        "ooo":         "ooo",
    }
    if category in metric_map:
        _increment(cid, metric_map[category])

    # Auto-update lead stage
    new_stage = CATEGORY_TO_STAGE.get(category)
    if new_stage and lead_id:
        db.update_lead_field(lead_id, stage=new_stage)
        db.log_outreach(lead_id, "email", subject, body, category, "in")

    # Auto-stop sequence if needed
    if category in STOP_CATEGORIES and lead_id:
        _cancel_sequences(lead_id)

    # Webhook on positive reply
    if category == "interested" and lead_id:
        try:
            import webhooks
            lead = db.get_lead(lead_id)
            webhooks.deliver_async("lead_interested", lead)
        except Exception:
            pass

    db.publish_event("campaign_reply", {
        "campaign_id": cid, "lead_id": lead_id, "category": category
    })
    return category

def record_meeting(cid: str, lead_id: str = ""):
    _increment(cid, "meetings_booked", lead_id)
    db.publish_event("campaign_meeting", {"campaign_id": cid, "lead_id": lead_id})

def record_won(cid: str, lead_id: str = ""):
    _increment(cid, "won", lead_id)
    if lead_id:
        db.update_lead_field(lead_id, stage="Won",
                             won_at=time.strftime("%Y-%m-%dT%H:%M:%S"))
        try:
            import webhooks
            lead = db.get_lead(lead_id)
            webhooks.deliver_async("lead_won", lead)
        except Exception:
            pass


def _increment(cid: str, metric: str, lead_id: str = "",
               variant: str = "", segment: str = ""):
    with _lock:
        data = _load_campaigns()
        if cid not in data:
            return
        c = data[cid]
        c["metrics"][metric] = c["metrics"].get(metric, 0) + 1
        c["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")

        if lead_id and lead_id not in c.get("lead_ids", []):
            c.setdefault("lead_ids", []).append(lead_id)

        if variant:
            c.setdefault("variants", {}).setdefault(variant, {"sends": 0, "replies": 0, "interested": 0})
            if metric in ("sends", "replies", "interested"):
                c["variants"][variant][metric] = c["variants"][variant].get(metric, 0) + 1

        if segment:
            c.setdefault("segments", {}).setdefault(segment, {"sends": 0, "replies": 0, "interested": 0})
            if metric in ("sends", "replies", "interested"):
                c["segments"][segment][metric] = c["segments"][segment].get(metric, 0) + 1

        _save_campaigns(data)


def _cancel_sequences(lead_id: str):
    """Cancel all pending sequence steps for a lead (stop-on-reply)."""
    try:
        with db._lock:
            with db._conn() as c:
                c.execute(
                    "UPDATE sequences SET status='cancelled' WHERE lead_id=? AND status='pending'",
                    (lead_id,)
                )
    except Exception:
        pass


# ── Computed metrics ──────────────────────────────────────────────────────────

def compute_rates(metrics: dict) -> dict:
    """
    Compute derived rates from raw counters.
    Primary signals: reply_rate, positive_rate, meeting_rate (not open rate —
    CogWorkLabs methodology explicitly deprioritizes open rate due to privacy).
    """
    sends = max(metrics.get("sends", 0), 1)
    return {
        "reply_rate":       round(metrics.get("replies", 0)         / sends * 100, 1),
        "positive_rate":    round(metrics.get("interested", 0)       / sends * 100, 1),
        "meeting_rate":     round(metrics.get("meetings_booked", 0)  / sends * 100, 1),
        "win_rate":         round(metrics.get("won", 0)              / sends * 100, 1),
        "unsubscribe_rate": round(metrics.get("unsubscribes", 0)     / sends * 100, 1),
        "bounce_rate":      round(metrics.get("bounces", 0)          / sends * 100, 1),
        "open_rate":        round(metrics.get("opens", 0)            / sends * 100, 1),
    }


def campaign_summary(cid: str) -> dict:
    """Full campaign summary with computed rates and variant/segment comparison."""
    c = get_campaign(cid)
    if not c:
        return {"error": "Campaign not found"}
    rates = compute_rates(c["metrics"])

    # Best performing variant
    best_variant = None
    best_variant_rate = -1
    for vname, vm in c.get("variants", {}).items():
        vsends = max(vm.get("sends", 0), 1)
        rate = vm.get("interested", 0) / vsends
        if rate > best_variant_rate:
            best_variant_rate = rate
            best_variant = vname

    # Best performing segment
    best_segment = None
    best_segment_rate = -1
    for sname, sm in c.get("segments", {}).items():
        ssends = max(sm.get("sends", 0), 1)
        rate = sm.get("interested", 0) / ssends
        if rate > best_segment_rate:
            best_segment_rate = rate
            best_segment = sname

    return {
        **c,
        "rates": rates,
        "best_variant": best_variant,
        "best_segment": best_segment,
        "insights": _generate_insights(c["metrics"], rates),
    }


def _generate_insights(metrics: dict, rates: dict) -> list:
    """Generate actionable text insights from campaign metrics."""
    insights = []
    sends = metrics.get("sends", 0)

    if sends < 20:
        insights.append("📊 Send to at least 20 leads before drawing conclusions from the data.")
    if rates["reply_rate"] < 2:
        insights.append("📧 Reply rate below 2% — try a more personal subject line or first sentence.")
    if rates["reply_rate"] >= 5:
        insights.append("🎉 Reply rate above 5% — this sequence is working. Scale it up.")
    if rates["bounce_rate"] > 5:
        insights.append("⚠️ Bounce rate above 5% — run your list through email verification.")
    if rates["unsubscribe_rate"] > 2:
        insights.append("🛑 Unsubscribe rate above 2% — your targeting or messaging may be off.")
    if rates["positive_rate"] > 0 and rates["meeting_rate"] == 0:
        insights.append("📞 People are interested but no meetings booked — add a direct calendar link to your CTA.")
    if metrics.get("interested", 0) > 0 and metrics.get("meetings_booked", 0) == 0:
        insights.append("🔗 Positive replies aren't converting to meetings — follow up faster (within 1 hour).")

    return insights


# ── Dashboard aggregate ───────────────────────────────────────────────────────

def all_campaigns_summary() -> dict:
    """Aggregated stats across all campaigns for the dashboard."""
    campaigns = list_campaigns()
    totals = {k: 0 for k in ["sends", "replies", "interested", "meetings_booked", "won",
                              "unsubscribes", "bounces"]}
    for c in campaigns:
        for k in totals:
            totals[k] += c.get("metrics", {}).get(k, 0)

    return {
        "campaign_count": len(campaigns),
        "totals": totals,
        "rates": compute_rates(totals),
        "campaigns": [
            {
                "id": c.get("id", ""),
                "name": c.get("name", ""),
                "status": c.get("status", ""),
                "sends": c.get("metrics", {}).get("sends", 0),
                "reply_rate": compute_rates(c.get("metrics", {}))["reply_rate"],
                "positive_rate": compute_rates(c.get("metrics", {}))["positive_rate"],
                "updated_at": c.get("updated_at", ""),
            }
            for c in campaigns
        ],
    }


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:

    if path == "/api/campaign/create":
        try:
            c = create_campaign(req.get("name", ""), req.get("description", ""))
            return {"campaign": c}
        except ValueError as ex:
            return {"error": str(ex)}

    if path == "/api/campaign/list":
        return {"campaigns": list_campaigns()}

    if path == "/api/campaign/get":
        return {"campaign": campaign_summary(req.get("id", ""))}

    if path == "/api/campaign/delete":
        delete_campaign(req.get("id", ""))
        return {"ok": True}

    if path == "/api/campaign/all":
        return all_campaigns_summary()

    if path == "/api/campaign/record/send":
        record_send(req.get("campaign_id", ""), req.get("lead_id", ""),
                    req.get("variant", ""), req.get("segment", ""))
        return {"ok": True}

    if path == "/api/campaign/record/open":
        record_open(req.get("campaign_id", ""), req.get("lead_id", ""))
        return {"ok": True}

    if path == "/api/campaign/record/reply":
        category = record_reply(
            req.get("campaign_id", ""), req.get("lead_id", ""),
            req.get("subject", ""), req.get("body", ""),
            req.get("variant", ""), req.get("segment", ""),
        )
        return {"ok": True, "category": category}

    if path == "/api/campaign/record/meeting":
        record_meeting(req.get("campaign_id", ""), req.get("lead_id", ""))
        return {"ok": True}

    if path == "/api/campaign/record/won":
        record_won(req.get("campaign_id", ""), req.get("lead_id", ""))
        return {"ok": True}

    if path == "/api/campaign/classify":
        # Standalone reply classifier (no campaign tracking)
        category = classify_reply(req.get("subject", ""), req.get("body", ""))
        return {"category": category}

    if path == "/api/campaign/status":
        cid = req.get("id", "")
        status = req.get("status", "active")
        with _lock:
            data = _load_campaigns()
            if cid in data:
                data[cid]["status"] = status
                data[cid]["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
                _save_campaigns(data)
        return {"ok": True}

    return {"error": f"Unknown campaign path: {path}"}
