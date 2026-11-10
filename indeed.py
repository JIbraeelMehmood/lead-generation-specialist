"""
indeed.py — Indeed Hiring Signals for LeadFinder.

Ported from Google-Maps-Lead-Generation/app/lib/indeed.js (Mapleads).

Scrapes Indeed job postings to surface businesses that are actively hiring —
a strong buying-intent signal (companies hiring = growing = budget = potential clients).

Since Playwright is optional in LeadFinder, this module has two modes:
  1. Playwright mode (optional, install: playwright install chromium)
     — Full browser scraping, same approach as Mapleads indeed.js
     — Handles pagination, anti-bot jitter, 403 retries
  2. HTTP fallback (stdlib only, no install)
     — Direct HTTP request with browser headers
     — Works for most searches but may hit Cloudflare on some regions

Fields scraped per job card:
  jobTitle, company, location, snippet, salary, jobUrl, postedText

The company name from job posts is cross-referenced against the lead DB —
if a company in your pipeline is hiring, it's flagged as a hot signal.
"""
import re, time, urllib.parse, json, random
import leadfinder as LF

# ── Constants ─────────────────────────────────────────────────────────────────

INDEED_BASE = "https://www.indeed.com/jobs"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
RESULTS_PER_PAGE = 15
MAX_PAGES        = 7     # indeed caps at ~100 results, 15/page

# CSS selectors for indeed job cards (from Mapleads indeed.js)
# Indeed uses two card variants: div.job_seen_beacon and td.resultContent
_CARD_SELECTORS = ["div.job_seen_beacon", "td.resultContent"]

# Regex extractors for stdlib/HTTP mode (parse HTML without browser)
_TITLE_RE    = re.compile(r'<h2[^>]+class="[^"]*jobTitle[^"]*"[^>]*>.*?<span[^>]*>([^<]+)</span>', re.S | re.I)
_COMPANY_RE  = re.compile(r'data-testid="company-name"[^>]*>([^<]+)<', re.I)
_LOCATION_RE = re.compile(r'data-testid="text-location"[^>]*>([^<]+)<', re.I)
_SALARY_RE   = re.compile(r'class="[^"]*salary-snippet[^"]*"[^>]*>([^<]+)<', re.I)
_DATE_RE     = re.compile(r'class="[^"]*date[^"]*"[^>]*>([^<]+)<', re.I)
_LINK_RE     = re.compile(r'<h2[^>]+class="[^"]*jobTitle[^"]*"[^>]*>\s*<a[^>]+href="(/viewjob[^"]+)"', re.I)
_SNIPPET_RE  = re.compile(r'class="[^"]*job-snippet[^"]*"[^>]*>(.*?)</(?:ul|div)>', re.S | re.I)
_BLOCKED_RE  = re.compile(r"(enable javascript|cloudflare|just a moment|checking your browser)", re.I)


def _jitter(base_ms: int, spread_ms: int) -> float:
    """Random delay matching Mapleads jitter(baseMs, spreadMs)."""
    return (base_ms + random.randint(0, spread_ms)) / 1000.0


def _strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").strip()


# ── HTTP fallback scraper (stdlib only) ───────────────────────────────────────

def _search_http(keyword: str, location: str, max_results: int = 50) -> list:
    """
    Scrape Indeed via stdlib HTTP requests + regex.
    Good for most cases; may hit anti-bot on some IPs.
    """
    jobs = []
    seen_urls = set()
    pages = min((max_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE, MAX_PAGES)

    for page_idx in range(pages):
        params = {"q": keyword, "start": str(page_idx * RESULTS_PER_PAGE)}
        if location:
            params["l"] = location
        url = INDEED_BASE + "?" + urllib.parse.urlencode(params)

        try:
            html, _, _ = LF.fetch_text(url, timeout=20)
        except Exception:
            break

        if _BLOCKED_RE.search(html[:2000]):
            if jobs:
                break
            raise RuntimeError(
                "Indeed blocked this request (Cloudflare). "
                "Try again, use a VPN, or install Playwright for browser-mode scraping."
            )

        # Extract job cards via regex
        # Split on job card boundaries
        card_boundaries = list(re.finditer(r'class="[^"]*(?:job_seen_beacon|resultContent)[^"]*"', html))
        if not card_boundaries:
            break

        for i, m in enumerate(card_boundaries):
            start = m.start()
            end = card_boundaries[i + 1].start() if i + 1 < len(card_boundaries) else start + 3000
            chunk = html[start:end]

            title_m   = _TITLE_RE.search(chunk)
            company_m = _COMPANY_RE.search(chunk)
            if not title_m or not company_m:
                continue

            title   = _strip_tags(title_m.group(1))
            company = _strip_tags(company_m.group(1))

            loc_m     = _LOCATION_RE.search(chunk)
            salary_m  = _SALARY_RE.search(chunk)
            date_m    = _DATE_RE.search(chunk)
            link_m    = _LINK_RE.search(chunk)
            snippet_m = _SNIPPET_RE.search(chunk)

            job_url = ""
            if link_m:
                job_url = "https://www.indeed.com" + link_m.group(1).replace("&amp;", "&")
            if job_url in seen_urls:
                continue
            seen_urls.add(job_url)

            snippet = _strip_tags(snippet_m.group(1)) if snippet_m else ""
            snippet = re.sub(r"\s+", " ", snippet).strip()[:200]

            jobs.append({
                "jobTitle":   title,
                "company":    company,
                "location":   _strip_tags(loc_m.group(1))   if loc_m    else "",
                "snippet":    snippet,
                "salary":     _strip_tags(salary_m.group(1)) if salary_m else "",
                "postedText": _strip_tags(date_m.group(1))   if date_m   else "",
                "jobUrl":     job_url,
                "source":     "indeed:http",
            })

            if len(jobs) >= max_results:
                break

        if len(jobs) >= max_results:
            break

        time.sleep(_jitter(1200, 800))

    return jobs[:max_results]


# ── Playwright scraper (optional, mirrors Mapleads indeed.js exactly) ─────────

def _search_playwright(keyword: str, location: str, max_results: int = 50) -> list:
    """
    Browser-based scraping using Playwright (optional dependency).
    Identical approach to Mapleads indeed.js:
      - stealth headers, viewport, Accept-Language
      - jitter delays between pages and between cards
      - up to MAX_PAGE_RETRIES=2 on 403
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError(
            "Playwright not installed. Run: pip install playwright && playwright install chromium\n"
            "Or use the HTTP fallback by not setting use_playwright=True."
        )

    jobs = []
    pages = min((max_results + RESULTS_PER_PAGE - 1) // RESULTS_PER_PAGE, MAX_PAGES)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=UA,
            locale="en-US",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        page = context.new_page()
        page.set_default_timeout(1000)

        seen_urls = set()

        for page_idx in range(pages):
            params = {"q": keyword, "start": str(page_idx * RESULTS_PER_PAGE)}
            if location:
                params["l"] = location
            url = INDEED_BASE + "?" + urllib.parse.urlencode(params)

            response = None
            for attempt in range(3):
                try:
                    response = page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    if response and response.ok:
                        break
                    if response and response.status != 403:
                        break
                except Exception:
                    response = None
                if attempt < 2:
                    page.wait_for_timeout(int(_jitter(2000, 2000) * (attempt + 1) * 1000))

            if not response or not response.ok:
                if jobs:
                    break
                raise RuntimeError(
                    f"Indeed blocked (status {response.status if response else 'unknown'}). "
                    "This is Indeed's anti-bot — may pass on retry or with smaller batch."
                )

            page.wait_for_timeout(int(_jitter(1200, 800) * 1000))

            # Collect all cards
            cards = []
            for sel in _CARD_SELECTORS:
                try:
                    cards = page.locator(sel).all()
                    if cards:
                        break
                except Exception:
                    pass

            if not cards:
                break

            for card in cards:
                def safe_text(selector):
                    try:
                        return card.locator(selector).first.inner_text(timeout=1000).strip()
                    except Exception:
                        return ""

                def safe_attr(selector, attr):
                    try:
                        return card.locator(selector).first.get_attribute(attr, timeout=1000)
                    except Exception:
                        return None

                title   = safe_text("h2.jobTitle span")
                company = safe_text('span[data-testid="company-name"]')
                if not title or not company:
                    continue

                relative_link = safe_attr("h2.jobTitle a", "href")
                job_url = ("https://www.indeed.com" + relative_link) if relative_link else ""
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                jobs.append({
                    "jobTitle":   title,
                    "company":    company,
                    "location":   safe_text('div[data-testid="text-location"]'),
                    "snippet":    re.sub(r"\s+", " ", safe_text('div[class*="job-snippet"]'))[:200],
                    "salary":     safe_text('div[class*="salary-snippet"], div[data-testid="attribute_snippet_testid"]'),
                    "postedText": safe_text('span[class*="date"]'),
                    "jobUrl":     job_url,
                    "source":     "indeed:playwright",
                })

                if len(jobs) >= max_results:
                    break

            if len(jobs) >= max_results:
                break
            page.wait_for_timeout(int(_jitter(800, 700) * 1000))

        browser.close()

    return jobs[:max_results]


# ── Cross-reference against LeadFinder pipeline ───────────────────────────────

def _cross_reference(jobs: list) -> list:
    """
    For each job, check if the hiring company is already in the LeadFinder
    pipeline. If so, flag it as a hot signal and add the pipeline stage.
    """
    try:
        import db
        leads = db.get_leads(limit=2000)
        lead_names = {l["name"].lower(): l for l in leads}
    except Exception:
        return jobs

    for job in jobs:
        company_lower = (job.get("company") or "").lower()
        matched_lead = None
        for lead_name, lead in lead_names.items():
            # Fuzzy: company name contained in lead name or vice versa
            if company_lower in lead_name or lead_name in company_lower:
                matched_lead = lead
                break
        if matched_lead:
            job["in_pipeline"] = True
            job["pipeline_stage"] = matched_lead.get("stage", "")
            job["pipeline_lead_id"] = matched_lead.get("id", "")
        else:
            job["in_pipeline"] = False

    return jobs


# ── Main search function ──────────────────────────────────────────────────────

def search(keyword: str, location: str = "", max_results: int = 50,
           use_playwright: bool = False) -> list:
    """
    Search Indeed for job postings.

    Args:
        keyword:        Job search keyword (e.g. "web developer", "marketing manager")
        location:       City/state/country (e.g. "New York, NY" or "United Kingdom")
        max_results:    Max jobs to return (capped at 100)
        use_playwright: True to use Playwright browser (more reliable, needs install)

    Returns:
        List of job dicts: jobTitle, company, location, snippet, salary,
                           postedText, jobUrl, source, in_pipeline
    """
    max_results = min(int(max_results), 100)

    if use_playwright:
        jobs = _search_playwright(keyword, location, max_results)
    else:
        jobs = _search_http(keyword, location, max_results)

    return _cross_reference(jobs)


# ── Scoring ───────────────────────────────────────────────────────────────────

def score_job(job: dict, your_skills: list = None) -> int:
    """
    Score a job posting 0-10 as a lead opportunity signal.
    Higher = stronger buying-intent indicator.
    Ported from LeadFinder's hiring.py scoring approach.
    """
    score = 0
    text = (job.get("jobTitle", "") + " " + job.get("snippet", "")).lower()

    # Company in pipeline already = very hot
    if job.get("in_pipeline"):
        score += 4

    # Skills match
    if your_skills:
        for skill in your_skills:
            if skill.lower() in text:
                score += 2
                break

    # Urgency signals
    if re.search(r"\b(urgent|immediately|asap|now|start date)\b", text):
        score += 1

    # Budget signals
    if job.get("salary"):
        score += 1

    # Recent posting
    posted = (job.get("postedText") or "").lower()
    if any(w in posted for w in ("today", "1 day", "just posted")):
        score += 2
    elif any(w in posted for w in ("2 day", "3 day")):
        score += 1

    return min(10, score)


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/indeed/search":
        keyword     = req.get("keyword", "")
        location    = req.get("location", "")
        max_results = int(req.get("maxResults", 50))
        use_pw      = bool(req.get("use_playwright", False))
        if not keyword:
            return {"error": "keyword is required"}
        try:
            jobs = search(keyword, location, max_results, use_pw)
            return {"count": len(jobs), "jobs": jobs}
        except RuntimeError as ex:
            return {"error": str(ex), "jobs": []}

    if path == "/api/indeed/score":
        job    = req.get("job", {})
        skills = req.get("skills", [])
        return {"score": score_job(job, skills)}

    return {"error": f"Unknown indeed path: {path}"}
