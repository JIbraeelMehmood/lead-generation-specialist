"""
Prospect analysis for LeadFinder:
  * finds nearby competitors (same business type)
  * checks each one's digital presence: website, mobile-friendly, social media,
    mobile app, online booking / ordering, WhatsApp
  * optional AI writer (free: Ollama on your PC, or any OpenAI-compatible API)
"""
import json, math, re, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import leadfinder as LF

# ---------------------------------------------------------------- distance
def km_between(a_lat, a_lng, b_lat, b_lng):
    if None in (a_lat, a_lng, b_lat, b_lng): return None
    r = 6371.0
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = p2 - p1, math.radians(b_lng - a_lng)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(h)), 2)

# ---------------------------------------------------------------- competitors
def competitors_google(api_key, query, lat, lng, radius_m):
    LF._spend("google")
    body = {"textQuery": query, "pageSize": 20,
            "locationBias": {"circle": {"center": {"latitude": lat, "longitude": lng}, "radius": float(radius_m)}}}
    try:
        res = LF.http_json("https://places.googleapis.com/v1/places:searchText", body, {
            "Content-Type": "application/json", "X-Goog-Api-Key": api_key, "X-Goog-FieldMask": LF.G_FIELDS})
    except RuntimeError as ex:
        raise RuntimeError(LF._google_error(str(ex)))
    return [LF._g_convert(p, query) for p in res.get("places", [])]

def competitors_serpapi(api_key, query, lat, lng):
    LF._spend("serpapi")
    params = {"engine": "google_maps", "type": "search", "api_key": api_key, "q": query, "ll": f"@{lat},{lng},14z"}
    res = LF.http_json("https://serpapi.com/search.json?" + urllib.parse.urlencode(params), timeout=90)
    if res.get("error"): raise RuntimeError("SerpApi: " + res["error"])
    return [LF._serp_convert(p, query) for p in (res.get("local_results") or [])]

def competitors_osm(category, lat, lng, radius_m):
    tags = LF.OSM_TAGS.get(category)
    if not tags: return []
    parts = "".join(f'nwr[{t}]["name"](around:{int(radius_m)},{lat},{lng});' for t in tags)
    q = f"[out:json][timeout:60];({parts});out center tags 60;"
    res = LF.http_json("https://overpass-api.de/api/interpreter", urllib.parse.urlencode({"data": q}).encode(),
                       {"Content-Type": "application/x-www-form-urlencoded"}, timeout=90)
    return [LF._osm_convert(el, category) for el in res.get("elements", [])]

def find_competitors(lead, source, keys, radius_m=3000, limit=6):
    keys = {"google": keys.get("google") or LF._stored_key("google"), "serp": keys.get("serp") or LF._stored_key("serp")}
    lat, lng = lead.get("lat"), lead.get("lng")
    if lat is None or lng is None:
        raise RuntimeError("This business has no map location, so nearby competitors can't be found. Search it again to refresh.")
    query = lead.get("searchQuery") or lead.get("category") or ""
    if source == "google":
        items = competitors_google(keys.get("google"), query, lat, lng, radius_m)
    elif source == "serpapi":
        items = competitors_serpapi(keys.get("serp"), query, lat, lng)
    else:
        items = competitors_osm(lead.get("category"), lat, lng, radius_m)
    out, name_l = [], (lead.get("name") or "").strip().lower()
    for c in items:
        if c["id"] == lead.get("id") or (c.get("name") or "").strip().lower() == name_l:
            continue
        c["distanceKm"] = km_between(lat, lng, c.get("lat"), c.get("lng"))
        if c["distanceKm"] is not None and c["distanceKm"] > radius_m / 1000 * 2:
            continue
        out.append(c)
    # strongest competitors first: most reviews, then closest
    out.sort(key=lambda c: (-(c.get("reviews") or 0), c.get("distanceKm") or 99))
    return out[:limit]

# ---------------------------------------------------------------- digital presence
SOCIAL = {
    "facebook": r"https?://(?:www\.|m\.|web\.)?facebook\.com/(?!sharer|share|plugins|dialog|tr\b|2008)[A-Za-z0-9_.\-/]+",
    "instagram": r"https?://(?:www\.)?instagram\.com/(?!p/|explore)[A-Za-z0-9_.]+",
    "tiktok": r"https?://(?:www\.)?tiktok\.com/@[A-Za-z0-9_.]+",
    "youtube": r"https?://(?:www\.)?youtube\.com/(?:@|channel/|c/|user/)[A-Za-z0-9_\-]+",
    "linkedin": r"https?://(?:[a-z]+\.)?linkedin\.com/(?:company|in)/[A-Za-z0-9_\-]+",
    "x": r"https?://(?:www\.)?(?:twitter|x)\.com/(?!intent|share|home)[A-Za-z0-9_]+",
}
APPS = {
    "ios": r"https?://apps\.apple\.com/[^\s\"'<>]+",
    "android": r"https?://play\.google\.com/store/apps/details\?id=[A-Za-z0-9_.]+",
}
BOOKING = ["calendly.com", "booksy.com", "fresha.com", "vagaro.com", "setmore.com", "acuityscheduling",
           "squareup.com/appointments", "simplybook", "zocdoc.com", "opentable.", "resy.com", "sevenrooms",
           "mindbodyonline", "glofox", "booking.com", "book now", "book online", "book an appointment",
           "schedule an appointment", "request an appointment", "reserve a table", "make a reservation"]
ORDERING = ["ubereats.com", "doordash.com", "grubhub.com", "deliveroo.", "just-eat.", "justeat.", "foodpanda.",
            "talabat.", "careem", "order online", "order now", "add to cart", "shopify", "woocommerce", "checkout"]
FORMS = ["<form", "get a quote", "free quote", "request a quote", "contact form", "get an estimate"]
CHAT = ["wa.me/", "api.whatsapp.com", "tawk.to", "intercom", "livechat", "crisp.chat", "tidio"]

def presence_from_url(url):
    """Check a business website and report what digital channels it has."""
    p = {"website": bool(url), "siteLoads": False, "https": False, "mobile": False,
         "socials": {}, "apps": {}, "booking": False, "ordering": False, "quoteForm": False,
         "chat": False, "socialOnly": False}
    if not url: return p
    u = LF.norm_url(url)
    host = urllib.parse.urlparse(u).netloc.lower()
    for name, rx in SOCIAL.items():
        if re.match(rx, u, re.I):
            p["socials"][name] = u
            p["socialOnly"] = True
    if p["socialOnly"]:
        p["website"] = False
        return p
    try:
        html, final, _ = LF.fetch_text(u, timeout=12)
    except Exception:
        return p
    p["siteLoads"] = True
    p["https"] = final.lower().startswith("https://")
    low = html.lower()
    p["mobile"] = 'name="viewport"' in low or "name='viewport'" in low
    for name, rx in SOCIAL.items():
        m = re.search(rx, html, re.I)
        if m: p["socials"][name] = m.group(0).rstrip("/\"'")
    for name, rx in APPS.items():
        m = re.search(rx, html, re.I)
        if m: p["apps"][name] = m.group(0)
    p["booking"] = any(k in low for k in BOOKING)
    p["ordering"] = any(k in low for k in ORDERING)
    p["quoteForm"] = any(k in low for k in FORMS)
    p["chat"] = any(k in low for k in CHAT)
    if any(k in host for k in ("wixsite.com", "weebly.com", "blogspot.", "sites.google.com", "business.site")):
        p["freeBuilder"] = True
    return p

def digital_score(p, reviews=0, rating=None):
    s = 0
    if p.get("website") and p.get("siteLoads"): s += 30
    if p.get("mobile"): s += 8
    if p.get("https"): s += 4
    s += min(24, 8 * len(p.get("socials", {})))
    if p.get("apps"): s += 10
    if p.get("booking") or p.get("ordering") or p.get("quoteForm"): s += 10
    if p.get("chat"): s += 4
    r = reviews or 0
    s += 10 if r >= 100 else 6 if r >= 30 else 3 if r >= 10 else 0
    return min(100, s)

def analyze(lead, source, keys, radius_m=3000):
    t0 = time.time()
    try:
        comps = find_competitors(lead, source, keys, radius_m)
        comp_error = ""
    except Exception as ex:
        comps, comp_error = [], str(ex)
    everyone = [lead] + comps
    with ThreadPoolExecutor(8) as ex:
        pres = list(ex.map(lambda b: presence_from_url(b.get("website")), everyone))
    rows = []
    for b, p in zip(everyone, pres):
        if b.get("social"):  # social link known from the map data
            for name in SOCIAL:
                if name in b["social"].lower() and name not in p["socials"]:
                    p["socials"][name] = b["social"]
        rows.append({
            "id": b.get("id"), "name": b.get("name"), "address": b.get("address"),
            "phone": b.get("phone"), "website": b.get("website"), "rating": b.get("rating"),
            "reviews": b.get("reviews") or 0, "distanceKm": b.get("distanceKm"),
            "mapsUrl": b.get("mapsUrl"), "presence": p,
            "digitalScore": digital_score(p, b.get("reviews"), b.get("rating")),
        })
    return {"lead": rows[0], "competitors": rows[1:], "competitorError": comp_error,
            "radiusKm": radius_m / 1000, "seconds": round(time.time() - t0, 1),
            "analyzedAt": time.strftime("%Y-%m-%d")}

# ---------------------------------------------------------------- AI writer (free options)
def ai_write(prompt, cfg):
    provider = (cfg or {}).get("provider", "ollama")
    model = (cfg or {}).get("model") or ("llama3.2" if provider == "ollama" else "")
    system = ("You are a friendly, honest sales coach for a freelance web designer. "
              "Write short, natural, specific outreach. Never invent facts, numbers or statistics "
              "that are not in the data given. Use plain language.")
    if provider == "ollama":
        base = (cfg.get("baseUrl") or "http://localhost:11434").rstrip("/")
        try:
            res = LF.http_json(base + "/api/chat", {"model": model, "stream": False, "messages": [
                {"role": "system", "content": system}, {"role": "user", "content": prompt}]}, timeout=300)
        except Exception as ex:
            raise RuntimeError(f"Couldn't reach Ollama at {base}. Is Ollama running and is the model '{model}' "
                               f"downloaded? (run: ollama pull {model}) Details: {ex}")
        return (res.get("message") or {}).get("content", "").strip()
    base = (cfg.get("baseUrl") or "").rstrip("/")
    if not base or not model:
        raise RuntimeError("Set the AI base URL and model name in Settings.")
    headers = {"Content-Type": "application/json"}
    if cfg.get("apiKey"): headers["Authorization"] = "Bearer " + cfg["apiKey"]
    res = LF.http_json(base + "/chat/completions", {"model": model, "temperature": 0.7, "messages": [
        {"role": "system", "content": system}, {"role": "user", "content": prompt}]}, headers, timeout=180)
    return res["choices"][0]["message"]["content"].strip()
