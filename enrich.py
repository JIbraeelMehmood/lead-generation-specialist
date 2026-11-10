"""
enrich.py — Advanced enrichment for LeadFinder.

Absorbs the best ideas from:
  - intent-engine/llm_extractor.py   → LLM decision-maker extraction
  - intent-engine/enrichment.py      → Hunter.io + Apollo.io fallback
  - google-maps-leads-scraper-python → social handle extraction
  - b2b-buyer-discovery/src/skills/  → tech stack fingerprinting

All calls use the Python standard library. LLM calls go through LeadFinder's
existing ai_pool so no extra keys are needed.
"""
import re, time, urllib.parse
import leadfinder as LF

# ── Social handle extraction ──────────────────────────────────────────────────
# Patterns that identify profile URLs for each social platform.
SOCIAL_PATTERNS = {
    "facebook":  re.compile(r'facebook\.com/(?!sharer|share|pages/create)([A-Za-z0-9.\-_]+)', re.I),
    "instagram": re.compile(r'instagram\.com/([A-Za-z0-9._]+)', re.I),
    "twitter":   re.compile(r'(?:twitter|x)\.com/([A-Za-z0-9_]+)', re.I),
    "linkedin":  re.compile(r'linkedin\.com/(?:company|in)/([A-Za-z0-9._\-]+)', re.I),
    "tiktok":    re.compile(r'tiktok\.com/@([A-Za-z0-9._]+)', re.I),
    "youtube":   re.compile(r'youtube\.com/(?:c/|channel/|@)([A-Za-z0-9._\-]+)', re.I),
    "whatsapp":  re.compile(r'(?:wa\.me|api\.whatsapp\.com/send)[/?]+(\d{7,15})', re.I),
}

IGNORE_HANDLES = {"share", "sharer", "intent", "home", "search", "help", "www",
                  "legal", "privacy", "terms", "about", "login", "signup"}


def social_handles(website: str) -> dict:
    """Extract social media profile handles/URLs from a business website."""
    url = LF.norm_url(website)
    if not url:
        return {}
    handles = {}
    try:
        html, _, _ = LF.fetch_text(url, timeout=12)
    except Exception:
        return {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        for m in pattern.finditer(html):
            handle = m.group(1).rstrip("/").lower()
            if handle not in IGNORE_HANDLES and len(handle) >= 2:
                # For whatsapp, store the full wa.me link
                if platform == "whatsapp":
                    handles[platform] = f"https://wa.me/{handle}"
                else:
                    handles[platform] = handle
                break  # first match per platform
    return handles


# ── Tech stack fingerprinting ─────────────────────────────────────────────────

TECH_SIGNATURES = {
    "WordPress":   ["wp-content/", "wp-includes/", "xmlrpc.php", "WordPress"],
    "Shopify":     ["cdn.shopify.com", "shopify.com/s/", "Shopify.theme"],
    "Wix":         ["static.wixstatic.com", "wix-code", "_wix_"],
    "Squarespace": ["squarespace.com", "sqsp.net", "Squarespace"],
    "Webflow":     ["webflow.com", "wf-form"],
    "Bootstrap":   ["bootstrap.min.css", "bootstrap.css"],
    "React":       ["react.min.js", "__react", "data-reactroot"],
    "Next.js":     ["_next/static/", "__NEXT_DATA__"],
    "Vue.js":      ["vue.min.js", "__vue__", "data-v-"],
    "jQuery":      ["jquery.min.js", "jquery-", "/jquery/"],
    "Google Analytics": ["google-analytics.com/analytics.js", "gtag/js", "UA-", "G-"],
    "Facebook Pixel": ["connect.facebook.net/en_US/fbevents.js", "fbq("],
    "HubSpot":     ["js.hs-scripts.com", "js.hubspot.com"],
    "Mailchimp":   ["mailchimp.com", "mc-embedded-subscribe"],
    "Calendly":    ["calendly.com/assets", "Calendly.initInlineWidget"],
    "Stripe":      ["js.stripe.com", "stripe.js"],
    "PayPal":      ["paypal.com/sdk", "paypalobjects.com"],
    "Cloudflare":  ["cdnjs.cloudflare.com", "__cf_bm"],
    "OpenAI":      ["openai.com"],
}

def tech_stack(website: str) -> list:
    """Return a list of detected technology names for a business website."""
    url = LF.norm_url(website)
    if not url:
        return []
    try:
        html, _, _ = LF.fetch_text(url, timeout=12)
    except Exception:
        return []
    detected = []
    for tech, signatures in TECH_SIGNATURES.items():
        if any(sig in html for sig in signatures):
            detected.append(tech)
    return detected


# ── Quick (regex-only) decision-maker extraction ──────────────────────────────

OWNER_PATTERNS = [
    re.compile(
        r'(?:CEO|Founder|Owner|Director|President|Principal|Managing Director|Head|Partner)'
        r'[,\s:–-]{1,20}([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20}){0,2})',
        re.I
    ),
    re.compile(
        r'([A-Z][a-z]{1,20}(?:\s[A-Z][a-z]{1,20}){0,2})'
        r'[,\s]{1,10}(?:CEO|Founder|Owner|Director|President|Principal|Managing Director)',
        re.I
    ),
]

TITLE_PATTERN = re.compile(
    r'\b(CEO|Founder|Co-Founder|Owner|Director|President|Principal|Managing Director|'
    r'Head of|Partner|Chief Executive|General Manager|Chairman)\b',
    re.I
)

def quick_decision_maker(website: str) -> dict:
    """Fast regex-based extraction of a decision-maker from about/team pages."""
    url = LF.norm_url(website)
    if not url:
        return {}
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    pages = [url, base + "/about", base + "/about-us", base + "/team", base + "/our-team"]
    for page_url in pages:
        try:
            html, _, _ = LF.fetch_text(page_url, timeout=10)
        except Exception:
            continue
        # Strip HTML tags for cleaner text
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        for pat in OWNER_PATTERNS:
            m = pat.search(text)
            if m:
                name = m.group(1).strip()
                if 3 <= len(name) <= 50:
                    title_m = TITLE_PATTERN.search(text[max(0, m.start()-100):m.end()+100])
                    return {
                        "name": name,
                        "title": title_m.group(0) if title_m else "Owner/Decision Maker",
                        "source": "website",
                        "confidence": "medium",
                        "source_url": page_url,
                    }
    return {}


# ── LLM-based decision-maker extraction ──────────────────────────────────────

def llm_decision_maker(website: str, company_name: str = "") -> dict:
    """
    Use the AI pool (Gemini/Groq/Ollama etc.) to extract the decision-maker
    from a business's about/team page. Falls back to quick_regex if AI unavailable.

    Ported from intent-engine/llm_extractor.py but using LeadFinder's existing
    ai_pool so no new API keys are needed.
    """
    # First try regex (free, fast)
    dm = quick_decision_maker(website)

    # Then try LLM for higher confidence
    url = LF.norm_url(website)
    if not url:
        return dm
    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    page_text = ""
    for page_url in [url, base + "/about", base + "/about-us", base + "/team"]:
        try:
            html, _, _ = LF.fetch_text(page_url, timeout=10)
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)[:3000]  # keep under LLM context limit
            page_text += text + "\n"
        except Exception:
            continue
        if len(page_text) > 4000:
            break

    if not page_text.strip():
        return dm

    prompt = f"""You are extracting the decision-maker (owner, founder, CEO, or director) 
from the about/team page of a business website.

Company: {company_name or website}
Page text (first 4000 chars):
{page_text[:4000]}

Return a JSON object with these fields:
- name: full name of the decision-maker (or null if not found)
- title: their job title (or null)
- email: their direct email if visible (or null)
- confidence: "high", "medium", or "low"

Return ONLY valid JSON, no explanation."""

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=200)
        text = result.get("text", "").strip()
        # Extract JSON from response
        json_match = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if json_match:
            import json
            parsed = json.loads(json_match.group(0))
            if parsed.get("name"):
                return {
                    "name": parsed.get("name", ""),
                    "title": parsed.get("title", ""),
                    "email": parsed.get("email", ""),
                    "confidence": parsed.get("confidence", "medium"),
                    "source": "llm",
                    "source_url": website,
                }
    except Exception:
        pass  # Fall back to regex result

    return dm


# ── Hunter.io domain search ────────────────────────────────────────────────────

def hunter_lookup(domain: str, api_key: str) -> list:
    """
    Search Hunter.io for email addresses associated with a domain.
    Returns list of email dicts with {email, first_name, last_name, position, confidence}.
    """
    if not domain or not api_key:
        return []
    url = "https://api.hunter.io/v2/domain-search?" + urllib.parse.urlencode({
        "domain": domain,
        "api_key": api_key,
        "limit": 10,
    })
    try:
        data = LF.http_json(url, timeout=15)
        emails = []
        for e in (data.get("data") or {}).get("emails", []):
            emails.append({
                "email": e.get("value", ""),
                "first_name": e.get("first_name", ""),
                "last_name": e.get("last_name", ""),
                "position": e.get("position", ""),
                "confidence": e.get("confidence", 0),
                "source": "hunter.io",
            })
        return emails
    except Exception:
        return []


# ── Apollo.io people search fallback ─────────────────────────────────────────

def apollo_lookup(domain: str, api_key: str) -> list:
    """
    Apollo.io people search fallback for a domain.
    Returns list of contact dicts.
    """
    if not domain or not api_key:
        return []
    url = "https://api.apollo.io/v1/mixed_people/search"
    body = {
        "api_key": api_key,
        "q_organization_domains": domain,
        "page": 1,
        "per_page": 5,
        "person_titles": ["CEO", "Founder", "Owner", "Director", "President"],
    }
    try:
        data = LF.http_json(url, body, {"Content-Type": "application/json"}, timeout=15)
        people = []
        for p in (data.get("people") or []):
            people.append({
                "email": p.get("email", ""),
                "first_name": p.get("first_name", ""),
                "last_name": p.get("last_name", ""),
                "title": p.get("title", ""),
                "linkedin": p.get("linkedin_url", ""),
                "source": "apollo.io",
            })
        return people
    except Exception:
        return []


# ── Full enrichment pipeline ──────────────────────────────────────────────────

def full_enrich(lead: dict, hunter_key: str = "", apollo_key: str = "",
                use_llm: bool = True) -> dict:
    """
    Run the complete enrichment pipeline on a single lead.
    Returns an enrichment dict with all discovered data.
    """
    website = lead.get("website", "")
    result = {
        "lead_id": lead.get("id", ""),
        "social_handles": {},
        "tech_stack": [],
        "decision_maker": {},
        "emails_found": [],
        "hunter_contacts": [],
        "apollo_contacts": [],
    }

    if website:
        url = LF.norm_url(website)
        # Social handles
        result["social_handles"] = social_handles(url)
        # Tech stack
        result["tech_stack"] = tech_stack(url)
        # Decision maker
        if use_llm:
            result["decision_maker"] = llm_decision_maker(url, lead.get("name", ""))
        else:
            result["decision_maker"] = quick_decision_maker(url)
        # Emails
        found = LF.find_emails(url)
        result["emails_found"] = found.get("emails", [])

    # Hunter.io fallback when no email found
    if not result["emails_found"] and hunter_key and website:
        import urllib.parse as UP
        try:
            domain = UP.urlparse(LF.norm_url(website)).hostname or ""
            if domain.startswith("www."):
                domain = domain[4:]
            if domain:
                result["hunter_contacts"] = hunter_lookup(domain, hunter_key)
        except Exception:
            pass

    # Apollo fallback
    if not result["emails_found"] and not result["hunter_contacts"] and apollo_key and website:
        import urllib.parse as UP
        try:
            domain = UP.urlparse(LF.norm_url(website)).hostname or ""
            if domain.startswith("www."):
                domain = domain[4:]
            if domain:
                result["apollo_contacts"] = apollo_lookup(domain, apollo_key)
        except Exception:
            pass

    return result


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    import assistant

    if path == "/api/enrich/social":
        return {"handles": social_handles(req.get("website", ""))}

    if path == "/api/enrich/tech":
        return {"tech_stack": tech_stack(req.get("website", ""))}

    if path == "/api/enrich/decision_maker":
        use_llm = bool(req.get("use_llm", True))
        website = req.get("website", "")
        if use_llm:
            dm = llm_decision_maker(website, req.get("company_name", ""))
        else:
            dm = quick_decision_maker(website)
        return {"decision_maker": dm}

    if path == "/api/enrich/hunter":
        key = req.get("api_key") or assistant.cfg()["keys"].get("hunter", "")
        return {"contacts": hunter_lookup(req.get("domain", ""), key)}

    if path == "/api/enrich/apollo":
        key = req.get("api_key") or assistant.cfg()["keys"].get("apollo", "")
        return {"contacts": apollo_lookup(req.get("domain", ""), key)}

    if path == "/api/enrich/full":
        c = assistant.cfg()
        result = full_enrich(
            req.get("lead", {}),
            hunter_key=c["keys"].get("hunter", ""),
            apollo_key=c["keys"].get("apollo", ""),
            use_llm=bool(req.get("use_llm", True)),
        )
        # Also persist to DB if lead has an id
        lid = result.get("lead_id", "")
        if lid:
            update = {
                "social_handles": result["social_handles"],
                "tech_stack": ", ".join(result["tech_stack"]),
                "decision_maker": result["decision_maker"],
            }
            if result["emails_found"]:
                update["email"] = result["emails_found"][0]
            elif result["hunter_contacts"]:
                update["email"] = result["hunter_contacts"][0].get("email", "")
            if result["decision_maker"].get("name"):
                update["owner_name"] = result["decision_maker"]["name"]
            try:
                import db
                db.update_lead_field(lid, **update)
            except Exception:
                pass
        return result

    return {"error": f"Unknown enrich path: {path}"}
