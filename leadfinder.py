#!/usr/bin/env python3
"""
LeadFinder - find local businesses anywhere in the world, see which ones have
no website, collect phone / email, research them, and track your outreach.

Run:  python leadfinder.py      then open http://localhost:8765
Needs only Python 3.8+ (no pip installs).

Data sources
  * Google Places API (best coverage, shows website + phone). Needs an API key.
  * OpenStreetMap (free, no key). Coverage varies by city; sometimes has emails.
"""
import json, os, re, ssl, sys, time, math, webbrowser, threading
import urllib.request, urllib.parse, urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from concurrent.futures import ThreadPoolExecutor

PORT = int(os.environ.get("LEADFINDER_PORT", "8765"))
UA = "LeadFinder/1.0 (local lead research tool)"
CTX = ssl.create_default_context()

# ---------------------------------------------------------------- helpers
def http_json(url, data=None, headers=None, timeout=60, method=None):
    h = {"User-Agent": UA}
    if headers: h.update(headers)
    body = None
    if data is not None:
        body = data if isinstance(data, bytes) else json.dumps(data).encode()
    req = urllib.request.Request(url, data=body, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return json.loads(r.read().decode("utf-8", "replace"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code} from {urllib.parse.urlparse(url).netloc}: {detail}")

# Browser-like headers: many small-business sites block unknown bots.
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/128.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en;q=0.9",
}
SITE_TTL = 6 * 3600      # reuse a downloaded page for 6 hours
FAIL_TTL = 15 * 60       # remember a dead site for 15 minutes (no repeated timeouts)
_site_cache, _site_lock = {}, threading.Lock()

def _fetch_once(url, timeout, limit):
    req = urllib.request.Request(url, headers=BROWSER_HEADERS)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        raw = r.read(limit)
        final = r.geturl()
        charset = r.headers.get_content_charset() or "utf-8"
    return raw.decode(charset, "replace"), final, time.time() - t0

def fetch_text(url, timeout=15, limit=600_000):
    """Download a page. Results (and failures) are cached per URL, so the audit,
    presence check, email finder and owner finder share one download."""
    key = (url, limit)
    now = time.time()
    with _site_lock:
        hit = _site_cache.get(key)
    if hit and now - hit[0] < (SITE_TTL if hit[1] == "ok" else FAIL_TTL):
        if hit[1] == "ok":
            return hit[2]
        raise hit[2]
    try:
        try:
            res = _fetch_once(url, timeout, limit)
        except urllib.error.HTTPError:
            raise                       # 404 / 403 etc: retrying won't help
        except (urllib.error.URLError, TimeoutError, ConnectionError) as ex:
            reason = getattr(ex, "reason", ex)
            if isinstance(reason, ConnectionRefusedError) or "Name or service not known" in str(ex) \
               or "getaddrinfo" in str(ex) or "nodename nor servname" in str(ex):
                raise                   # nothing listening / domain doesn't exist: retrying won't help
            time.sleep(1.5)             # one retry for timeouts / resets
            res = _fetch_once(url, timeout, limit)
    except Exception as ex:
        with _site_lock:
            _site_cache[key] = (time.time(), "fail", ex)
        raise
    with _site_lock:
        if len(_site_cache) > 800:      # keep memory small: drop the oldest half
            for k in sorted(_site_cache, key=lambda k: _site_cache[k][0])[:400]:
                _site_cache.pop(k, None)
        _site_cache[key] = (time.time(), "ok", res)
    return res

def norm_url(u):
    u = (u or "").strip()
    if u and not re.match(r"^https?://", u, re.I):
        u = "http://" + u
    return u

# ---------------------------------------------------------------- Google Places (New)
G_FIELDS = ",".join([
    "places.id", "places.displayName", "places.formattedAddress",
    "places.nationalPhoneNumber", "places.internationalPhoneNumber",
    "places.websiteUri", "places.rating", "places.userRatingCount",
    "places.googleMapsUri", "places.businessStatus", "places.location", "places.primaryTypeDisplayName",
    "nextPageToken",
])

def _spend(kind):
    import assistant
    assistant.spend(kind)

def _google_error(msg):
    m = msg.lower()
    if "api_key_invalid" in m or "api key not valid" in m:
        return "Google says this API key is not valid. Copy it again from Google Cloud > Credentials."
    if "billing" in m:
        return "Google requires billing on your Google Cloud project. Turn on billing, then try again."
    if "has not been used" in m or "is disabled" in m or "service_disabled" in m:
        return "Places API (New) is not enabled. In Google Cloud go to APIs & Services > Library, search 'Places API (New)' and press Enable. Wait 2-5 minutes."
    if "referer" in m or "api_key_http_referrer_blocked" in m or "ip address" in m:
        return "Your key has restrictions that block this app. In Credentials, set Application restrictions to 'None' (keep the API restriction to Places API (New))."
    if "quota" in m or "resource_exhausted" in m or "429" in m:
        return "Google quota reached. Wait a bit or raise the quota in Google Cloud."
    return "Google error: " + msg

def _g_convert(p, query):
    return {
        "id": "g:" + p.get("id", ""),
        "source": "Google",
        "name": (p.get("displayName") or {}).get("text", ""),
        "category": (p.get("primaryTypeDisplayName") or {}).get("text", query),
        "address": p.get("formattedAddress", ""),
        "phone": p.get("internationalPhoneNumber") or p.get("nationalPhoneNumber", ""),
        "email": "",
        "website": p.get("websiteUri", ""),
        "social": "",
        "rating": p.get("rating"),
        "reviews": p.get("userRatingCount") or 0,
        "mapsUrl": p.get("googleMapsUri", ""),
        "lat": (p.get("location") or {}).get("latitude"),
        "lng": (p.get("location") or {}).get("longitude"),
        "searchQuery": query,
    }

def _serp_convert(p, query):
    gps = p.get("gps_coordinates") or {}
    return {
        "id": "s:" + str(p.get("place_id") or p.get("data_id") or p.get("title")),
        "source": "Google (SerpApi)",
        "name": p.get("title", ""),
        "category": p.get("type") or query,
        "address": p.get("address", ""),
        "phone": p.get("phone", ""),
        "email": "",
        "website": p.get("website", ""),
        "social": "",
        "rating": p.get("rating"),
        "reviews": p.get("reviews") or 0,
        "mapsUrl": ("https://www.google.com/maps/place/?q=place_id:" + p["place_id"]) if p.get("place_id") else "",
        "lat": gps.get("latitude"), "lng": gps.get("longitude"),
        "searchQuery": query,
    }

def _g_text_search(api_key, text, max_pages, rect=None):
    out, token = [], None
    for _ in range(max(1, min(int(max_pages), 3))):
        body = {"textQuery": text, "pageSize": 20}
        if rect:
            s, w, n, e = rect
            body["locationRestriction"] = {"rectangle": {
                "low": {"latitude": s, "longitude": w}, "high": {"latitude": n, "longitude": e}}}
        if token: body["pageToken"] = token
        _spend("google")
        try:
            res = http_json("https://places.googleapis.com/v1/places:searchText", body, {
                "Content-Type": "application/json",
                "X-Goog-Api-Key": api_key,
                "X-Goog-FieldMask": G_FIELDS,
            })
        except RuntimeError as ex:
            raise RuntimeError(_google_error(str(ex)))
        out.extend(res.get("places", []))
        token = res.get("nextPageToken")
        if not token: break
        time.sleep(2)
    return out

def _stored_key(k):
    try:
        import assistant
        return assistant.cfg()["keys"].get(k, "")
    except Exception:
        return ""

def google_search(api_key, query, location, max_pages=3, deep=0):
    """deep=0: one search (max 60). deep=2 or 3: split the city into a 2x2 or 3x3
    grid and search each square (up to 240 / 540 results, more API calls)."""
    api_key = api_key or _stored_key("google")
    if not api_key:
        raise RuntimeError("Add your Google Places API key in Settings, or switch to OpenStreetMap (free).")
    places = {}
    if deep and location:
        s, w, n, e, _label = geocode(location)
        g = int(deep)
        for i in range(g):
            for j in range(g):
                rect = (s + (n - s) * i / g, w + (e - w) * j / g,
                        s + (n - s) * (i + 1) / g, w + (e - w) * (j + 1) / g)
                for p in _g_text_search(api_key, query, max_pages, rect):
                    places[p.get("id")] = p
    else:
        text = f"{query} in {location}" if location else query
        for p in _g_text_search(api_key, text, max_pages):
            places[p.get("id")] = p
    return [_g_convert(p, query) for p in places.values()
            if not p.get("businessStatus") or p["businessStatus"] == "OPERATIONAL"]

def google_test_key(api_key):
    if not api_key:
        raise RuntimeError("Paste a key first.")
    res = _g_text_search(api_key, "coffee in London", 1)
    return f"Key works. Google returned {len(res)} test results."

# ---------------------------------------------------------------- SerpApi (Google Maps data, no Google Cloud)
def serpapi_search(api_key, query, location, max_pages=3):
    api_key = api_key or _stored_key("serp")
    if not api_key:
        raise RuntimeError("Add your SerpApi key in Settings (serpapi.com), or use another source.")
    out, seen = [], set()
    for page in range(max(1, min(int(max_pages), 3))):
        params = {"engine": "google_maps", "type": "search", "api_key": api_key,
                  "q": f"{query} in {location}" if location else query, "start": page * 20}
        _spend("serpapi")
        try:
            res = http_json("https://serpapi.com/search.json?" + urllib.parse.urlencode(params), timeout=90)
        except RuntimeError as ex:
            raise RuntimeError("SerpApi error: " + str(ex))
        if res.get("error"):
            if page and "hasn't returned any results" in res["error"]: break
            raise RuntimeError("SerpApi: " + res["error"])
        items = res.get("local_results") or []
        if isinstance(items, dict): items = [items]
        if not items and res.get("place_results"): items = [res["place_results"]]
        for p in items:
            c = _serp_convert(p, query)
            if c["id"] in seen: continue
            seen.add(c["id"])
            out.append(c)
        if len(items) < 20: break
    return out

# ---------------------------------------------------------------- OpenStreetMap
OSM_TAGS = {
    "Dentist": ['"amenity"="dentist"', '"healthcare"="dentist"'],
    "Doctor / clinic": ['"amenity"="doctors"', '"amenity"="clinic"'],
    "Vet": ['"amenity"="veterinary"'],
    "Restaurant": ['"amenity"="restaurant"'],
    "Cafe": ['"amenity"="cafe"'],
    "Fast food": ['"amenity"="fast_food"'],
    "Bakery": ['"shop"="bakery"'],
    "Hair salon / barber": ['"shop"="hairdresser"'],
    "Beauty salon": ['"shop"="beauty"'],
    "Gym": ['"leisure"="fitness_centre"'],
    "Car repair": ['"shop"="car_repair"'],
    "Car wash": ['"amenity"="car_wash"'],
    "Plumber": ['"craft"="plumber"'],
    "Electrician": ['"craft"="electrician"'],
    "Builder / contractor": ['"craft"="builder"', '"office"="construction_company"'],
    "Roofer": ['"craft"="roofer"'],
    "Painter / decorator": ['"craft"="painter"'],
    "Carpenter": ['"craft"="carpenter"'],
    "Tailor": ['"craft"="tailor"', '"shop"="tailor"'],
    "Florist": ['"shop"="florist"'],
    "Clothing store": ['"shop"="clothes"'],
    "Furniture store": ['"shop"="furniture"'],
    "Hardware store": ['"shop"="hardware"', '"shop"="doityourself"'],
    "Pet shop / grooming": ['"shop"="pet"', '"shop"="pet_grooming"'],
    "Laundry / dry cleaning": ['"shop"="laundry"', '"shop"="dry_cleaning"'],
    "Accountant": ['"office"="accountant"', '"office"="tax_advisor"'],
    "Lawyer": ['"office"="lawyer"'],
    "Real estate agent": ['"office"="estate_agent"'],
    "Insurance agent": ['"office"="insurance"'],
    "Hotel / guest house": ['"tourism"="hotel"', '"tourism"="guest_house"'],
    "Driving school": ['"amenity"="driving_school"'],
    "Optician": ['"shop"="optician"'],
    "Pharmacy": ['"amenity"="pharmacy"'],
    "Photographer": ['"craft"="photographer"', '"shop"="photo"'],
    "Jeweller": ['"shop"="jewelry"'],
    "Mobile phone shop": ['"shop"="mobile_phone"'],
}

_last_nominatim = [0.0]
def geocode(location):
    wait = 1.1 - (time.time() - _last_nominatim[0])
    if wait > 0: time.sleep(wait)
    _last_nominatim[0] = time.time()
    url = "https://nominatim.openstreetmap.org/search?" + urllib.parse.urlencode(
        {"q": location, "format": "json", "limit": 1})
    res = http_json(url, timeout=30)
    if not res:
        raise RuntimeError(f"Couldn't find the place \"{location}\". Try \"City, Country\".")
    s, n, w, e = map(float, res[0]["boundingbox"])
    return s, w, n, e, res[0].get("display_name", location)

def osm_search(category, location, limit=400):
    tags = OSM_TAGS.get(category)
    if not tags:
        raise RuntimeError("For OpenStreetMap, pick a business type from the list.")
    if not location:
        raise RuntimeError("Enter a city, e.g. \"Austin, USA\" or \"Leeds, UK\".")
    s, w, n, e, label = geocode(location)
    km_ns = (n - s) * 111
    km_ew = (e - w) * 111 * math.cos(math.radians((n + s) / 2))
    if km_ns * km_ew > 40000:
        raise RuntimeError(f"\"{label}\" is too large for a free search. Use a city or district instead of a whole country or state.")
    bbox = f"{s},{w},{n},{e}"
    parts = "".join(f'nwr[{t}]["name"]({bbox});' for t in tags)
    q = f"[out:json][timeout:90];({parts});out center tags {int(limit)};"
    res = None
    for ep in ("https://overpass-api.de/api/interpreter", "https://overpass.kumi.systems/api/interpreter"):
        try:
            res = http_json(ep, urllib.parse.urlencode({"data": q}).encode(),
                            {"Content-Type": "application/x-www-form-urlencoded"}, timeout=120)
            break
        except Exception as ex:
            last = ex
    if res is None:
        raise RuntimeError(f"OpenStreetMap servers are busy, try again in a minute. ({last})")
    return [_osm_convert(el, category) for el in res.get("elements", [])]

def _osm_convert(el, category):
    t = el.get("tags", {})
    addr = ", ".join(x for x in [
        " ".join(filter(None, [t.get("addr:housenumber"), t.get("addr:street")])),
        t.get("addr:suburb") or t.get("addr:district"),
        t.get("addr:city"), t.get("addr:postcode")] if x)
    social = t.get("contact:facebook") or t.get("facebook") or t.get("contact:instagram") or t.get("instagram") or ""
    center = el.get("center") or {}
    return {
        "id": f"o:{el['type']}/{el['id']}",
        "source": "OpenStreetMap",
        "name": t.get("name", ""),
        "category": category,
        "address": addr,
        "phone": (t.get("phone") or t.get("contact:phone") or t.get("contact:mobile") or "").split(";")[0].strip(),
        "email": (t.get("email") or t.get("contact:email") or "").split(";")[0].strip(),
        "website": t.get("website") or t.get("contact:website") or t.get("url") or "",
        "social": social,
        "rating": None,
        "reviews": 0,
        "mapsUrl": f"https://www.openstreetmap.org/{el['type']}/{el['id']}",
        "lat": el.get("lat", center.get("lat")),
        "lng": el.get("lon", center.get("lon")),
        "searchQuery": category,
    }

# ---------------------------------------------------------------- email finder
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}")
BAD_EXT = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".css", ".js")
BAD_DOM = ("example.com", "sentry.io", "wixpress.com", "domain.com", "email.com", "godaddy.com", "sentry-next.wixpress.com")

def _emails_in(html):
    html = html.replace("&#64;", "@").replace("[at]", "@").replace("(at)", "@")
    out = []
    for m in EMAIL_RE.findall(html):
        m = m.strip(".").lower()
        if m.endswith(BAD_EXT) or any(m.endswith("@" + d) or m.split("@")[1].endswith(d) for d in BAD_DOM):
            continue
        if m not in out: out.append(m)
    return out

def _try_fetch(p):
    try:
        html, final, _ = fetch_text(p, timeout=10)
        return html, final
    except Exception:
        return None

def find_emails(url):
    url = norm_url(url)
    if not url: return {"emails": [], "checked": []}
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    rest = [base + x for x in ("/contact", "/contact-us", "/about", "/about-us")]
    rest = [p for p in dict.fromkeys(rest) if p != url]
    found, checked = [], []
    def take(r):
        if not r: return
        checked.append(r[1])
        for e in _emails_in(r[0]):
            if e not in found: found.append(e)
    take(_try_fetch(url))
    if len(found) < 5 and rest:
        with ThreadPoolExecutor(4) as ex:
            for r in ex.map(_try_fetch, rest):
                take(r)
    return {"emails": found[:5], "checked": checked}

# ---------------------------------------------------------------- website audit
def audit_site(url):
    url = norm_url(url)
    r = {"url": url, "ok": False, "issues": [], "score": 0}
    try:
        html, final, secs = fetch_text(url, timeout=20)
    except Exception as ex:
        r["issues"].append(f"Site didn't load ({type(ex).__name__}) - broken or offline website")
        r["score"] = 40
        return r
    r["ok"] = True
    r["finalUrl"] = final
    r["loadSeconds"] = round(secs, 1)
    low = html.lower()
    score = 0
    if not final.lower().startswith("https://"):
        r["issues"].append("No HTTPS - browsers show 'Not secure'"); score += 15
    if 'name="viewport"' not in low and "name='viewport'" not in low:
        r["issues"].append("Not mobile-friendly (no viewport tag)"); score += 20
    if secs > 3:
        r["issues"].append(f"Slow: {secs:.1f}s to load the page"); score += 10
    years = [int(y) for y in re.findall(r"(?:©|&copy;|copyright)\s*(?:\d{4}\s*[-–]\s*)?((?:19|20)\d{2})", low)]
    if years and max(years) < time.localtime().tm_year - 2:
        r["issues"].append(f"Looks outdated (copyright {max(years)})"); score += 10
    if "<title>" not in low or re.search(r"<title>\s*</title>", low):
        r["issues"].append("Missing page title (bad for Google)"); score += 5
    if 'name="description"' not in low:
        r["issues"].append("No meta description (bad for Google)"); score += 5
    if any(k in low for k in ("wixsite.com", "weebly.com", "blogspot.", "sites.google.com")) or \
       any(k in final for k in ("wixsite.com", "weebly.com", "blogspot.", "sites.google.com", "facebook.com")):
        r["issues"].append("Free subdomain / builder site - upgrade opportunity"); score += 10
    if "tel:" not in low:
        r["issues"].append("No click-to-call phone link"); score += 5
    r["score"] = score
    return r

# ---------------------------------------------------------------- web server
HTML_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app.html")

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("  " + fmt % args + "\n")

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            with open(HTML_PATH, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if self.path.startswith("/static/"):
            name = os.path.basename(self.path.split("?")[0])
            fp = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static", name)
            if os.path.isfile(fp):
                ctype = "application/javascript" if name.endswith(".js") else "text/css" if name.endswith(".css") else "application/octet-stream"
                with open(fp, "rb") as f:
                    return self._send(200, f.read(), ctype + "; charset=utf-8")
        if self.path == "/api/health":
            import assistant
            c = assistant.cfg()
            return self._send(200, {"ok": True, "usage": assistant.usage(), "caps": c["caps"],
                                    "autopilotLastRun": c.get("lastRun"), "autopilotRunning": assistant.state["running"],
                                    "cachedPages": len(_site_cache)})
        if self.path == "/api/meta":
            return self._send(200, {"categories": list(OSM_TAGS.keys()),
                                    "envKey": bool(os.environ.get("GOOGLE_PLACES_API_KEY")), "envSerp": bool(os.environ.get("SERPAPI_KEY"))})
        # GET endpoints for status/config reads
        if self.path == "/api/imap/status":
            import imap_monitor
            return self._send(200, imap_monitor.handle("/api/imap/status", {}))
        if self.path.startswith("/api/sheets/status"):
            import sheets_export
            return self._send(200, sheets_export.handle("/api/sheets/status", {}))
        if self.path.startswith("/api/webcrawler/schedule"):
            import webcrawler
            return self._send(200, webcrawler.handle("/api/webcrawler/schedule", {}))
        if self.path.startswith("/api/suppression"):
            import pipeline
            return self._send(200, pipeline.handle(self.path.split("?")[0], {}))
        # ── NEW: Server-Sent Events stream (real-time job/enrichment progress) ─
        if self.path == "/api/events/stream":
            import db as _db
            import queue as _queue
            q = _db.subscribe_events()
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            # Replay last 20 events for reconnect
            for ev in _db.recent_events(20):
                try:
                    self.wfile.write(f"data: {json.dumps(ev)}\n\n".encode())
                    self.wfile.flush()
                except Exception:
                    return
            while True:
                try:
                    payload = q.get(timeout=25)
                    self.wfile.write(f"data: {payload}\n\n".encode())
                    self.wfile.flush()
                except _queue.Empty:
                    # Send a keepalive comment
                    try:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
                    except Exception:
                        return
                except Exception:
                    return
        # ── NEW: DB leads GET (read-only quick access) ─────────────────────
        if self.path.startswith("/api/db/"):
            import db as _db
            return self._send(200, _db.handle(self.path, {}))
        # ── NEW: Knowledge base GET (file listing / content) ──────────────
        if self.path.startswith("/api/knowledge/"):
            import knowledge as _kb
            return self._send(200, _kb.handle(self.path, {}))
        # ── NEW: Webhooks GET (list / log) ─────────────────────────────────
        if self.path.startswith("/api/webhooks/"):
            import webhooks as _wh
            return self._send(200, _wh.handle(self.path, {}))
        # ── NEW: Auth status GET ──────────────────────────────────────────
        if self.path.startswith("/api/auth/"):
            import auth as _auth
            return self._send(200, _auth.handle(self.path, {}))
        self._send(404, {"error": "Not found"})

    def do_POST(self):
        # Only accept requests from this app (blocks other websites from using your key)
        origin = self.headers.get("Origin", "")
        if origin and urllib.parse.urlparse(origin).hostname not in ("localhost", "127.0.0.1"):
            return self._send(403, {"error": "Forbidden"})
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
            if self.path == "/api/search":
                src = req.get("source", "osm")
                if src == "google":
                    key = req.get("apiKey") or os.environ.get("GOOGLE_PLACES_API_KEY", "")
                    leads = google_search(key, req.get("query", ""), req.get("location", ""),
                                          req.get("pages", 3), req.get("deep", 0))
                elif src == "serpapi":
                    key = req.get("serpKey") or os.environ.get("SERPAPI_KEY", "")
                    leads = serpapi_search(key, req.get("query", ""), req.get("location", ""), req.get("pages", 3))
                else:
                    leads = osm_search(req.get("category", ""), req.get("location", ""))
                return self._send(200, {"leads": leads})
            if self.path == "/api/test-key":
                key = req.get("apiKey") or os.environ.get("GOOGLE_PLACES_API_KEY", "")
                return self._send(200, {"message": google_test_key(key)})
            if self.path in ("/api/identity", "/api/owner", "/api/sender-check"):
                import identity as ID
                if self.path == "/api/identity":
                    return self._send(200, ID.identity(req.get("lead", {}), bool(req.get("owner")), bool(req.get("useAI"))))
                if self.path == "/api/owner":
                    return self._send(200, ID.find_owner(req.get("lead", {}), bool(req.get("useAI"))))
                return self._send(200, ID.sender_check(req.get("email", "")))
            if self.path.startswith("/api/hiring/"):
                import hiring
                return self._send(200, hiring.handle(self.path, req))
            if self.path.startswith("/api/jobsearch"):
                import jobsearch
                return self._send(200, jobsearch.handle(self.path, req))
            if self.path.startswith("/api/career"):
                import career
                return self._send(200, career.handle(self.path, req))
            if self.path.startswith("/api/opportunities"):
                import opportunities
                return self._send(200, opportunities.handle(self.path, req))
            if self.path.startswith(("/api/suppression", "/api/dedup/", "/api/bp-config")):
                import pipeline
                return self._send(200, pipeline.handle(self.path, req))
            if self.path.startswith("/api/emailverify"):
                import emailverify
                return self._send(200, emailverify.handle(self.path, req))
            if self.path.startswith("/api/dorking"):
                import dorking
                return self._send(200, dorking.handle(self.path, req))
            if self.path.startswith("/api/pagespeed"):
                import pagespeed
                return self._send(200, pagespeed.handle(self.path, req))
            if self.path.startswith("/api/sheets"):
                import sheets_export
                return self._send(200, sheets_export.handle(self.path, req))
            if self.path.startswith("/api/imap"):
                import imap_monitor
                return self._send(200, imap_monitor.handle(self.path, req))
            if self.path.startswith("/api/webcrawler"):
                import webcrawler
                return self._send(200, webcrawler.handle(self.path, req))
            if self.path.startswith("/api/dashboard"):
                import dashboard
                return self._send(200, dashboard.handle(self.path, req))
            if self.path.startswith(("/api/assistant/", "/api/pool/", "/api/contacts/")):
                import assistant
                return self._send(200, assistant.handle(self.path, req))
            # ── NEW: SQLite CRM ──────────────────────────────────────────────
            if self.path.startswith("/api/db/"):
                import db
                return self._send(200, db.handle(self.path, req))
            # ── NEW: Background job queue ────────────────────────────────────
            if self.path.startswith("/api/jobs/"):
                import jobs, db
                jobs.start()
                return self._send(200, jobs.handle(self.path, req))
            # ── NEW: Enrichment (social handles, tech stack, decision maker, Hunter, Apollo) ─
            if self.path.startswith("/api/enrich/"):
                import enrich
                return self._send(200, enrich.handle(self.path, req))
            # ── NEW: B2B international buyer discovery ───────────────────────
            if self.path.startswith("/api/b2b/"):
                import b2b
                return self._send(200, b2b.handle(self.path, req))
            # ── NEW: AI strategy generation (30-day / 90-day plan) ──────────
            if self.path.startswith("/api/strategy/"):
                import strategy
                return self._send(200, strategy.handle(self.path, req))
            # ── NEW: Inbound lead capture + reply classification ──────────────
            if self.path.startswith("/api/inbound/"):
                import inbound
                return self._send(200, inbound.handle(self.path, req))
            # ── NEW: Knowledge base (principal-awareness) ─────────────────────
            if self.path.startswith("/api/knowledge/"):
                import knowledge
                return self._send(200, knowledge.handle(self.path, req))
            # ── NEW: CRM webhooks (Zapier / Make / HubSpot) ───────────────────
            if self.path.startswith("/api/webhooks/"):
                import webhooks
                return self._send(200, webhooks.handle(self.path, req))
            # ── NEW: Campaign optimization + feedback loop ────────────────────
            if self.path.startswith("/api/campaign/"):
                import campaign
                return self._send(200, campaign.handle(self.path, req))
            # ── NEW: Indeed hiring signals ────────────────────────────────────
            if self.path.startswith("/api/indeed/"):
                import indeed
                return self._send(200, indeed.handle(self.path, req))
            # ── NEW: WhatsApp real sending (Baileys bridge) ───────────────────
            if self.path.startswith("/api/whatsapp/"):
                import whatsapp_bridge
                return self._send(200, whatsapp_bridge.handle(self.path, req))
            # ── NEW: AI Voice call agent (n8n / Vapi / Twilio) ───────────────
            if self.path.startswith("/api/voice/"):
                import voice_agent
                return self._send(200, voice_agent.handle(self.path, req))
            # ── NEW: Playwright deep scan ─────────────────────────────────────
            if self.path.startswith("/api/deepscan/"):
                import deepscan
                return self._send(200, deepscan.handle(self.path, req))
            # ── NEW: AI style learning ────────────────────────────────────────
            if self.path.startswith("/api/style/"):
                import style_learning
                return self._send(200, style_learning.handle(self.path, req))
            # ── NEW: Multi-user auth (register/login/logout/users) ───────────
            if self.path.startswith("/api/auth/"):
                import auth
                return self._send(200, auth.handle(self.path, req))
            if self.path == "/api/analyze":
                import analyzer
                keys = {"google": req.get("apiKey") or os.environ.get("GOOGLE_PLACES_API_KEY", ""),
                        "serp": req.get("serpKey") or os.environ.get("SERPAPI_KEY", "")}
                return self._send(200, analyzer.analyze(req.get("lead", {}), req.get("source", "google"),
                                                        keys, int(req.get("radius", 3000))))
            if self.path in ("/api/cities", "/api/market-sample", "/api/send-email"):
                import nichefinder as NF
                if self.path == "/api/cities":
                    return self._send(200, {"cities": NF.top_cities(req.get("country", "United States"),
                                                                    req.get("minPop", 100000), req.get("limit", 150)),
                                            "countries": list(NF.COUNTRIES)})
                if self.path == "/api/market-sample":
                    keys = {"google": req.get("apiKey") or os.environ.get("GOOGLE_PLACES_API_KEY", ""),
                            "serp": req.get("serpKey") or os.environ.get("SERPAPI_KEY", "")}
                    return self._send(200, NF.market_sample(req.get("source", "google"), keys,
                                                            req.get("niche", ""), req.get("city", "")))
                return self._send(200, NF.send_email(req.get("smtp", {}), req.get("to", ""),
                                                     req.get("subject", ""), req.get("body", ""), req.get("replyTo", "")))
            if self.path == "/api/ai":
                import analyzer
                ai = req.get("ai", {}) or {}
                if ai.get("provider", "pool") == "pool":
                    import assistant, ai_pool
                    r = ai_pool.complete(req.get("prompt", ""), assistant.cfg().get("pool"))
                    return self._send(200, r)
                return self._send(200, {"text": analyzer.ai_write(req.get("prompt", ""), ai)})
            if self.path == "/api/emails":
                return self._send(200, find_emails(req.get("url", "")))
            if self.path == "/api/audit":
                return self._send(200, audit_site(req.get("url", "")))
            if self.path == "/api/bulk-emails":
                urls = req.get("urls", [])[:60]
                with ThreadPoolExecutor(8) as ex:
                    res = dict(zip(urls, ex.map(lambda u: find_emails(u)["emails"], urls)))
                return self._send(200, {"results": res})
            self._send(404, {"error": "Not found"})
        except Exception as ex:
            self._send(400, {"error": str(ex)})

def main():
    srv = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    import assistant
    assistant.start()
    # Start background job worker (db.py + jobs.py)
    import db, jobs, webhooks, knowledge
    db.init()
    jobs.start()
    # Wire webhook auto-fire on lead stage changes
    webhooks.patch_db_for_webhooks()
    # Bootstrap knowledge base (create .leadfinder/knowledge/ if first run)
    knowledge.bootstrap()
    # Scaffold WhatsApp bridge files (Node.js server.js + package.json)
    try:
        import whatsapp_bridge
        whatsapp_bridge._scaffold_bridge()
    except Exception:
        pass
    url = f"http://localhost:{PORT}"
    print(f"\n  LeadFinder is running at {url}\n  Press Ctrl+C to stop.\n")
    if "--no-browser" not in sys.argv:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n  Stopped.")

if __name__ == "__main__":
    main()
