"""
db.py — SQLite persistence layer for LeadFinder.

Replaces browser localStorage as the CRM store. All lead data, pipeline stages,
notes, follow-up dates and outreach history survive browser clears and reboots.

Uses only Python stdlib (sqlite3 is built-in). Falls back gracefully if anything
goes wrong — the system still runs, it just can't persist to DB.

Tables
  leads          — the main CRM: one row per tracked lead
  outreach_log   — email/whatsapp/call events per lead
  sequences      — 3-step email sequence definitions
  tasks          — background job queue (see jobs.py)
  events         — real-time event stream for SSE (see sse.py)
"""
import json, os, sqlite3, threading, time

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "leads.db")
_lock = threading.RLock()

# ── Schema ────────────────────────────────────────────────────────────────────

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS leads (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT '',
    source      TEXT DEFAULT '',
    category    TEXT DEFAULT '',
    address     TEXT DEFAULT '',
    phone       TEXT DEFAULT '',
    email       TEXT DEFAULT '',
    website     TEXT DEFAULT '',
    social      TEXT DEFAULT '',
    rating      REAL,
    reviews     INTEGER DEFAULT 0,
    maps_url    TEXT DEFAULT '',
    lat         REAL,
    lng         REAL,
    score       INTEGER DEFAULT 0,
    priority    TEXT DEFAULT 'normal',
    stage       TEXT DEFAULT 'New',
    follow_up   TEXT DEFAULT '',
    notes       TEXT DEFAULT '',
    owner_name  TEXT DEFAULT '',
    tech_stack  TEXT DEFAULT '',
    social_handles TEXT DEFAULT '{}',
    decision_maker TEXT DEFAULT '{}',
    audit_data  TEXT DEFAULT '{}',
    opportunities TEXT DEFAULT '[]',
    bp_score    INTEGER DEFAULT 0,
    tags        TEXT DEFAULT '[]',
    search_query TEXT DEFAULT '',
    added_at    TEXT DEFAULT '',
    updated_at  TEXT DEFAULT '',
    contacted_at TEXT DEFAULT '',
    won_at      TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS outreach_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    channel     TEXT NOT NULL,  -- email | whatsapp | call | linkedin | social
    direction   TEXT DEFAULT 'out',  -- out | in
    subject     TEXT DEFAULT '',
    body        TEXT DEFAULT '',
    status      TEXT DEFAULT 'sent',  -- sent | draft | failed | replied | unsubscribed
    reply_text  TEXT DEFAULT '',
    reply_at    TEXT DEFAULT '',
    created_at  TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS sequences (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id     TEXT NOT NULL REFERENCES leads(id) ON DELETE CASCADE,
    step        INTEGER NOT NULL DEFAULT 1,
    send_after_days INTEGER DEFAULT 0,
    subject     TEXT DEFAULT '',
    body        TEXT DEFAULT '',
    status      TEXT DEFAULT 'pending',  -- pending | sent | skipped | cancelled
    created_at  TEXT DEFAULT '',
    sent_at     TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    type        TEXT NOT NULL,  -- enrich | audit | email | call | whatsapp | scrape | b2b_hunt
    payload     TEXT DEFAULT '{}',
    status      TEXT DEFAULT 'queued',  -- queued | running | done | failed
    progress    INTEGER DEFAULT 0,
    total       INTEGER DEFAULT 0,
    result      TEXT DEFAULT '{}',
    error       TEXT DEFAULT '',
    created_at  TEXT DEFAULT '',
    started_at  TEXT DEFAULT '',
    finished_at TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    type        TEXT NOT NULL,
    data        TEXT DEFAULT '{}',
    created_at  TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_leads_stage ON leads(stage);
CREATE INDEX IF NOT EXISTS idx_leads_score ON leads(score DESC);
CREATE INDEX IF NOT EXISTS idx_outreach_lead ON outreach_log(lead_id);
CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at);
"""

def _conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    c = sqlite3.connect(DB_PATH, timeout=30, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init():
    """Create all tables. Safe to call multiple times."""
    with _lock:
        with _conn() as c:
            c.executescript(SCHEMA)

# ── Leads CRUD ────────────────────────────────────────────────────────────────

def _row_to_lead(row):
    if row is None:
        return None
    d = dict(row)
    for field in ("social_handles", "decision_maker", "audit_data", "opportunities", "tags"):
        try:
            d[field] = json.loads(d.get(field) or ("[]" if field in ("opportunities", "tags") else "{}"))
        except Exception:
            d[field] = [] if field in ("opportunities", "tags") else {}
    return d

def upsert_lead(lead: dict) -> dict:
    """Insert or update a lead. Returns the saved lead dict."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    lid = lead.get("id") or ""
    if not lid:
        return lead

    with _lock:
        with _conn() as c:
            existing = c.execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone()
            if existing:
                # Merge: only update fields that are non-empty in the incoming lead
                merged = dict(existing)
                for k, v in lead.items():
                    if v not in (None, "", [], {}):
                        if k in ("social_handles", "decision_maker", "audit_data", "opportunities", "tags"):
                            merged[k] = json.dumps(v)
                        else:
                            merged[k] = v
                merged["updated_at"] = now
                c.execute("""
                    UPDATE leads SET
                        name=:name, source=:source, category=:category, address=:address,
                        phone=:phone, email=:email, website=:website, social=:social,
                        rating=:rating, reviews=:reviews, maps_url=:maps_url, lat=:lat, lng=:lng,
                        score=:score, priority=:priority, stage=:stage, follow_up=:follow_up,
                        notes=:notes, owner_name=:owner_name, tech_stack=:tech_stack,
                        social_handles=:social_handles, decision_maker=:decision_maker,
                        audit_data=:audit_data, opportunities=:opportunities, bp_score=:bp_score,
                        tags=:tags, search_query=:search_query, updated_at=:updated_at,
                        contacted_at=:contacted_at, won_at=:won_at
                    WHERE id=:id
                """, merged)
            else:
                vals = {
                    "id": lid,
                    "name": lead.get("name", ""),
                    "source": lead.get("source", ""),
                    "category": lead.get("category", ""),
                    "address": lead.get("address", ""),
                    "phone": lead.get("phone", ""),
                    "email": lead.get("email", ""),
                    "website": lead.get("website", ""),
                    "social": lead.get("social", ""),
                    "rating": lead.get("rating"),
                    "reviews": lead.get("reviews", 0),
                    "maps_url": lead.get("mapsUrl", lead.get("maps_url", "")),
                    "lat": lead.get("lat"),
                    "lng": lead.get("lng"),
                    "score": lead.get("score", 0),
                    "priority": lead.get("priority", "normal"),
                    "stage": lead.get("stage", "New"),
                    "follow_up": lead.get("follow_up", lead.get("followUp", "")),
                    "notes": lead.get("notes", ""),
                    "owner_name": lead.get("owner_name", lead.get("ownerName", "")),
                    "tech_stack": lead.get("tech_stack", lead.get("techStack", "")),
                    "social_handles": json.dumps(lead.get("social_handles", lead.get("socialHandles", {}))),
                    "decision_maker": json.dumps(lead.get("decision_maker", lead.get("decisionMaker", {}))),
                    "audit_data": json.dumps(lead.get("audit_data", lead.get("audit", {}))),
                    "opportunities": json.dumps(lead.get("opportunities", [])),
                    "bp_score": lead.get("bp_score", lead.get("bpScore", 0)),
                    "tags": json.dumps(lead.get("tags", [])),
                    "search_query": lead.get("searchQuery", lead.get("search_query", "")),
                    "added_at": lead.get("added_at", now),
                    "updated_at": now,
                    "contacted_at": lead.get("contacted_at", ""),
                    "won_at": lead.get("won_at", ""),
                }
                c.execute("""
                    INSERT INTO leads
                    (id,name,source,category,address,phone,email,website,social,rating,reviews,
                     maps_url,lat,lng,score,priority,stage,follow_up,notes,owner_name,tech_stack,
                     social_handles,decision_maker,audit_data,opportunities,bp_score,tags,
                     search_query,added_at,updated_at,contacted_at,won_at)
                    VALUES
                    (:id,:name,:source,:category,:address,:phone,:email,:website,:social,:rating,:reviews,
                     :maps_url,:lat,:lng,:score,:priority,:stage,:follow_up,:notes,:owner_name,:tech_stack,
                     :social_handles,:decision_maker,:audit_data,:opportunities,:bp_score,:tags,
                     :search_query,:added_at,:updated_at,:contacted_at,:won_at)
                """, vals)
    return get_lead(lid)

def get_lead(lid: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM leads WHERE id=?", (lid,)).fetchone()
    return _row_to_lead(row)

def get_leads(stage=None, search=None, limit=500, offset=0) -> list:
    clauses, params = [], []
    if stage and stage != "All":
        clauses.append("stage=?"); params.append(stage)
    if search:
        clauses.append("(name LIKE ? OR address LIKE ? OR category LIKE ? OR email LIKE ?)")
        s = f"%{search}%"
        params.extend([s, s, s, s])
    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params += [limit, offset]
    with _conn() as c:
        rows = c.execute(f"SELECT * FROM leads {where} ORDER BY score DESC, added_at DESC LIMIT ? OFFSET ?",
                         params).fetchall()
    return [_row_to_lead(r) for r in rows]

def count_leads(stage=None) -> int:
    clause = "WHERE stage=?" if stage and stage != "All" else ""
    params = [stage] if stage and stage != "All" else []
    with _conn() as c:
        return c.execute(f"SELECT COUNT(*) FROM leads {clause}", params).fetchone()[0]

def update_lead_field(lid: str, **kwargs):
    """Patch one or more fields on a lead by id."""
    if not kwargs:
        return get_lead(lid)
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    kwargs["updated_at"] = now
    # JSON-encode complex fields
    for f in ("social_handles", "decision_maker", "audit_data", "opportunities", "tags"):
        if f in kwargs and not isinstance(kwargs[f], str):
            kwargs[f] = json.dumps(kwargs[f])
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [lid]
    with _lock:
        with _conn() as c:
            c.execute(f"UPDATE leads SET {sets} WHERE id=?", vals)
    return get_lead(lid)

def delete_lead(lid: str):
    with _lock:
        with _conn() as c:
            c.execute("DELETE FROM leads WHERE id=?", (lid,))

def pipeline_stats() -> dict:
    stages = ["New", "Contacted", "No answer", "Interested", "Follow up",
              "Proposal sent", "Won", "Not interested"]
    with _conn() as c:
        counts = dict(c.execute("SELECT stage, COUNT(*) FROM leads GROUP BY stage").fetchall())
    return {s: counts.get(s, 0) for s in stages}

def import_leads(leads: list) -> dict:
    added, updated = 0, 0
    for lead in leads:
        if not lead.get("id") or not lead.get("name"):
            continue
        existing = get_lead(lead["id"])
        upsert_lead(lead)
        if existing:
            updated += 1
        else:
            added += 1
    return {"added": added, "updated": updated, "total": len(leads)}

# ── Outreach log ──────────────────────────────────────────────────────────────

def log_outreach(lead_id: str, channel: str, subject: str = "", body: str = "",
                 status: str = "sent", direction: str = "out") -> int:
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _lock:
        with _conn() as c:
            cur = c.execute("""
                INSERT INTO outreach_log (lead_id,channel,direction,subject,body,status,created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (lead_id, channel, direction, subject, body, status, now))
            return cur.lastrowid

def get_outreach_log(lead_id: str) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM outreach_log WHERE lead_id=? ORDER BY created_at DESC", (lead_id,)
        ).fetchall()
    return [dict(r) for r in rows]

def mark_reply(log_id: int, reply_text: str = "", status: str = "replied"):
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _lock:
        with _conn() as c:
            c.execute("UPDATE outreach_log SET status=?, reply_text=?, reply_at=? WHERE id=?",
                      (status, reply_text, now, log_id))

# ── Sequences ─────────────────────────────────────────────────────────────────

def save_sequence(lead_id: str, steps: list) -> list:
    """Save a 3-step sequence for a lead. Replaces any existing pending steps."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _lock:
        with _conn() as c:
            c.execute("DELETE FROM sequences WHERE lead_id=? AND status='pending'", (lead_id,))
            ids = []
            for i, step in enumerate(steps, 1):
                cur = c.execute("""
                    INSERT INTO sequences (lead_id,step,send_after_days,subject,body,status,created_at)
                    VALUES (?,?,?,?,?,?,?)
                """, (lead_id, i, step.get("delay_days", (i-1)*3),
                      step.get("subject", ""), step.get("body", ""), "pending", now))
                ids.append(cur.lastrowid)
    return ids

def get_sequences(lead_id: str) -> list:
    with _conn() as c:
        rows = c.execute("SELECT * FROM sequences WHERE lead_id=? ORDER BY step", (lead_id,)).fetchall()
    return [dict(r) for r in rows]

# ── Background task queue ─────────────────────────────────────────────────────

import uuid

def enqueue_task(task_type: str, payload: dict) -> str:
    """Add a task to the queue. Returns the task id."""
    tid = str(uuid.uuid4())[:12]
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    with _lock:
        with _conn() as c:
            c.execute("""
                INSERT INTO tasks (id,type,payload,status,progress,total,created_at)
                VALUES (?,?,?,?,?,?,?)
            """, (tid, task_type, json.dumps(payload), "queued", 0,
                  payload.get("total", len(payload.get("leads", []))), now))
    return tid

def get_task(tid: str):
    with _conn() as c:
        row = c.execute("SELECT * FROM tasks WHERE id=?", (tid,)).fetchone()
    if not row:
        return None
    d = dict(row)
    for f in ("payload", "result"):
        try:
            d[f] = json.loads(d.get(f) or "{}")
        except Exception:
            d[f] = {}
    return d

def update_task(tid: str, **kwargs):
    if not kwargs:
        return
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    for f in ("payload", "result"):
        if f in kwargs and not isinstance(kwargs[f], str):
            kwargs[f] = json.dumps(kwargs[f])
    if kwargs.get("status") == "running" and "started_at" not in kwargs:
        kwargs["started_at"] = now
    if kwargs.get("status") in ("done", "failed") and "finished_at" not in kwargs:
        kwargs["finished_at"] = now
    sets = ", ".join(f"{k}=?" for k in kwargs)
    vals = list(kwargs.values()) + [tid]
    with _lock:
        with _conn() as c:
            c.execute(f"UPDATE tasks SET {sets} WHERE id=?", vals)

def list_tasks(status=None, limit=50) -> list:
    if status:
        rows = _conn().execute("SELECT * FROM tasks WHERE status=? ORDER BY created_at DESC LIMIT ?",
                               (status, limit)).fetchall()
    else:
        rows = _conn().execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    out = []
    for row in rows:
        d = dict(row)
        for f in ("payload", "result"):
            try:
                d[f] = json.loads(d.get(f) or "{}")
            except Exception:
                d[f] = {}
        out.append(d)
    return out

# ── SSE event bus ─────────────────────────────────────────────────────────────

_sse_listeners: list = []
_sse_lock = threading.Lock()

def publish_event(etype: str, data: dict):
    """Broadcast an event to all SSE listeners and persist it briefly."""
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    payload = json.dumps({"type": etype, "data": data, "ts": now})
    with _sse_lock:
        dead = []
        for q in _sse_listeners:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for q in dead:
            _sse_listeners.remove(q)
    # Keep last 200 events in DB for reconnect replay
    try:
        with _conn() as c:
            c.execute("INSERT INTO events (type,data,created_at) VALUES (?,?,?)",
                      (etype, json.dumps(data), now))
            c.execute("DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 200)")
    except Exception:
        pass

def subscribe_events():
    """Return a queue that receives future SSE payloads."""
    import queue
    q = queue.Queue(maxsize=200)
    with _sse_lock:
        _sse_listeners.append(q)
    return q

def recent_events(limit=50) -> list:
    with _conn() as c:
        rows = c.execute(
            "SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
    return [{"id": r["id"], "type": r["type"],
             "data": json.loads(r["data"] or "{}"), "ts": r["created_at"]} for r in reversed(rows)]

# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    # --- leads ---
    if path == "/api/db/leads":
        leads = get_leads(
            stage=req.get("stage"),
            search=req.get("search"),
            limit=int(req.get("limit", 500)),
            offset=int(req.get("offset", 0)),
        )
        return {"leads": leads, "total": count_leads(req.get("stage"))}

    if path == "/api/db/lead":
        lid = req.get("id", "")
        return {"lead": get_lead(lid)}

    if path == "/api/db/upsert":
        lead = req.get("lead", {})
        return {"lead": upsert_lead(lead)}

    if path == "/api/db/update":
        lid = req.get("id", "")
        patch = {k: v for k, v in req.items() if k != "id"}
        return {"lead": update_lead_field(lid, **patch)}

    if path == "/api/db/delete":
        delete_lead(req.get("id", ""))
        return {"ok": True}

    if path == "/api/db/import":
        return import_leads(req.get("leads", []))

    if path == "/api/db/stats":
        return {"pipeline": pipeline_stats(), "total": count_leads()}

    # --- outreach ---
    if path == "/api/db/outreach/log":
        return {"log": get_outreach_log(req.get("lead_id", ""))}

    if path == "/api/db/outreach/add":
        row_id = log_outreach(
            req.get("lead_id", ""), req.get("channel", "email"),
            req.get("subject", ""), req.get("body", ""),
            req.get("status", "sent"), req.get("direction", "out"),
        )
        return {"id": row_id}

    # --- sequences ---
    if path == "/api/db/sequence/save":
        ids = save_sequence(req.get("lead_id", ""), req.get("steps", []))
        return {"ids": ids}

    if path == "/api/db/sequence/get":
        return {"steps": get_sequences(req.get("lead_id", ""))}

    # --- tasks ---
    if path == "/api/db/tasks":
        return {"tasks": list_tasks(req.get("status"))}

    if path == "/api/db/task":
        return {"task": get_task(req.get("id", ""))}

    if path == "/api/db/task/enqueue":
        tid = enqueue_task(req.get("type", ""), req.get("payload", {}))
        return {"id": tid}

    # --- events ---
    if path == "/api/db/events":
        return {"events": recent_events(int(req.get("limit", 50)))}

    return {"error": f"Unknown db path: {path}"}


# ── Init on import ────────────────────────────────────────────────────────────
init()
