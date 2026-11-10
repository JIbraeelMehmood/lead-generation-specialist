"""
b2b.py — B2B International Buyer Discovery for LeadFinder.

Ported from b2b-buyer-discovery (TypeScript) — a multi-country, multi-keyword
search engine for finding B2B product buyers (not just local service businesses).

Key features absorbed:
  - Multi-keyword × multi-market batch Google CSE search
  - Dual-layer scoring: rule engine (11 filters) + AI deep scoring
  - WhatsApp direct links in output
  - Bilingual email generation (Spanish for LATAM, English elsewhere)
  - 12-point composite intent score
  - Contact enrichment: email/phone/WhatsApp from scraped pages

Uses: Google Custom Search API (same CSE key as dorking.py) or SerpApi.
"""
import re, time, urllib.parse
import leadfinder as LF

# ── Rule engine: quick filter (11 rules) ─────────────────────────────────────
# Skip sites that are suppliers/manufacturers/directories, not buyers.

SKIP_PATTERNS = re.compile(
    r'manufacturer|manufacturing|supplier|suppliers|wholesaler|wholesale|'
    r'importer|exporter|distributor|distributor|factory|factories|'
    r'alibaba|made-in-china|globalsources|tradekey|exportersindia|'
    r'yellowpages|yell\.com|yelp\.com|tripadvisor|trustpilot|'
    r'we manufacture|we produce|we supply|our factory|our plant',
    re.I
)

BUYER_SIGNALS = re.compile(
    r'rfq|request for quote|request for quotation|purchase order|'
    r'we are looking for|looking to buy|buying agent|procurement|'
    r'we import|we purchase|our buyer|buyer wanted|tender|bidding|'
    r'needed urgently|urgent requirement|required quantity|minimum order',
    re.I
)

WHATSAPP_RE = re.compile(r'(?:wa\.me|whatsapp\.com/send)[/?]+(\+?[\d\s-]{7,15})', re.I)
PHONE_RE    = re.compile(r'(?:\+?\d[\d\s\-().]{7,16}\d)')
EMAIL_RE    = re.compile(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,24}')

LATAM_COUNTRIES = {
    "Mexico", "Peru", "Chile", "Colombia", "Argentina", "Brazil",
    "Ecuador", "Bolivia", "Venezuela", "Paraguay", "Uruguay", "Guatemala",
    "Honduras", "El Salvador", "Costa Rica", "Panama", "Cuba", "Dominican Republic",
}

# ── Score labels ──────────────────────────────────────────────────────────────

def _score_band(score: int) -> dict:
    if score >= 10:
        return {"band": "🔴 Extremely High", "label": "extreme", "priority": 1}
    if score >= 7:
        return {"band": "🟠 High", "label": "high", "priority": 2}
    if score >= 4:
        return {"band": "🟡 Medium", "label": "medium", "priority": 3}
    return {"band": "🟢 Low", "label": "low", "priority": 4}


# ── Google CSE search ─────────────────────────────────────────────────────────

def _cse_search(keyword: str, market: str, cse_key: str, cx: str,
                max_results: int = 20) -> list:
    """Search Google CSE for buyer pages."""
    query = f"{keyword} buyer {market}"
    results = []
    start = 1
    while len(results) < max_results:
        params = {
            "key": cse_key, "cx": cx,
            "q": query, "num": min(10, max_results - len(results)),
            "start": start,
        }
        try:
            data = LF.http_json(
                "https://www.googleapis.com/customsearch/v1?" + urllib.parse.urlencode(params),
                timeout=20,
            )
        except Exception:
            break
        items = data.get("items", [])
        if not items:
            break
        for item in items:
            results.append({
                "url": item.get("link", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
            })
        if len(items) < 10:
            break
        start += 10
        time.sleep(0.5)
    return results


def _serpapi_search(keyword: str, market: str, serp_key: str,
                    max_results: int = 20) -> list:
    """Fallback: use SerpApi for buyer page discovery."""
    query = f"{keyword} buyer {market}"
    params = {
        "engine": "google", "q": query,
        "api_key": serp_key, "num": min(20, max_results),
    }
    try:
        data = LF.http_json(
            "https://serpapi.com/search.json?" + urllib.parse.urlencode(params),
            timeout=30,
        )
        return [{"url": r.get("link", ""), "title": r.get("title", ""),
                 "snippet": r.get("snippet", "")}
                for r in data.get("organic_results", [])]
    except Exception:
        return []


# ── Page scraping & contact extraction ───────────────────────────────────────

def _scrape_page(url: str) -> dict:
    """Download a page and extract contacts + buyer signals."""
    result = {"url": url, "emails": [], "phones": [], "whatsapp": "",
              "text": "", "buyer_signals": 0, "skip": False}
    try:
        html, final_url, _ = LF.fetch_text(url, timeout=12)
    except Exception:
        return result
    # Clean to text
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)[:5000]
    result["text"] = text
    result["url"] = final_url

    # Rule engine: skip suppliers
    if SKIP_PATTERNS.search(text[:2000]):
        result["skip"] = True
        return result

    # Count buyer signals
    result["buyer_signals"] = len(BUYER_SIGNALS.findall(text))

    # Contacts
    result["emails"] = list(set(EMAIL_RE.findall(html)))[:5]
    for m in WHATSAPP_RE.finditer(html):
        num = re.sub(r'[\s\-()]', '', m.group(1))
        if len(num) >= 7:
            result["whatsapp"] = f"https://wa.me/{num}"
            break
    phones = PHONE_RE.findall(text[:3000])
    result["phones"] = [p.strip() for p in phones[:3]]

    return result


# ── Rule-based score (0-10) ────────────────────────────────────────────────────

def _rule_score(scraped: dict, snippet: str = "") -> int:
    score = 0
    text = (scraped.get("text", "") + " " + snippet).lower()

    # Has contacts
    if scraped.get("emails"): score += 2
    if scraped.get("whatsapp"): score += 1
    if scraped.get("phones"): score += 1

    # Buyer signals in page text
    bs = scraped.get("buyer_signals", 0)
    score += min(bs * 2, 4)

    # Keyword mentions in snippet
    if re.search(r'buy|purchase|import|procure|order|sourcing', snippet, re.I):
        score += 1

    # Penalty: very generic landing page
    if len(scraped.get("text", "")) < 200:
        score -= 1

    return max(0, min(10, score))


# ── AI deep score ─────────────────────────────────────────────────────────────

def _ai_score(text: str, keyword: str, market: str) -> dict:
    """AI analysis for buyer intent (0-10 + reasoning). Uses LeadFinder's AI pool."""
    prompt = f"""Analyze this business page and score its likelihood of being a genuine B2B BUYER 
(not a seller/manufacturer/directory) for "{keyword}" in {market}.

Page text excerpt:
{text[:2500]}

Score on a scale of 0-10:
- 0-3: Likely supplier/manufacturer/directory, not a buyer
- 4-6: Possibly a buyer but unclear
- 7-9: Strong buyer signals
- 10: Confirmed buyer (RFQ, purchase order, urgent requirement mentioned)

Also identify:
- company_name: the company name if visible
- contact_name: decision maker name if visible

Return ONLY valid JSON:
{{"score": <0-10>, "reasoning": "<one sentence>", "company_name": "<or null>", "contact_name": "<or null>"}}"""

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=200)
        text_out = result.get("text", "").strip()
        json_match = re.search(r'\{[^{}]+\}', text_out, re.DOTALL)
        if json_match:
            import json
            return json.loads(json_match.group(0))
    except Exception:
        pass
    return {"score": 5, "reasoning": "AI unavailable", "company_name": None, "contact_name": None}


# ── Lead builder ──────────────────────────────────────────────────────────────

def _build_lead(url: str, title: str, snippet: str, scraped: dict,
                rule_s: int, ai_result: dict, keyword: str, market: str) -> dict:
    """Assemble a LeadFinder-compatible lead dict from B2B search results."""
    import hashlib, time
    combined_score = rule_s + ai_result.get("score", 5)  # max 20, normalized to 12
    score_12 = min(12, round(combined_score * 12 / 20))

    band = _score_band(score_12)
    email = (scraped.get("emails") or [""])[0]
    phone = (scraped.get("phones") or [""])[0]
    whatsapp = scraped.get("whatsapp", "")

    # Tags
    tags = []
    if score_12 >= 10: tags.append("🔥 price_inquiry")
    if re.search(r'distributor|distribution', scraped.get("text", ""), re.I): tags.append("⭐ distributor")
    if email: tags.append("📧 has_email")
    if whatsapp: tags.append("💬 has_whatsapp")

    name = (ai_result.get("company_name") or title or url).strip()[:80]
    lid = "b2b:" + hashlib.md5(url.encode()).hexdigest()[:10]

    return {
        "id": lid,
        "source": "B2B Buyer Hunt",
        "name": name,
        "category": f"B2B Buyer — {keyword}",
        "address": market,
        "phone": phone,
        "email": email,
        "website": url,
        "social": whatsapp,
        "social_handles": {"whatsapp": whatsapp} if whatsapp else {},
        "rating": None,
        "reviews": 0,
        "mapsUrl": "",
        "lat": None, "lng": None,
        "score": score_12,
        "bp_score": score_12,
        "priority": "high" if score_12 >= 7 else "normal",
        "stage": "New",
        "tags": tags,
        "search_query": f"{keyword} in {market}",
        "intent_score": score_12,
        "intent_band": band["band"],
        "rule_score": rule_s,
        "ai_score": ai_result.get("score", 0),
        "ai_reasoning": ai_result.get("reasoning", ""),
        "owner_name": ai_result.get("contact_name", "") or "",
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        # Outreach helpers
        "whatsapp_link": whatsapp,
        "linkedin_search": f"https://www.linkedin.com/search/results/companies/?keywords={urllib.parse.quote(name)}",
        "is_latam": market in LATAM_COUNTRIES,
    }


# ── Email generation ──────────────────────────────────────────────────────────

def generate_outreach_email(lead: dict, your_product: str,
                            your_company: str = "", language: str = "auto") -> dict:
    """
    Generate a bilingual outreach email (Spanish for LATAM, English otherwise).
    Ported from b2b-buyer-discovery/src/skills/email/composer.ts
    """
    if language == "auto":
        language = "spanish" if lead.get("is_latam") else "english"

    name = lead.get("name", "")
    country = lead.get("address", "")

    if language == "spanish":
        prompt = f"""Escribe un correo de ventas B2B profesional en ESPAÑOL para:
Empresa destino: {name} en {country}
Nuestro producto: {your_product}
Nuestra empresa: {your_company or "nuestra compañía"}

El correo debe:
- Ser conciso (máx 150 palabras)
- Mencionar el producto específico y su utilidad para ellos
- Tener un CTA claro: solicitar una cotización o reunión
- Sonar profesional y no genérico

Formato: Asunto en la primera línea, luego el cuerpo del correo."""
    else:
        prompt = f"""Write a professional B2B sales email in ENGLISH for:
Target company: {name} in {country}
Our product: {your_product}
Our company: {your_company or "our company"}

The email should:
- Be concise (max 150 words)
- Mention the specific product and its relevance to them
- Have a clear CTA: request a quote or meeting
- Sound professional and specific, not generic

Format: Subject line first, then the email body."""

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=400)
        text = result.get("text", "").strip()
        lines = text.split("\n", 1)
        subject = lines[0].strip().lstrip("Subject:").lstrip("Asunto:").strip()
        body = lines[1].strip() if len(lines) > 1 else text
        return {"subject": subject, "body": body, "language": language}
    except Exception as ex:
        return {"subject": f"RE: {your_product}", "body": "", "error": str(ex)}


# ── Main hunt function ─────────────────────────────────────────────────────────

def hunt(keyword: str, markets: list, min_score: int = 5,
         max_per_keyword: int = 20) -> list:
    """
    Run B2B buyer discovery across multiple markets.

    Args:
        keyword:         Product/category to search for buyers of
        markets:         List of country names to search in
        min_score:       Minimum 12-point intent score to include
        max_per_keyword: Max search results per keyword × market combo

    Returns:
        List of LeadFinder-compatible lead dicts, sorted by intent score desc.
    """
    import assistant
    c = assistant.cfg()
    cse_key = c["keys"].get("cse", "")
    cx = c["keys"].get("cseId", "")
    serp_key = c["keys"].get("serp", "")

    if not cse_key and not serp_key:
        raise RuntimeError(
            "B2B Buyer Hunt needs a Google Custom Search API key (Settings → Additional API keys → CSE key) "
            "or a SerpApi key."
        )

    all_leads = []
    seen_urls = set()

    for market in markets:
        # Search
        if cse_key and cx:
            raw_results = _cse_search(keyword, market, cse_key, cx, max_per_keyword)
        else:
            raw_results = _serpapi_search(keyword, market, serp_key, max_per_keyword)

        import db
        for item in raw_results:
            url = item.get("url", "")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # Scrape
            scraped = _scrape_page(url)
            if scraped.get("skip"):
                continue

            # Score
            rule_s = _rule_score(scraped, item.get("snippet", ""))
            if rule_s < 2:  # quick filter: too low to be worth AI call
                continue

            ai_result = _ai_score(scraped.get("text", ""), keyword, market)
            combined = rule_s + ai_result.get("score", 0)
            score_12 = min(12, round(combined * 12 / 20))

            if score_12 < min_score:
                continue

            lead = _build_lead(url, item.get("title", ""), item.get("snippet", ""),
                               scraped, rule_s, ai_result, keyword, market)
            all_leads.append(lead)

            # Publish progress event
            try:
                db.publish_event("b2b_lead_found", {
                    "name": lead["name"], "score": score_12, "market": market
                })
            except Exception:
                pass

            time.sleep(0.3)  # polite delay

    # Sort by score desc
    all_leads.sort(key=lambda l: l.get("score", 0), reverse=True)
    return all_leads


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/b2b/hunt":
        leads = hunt(
            keyword=req.get("keyword", ""),
            markets=req.get("markets", []),
            min_score=int(req.get("min_score", 5)),
            max_per_keyword=int(req.get("max_per_keyword", 20)),
        )
        # Save to DB
        try:
            import db
            for lead in leads:
                db.upsert_lead(lead)
        except Exception:
            pass
        return {"leads": leads, "count": len(leads)}

    if path == "/api/b2b/email":
        return generate_outreach_email(
            req.get("lead", {}),
            your_product=req.get("product", ""),
            your_company=req.get("company", ""),
            language=req.get("language", "auto"),
        )

    if path == "/api/b2b/score":
        lead = req.get("lead", {})
        url = lead.get("website", "")
        scraped = _scrape_page(url) if url else {}
        rule_s = _rule_score(scraped, lead.get("snippet", ""))
        ai_result = _ai_score(scraped.get("text", ""),
                              req.get("keyword", ""), req.get("market", ""))
        combined = rule_s + ai_result.get("score", 0)
        score_12 = min(12, round(combined * 12 / 20))
        return {
            "rule_score": rule_s,
            "ai_score": ai_result.get("score", 0),
            "total_score": score_12,
            "band": _score_band(score_12),
            "reasoning": ai_result.get("reasoning", ""),
        }

    return {"error": f"Unknown b2b path: {path}"}
