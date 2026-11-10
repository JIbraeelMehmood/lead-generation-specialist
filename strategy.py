"""
strategy.py — AI Strategy Generation for LeadFinder.

Ported from leadgenius-ai (Next.js + Gemini) — generates structured 30-day and
90-day lead generation strategy plans using LeadFinder's existing AI pool.

Key features:
  - Business profile intake (describe in plain English → structured form)
  - Magic Auto-Fill: AI fills structured profile from plain English description
  - 30-day action plan with weekly milestones
  - 90-day scaling path with revenue potential
  - Target ICP definition + lead source recommendations
  - AI-generated email/WhatsApp outreach template sets per stage
  - Hot/Warm/Cold lead qualification criteria for the niche
  - Stored in data/strategy.json (one strategy per profile)

Uses: LeadFinder's AI pool (Gemini, Groq, Ollama, etc.) — no extra API keys needed.
"""
import json, os, time, re

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STRATEGY_FILE = os.path.join(DATA_DIR, "strategy.json")


# ── Storage helpers ───────────────────────────────────────────────────────────

def _load_all() -> dict:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.isfile(STRATEGY_FILE):
        return {}
    try:
        with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_all(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


# ── Auto-fill: plain English → structured profile ─────────────────────────────

def autofill_profile(description: str) -> dict:
    """
    Given a plain-English description of your business (e.g. "I'm a freelance web
    developer in Karachi, Pakistan working with restaurants and salons"),
    return a structured profile dict.
    Ported from LeadGenius AI's Magic Auto-Fill pattern.
    """
    prompt = f"""Extract structured business profile information from this description.

Description: "{description}"

Return ONLY valid JSON with these fields:
{{
  "business_type": "<what you do, e.g. Web Development, SEO Agency>",
  "your_name": "<name if mentioned, else null>",
  "your_location": "<your city/country if mentioned>",
  "target_niche": "<the type of businesses you target, e.g. restaurants, salons, dentists>",
  "target_location": "<city/region you're targeting>",
  "primary_service": "<your main service offering>",
  "price_range": "<rough price range if mentioned, else null>",
  "usp": "<your unique selling point if mentioned, else null>",
  "language": "<primary language for outreach: English, Spanish, etc.>"
}}"""
    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=400)
        text = result.get("text", "").strip()
        m = re.search(r'\{[\s\S]+\}', text)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return {"business_type": "", "target_niche": "", "target_location": "",
            "primary_service": description}


# ── Core strategy generation ──────────────────────────────────────────────────

def generate_strategy(profile: dict) -> dict:
    """
    Generate a full 30-day and 90-day lead generation strategy.
    Returns a strategy dict with sections for ICP, lead sources, outreach sequences,
    weekly milestones, and revenue potential.

    Ported from leadgenius-ai/app/api/generate-strategy/route.ts
    """
    business_type    = profile.get("business_type", "freelance service business")
    target_niche     = profile.get("target_niche", "local businesses")
    target_location  = profile.get("target_location", "")
    primary_service  = profile.get("primary_service", "digital services")
    price_range      = profile.get("price_range", "$500–$2,000 per project")
    usp              = profile.get("usp", "fast delivery and clear communication")
    language         = profile.get("language", "English")

    prompt = f"""You are an expert B2B lead generation strategist. Generate a detailed, actionable 
lead generation strategy for the following business.

BUSINESS PROFILE:
- Business type: {business_type}
- Primary service: {primary_service}
- Target niche: {target_niche}
- Target location: {target_location or "anywhere"}
- Price range: {price_range}
- USP: {usp}
- Outreach language: {language}

Generate a complete strategy in VALID JSON format with these exact sections:

{{
  "icp": {{
    "description": "<ideal customer profile in 2 sentences>",
    "hot_signals": ["<signal 1>", "<signal 2>", "<signal 3>"],
    "cold_signals": ["<signal that makes a lead unlikely to convert>"],
    "target_job_titles": ["<title 1>", "<title 2>"],
    "company_size": "<e.g. 1-10 employees, local brick-and-mortar>",
    "pain_points": ["<pain point 1>", "<pain point 2>", "<pain point 3>"]
  }},
  "lead_sources": [
    {{"source": "<e.g. Google Maps>", "query": "<exact search query to use>", "priority": "high|medium|low", "reason": "<why this source works>"}},
    {{"source": "<e.g. Google Dorking>", "query": "<exact dork query>", "priority": "high|medium|low", "reason": "<why>"}},
    {{"source": "<source 3>", "query": "<query>", "priority": "high|medium|low", "reason": "<why>"}}
  ],
  "qualification_criteria": {{
    "hot": "<what makes a lead HOT — book immediately>",
    "warm": "<what makes a lead WARM — nurture>",
    "cold": "<what makes a lead COLD — low priority>"
  }},
  "day_30_plan": {{
    "goal": "<specific measurable goal for first 30 days>",
    "week1": {{"focus": "<focus>", "tasks": ["<task 1>", "<task 2>", "<task 3>"], "target_leads": 20}},
    "week2": {{"focus": "<focus>", "tasks": ["<task 1>", "<task 2>", "<task 3>"], "target_leads": 30}},
    "week3": {{"focus": "<focus>", "tasks": ["<task 1>", "<task 2>", "<task 3>"], "target_leads": 20}},
    "week4": {{"focus": "<focus>", "tasks": ["<task 1>", "<task 2>", "<task 3>"], "target_leads": 15}},
    "kpis": ["<KPI 1: e.g. 50 leads found>", "<KPI 2>", "<KPI 3>"]
  }},
  "day_90_plan": {{
    "goal": "<specific measurable goal for 90 days>",
    "month2": {{"focus": "<focus>", "strategy": "<strategy>", "target": "<measurable target>"}},
    "month3": {{"focus": "<focus>", "strategy": "<strategy>", "target": "<measurable target>"}},
    "scaling_moves": ["<action to scale up at day 60>", "<action at day 75>", "<action at day 90>"]
  }},
  "email_sequence": [
    {{"step": 1, "day": 0, "subject": "<subject>", "purpose": "<purpose>", "hook": "<first 2 sentences>"}},
    {{"step": 2, "day": 3, "subject": "<subject>", "purpose": "<purpose>", "hook": "<first 2 sentences>"}},
    {{"step": 3, "day": 7, "subject": "<subject>", "purpose": "<purpose>", "hook": "<first 2 sentences>"}}
  ],
  "whatsapp_template": "<a brief WhatsApp opener message — max 2 sentences, conversational>",
  "revenue_potential": {{
    "conservative": "<monthly revenue estimate, low scenario>",
    "realistic": "<monthly revenue estimate, realistic scenario>",
    "optimistic": "<monthly revenue estimate, optimistic scenario>",
    "assumptions": "<key assumptions used in this estimate>"
  }},
  "quick_wins": ["<action you can take TODAY>", "<action this week>", "<action in first 2 weeks>"]
}}

Return ONLY valid JSON. Make it specific to the business described, not generic advice."""

    strategy = {
        "profile": profile,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "icp": {},
        "lead_sources": [],
        "qualification_criteria": {},
        "day_30_plan": {},
        "day_90_plan": {},
        "email_sequence": [],
        "whatsapp_template": "",
        "revenue_potential": {},
        "quick_wins": [],
        "error": None,
    }

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=2000)
        text = result.get("text", "").strip()
        # Extract JSON — handle markdown code fences
        text = re.sub(r'^```(?:json)?\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*```\s*$', '', text, flags=re.MULTILINE)
        m = re.search(r'\{[\s\S]+\}', text)
        if m:
            parsed = json.loads(m.group(0))
            for key in ("icp", "lead_sources", "qualification_criteria", "day_30_plan",
                        "day_90_plan", "email_sequence", "whatsapp_template",
                        "revenue_potential", "quick_wins"):
                if key in parsed:
                    strategy[key] = parsed[key]
    except json.JSONDecodeError as ex:
        strategy["error"] = f"AI response could not be parsed as JSON: {ex}"
    except Exception as ex:
        strategy["error"] = str(ex)

    return strategy


# ── Save / load strategy ──────────────────────────────────────────────────────

def save_strategy(strategy: dict) -> str:
    """Save a strategy. Returns its ID."""
    all_data = _load_all()
    sid = time.strftime("%Y%m%d%H%M%S")
    all_data[sid] = strategy
    # Keep last 10 strategies
    if len(all_data) > 10:
        oldest = sorted(all_data.keys())[:len(all_data) - 10]
        for k in oldest:
            del all_data[k]
    _save_all(all_data)
    return sid


def list_strategies() -> list:
    all_data = _load_all()
    return [
        {
            "id": sid,
            "generated_at": s.get("generated_at", ""),
            "business_type": s.get("profile", {}).get("business_type", ""),
            "target_niche": s.get("profile", {}).get("target_niche", ""),
            "goal": s.get("day_30_plan", {}).get("goal", ""),
        }
        for sid, s in sorted(all_data.items(), reverse=True)
    ]


def get_strategy(sid: str):
    all_data = _load_all()
    return all_data.get(sid)


def delete_strategy(sid: str):
    all_data = _load_all()
    all_data.pop(sid, None)
    _save_all(all_data)


# ── Marketing brief ────────────────────────────────────────────────────────────

def generate_marketing_brief(website_url: str) -> dict:
    """
    Read all pages of your own website and generate a marketing brief:
    who you are, what you offer, what's proven.
    Ported from Prospex's Marketing Brief feature.
    """
    import leadfinder as LF
    import urllib.parse

    url = LF.norm_url(website_url)
    if not url:
        return {"error": "Invalid URL"}

    base = "{0.scheme}://{0.netloc}".format(urllib.parse.urlparse(url))
    pages_to_read = [url, base + "/about", base + "/services", base + "/work",
                     base + "/portfolio", base + "/case-studies", base + "/pricing"]

    combined_text = ""
    for page_url in pages_to_read:
        try:
            html, _, _ = LF.fetch_text(page_url, timeout=10)
            text = re.sub(r'<[^>]+>', ' ', html)
            text = re.sub(r'\s+', ' ', text)[:1500]
            combined_text += f"\n--- {page_url} ---\n{text}"
        except Exception:
            continue
        if len(combined_text) > 6000:
            break

    if not combined_text.strip():
        return {"error": "Could not read any pages from that website"}

    prompt = f"""Read the following pages from a business website and generate a concise marketing brief.

Website pages:
{combined_text[:6000]}

Return ONLY valid JSON:
{{
  "company_name": "<name>",
  "tagline": "<one-sentence tagline that captures what they do>",
  "who_we_are": "<2-3 sentences: who the company is, their background>",
  "what_we_offer": ["<service/product 1>", "<service/product 2>", "<service/product 3>"],
  "proven_results": ["<result or proof point 1>", "<result or proof point 2>"],
  "target_customer": "<description of their ideal customer>",
  "differentiators": ["<what makes them different 1>", "<what makes them different 2>"],
  "cta": "<call to action they use on their site>"
}}"""

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=600)
        text = result.get("text", "").strip()
        m = re.search(r'\{[\s\S]+\}', text)
        if m:
            brief = json.loads(m.group(0))
            brief["website"] = website_url
            brief["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            return brief
    except Exception as ex:
        return {"error": str(ex)}

    return {"error": "AI did not return a valid brief"}


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    if path == "/api/strategy/autofill":
        profile = autofill_profile(req.get("description", ""))
        return {"profile": profile}

    if path == "/api/strategy/generate":
        profile = req.get("profile", {})
        if not profile:
            # Allow plain-English description to be passed directly
            description = req.get("description", "")
            if description:
                profile = autofill_profile(description)
        strategy = generate_strategy(profile)
        sid = save_strategy(strategy)
        strategy["id"] = sid
        return strategy

    if path == "/api/strategy/list":
        return {"strategies": list_strategies()}

    if path == "/api/strategy/get":
        sid = req.get("id", "")
        s = get_strategy(sid)
        if s:
            s["id"] = sid
            return s
        return {"error": "Strategy not found"}

    if path == "/api/strategy/delete":
        delete_strategy(req.get("id", ""))
        return {"ok": True}

    if path == "/api/strategy/brief":
        return generate_marketing_brief(req.get("website", ""))

    return {"error": f"Unknown strategy path: {path}"}
