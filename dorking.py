"""
Google Custom / Programmable Search discovery for LeadFinder.

Rebuilt around the stable Google Custom Search JSON API (REST, standard library)
from the ideas in the DOrky, Google-Dorking-Automation and WebCrawler repos, plus
the blueprint's "dorking" design (section 5): a query-template engine for finding
public business information only.

This is NOT a vulnerability/secret scanner. Templates target public business pages
only: contact pages, service/niche + city, "we are hiring" / intent signals, case
studies. No passwords, keys, private files, admin panels or sensitive data.

Keys are rotated across a list (the free CSE tier is ~100 queries/day per key), so
several free keys multiply the daily budget.
"""
import json, re, time, urllib.parse
import leadfinder as LF

# Safe public-business query templates. Variables: {niche} {city} {country} {company}
TEMPLATES = {
    "niche_city":         "{niche} in {city} {country}",
    "contact_page":       "{niche} {city} contact us",
    "hiring":             '"we are hiring" {niche} {city}',          # intent / companies actively recruiting
    "needs_website":      '{niche} {city} -site:facebook.com -site:instagram.com',
    "case_studies":       "{niche} case studies {city}",
    "company":            '"{company}" {city} {country}',
}
# Default template set run for a niche+city discovery batch
DEFAULT_TEMPLATES = ["niche_city", "hiring", "needs_website"]

_last_error = {}


def _keys(req):
    import assistant
    cfg = assistant.cfg().get("keys", {})
    ks = req.get("cseKey")
    if isinstance(ks, str) and ks:
        ks = [ks]
    elif not ks:
        ks = cfg.get("cse") or []
        if isinstance(ks, str) and ks:
            ks = [ks]
    if not isinstance(ks, list):
        ks = [ks] if ks else []
    cid = req.get("cseId") or cfg.get("cseId") or ""
    return [k for k in ks if k], cid


def _cse_call(key, cx, query, start):
    url = "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode({
        "key": key, "cx": cx, "q": query, "start": start, "num": 10})
    return LF.http_json(url, timeout=30)


def cse_search(query, keys, cx, limit=20):
    """Run one query across the key list (rotating on quota), up to `limit` results."""
    if not keys:
        raise RuntimeError("Add a Google Custom Search API key + Search Engine ID in Settings, or set cseKey/cseId.")
    if not cx:
        raise RuntimeError("Add a Google Programmable Search Engine ID (cse Id). Create one at cse.google.com.")
    out, errors, start = [], [], 1
    while len(out) < limit:
        progressed = False
        for k in keys:
            if k in _last_error and time.time() - _last_error[k] < 3600:
                continue
            try:
                res = _cse_call(k, cx, query, start)
                if res.get("error"):
                    err = res["error"].get("message", "error")
                    if "quota" in err.lower() or res["error"].get("code") == 429:
                        _last_error[k] = time.time()
                        errors.append("a key hit its daily quota")
                        continue
                    raise RuntimeError("Google CSE: " + err)
                items = res.get("items") or []
                for it in items:
                    out.append({
                        "id": "cse:" + str(it.get("cacheId") or it.get("link")),
                        "source": "Google CSE", "name": it.get("title", "").split(" - ")[0][:120],
                        "website": it.get("link", ""), "address": "",
                        "phone": "", "email": "", "social": "", "rating": None, "reviews": 0,
                        "mapsUrl": "", "lat": None, "lng": None, "searchQuery": query,
                        "snippet": it.get("snippet", ""),
                    })
                start += 10
                progressed = True
                break
            except Exception as ex:
                _last_error[k] = time.time()
                errors.append(str(ex)[:120])
                continue
        if not progressed:
            break
        time.sleep(0.3)
    return out[:limit], errors


def discover(req):
    niche = (req.get("niche") or "").strip()
    city = (req.get("city") or "").strip()
    country = (req.get("country") or "").strip()
    company = (req.get("company") or "").strip()
    tnames = req.get("templates") or DEFAULT_TEMPLATES
    if not (niche or company):
        raise RuntimeError("Provide a niche (or a company name) to search for.")
    keys, cx = _keys(req)
    limit = int(req.get("limit", 20))
    all_leads, report = [], {}
    for tname in tnames:
        tpl = TEMPLATES.get(tname)
        if not tpl:
            continue
        q = tpl.format(niche=niche, city=city, country=country, company=company).strip()
        if "{niche}" in q and not niche:
            continue
        leads, errs = cse_search(q, keys, cx, limit)
        report[tname] = {"query": q, "found": len(leads), "errors": errs}
        all_leads.extend(leads)
    # de-dup by website
    seen, dedup = set(), []
    for l in all_leads:
        if l["website"] and l["website"] in seen:
            continue
        if l["website"]:
            seen.add(l["website"])
        dedup.append(l)
    return {"leads": dedup, "report": report, "templates": TEMPLATES}


def handle(path, req):
    if path == "/api/dorking":
        return discover(req)
    if path == "/api/dorking/templates":
        return {"templates": TEMPLATES, "default": DEFAULT_TEMPLATES}
    raise RuntimeError("Unknown endpoint")
