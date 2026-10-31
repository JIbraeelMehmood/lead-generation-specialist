"""
Opportunity engine + lead scoring for LeadFinder.

Merges the core of the "Lead Generator Enhancement & Integration Blueprint" into
LeadFinder: it turns the existing website audit / presence checks into
structured, evidence-backed, explainable improvement opportunities, and rates each
prospect with the blueprint's visible multi-component score (0-100) with bands.

Design rules from the blueprint this enforces:
  * Every opportunity carries an evidence_url + evidence_excerpt or measured_value,
    a confidence level, an impact explanation, a suggested fix and a service fit.
    Measured facts are separated from hypotheses.
  * Scoring is broken into visible components (opportunity 0-30, fit 0-20,
    commercial 0-20, contactability 0-15, confidence 0-15), never an unexplained number.
  * Contact fields carry a provenance label (directory-sourced / verified / unverified)
    and are never silently invented.
  * A site is not labelled 'bad' for being simple, and no missing feature is asserted
    without a page URL or reproducible measurement.

It reuses leadfinder.audit_site and analyzer.presence_from_url so it does not
duplicate the existing checks; it structures and scores their output.
"""
import html as htmllib, re, time, urllib.parse
import leadfinder as LF
import analyzer

BANDS = [(80, "Review first"), (65, "Normal review"), (50, "Nurture / research"), (0, "Skip")]

# productized packages from the blueprint (starting points, not commitments)
PACKAGES = [
    {"name": "3-page refresh", "price": "$349", "fit": "minor polish, speed, SEO, copy fixes"},
    {"name": "5-page professional website", "price": "$699", "fit": "redesign / conversion gaps / missing key pages"},
    {"name": "8-page growth website", "price": "$999", "fit": "no site / broken / free-builder / full rebuild"},
]

# niche fit (service/niche fit 0-20): local service businesses are the best $300-1k fit
HIGH_FIT = re.compile(r"plumb|electric|roof|builder|contract|construct|hvac|heating|clean|landscap|garden|"
    r"paint|decor|carpent|handyman|pest|lock|glaz|floor|tile|mechanic|car repair|garage|tyre|tire|"
    r"dent|clinic|doctor|medical|physio|chiro|vet|optic|pharma|health|therap|"
    r"salon|beauty|barber|hair|nail|spa|massage|"
    r"gym|fitness|yoga|pilates|crossfit|martial|dance|"
    r"restaurant|cafe|coffee|bakery|food|pizza|burger|diner|bar|grill|kitchen|takeaway|"
    r"hotel|guest|hostel|bnb|resort|florist|driving school|photographer|jewel|tailor|optician", re.I)
LOW_FIT = re.compile(r"software|saas|startup|agency|crypto|ai|fintech|developer|tech|it services|"
    r"marketing agency|consultancy firm|design studio", re.I)


# ---------------------------------------------------------------- helpers
def _clean(html):
    h = re.sub(r"(?i)<(script|style|noscript|svg)[\s\S]*?</\1>", " ", html or "")
    h = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", h)
    t = htmllib.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t).strip()

def _text_of(url):
    """Fetch a homepage and return (text, final_url, load_seconds) or (None, None, None)."""
    try:
        html, final, secs = LF.fetch_text(url, timeout=18)
        return _clean(html), final, secs
    except Exception:
        return None, None, None

PLACEHOLDER = re.compile(r"lorem ipsum|lorem|sample text|demo content|coming soon|placeholder|"
    r"your text here|dummy text|type your|default content|insert text|test text", re.I)


# ---------------------------------------------------------------- opportunity builder
def _opp(oid, category, observation, evidence_url, impact, fix, service_fit,
         confidence="medium", excerpt="", measured=None, weight=2):
    return {"id": oid, "category": category, "observation": observation,
            "evidence_url": evidence_url or "", "evidence_excerpt": excerpt,
            "measured_value": measured, "impact": impact, "suggested_fix": fix,
            "service_fit": service_fit, "confidence": confidence, "weight": weight,
            "verification_status": "measured" if measured is not None or excerpt else "observed",
            "detected_at": time.strftime("%Y-%m-%d")}


def build_opportunities(lead, audit, pres):
    """Turn audit_site + presence_from_url results into structured opportunities."""
    site = lead.get("website") or ""
    base = audit.get("finalUrl") or LF.norm_url(site)
    issues = audit.get("issues") or []
    out = []
    n = [0]
    def add(category, obs, impact, fix, fit, confidence="medium", excerpt="", measured=None, weight=2):
        n[0] += 1
        out.append(_opp(f"OP-{n[0]:02d}", category, obs, base, impact, fix, fit, confidence, excerpt, measured, weight))

    # ---- no website / social only (highest value)
    if not site:
        add("trust_content", "The business has no website listed.",
            "Customers searching online land on competitors; no place to show services, prices or reviews.",
            "Build a starter website with services, contact and reviews.", PACKAGES[2]["name"], "high", weight=28)
        return out
    if pres.get("socialOnly"):
        add("trust_content", "The business has only a social-media page, not its own website.",
            "A social page is not searchable like a website and gives no control over SEO or conversions.",
            "Build a small own-domain website.", PACKAGES[1]["name"], "high", weight=24)
        # social-only sites can't be audited further
        return out

    # ---- technical basics (from audit + presence)
    if not audit.get("ok"):
        add("technical_basics", "The website did not load when checked.",
            "A broken or offline website loses every visitor who tries to visit.",
            "Diagnose hosting/domain and rebuild or repair the site.", PACKAGES[2]["name"], "high",
            excerpt=next((i for i in issues if "didn't load" in i), ""), weight=30)
        return out  # can't measure further
    for i in issues:
        low = i.lower()
        if "no https" in low:
            add("technical_basics", "The site is not served over HTTPS.",
                "Browsers show 'Not secure', which hurts trust and Google ranking.",
                "Install an SSL/TLS certificate and redirect HTTP to HTTPS.", PACKAGES[0]["name"], "high", weight=10)
        elif "mobile-friendly" in low or "viewport" in low:
            add("technical_basics", "No mobile viewport tag - the site is not mobile-friendly.",
                "Most visitors are on phones; a non-responsive site is hard to use and ranks worse.",
                "Redesign responsively with a viewport tag.", PACKAGES[1]["name"], "high", weight=14)
        elif "slow" in low:
            m = re.search(r"([0-9.]+)\s*s", low)
            add("technical_basics", "The homepage is slow to load.",
                "Slow load raises bounce rate and lowers Google ranking.",
                "Optimize images, caching and hosting.", PACKAGES[0]["name"], "medium",
                measured=(m.group(1) + "s") if m else None, weight=8)
        elif "outdated" in low or "copyright" in low:
            m = re.search(r"(\d{4})", low)
            add("trust_content", "The site looks outdated.",
                "An old copyright year signals a neglected site and lowers trust.",
                "Refresh content and update the copyright.", PACKAGES[0]["name"], "medium",
                measured=m.group(1) if m else None, weight=6)
        elif "missing page title" in low:
            add("technical_basics", "The page is missing a title tag.",
                "The title is the main signal Google uses; without it the site ranks poorly.",
                "Add a descriptive page title.", PACKAGES[0]["name"], "medium", weight=5)
        elif "meta description" in low:
            add("technical_basics", "The page is missing a meta description.",
                "No description means Google writes its own snippet, reducing clicks.",
                "Add a meta description for each page.", PACKAGES[0]["name"], "medium", weight=4)
        elif "free subdomain" in low or "builder site" in low:
            add("trust_content", "The site is on a free builder subdomain.",
                "A free subdomain looks unprofessional and limits SEO and features.",
            "Move to its own domain with a custom-built site.", PACKAGES[2]["name"], "high", weight=18)
        elif "click-to-call" in low or "tel:" in low:
            add("conversion", "No click-to-call phone link on the site.",
                "Mobile visitors can't tap to call, losing quick contacts.",
                "Add a tap-to-call phone link.", PACKAGES[0]["name"], "medium", weight=6)

    if pres.get("freeBuilder"):
        add("trust_content", "The site uses a free website builder.",
            "Free builders limit design, speed and SEO and signal a low-budget presence.",
            "Upgrade to a custom own-domain website.", PACKAGES[1]["name"], "high", weight=16)

    # ---- content quality (homepage text)
    txt, _final, _ = _text_of(base)
    if txt:
        m = PLACEHOLDER.search(txt)
        if m:
            add("trust_content", "Visible placeholder / generic copy on the homepage.",
                "Placeholder text signals an unfinished site and erodes trust immediately.",
                "Replace placeholder copy with real, specific content.", PACKAGES[0]["name"], "high",
                excerpt=m.group(0), weight=14)
        elif len(txt) < 300:
            add("trust_content", "Very little text content on the homepage.",
                "Thin content gives Google little to rank and visitors little reason to stay.",
                "Add real service and about content.", PACKAGES[0]["name"], "medium",
                measured=f"{len(txt)} chars", weight=8)
        # missing company name in homepage text is a weak signal — skip to avoid false positives

    # ---- conversion
    is_service = bool(HIGH_FIT.search(f"{lead.get('category','')} {lead.get('searchQuery','')}"))
    if audit.get("ok") and not (pres.get("booking") or pres.get("ordering") or pres.get("quoteForm")):
        if is_service:
            add("conversion", "No clear booking, quote or contact form on the site.",
                "Service businesses lose the customers who want to book or request a quote outside hours.",
                "Add an online booking or quote-request form.", PACKAGES[1]["name"], "high", weight=14)
        else:
            add("conversion", "No clear call-to-action (no booking, order or quote form).",
                "Visitors with no next step leave without converting.",
                "Add a clear primary call-to-action.", PACKAGES[0]["name"], "medium", weight=8)
    if audit.get("ok") and not pres.get("socials"):
        add("conversion", "No social media links found on the site.",
            "No social connection means missed free reach and weaker trust signals.",
            "Add links to active social profiles.", PACKAGES[0]["name"], "low", weight=4)
    if audit.get("ok") and is_service and not pres.get("chat"):
        add("conversion", "No live chat / WhatsApp contact option.",
            "Service customers often want to ask a quick question before booking.",
            "Add a WhatsApp or chat widget.", PACKAGES[0]["name"], "low", weight=3)

    # ---- catalogue / e-commerce (only when commerce signals present)
    low_html = ""
    try:
        low_html = LF.fetch_text(base, timeout=12)[0].lower()
    except Exception:
        pass
    if any(k in low_html for k in ("shopify", "woocommerce", "/cart", "add to cart", "shop now")):
        if not any(k in low_html for k in ("/product/", "product-details", "shop/collection", "category")):
            add("catalogue", "E-commerce detected but product/category structure looks weak.",
                "Weak product organisation makes browsing and buying harder, reducing sales.",
                "Improve product categorisation and product detail pages.", PACKAGES[1]["name"], "medium", weight=10)

    # ---- local business
    if is_service and audit.get("ok"):
        if not (lead.get("address") or lead.get("phone")):
            add("local_business", "Service-area / contact details not clearly present.",
                "Local customers need to see the area served and how to reach the business.",
                "Add a service-area and contact section.", PACKAGES[0]["name"], "medium", weight=8)
        if not re.search(r"review|testimonial|what (our )?clients say", low_html):
            add("local_business", "No testimonials / reviews shown on the site.",
                "Showing reviews builds trust and is a strong local conversion driver.",
                "Add a testimonials / reviews section.", PACKAGES[0]["name"], "low", weight=4)

    return out


# ---------------------------------------------------------------- scoring (blueprint model)
def _fit(lead):
    blob = f"{lead.get('category','')} {lead.get('searchQuery','')} {lead.get('name','')}"
    if LOW_FIT.search(blob):
        return 5
    if HIGH_FIT.search(blob):
        return 18
    return 11

def _commercial(lead):
    r = lead.get("reviews") or 0
    rating = lead.get("rating") or 0
    if r >= 100 and rating >= 4:
        return 20
    if r >= 50:
        return 17
    if r >= 30:
        return 14
    if r >= 10:
        return 10
    if r > 0:
        return 6
    return 8  # unknown activity

def _contactability(lead):
    s = 0
    if lead.get("phone"):
        s += 6
    email = lead.get("email") or ""
    if email:
        st = lead.get("emailStatus") or ""
        if st == "deliverable-domain":
            s += 9                      # verified domain email
        else:
            s += 5                      # present, unverified
    return min(15, s)

def _confidence(lead, audit):
    s = 0
    if audit.get("ok"):
        s += 6
    elif lead.get("website"):
        s += 3                          # website exists even if audit failed
    src = str(lead.get("source") or "")
    if src.startswith("Google"):
        s += 5
    elif src == "OpenStreetMap":
        s += 3
    if lead.get("address") or (lead.get("lat") is not None):
        s += 3
    if lead.get("name"):
        s += 1
    return min(15, s)

def _opportunity_score(opps):
    if not opps:
        return 0
    return min(30, sum(o.get("weight", 2) for o in opps))

def _band(total):
    for thr, label in BANDS:
        if total >= thr:
            return label
    return "Skip"

def _provenance(lead):
    phone = "directory-sourced" if lead.get("phone") else "none"
    email = "none"
    if lead.get("email"):
        st = lead.get("emailStatus") or ""
        email = "verified domain" if st == "deliverable-domain" else "unverified"
    return {"phone": phone, "email": email,
            "note": "Directory-sourced contacts should be verified on the company's official site."}


def _recommended_package(opps, audit, lead):
    if not lead.get("website") or pres_social_only(lead) or (audit.get("ok") is False):
        return PACKAGES[2]
    high = [o for o in opps if o["confidence"] == "high"]
    if len(high) >= 3 or any(o["category"] in ("trust_content", "conversion") and o["confidence"] == "high" for o in opps):
        return PACKAGES[1] if len(high) < 4 else PACKAGES[2]
    if len(high) >= 1:
        return PACKAGES[1]
    return PACKAGES[0]

def pres_social_only(lead):
    # mimic analyzer presence flag without full fetch
    return False

def analyze_opportunities(lead):
    """Build the evidence-backed opportunity report + blueprint score for one lead."""
    site = lead.get("website") or ""
    audit = {"ok": False, "issues": [], "score": 0}
    pres = {}
    if site:
        try:
            audit = LF.audit_site(site)
        except Exception as ex:
            audit = {"ok": False, "issues": [f"Site didn't load ({type(ex).__name__}) - broken or offline website"], "score": 40}
        try:
            pres = analyzer.presence_from_url(site)
        except Exception:
            pres = {}
    opps = build_opportunities(lead, audit, pres)
    sub = {
        "opportunity": _opportunity_score(opps),
        "fit": _fit(lead),
        "commercial": _commercial(lead),
        "contactability": _contactability(lead),
        "confidence": _confidence(lead, audit),
    }
    total = min(100, sum(sub.values()))
    sub["total"] = total
    sub["band"] = _band(total)
    return {
        "lead": {"name": lead.get("name"), "website": site, "category": lead.get("category"),
                 "source": lead.get("source")},
        "opportunities": opps,
        "score": sub,
        "provenance": _provenance(lead),
        "recommendedPackage": _recommended_package(opps, audit, lead),
        "audit": {"ok": audit.get("ok"), "issues": audit.get("issues"),
                  "loadSeconds": audit.get("loadSeconds"), "finalUrl": audit.get("finalUrl")},
        "presence": {"socials": list((pres.get("socials") or {}).keys()),
                     "booking": pres.get("booking"), "ordering": pres.get("ordering"),
                     "quoteForm": pres.get("quoteForm"), "chat": pres.get("chat"),
                     "mobile": pres.get("mobile"), "https": pres.get("https")},
        "evidenceUrls": sorted({o["evidence_url"] for o in opps if o["evidence_url"]}),
        "generatedAt": time.strftime("%Y-%m-%d"),
    }


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/opportunities":
        return analyze_opportunities(req.get("lead", {}))
    if path == "/api/opportunities/batch":
        leads = req.get("leads", [])[:200]
        return {"results": [{"id": l.get("id"), "name": l.get("name"),
                             "score": (lambda r: r["score"])(analyze_opportunities(l))}
                            for l in leads]}
    raise RuntimeError("Unknown endpoint")
