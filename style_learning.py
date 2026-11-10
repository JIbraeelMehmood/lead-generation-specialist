"""
style_learning.py — AI Style Learning for LeadFinder.

Ported from Prospex's AI Style Learning feature (apps/api/src/messaging/message-writer.service.ts).

Learns your writing voice from:
  1. Your email/WhatsApp conversation exports (paste or upload)
  2. Your manually written email examples
  3. Your knowledge base style.md

The learned style is used to personalize every AI-generated email and message
so it sounds like YOU, not like a generic AI.

Stored in data/style_examples.json and .leadfinder/knowledge/style.md
"""
import json, os, re, time, threading

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
STYLE_FILE = os.path.join(DATA, "style_examples.json")
_lock = threading.RLock()

DEFAULT_STYLE = {
    "examples": [],         # list of {text, label, added_at}
    "learned_at": "",
    "profile": {
        "tone": "",
        "sentence_length": "",
        "greeting_style": "",
        "signature": "",
        "avoid": [],
        "patterns": [],
        "sample_opener": "",
        "sample_cta": "",
    }
}


# ── Storage ───────────────────────────────────────────────────────────────────

def _load():
    os.makedirs(DATA, exist_ok=True)
    try:
        with open(STYLE_FILE, encoding="utf-8") as f:
            d = json.load(f)
        out = dict(DEFAULT_STYLE)
        out.update(d)
        return out
    except Exception:
        return dict(DEFAULT_STYLE)

def _save(data: dict):
    os.makedirs(DATA, exist_ok=True)
    with _lock:
        tmp = STYLE_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f: json.dump(data, f, indent=2)
        os.replace(tmp, STYLE_FILE)


# ── Example management ────────────────────────────────────────────────────────

def add_example(text: str, label: str = "email") -> dict:
    """Add a writing example (email, WhatsApp message, etc.)."""
    text = text.strip()
    if not text:
        return {"error": "Empty text"}
    data = _load()
    data["examples"].insert(0, {
        "text": text[:2000],
        "label": label,
        "added_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })
    data["examples"] = data["examples"][:50]  # keep last 50
    _save(data)
    return {"ok": True, "count": len(data.get("examples", []))}

def remove_example(index: int) -> dict:
    data = _load()
    if 0 <= index < len(data["examples"]):
        data["examples"].pop(index)
        _save(data)
    return {"ok": True}

def clear_examples() -> dict:
    data = _load()
    data["examples"] = []
    _save(data)
    return {"ok": True}


# ── Import from chat export ───────────────────────────────────────────────────

def import_from_chat_export(raw_text: str, your_name: str = "") -> dict:
    """
    Parse a WhatsApp or email export and extract your own messages as examples.

    WhatsApp export format: "DD/MM/YYYY, HH:MM - Name: message"
    Gmail/Outlook: plain text conversations
    """
    added = 0
    # WhatsApp format
    wa_pattern = re.compile(
        r"\d{1,2}/\d{1,2}/\d{2,4},\s*\d{1,2}:\d{2}(?:\s*[AP]M)?\s*[-–]\s*(.+?):\s*(.+)",
        re.I
    )
    your_name_lower = (your_name or "").lower()

    for m in wa_pattern.finditer(raw_text):
        sender  = m.group(1).strip()
        message = m.group(2).strip()
        # Only keep YOUR messages
        if your_name_lower and your_name_lower not in sender.lower():
            continue
        if len(message) > 20 and not message.startswith("["):  # skip media refs
            add_example(message, "whatsapp_import")
            added += 1

    if added == 0:
        # Try email-style: lines starting with "> " are quotes, skip them
        lines = [l.strip() for l in raw_text.split("\n")
                 if l.strip() and not l.strip().startswith(">") and len(l.strip()) > 30]
        for line in lines[:20]:
            add_example(line, "email_import")
            added += 1

    return {"added": added, "total": len(_load()["examples"])}


# ── Learn style from examples using AI ───────────────────────────────────────

def learn_style() -> dict:
    """
    Analyze accumulated writing examples with AI and extract a style profile.
    Saves the profile to data/style_examples.json and updates .leadfinder/knowledge/style.md
    """
    data = _load()
    examples = data.get("examples", [])
    if len(examples) < 3:
        return {"error": "Add at least 3 writing examples before learning your style"}

    # Compose examples text for the prompt
    sample_texts = "\n\n---\n".join([f"Example {i+1}:\n{e['text']}" for i, e in enumerate(examples[:20])])

    prompt = f"""Analyze these {len(examples[:20])} writing samples and extract a detailed writing style profile.

{sample_texts}

Return a JSON object with these fields:
{{
  "tone": "<e.g. direct and professional | warm and casual | formal>",
  "sentence_length": "<e.g. short sentences, rarely more than 15 words>",
  "greeting_style": "<e.g. starts with 'Hi [Name],' or 'Hello,' or no greeting>",
  "signature": "<how they typically sign off, e.g. 'Best, [Name]'>",
  "avoid": ["<words or phrases they never use, e.g. 'synergy', 'leverage'>"],
  "patterns": ["<recurring patterns, e.g. 'asks one question at the end'>", "<pattern 2>"],
  "sample_opener": "<a sample first sentence in their style>",
  "sample_cta": "<a sample call-to-action in their style>",
  "summary": "<2 sentence summary of their writing voice>"
}}

Return ONLY valid JSON."""

    try:
        import ai_pool, assistant
        result = ai_pool.complete(prompt, assistant.cfg().get("pool"), max_tokens=600)
        text = result.get("text", "").strip()
        text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.M)
        text = re.sub(r"\s*```\s*$", "", text, flags=re.M)
        m = re.search(r"\{[\s\S]+\}", text)
        if m:
            profile = json.loads(m.group(0))
            data["profile"] = profile
            data["learned_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _save(data)
            # Update knowledge base style.md
            _update_style_md(profile)
            return {"ok": True, "profile": profile, "examples_used": min(20, len(examples))}
        return {"error": "AI did not return valid JSON"}
    except Exception as ex:
        return {"error": str(ex)}


def _update_style_md(profile: dict):
    """Write the learned style profile to .leadfinder/knowledge/style.md"""
    try:
        import knowledge
        kb_dir = knowledge.KNOWLEDGE_DIR
        os.makedirs(kb_dir, exist_ok=True)
        style_path = os.path.join(kb_dir, "style.md")
        content = f"""# My Writing Style (AI-Learned)
*Last updated: {time.strftime("%Y-%m-%d")}*

## Tone
{profile.get('tone', '')}

## Sentence style
{profile.get('sentence_length', '')}

## Greeting style
{profile.get('greeting_style', '')}

## Sign-off
{profile.get('signature', '')}

## Words/phrases to AVOID
{chr(10).join('- ' + w for w in profile.get('avoid', []))}

## Patterns to follow
{chr(10).join('- ' + p for p in profile.get('patterns', []))}

## Sample opener (write like this)
"{profile.get('sample_opener', '')}"

## Sample CTA (write like this)
"{profile.get('sample_cta', '')}"

## Summary
{profile.get('summary', '')}
"""
        with open(style_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception:
        pass


# ── Build style prompt injection ──────────────────────────────────────────────

def get_style_instructions() -> str:
    """
    Return a style injection string for AI prompts.
    Called by ai_pool.py when knowledge base is loaded.
    """
    data = _load()
    p = data.get("profile", {})
    if not p.get("tone"):
        return ""

    parts = [f"Writing style: {p.get('tone', '')}"]
    if p.get("sentence_length"):
        parts.append(f"Sentence length: {p['sentence_length']}")
    if p.get("greeting_style"):
        parts.append(f"Greeting: {p['greeting_style']}")
    if p.get("signature"):
        parts.append(f"Sign-off: {p['signature']}")
    if p.get("avoid"):
        parts.append(f"Never use: {', '.join(p['avoid'][:5])}")
    if p.get("sample_opener"):
        parts.append(f'Example opener: "{p["sample_opener"]}"')
    return " | ".join(parts)


# ── API handler ───────────────────────────────────────────────────────────────

def handle(path: str, req: dict) -> dict:

    if path == "/api/style/add":
        return add_example(req.get("text", ""), req.get("label", "email"))

    if path == "/api/style/remove":
        return remove_example(int(req.get("index", 0)))

    if path == "/api/style/clear":
        return clear_examples()

    if path == "/api/style/import":
        return import_from_chat_export(
            req.get("text", ""),
            req.get("your_name", ""),
        )

    if path == "/api/style/learn":
        return learn_style()

    if path == "/api/style/list":
        data = _load()
        return {
            "examples": data.get("examples", []),
            "profile":  data.get("profile", {}),
            "learned_at": data.get("learned_at", ""),
            "count": len(data.get("examples", [])),
        }

    if path == "/api/style/profile":
        return {"profile": _load().get("profile", {}), "instructions": get_style_instructions()}

    return {"error": f"Unknown style path: {path}"}
