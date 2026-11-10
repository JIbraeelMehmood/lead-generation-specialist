"""
jobs.py — Background job worker for LeadFinder.

Replaces the blocking synchronous task model. Long-running operations
(bulk enrichment, batch scraping, B2B hunt, deep scans) are submitted as
tasks to the SQLite queue (db.py) and executed in a thread pool here.

The worker runs as a daemon thread started by leadfinder.py at startup.
Jobs emit SSE events (db.publish_event) so the frontend can show live progress.

Supported task types
  bulk_enrich    — find email + verify + tech-stack + social handles for a list of leads
  bulk_audit     — website audit + PageSpeed for a list of leads
  bulk_score     — run the opportunity engine for a list of leads
  deep_scan      — Playwright deep scan for extra Maps data (optional, needs playwright)
  b2b_hunt       — B2B international buyer discovery (from b2b-buyer-discovery logic)
  decision_maker — LLM decision-maker extraction for a list of leads
  send_sequence  — scheduled 3-step email sequence sender
"""

import threading, time, traceback
from concurrent.futures import ThreadPoolExecutor, as_completed

import db

_worker_thread = None
_pool = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lf-job")


# ── Job handlers ──────────────────────────────────────────────────────────────

def _run_bulk_enrich(task: dict) -> dict:
    """Find emails, tech stack, social handles for a batch of leads."""
    payload = task["payload"]
    leads = payload.get("leads", [])
    results = {}
    for i, lead in enumerate(leads):
        lid = lead.get("id", "")
        website = lead.get("website", "")
        db.update_task(task["id"], progress=i, status="running")
        db.publish_event("task_progress", {
            "task_id": task["id"], "step": i, "total": len(leads),
            "current": lead.get("name", ""),
        })
        if not website:
            results[lid] = {"error": "no website"}
            continue
        try:
            import leadfinder as LF
            import contacts, enrich as E
            # Email
            found = LF.find_emails(website)
            emails = found.get("emails", [])
            # Social handles
            social = E.social_handles(website)
            # Tech stack
            tech = E.tech_stack(website)
            # Decision maker (quick, no LLM)
            dm = E.quick_decision_maker(website)
            update = {
                "email": emails[0] if emails else lead.get("email", ""),
                "social_handles": social,
                "tech_stack": ", ".join(tech) if tech else "",
                "decision_maker": dm,
            }
            db.update_lead_field(lid, **update)
            results[lid] = {"ok": True, "email": update["email"], "social": social, "tech": tech}
            db.publish_event("lead_enriched", {"lead_id": lid, **update})
        except Exception as ex:
            results[lid] = {"error": str(ex)}
    return {"results": results, "count": len(leads)}


def _run_bulk_audit(task: dict) -> dict:
    """Run website audit on a batch of leads."""
    import leadfinder as LF
    payload = task["payload"]
    leads = payload.get("leads", [])
    results = {}
    for i, lead in enumerate(leads):
        lid = lead.get("id", "")
        website = lead.get("website", "")
        db.update_task(task["id"], progress=i, status="running")
        db.publish_event("task_progress", {"task_id": task["id"], "step": i, "total": len(leads)})
        if not website:
            results[lid] = {"error": "no website"}
            continue
        try:
            audit = LF.audit_site(website)
            db.update_lead_field(lid, audit_data=audit, score=audit.get("score", 0))
            results[lid] = audit
            db.publish_event("lead_audited", {"lead_id": lid, "score": audit.get("score", 0)})
        except Exception as ex:
            results[lid] = {"error": str(ex)}
    return {"results": results}


def _run_bulk_score(task: dict) -> dict:
    """Run the full opportunity engine on a batch of leads."""
    import opportunities as OPP
    payload = task["payload"]
    leads = payload.get("leads", [])
    results = {}
    for i, lead in enumerate(leads):
        lid = lead.get("id", "")
        db.update_task(task["id"], progress=i, status="running")
        db.publish_event("task_progress", {"task_id": task["id"], "step": i, "total": len(leads)})
        try:
            result = OPP.score_lead(lead)
            db.update_lead_field(lid, bp_score=result.get("score", 0),
                                 opportunities=result.get("opportunities", []))
            results[lid] = result
            db.publish_event("lead_scored", {"lead_id": lid, "score": result.get("score", 0)})
        except Exception as ex:
            results[lid] = {"error": str(ex)}
    return {"results": results}


def _run_decision_maker(task: dict) -> dict:
    """LLM-based decision-maker extraction for a batch of leads."""
    import enrich as E
    payload = task["payload"]
    leads = payload.get("leads", [])
    results = {}
    for i, lead in enumerate(leads):
        lid = lead.get("id", "")
        website = lead.get("website", "")
        db.update_task(task["id"], progress=i, status="running")
        db.publish_event("task_progress", {"task_id": task["id"], "step": i, "total": len(leads)})
        if not website:
            results[lid] = {"error": "no website"}
            continue
        try:
            dm = E.llm_decision_maker(website, lead.get("name", ""))
            db.update_lead_field(lid, decision_maker=dm,
                                 owner_name=dm.get("name", lead.get("owner_name", "")))
            results[lid] = dm
            db.publish_event("lead_dm_found", {"lead_id": lid, **dm})
        except Exception as ex:
            results[lid] = {"error": str(ex)}
    return {"results": results}


def _run_b2b_hunt(task: dict) -> dict:
    """B2B international buyer discovery — logic from b2b-buyer-discovery."""
    import b2b
    payload = task["payload"]
    db.update_task(task["id"], status="running")
    db.publish_event("task_progress", {"task_id": task["id"], "step": 0, "total": 1,
                                       "current": "Searching global buyers..."})
    try:
        leads = b2b.hunt(
            keyword=payload.get("keyword", ""),
            markets=payload.get("markets", []),
            min_score=int(payload.get("min_score", 5)),
            max_per_keyword=int(payload.get("max_per_keyword", 20)),
        )
        # Persist to DB
        for lead in leads:
            db.upsert_lead(lead)
        db.publish_event("b2b_hunt_done", {"count": len(leads)})
        return {"leads": leads, "count": len(leads)}
    except Exception as ex:
        return {"error": str(ex), "leads": []}


def _run_send_sequence(task: dict) -> dict:
    """Send the next pending step in a 3-email sequence."""
    import nichefinder as NF
    payload = task["payload"]
    smtp_cfg = payload.get("smtp", {})
    lead_id = payload.get("lead_id", "")
    steps = db.get_sequences(lead_id)
    pending = [s for s in steps if s["status"] == "pending"]
    if not pending:
        return {"message": "No pending steps"}
    step = pending[0]
    lead = db.get_lead(lead_id)
    if not lead:
        return {"error": "Lead not found"}
    try:
        NF.send_email(smtp_cfg, lead.get("email", ""),
                      step["subject"], step["body"])
        with db._lock:
            with db._conn() as c:
                now = time.strftime("%Y-%m-%dT%H:%M:%S")
                c.execute("UPDATE sequences SET status='sent', sent_at=? WHERE id=?",
                          (now, step["id"]))
        db.log_outreach(lead_id, "email", step["subject"], step["body"], "sent")
        db.publish_event("sequence_sent", {"lead_id": lead_id, "step": step["step"]})
        return {"sent": True, "step": step["step"]}
    except Exception as ex:
        with db._lock:
            with db._conn() as c:
                c.execute("UPDATE sequences SET status='failed' WHERE id=?", (step["id"],))
        return {"error": str(ex)}


_HANDLERS = {
    "bulk_enrich": _run_bulk_enrich,
    "bulk_audit": _run_bulk_audit,
    "bulk_score": _run_bulk_score,
    "decision_maker": _run_decision_maker,
    "b2b_hunt": _run_b2b_hunt,
    "send_sequence": _run_send_sequence,
}


# ── Worker loop ───────────────────────────────────────────────────────────────

def _work_one(task: dict):
    tid = task["id"]
    ttype = task["type"]
    db.update_task(tid, status="running")
    db.publish_event("task_started", {"task_id": tid, "type": ttype})
    try:
        handler = _HANDLERS.get(ttype)
        if handler is None:
            raise RuntimeError(f"Unknown task type: {ttype}")
        result = handler(task)
        db.update_task(tid, status="done", result=result, progress=task.get("total", 0))
        db.publish_event("task_done", {"task_id": tid, "type": ttype,
                                       "count": result.get("count", 0) if isinstance(result, dict) else 0})
    except Exception as ex:
        err = traceback.format_exc(limit=3)
        db.update_task(tid, status="failed", error=str(ex) + "\n" + err)
        db.publish_event("task_failed", {"task_id": tid, "error": str(ex)})


def _worker_loop():
    while True:
        try:
            queued = db.list_tasks(status="queued", limit=1)
            if queued:
                task = queued[0]
                _pool.submit(_work_one, task)
        except Exception:
            pass
        time.sleep(2)


def start():
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_thread = threading.Thread(target=_worker_loop, daemon=True, name="lf-worker")
    _worker_thread.start()


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/jobs/enqueue":
        tid = db.enqueue_task(req.get("type", ""), req.get("payload", {}))
        start()  # make sure worker is running
        return {"task_id": tid}

    if path == "/api/jobs/status":
        return {"task": db.get_task(req.get("task_id", ""))}

    if path == "/api/jobs/list":
        return {"tasks": db.list_tasks(req.get("status"))}

    if path == "/api/jobs/cancel":
        tid = req.get("task_id", "")
        db.update_task(tid, status="failed", error="Cancelled by user")
        return {"ok": True}

    return {"error": f"Unknown jobs path: {path}"}
