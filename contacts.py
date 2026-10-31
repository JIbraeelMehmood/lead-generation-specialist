"""
Free contact tools: find + guess + verify business emails, find contact pages,
optional Hunter.io lookup. Email checks use free DNS-over-HTTPS (no SMTP probing).
"""
import re, time, urllib.parse
import leadfinder as LF

_mx_cache = {}
FREE_MAIL = {"gmail.com", "yahoo.com", "hotmail.com", "outlook.com", "live.com", "aol.com", "icloud.com",
             "proton.me", "protonmail.com", "gmx.com", "yandex.com", "mail.com", "msn.com", "ymail.com"}
DISPOSABLE = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "yopmail.com",
              "trashmail.com", "sharklasers.com", "getnada.com", "temp-mail.org", "dispostable.com"}
HOSTED = ("wixsite.com", "weebly.com", "blogspot.", "sites.google.com", "business.site", "facebook.com",
          "instagram.com", "godaddysites.com", "square.site", "linktr.ee", "wordpress.com", "carrd.co")
ROLE = {"info", "contact", "hello", "office", "admin", "sales", "enquiries", "inquiries", "support", "bookings", "reception"}

def _doh(name, rtype):
    for url in ("https://cloudflare-dns.com/dns-query", "https://dns.google/resolve"):
        try:
            r = LF.http_json(url + "?" + urllib.parse.urlencode({"name": name, "type": rtype}),
                             headers={"Accept": "application/dns-json"}, timeout=10)
            return r
        except Exception:
            continue
    return None

def mx(domain):
    domain = domain.lower().strip(".")
    c = _mx_cache.get(domain)
    if c and time.time() - c[0] < 86400: return c[1]
    r = _doh(domain, "MX")
    if r is None:
        res = {"ok": None, "hosts": [], "note": "DNS lookup unavailable"}
    else:
        hosts = [a["data"].split()[-1].rstrip(".") for a in r.get("Answer", []) if a.get("type") == 15]
        hosts = [h for h in hosts if h]  # "0 ." null MX means no mail
        if hosts:
            res = {"ok": True, "hosts": hosts[:3], "note": ""}
        elif r.get("Status") == 3:
            res = {"ok": False, "hosts": [], "note": "domain does not exist"}
        else:
            a = _doh(domain, "A")
            has_a = bool(a and any(x.get("type") == 1 for x in a.get("Answer", [])))
            res = {"ok": False if not has_a else None, "hosts": [], "note": "no mail server (MX) record" if not has_a else "no MX record, mail may still work via the web server"}
    _mx_cache[domain] = (time.time(), res)
    return res

def verify(email):
    e = (email or "").strip().lower()
    out = {"email": e, "status": "invalid", "reasons": []}
    if not re.match(r"^[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,24}$", e):
        out["reasons"].append("bad format"); return out
    local, domain = e.split("@", 1)
    if domain in DISPOSABLE:
        out["reasons"].append("disposable address"); return out
    out["free"] = domain in FREE_MAIL
    out["role"] = local in ROLE
    m = mx(domain)
    if m["ok"] is True:
        out["status"] = "deliverable-domain"
        out["reasons"].append("domain accepts email" + (" (free provider)" if out["free"] else ""))
    elif m["ok"] is None:
        out["status"] = "unknown"; out["reasons"].append(m["note"])
    else:
        out["status"] = "invalid"; out["reasons"].append(m["note"])
    return out

def domain_of(website):
    try:
        host = urllib.parse.urlparse(LF.norm_url(website)).hostname or ""
    except Exception:
        return ""
    host = host.lower()
    if host.startswith("www."): host = host[4:]
    if not host or any(h in host for h in HOSTED): return ""
    return host

def contact_page(website):
    url = LF.norm_url(website)
    try:
        html, final, _ = LF.fetch_text(url, timeout=10)
    except Exception:
        return ""
    for m in re.finditer(r'href=["\']([^"\']+)["\'][^>]*>([^<]{0,60})', html, re.I):
        href, text = m.group(1), m.group(2)
        if re.search(r"contact|get in touch|enquir|inquir|quote", href + " " + text, re.I) and not href.startswith(("mailto:", "tel:", "#")):
            return urllib.parse.urljoin(final, href)
    return ""

def enrich(website):
    """Everything free we can learn about how to contact a business from its website."""
    res = {"website": website, "emails": [], "guessed": [], "contactPage": "", "domain": domain_of(website)}
    if not website: return res
    found = LF.find_emails(website)["emails"]
    res["contactPage"] = contact_page(website)
    for e in found:
        v = verify(e)
        if v["status"] != "invalid":
            res["emails"].append(v)
    if not res["emails"] and res["domain"]:
        m = mx(res["domain"])
        if m["ok"]:
            res["guessed"] = [f"{p}@{res['domain']}" for p in ("info", "contact", "hello", "office")]
    return res

def hunter(domain, key):
    if not key: raise RuntimeError("Add a Hunter.io key in Settings (free plan: small monthly allowance).")
    if key.startswith("AIza"):
        raise RuntimeError("The Hunter.io field contains a Google key. Paste your key from hunter.io/api-keys, or clear the field.")
    r = LF.http_json("https://api.hunter.io/v2/domain-search?" + urllib.parse.urlencode(
        {"domain": domain, "api_key": key, "limit": 10}), timeout=30)
    d = r.get("data") or {}
    return {"pattern": d.get("pattern"), "organization": d.get("organization"),
            "emails": [{"email": e.get("value"), "confidence": e.get("confidence"),
                        "name": " ".join(filter(None, [e.get("first_name"), e.get("last_name")])),
                        "position": e.get("position")} for e in d.get("emails", [])]}
