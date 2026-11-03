"""
Daily assistant backend for LeadFinder.
Local JSON remains the fallback; when MONGODB_URI is configured, state is
also read from and written to MongoDB Atlas. This app is intentionally local.
"""
import json, os, threading, time, traceback
import leadfinder as LF

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
os.makedirs(DATA, exist_ok=True)
_lock = threading.RLock()
state = {"running": False, "log": [], "progress": ""}

# Load a simple local .env file for desktop use. Real environment variables win.
def _load_dotenv():
    path = os.path.join(BASE, ".env")
    try:
        with open(path, encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key, value = key.strip(), value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except FileNotFoundError:
        pass

_load_dotenv()

_mongo_client = None
_mongo_db = None
_mongo_error_logged = False

def _mongo():
    """Return the optional Atlas database; never make MongoDB mandatory."""
    global _mongo_client, _mongo_db, _mongo_error_logged
    uri = os.environ.get("MONGODB_URI", "").strip()
    if not uri:
        return None
    if _mongo_db is not None:
        return _mongo_db
    try:
        from pymongo import MongoClient
        _mongo_client = MongoClient(uri, serverSelectionTimeoutMS=3500,
                                   connectTimeoutMS=3500, appname="LeadFinder")
        _mongo_client.admin.command("ping")
        name = os.environ.get("MONGODB_DATABASE", "leadfinder").strip() or "leadfinder"
        _mongo_db = _mongo_client[name]
        return _mongo_db
    except Exception as exc:
        if not _mongo_error_logged:
            print("  [storage] MongoDB unavailable; using local JSON:", exc)
            _mongo_error_logged = True
        return None

def _path(n):
    return os.path.join(DATA, n + ".json")

def _cloud_value(name, value):
    # API credentials and provider pool settings stay on this computer.
    if name == "config" and isinstance(value, dict):
        return {k: value[k] for k in ("jobs", "runHour", "autopilot", "lastRun", "caps") if k in value}
    return value

def _local_config_secrets(default):
    try:
        with open(_path("config"), encoding="utf-8") as f:
            local = json.load(f)
        return {
            "keys": local.get("keys", default.get("keys", {})),
            "pool": local.get("pool", default.get("pool", [])),
        }
    except Exception:
        return {"keys": default.get("keys", {}), "pool": default.get("pool", [])}

def load(n, default):
    """Read Atlas first, then fall back to the existing local JSON file."""
    try:
        database = _mongo()
        if database is not None:
            doc = database.app_state.find_one({"_id": str(n)})
            if doc is not None:
                value = doc.get("value", default)
                if n == "config" and isinstance(value, dict):
                    value = {**value, **_local_config_secrets(default)}
                return value
    except Exception as exc:
        print("  [storage] MongoDB read failed; using JSON:", exc)
    try:
        with open(_path(n), encoding="utf-8") as f:
            value = json.load(f)
        # One-time migration: seed Atlas from existing local state.
        database = _mongo()
        if database is not None:
            try:
                database.app_state.update_one(
                    {"_id": str(n)},
                    {"$setOnInsert": {"value": _cloud_value(n, value), "updatedAt": time.time()}},
                    upsert=True,
                )
            except Exception as exc:
                print("  [storage] Could not migrate local state to MongoDB:", exc)
        return value
    except Exception:
        return default

def save(n, obj):
    """Write local JSON first, then mirror to Atlas when it is reachable."""
    with _lock:
        tmp = _path(n) + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(obj, f, ensure_ascii=False, indent=1)
        os.replace(tmp, _path(n))
        try:
            database = _mongo()
            if database is not None:
                database.app_state.replace_one(
                    {"_id": str(n)},
                    {"_id": str(n), "value": _cloud_value(n, obj), "updatedAt": time.time()},
                    upsert=True,
                )
        except Exception as exc:
            print("  [storage] MongoDB write failed; local JSON is safe:", exc)

DEFAULT_CFG = {
    "jobs": [], "runHour": 8, "autopilot": True, "lastRun": "",
    "caps": {"google": 900, "serpapi": 90},
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

def inbox(): return load("inbox", [])
def seen(): return set(load("seen", []))

def resolve(ids, extra_seen=()):
    with _lock:
        ids = set(ids)
        save("inbox", [l for l in inbox() if l["id"] not in ids])
        s = seen() | ids | set(extra_seen)
        save("seen", sorted(s))

def mark_seen(ids):
    with _lock:
        save("seen", sorted(seen() | set(ids)))

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
                    mark_seen([l["id"] for l in leads])
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
                hiring.daily()
        except Exception:
            log("Scheduler error: " + traceback.format_exc(limit=1))
        time.sleep(300)

def start():
    threading.Thread(target=_scheduler, daemon=True).start()

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
                c["keys"]["hunter"] = ""
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
    if path == "/api/assistant/inbox": return {"inbox": inbox()}
    if path == "/api/assistant/resolve":
        resolve(req.get("ids", []), req.get("seen", [])); return {"ok": True}
    if path == "/api/assistant/seen":
        mark_seen(req.get("ids", [])); return {"ok": True}
    if path == "/api/pool/complete":
        return ai_pool.complete(req.get("prompt", ""), c.get("pool"), req.get("system") or ai_pool.SYSTEM,
                                int(req.get("maxTokens", 900)))
    if path == "/api/pool/test": return ai_pool.test(req.get("cfg", {}))
    if path == "/api/pool/models": return {"models": ai_pool.list_models(req.get("cfg", {}))}
    if path == "/api/contacts/enrich": return contacts.enrich(req.get("website", ""))
    if path == "/api/contacts/verify": return {"results": [contacts.verify(e) for e in req.get("emails", [])[:50]]}
    if path == "/api/contacts/hunter": return contacts.hunter(req.get("domain", ""), c["keys"].get("hunter"))
    raise RuntimeError("Unknown endpoint")

def _safe_run(only):
    try: run_jobs(only)
    except Exception as ex: log(f"Run failed: {ex}")
