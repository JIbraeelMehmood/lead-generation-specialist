# LeadFinder — Repository Integration Plan

**Goal:** make LeadFinder the hub of a lead-generation system that can build on, and be supported by, the collected reference repositories and the two blueprint docs — without becoming dependent on brittle browser-scraping apps.

The two blueprint docs (`lead_generator_integration_blueprint.docx`, `complete_lead_generation_platform_implementation_plan.docx`) agree on one thing: **treat public repos as reference implementations, not production dependencies. Prefer small adapters around stable APIs over merging entire applications.** This plan follows that rule.

---

## 1. What each repo contributes (analysis)

| Repo | What it does | Tech | Best idea to port into LeadFinder | How |
|---|---|---|---|---|
| **OutLead** | Full loop: scrape→enrich→verify→score→3-email sequence→send+IMAP reply stop | Playwright, SQLite, SMTP, IMAP | **Email verification** (syntax→MX→placeholder→live mailbox) and the **suppression / two-key send gate / auto-stop-on-reply** discipline | Port the verify logic to stdlib (MX via DNS-over-HTTPS + `smtplib`); suppression already in `pipeline.py` |
| **intent-engine** | Niche+location scrape → LLM decision-maker extraction → Hunter/Apollo fallback → AI email sequences | FastAPI/Next.js/Celery/Playwright | **Decision-maker + intent-signal extraction** from about/team pages; **AI 3-step sequence** | Port the LLM extraction (LeadFinder already fetches pages); reuse LeadFinder's AI pool. The Playwright scrape is replaced by Places/SerpApi (already in LeadFinder) |
| **LeadMapAI** | Playwright+Streamlit Google Maps scraper, modular scraper/exporter/models | Playwright, Streamlit | Clean **modular scraper/exporter structure** + Excel/JSON export | Reference for structure; LeadFinder already has Maps discovery + CSV/Excel-style export |
| **LeadGenPy** | Selenium Google Maps scrape + ChatGPT emails + Google Sheets | Selenium, openai, gspread | **Google Sheets export** as a CRM workbook | Reference; implement Sheets via OAuth REST (stdlib) later |
| **google-maps-leads-scraper-python** | Drives an Apify actor; geo-drilling to beat the 120-cap; website email/social extraction | Apify client | **Geo-drilling** idea (LeadFinder's `deep` grid already does this) + **website email/social extraction** | LeadFinder's `google_search(deep=2/3)` already grids; enhance `find_emails`/enrich with socials (already partial) |
| **DOrky** | CLI Google dorking via Custom Search API + screenshots | google-api-python-client, selenium | **Google Programmable/Custom Search as a discovery source** (REST, stdlib) | New `dorking` discovery source using Google CSE JSON API (no pip) |
| **Google-Dorking-Automation** | Configurable dork templates with `{domain}`/`{company}` vars, multi-key rotation | Python | **Query-template engine** (templates with variables, key rotation) | Fold into the dorking source |
| **WebCrawler-and-Email-Automation-System** | Google CSE → scrape → email regex → CSV → Gmail SMTP | requests, bs4, pandas | **CSE-driven website discovery + Gmail SMTP outreach** | Reference; CSE folds into dorking; SMTP outreach LeadFinder already has via `nichefinder.send_email` |
| **proficiently-claude-skills** | Career pipeline (profile, fit-score, tailor resume, cover letter, apply) | Markdown skills | Already **merged** this session into LeadFinder's Career tab (`career.py`/`career.js`) | Done |

**Common overlap:** 5 of 8 repos are Google Maps scrapers (Playwright/Selenium/Apify). They exist to beat Google's result cap and to harvest emails from each business's website — *because the Places API returns no emails*. LeadFinder already has Places/SerpApi/OSM discovery with a `deep` grid to beat the cap; the real gap it shares with these repos is **website email/social extraction + email verification**.

---

## 2. Architecture: LeadFinder as the hub

```
                       ┌──────────────────────── LeadFinder (this repo) ─────────────────────────┐
 DISCOVERY             │ Places API · SerpApi Maps · OpenStreetMap · NEW Google CSE "dorking"    │
 (adapters, stdlib)    │ (each returns a common Lead record; source URL + timestamp kept)        │
                       └─────────────────────────────────┬──────────────────────────────────────┘
                                                          ▼
 NORMALIZE/DEDUP        canonical_domain + suppression  (pipeline.py)   ← blueprint §5/§11
                                                          ▼
 ENRICH                 find_emails + contacts.enrich + NEW emailverify  ← OutLead-style, stdlib
                        (official-site / directory / unverified provenance)  ← blueprint §7
                                                          ▼
 AUDIT + OPPORTUNITIES  audit_site + presence + opportunities.py          ← blueprint §8
                        (categorized, evidence-backed, confidence, fix, service-fit)
                                                          ▼
 SCORE                  5-component 0–100 + bands  (opportunities.py)      ← blueprint §9
                                                          ▼
 OUTREACH               AI pool writer + nichefinder.send_email (SMTP)     ← blueprint §10
                        + suppression gate (no repeat, honor opt-out)
                                                          ▼
 CRM / EXPORT           My list + suppression + CSV → (future) Google Docs/Sheets  ← blueprint §12
```

**Rule for the browser repos (OutLead, intent-engine, LeadMapAI, LeadGenPy, Apify):** they are *optional external adapters*, not merged. LeadFinder defines a stable `Lead` record and a discovery-adapter contract; a user who installs one of those scrapers can point its CSV/JSON output at LeadFinder's import, or LeadFinder can shell out to it. LeadFinder's own discovery already covers the same need via official APIs (the blueprint's recommended path: "prefer Places API over scraping the consumer UI").

---

## 3. What this session already merged (the blueprint core, server-side, stdlib)

- `opportunities.py` — evidence-backed opportunities (category, evidence_url, excerpt/measured_value, impact, suggested_fix, service_fit, confidence, verification_status) + **5-component scoring** (opportunity 30 / fit 20 / commercial 20 / contactability 15 / confidence 15) + bands + provenance + recommended package. → blueprint §8/§9. Endpoint `/api/opportunities`.
- `pipeline.py` — suppression/do-not-contact list, canonical-domain dedup, blueprint config. → blueprint §5/§11. Endpoints `/api/suppression`, `/api/dedup/*`, `/api/bp-config`.
- `career.py` — Proficiently career pipeline (profile, fit, tailor resume, cover letter, application tracking). → proficiently repo.
- `jobsearch.py` — BeBee/Google/JobLeads job-lead search.

## 4. Next portable integrations (this turn + roadmap)

**This turn (fully stdlib, no pip):**
- `emailverify.py` — OutLead-style verification: syntax → disposable/placeholder filter → **MX lookup via DNS-over-HTTPS (dns.google)** → **SMTP mailbox check (`smtplib`)** → `verified | domain-only | invalid | unknown`. Replaces the basic check in `contacts.py`. → blueprint §7 ("verification state"); OutLead's standout feature, ported without Playwright.
- `dorking.py` — Google Custom/Programmable Search discovery source (REST via `http_json`), with query templates (`{domain}`, `{company}`, niche+city) and multi-key rotation. → blueprint §5; DOrky/Google-Dorking-Automation/WebCrawler, rebuilt around the stable API.

**Roadmap (need external setup, designed but not required to run):**
- **Google Docs/Sheets export** (blueprint §12) — OAuth + Docs/Sheets REST via stdlib; needs the user's Google Cloud OAuth client. (The `md2docs`/`gdoctableapppy` refs are optional.)
- **IMAP reply detection** (OutLead) — `imaplib` watches for replies → auto-stop a sequence / mark "Replied". Needs IMAP creds.
- **Decision-maker extraction** (intent-engine) — LLM over about/team pages; LeadFinder's `identity.find_owner` already does much of this.
- **PageSpeed performance audit** (blueprint §8) — optional Google PageSpeed API adapter.

## 5. How the systems support each other
- **LeadFinder** is the orchestrator + UI + scoring + CRM, stdlib-only, runs anywhere Python 3.8+ runs.
- The **browser-scraping repos** are interchangeable *discovery adapters* that feed LeadFinder's common `Lead` record (CSV/JSON import already exists in "My list"). They are not merged, so they can be swapped or dropped without touching LeadFinder.
- The **dorking repos** are folded into one stdlib adapter (`dorking.py`) around the Google CSE API.
- The **blueprint docs** are the spec; LeadFinder's modules map 1:1 to their service list (discovery/normalization/enrichment/website_audit/opportunity_engine/scoring/outreach/crm/exports).
