"""
deepscan.py — Playwright Deep Scan for LeadFinder.

Ported from Google-Maps-Lead-Generation (Mapleads) deep-extract API route.

Extracts data from Google Maps listings that the Places API does not expose:
  - Business description
  - Owner's response rate and recent replies to reviews
  - Photo count
  - Popular times
  - Menu / services listed
  - Website email (by visiting the actual website during the scan)
  - Social links (Facebook, Instagram, etc.)

Requires: playwright install chromium  (optional — falls back gracefully)

Also supports generic Playwright scraping for any URL (deep website scan).
"""
import re, time, json, os

import leadfinder as LF
import db

# ── Playwright availability check ─────────────────────────────────────────────

def _has_playwright() -> bool:
    try:
        import playwright  # noqa
        return True
    except ImportError:
        return False


# ── Google Maps deep scan ─────────────────────────────────────────────────────

def deep_scan_maps_listing(maps_url: str, lead_id: str = "") -> dict:
    """
    Scrape a Google Maps listing page for fields the Places API doesn't expose.
    Returns a dict of extracted fields.
    """
    if not maps_url:
        return {"error": "No Maps URL provided"}

    if not _has_playwright():
        return {
            "error": "Playwright not installed.",
            "install": "pip install playwright && playwright install chromium",
            "fallback": _http_deep_scan(maps_url),
        }

    from playwright.sync_api import sync_playwright

    result = {
        "maps_url": maps_url,
        "description": "",
        "owner_response_rate": "",
        "photo_count": 0,
        "popular_times": [],
        "menu_items": [],
        "emails_on_site": [],
        "social_links": {},
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                locale="en-US",
                viewport={"width": 1366, "height": 900},
            )
            page = context.new_page()
            page.set_default_timeout(2000)

            page.goto(maps_url, wait_until="domcontentloaded", timeout=25000)
            page.wait_for_timeout(2000)

            def safe_text(selector):
                try:
                    return page.locator(selector).first.inner_text(timeout=1500).strip()
                except Exception:
                    return ""

            def safe_all(selector):
                try:
                    return [el.inner_text(timeout=1000).strip()
                            for el in page.locator(selector).all()
                            if el.inner_text(timeout=500).strip()][:10]
                except Exception:
                    return []

            # Description
            result["description"] = (
                safe_text('[data-attrid="kc:/local:place_description"] span') or
                safe_text('div[data-section-id="dsg"] div') or
                safe_text('div.PYvSYb')
            )

            # Photo count
            photo_text = safe_text('div[data-tab-index] button[aria-label*="photo"]')
            m = re.search(r"(\d[\d,]+)", photo_text)
            if m: result["photo_count"] = int(m.group(1).replace(",", ""))

            # Owner responses in reviews
            owner_responses = page.locator('div[class*="CDe7pd"]').count()
            result["owner_response_rate"] = f"{owner_responses} owner responses visible"

            # Popular times hours
            pt_items = safe_all('div[aria-label*="Popular times"] li, div[data-popular-times] li')
            result["popular_times"] = pt_items[:7]

            # Menu items
            menu_items = safe_all('div[aria-label="Menu"] li, div[data-section-id="mtm"] li')
            result["menu_items"] = menu_items[:10]

            browser.close()

    except Exception as ex:
        result["playwright_error"] = str(ex)
        # Fall back to HTTP scan
        result["fallback"] = _http_deep_scan(maps_url)

    # Persist to lead if provided
    if lead_id:
        try:
            db.update_lead_field(lead_id, audit_data=result)
        except Exception:
            pass
        db.publish_event("deep_scan_done", {"lead_id": lead_id, **{k: v for k, v in result.items() if k != "fallback"}})

    return result


# ── HTTP fallback scan (stdlib only) ──────────────────────────────────────────

def _http_deep_scan(url: str) -> dict:
    """
    Stdlib-only deep scan: fetch the page and extract as much as possible via regex.
    Less reliable than Playwright but works without any install.
    """
    result = {"emails": [], "social": {}, "phone": "", "description": ""}
    try:
        html, final_url, _ = LF.fetch_text(url, timeout=15)

        # Emails
        emails = list(set(re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", html)))
        result["emails"] = [e for e in emails if not e.endswith((".png", ".jpg", ".gif"))][:5]

        # Social links
        from enrich import SOCIAL_PATTERNS
        for platform, pattern in SOCIAL_PATTERNS.items():
            m = pattern.search(html)
            if m:
                result["social"][platform] = m.group(1).rstrip("/")

        # Description / meta description
        meta_m = re.search(r'<meta\s+name="description"\s+content="([^"]+)"', html, re.I)
        if meta_m:
            result["description"] = meta_m.group(1)[:300]

    except Exception:
        pass
    return result


# ── Generic website deep scan ─────────────────────────────────────────────────

def deep_scan_website(website_url: str, lead_id: str = "") -> dict:
    """
    Deep scan a business website using Playwright (or HTTP fallback).
    Goes beyond the home page — also visits /about, /contact, /team.
    """
    url = LF.norm_url(website_url)
    if not url:
        return {"error": "Invalid URL"}

    if _has_playwright():
        return _playwright_website_scan(url, lead_id)
    return _http_website_scan(url, lead_id)


def _playwright_website_scan(url: str, lead_id: str = "") -> dict:
    from playwright.sync_api import sync_playwright
    import urllib.parse

    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    pages_to_visit = [url, base + "/about", base + "/about-us",
                      base + "/contact", base + "/team"]

    result = {
        "url": url,
        "emails": [],
        "phones": [],
        "social_links": {},
        "tech_stack": [],
        "decision_maker": {},
        "pages_scanned": 0,
        "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    seen_emails = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                           "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()
            page.set_default_timeout(2000)

            for page_url in pages_to_visit:
                try:
                    page.goto(page_url, wait_until="domcontentloaded", timeout=12000)
                    page.wait_for_timeout(800)
                    html = page.content()
                    result["pages_scanned"] += 1

                    # Emails
                    for em in re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", html):
                        if em not in seen_emails and not em.endswith((".png", ".jpg")):
                            seen_emails.add(em)
                            result["emails"].append(em)

                    # Phones
                    if not result["phones"]:
                        phones = re.findall(r"\+?[\d\s\-().]{7,16}\d", html)
                        result["phones"] = [p.strip() for p in phones[:3]]

                except Exception:
                    pass

            browser.close()

    except Exception as ex:
        result["error"] = str(ex)

    # Enrich with enrich.py
    try:
        import enrich
        result["social_links"] = enrich.social_handles(url)
        result["tech_stack"]   = enrich.tech_stack(url)
        result["decision_maker"] = enrich.quick_decision_maker(url)
    except Exception:
        pass

    # Persist
    if lead_id and (result["emails"] or result["decision_maker"]):
        try:
            updates = {}
            if result["emails"]:
                updates["email"] = result["emails"][0]
            if result["decision_maker"].get("name"):
                updates["owner_name"]     = result["decision_maker"]["name"]
                updates["decision_maker"] = result["decision_maker"]
            if result["social_links"]:
                updates["social_handles"] = result["social_links"]
            if result["tech_stack"]:
                updates["tech_stack"] = ", ".join(result["tech_stack"])
            if updates:
                db.update_lead_field(lead_id, **updates)
        except Exception:
            pass

    db.publish_event("deep_scan_done", {"lead_id": lead_id, "emails": len(result["emails"])})
    return result


def _http_website_scan(url: str, lead_id: str = "") -> dict:
    """Stdlib HTTP fallback for website deep scan."""
    try:
        import enrich
        result = {
            "url": url,
            "emails":    LF.find_emails(url).get("emails", []),
            "social_links": enrich.social_handles(url),
            "tech_stack":   enrich.tech_stack(url),
            "decision_maker": enrich.quick_decision_maker(url),
            "mode": "http_fallback",
            "scanned_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        return result
    except Exception as ex:
        return {"error": str(ex)}


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/deepscan/maps":
        return deep_scan_maps_listing(req.get("maps_url", ""), req.get("lead_id", ""))

    if path == "/api/deepscan/website":
        return deep_scan_website(req.get("website", ""), req.get("lead_id", ""))

    if path == "/api/deepscan/status":
        return {
            "playwright_available": _has_playwright(),
            "install_command": "pip install playwright && playwright install chromium",
        }

    return {"error": f"Unknown deepscan path: {path}"}
