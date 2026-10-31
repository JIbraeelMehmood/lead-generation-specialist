"""
Dashboard analytics & reporting for LeadFinder.

Aggregates data from all modules to produce:
  * Pipeline funnel (New → Contacted → Interested → Proposal → Won)
  * Daily/weekly activity metrics (calls, emails, new leads)
  * Source performance (which discovery source yields the best leads)
  * Email campaign stats (open, sent, failed rates)
  * Top opportunities (hot leads by score)
  * Streak and conversion rate calculations
  * AI-powered weekly summary

Standard library only.
"""
import json, os, re, time
DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def _load(name, default=None):
    import assistant
    return assistant.load(name, default if default is not None else {})


# ---------------------------------------------------------------- pipeline funnel
def pipeline_funnel(leads):
    """
    Compute funnel counts from leads list (passed from the frontend's My list).
    """
    stages = ["New", "Contacted", "No answer", "Interested",
              "Follow up", "Proposal sent", "Won", "Not interested"]
    counts = {s: 0 for s in stages}
    for l in leads:
        s = l.get("stage") or "New"
        counts[s] = counts.get(s, 0) + 1
    total = sum(counts.values())
    won = counts.get("Won", 0)
    contacted = sum(counts.get(s, 0) for s in
                    ["Contacted", "No answer", "Interested", "Follow up", "Proposal sent", "Won"])
    conv_rate = round(100 * won / contacted, 1) if contacted else 0
    return {
        "stages": [{"stage": s, "count": counts[s]} for s in stages],
        "total": total,
        "won": won,
        "contacted": contacted,
        "conversionRate": conv_rate,
    }


# ---------------------------------------------------------------- activity metrics
def activity_metrics(days=30):
    """Read the activity log stored by assistant.js (lf-log — browser localStorage).
    Since Python can't read localStorage, we expose an endpoint so the JS
    posts the log and we cache it server-side."""
    log = _load("activity_log", {})
    today = time.strftime("%Y-%m-%d")
    result = {}
    for i in range(days):
        t = time.localtime(time.time() - i * 86400)
        d = time.strftime("%Y-%m-%d", t)
        result[d] = log.get(d, {"calls": 0, "emails": 0, "newLeads": 0})
    return result


def save_activity(day_data):
    """Called by the frontend to sync its localStorage log server-side."""
    import assistant
    log = _load("activity_log", {})
    log.update(day_data)
    # keep last 365 days only
    cutoff = time.strftime("%Y-%m-%d", time.localtime(time.time() - 365 * 86400))
    log = {k: v for k, v in log.items() if k >= cutoff}
    assistant.save("activity_log", log)
    return log


# ---------------------------------------------------------------- source performance
def source_performance(leads):
    """Which discovery source (Google, SerpApi, OSM, WebCrawler, CSE) produced the
    most actionable leads (Won + Interested + Proposal)."""
    by_source = {}
    valuable = {"Won", "Interested", "Proposal sent", "Follow up"}
    for l in leads:
        src = l.get("source") or "Unknown"
        # normalise source label
        if src.startswith("Google (SerpApi)"):
            src = "SerpApi"
        elif src.startswith("Google"):
            src = "Google Maps"
        elif src == "OpenStreetMap":
            src = "OpenStreetMap"
        elif "CSE" in src or "Dork" in src:
            src = "Google Dorking (CSE)"
        elif "WebCrawler" in src:
            src = "WebCrawler"
        elif "LeadMapAI" in src or "OutLead" in src:
            src = "Browser Scraper"
        s = by_source.setdefault(src, {"source": src, "total": 0, "valuable": 0,
                                       "won": 0, "hasEmail": 0, "hasPhone": 0})
        s["total"] += 1
        if l.get("stage") in valuable:
            s["valuable"] += 1
        if l.get("stage") == "Won":
            s["won"] += 1
        if l.get("email"):
            s["hasEmail"] += 1
        if l.get("phone"):
            s["hasPhone"] += 1
    out = sorted(by_source.values(), key=lambda x: -x["total"])
    for s in out:
        s["convRate"] = round(100 * s["won"] / s["total"], 1) if s["total"] else 0
    return out


# ---------------------------------------------------------------- email stats
def email_stats(outbox_items):
    """Accept the outbox list from the frontend and compute stats."""
    counts = {"draft": 0, "approved": 0, "sent": 0, "failed": 0, "rejected": 0}
    by_group = {}
    today = time.strftime("%Y-%m-%d")
    sent_today = 0
    for o in outbox_items:
        status = o.get("status", "draft")
        counts[status] = counts.get(status, 0) + 1
        group = o.get("group", "General")
        g = by_group.setdefault(group, {"group": group, "sent": 0, "draft": 0})
        if status == "sent":
            g["sent"] += 1
            if (o.get("sentAt") or "").startswith(today):
                sent_today += 1
        elif status == "draft":
            g["draft"] += 1
    total_sent = counts.get("sent", 0)
    fail_rate = round(100 * counts.get("failed", 0) / max(1, total_sent + counts.get("failed", 0)), 1)
    return {
        "counts": counts,
        "byGroup": sorted(by_group.values(), key=lambda x: -x["sent"]),
        "sentToday": sent_today,
        "failRate": fail_rate,
    }


# ---------------------------------------------------------------- top opportunities
def top_opportunities(leads, n=10):
    """Return the top N leads by computed score that haven't been won yet."""
    def score(l):
        s = 0
        if not l.get("website"):
            s += 50
        elif any(x in l.get("website", "").lower()
                 for x in ("facebook", "instagram", "linktr", "business.site")):
            s += 40
        rev = l.get("reviews") or 0
        s += 20 if rev >= 100 else 15 if rev >= 30 else 8 if rev >= 10 else 0
        if (l.get("rating") or 0) >= 4.5:
            s += 10
        elif (l.get("rating") or 0) >= 4:
            s += 5
        if l.get("phone"):
            s += 10
        if l.get("email"):
            s += 10
        return min(100, s)

    excluded = {"Won", "Not interested"}
    candidates = [l for l in leads if l.get("stage") not in excluded]
    ranked = sorted(candidates, key=score, reverse=True)
    return [{"id": l.get("id"), "name": l.get("name"), "category": l.get("category"),
             "address": l.get("address"), "phone": l.get("phone"), "email": l.get("email"),
             "website": l.get("website"), "stage": l.get("stage"),
             "reviews": l.get("reviews"), "rating": l.get("rating"),
             "score": score(l), "priority": l.get("priority")}
            for l in ranked[:n]]


# ---------------------------------------------------------------- streak
def streak_days(activity_log):
    """Calculate outreach streak (consecutive days with calls or emails)."""
    s = 0
    for i in range(365):
        t = time.localtime(time.time() - i * 86400)
        d = time.strftime("%Y-%m-%d", t)
        day = activity_log.get(d, {})
        if (day.get("calls", 0) + day.get("emails", 0)) > 0:
            s += 1
        elif i > 0:
            break
    return s


# ---------------------------------------------------------------- AI weekly summary
def ai_weekly_summary(leads, activity_log, pool):
    """Generate an AI-powered weekly performance summary."""
    import ai_pool
    today = time.strftime("%Y-%m-%d")
    week_acts = {}
    for i in range(7):
        t = time.localtime(time.time() - i * 86400)
        d = time.strftime("%Y-%m-%d", t)
        week_acts[d] = activity_log.get(d, {})

    total_calls = sum(v.get("calls", 0) for v in week_acts.values())
    total_emails = sum(v.get("emails", 0) for v in week_acts.values())
    pipeline = pipeline_funnel(leads)
    won_this_week = sum(1 for l in leads if l.get("stage") == "Won" and
                        (l.get("updatedAt") or "") >= time.strftime(
                            "%Y-%m-%d", time.localtime(time.time() - 7 * 86400)))

    prompt = (
        f"This is a weekly performance report for a freelance web designer doing cold outreach.\n\n"
        f"Week: {time.strftime('%Y-%m-%d', time.localtime(time.time() - 6 * 86400))} to {today}\n"
        f"Calls made: {total_calls}\n"
        f"Emails sent: {total_emails}\n"
        f"Pipeline: {pipeline['total']} total leads — "
        f"{pipeline['stages'][0]['count']} New, "
        f"{pipeline['stages'][3]['count']} Interested, "
        f"{pipeline['stages'][5]['count']} Proposal sent, "
        f"{pipeline['won']} Won\n"
        f"Conversion rate: {pipeline['conversionRate']}%\n"
        f"Wins this week: {won_this_week}\n\n"
        "Write a short (4–6 sentences), honest, practical weekly review. "
        "Mention what went well, what needs improvement, and one specific suggestion "
        "for next week. Be direct and encouraging."
    )
    result = ai_pool.complete(prompt, pool, max_tokens=300)
    return result.get("text", "")


# ---------------------------------------------------------------- full dashboard data
def full_dashboard(leads, outbox_items, activity_log_from_js=None):
    """Aggregate everything into one response object."""
    if activity_log_from_js:
        save_activity(activity_log_from_js)
    log = _load("activity_log", {})
    today = time.strftime("%Y-%m-%d")
    import assistant
    cfg = assistant.cfg()
    usage = assistant.usage()

    return {
        "funnel": pipeline_funnel(leads),
        "activityMetrics": {
            "today": log.get(today, {"calls": 0, "emails": 0, "newLeads": 0}),
            "last7Days": {
                d: log.get(time.strftime(
                    "%Y-%m-%d", time.localtime(time.time() - i * 86400)), {})
                for i, d in enumerate(
                    [time.strftime("%Y-%m-%d",
                                   time.localtime(time.time() - j * 86400))
                     for j in range(6, -1, -1)])
            },
            "streak": streak_days(log),
        },
        "sourcePerformance": source_performance(leads),
        "emailStats": email_stats(outbox_items),
        "topOpportunities": top_opportunities(leads),
        "usage": usage,
        "inboxCount": len(assistant.inbox()),
        "lastRun": cfg.get("lastRun"),
        "generatedAt": today,
    }


# ---------------------------------------------------------------- API
def handle(path, req):
    import assistant
    if path == "/api/dashboard":
        leads = req.get("leads", [])
        outbox = req.get("outbox", [])
        activity = req.get("activityLog")
        return full_dashboard(leads, outbox, activity)

    if path == "/api/dashboard/activity":
        if req.get("save"):
            return {"log": save_activity(req["save"])}
        return {"log": activity_metrics(int(req.get("days", 30)))}

    if path == "/api/dashboard/ai-summary":
        leads = req.get("leads", [])
        log = _load("activity_log", {})
        cfg = assistant.cfg()
        return {"summary": ai_weekly_summary(leads, log, cfg.get("pool", []))}

    raise RuntimeError("Unknown endpoint")
