"""
Job lead search for LeadFinder: find companies actively hiring developers,
using public job sites and search engines.

Sources (every result links back to its source; nothing logs in or sends anything):
  * BeBee (bebee.com)          - free, no key. Job cards carry clean data-voice attrs.
  * Google web search          - via SerpApi (engine=google). Reuses your SerpApi key.
  * JobLeads (jobleads.com)     - the site is behind a Cloudflare bot challenge, so its
                                  postings are surfaced through Google with a
                                  site:jobleads.com search (also via SerpApi).

You read the post and reply yourself.
"""
import html as htmllib, re, urllib.parse
import leadfinder as LF

SOURCES = {
    "bebee":    {"name": "BeBee",          "home": "https://bebee.com",        "needsKey": False},
    "google":   {"name": "Google search",  "home": "https://www.google.com",   "needsKey": True},
    "jobleads": {"name": "JobLeads",       "home": "https://www.jobleads.com", "needsKey": True},
}

# BeBee filter dropdowns (kept in sync with the live site)
BEEBEE_FILTERS = {
    "contractType": ["", "full_time", "part_time", "contract"],
    "postedWithin": ["", "24h", "3d", "7d", "14d", "30d"],
    "remote":       ["", "full_remote", "hybrid", "on_site"],
    "jobType":      ["", "company", "recruiter", "headhunter"],
}


# ---------------------------------------------------------------- helpers
def _clean(h, limit=None):
    """Strip tags from an HTML fragment."""
    h = re.sub(r"(?i)<br\s*/?>|</p>|<p>", "\n", h or "")
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t[:limit] if limit else t

def _host(u):
    try:
        return urllib.parse.urlparse(u).hostname.replace("www.", "") if u else ""
    except Exception:
        return ""

def _attr(tag, name):
    m = re.search(name + r'="([^"]*)"', tag)
    return m.group(1) if m else ""


# ---------------------------------------------------------------- BeBee (direct, free)
def _bebee_url(query, country, filters):
    country = (country or "pk").strip().lower() or "pk"
    base = f"https://bebee.com/{country}/jobs"
    p = [("q", query)]
    for k in ("contractType", "postedWithin", "remote", "jobType"):
        v = filters.get(k)
        if v:
            p.append((k, v))
    loc = filters.get("location")
    if loc:
        p.append(("location", loc))
    return base + "?" + urllib.parse.urlencode(p)

def fetch_bebee(query, country, filters):
    """Scrape one BeBee results page (~20 cards). Each card exposes data-voice
    attributes (id, title, company, location, url) plus job-type badges, a
    snippet and a posted date."""
    url = _bebee_url(query, country, filters)
    html, _final, _ = LF.fetch_text(url, timeout=30)
    out = []
    for m in re.finditer(r'<article[^>]*data-voice-job="card"[^>]*>', html):
        tag = m.group(0)
        vid = _attr(tag, "data-voice-id")
        if not vid:
            continue
        href = _attr(tag, "data-voice-url")
        link = urllib.parse.urljoin("https://bebee.com", href) if href else url
        # card body, up to its closing tag
        body = html[m.end():m.end() + 4000]
        end = body.find("</article>")
        if end != -1:
            body = body[:end]
        badges = re.findall(r'rounded-full[^>]*>\s*([^<]{1,40})\s*</span>', body)
        job_type = ", ".join(dict.fromkeys(b.strip() for b in badges if b.strip()))
        posted = ""
        dm = re.search(r'>\s*(Today|Yesterday|\d+\s+\w+\s+ago)\s*<', body, re.I)
        if dm:
            posted = dm.group(1).strip()
        sm = re.search(r'<p[^>]*line-clamp[^>]*>(.*?)</p>', body, re.S)
        snippet = _clean(sm.group(1), 600) if sm else ""
        out.append({
            "id": "bebee:" + vid, "source": "bebee", "sourceName": "BeBee",
            "title": _attr(tag, "data-voice-title") or "Job posting",
            "company": _attr(tag, "data-voice-company"),
            "location": _attr(tag, "data-voice-location"),
            "url": link, "jobType": job_type, "postedAt": posted,
            "snippet": snippet, "query": query, "needsKey": False,
        })
    if not out:
        raise RuntimeError("BeBee returned no job cards. The page layout may have changed, or the search had no matches.")
    return out


# ---------------------------------------------------------------- SerpApi (Google + JobLeads)
def _serpapi_key(req):
    key = (req.get("serpKey") or "").strip()
    if not key:
        key = LF._stored_key("serp")
    if not key:
        raise RuntimeError("Google and JobLeads need a SerpApi key. Add it in Settings, "
                           "or turn those sources off - BeBee is free and needs no key.")
    return key

def _serpapi_google(key, query, source_key, source_name):
    """Run a Google web search through SerpApi and return organic results as job leads."""
    LF._spend("serpapi")
    params = {"engine": "google", "q": query, "api_key": key, "num": 20, "gl": "us", "hl": "en"}
    res = LF.http_json("https://serpapi.com/search.json?" + urllib.parse.urlencode(params), timeout=90)
    if res.get("error"):
        raise RuntimeError("SerpApi: " + str(res["error"]))
    out = []
    for i, r in enumerate(res.get("organic_results") or []):
        link = r.get("link") or r.get("redirect") or ""
        company = r.get("source") or _host(r.get("displayed_link") or link)
        out.append({
            "id": source_key + ":" + str(r.get("position") or i),
            "source": source_key, "sourceName": source_name,
            "title": r.get("title", ""),
            "company": company,
            "location": "",
            "url": link, "jobType": "",
            "postedAt": (r.get("date") or "")[:40],
            "snippet": r.get("snippet", ""), "query": query, "needsKey": True,
        })
    return out

def fetch_google(key, query, location):
    q = " ".join(x for x in (query, location) if x).strip()
    return _serpapi_google(key, q, "google", "Google search")

def fetch_jobleads(key, query, location):
    # JobLeads itself is Cloudflare-protected; surface its postings via Google.
    q = "site:jobleads.com " + " ".join(x for x in (query, location) if x).strip()
    return _serpapi_google(key, q, "jobleads", "JobLeads")


# ---------------------------------------------------------------- search
def search(req):
    query = (req.get("query") or "").strip()
    location = (req.get("location") or "").strip()
    if not query:
        raise RuntimeError("Enter a job search query, e.g. \"PHP Laravel backend developer\".")
    sources = req.get("sources") or ["bebee"]
    filters = req.get("filters") or {}
    country = req.get("country") or "pk"
    results, report = [], {}

    if "bebee" in sources:
        try:
            items = fetch_bebee(query, country, {**filters, "location": location})
            report["bebee"] = {"fetched": len(items)}
            results.extend(items)
        except Exception as ex:
            report["bebee"] = {"error": str(ex)[:300]}

    needs_key = [s for s in ("google", "jobleads") if s in sources]
    if needs_key:
        try:
            key = _serpapi_key(req)
        except Exception as ex:
            for s in needs_key:
                report[s] = {"error": str(ex)[:300]}
            key = None
        if key:
            for s in needs_key:
                try:
                    if s == "google":
                        items = fetch_google(key, query, location)
                    else:
                        items = fetch_jobleads(key, query, location)
                    report[s] = {"fetched": len(items)}
                    results.extend(items)
                except Exception as ex:
                    report[s] = {"error": str(ex)[:300]}

    # de-dup by url, keep first seen
    seen, dedup = set(), []
    for r in results:
        u = r.get("url")
        if u and u in seen:
            continue
        if u:
            seen.add(u)
        dedup.append(r)
    return {"results": dedup, "report": report, "sources": SOURCES}


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/jobsearch":
        return search(req)
    if path == "/api/jobsearch/sources":
        return {"sources": SOURCES, "bebeeFilters": BEEBEE_FILTERS}
    raise RuntimeError("Unknown endpoint")
