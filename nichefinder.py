"""
Niche & city finder + email sending for LeadFinder.
  * top_cities: largest cities in a country with population (live from Wikidata, free)
  * market_sample: samples Google Maps for a niche in a city and measures how many
    established businesses have no website (real opportunity data)
  * send_email: sends one approved email through your own SMTP account
"""
import json, re, smtplib, ssl, time, urllib.parse
from email.message import EmailMessage
from email.utils import formataddr, make_msgid
import leadfinder as LF

COUNTRIES = {
    "United States": "Q30", "United Kingdom": "Q145", "Canada": "Q16", "Australia": "Q408",
    "New Zealand": "Q664", "Ireland": "Q27", "Germany": "Q183", "United Arab Emirates": "Q878",
    "Saudi Arabia": "Q851", "Pakistan": "Q843", "India": "Q668", "South Africa": "Q258",
}
_cache = {}

def top_cities(country, min_pop=100000, limit=150):
    qid = COUNTRIES.get(country)
    if not qid:
        raise RuntimeError("Unknown country.")
    key = (qid, int(min_pop), int(limit))
    if key in _cache and time.time() - _cache[key][0] < 86400:
        return _cache[key][1]
    q = f"""
SELECT ?city ?cityLabel (MAX(?pop) AS ?population) (SAMPLE(?admLabel) AS ?region) WHERE {{
  VALUES ?cls {{ wd:Q515 wd:Q1549591 wd:Q1637706 wd:Q1093829 wd:Q200250 }}
  ?city wdt:P31 ?cls; wdt:P17 wd:{qid}; wdt:P1082 ?pop.
  FILTER(?pop >= {int(min_pop)})
  OPTIONAL {{ ?city wdt:P131 ?adm. ?adm rdfs:label ?admLabel. FILTER(LANG(?admLabel) = "en") }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
}}
GROUP BY ?city ?cityLabel
ORDER BY DESC(?population)
LIMIT {int(limit)}"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode({"query": q, "format": "json"})
    try:
        res = LF.http_json(url, headers={"Accept": "application/sparql-results+json"}, timeout=90)
    except Exception as ex:
        raise RuntimeError(f"Couldn't load city data from Wikidata (try again in a minute): {ex}")
    out, seen = [], set()
    for b in res["results"]["bindings"]:
        name = b["cityLabel"]["value"]
        if re.match(r"^Q\d+$", name) or name.lower() in seen:
            continue
        seen.add(name.lower())
        out.append({"name": name, "population": int(float(b["population"]["value"])),
                    "region": b.get("region", {}).get("value", ""),
                    "wikidata": b["city"]["value"]})
    _cache[key] = (time.time(), out)
    return out

def market_sample(source, keys, niche, city):
    """One map search (up to 20 businesses) -> how many established businesses lack a website."""
    if source == "google":
        leads = LF.google_search(keys.get("google"), niche, city, max_pages=1)
    elif source == "serpapi":
        leads = LF.serpapi_search(keys.get("serp"), niche, city, max_pages=1)
    else:
        raise RuntimeError("Market check needs Google Maps or SerpApi (OpenStreetMap has too little website data).")
    n = len(leads)
    def no_site(l):
        w = (l.get("website") or "").lower()
        return not w or any(s in w for s in ("facebook.com", "instagram.com", "business.site", "linktr.ee"))
    ns = [l for l in leads if no_site(l)]
    established = [l for l in ns if (l.get("reviews") or 0) >= 10]
    avg_rev = round(sum((l.get("reviews") or 0) for l in leads) / n) if n else 0
    # opportunity points: each no-website business counts more if it is established and reachable
    pts = sum(0.3 + min(l.get("reviews") or 0, 100) / 100 + (0.2 if l.get("phone") else 0) for l in ns)
    return {"niche": niche, "city": city, "sampled": n, "noWebsite": len(ns),
            "pctNoWebsite": round(100 * len(ns) / n) if n else 0,
            "establishedNoWebsite": len(established), "avgReviews": avg_rev,
            "opportunity": round(pts, 1),
            "examples": [{"name": l["name"], "reviews": l.get("reviews") or 0, "phone": l.get("phone", "")}
                         for l in sorted(established, key=lambda x: -(x.get("reviews") or 0))[:3]]}

def send_email(smtp, to, subject, body, reply_to=""):
    host = (smtp or {}).get("host", "").strip()
    user = (smtp or {}).get("user", "").strip()
    pw = (smtp or {}).get("password", "")
    if not (host and user and pw):
        raise RuntimeError("Set up email sending in Emails > Sender setup first.")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", to or ""):
        raise RuntimeError(f"Invalid recipient address: {to}")
    port = int(smtp.get("port") or 587)
    msg = EmailMessage()
    msg["From"] = formataddr((smtp.get("fromName") or "", smtp.get("fromEmail") or user))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Message-ID"] = make_msgid()
    if reply_to: msg["Reply-To"] = reply_to
    if smtp.get("unsubEmail"):
        msg["List-Unsubscribe"] = f"<mailto:{smtp['unsubEmail']}?subject=unsubscribe>"
    msg.set_content(body)
    ctx = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
                s.login(user, pw); s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as s:
                s.starttls(context=ctx); s.login(user, pw); s.send_message(msg)
    except smtplib.SMTPAuthenticationError:
        raise RuntimeError("Email login failed. For Gmail, use an App Password (Google Account > Security > App passwords), not your normal password.")
    except smtplib.SMTPRecipientsRefused:
        raise RuntimeError(f"The mail server refused the address {to}.")
    except (OSError, smtplib.SMTPException) as ex:
        raise RuntimeError(f"Couldn't send via {host}:{port} ({ex}). Check the server name and port.")
    return {"sent": True, "to": to, "at": time.strftime("%Y-%m-%d %H:%M")}
