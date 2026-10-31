"""
Free AI pool: uses several free-tier AI providers and switches automatically
when one hits its per-minute or daily limit. Standard library only.
"""
import json, re, time, threading, urllib.request
import leadfinder as LF

PROVIDERS = {
    "gemini":     {"label": "Google Gemini (AI Studio)", "base": "https://generativelanguage.googleapis.com/v1beta/openai",
                   "model": "gemini-2.5-flash", "signup": "https://aistudio.google.com/apikey", "free": True},
    "groq":       {"label": "Groq", "base": "https://api.groq.com/openai/v1",
                   "model": "llama-3.3-70b-versatile", "signup": "https://console.groq.com/keys", "free": True},
    "openrouter": {"label": "OpenRouter (:free models)", "base": "https://openrouter.ai/api/v1",
                   "model": "", "signup": "https://openrouter.ai/keys", "free": True},
    "mistral":    {"label": "Mistral (Experiment plan)", "base": "https://api.mistral.ai/v1",
                   "model": "mistral-small-latest", "signup": "https://console.mistral.ai/api-keys", "free": True},
    "github":     {"label": "GitHub Models", "base": "https://models.github.ai/inference",
                   "model": "openai/gpt-4.1-mini", "signup": "https://github.com/settings/tokens", "free": True},
    "nvidia":     {"label": "NVIDIA NIM", "base": "https://integrate.api.nvidia.com/v1",
                   "model": "meta/llama-3.3-70b-instruct", "signup": "https://build.nvidia.com", "free": True},
    "cerebras":   {"label": "Cerebras", "base": "https://api.cerebras.ai/v1",
                   "model": "", "signup": "https://cloud.cerebras.ai", "free": True},
    "ollama":     {"label": "Ollama (on this computer)", "base": "http://localhost:11434",
                   "model": "llama3.2", "signup": "https://ollama.com", "free": True, "nokey": True},
    "anthropic":  {"label": "Anthropic Claude API (paid)", "base": "https://api.anthropic.com/v1",
                   "model": "claude-haiku-4-5-20251001", "signup": "https://console.anthropic.com", "free": False},
    "custom":     {"label": "Custom OpenAI-compatible", "base": "", "model": "", "signup": "", "free": None},
}

SYSTEM = ("You are a practical sales assistant for a freelance web designer who finds local business clients. "
          "Write short, natural, specific text. Never invent facts, numbers or statistics that are not in the data given.")

_lock = threading.Lock()
_cool = {}      # provider -> (until_ts, reason)
_used = {}      # (provider, date) -> count

def _code(msg):
    m = re.search(r"HTTP (\d{3})", str(msg))
    return int(m.group(1)) if m else 0

def _classify(err):
    s, c = str(err).lower(), _code(err)
    if c == 429 or "rate limit" in s or "resource_exhausted" in s or "quota" in s or "too many" in s:
        daily = any(k in s for k in ("per day", "daily", "perday", "rpd", "tokens per day", "free-models-per-day", "quota exceeded"))
        return (3 * 3600 if daily else 65), ("daily limit reached" if daily else "rate limited")
    if c in (401, 403):
        return 1800, "key rejected (check the key)"
    if c == 404 or "model" in s and ("not found" in s or "does not exist" in s):
        return 1800, "model not found (use List models)"
    return 120, "temporarily unavailable"

def _call(pid, cfg, prompt, system, max_tokens):
    p = PROVIDERS.get(pid, PROVIDERS["custom"])
    base = (cfg.get("base") or p["base"]).rstrip("/")
    model = cfg.get("model") or p["model"]
    key = cfg.get("key", "")
    if not model:
        raise RuntimeError("HTTP 404 model not set: choose one with List models")
    if pid == "ollama":
        r = LF.http_json(base + "/api/chat", {"model": model, "stream": False, "messages": [
            {"role": "system", "content": system}, {"role": "user", "content": prompt}]}, timeout=300)
        return (r.get("message") or {}).get("content", "").strip(), model
    if pid == "anthropic":
        r = LF.http_json(base + "/messages", {"model": model, "max_tokens": max_tokens, "system": system,
                         "messages": [{"role": "user", "content": prompt}]},
                         {"x-api-key": key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"}, timeout=180)
        return "".join(b.get("text", "") for b in r.get("content", [])).strip(), model
    h = {"Content-Type": "application/json"}
    if key: h["Authorization"] = "Bearer " + key
    if pid == "openrouter":
        h["HTTP-Referer"] = "http://localhost"; h["X-Title"] = "LeadFinder"
    r = LF.http_json(base + "/chat/completions", {"model": model, "temperature": 0.7, "max_tokens": max_tokens,
                     "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}, h, timeout=180)
    if r.get("error"):
        raise RuntimeError(f"HTTP {r['error'].get('code', 500)} {r['error'].get('message', '')}")
    return (r["choices"][0]["message"].get("content") or "").strip(), model

def complete(prompt, pool, system=SYSTEM, max_tokens=900):
    """pool: ordered list of {provider, key, model, base, enabled}"""
    active = [x for x in (pool or []) if x.get("enabled", True) and (x.get("key") or PROVIDERS.get(x.get("provider"), {}).get("nokey"))]
    if not active:
        raise RuntimeError("No AI provider set up. Add at least one free key in Settings > Free AI pool.")
    errors, now = [], time.time()
    for cfg in active:
        pid = cfg["provider"]
        slot = pid + ":" + (cfg.get("model") or "")
        until, why = _cool.get(slot, (0, ""))
        if until > now:
            errors.append(f"{PROVIDERS.get(pid, {}).get('label', pid)}: {why}, retry in {int(until - now)}s")
            continue
        try:
            text, model = _call(pid, cfg, prompt, system, max_tokens)
            if not text: raise RuntimeError("empty answer")
            with _lock:
                k = (pid, time.strftime("%Y-%m-%d"))
                _used[k] = _used.get(k, 0) + 1
            return {"text": text, "provider": PROVIDERS.get(pid, {}).get("label", pid), "model": model}
        except Exception as ex:
            secs, why = _classify(ex)
            _cool[slot] = (time.time() + secs, why)
            errors.append(f"{PROVIDERS.get(pid, {}).get('label', pid)}: {why} ({str(ex)[:120]})")
    raise RuntimeError("All AI providers failed right now. " + " | ".join(errors))

def status(pool):
    now, today = time.time(), time.strftime("%Y-%m-%d")
    out = []
    for cfg in pool or []:
        pid = cfg.get("provider")
        until, why = _cool.get(pid + ":" + (cfg.get("model") or ""), (0, ""))
        out.append({"provider": pid, "usedToday": _used.get((pid, today), 0),
                    "coolingFor": max(0, int(until - now)), "reason": why if until > now else ""})
    return out

def test(cfg):
    _cool.pop(cfg.get("provider", "") + ":" + (cfg.get("model") or ""), None)
    t0 = time.time()
    text, model = _call(cfg["provider"], cfg, "Reply with exactly: OK", "You are a test.", 10)
    return {"ok": True, "model": model, "reply": text[:40], "seconds": round(time.time() - t0, 1)}

def list_models(cfg):
    pid = cfg.get("provider")
    p = PROVIDERS.get(pid, PROVIDERS["custom"])
    base = (cfg.get("base") or p["base"]).rstrip("/")
    key = cfg.get("key", "")
    if pid == "ollama":
        r = LF.http_json(base + "/api/tags", timeout=20)
        return [m["name"] for m in r.get("models", [])]
    if pid == "anthropic":
        r = LF.http_json(base + "/models", headers={"x-api-key": key, "anthropic-version": "2023-06-01"}, timeout=30)
        return [m["id"] for m in r.get("data", [])]
    if pid == "github":
        r = LF.http_json("https://models.github.ai/catalog/models", headers={"Authorization": "Bearer " + key}, timeout=30)
        return [m.get("id") for m in (r if isinstance(r, list) else r.get("data", [])) if m.get("id")]
    r = LF.http_json(base + "/models", headers={"Authorization": "Bearer " + key} if key else None, timeout=30)
    ids = [m.get("id", "").replace("models/", "") for m in r.get("data", r.get("models", []))]
    if pid == "openrouter":
        ids = [i for i in ids if i.endswith(":free")] + ["openrouter/free"]
    return sorted(i for i in ids if i)
