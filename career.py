"""
Career pipeline for LeadFinder, ported from the "Proficiently" Claude skills.

This merges the portable parts of the Proficiently job-search plugin into
LeadFinder's server-side model (no browser automation needed):

  * Profile & preferences   (from the `setup` skill) - resume, job matching
                              rules, work-history profile. Stored in data/.
  * Fit scoring              (from `fit-scoring.md`) - rate a job High/Medium/
                              Low/Skip against your preferences.
  * Tailor resume            (from `tailor-resume`)   - generate a tailored resume
                              for a specific posting (faithful LLM prompt).
  * Cover letter             (from `cover-letter`)    - generate a cover letter
                              (faithful LLM prompt + QC checklist).
  * Job applications         (the per-job `jobs/<slug>/` data model) - track each
                              application: posting, tailored resume, cover letter,
                              applied status.

Not ported (they need a live browser / external bot that a server app can't run):
  * apply    - filling Greenhouse/Lever/Workday forms (needs browser automation)
  * jobsearch-telegram - Telegram polling + browser orchestration
  * network-scan - scanning careers pages (needs a browser; resolve-careers is
    portable but the scan step is not)
All generation uses LeadFinder's free AI pool (configured in Settings > Free AI pool).
"""
import json, re, time, urllib.parse
import leadfinder as LF

_lock = None
def _L():
    global _lock
    if _lock is None:
        import threading
        _lock = threading.RLock()
    return _lock

EMPTY_PROFILE = {
    "resume": "",
    "preferences": {
        "targetRoles": [], "location": "", "salary": "",
        "mustHaves": [], "niceToHaves": [], "dealbreakers": [],
        "companiesInterest": [], "companiesAvoid": [],
    },
    "workHistory": "",
    "updatedAt": "",
}


# ---------------------------------------------------------------- store
def _load(name, default):
    import assistant
    return assistant.load(name, default)

def _save(name, obj):
    import assistant
    assistant.save(name, obj)

def get_profile():
    p = _load("career_profile", {})
    out = json.loads(json.dumps(EMPTY_PROFILE))
    if p.get("resume"): out["resume"] = p["resume"]
    if p.get("workHistory"): out["workHistory"] = p["workHistory"]
    if isinstance(p.get("preferences"), dict):
        for k in out["preferences"]:
            if isinstance(p["preferences"].get(k), list):
                out["preferences"][k] = p["preferences"][k]
            elif isinstance(p["preferences"].get(k), str):
                out["preferences"][k] = [x.strip() for x in p["preferences"][k].split(",") if x.strip()] \
                    if k != "location" and k != "salary" else p["preferences"][k]
    out["updatedAt"] = p.get("updatedAt", "")
    return out

def save_profile(obj):
    obj["updatedAt"] = time.strftime("%Y-%m-%d")
    _save("career_profile", obj)
    return get_profile()

def _jobs():
    return _load("career_jobs", [])

def _set_jobs(arr):
    _save("career_jobs", arr)

def _slug(s):
    s = re.sub(r"[^a-z0-9]+", "-", (s or "").lower()).strip("-")
    return s[:50] or "job"

def _new_id(job):
    base = _slug(job.get("company") or job.get("title") or "job")
    return f"{base}-{int(time.time())}"


# ---------------------------------------------------------------- AI
CAREER_SYSTEM = ("You are a world-class career strategist and resume writer. "
                 "You write sharp, natural, human prose - never corporate jargon, "
                 "never AI tells. You NEVER invent facts, metrics, titles, or scope "
                 "that are not explicitly in the candidate's materials.")

def _ai(prompt, system=CAREER_SYSTEM, max_tokens=2200):
    import assistant, ai_pool
    return ai_pool.complete(prompt, assistant.cfg().get("pool"), system=system, max_tokens=max_tokens)

def _strip(text):
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    return text.strip()

def _prefs_block(prefs):
    p = prefs or {}
    def lst(k): return ", ".join(p.get(k, [])) or "(none given)"
    return f"""TARGET ROLES: {lst('targetRoles')}
LOCATION: {p.get('location') or '(any)'}
SALARY MINIMUM: {p.get('salary') or '(none)'}
MUST-HAVES: {lst('mustHaves')}
NICE-TO-HAVES: {lst('niceToHaves')}
DEALBREAKERS: {lst('dealbreakers')}
COMPANIES OF INTEREST: {lst('companiesInterest')}
COMPANIES TO AVOID: {lst('companiesAvoid')}"""


# ---------------------------------------------------------------- fit scoring (fit-scoring.md)
def fit_score(job):
    """Rate one job against the profile's preferences. Returns {fit, reasons}."""
    prof = get_profile()
    if not prof["preferences"]["targetRoles"] and not prof["preferences"]["mustHaves"] \
       and not prof["preferences"]["dealbreakers"]:
        raise RuntimeError("Set up your job preferences in the Career tab first "
                           "(target roles, must-haves, dealbreakers).")
    posting = " ".join(x for x in (job.get("title"), job.get("company"),
                                   job.get("location"), job.get("snippet"),
                                   job.get("posting"), job.get("jobType")) if x)
    prompt = f"""You are evaluating job-candidate fit. Score this job against the candidate's preferences using this process:

1. DEALBREAKERS: if ANY dealbreaker is present, the rating is "Skip".
2. MUST-HAVES: count how many must-have criteria are met (all met -> strong; most -> medium; few -> weak).
3. NICE-TO-HAVES: count nice-to-haves met.
4. RATING:
   - High   = no dealbreakers + all must-haves + 2+ nice-to-haves
   - Medium = no dealbreakers + most must-haves (or all must-haves but few nice-to-haves)
   - Low    = no dealbreakers but significant gaps in must-haves
   - Skip   = any dealbreaker present

CANDIDATE PREFERENCES:
{_prefs_block(prof['preferences'])}

JOB:
{posting[:3000]}

Reply with ONLY a JSON object, nothing else:
{{"fit": "High|Medium|Low|Skip", "reasons": "one or two short sentences", "dealbreakers": ["any matched dealbreakers"], "matchedMustHaves": ["which must-haves are met"]}}"""
    r = _ai(prompt, system="You are a precise job-fit evaluator. Output only valid JSON.", max_tokens=400)
    txt = _strip(r["text"])
    try:
        m = re.search(r"\{.*\}", txt, re.S)
        d = json.loads(m.group(0) if m else txt)
    except Exception:
        d = {"fit": "Low", "reasons": "Could not parse evaluation: " + txt[:200]}
    d.setdefault("fit", "Low")
    if d["fit"] not in ("High", "Medium", "Low", "Skip"):
        d["fit"] = "Low"
    return d


# ---------------------------------------------------------------- job applications
def _find(jobs, jid):
    for j in jobs:
        if j["id"] == jid:
            return j
    return None

def save_job(job):
    """Create or update a job-application record from a search result."""
    with _L():
        jobs = _jobs()
        jid = job.get("id")
        rec = _find(jobs, jid) if jid else None
        if rec is None:
            jid = jid or _new_id(job)
            rec = {"id": jid, "company": "", "title": "", "url": "", "location": "",
                   "jobType": "", "source": "", "query": "", "savedAt": time.strftime("%Y-%m-%d"),
                   "status": "saved", "appliedAt": "", "notes": "",
                   "posting": "", "resume": "", "coverLetter": ""}
            jobs.append(rec)
        for k in ("company", "title", "url", "location", "jobType", "source", "query", "posting"):
            if job.get(k):
                rec[k] = job[k]
        _set_jobs(jobs)
        return {"id": rec["id"]}

def list_jobs():
    return {"jobs": [{k: j.get(k, "") for k in
        ("id", "company", "title", "url", "location", "jobType", "source",
         "savedAt", "status", "appliedAt", "notes")}
        for j in _jobs()]}

def get_job(jid):
    j = _find(_jobs(), jid)
    if not j:
        raise RuntimeError("Job application not found.")
    return j

def set_job_text(jid, field, text):
    if field not in ("resume", "coverLetter", "posting", "notes"):
        raise RuntimeError("Cannot edit that field.")
    with _L():
        jobs = _jobs()
        j = _find(jobs, jid)
        if not j:
            raise RuntimeError("Job application not found.")
        j[field] = text
        _set_jobs(jobs)
        return {"ok": True}

def set_job_status(jid, status, notes=None):
    if status not in ("saved", "applied", "interview", "rejected", "offer"):
        raise RuntimeError("Unknown status.")
    with _L():
        jobs = _jobs()
        j = _find(jobs, jid)
        if not j:
            raise RuntimeError("Job application not found.")
        j["status"] = status
        if status == "applied" and not j.get("appliedAt"):
            j["appliedAt"] = time.strftime("%Y-%m-%d")
        if notes is not None:
            j["notes"] = notes
        _set_jobs(jobs)
        return {"ok": True}

def delete_job(jid):
    with _L():
        _set_jobs([j for j in _jobs() if j["id"] != jid])
        return {"ok": True}


# ---------------------------------------------------------------- posting fetch
def _text(html):
    h = re.sub(r"(?i)<(script|style|noscript)[\s\S]*?</\1>", " ", html or "")
    h = re.sub(r"(?i)<br\s*/?>|</p>|</li>|</h[1-6]>", "\n", h)
    import html as H
    t = H.unescape(re.sub(r"<[^>]+>", " ", h))
    t = re.sub(r"[ \t\r\f\v]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t).strip()
    return t

def fetch_posting(url):
    url = LF.norm_url(url)
    if not url:
        return ""
    try:
        html, _final, _ = LF.fetch_text(url, timeout=25)
        t = _text(html)
        return t[:8000]
    except Exception as ex:
        raise RuntimeError(f"Couldn't read that job page ({str(ex)[:120]}). Paste the job description instead.")


# ---------------------------------------------------------------- tailor resume (tailor-resume.md)
def tailor_resume(payload):
    prof = get_profile()
    if not prof["resume"]:
        raise RuntimeError("Add your resume in the Career tab first.")
    with _L():
        jobs = _jobs()
        jid = payload.get("jobId")
        job = _find(jobs, jid) if jid else None
        # resolve posting
        if job is None:
            job = payload.get("job") or {}
            jid = job.get("id")
            job = _find(jobs, jid) if jid else None
        if job is None:
            job = {"id": _new_id(payload.get("job") or {}),
                   "company": (payload.get("job") or {}).get("company", ""),
                   "title": (payload.get("job") or {}).get("title", ""),
                   "url": (payload.get("job") or {}).get("url", ""),
                   "location": (payload.get("job") or {}).get("location", ""),
                   "jobType": (payload.get("job") or {}).get("jobType", ""),
                   "source": (payload.get("job") or {}).get("source", ""),
                   "query": (payload.get("job") or {}).get("query", ""),
                   "savedAt": time.strftime("%Y-%m-%d"), "status": "saved", "appliedAt": "",
                   "notes": "", "posting": "", "resume": "", "coverLetter": ""}
            jobs.append(job)
        posting = job.get("posting") or ""
        if not posting and payload.get("posting"):
            posting = payload["posting"]; job["posting"] = posting
        if not posting and payload.get("jobUrl"):
            posting = fetch_posting(payload["jobUrl"]); job["posting"] = posting; job["url"] = payload["jobUrl"]
        if not posting:
            posting = " ".join(x for x in (job.get("title"), job.get("company"),
                                           job.get("location"), (payload.get("job") or {}).get("snippet", "")) if x)
        _set_jobs(jobs)
    prompt = f"""Create a tailored resume that makes this candidate the obvious choice for the target role.

PHILOSOPHY: Reorganize and reframe their REAL experience so a hiring manager sees the fit in ~7 seconds. Do NOT invent experience. Only use information explicitly in the resume or profile.

CANDIDATE RESUME:
\"\"\"
{prof['resume']}
\"\"\"

WORK HISTORY PROFILE:
\"\"\"
{prof['workHistory'] or '(no detailed profile - base the resume only on the resume text, and stay conservative about scope)'}
\"\"\"

TARGET JOB POSTING:
\"\"\"
{posting[:5000]}
\"\"\"

REQUIREMENTS for the tailored resume:
- Summary: 2-3 SHORT sentences (each under 20 words) referencing the specific role/industry, leading with the most relevant credential, with 2-3 keywords from the posting.
- Experience: keep all roles from the original resume; rewrite/reorder bullets so the most relevant to THIS job are first. Bullet formula: [Action verb] + [what] + [scale] + [measurable result]. Current role 5-7 bullets, previous 3-5, older 2-3.
- Skills: reorder to lead with what the job asks for.
- Mirror the job posting's language where authentic.
- Level calibration: executive roles -> strategy/P&L/board; director -> program ownership/team/ops; IC -> hands-on depth/impact.
- Keep job titles and dates unchanged. Don't remove roles. Fit within 2 pages.

STRICT ACCURACY (non-negotiable): Only use info explicitly in the resume or profile. Never assume business model, revenue type, or company stage. Never inflate scope. Never add responsibilities/skills/partnerships the candidate didn't mention. When ambiguous, understate or omit.

STYLE (target high readability): No em dashes - use commas, periods, colons, semicolons, parentheses. Vary sentence structure. No filler ("demonstrating ability to", "leveraging", "spanning", "utilizing"). One idea per sentence. No stacked buzzwords. No preamble clauses.

Output ONLY the tailored resume in clean markdown, following the candidate's original structure. Do not add commentary."""
    r = _ai(prompt, max_tokens=2600)
    resume = _strip(r["text"])
    with _L():
        jobs = _jobs(); j = _find(jobs, job["id"])
        if j: j["resume"] = resume; _set_jobs(jobs)
    return {"resume": resume, "jobId": job["id"], "provider": r.get("provider")}


# ---------------------------------------------------------------- cover letter (write-cover-letter.md)
def write_cover_letter(jid):
    prof = get_profile()
    if not prof["resume"]:
        raise RuntimeError("Add your resume in the Career tab first.")
    job = get_job(jid)
    posting = job.get("posting") or " ".join(x for x in (job.get("title"), job.get("company"), job.get("location")) if x)
    resume = job.get("resume") or prof["resume"]
    prompt = f"""Write a natural, persuasive cover letter that sounds like authentic human writing, not AI. It must NOT lie - only use information directly supported by the resume/profile.

CANDIDATE RESUME:
\"\"\"
{resume}
\"\"\"

WORK HISTORY PROFILE:
\"\"\"
{prof['workHistory'] or '(none)'}
\"\"\"

JOB POSTING:
\"\"\"
{posting[:5000]}
\"\"\"

RULES:
- Start with "Dear Hiring Manager," and end with "Regards, [Candidate Name]". No other headers/footers.
- Opening (1-2 sentences): a direct, natural statement connecting your specific experience to their specific need.
- Evidence (2 paragraphs): 2-3 concrete achievements with measurable results that address what the employer needs most.
- Closing (2-3 sentences): a clear statement of mutual benefit, like the end of a real conversation.
- Total length 250-350 words. Vary paragraph lengths.
- Tone: confident but approachable, like explaining your value to a respected colleague over coffee. Natural first-person, varied sentence structure. Mix short and longer sentences.

CRITICAL PROHIBITIONS:
- No em dashes - use hyphens only.
- No corporate jargon. No "aligns perfectly/seamlessly", "living and breathing", "I am excited about the opportunity".
- No sentence longer than ~25 words without a natural break. No consecutive sentences starting the same way.
- Never extend a role's duration, never call a role "current" unless its end date is "Present", never inflate seniority/scope, never assume ambiguous details - omit instead.
- Company-attribution lock: a metric named with a company must actually exist under that company's role in the resume. Never merge metrics from different companies in one sentence.

QC before returning: read each sentence aloud for naturalness; replace any em dashes; break long sentences; verify every detail matches the resume exactly (titles, companies, employment status, timelines, scope).

Output ONLY the cover letter text."""
    r = _ai(prompt, system=CAREER_SYSTEM, max_tokens=1500)
    letter = _strip(r["text"])
    with _L():
        jobs = _jobs(); j = _find(jobs, jid)
        if j: j["coverLetter"] = letter; _set_jobs(jobs)
    return {"coverLetter": letter, "jobId": jid, "provider": r.get("provider")}


# ---------------------------------------------------------------- API
def handle(path, req):
    if path == "/api/career/profile":
        if req.get("save"):
            return {"profile": save_profile(req["save"])}
        return {"profile": get_profile()}
    if path == "/api/career/fit":
        return fit_score(req.get("job", {}))
    if path == "/api/career/tailor":
        return tailor_resume(req)
    if path == "/api/career/cover-letter":
        return write_cover_letter(req.get("jobId", ""))
    if path == "/api/career/job/save":
        return save_job(req.get("job", {}))
    if path == "/api/career/jobs":
        return list_jobs()
    if path == "/api/career/job":
        return {"job": get_job(req.get("id", ""))}
    if path == "/api/career/job/text":
        return set_job_text(req.get("id", ""), req.get("field", ""), req.get("text", ""))
    if path == "/api/career/job/status":
        return set_job_status(req.get("id", ""), req.get("status", "saved"), req.get("notes"))
    if path == "/api/career/delete":
        return delete_job(req.get("id", ""))
    if path == "/api/career/fetch-posting":
        return {"posting": fetch_posting(req.get("url", ""))}
    raise RuntimeError("Unknown endpoint")
