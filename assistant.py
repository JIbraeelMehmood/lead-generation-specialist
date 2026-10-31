"""
Daily assistant back end for LeadFinder:
  * local JSON store in ./data (config, inbox, seen ids, usage)
  * free-quota guard for Google Places / SerpApi
  * autopilot: runs your saved searches once a day and collects NEW leads into an inbox
"""
import json, os, threading, time, traceback
import leadfinder as LF

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)
_lock = threading.RLock()
state = {"running": False, "log": [], "progress": ""}

def _path(n): return os.path.join(DATA, n + ".json")
def load(n, default):
    try:
        with open(_path(n), encoding="utf-8") as f: return json.load(f)
    except Exception:
        return default
def save(n, obj):
    with _lock:
        tmp = _path(n) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(n))

DEFAULT_CFG = {
    "jobs": [], "runHour": 8, "autopilot": True, "lastRun": "",
    "caps": {"google": 900, "serpapi": 90},   # monthly safety caps (Google Enterprise free ≈1,000; set yours)
    "keys": {"google": "", "serp": "", "hunter": "", "cse": "", "cseId": "",
             "pagespeed": "", "ch": "", "sheetsCredsPath": ""},
    "pool": [],
}
def cfg():
    c = load("config", {})
    out = json.loads(json.dumps(DEFAULT_CFG))
    out.update(c)
    return out

def log(msg):
    line = time.strftime("%H:%M ") + msg
    state["log"] = ([line] + state["log"])[:60]
    print("  [assistant] " + msg)

# ---------------------------------------------------------------- quota guard
def usage():
    u = load("usage", {})
    m = time.strftime("%Y-%m")
    if u.get("month") != m: u = {"month": m, "google": 0, "serpapi": 0}
    return u

def spend(kind, n=1):
    with _lock:
        u = usage()
        cap = cfg()["caps"].get(kind, 0)
        if cap and u.get(kind, 0) + n > cap:
            raise RuntimeError(f"Monthly safety cap reached for {kind}: {u.get(kind,0)}/{cap} calls. "
                               f"Raise it in Settings > Free quota guard if you accept possible charges.")
        u[kind] = u.get(kind, 0) + n
        save("usage", u)

# ---------------------------------------------------------------- inbox
def inbox():  return load("inbox", [])
def seen():   return set(load("seen", []))

def resolve(ids, extra_seen=()):
    with _lock:
        ids = set(ids)
        save("inbox", [l for l in inbox() if l["id"] not in ids])
        s = seen() | ids | set(extra_seen)
        save("seen", sorted(s))

def mark_seen(ids):
    with _lock:
        save("seen", sorted(seen() | set(ids)))

# ---------------------------------------------------------------- autopilot
def _no_site(l):
    w = (l.get("website") or "").lower()
    return not w or any(s in w for s in ("facebook.com", "instagram.com", "business.site", "linktr.ee"))

def run_jobs(only=None):
    if state["running"]:
        raise RuntimeError("Autopilot is already running.")
    state["running"] = True
    c = cfg()
    try:
        jobs = [j for j in c["jobs"] if j.get("enabled", True) and (not only or j["id"] in only)]
        total_new = 0
        for i, j in enumerate(jobs, 1):
            state["progress"] = f"{i}/{len(jobs)}: {j['niche']} in {j['city']}"
            try:
                src = j.get("source", "google")
                if src == "google":
                    leads = LF.google_search(c["keys"].get("google"), j["niche"], j["city"], j.get("pages", 1))
                elif src == "serpapi":
                    leads = LF.serpapi_search(c["keys"].get("serp"), j["niche"], j["city"], j.get("pages", 1))
                else:
                    leads = LF.osm_search(j["niche"], j["city"])
                s = seen()
                fresh = [l for l in leads if l["id"] not in s and (j.get("filter") == "all" or _no_site(l)
                         or (j.get("filter") == "weak"))]
                if j.get("minReviews"):
                    fresh = [l for l in fresh if (l.get("reviews") or 0) >= int(j["minReviews"]) or l["source"] == "OpenStreetMap"]
                if j.get("filter") == "weak":
                    import contacts
                    keep = []
                    for l in fresh:
                        if _no_site(l): keep.append(l); continue
                        a = LF.audit_site(l["website"])
                        if a["score"] >= 20:
                            l["audit"] = a
                            e = contacts.enrich(l["website"])
                            if e["emails"]: l["email"] = e["emails"][0]["email"]
                            l["emailsFound"] = [x["email"] for x in e["emails"]]
                            l["contactPage"] = e["contactPage"]
                            keep.append(l)
                    fresh = keep
                stamp = time.strftime("%Y-%m-%d")
                for l in fresh:
                    l["foundAt"] = stamp; l["job"] = f"{j['niche']} in {j['city']}"
                with _lock:
                    save("inbox", fresh + inbox())
                    mark_seen([l["id"] for l in leads])   # never show the same business twice
                total_new += len(fresh)
                log(f"{j['niche']} in {j['city']}: {len(leads)} checked, {len(fresh)} new")
            except Exception as ex:
                log(f"{j['niche']} in {j['city']}: FAILED: {ex}")
        c = cfg(); c["lastRun"] = time.strftime("%Y-%m-%d"); save("config", c)
        log(f"Autopilot finished: {total_new} new leads in your inbox.")
        return total_new
    finally:
        state["running"] = False
        state["progress"] = ""

def _scheduler():
    time.sleep(20)
    while True:
        try:
            c = cfg()
            if c.get("autopilot") and c["jobs"] and c.get("lastRun") != time.strftime("%Y-%m-%d") \
               and time.localtime().tm_hour >= int(c.get("runHour", 8)) and not state["running"]:
                log("Daily autopilot starting.")
                run_jobs()
            if c.get("autopilot") and time.localtime().tm_hour >= int(c.get("runHour", 8)):
                import hiring
                hiring.daily()          # one hiring-posts check per day (it skips itself if done)
        except Exception:
            log("Scheduler error: " + traceback.format_exc(limit=1))
        time.sleep(300)

def start():
    threading.Thread(target=_scheduler, daemon=True).start()

# ---------------------------------------------------------------- API
def handle(path, req):
    import ai_pool, contacts
    c = cfg()
    if path == "/api/assistant/config":
        if req.get("save"):
            new = req["save"]
            for k in ("jobs", "runHour", "autopilot", "caps", "pool"):
                if k in new: c[k] = new[k]
            if "keys" in new: c["keys"].update({k: v for k, v in new["keys"].items() if v is not None})
            if str(c["keys"].get("hunter", "")).startswith("AIza"):
                c["keys"]["hunter"] = ""   # a Google key pasted into the Hunter field by mistake
            save("config", c)
        u = usage()
        return {"config": c, "usage": u, "providers": ai_pool.PROVIDERS}
    if path == "/api/assistant/status":
        return {"running": state["running"], "progress": state["progress"], "log": state["log"],
                "lastRun": c.get("lastRun"), "inboxCount": len(inbox()), "usage": usage(),
                "caps": c["caps"], "ai": ai_pool.status(c.get("pool"))}
    if path == "/api/assistant/run":
        threading.Thread(target=lambda: _safe_run(req.get("only")), daemon=True).start()
        return {"started": True}
    if path == "/api/assistant/inbox":
        return {"inbox": inbox()}
    if path == "/api/assistant/resolve":
        resolve(req.get("ids", []), req.get("seen", []))
        return {"ok": True}
    if path == "/api/assistant/seen":
        mark_seen(req.get("ids", []))
        return {"ok": True}
    if path == "/api/pool/complete":
        return ai_pool.complete(req.get("prompt", ""), c.get("pool"), req.get("system") or ai_pool.SYSTEM,
                                int(req.get("maxTokens", 900)))
    if path == "/api/pool/test":
        return ai_pool.test(req.get("cfg", {}))
    if path == "/api/pool/models":
        return {"models": ai_pool.list_models(req.get("cfg", {}))}
    if path == "/api/contacts/enrich":
        return contacts.enrich(req.get("website", ""))
    if path == "/api/contacts/verify":
        return {"results": [contacts.verify(e) for e in req.get("emails", [])[:50]]}
    if path == "/api/contacts/hunter":
        return contacts.hunter(req.get("domain", ""), c["keys"].get("hunter"))
    raise RuntimeError("Unknown endpoint")

def _safe_run(only):
    try: run_jobs(only)
    except Exception as ex: log(f"Run failed: {ex}")
