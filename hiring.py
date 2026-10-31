"""
Hiring posts for LeadFinder: people who are already looking for a developer.

Sources (all public and allowed for automated reading; every post links back to its source):
  * Hacker News "Freelancer? Seeking freelancer?" and "Who is hiring?" threads (official HN Algolia API)
  * Remotive public API (software-dev jobs; Remotive asks for a link back and credit)
  * We Work Remotely public RSS feeds (WWR asks for a link back)

Nothing here logs in anywhere, and nothing is sent. You read the post and reply yourself.
"""
import html as htmllib, json, re, threading, time, urllib.parse
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import leadfinder as LF

MIN_GAP = 3 * 3600          # never ask a source more than once every 3 hours
KEEP_DAYS = 30              # forget posts older than this
_lock = threading.RLock()

SOURCES = {
    "hn": {"name": "Hacker News", "home": "https://news.ycombinator.com"},
    "remotive": {"name": "Remotive", "home": "https://remotive.com"},
    "wwr": {"name": "We Work Remotely", "home": "https://weworkremotely.com"},
}
WWR_FEEDS = {
    "back-end": "https://weworkremotely.com/categories/remote-back-end-programming-jobs.rss",
    "full-stack": "https://weworkremotely.com/categories/remote-full-stack-programming-jobs.rss",
    "front-end": "https://weworkremotely.com/categories/remote-front-end-programming-jobs.rss",
}
DEFAULT_SETTINGS = {
    "keywords": "laravel, php, wordpress, woocommerce, shopify, magento, livewire, react, full stack, rest api",
    "exclude": "unpaid, equity only, internship",
    "sources": {"hn": True, "remotive": True, "wwr": True},
    "wwrFeeds": ["back-end", "full-stack"],
    "onlyFreelance": False,
    "auto": True,
}
FREELANCE_RX = re.compile(r"\b(freelanc\w*|contract(?:or)?|part[- ]time|project[- ]based|fixed[- ]price|hourly|short[- ]term|consultant)\b", re.I)


# ---------------------------------------------------------------- store
def _load():
    import assistant
    d = assistant.load("hiring", {})
    d.setdefault("posts", [])
    d.setdefault("lastFetch", {})
    d.setdefault("lastAuto", "")
    s = json.loads(json.dumps(DEFAULT_SETTINGS))
    s.update(d.get("settings") or {})
    d["settings"] = s
    return d

def _save(d):
    import assistant
    assistant.save("hiring", d)


# ---------------------------------------------------------------- helpers
def _plain(h, limit=None):
    h = re.sub(r"(?i)<br\s*/?>|</p>|<p>", "\n", h or "")
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t[:limit] if limit else t

def _iso(ts):
    try:
        return time.strftime("%Y-%m-%d", time.gmtime(float(ts)))
    except Exception:
        return ""

def _terms(s):
    return [x.strip().lower() for x in (s or "").split(",") if x.strip()]

def _has(term, text):
    # whole-word match, so "php" doesn't match "graphql" and "react" doesn't match "reactive"
    return re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")


# ---------------------------------------------------------------- sources
def fetch_hn():
    """Top-level posts from the latest 'Freelancer? Seeking freelancer?' (only SEEKING FREELANCER)
    and 'Who is hiring?' threads."""
    q = "https://hn.algolia.com/api/v1/search_by_date?" + urllib.parse.urlencode(
        {"tags": "story,author_whoishiring", "hitsPerPage": 10})
    stories = LF.http_json(q, timeout=30).get("hits", [])
    picks = {}
    for s in stories:   # newest first
        title = s.get("title") or ""
        if "freelancer" in title.lower() and "freelance" not in picks:
            picks["freelance"] = s
        elif "who is hiring" in title.lower() and "hiring" not in picks:
            picks["hiring"] = s
    out = []
    for kind, s in picks.items():
        sid = str(s.get("objectID"))
        url = "https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
            {"tags": f"comment,story_{sid}", "hitsPerPage": 1000})
        for c in LF.http_json(url, timeout=60).get("hits", []):
            if str(c.get("parent_id")) != sid:
                continue                                    # replies, not posts
            text = _plain(c.get("comment_text"))
            if not text:
                continue
            if kind == "freelance" and not re.match(r"\s*seeking\s+freelancer", text, re.I):
                continue                                    # skip "SEEKING WORK" (other freelancers)
            lines = [x.strip() for x in text.split("\n") if x.strip()]
            first = re.sub(r"(?i)^\s*seeking\s+freelancer\s*[-:|]?\s*", "", lines[0])
            if kind == "freelance":
                # the first line is usually just "Remote" or a location; the need is on the next line
                need = lines[1] if len(lines) > 1 else first
                first = f"{need[:110]}" + (f" ({first[:30]})" if first and first != need else "")
            company = first.split("|")[0].strip()[:80] if kind == "hiring" else (c.get("author") or "")
            out.append({
                "id": f"hn:{c.get('objectID')}", "source": "hn",
                "title": (first[:140] or "Seeking freelancer"), "company": company,
                "url": f"https://news.ycombinator.com/item?id={c.get('objectID')}",
                "postedAt": _iso(c.get("created_at_i")), "location": "",
                "jobType": "Freelance" if kind == "freelance" else "",
                "text": text[:4000], "thread": s.get("title", ""),
                "email": next(iter(EMAIL_RE.findall(text)), ""),
            })
    return out

def fetch_remotive():
    res = LF.http_json("https://remotive.com/api/remote-jobs?category=software-dev", timeout=60)
    out = []
    for j in res.get("jobs", []):
        out.append({
            "id": f"remotive:{j.get('id')}", "source": "remotive",
            "title": j.get("title", ""), "company": j.get("company_name", ""),
            "url": j.get("url", ""), "postedAt": (j.get("publication_date") or "")[:10],
            "location": j.get("candidate_required_location", ""),
            "jobType": (j.get("job_type") or "").replace("_", " ").title(),
            "salary": j.get("salary", ""),
            "text": (" ".join(j.get("tags") or []) + "\n" + _plain(j.get("description")))[:4000],
            "email": "",
        })
    return out

def fetch_wwr(feeds):
    out, seen = [], set()
    for f in feeds:
        url = WWR_FEEDS.get(f)
        if not url:
            continue
        xml, _, _ = LF.fetch_text(url, timeout=40, limit=4_000_000)
        root = ET.fromstring(xml.encode("utf-8"))
        for it in root.iter("item"):
            g = lambda tag: (it.findtext(tag) or "").strip()
            link = g("link") or g("guid")
            if not link or link in seen:
                continue
            seen.add(link)
            title = g("title")
            company, _, role = title.partition(": ")
            try:
                posted = parsedate_to_datetime(g("pubDate")).strftime("%Y-%m-%d")
            except Exception:
                posted = ""
            out.append({
                "id": "wwr:" + link.rstrip("/").rsplit("/", 1)[-1], "source": "wwr",
                "title": role or title, "company": company if role else "",
                "url": link, "postedAt": posted, "location": g("region"),
                "jobType": g("type"), "text": _plain(g("description"))[:4000], "email": "",
            })
    return out


# ---------------------------------------------------------------- scoring
def score(post, st):
    """Return (score, matched keywords) or None if the post should be hidden."""
    title = (post.get("title") or "").lower()
    body = f"{title} {post.get('company','')} {post.get('jobType','')} {post.get('text','')}".lower()
    if any(_has(x, body) for x in _terms(st.get("exclude"))):
        return None
    matched = [k for k in _terms(st.get("keywords")) if _has(k, body)]
    if not matched:
        return None
    freelance = (post["source"] == "hn" and post.get("jobType") == "Freelance") or \
        bool(FREELANCE_RX.search(f"{post.get('jobType','')} {title} {post.get('text','')[:1500]}"))
    if st.get("onlyFreelance") and not freelance:
        return None
    s = sum(3 if _has(k, title) else 1 for k in matched)
    if freelance: s += 4          # contract / freelance work fits you best
    if post.get("email"): s += 1  # you can reply directly
    try:
        age = (time.time() - time.mktime(time.strptime(post["postedAt"], "%Y-%m-%d"))) / 86400
        if age <= 3: s += 2
        elif age <= 7: s += 1
    except Exception:
        pass
    return s, matched, freelance


# ---------------------------------------------------------------- refresh
def refresh(force_sources=None, auto=False):
    """Fetch the enabled sources (respecting the 3-hour gap) and merge new posts."""
    with _lock:
        d = _load()
        st = d["settings"]
        wanted = [k for k, on in st["sources"].items() if on and k in SOURCES]
        if force_sources:
            wanted = [k for k in wanted if k in force_sources]
        report, now = {}, time.time()
        byid = {p["id"]: p for p in d["posts"]}
        for src in wanted:
            last = d["lastFetch"].get(src, 0)
            if now - last < MIN_GAP:
                mins = int((MIN_GAP - (now - last)) / 60)
                report[src] = {"skipped": True, "note": f"checked recently; next check in {mins} min"}
                continue
            try:
                items = fetch_hn() if src == "hn" else fetch_remotive() if src == "remotive" else fetch_wwr(st["wwrFeeds"])
                d["lastFetch"][src] = now
                new = 0
                for p in items:
                    if p["id"] in byid:
                        byid[p["id"]].update({k: p[k] for k in ("title", "text", "url", "jobType", "location")})
                        continue
                    p.update({"status": "new", "foundAt": time.strftime("%Y-%m-%d"), "notes": ""})
                    byid[p["id"]] = p
                    new += 1
                report[src] = {"fetched": len(items), "new": new}
            except Exception as ex:
                report[src] = {"error": str(ex)[:300]}
        cutoff = time.strftime("%Y-%m-%d", time.gmtime(now - KEEP_DAYS * 86400))
        d["posts"] = [p for p in byid.values()
                      if p.get("status") in ("saved", "applied") or (p.get("postedAt") or p.get("foundAt", "")) >= cutoff]
        if auto:
            d["lastAuto"] = time.strftime("%Y-%m-%d")
        _save(d)
        return report

def daily():
    """Called by the Autopilot scheduler: one refresh per day."""
    d = _load()
    if d["settings"].get("auto") and d.get("lastAuto") != time.strftime("%Y-%m-%d"):
        rep = refresh(auto=True)
        import assistant
        new = sum(r.get("new", 0) for r in rep.values())
        errs = [f"{SOURCES[k]['name']}: {r['error']}" for k, r in rep.items() if r.get("error")]
        assistant.log(f"Hiring posts: {new} new" + (f" ({'; '.join(errs)})" if errs else ""))

def listing(status="new"):
    d = _load()
    st = d["settings"]
    out = []
    counts = {"new": 0, "saved": 0, "applied": 0, "dismissed": 0}
    for p in d["posts"]:
        r = score(p, st)
        if r is None and p.get("status") not in ("saved", "applied"):
            continue
        s, matched, freelance = r or (0, [], False)
        counts[p.get("status", "new")] = counts.get(p.get("status", "new"), 0) + 1
        if status and p.get("status", "new") != status:
            continue
        q = dict(p)
        q.update({"score": s, "matched": matched, "freelance": freelance,
                  "sourceName": SOURCES[p["source"]]["name"], "snippet": p.get("text", "")[:600]})
        q.pop("text", None)
        out.append(q)
    out.sort(key=lambda p: p.get("postedAt", ""), reverse=True)   # newest first...
    out.sort(key=lambda p: -p["score"])                            # ...within the same score
    return {"posts": out, "counts": counts, "settings": st,
            "lastFetch": {k: _iso(v) for k, v in d["lastFetch"].items()}, "sources": SOURCES,
            "wwrFeeds": list(WWR_FEEDS)}

def post_text(pid):
    for p in _load()["posts"]:
        if p["id"] == pid:
            return p
    raise RuntimeError("Post not found (it may be older than 30 days).")

def update(pid, patch):
    with _lock:
        d = _load()
        for p in d["posts"]:
            if p["id"] == pid:
                for k in ("status", "notes"):
                    if k in patch: p[k] = patch[k]
                _save(d)
                return {"ok": True}
    raise RuntimeError("Post not found.")


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/hiring/list":
        return listing(req.get("status", "new"))
    if path == "/api/hiring/refresh":
        return {"report": refresh(req.get("sources"))}
    if path == "/api/hiring/update":
        return update(req.get("id", ""), req)
    if path == "/api/hiring/post":
        return {"post": post_text(req.get("id", ""))}
    if path == "/api/hiring/settings":
        with _lock:
            d = _load()
            new = req.get("settings") or {}
            for k in ("keywords", "exclude", "onlyFreelance", "auto"):
                if k in new: d["settings"][k] = new[k]
            if isinstance(new.get("sources"), dict):
                d["settings"]["sources"].update({k: bool(v) for k, v in new["sources"].items() if k in SOURCES})
            if isinstance(new.get("wwrFeeds"), list):
                d["settings"]["wwrFeeds"] = [f for f in new["wwrFeeds"] if f in WWR_FEEDS]
            _save(d)
        return listing(req.get("status", "new"))
    raise RuntimeError("Unknown endpoint")
