"""
Digital identity for LeadFinder:
  * identity score: what a business has / is missing online (website, Google profile,
    social, booking, WhatsApp, professional email, app fit)
  * owner finder: About/Team pages (+ optional free AI) and UK Companies House directors
  * sender check: SPF / DKIM / DMARC / MX of YOUR sending domain
"""
import base64, html as htmllib, json, re, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor
import leadfinder as LF

# ---------------------------------------------------------------- app fit
APP_FIT = [
    ("High", r"restaurant|cafe|coffee|bakery|pizza|burger|takeaway|fast food|food|juice|dessert",
     "Repeat customers who reorder", "Installable web app (PWA) with menu, online ordering and loyalty points"),
    ("High", r"gym|fitness|yoga|pilates|crossfit|martial|boxing|dance|trainer",
     "Members visit weekly", "PWA with class booking, membership and progress tracking"),
    ("High", r"salon|barber|hair|nail|spa|lash|brow|beauty|massage|groom",
     "Clients rebook every few weeks", "PWA with online booking, reminders and loyalty"),
    ("High", r"dent|clinic|doctor|physio|chiro|vet|medical|therap|optic",
     "Patients return for appointments", "PWA with appointment booking and reminders"),
    ("High", r"school|tutor|academy|daycare|nursery|driving school|lesson",
     "Students and parents check in often", "PWA with timetables, notices and fee reminders"),
    ("High", r"car wash|laundry|dry clean|detailing",
     "Frequent repeat service", "PWA with booking and punch-card loyalty"),
    ("Medium", r"hotel|guest|resort|real estate|estate agent|pharmacy|grocery|supermarket|store|shop|boutique",
     "Some repeat visits", "Start with a website; add a PWA later for bookings, listings or loyalty"),
    ("Low", r"plumb|electric|roof|contract|builder|construct|hvac|paint|landscap|lawyer|attorney|account|tax|insur|mov|pest|lock",
     "Customers need them occasionally", "No app needed: website with click-to-call and quote form works best"),
]
def app_fit(lead):
    txt = f"{lead.get('category','')} {lead.get('searchQuery','')} {lead.get('name','')}".lower()
    for level, rx, why, idea in APP_FIT:
        if re.search(rx, txt):
            if level == "Medium" and (lead.get("reviews") or 0) >= 200: level = "High"
            return {"level": level, "why": why, "idea": idea}
    return {"level": "Low", "why": "Not a typical repeat-visit business", "idea": "Website first; an app is rarely worth it here"}

# ---------------------------------------------------------------- email info
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "aol.com", "icloud.com",
             "ymail.com", "msn.com", "gmx.com", "yandex.com", "proton.me", "protonmail.com", "mail.com"}
def mail_provider(hosts):
    h = " ".join(hosts).lower()
    for k, v in (("google", "Google Workspace"), ("outlook", "Microsoft 365"), ("zoho", "Zoho Mail"),
                 ("secureserver", "GoDaddy email"), ("titan", "Titan email"), ("mimecast", "Mimecast")):
        if k in h: return v
    return "Other / web host email" if hosts else ""

def email_info(lead, domain):
    import contacts
    emails = [lead.get("email")] + list(lead.get("emailsFound") or [])
    emails = [e for e in emails if e]
    out = {"emails": emails, "professional": False, "freeProvider": False, "provider": "", "domainMail": None}
    if any(e.split("@")[-1].lower() not in FREE_MAIL for e in emails):
        out["professional"] = True
    if emails and all(e.split("@")[-1].lower() in FREE_MAIL for e in emails):
        out["freeProvider"] = True
    if domain:
        m = contacts.mx(domain)
        out["domainMail"] = m["ok"]
        out["provider"] = mail_provider(m["hosts"])
        if m["ok"] and not out["freeProvider"]:
            out["professional"] = True
    return out

# ---------------------------------------------------------------- identity score
def identity(lead, owner=False, use_ai=False):
    import analyzer, contacts
    web = lead.get("website") or ""
    p = analyzer.presence_from_url(web)
    if lead.get("social"):
        for name in analyzer.SOCIAL:
            if name in lead["social"].lower(): p["socials"].setdefault(name, lead["social"])
    man = lead.get("manualPresence") or {}
    for k in ("facebook", "instagram", "tiktok"):
        if man.get(k): p["socials"].setdefault(k, "(found by hand)")
    domain = contacts.domain_of(web) if p.get("siteLoads") else ""
    em = email_info(lead, domain)
    has_manifest = False
    if p.get("siteLoads"):
        try:
            h, _, _ = LF.fetch_text(LF.norm_url(web), timeout=10)
            has_manifest = 'rel="manifest"' in h.lower() or "rel='manifest'" in h.lower()
        except Exception:
            pass
    fit = app_fit(lead)
    reviews, rating = lead.get("reviews") or 0, lead.get("rating") or 0
    on_google = str(lead.get("source", "")).startswith("Google")
    parts = []
    def part(key, label, pts, got, tip):
        parts.append({"key": key, "label": label, "max": pts, "points": pts if got else 0, "ok": bool(got), "tip": tip})
    site_ok = p.get("website") and p.get("siteLoads")
    part("website", "Working website", 25, site_ok,
         "Build a mobile-friendly website" if not p.get("website") else "Fix or rebuild the website (it doesn't load)" if not site_ok else "")
    part("quality", "Mobile-friendly and secure (HTTPS)", 10, site_ok and p.get("mobile") and p.get("https"),
         "Redesign for mobile, add HTTPS and speed up the site" if site_ok else "Included with a new website")
    part("google", "Google Business Profile", 15, on_google or man.get("google"),
         "Create and verify a Google Business Profile" if not on_google else "")
    part("reviews", "Strong reviews (4★+, 25+)", 5, rating >= 4 and reviews >= 25,
         "Set up a simple review-request routine (QR code / WhatsApp link)")
    part("social", "Social media page", 10, len(p["socials"]) >= 1, "Set up branded Facebook and Instagram pages")
    part("social2", "Two or more social channels", 5, len(p["socials"]) >= 2, "Add a second channel (Instagram, TikTok or LinkedIn)")
    part("booking", "Online booking, ordering or quote form", 10,
         p.get("booking") or p.get("ordering") or p.get("quoteForm") or man.get("booking"),
         "Add online booking / ordering / a quote form")
    part("chat", "WhatsApp or live chat", 5, p.get("chat"), "Add a WhatsApp chat button")
    part("email", "Professional email (name@business)", 10, em["professional"],
         "Set up a professional email on their own domain" if not em["freeProvider"] else "They use a free Gmail/Yahoo address: move to name@theirbusiness")
    app_ok = bool(p.get("apps")) or has_manifest or man.get("app")
    part("app", "App / installable web app", 5, app_ok or fit["level"] == "Low",
         fit["idea"] if fit["level"] != "Low" else "")
    score = sum(x["points"] for x in parts)
    res = {"score": score, "grade": "Weak" if score < 40 else "Basic" if score < 70 else "Strong",
           "parts": parts, "missing": [x["key"] for x in parts if not x["ok"]],
           "appFit": fit, "email": em, "presence": p, "hasManifest": has_manifest,
           "checkedAt": time.strftime("%Y-%m-%d")}
    if owner:
        try:
            res["owner"] = find_owner(lead, use_ai=use_ai)
        except Exception as ex:
            res["owner"] = {"name": "", "error": str(ex), "candidates": []}
    return res

# ---------------------------------------------------------------- owner finder
ROLE_WORDS = r"owner|co-owner|founder|co-founder|proprietor|principal|managing director|director|ceo|head chef|chef patron|lead dentist|practice owner|clinical director"
NAME = r"(?:Dr\.?\s+)?[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?(?:\s+[A-Z][a-z]+(?:[-'][A-Z]?[a-z]+)?){1,2}"
BAD = {"our", "the", "team", "contact", "about", "read", "more", "meet", "home", "services", "call", "book", "now", "us",
       "privacy", "policy", "terms", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
       "january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
       "november", "december", "street", "road", "avenue", "suite", "google", "facebook", "instagram", "free",
       "quote", "welcome", "company", "limited", "ltd", "llc", "inc", "group", "family", "business", "customer"}
PAGES = ["", "/about", "/about-us", "/our-story", "/team", "/our-team", "/meet-the-team", "/meet-us", "/who-we-are"]

def _text(html):
    html = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?i)<br\s*/?>|</(p|div|h\d|li|td)>", "\n", html)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", html))
    return re.sub(r"[ \t\r\f\v]+", " ", t)

def _clean(n, biz_words):
    n = re.sub(r"^Dr\.?\s+", "Dr. ", n.strip())
    words = [w.lower().strip(".") for w in n.split() if w.lower() != "dr."]
    if not words or any(w in BAD or w in biz_words for w in words): return ""
    if len(words) < 2: return ""
    return n

def owner_from_site(website, business=""):
    base = LF.norm_url(website)
    root = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(base))
    biz_words = {w.lower() for w in re.findall(r"[A-Za-z]+", business or "")}
    counts, where, texts = {}, {}, []
    urls = list(dict.fromkeys(base if not path else root + path for path in PAGES))
    def get(url):
        try:
            h, final, _ = LF.fetch_text(url, timeout=8)
            return h, final
        except Exception:
            return None
    pats = [
        (rf"(?:{ROLE_WORDS})\s*[,:\-–|]?\s*({NAME})", 1, 3),
        (rf"({NAME})\s*[,\-–|(]\s*(?:our\s+|the\s+)?(?:{ROLE_WORDS})", 1, 3),
        (rf"(?:founded|owned|started|run|established)\s+(?:in\s+\d{{4}}\s+)?by\s+({NAME})", 1, 4),
        (rf"(?:[Mm]y name is|[Hh]i,? I'?m|I am)\s+({NAME})", 1, 2),
    ]
    # fetch in two parallel waves; skip the second wave if the first already found a name
    for wave in (urls[:5], urls[5:]):
        if not wave or (len(texts) >= 4 and counts): break
        with ThreadPoolExecutor(4) as ex:
            pages = list(ex.map(get, wave))
        for r in pages:
            if not r: continue
            h, final = r
            t = _text(h)
            texts.append(t[:4000])
            for rx, g, weight in pats:
                for m in re.finditer(rx, t):
                    n = _clean(m.group(g), biz_words)
                    if n:
                        counts[n] = counts.get(n, 0) + weight
                        ctx = t[max(0, m.start() - 40): m.end() + 40].replace("\n", " ").strip()
                        where.setdefault(n, (final, ctx))
    cands = sorted(counts.items(), key=lambda x: -x[1])[:5]
    return [{"name": n, "score": s, "source": "website", "url": where[n][0], "context": where[n][1]} for n, s in cands], texts

def owner_with_ai(texts, business):
    import assistant, ai_pool
    pool = assistant.cfg().get("pool")
    if not pool: return None
    blob = "\n---\n".join(texts)[:6000]
    r = ai_pool.complete(
        f"Business: {business}\nText from its website:\n{blob}\n\n"
        "Who is the owner, founder or main person of this business? Answer ONLY with JSON like "
        '{"name": "First Last", "role": "Owner"} using a name that appears in the text, or {"name": null} if none is clearly stated.',
        pool, "You extract facts from text. Never guess names that are not in the text.", 120)
    m = re.search(r"\{.*\}", r["text"], re.S)
    if not m: return None
    try:
        d = json.loads(m.group(0))
    except Exception:
        return None
    n = (d.get("name") or "").strip()
    if n and n.split()[-1] in blob:
        return {"name": n, "role": d.get("role") or "", "source": "website (AI read)", "score": 5}
    return None

UK_POSTCODE = re.compile(r"\b([A-Z]{1,2}\d[A-Z\d]?)\s*(\d[A-Z]{2})\b", re.I)
def is_uk(lead):
    a = (lead.get("address") or "")
    return bool(re.search(r"\b(UK|United Kingdom|England|Scotland|Wales|Northern Ireland)\b", a) or
                (UK_POSTCODE.search(a) and "USA" not in a))

def _ch(path, key):
    auth = base64.b64encode((key + ":").encode()).decode()
    return LF.http_json("https://api.company-information.service.gov.uk" + path,
                        headers={"Authorization": "Basic " + auth}, timeout=20)

def _norm_biz(s):
    s = re.sub(r"\b(ltd|limited|llp|plc|the|and|&)\b", " ", (s or "").lower())
    return set(re.findall(r"[a-z0-9]+", s))

def owner_companies_house(lead, key):
    if not key: return []
    q = re.sub(r"\s+-\s+.*$", "", lead.get("name", ""))
    res = _ch("/search/companies?" + urllib.parse.urlencode({"q": q, "items_per_page": 10}), key)
    want = _norm_biz(q)
    pc = UK_POSTCODE.search(lead.get("address") or "")
    best, best_s = None, 0
    for it in res.get("items", []):
        if it.get("company_status") != "active": continue
        have = _norm_biz(it.get("title"))
        s = len(want & have) / max(1, len(want))
        snip = (it.get("address_snippet") or "").upper()
        if pc and pc.group(1).upper() in snip: s += 0.6
        if s > best_s: best, best_s = it, s
    if not best or best_s < 0.6: return []
    offs = _ch(f"/company/{best['company_number']}/officers?items_per_page=35", key)
    out = []
    for o in offs.get("items", []):
        if o.get("resigned_on") or o.get("officer_role") not in ("director", "llp-designated-member", "llp-member"):
            continue
        raw = o.get("name", "")
        if "," in raw:
            last, first = [x.strip() for x in raw.split(",", 1)]
            first = re.sub(r"^(Mr|Mrs|Ms|Miss|Dr)\.?\s+", "", first, flags=re.I)
            nm = f"{first.split()[0].title()} {last.title()}" if first else last.title()
        else:
            nm = raw.title()
        out.append({"name": nm, "role": o.get("officer_role", "").replace("-", " ").title(),
                    "source": "Companies House", "score": 4,
                    "url": f"https://find-and-update.company-information.service.gov.uk/company/{best['company_number']}/officers",
                    "company": best.get("title")})
    return out[:4]

US_STATES = {"AL","AK","AZ","AR","CA","CO","CT","DE","FL","GA","HI","ID","IL","IN","IA","KS","KY","LA","ME","MD","MA","MI","MN",
             "MS","MO","MT","NE","NV","NH","NJ","NM","NY","NC","ND","OH","OK","OR","PA","RI","SC","SD","TN","TX","UT","VT","VA",
             "WA","WV","WI","WY","DC"}
def research_links(lead):
    name = lead.get("name", "")
    links = [{"label": "Google: owner", "url": "https://www.google.com/search?q=" + urllib.parse.quote(f'"{name}" owner OR founder')},
             {"label": "LinkedIn (view only)", "url": "https://www.google.com/search?q=" + urllib.parse.quote(f'site:linkedin.com "{name}"')}]
    m = re.search(r",\s*([A-Z]{2})\s+\d{5}", lead.get("address") or "")
    if m and m.group(1) in US_STATES:
        links.append({"label": f"{m.group(1)} business registry (OpenCorporates)",
                      "url": "https://opencorporates.com/companies?" + urllib.parse.urlencode(
                          {"q": name, "jurisdiction_code": "us_" + m.group(1).lower()})})
    if is_uk(lead):
        links.append({"label": "Companies House search", "url": "https://find-and-update.company-information.service.gov.uk/search/companies?q=" + urllib.parse.quote(name)})
    return links

def find_owner(lead, use_ai=False):
    import assistant
    key = assistant.cfg()["keys"].get("ch", "")
    cands, texts = [], []
    if lead.get("website") and not re.search(r"facebook|instagram|linktr", lead["website"], re.I):
        cands, texts = owner_from_site(lead["website"], lead.get("name"))
    if not cands and use_ai and texts:
        try:
            a = owner_with_ai(texts, lead.get("name"))
            if a: cands.append(a)
        except Exception:
            pass
    err = ""
    if is_uk(lead):
        try:
            cands += owner_companies_house(lead, key)
        except Exception as ex:
            err = f"Companies House: {ex}"
        if not key: err = "Add a free Companies House key in Settings to look up UK directors."
    # merge the same person found in several sources (e.g. website + Companies House)
    merged = []
    for c in cands:
        key = re.sub(r"^Dr\.?\s+", "", c["name"]).lower().split()
        twin = next((m for m in merged if re.sub(r"^Dr\.?\s+", "", m["name"]).lower().split()[-1:] == key[-1:]
                     and re.sub(r"^Dr\.?\s+", "", m["name"]).lower().split()[:1] == key[:1]), None)
        if twin:
            twin["score"] += c.get("score", 0) + 3
            if c["source"] not in twin["source"]: twin["source"] += " + " + c["source"]
            twin.setdefault("role", c.get("role", ""))
            if not twin.get("role"): twin["role"] = c.get("role", "")
            twin["confirmed"] = True
        else:
            merged.append(dict(c))
    cands = sorted(merged, key=lambda c: -c.get("score", 0))
    best = cands[0] if cands else None
    name = best["name"] if best else ""
    first = re.sub(r"^Dr\.?\s+", "", name).split()[0] if name else ""
    if name.startswith("Dr"): first = "Dr. " + name.split()[-1]
    return {"name": name, "first": first, "role": (best or {}).get("role", ""), "source": (best or {}).get("source", ""),
            "candidates": cands, "links": research_links(lead), "note": err}

# ---------------------------------------------------------------- sender domain check
def sender_check(email_or_domain):
    import contacts
    d = email_or_domain.split("@")[-1].strip().lower()
    out = {"domain": d, "checks": [], "ok": True}
    def add(name, status, detail, fix=""):
        out["checks"].append({"name": name, "status": status, "detail": detail, "fix": fix})
        if status == "fail": out["ok"] = False
    if d in FREE_MAIL:
        add("Own domain", "warn", f"You are sending from a free {d} address.",
            "Free addresses work for low volume, but a separate domain (e.g. yourstudio-mail.com) with Google Workspace or Zoho looks more professional and protects your main address.")
        return out
    def txt(name):
        r = contacts._doh(name, "TXT")
        return [a["data"].strip('"').replace('" "', "") for a in (r or {}).get("Answer", []) if a.get("type") == 16]
    m = contacts.mx(d)
    add("MX (can receive replies)", "pass" if m["ok"] else "fail",
        ", ".join(m["hosts"]) or m["note"], "" if m["ok"] else "Set up email hosting for your domain so replies arrive.")
    spf = [t for t in txt(d) if t.lower().startswith("v=spf1")]
    if len(spf) == 1:
        add("SPF", "pass", spf[0][:120])
    elif len(spf) > 1:
        add("SPF", "fail", "More than one SPF record found", "Merge them into a single v=spf1 record.")
    else:
        add("SPF", "fail", "No SPF record", "Add the SPF TXT record your email provider gives you (e.g. v=spf1 include:_spf.google.com ~all).")
    dm = [t for t in txt("_dmarc." + d) if t.lower().startswith("v=dmarc1")]
    add("DMARC", "pass" if dm else "warn", dm[0][:120] if dm else "No DMARC record",
        "" if dm else "Add a TXT record at _dmarc with: v=DMARC1; p=none; rua=mailto:you@" + d)
    sels = ("google", "selector1", "selector2", "default", "k1", "s1", "s2", "mail", "dkim", "zoho", "zmail", "mxvault")
    with ThreadPoolExecutor(6) as ex:
        hits = list(ex.map(lambda sel: any("p=" in t for t in txt(f"{sel}._domainkey.{d}")), sels))
    found = next((sel for sel, ok in zip(sels, hits) if ok), "")
    add("DKIM", "pass" if found else "warn", f"Found selector '{found}'" if found else "No DKIM found on common selectors (it may use a custom one)",
        "" if found else "Turn on DKIM signing in your email provider's admin panel and publish its TXT record.")
    return out
