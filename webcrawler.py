"""
WebCrawler integration for LeadFinder — ported from WebCrawler-and-Email-Automation-System.

Provides:
  * CSE-driven multi-URL scraping for business discovery and email extraction
  * Parallel scraping with the same caching as leadfinder.fetch_text
  * Import from/export to CSV (compatible with LeadFinder's My list format)
  * Integration with the existing email verification pipeline

Standard library only — no requests, no BeautifulSoup, no pandas.
"""
import csv, io, json, os, re, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import leadfinder as LF

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA, exist_ok=True)

# Regex patterns (stdlib re, no bs4)
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s\-]?)?(\(?\d{2,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,5})")
ADDRESS_KW = re.compile(r"\b(address|location|office|our office|find us|visit us|"
                         r"where we are|street|avenue|road)\b", re.I)

# Tags that suggest HTTPS insecurity or builder sites
BUILDER_HOSTS = ("wixsite.com", "weebly.com", "blogspot.", "sites.google.com",
                 "business.site", "wordpress.com", "square.site", "carrd.co",
                 "godaddysites.com", "jimdo.com", "webflow.io")


def _tag_text(html, tag):
    """Extract text of the first matching HTML tag."""
    m = re.search(rf"<{tag}[^>]*>(.*?)</{tag}>", html, re.I | re.S)
    if m:
        return re.sub(r"<[^>]+>", "", m.group(1)).strip()
    return ""


def scrape_url(url, timeout=12):
    """
    Scrape a single URL: extract business name, emails, phone, address,
    social links. Returns a partial lead dict.
    """
    result = {
        "website": url, "name": "", "email": "", "phone": "",
        "address": "", "emails": [], "source": "WebCrawler",
    }
    try:
        html, final, elapsed = LF.fetch_text(url, timeout=timeout)
    except Exception as ex:
        result["crawlError"] = str(ex)[:100]
        return result

    # Business name from <title>
    title_text = _tag_text(html, "title")
    result["name"] = title_text.split(" - ")[0].split(" | ")[0].strip()[:80]

    # All emails
    raw_emails = LF._emails_in(html)
    result["emails"] = raw_emails[:5]
    result["email"] = raw_emails[0] if raw_emails else ""

    # Phone (first plausible match)
    for m in PHONE_RE.finditer(html):
        digits = re.sub(r"\D", "", m.group(0))
        if 7 <= len(digits) <= 15:
            result["phone"] = m.group(0).strip()[:25]
            break

    # Address guess: text near address keywords
    text = re.sub(r"<[^>]+>", " ", html)
    for m in ADDRESS_KW.finditer(text):
        snippet = text[m.start(): m.start() + 200]
        addr = re.sub(r"\s+", " ", snippet).strip()[:120]
        if len(addr) > 20:
            result["address"] = addr
            break

    result["finalUrl"] = final
    return result


def batch_scrape(urls, workers=6):
    """Scrape multiple URLs in parallel. Returns list of lead dicts."""
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(scrape_url, urls))
    return results


def cse_discover(keyword, api_key, cse_id, max_results=50):
    """
    Discover business URLs using Google Custom Search (same as dorking.py but
    a simpler single-keyword interface matching the WebCrawler original).
    """
    if not api_key or not cse_id:
        raise RuntimeError("Add a Google Custom Search API key and Search Engine ID in Settings > Dorking.")
    out = []
    for start in range(1, max_results + 1, 10):
        url = ("https://www.googleapis.com/customsearch/v1?" +
               urllib.parse.urlencode({"key": api_key, "cx": cse_id,
                                       "q": keyword, "start": start, "num": 10}))
        try:
            res = LF.http_json(url, timeout=30)
        except Exception as ex:
            break
        if res.get("error"):
            raise RuntimeError("Google CSE: " + (res["error"].get("message") or str(res["error"])))
        items = res.get("items") or []
        for it in items:
            link = it.get("link", "")
            if link:
                out.append(link)
        if len(items) < 10:
            break
        time.sleep(0.4)
    return list(dict.fromkeys(out))[:max_results]  # de-dup, preserve order


def crawl_and_scrape(keyword, api_key, cse_id, max_results=30):
    """
    Full pipeline: CSE → scrape each URL → return leads with emails.
    Matches the original WebCrawler workflow.
    """
    urls = cse_discover(keyword, api_key, cse_id, max_results)
    if not urls:
        return {"leads": [], "urlsFound": 0, "withEmail": 0}
    leads = batch_scrape(urls)
    # De-dup by domain
    seen, deduped = set(), []
    for l in leads:
        domain = (urllib.parse.urlparse(l["website"]).netloc or "").lower().replace("www.", "")
        if domain and domain not in seen:
            seen.add(domain)
            # Convert to LeadFinder lead format
            lid = "wc:" + domain
            deduped.append({
                "id": lid, "source": "WebCrawler (CSE)",
                "name": l["name"], "category": keyword,
                "address": l["address"], "phone": l["phone"],
                "email": l["email"], "emailsFound": l["emails"],
                "website": l["website"],
                "social": "", "rating": None, "reviews": 0,
                "mapsUrl": "", "lat": None, "lng": None,
                "searchQuery": keyword,
                "snippet": "",
            })
    with_email = sum(1 for l in deduped if l["email"])
    return {"leads": deduped, "urlsFound": len(urls), "withEmail": with_email,
            "crawledAt": time.strftime("%Y-%m-%d %H:%M")}


# ---------------------------------------------------------------- CSV export/import (LeadFinder format)
EXPORT_FIELDS = ["name", "category", "address", "phone", "email", "website",
                 "rating", "reviews", "source", "stage", "followUp", "notes",
                 "priority", "id"]

def leads_to_csv(leads):
    """Return a CSV string from a list of lead dicts."""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_FIELDS, extrasaction="ignore")
    w.writeheader()
    for l in leads:
        row = {k: l.get(k, "") for k in EXPORT_FIELDS}
        w.writerow(row)
    return buf.getvalue()

def csv_to_leads(csv_text):
    """Parse a CSV string into lead dicts (LeadFinder import format)."""
    reader = csv.DictReader(io.StringIO(csv_text))
    leads = []
    for row in reader:
        l = {k: row.get(k, "").strip() for k in EXPORT_FIELDS if k in row}
        if l.get("name"):
            if not l.get("id"):
                l["id"] = "imp:" + re.sub(r"\W+", "-", l["name"].lower())[:30]
            leads.append(l)
    return leads


# ---------------------------------------------------------------- scheduled crawl storage
_SCHEDULE_FILE = os.path.join(DATA, "crawl_schedule.json")

def _load_schedule():
    try:
        with open(_SCHEDULE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"jobs": []}

def _save_schedule(s):
    with open(_SCHEDULE_FILE, "w", encoding="utf-8") as f:
        json.dump(s, f, indent=2)


# ---------------------------------------------------------------- API
def handle(path, req):
    import assistant
    cfg = assistant.cfg()
    api_key = req.get("apiKey") or cfg["keys"].get("cse", "")
    cse_id  = req.get("cseId")  or cfg["keys"].get("cseId", "")

    if path == "/api/webcrawler/crawl":
        keyword = req.get("keyword", "").strip()
        if not keyword:
            raise RuntimeError("Provide a keyword to crawl.")
        limit = min(int(req.get("limit", 30)), 100)
        return crawl_and_scrape(keyword, api_key, cse_id, limit)

    if path == "/api/webcrawler/scrape":
        urls = req.get("urls", [])[:50]
        if not urls:
            raise RuntimeError("Provide a list of URLs to scrape.")
        leads = batch_scrape(urls)
        return {"leads": leads, "count": len(leads)}

    if path == "/api/webcrawler/export-csv":
        leads = req.get("leads", [])
        return {"csv": leads_to_csv(leads)}

    if path == "/api/webcrawler/import-csv":
        csv_text = req.get("csv", "")
        if not csv_text:
            raise RuntimeError("Provide CSV text to import.")
        leads = csv_to_leads(csv_text)
        return {"leads": leads, "count": len(leads)}

    if path == "/api/webcrawler/schedule":
        sch = _load_schedule()
        if req.get("add"):
            job = req["add"]
            job["id"] = str(int(time.time()))
            job["enabled"] = True
            sch["jobs"].append(job)
            _save_schedule(sch)
        if req.get("delete"):
            sch["jobs"] = [j for j in sch["jobs"] if j["id"] != req["delete"]]
            _save_schedule(sch)
        if req.get("toggle"):
            for j in sch["jobs"]:
                if j["id"] == req["toggle"]:
                    j["enabled"] = not j["enabled"]
            _save_schedule(sch)
        return _load_schedule()

    raise RuntimeError("Unknown endpoint")
