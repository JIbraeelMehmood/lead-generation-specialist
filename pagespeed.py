"""
Google PageSpeed Insights adapter for LeadFinder — blueprint §8.

Uses the free PageSpeed Insights API (no key required for basic use;
optional key raises the quota). Returns Core Web Vitals:
  LCP, FID/INP, CLS, FCP, TTFB, Speed Index, Performance score (0–100).

Also extracts the top 3 actionable opportunities from Lighthouse audits.

Standard library only: urllib.request.
"""
import time, urllib.parse
import leadfinder as LF

PAGESPEED_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

CATEGORIES = {
    "performance": "Performance",
    "accessibility": "Accessibility",
    "best-practices": "Best Practices",
    "seo": "SEO",
}

# Audits we care most about for local business sites
KEY_AUDITS = [
    "first-contentful-paint",
    "largest-contentful-paint",
    "total-blocking-time",
    "cumulative-layout-shift",
    "speed-index",
    "interactive",
    "uses-optimized-images",
    "uses-webp-images",
    "render-blocking-resources",
    "uses-long-cache-ttl",
    "unused-javascript",
    "unused-css-rules",
    "efficient-animated-content",
    "uses-text-compression",
]


def _grade(score):
    if score is None:
        return "?"
    if score >= 90:
        return "Good"
    if score >= 50:
        return "Needs Improvement"
    return "Poor"


def _metric(lhr, audit_id):
    audit = (lhr.get("audits") or {}).get(audit_id, {})
    return {
        "id": audit_id,
        "title": audit.get("title", audit_id),
        "displayValue": audit.get("displayValue", ""),
        "score": audit.get("score"),
        "grade": _grade(audit.get("score")),
        "description": (audit.get("description") or "")[:200],
    }


def analyze_page(url, api_key=None, strategy="mobile"):
    """
    Fetch PageSpeed Insights for `url`.
    strategy: "mobile" or "desktop"
    Returns a dict with scores, Core Web Vitals, opportunities.
    """
    url = LF.norm_url(url)
    if not url:
        raise RuntimeError("Provide a URL to analyze.")
    params = {"url": url, "strategy": strategy}
    if api_key:
        params["key"] = api_key
    for cat in CATEGORIES:
        params[f"category"] = cat  # last one wins in urlencode, use list
    # urlencode with repeating keys for multiple categories
    qs_parts = [("url", url), ("strategy", strategy)]
    if api_key:
        qs_parts.append(("key", api_key))
    for cat in CATEGORIES:
        qs_parts.append(("category", cat))
    endpoint = PAGESPEED_URL + "?" + urllib.parse.urlencode(qs_parts)

    try:
        data = LF.http_json(endpoint, timeout=60)
    except RuntimeError as ex:
        raise RuntimeError(f"PageSpeed API error: {ex}")

    lhr = data.get("lighthouseResult") or {}
    cats = lhr.get("categories") or {}
    audits_raw = lhr.get("audits") or {}

    # Category scores (0-100)
    scores = {}
    for cid, clabel in CATEGORIES.items():
        c = cats.get(cid, {})
        raw = c.get("score")
        scores[clabel] = {"score": round(raw * 100) if raw is not None else None,
                          "grade": _grade(raw * 100 if raw is not None else None)}

    # Core Web Vitals
    cwv = {
        "FCP": _metric(lhr, "first-contentful-paint"),
        "LCP": _metric(lhr, "largest-contentful-paint"),
        "TBT": _metric(lhr, "total-blocking-time"),
        "CLS": _metric(lhr, "cumulative-layout-shift"),
        "SI":  _metric(lhr, "speed-index"),
        "TTI": _metric(lhr, "interactive"),
    }

    # Top opportunities (audits that need improvement, sorted by impact)
    opps = []
    for aid, audit in audits_raw.items():
        if audit.get("score") in (1, None):
            continue
        details = audit.get("details") or {}
        savings = details.get("overallSavingsMs") or details.get("overallSavingsBytes") or 0
        if audit.get("score", 1) < 0.9 or savings:
            opps.append({
                "id": aid,
                "title": audit.get("title", aid),
                "description": (audit.get("description") or "")[:200],
                "displayValue": audit.get("displayValue", ""),
                "score": audit.get("score"),
                "savingsMs": details.get("overallSavingsMs", 0),
            })
    opps.sort(key=lambda x: (x.get("score") or 1, -x.get("savingsMs", 0)))

    loading_exp = data.get("loadingExperience") or {}
    field_data = {}
    for metric_key, info in loading_exp.get("metrics", {}).items():
        field_data[metric_key] = {
            "category": info.get("category", ""),
            "percentile": info.get("percentile"),
        }

    return {
        "url": url,
        "strategy": strategy,
        "scores": scores,
        "cwv": cwv,
        "opportunities": opps[:8],
        "fieldData": field_data,
        "fetchTime": lhr.get("fetchTime", ""),
        "analyzedAt": time.strftime("%Y-%m-%d %H:%M"),
    }


def handle(path, req):
    import assistant
    api_key = req.get("apiKey") or assistant.cfg()["keys"].get("pagespeed", "")

    if path == "/api/pagespeed":
        url = req.get("url", "")
        strategy = req.get("strategy", "mobile")
        return analyze_page(url, api_key, strategy)

    if path == "/api/pagespeed/both":
        url = req.get("url", "")
        mobile = analyze_page(url, api_key, "mobile")
        desktop = analyze_page(url, api_key, "desktop")
        return {"mobile": mobile, "desktop": desktop}

    raise RuntimeError("Unknown endpoint")
