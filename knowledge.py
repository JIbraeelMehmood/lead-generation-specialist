"""
knowledge.py — Principal-Awareness Knowledge Base for LeadFinder.

Ported from meta-automation/src/knowledge/knowledge-engine.js.

The knowledge base is a folder of plain Markdown files that act as the
SINGLE SOURCE OF TRUTH for who you are, what you offer, and how the AI
should write on your behalf. Every AI call in LeadFinder reads from here.

Default location: .leadfinder/knowledge/   (created automatically)

Standard files (all optional — system works with zero files):
  about.md       — your business description, background, what you do
  services.md    — approved services + excluded services
  founder.md     — your name, role, location, contact handles
  company.md     — company name, website, type, flagship product
  style.md       — your writing voice, tone, things to avoid
  lead-rules.md  — who is a good lead vs who to skip

Usage in AI prompts:
    import knowledge
    kb = knowledge.engine()
    system_prompt = kb.build_system_prompt()
    # then pass system_prompt to ai_pool.complete(prompt, pool, system=system_prompt)
"""
import os, re, time, threading, json

KNOWLEDGE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    ".leadfinder", "knowledge"
)
_CHECK_INTERVAL = 2.0   # re-read files at most every 2 seconds (mtime-based, like JS version)
_lock = threading.Lock()
_singleton = None


class KnowledgeEngine:
    """
    Reads all .md files from KNOWLEDGE_DIR, caches with mtime invalidation,
    and exposes them for injection into AI system prompts.

    Mirrors meta-automation KnowledgeEngine: same file names, same approach,
    but in Python using stdlib only.
    """

    def __init__(self, knowledge_dir: str = KNOWLEDGE_DIR):
        self.dir = knowledge_dir
        self._cache = {}          # filename -> {"mtime": float, "raw": str}
        self._last_checked = 0.0
        self._load_all()

    # ── File loading ──────────────────────────────────────────────────────────

    def _load_all(self, force: bool = False):
        now = time.time()
        with _lock:
            if not force and (now - self._last_checked < _CHECK_INTERVAL) and self._cache:
                return
            self._last_checked = now

        if not os.path.isdir(self.dir):
            return

        for fname in os.listdir(self.dir):
            if not fname.endswith(".md"):
                continue
            fpath = os.path.join(self.dir, fname)
            try:
                mtime = os.path.getmtime(fpath)
                cached = self._cache.get(fname)
                if force or not cached or cached["mtime"] != mtime:
                    with open(fpath, encoding="utf-8") as f:
                        raw = f.read()
                    self._cache[fname] = {"mtime": mtime, "raw": raw}
            except Exception:
                pass

    def get_raw(self, filename: str) -> str:
        """Return raw markdown content of a knowledge file, or '' if not found."""
        self._load_all()
        if not filename.endswith(".md"):
            filename = filename + ".md"
        return self._cache.get(filename, {}).get("raw", "")

    def get_all_raw(self) -> dict:
        """Return dict of {filename: raw_content} for all loaded files."""
        self._load_all()
        return {k: v["raw"] for k, v in self._cache.items()}

    def list_files(self) -> list:
        """Return list of loaded knowledge file names."""
        self._load_all()
        return sorted(self._cache.keys())

    # ── Structured parsers (mirrors KnowledgeEngine JS parsers) ──────────────

    def get_founder_info(self) -> dict:
        """Parse founder.md → {name, role, location, email, phone, linkedin, threads}."""
        raw = self.get_raw("founder.md")
        if not raw:
            return {}
        info = {}
        for field, pattern in [
            ("name",     r"(?:^|\n)\s*(?:##\s*)?Name\s*[:\-]\s*([^\n]+)"),
            ("role",     r"(?:^|\n)\s*(?:##\s*)?Role\s*[:\-]\s*([^\n]+)"),
            ("location", r"(?:^|\n)\s*(?:##\s*)?Location\s*[:\-]\s*([^\n]+)"),
            ("email",    r"(?:^|\n)\s*(?:##\s*)?Email\s*[:\-]\s*([^\n]+)"),
            ("phone",    r"(?:^|\n)\s*(?:##\s*)?(?:Phone|Mobile|WhatsApp)\s*[:\-]\s*([^\n]+)"),
            ("linkedin", r"linkedin\.com/in/([A-Za-z0-9\-_]+)"),
            ("threads",  r"threads\.(?:net|com)/@([A-Za-z0-9._\-]+)"),
        ]:
            m = re.search(pattern, raw, re.I | re.M)
            if m:
                info[field] = m.group(1).strip()
        return info

    def get_company_info(self) -> dict:
        """Parse company.md → {name, website, type, flagship, description}."""
        raw = self.get_raw("company.md")
        if not raw:
            return {}
        info = {}
        for field, pattern in [
            ("name",        r"(?:^|\n)\s*(?:##\s*)?(?:Company\s+)?Name\s*[:\-]\s*([^\n]+)"),
            ("website",     r"(?:^|\n)\s*(?:##\s*)?Website\s*[:\-]\s*([^\n]+)"),
            ("type",        r"(?:^|\n)\s*(?:##\s*)?(?:Company\s+)?Type\s*[:\-]\s*([^\n]+)"),
            ("flagship",    r"(?:^|\n)\s*(?:##\s*)?(?:Flagship\s+)?Product\s*[:\-]\s*([^\n]+)"),
            ("description", r"(?:^|\n)\s*(?:##\s*)?Description\s*[:\-]\s*([^\n]+)"),
        ]:
            m = re.search(pattern, raw, re.I | re.M)
            if m:
                info[field] = m.group(1).strip()
        # Fallback: first heading as company name
        if not info.get("name"):
            m = re.search(r"^#\s+([^\n]+)", raw, re.M)
            if m:
                info["name"] = m.group(1).strip()
        return info

    def get_approved_services(self) -> list:
        """Parse services.md → list of approved service names."""
        raw = self.get_raw("services.md")
        if not raw:
            return []
        approved = []
        in_exclusion = False
        for line in raw.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().upper()
                in_exclusion = any(w in heading for w in
                                   ("EXCLUD", "NOT A ", "OUT OF SCOPE", "DO NOT", "AVOID"))
                continue
            if not in_exclusion and (stripped.startswith("- ") or stripped.startswith("* ")):
                item = stripped[2:].strip()
                # Strip markdown links
                item = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", item).strip()
                if item:
                    approved.append(item)
        return approved

    def get_excluded_services(self) -> list:
        """Parse services.md → list of excluded/out-of-scope service names."""
        raw = self.get_raw("services.md")
        if not raw:
            return []
        excluded = []
        in_exclusion = False
        for line in raw.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                heading = stripped.lstrip("#").strip().upper()
                in_exclusion = any(w in heading for w in
                                   ("EXCLUD", "NOT A ", "OUT OF SCOPE", "DO NOT", "AVOID"))
                continue
            if in_exclusion and (stripped.startswith("- ") or stripped.startswith("* ")):
                item = stripped[2:].strip()
                item = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", item).strip()
                if item:
                    excluded.append(item)
        return excluded

    def get_writing_style(self) -> str:
        """Return raw style.md or communication-style.md content."""
        return self.get_raw("style.md") or self.get_raw("communication-style.md")

    def get_lead_rules(self) -> str:
        """Return raw lead-rules.md content."""
        return self.get_raw("lead-rules.md")

    # ── System prompt builder ─────────────────────────────────────────────────

    def build_system_prompt(self, include: list = None) -> str:
        """
        Build a comprehensive system prompt from all knowledge files.
        Inject into every AI call: ai_pool.complete(prompt, pool, system=kb.build_system_prompt())

        include: list of section names to include, e.g. ["about", "services", "style"]
                 None = include all non-empty files
        """
        self._load_all()
        sections = []

        file_to_section = {
            "about.md":     "ABOUT ME / MY BUSINESS",
            "company.md":   "COMPANY",
            "founder.md":   "FOUNDER",
            "services.md":  "SERVICES I OFFER",
            "style.md":     "WRITING STYLE & TONE",
            "communication-style.md": "WRITING STYLE & TONE",
            "lead-rules.md": "LEAD QUALIFICATION RULES",
            "positioning.md": "POSITIONING",
        }

        for fname, section_title in file_to_section.items():
            if include and section_title.lower().split()[0] not in [i.lower() for i in include]:
                continue
            raw = self.get_raw(fname)
            if raw.strip():
                sections.append(f"## {section_title}\n{raw.strip()}")

        if not sections:
            return ""

        return ("You have access to the following knowledge base about the user's business. "
                "Use this information to personalize every response.\n\n"
                + "\n\n---\n\n".join(sections))

    def is_empty(self) -> bool:
        """True if no knowledge files have been created yet."""
        self._load_all()
        return len(self._cache) == 0


# ── Singleton accessor ────────────────────────────────────────────────────────

def engine() -> KnowledgeEngine:
    """Return the shared KnowledgeEngine singleton (lazy-initialized)."""
    global _singleton
    if _singleton is None:
        _singleton = KnowledgeEngine()
    return _singleton


# ── Bootstrap: create directory and example files if missing ─────────────────

EXAMPLE_FILES = {
    "about.md": """# About My Business

**Business type:** [e.g. Freelance Web Developer / SEO Agency / Marketing Consultant]
**Location:** [Your city, country]
**Primary service:** [e.g. I build websites for local businesses in Karachi]
**Price range:** [e.g. $300–$800 per project]

## Background
[2–3 sentences about your background and experience]

## What makes me different
[Your USP — what you do better or differently than competitors]
""",
    "founder.md": """# Founder

Name: [Your Full Name]
Role: [Your Title, e.g. Founder & Lead Developer]
Location: [City, Country]
Email: [your@email.com]
Phone: [+1 234 567 8900]
LinkedIn: https://linkedin.com/in/yourprofile
""",
    "services.md": """# Services I Offer

- [Service 1, e.g. WordPress website design]
- [Service 2, e.g. E-commerce store setup (WooCommerce / Shopify)]
- [Service 3, e.g. Website speed optimization]
- [Service 4, e.g. SEO setup and on-page optimization]

## Services I Do NOT Offer (Exclusions)

- [e.g. Logo design / graphic design]
- [e.g. Paid advertising / Google Ads management]
- [e.g. Social media management]
""",
    "style.md": """# My Writing Style

**Tone:** [e.g. Professional but friendly. Never salesy. Concise.]
**Avoid:** [e.g. Buzzwords, corporate jargon, em dashes, passive voice]
**Personalization:** Always mention something specific about the lead's business
**CTA style:** [e.g. One soft ask per email: "Would a 15-minute call make sense?"]
**Length:** Keep emails under 120 words. No walls of text.
""",
    "lead-rules.md": """# Lead Qualification Rules

## Good leads (prioritize these)
- Businesses with no website or an outdated website (built before 2020)
- Restaurants, salons, dental clinics, real estate agents, gyms
- Rating ≥ 3.5 on Google Maps (legitimate business)
- Has a phone number listed

## Skip these
- Businesses that already have a modern, fast website
- Franchise chains (not decision-makers)
- Businesses with no phone or no online presence at all
- Companies outside my target city/region
""",
}

def bootstrap():
    """Create the knowledge directory and example files if they don't exist."""
    os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
    created = []
    for fname, content in EXAMPLE_FILES.items():
        fpath = os.path.join(KNOWLEDGE_DIR, fname)
        if not os.path.exists(fpath):
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(content)
            created.append(fname)
    if _singleton:
        _singleton._load_all(force=True)
    return created


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:
    kb = engine()

    if path == "/api/knowledge/list":
        kb._load_all(force=True)
        files = []
        for fname in kb.list_files():
            raw = kb.get_raw(fname)
            files.append({"name": fname, "size": len(raw), "preview": raw[:120]})
        return {"files": files, "dir": KNOWLEDGE_DIR, "empty": kb.is_empty()}

    if path == "/api/knowledge/get":
        fname = req.get("file", "")
        return {"file": fname, "content": kb.get_raw(fname)}

    if path == "/api/knowledge/save":
        fname = req.get("file", "")
        content = req.get("content", "")
        if not fname or not fname.endswith(".md"):
            return {"error": "File name must end in .md"}
        # Security: only allow simple filenames, no path traversal
        if "/" in fname or "\\" in fname or ".." in fname:
            return {"error": "Invalid file name"}
        os.makedirs(KNOWLEDGE_DIR, exist_ok=True)
        fpath = os.path.join(KNOWLEDGE_DIR, fname)
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(content)
        kb._load_all(force=True)
        return {"ok": True, "file": fname}

    if path == "/api/knowledge/delete":
        fname = req.get("file", "")
        if "/" in fname or "\\" in fname or ".." in fname:
            return {"error": "Invalid file name"}
        fpath = os.path.join(KNOWLEDGE_DIR, fname)
        if os.path.exists(fpath):
            os.remove(fpath)
        kb._cache.pop(fname, None)
        return {"ok": True}

    if path == "/api/knowledge/bootstrap":
        created = bootstrap()
        return {"created": created, "dir": KNOWLEDGE_DIR}

    if path == "/api/knowledge/prompt_preview":
        return {"system_prompt": kb.build_system_prompt()}

    if path == "/api/knowledge/structured":
        return {
            "founder":            kb.get_founder_info(),
            "company":            kb.get_company_info(),
            "approved_services":  kb.get_approved_services(),
            "excluded_services":  kb.get_excluded_services(),
            "writing_style":      kb.get_writing_style(),
            "lead_rules":         kb.get_lead_rules(),
        }

    return {"error": f"Unknown knowledge path: {path}"}
