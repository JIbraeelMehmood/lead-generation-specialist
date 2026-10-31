"""
Prospecting pipeline helpers for LeadFinder (from the Lead Generator Blueprint):

  * Suppression / do-not-contact list  - honor opt-outs across imports and exports.
  * Canonical-domain deduplication      - detect the same company across search runs.
  * Blueprint configuration              - daily target, project value, evidence &
    approval requirements.

Standard library only; data stored in ./data.
"""
import json, re, urllib.parse
import leadfinder as LF

DEFAULT_BP = {
    "daily_candidate_target": 75,
    "project_value_min_usd": 300,
    "project_value_max_usd": 1000,
    "require_human_approval_before_outreach": True,
    "require_evidence_for_confirmed_opportunity": True,
    "store_source_url_and_timestamp": True,
    "deduplicate_by": "canonical_domain",
    "respect_opt_outs": True,
}


# ---------------------------------------------------------------- store
def _load(name, default):
    import assistant
    return assistant.load(name, default)

def _save(name, obj):
    import assistant
    assistant.save(name, obj)


# ---------------------------------------------------------------- canonical domain / dedup
_TRACK = re.compile(r"^(www|m|mobile|web|amp)\.")
_STRIP_PARAMS = ("utm_", "gclid", "fbclid", "ref", "source", "_ga")

def canonical_domain(url_or_domain):
    u = (url_or_domain or "").strip()
    if not u:
        return ""
    if "://" not in u:
        u = "http://" + u
    try:
        host = urllib.parse.urlparse(u).hostname or ""
    except Exception:
        host = u
    host = _TRACK.sub("", host.lower())
    # drop country-style multi-part TLDs handled by netloc; keep simple host
    return host

def _domain(lead):
    return canonical_domain(lead.get("website") or lead.get("domain") or lead.get("url") or "")


# ---------------------------------------------------------------- suppression list
def suppressed():
    return _load("suppression", {"domains": []})

def is_suppressed(domain):
    if not domain:
        return False
    return domain.lower() in [d.lower() for d in suppressed()["domains"]]

def add_suppression(domain):
    domain = canonical_domain(domain) or (domain or "").strip().lower()
    if not domain:
        raise RuntimeError("Provide a domain to suppress.")
    with __import__("threading").RLock():
        d = suppressed()
        if domain not in d["domains"]:
            d["domains"].append(domain)
            _save("suppression", d)
        return d

def remove_suppression(domain):
    domain = (domain or "").strip().lower()
    with __import__("threading").RLock():
        d = suppressed()
        d["domains"] = [x for x in d["domains"] if x.lower() != domain]
        _save("suppression", d)
        return d

def filter_suppressed(leads):
    """Return (kept, dropped) for a list of leads, dropping suppressed domains."""
    d = {x.lower() for x in suppressed()["domains"]}
    kept, dropped = [], []
    for l in leads:
        dom = _domain(l)
        if dom and dom in d:
            dropped.append(l)
        else:
            kept.append(l)
    return kept, dropped


# ---------------------------------------------------------------- blueprint config
def bp_config():
    c = _load("bp_config", {})
    out = json.loads(json.dumps(DEFAULT_BP))
    out.update(c)
    return out

def save_bp_config(obj):
    c = bp_config()
    for k in DEFAULT_BP:
        if k in obj:
            c[k] = obj[k]
    _save("bp_config", c)
    return bp_config()


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/suppression" and req.get("add"):
        return {"suppression": add_suppression(req["add"])}
    if path == "/api/suppression" and req.get("remove"):
        return {"suppression": remove_suppression(req["remove"])}
    if path == "/api/suppression":
        return suppressed()
    if path == "/api/dedup/canonical":
        return {"domain": canonical_domain(req.get("url", ""))}
    if path == "/api/dedup/check":
        dom = canonical_domain(req.get("url", ""))
        return {"domain": dom, "suppressed": is_suppressed(dom)}
    if path == "/api/dedup/filter":
        kept, dropped = filter_suppressed(req.get("leads", []))
        return {"kept": kept, "dropped": dropped, "droppedCount": len(dropped)}
    if path == "/api/bp-config":
        if req.get("save"):
            return {"config": save_bp_config(req["save"])}
        return {"config": bp_config()}
    raise RuntimeError("Unknown endpoint")
