# LeadFinder — Complete System Documentation

**Version:** Updated 2 (leadfinder-updated-2)  
**Last updated:** October 2026  
**Stack:** Python 3.8+ · Standard library only · Single-page web app · No pip installs required

---

## Table of Contents

1. [What is LeadFinder?](#1-what-is-leadfinder)
2. [How to Run It](#2-how-to-run-it)
3. [Architecture Overview](#3-architecture-overview)
4. [All Features & Tabs](#4-all-features--tabs)
   - 4.1 Find Leads
   - 4.2 My List (CRM)
   - 4.3 Niche Finder
   - 4.4 Outreach (Email)
   - 4.5 Social Outreach
   - 4.6 How to Get Clients (Guide)
   - 4.7 Settings
   - 4.8 Opportunities
   - 4.9 Pipeline / Suppression
   - 4.10 Dorking
   - 4.11 AI Assistant (Autopilot)
   - 4.12 Identity
   - 4.13 Hiring Monitor
   - 4.14 Job Search
   - 4.15 Career Pipeline
   - 4.16 Dashboard
   - 4.17 Integrations
5. [Backend Modules (Python)](#5-backend-modules-python)
6. [Data Flow — How Requests Work](#6-data-flow--how-requests-work)
7. [External APIs & Services](#7-external-apis--services)
8. [Data Storage & Persistence](#8-data-storage--persistence)
9. [API Key Setup Guide](#9-api-key-setup-guide)
10. [Security Model](#10-security-model)
11. [File Structure](#11-file-structure)
12. [Limitations & Known Constraints](#12-limitations--known-constraints)

---

## 1. What is LeadFinder?

LeadFinder is a **local-first lead generation platform** for freelance web designers and digital agencies. It runs entirely on your own computer — no cloud subscription, no shared database, no SaaS fees. You open a terminal, run one command, and a full-featured web app opens in your browser.

**Core purpose:** Find local businesses that have no website, a weak website, or a poor digital presence, then research them, score them as prospects, compose and send outreach emails, track your pipeline, and analyze replies — all from one interface.

**Who it is for:**
- Freelance web designers looking for clients
- Digital agencies prospecting new local business accounts
- Anyone who cold-outreaches to local SMEs (plumbers, restaurants, salons, clinics, etc.)

**What makes it different:**
- Runs 100% offline on your machine — your API keys never leave your computer
- No pip installs: pure Python 3.8+ standard library
- Integrates 3 free lead data sources (Google Maps, SerpApi, OpenStreetMap)
- Full AI email writing with free-tier providers (Gemini, Groq, Ollama, and 6 more)
- Built-in CRM, autopilot, email verification, IMAP reply monitoring, and Google Sheets export

---

## 2. How to Run It

### Requirements

- Python 3.8 or newer
- Internet connection (for API calls)
- No additional packages needed

### Start the server

```bash
cd /path/to/leadfinder-updated-2
python3 leadfinder.py
```

The browser opens automatically to `http://localhost:8765`. To prevent the browser from opening:

```bash
python3 leadfinder.py --no-browser
```

To use a different port:

```bash
LEADFINDER_PORT=9000 python3 leadfinder.py
```

To pre-load your Google Places API key without entering it in the UI:

```bash
GOOGLE_PLACES_API_KEY="AIza..." python3 leadfinder.py
SERPAPI_KEY="your-serpapi-key" python3 leadfinder.py
```

### Stop the server

Press `Ctrl+C` in the terminal.

### First-time setup

1. Run the server
2. Open the **Settings** tab
3. Paste your API keys (Google Places, SerpApi, CSE, etc.)
4. Click **Save API keys**
5. Optionally configure the free AI pool (add a free Gemini or Groq key)
6. Go to **Find leads** and run your first search

The `data/` folder is created automatically on first run and stores all your configuration and lead data.

---

## 3. Architecture Overview

```
Browser (app.html + static/*.js)
        │
        │  HTTP (localhost:8765 only)
        │  POST JSON → response JSON
        ▼
leadfinder.py   ← ThreadingHTTPServer, 127.0.0.1:8765
  do_GET()      ← serves app.html, static JS files, health/status endpoints
  do_POST()     ← routes all API calls by path prefix
        │
        ├── /api/search           → google_search / serpapi_search / osm_search (built-in)
        ├── /api/analyze          → analyzer.py
        ├── /api/opportunities    → opportunities.py
        ├── /api/suppression      → pipeline.py
        ├── /api/bp-config        → pipeline.py
        ├── /api/dedup/*          → pipeline.py
        ├── /api/emailverify      → emailverify.py
        ├── /api/dorking          → dorking.py
        ├── /api/dashboard        → dashboard.py
        ├── /api/sheets           → sheets_export.py
        ├── /api/imap             → imap_monitor.py
        ├── /api/webcrawler       → webcrawler.py
        ├── /api/pagespeed        → pagespeed.py
        ├── /api/hiring           → hiring.py
        ├── /api/jobsearch        → jobsearch.py
        ├── /api/career           → career.py
        ├── /api/assistant        → assistant.py
        ├── /api/pool             → assistant.py → ai_pool.py
        ├── /api/contacts         → assistant.py → contacts.py
        ├── /api/identity         → identity.py
        ├── /api/owner            → identity.py
        ├── /api/sender-check     → identity.py
        ├── /api/cities           → nichefinder.py
        ├── /api/market-sample    → nichefinder.py
        ├── /api/send-email       → nichefinder.py (SMTP)
        ├── /api/emails           → find_emails() (built-in)
        ├── /api/audit            → audit_site() (built-in)
        └── /api/ai               → ai_pool.py

Persistent state: data/*.json
```

### Key design principles

**Single-file server.** `leadfinder.py` is the complete HTTP server. All routes are defined in one `do_POST()` method. Modules are loaded lazily (imported inside the route handler, not at startup), so the server starts instantly and a broken module doesn't prevent the rest from working.

**Shared page cache.** Every time a business website needs to be fetched — for the email finder, the website audit, the presence checker, the opportunity engine, the owner finder — it goes through the same central `fetch_text()` function with a 6-hour in-memory cache. One business website is downloaded at most once per 6 hours no matter how many features use it.

**Frontend tab injection.** The `app.html` file defines only 4 tabs. Every other tab is dynamically created and injected into the page by its corresponding JS file. Each JS module calls `document.createElement("section")`, sets the HTML, appends it to the page, and adds its button to the navbar. The `window.LF` namespace is a shared API bridge so all modules can access the same lead list, send API calls, switch tabs, and log activity.

**No pip installs.** All HTTP calls use `urllib.request`, all DNS lookups use DNS-over-HTTPS via `urllib`, email sending uses `smtplib`, IMAP uses `imaplib`, CSV uses `csv`, threading uses `threading`. This means the app runs anywhere Python 3.8 runs.

---

## 4. All Features & Tabs

### 4.1 Find Leads

**Tab:** `Find leads` (built into app.html)  
**Backend:** `leadfinder.py` — `google_search()`, `serpapi_search()`, `osm_search()`

The primary discovery tool. Choose a data source, enter a business type and location, click Search.

**Data sources:**

| Source | Key Required | What You Get | Search Depth |
|--------|-------------|--------------|-------------|
| Google Maps (Places API New) | Yes (Google Cloud) | Business name, phone, website, address, rating, reviews, coordinates. Reliable website data. | Up to 60 results (normal), 240 (deep 2x2 grid), 540 (deeper 3x3 grid) |
| Google Maps via SerpApi | Yes (SerpApi) | Same data via SerpApi — no Google Cloud account needed. | Up to 60 results |
| OpenStreetMap (free) | No | Same fields from OSM Overpass API. Website data is sparse. | Up to 400 results |

**Filters:**
- No website only
- No website + weak websites (failed audit, free builder, social-only)
- All businesses

**Per-lead actions:**
- **Find email** — scrapes the business website and up to 4 sub-pages (/contact, /about) looking for email addresses
- **Check site** — runs a website audit: HTTPS, mobile-friendly, load speed, outdated copyright, missing title/description, free builder
- **Analyze** — opens the full competitor analysis panel (report.js)
- **Identity** — opens the digital identity score panel
- **Add** — adds the lead to My list

**Bulk actions (toolbar):**
- **Find best targets** — analyzes the top N leads against nearby competitors, labels each Hot/Warm/Low
- **Find emails on all websites** — bulk email scrape (up to all shown leads, 5 parallel workers)
- **Check all websites** — bulk site audit
- **Add all shown** — adds every visible lead to My list
- **Download CSV** — exports visible results

**Scoring (inline):** Every lead gets a quick score (0–100) based on: no website (+50), social-only (+40), weak website (+20–40), reviews, rating, phone, email. Used to sort the results table.

---

### 4.2 My List (CRM)

**Tab:** `My list` (built into app.html)  
**Backend:** None — stored entirely in browser `localStorage`

A personal CRM for all leads you're tracking.

**Fields per lead:** business name, owner name, category, address, phone, email, website, social, rating, reviews, score, priority, stage, follow-up date, notes, map link.

**Stage pipeline:** New → Contacted → No answer → Interested → Follow up → Proposal sent → Won → Not interested

**Tally bar** shows total count, not-contacted count, follow-ups due today, warm leads (Interested + Proposal sent), and won count.

**Actions:**
- Filter by stage or search text
- Edit stage, follow-up date, notes inline
- Remove individual leads
- Clear entire list
- Export to CSV
- Import from CSV (maps standard column names)

**CSV import** accepts these column names (case-insensitive): name, type/category, address, phone, email, website, stage, notes.

---

### 4.3 Niche Finder

**Tab:** `Niche finder` (injected by `static/niche.js`)  
**Backend:** `nichefinder.py` — `/api/cities`, `/api/market-sample`

Helps you find the most underserved niche+city combinations before running a full search.

**Features:**
- **City picker** — selects a country (12 supported) and loads cities from Wikidata by population. Filters by minimum population.
- **Market sample** — picks one city, runs a 1-page Google/SerpApi search, counts what percentage of established businesses lack a website, and gives you an opportunity score.
- **Results table** — shows niche + city combinations ranked by opportunity, with counts of no-website businesses.

**Supported countries for city data:** United States, United Kingdom, Canada, Australia, Germany, France, India, Pakistan, UAE, Saudi Arabia, South Africa, Nigeria.

---

### 4.4 Outreach (Email)

**Tab:** `emails` (injected by `static/outreach.js`)  
**Backend:** `nichefinder.py` — `/api/send-email`

Cold email composition and sending.

**Features:**
- **Template library** — niche-specific templates (plumber, restaurant, salon, etc.) that auto-fill business name, city, issues found
- **AI email writer** — generates personalized cold emails using the AI pool with the lead's real data (name, reviews, website issues, category)
- **3-step sequence builder** — write initial email + 2 follow-ups
- **Draft management** — save drafts per lead, stored in `localStorage`
- **Send via SMTP** — enter your SMTP credentials (Gmail, Outlook, any provider), the system sends through `smtplib` with proper headers including `List-Unsubscribe`
- **Outbox** — tracks sent, draft, failed status per lead

---

### 4.5 Social Outreach

**Extends:** Lead cards in Find leads and My list (`static/social.js`)  
**Backend:** None (client-side only)

Adds social media quick-action buttons to lead cards:
- Copy WhatsApp message template
- Copy Instagram DM template
- Open Facebook/Instagram profile search links
- Templates auto-fill the business name and detected issues

---

### 4.6 How to Get Clients (Guide)

**Tab:** `guide` (built into app.html)  
**Backend:** None (static content)

A practical guide for freelance web designers:
- How to target the right businesses
- Pitching a "digital identity" vs just a website
- The demo-site method (highest-converting approach)
- Outreach channels by country (USA, UK, Pakistan/India/UAE, everywhere)
- Follow-up cadence
- Other acquisition channels (Upwork, Facebook groups, partnerships, referrals)
- Ready-to-use message templates (cold email, WhatsApp, phone call opener)

---

### 4.7 Settings

**Tab:** `settings` (built into app.html)  
**Backend:** `assistant.py` — `/api/assistant/config`

**Search settings** (stored in browser `localStorage`):
- Google Places API key
- SerpApi key
- Google results per search (20 / 40 / 60)
- Competitor search radius (1 km / 3 km / 8 km / 20 km)
- Your name and business name (used in AI-generated scripts)

**Additional API keys** (stored server-side in `data/config.json`):
- Google Custom Search API key (for Dorking + WebCrawler)
- Custom Search Engine ID (CX)
- PageSpeed API key (optional — free tier works without one)
- Companies House API key (UK owner lookup)
- Hunter.io API key (email finder)

**Free AI writer** (stored in localStorage):
- Provider: Ollama (local) or any OpenAI-compatible API
- Model name, Base URL, API key

**Free AI pool** (managed via `assistant.js` tab, stored server-side):
- Configure multiple providers: Gemini, Groq, OpenRouter, Mistral, GitHub Models, NVIDIA NIM, Cerebras, Ollama, Anthropic, or custom
- Providers rotate automatically when one rate-limits

---

### 4.8 Opportunities

**Tab:** `Opportunities` (injected by `static/opportunities.js`)  
**Backend:** `opportunities.py` — `/api/opportunities`, `/api/opportunities/batch`

Evidence-backed lead scoring for every lead in My list.

**How it works:**
1. Click "Analyze My list" — the system analyzes each lead concurrently (3 parallel workers)
2. For each lead it: fetches the website (using the shared cache), runs the audit, checks digital presence, builds a list of opportunities
3. Returns a blueprint score with 5 visible components

**The 5-component score (0–100 total):**

| Component | Max | What it measures |
|-----------|-----|-----------------|
| Opportunity | 30 | Weighted sum of detected issues (no website = 28pts, broken site = 30pts, no mobile = 14pts, etc.) |
| Service Fit | 20 | How well the business type matches web design services (plumber/salon/clinic = 18pts; tech/agency = 5pts) |
| Commercial | 20 | Review count + rating (100+ reviews = 20pts, 30+ = 14pts) |
| Contactability | 15 | Phone (6pts) + email — verified domain (9pts) or unverified (5pts) |
| Confidence | 15 | Data source quality (Google = 5pts), site loads (6pts), address present (3pts) |

**Score bands:**
- 80+ → Review first (highest priority)
- 65–79 → Normal review
- 50–64 → Nurture / research
- Below 50 → Skip

**Package recommendation:** Based on issue severity:
- 3-page refresh ($349) — minor polish needed
- 5-page professional website ($699) — conversion/redesign gaps
- 8-page growth website ($999) — no site, broken, or free builder

**Opportunity categories:** `technical_basics` (HTTPS, mobile, speed), `trust_content` (no website, builder site, outdated, placeholder copy), `conversion` (no booking form, no CTA, no social links, no WhatsApp), `catalogue` (e-commerce structure), `local_business` (no service area, no testimonials)

**Export:** CSV with all scores and opportunity counts.

---

### 4.9 Pipeline / Suppression

**Tab:** `Pipeline` (injected by `static/pipeline.js`)  
**Backend:** `pipeline.py` — `/api/suppression`, `/api/bp-config`, `/api/dedup/*`

**Suppression list:** Domains you never want contacted again (opt-outs, existing clients, competitors). Add/remove domains. The autopilot automatically skips suppressed domains. You can also filter your current My list to find and remove any suppressed leads.

**Blueprint configuration:** Controls how the autopilot and opportunity engine operate:
- Daily candidate target (default: 75)
- Project value range (default: $300–$1,000)
- Require human approval before outreach (default: on)
- Require evidence URL for confirmed opportunities (default: on)
- Always respect opt-outs (default: on)

**Deduplication check:** Enter any URL or domain to check if it's on the suppression list. The canonical domain normalizer strips `www`, `m`, `mobile`, `web`, `amp` prefixes for reliable matching.

---

### 4.10 Dorking

**Tab:** `Dorking` (injected by `static/dorking.js`)  
**Backend:** `dorking.py` — `/api/dorking`, `/api/dorking/templates`

Uses Google Custom Search Engine (CSE) query templates to discover business websites by niche and city. This finds sites that might not appear in Google Maps at all.

**6 built-in query templates:**

| Template | Query pattern | Use case |
|----------|--------------|---------|
| `niche_city` | `{niche} in {city} {country}` | General discovery |
| `contact_page` | `{niche} {city} contact us` | Businesses with contact pages |
| `hiring` | `"we are hiring" {niche} {city}` | Growing businesses |
| `needs_website` | `{niche} {city} -site:facebook.com -site:instagram.com` | Businesses without major social sites |
| `case_studies` | `{niche} case studies {city}` | Businesses showing their work |
| `company` | `"{company}" {city} {country}` | Searching for a specific company |

Select any combination of templates, enter niche + city + country, and all selected queries run in sequence. Results are deduplicated by website URL.

**Key rotation:** Supply multiple CSE API keys (free tier = 100 queries/day each) — the system rotates them automatically when one hits its quota.

**Custom query:** Enter any freeform Google search query against your CSE.

Results can be added to My list or exported to CSV.

---

### 4.11 AI Assistant (Autopilot)

**Tab:** `today` (injected by `static/assistant.js`, appears as "Today")  
**Backend:** `assistant.py` — `/api/assistant/*`, `/api/pool/*`

The daily autopilot and activity center.

**Daily inbox:** Every morning (configurable hour, default 8am), the autopilot runs all your saved search jobs and deposits new leads (ones you've never seen before) into the inbox. You can accept them to My list, mark them seen, or dismiss them.

**Autopilot jobs:** Configure saved searches (niche + city + source + filter + min reviews). The scheduler runs them once per day. Each job tracks the `seen` ID set to prevent showing you the same business twice.

**Follow-ups due today:** Shows leads in My list whose follow-up date is today or overdue.

**Call session timer:** Start a session, log each call outcome (connected / no answer / interested / callback), see today's call count vs your daily goal.

**Activity goals:** Daily targets for calls, emails, and new leads added. Visual progress bars.

**Free AI pool configuration:** Add and test AI providers (Gemini, Groq, OpenRouter, Mistral, GitHub Models, NVIDIA NIM, Cerebras, Ollama, Anthropic, custom). Providers are tried in order; if one rate-limits, the next one is used automatically. Shows cooldown status and today's usage count per provider.

**Monthly quota guard:** Configurable caps for Google Places and SerpApi calls. When the cap is reached, the system stops rather than running up unexpected charges.

---

### 4.12 Identity

**Slide-in panel:** opened from lead cards in Find leads and My list (`static/identity.js`)  
**Backend:** `identity.py` — `/api/identity`, `/api/owner`, `/api/sender-check`

**Digital identity score (0–100, 10 components):**

| Component | Points | How measured |
|-----------|--------|-------------|
| Has a website | 25 | Website field present |
| Website quality | up to 10 | HTTPS (5) + mobile-friendly (5) |
| Google Business Profile | 15 | Detected from web search or map data |
| Reviews | 5 | Review count > 0 |
| Social page | 10 | Facebook or Instagram found |
| 2+ social channels | 5 | Multiple platforms detected |
| Booking / contact form | 10 | Booking widget or quote form on site |
| WhatsApp / live chat | 5 | wa.me link or chat widget on site |
| Professional email | 10 | Domain-matched email (not Gmail/Yahoo) |
| App / PWA | 5 | iOS/Android app link found |

**App fit rating:** Classifies the business as High / Medium / Low fit for a mobile app/PWA based on niche (restaurants, gyms, salons, clinics = high fit; plumbers, lawyers = low fit).

**Owner finder:** Scrapes the About / Team / Contact page for name patterns near "Owner", "Founder", "Director", "Managing Director". Optionally uses the UK Companies House API (free key required) to look up registered directors. An AI readthrough option can extract names from complex pages.

**Sender domain check:** Verifies your own sending domain's email authentication:
- SPF — TXT record lookup via DNS-over-HTTPS
- DMARC — `_dmarc.<domain>` TXT lookup
- DKIM — probes 6 common selectors (google, selector1, default, zoho, mail, k1)
- MX — confirms the domain receives email

---

### 4.13 Hiring Monitor

**Tab:** `Hiring` (injected by `static/hiring.js`)  
**Backend:** `hiring.py` — `/api/hiring/*`

Monitors job boards for freelance web/development opportunities.

**Sources:**
- **Hacker News** (Algolia API) — "Who is hiring?" and "Freelancer? Seeking freelancer?" monthly threads
- **Remotive** (public API) — Remote job listings
- **We Work Remotely** (RSS) — Back-end, full-stack, front-end job feeds

Each source is checked at most once every 3 hours. Results cached in `data/hiring.json` and pruned after 30 days.

**Scoring:** Each post is scored by keyword matching (web design, landing page, Shopify, WordPress, etc.), freelance signals, post age (fresher = higher score), and presence of a direct contact email.

**Status tracking:** new → saved → applied → dismissed. Filter by status or source.

---

### 4.14 Job Search

**Tab:** `Job search` (injected by `static/jobsearch.js`)  
**Backend:** `jobsearch.py` — `/api/jobsearch`

Active job search across multiple sources.

**Sources:**
- **BeBee** — free, direct scrape (no API key required), structured job cards
- **Google web search** via SerpApi — searches for jobs matching your query
- **JobLeads** — Google `site:jobleads.com` search via SerpApi

Results deduplicated by URL. Links open the original job posting.

---

### 4.15 Career Pipeline

**Tab:** `Career` (injected by `static/career.js`)  
**Backend:** `career.py` — `/api/career/*`

A full AI-powered career pipeline ported from the "Proficiently" skills system.

**Profile setup:** Store your resume text, job preferences (role titles, location, salary, must-haves, deal-breakers, nice-to-haves), and work history in `data/career_profile.json`.

**Fit scoring:** Paste a job description, get an AI evaluation: High / Medium / Low / Skip, with reasoning about which of your must-haves and deal-breakers match.

**Resume tailoring:** The AI rewrites your resume specifically for the job — re-ordering sections, adjusting language to match the job description, while being strictly faithful to your actual experience. No invented metrics.

**Cover letter:** AI writes a 250–350 word cover letter with strict quality controls: no em dashes, no invented statistics, company attribution limited to what the job description states.

**Application tracker:** Status pipeline: saved → applied → interview → rejected → offer. Tailored resume and cover letter stored per job in `data/career_jobs.json`.

---

### 4.16 Dashboard

**Tab:** `Dashboard` (injected by `static/dashboard.js`)  
**Backend:** `dashboard.py` — `/api/dashboard/*`

Analytics and performance tracking.

**Panels:**
- **Pipeline funnel** — bar chart of leads at each stage (New through Won)
- **Activity chart** — daily calls, emails, and new leads over the past 30 days (from `data/activity_log.json`)
- **Source performance** — which discovery source (Google Maps, SerpApi, OSM, WebCrawler) produces the most wins and interested leads
- **Email stats** — sent / draft / failed counts from the outbox
- **Top opportunities** — highest-scoring leads not yet won
- **Streak** — consecutive days with at least one logged call or email
- **AI weekly summary** — an AI-generated paragraph summarizing this week's pipeline activity and recommending focus areas

---

### 4.17 Integrations

**Tab:** `Integrations` (injected by `static/integrations.js`)  
**Backend:** `sheets_export.py`, `imap_monitor.py`, `pagespeed.py`, `webcrawler.py`

**Google Sheets export:**
- Full Desktop OAuth 2.0 flow (opens browser for Google consent on first use, saves token to `data/sheets_token.json`)
- Exports 3 tabs: Leads (16 columns including stage, notes, score, priority), Suppressed domains, Blueprint config
- Subsequent exports overwrite the same spreadsheet
- Requires `credentials.json` downloaded from Google Cloud Console

**Reply Monitor (IMAP):**
- Connects to any IMAP server (Gmail, Outlook, etc.) using IMAP4_SSL
- Scans your INBOX for replies from anyone you've emailed
- Classifies replies as: positive (interested/book/price keywords), unsubscribe (opt-out keywords), out-of-office, or generic reply
- Auto-updates My list: unsubscribers → "Not interested" stage; positive replies → "Interested" stage
- Stores classified replies in `data/imap_replies.json`

**PageSpeed Analyzer:**
- Calls Google PageSpeed Insights API v5 for any URL
- Returns Lighthouse scores: Performance, Accessibility, Best Practices, SEO (0–100 each)
- Core Web Vitals: LCP, FCP, TBT, CLS, Speed Index, TTI
- Top actionable opportunities from Lighthouse
- Mobile and/or desktop strategy
- Useful for creating audit reports to pitch to prospects

**WebCrawler — CSE Discovery:**
- Enter a keyword, the system searches Google CSE for URLs, then scrapes each one for business name, email, phone, and address
- Parallel scraping (6 workers)
- Batch URL scraper: paste a list of URLs, scrape all of them
- CSV import: upload a CSV from an external tool (LeadMapAI, OutLead, etc.) and import leads into My list

---

## 5. Backend Modules (Python)

### `leadfinder.py` — Server & Core Engines

The main entry point. Contains the entire HTTP server plus the 3 core search engines and 2 core per-lead tools (email finder + website audit). All other modules are lazy-imported inside route handlers.

**Key functions:**
- `google_search()` — Google Places API (New) `places:searchText` endpoint. Supports grid subdivision for deep search.
- `serpapi_search()` — SerpApi `google_maps` engine
- `osm_search()` — Overpass API with hardcoded tag mappings for 37 business types. Geocodes location via Nominatim (rate-limited: 1 request/second).
- `find_emails()` — Downloads homepage + /contact/about pages, extracts emails with regex. Filters out image/CSS paths and known junk domains.
- `audit_site()` — Downloads a website, checks: HTTPS, viewport tag, load time >3s, copyright year >2 years old, missing title/description, free builder host, no `tel:` link.
- `fetch_text()` — Central cached HTTP downloader. 6-hour TTL for successful pages, 15-minute TTL for failures. Capped at 800 entries.

### `assistant.py` — Autopilot & Config Hub

Manages all persistent server-side state and runs the daily autopilot.

**Key responsibilities:**
- `load()` / `save()` — atomic JSON file read/write (writes to `.tmp` then `os.replace()`)
- `cfg()` — reads `data/config.json`, merged with defaults
- `spend()` / `usage()` — monthly quota guard (increments counters, blocks if cap reached)
- `run_jobs()` — the autopilot: runs saved searches, filters seen/suppressed leads, optionally enriches weak-site leads, deposits new ones in inbox
- `_scheduler()` — background thread, checks every 5 minutes whether to run jobs or `hiring.daily()`

### `analyzer.py` — Competitor & Presence Analysis

**Key responsibilities:**
- `find_competitors()` — finds nearby businesses of the same type using the same data source as the lead was found from
- `presence_from_url()` — downloads a website, extracts social links (Facebook, Instagram, TikTok, YouTube, LinkedIn, X/Twitter), iOS/Android app links, booking platforms, ordering/cart signals, quote forms, live chat
- `digital_score()` — 0–100 score from presence flags + review count
- `analyze()` — combines competitor fetch + presence check for all (ThreadPoolExecutor 8 workers), returns comparison
- `ai_write()` — simple AI writer for the older single-provider setup (Ollama or OpenAI-compatible)

### `ai_pool.py` — Free AI Provider Pool

**10 supported providers:**
- Gemini (Google AI Studio) — free, model: `gemini-2.5-flash`
- Groq — free, model: `llama-3.3-70b-versatile`
- OpenRouter — free `:free` models
- Mistral — free Experiment plan
- GitHub Models — free with GitHub token, model: `openai/gpt-4.1-mini`
- NVIDIA NIM — free tier, model: `meta/llama-3.3-70b-instruct`
- Cerebras — free tier
- Ollama — local, no key, model: `llama3.2`
- Anthropic Claude — paid
- Custom — any OpenAI-compatible endpoint

**Rotation logic:** `complete()` tries providers in the configured order. On any error it classifies the failure and sets a cooldown: 65 seconds for rate limits, 3 hours for daily quota exhaustion, 30 minutes for auth errors. The next provider is tried immediately. If all providers are cooling off, the error message lists each one and its remaining cooldown.

### `opportunities.py` — Lead Scoring

See Section 4.8 for the full scoring description.

**Additional detail:** Each opportunity object carries: `id`, `category`, `observation`, `evidence_url` (the page URL where the issue was found), `evidence_excerpt` (the matching text), `measured_value` (actual measurement, e.g., "4.2s"), `impact`, `suggested_fix`, `service_fit`, `confidence` (high/medium/low), `weight`, `verification_status` (measured vs observed), `detected_at`.

### `pipeline.py` — Suppression & Deduplication

- `canonical_domain()` — strips www/m/mobile/web/amp, lowercases, normalizes for reliable matching
- `add_suppression()` / `remove_suppression()` / `filter_suppressed()` — manage `data/suppression.json`
- `bp_config()` / `save_bp_config()` — manage `data/bp_config.json`

### `dorking.py` — Google CSE Discovery

- Key rotation: multiple CSE API keys (list in config), with 1-hour per-key cooldown on quota errors
- `cse_search()` — handles pagination (10 results/call), rotates keys
- `discover()` — runs selected templates, merges + deduplicates by website URL

### `emailverify.py` — Email Verification

Pipeline for each email:
1. Syntax check (regex)
2. Disposable domain filter (checks against a known list)
3. MX lookup via DNS-over-HTTPS (`https://dns.google/resolve?name=<domain>&type=MX` with Cloudflare fallback)
4. SMTP RCPT TO probe — opens SMTP connection, sends `EHLO` + `MAIL FROM` + `RCPT TO`, reads response code
5. Catch-all detection — if SMTP accepted the target address, probe a random UUID address; if that's also accepted, the domain is catch-all

Status values: `verified` (SMTP accepted, not catch-all), `deliverable-domain` (MX found, SMTP probe accepted but might be catch-all), `domain-only` (MX exists but SMTP blocked or catch-all), `invalid` (550/551 rejection), `unknown` (no MX records)

### `contacts.py` — Contact Enrichment

- `enrich()` — scrapes website for emails via `find_emails()`, finds contact page URL, generates guessed role emails (info@, contact@, hello@, support@) if no email found
- `verify()` — DNS-over-HTTPS MX check only (lighter than full SMTP probe)
- `hunter()` — calls Hunter.io domain search API for email patterns

### `identity.py` — Business Identity & Owner Lookup

- `identity()` — builds the 10-component digital identity score
- `find_owner()` — searches About/Team pages for owner name patterns; calls UK Companies House API (`api.company-search.companieshouse.gov.uk`) for director names; optionally sends page to AI for extraction
- `app_fit()` — niche-to-app-fit classification
- `sender_check()` — DNS-over-HTTPS lookups for SPF, DMARC, DKIM (6 selectors), MX

### `hiring.py` — Hiring Post Monitor

- **Hacker News** — Algolia `hn.algolia.com` API, searches for "Who is hiring?" and "Freelancer? Seeking freelancer?" threads, extracts child posts
- **Remotive** — `remotive.com/api/remote-jobs` public API
- **We Work Remotely** — RSS feeds for 3 job categories
- Minimum 3-hour gap between checks per source (stored in `data/hiring.json`)
- Scoring: keyword presence (20 keywords for web design), freelance signal, age penalty, email bonus

### `jobsearch.py` — Job Search

- **BeBee** — scrapes `bebee.com/jobs/q/{query}`, parses `<article data-voice-job="card">` elements
- **SerpApi Google search** — `engine=google`, query includes "web design" or custom
- **SerpApi JobLeads** — `engine=google`, adds `site:jobleads.com`

### `career.py` — Career Pipeline

All prompts have strict accuracy constraints: AI cannot invent any fact, metric, or claim not in the input data.
- `fit_score()` — ~600 token prompt with dealbreakers, must-haves, nice-to-haves
- `tailor_resume()` — ~2600 token prompt with full resume and job description
- `write_cover_letter()` — ~1200 token prompt with explicit prohibitions (em dashes, invented stats, company over-attribution)
- State stored in `data/career_profile.json` and `data/career_jobs.json`

### `dashboard.py` — Analytics

- Reads `data/activity_log.json` (synced from browser via `/api/dashboard/activity` POST)
- Computes pipeline stage counts, source performance, lead scores
- Returns chart data as arrays for the frontend to render
- `ai_weekly_summary()` — sends a week of activity data to the AI pool for a narrative summary

### `sheets_export.py` — Google Sheets

- Full OAuth 2.0 Desktop flow: generates auth URL, starts temporary HTTP server on port 28765 to receive the callback, exchanges code for tokens, saves to `data/sheets_token.json`
- Uses Google Sheets API v4 REST directly (no gspread library)
- Creates a new spreadsheet on first use, overwrites on subsequent exports
- 3 worksheets: Leads, Suppressed, Blueprint Config

### `imap_monitor.py` — Reply Monitor

- Connects via `imaplib.IMAP4_SSL` (port 993 by default)
- Searches `SINCE <date>` for recent messages, parses RFC822 with `email.message_from_bytes()`
- `classify_reply()` — regex matching for OOO, unsubscribe, positive signals
- Saves to `data/imap_replies.json`; the frontend polls this at tab open

### `pagespeed.py` — Google PageSpeed Insights

- API v5: `https://www.googleapis.com/pagespeedonline/v5/runPagespeed`
- Extracts Lighthouse categories, CWV metrics (LCP, FCP, TBT, CLS, TTI, SI), top 8 opportunity audits
- Handles both mobile and desktop strategies
- Works without a key (quota: 25,000 requests/day; optional key raises this)

### `webcrawler.py` — WebCrawler

- `cse_discover()` — Google CSE keyword search returning URLs (pagination, 10 per call)
- `scrape_url()` — single URL: extracts title→name, emails (regex), phone (digit-count filter 7–15 digits), address (keyword proximity snippet)
- `batch_scrape()` — 6-worker parallel scraping
- `crawl_and_scrape()` — full pipeline: CSE → scrape → deduplicate by domain → normalize to lead format
- CSV import/export with 14-field schema matching My list format

### `nichefinder.py` — Niche & City Analysis

- `top_cities()` — SPARQL query to `query.wikidata.org`, filters by minimum population, cached for 24 hours in memory
- `market_sample()` — 1-page search, computes no-website percentage
- `send_email()` — `smtplib` with STARTTLS (587) or SSL (465), proper `EmailMessage` with `List-Unsubscribe` header, retry logic

---

## 6. Data Flow — How Requests Work

### A typical search request

```
1. User fills in "plumber" + "Austin, Texas" + Google source, clicks Search
2. Browser: POST /api/search  {"source":"google","query":"plumber","location":"Austin, Texas","apiKey":"...","pages":"3"}
3. leadfinder.py do_POST() matches /api/search
4. google_search() called → 3 calls to Google Places searchText API (up to 60 results)
5. Each result normalized to lead dict: {id, source, name, category, address, phone, email, website, rating, reviews, mapsUrl, lat, lng, ...}
6. Response: {"leads": [...]} → browser
7. JS stores results in memory array, renders table
8. User clicks "Find email" on a lead with a website
9. Browser: POST /api/emails  {"url":"https://example-plumber.com"}
10. find_emails() → fetch_text() downloads homepage (caches it)
11. Checks /contact, /about pages concurrently (ThreadPoolExecutor 4)
12. Returns up to 5 emails found
13. JS updates the lead object in memory + syncs to My list in localStorage
```

### A typical analyze request

```
1. User clicks "Analyze" on a lead
2. Browser: POST /api/analyze  {"lead":{...},"source":"google","apiKey":"...","radius":3000}
3. analyzer.analyze() called
4. find_competitors() → Google Places API (nearby, same type) — 1 API call, counted against quota
5. ThreadPoolExecutor 8: presence_from_url() for lead + each competitor concurrently
6. Each presence check: fetch_text() (shared cache), regex scan for social/booking/chat
7. Returns {lead: {presence, digitalScore}, competitors: [...]}
8. report.js renders the slide-in panel
9. AI email button: POST /api/ai  {"prompt":"..."} → ai_pool.complete() → Gemini/Groq/etc.
10. AI-written script displayed in panel
```

### The autopilot cycle

```
Every 5 minutes, _scheduler() checks:
  - Is it past runHour (default 8am)?
  - Has it already run today?
  - Are there enabled jobs?
  - Is another run not already in progress?

If yes → run_jobs():
  For each job (niche + city + source):
    1. Run the search (Google/SerpApi/OSM)
    2. Load seen.json (all-time seen lead IDs)
    3. Filter: keep only leads not in seen set
    4. Optional: audit weak sites, enrich emails
    5. Add new leads to inbox.json
    6. Add ALL leads (new or not) to seen.json (prevents future duplicates)
  Update config.json → lastRun = today

Frontend polls /api/assistant/status every 30 seconds
  → shows inbox count badge on "today" tab
User opens "today" tab → inbox leads shown
  → Accept: adds to My list, removes from inbox
  → Dismiss: removes from inbox (stays in seen)
```

---

## 7. External APIs & Services

### Required for core functionality

| Service | Purpose | Where to get key | Free tier |
|---------|---------|-----------------|-----------|
| Google Places API (New) | Business search with website/phone data | console.cloud.google.com | ~$200/mo credit (≈800 searches) |
| SerpApi | Google Maps data without Google Cloud | serpapi.com | 100 searches/month |

### Optional but unlock major features

| Service | Purpose | Where to get key | Free tier |
|---------|---------|-----------------|-----------|
| Google Custom Search (CSE) | Dorking + WebCrawler discovery | console.cloud.google.com + cse.google.com | 100 queries/day |
| Google PageSpeed Insights | PageSpeed scores | console.cloud.google.com | 25,000/day free without key |
| Google Sheets API | Sheets export | console.cloud.google.com (OAuth, not key) | Free |
| UK Companies House | Owner lookup (UK businesses) | developer.company-information.service.gov.uk | Free |
| Hunter.io | Domain email pattern lookup | hunter.io | 25 searches/month free |

### Free (no key)

| Service | Purpose |
|---------|---------|
| OpenStreetMap / Overpass | Business discovery (free) |
| Nominatim | Geocoding (1 req/sec rate limit) |
| Wikidata SPARQL | City lists by country |
| Hacker News (Algolia API) | Hiring post monitor |
| Remotive API | Remote job listings |
| We Work Remotely (RSS) | Remote job feeds |
| BeBee (scrape) | Job search |
| DNS-over-HTTPS (Google + Cloudflare) | Email verification, MX lookup |
| Ollama (local) | AI writing (no internet required) |

### Free AI providers (sign up for free API key)

| Provider | Model | Sign up |
|----------|-------|---------|
| Google Gemini (AI Studio) | gemini-2.5-flash | aistudio.google.com/apikey |
| Groq | llama-3.3-70b-versatile | console.groq.com/keys |
| OpenRouter | Any `:free` model | openrouter.ai/keys |
| Mistral | mistral-small-latest | console.mistral.ai/api-keys |
| GitHub Models | openai/gpt-4.1-mini | GitHub Settings → Tokens |
| NVIDIA NIM | meta/llama-3.3-70b-instruct | build.nvidia.com |
| Cerebras | Available models | cloud.cerebras.ai |

---

## 8. Data Storage & Persistence

All server-side data lives in the `data/` folder (created automatically on first run). All writes are atomic: the system writes to a `.tmp` file then uses `os.replace()` to swap it in, preventing corruption on crash.

### Server-side files (`data/*.json`)

| File | Contents | Created by |
|------|----------|-----------|
| `config.json` | Autopilot jobs, all API keys, AI pool config, monthly quota caps, run hour, last run date | `assistant.py` |
| `usage.json` | Monthly Google Places and SerpApi call counts (resets each month) | `assistant.py` |
| `inbox.json` | Leads found by the autopilot, waiting to be reviewed | `assistant.py` |
| `seen.json` | All lead IDs ever shown by the autopilot (prevents duplicates) | `assistant.py` |
| `suppression.json` | Do-not-contact canonical domains | `pipeline.py` |
| `bp_config.json` | Blueprint configuration (daily target, project value, approval flags) | `pipeline.py` |
| `hiring.json` | Hiring post cache, status tracking, last-fetch timestamps | `hiring.py` |
| `career_profile.json` | Resume, job preferences, work history | `career.py` |
| `career_jobs.json` | Job applications with tailored resumes and cover letters | `career.py` |
| `activity_log.json` | Daily call/email/newLeads counts (synced from browser) | `dashboard.py` |
| `sheets_token.json` | Google OAuth access + refresh token | `sheets_export.py` |
| `sheets_config.json` | Spreadsheet ID, credentials file path, authorized status | `sheets_export.py` |
| `imap_config.json` | IMAP server, email, password, lookback days | `imap_monitor.py` |
| `imap_replies.json` | Classified reply records (last 50 shown in UI) | `imap_monitor.py` |
| `crawl_schedule.json` | Scheduled WebCrawler jobs | `webcrawler.py` |

### Browser-side (`localStorage`)

| Key | Contents |
|-----|----------|
| `lf-list` | Full "My list" CRM — all leads, stages, notes, follow-up dates, analysis results, enrichment data |
| `lf-settings` | Google/SerpApi keys (also stored server-side after "Save API keys"), UI preferences, AI config |
| `lf-log` | Activity log (synced to server daily) |
| `lf-outbox` | Email drafts and send history |
| `lf-ai-scripts` | Saved AI-generated email scripts |

**Important:** "My list" is stored only in your browser's localStorage. It is not backed up to `data/`. Export to CSV regularly, or export to Google Sheets, to preserve your CRM data.

---

## 9. API Key Setup Guide

### Google Places API (for "Google Maps" source in Find leads)

1. Go to `console.cloud.google.com`
2. Create a project (or select an existing one)
3. Enable billing (a card is required; there is a free monthly credit)
4. Go to APIs & Services → Library → search "Places API (New)" → Enable
5. Go to Credentials → Create Credentials → API Key
6. Under API restrictions: choose "Places API (New)"
7. Under Application restrictions: leave as "None"
8. Copy the key into Settings → Google Places API key

### SerpApi (alternative to Google Places, no Google Cloud needed)

1. Sign up at `serpapi.com`
2. Copy your API key from the dashboard
3. Paste into Settings → SerpApi key

### Google Custom Search (for Dorking + WebCrawler)

1. Go to `console.cloud.google.com` → APIs & Services → Library → enable "Custom Search API"
2. Create an API key (same as above)
3. Go to `cse.google.com`, create a new search engine
4. Under "Sites to search": put `*` to search the entire web
5. Copy the Search Engine ID (labeled "cx")
6. In Settings: paste the CSE API key into "Google Custom Search API key" and the CX into "Custom Search Engine ID"

### Free AI (Gemini — fastest to set up)

1. Go to `aistudio.google.com/apikey`
2. Create an API key (free, no billing required)
3. In the AI Assistant tab → Free AI pool → Add provider → Gemini → paste key → Save

### Google Sheets export

1. Go to `console.cloud.google.com` → enable "Google Sheets API"
2. Go to APIs & Services → Credentials → Create Credentials → OAuth client ID
3. Application type: **Desktop app**
4. Download the JSON file
5. In Integrations → Google Sheets → paste the path to the downloaded JSON file
6. Click Export — a browser window opens to authorize on first use

### IMAP Reply Monitor (Gmail example)

1. In Gmail settings → See all settings → Forwarding and POP/IMAP → Enable IMAP
2. Go to Google Account → Security → 2-Step Verification → App passwords
3. Create an app password for "Mail"
4. In Integrations → Reply Monitor: IMAP server = `imap.gmail.com`, email = your Gmail address, password = the app password

---

## 10. Security Model

**Localhost-only binding:** The server binds to `127.0.0.1:8765`, not `0.0.0.0`. It is not accessible from other devices on your network.

**CORS enforcement:** All POST requests check the `Origin` header. Requests from any origin other than `localhost` or `127.0.0.1` are blocked with a 403 response. This prevents a malicious website from sending API calls to your local server and using your API keys.

**Keys stay local:** All API keys are stored in your browser's localStorage or in `data/config.json` on your own machine. They are never transmitted to any external service other than the specific API they're for.

**No authentication:** There is no login. Anyone with access to your computer and the port number can use the app. Do not run this on a shared or public machine.

**SMTP credentials:** SMTP password and IMAP password are stored in plaintext in `data/imap_config.json`. Use App Passwords (not your main account password) when possible.

**Page cache:** Downloaded website content is cached in memory (not on disk) for 6 hours. The cache is cleared on server restart.

---

## 11. File Structure

```
leadfinder-updated-2/
├── leadfinder.py          # Main entry point: HTTP server, all routing, core search engines
├── app.html               # Single-page frontend (4 built-in tabs + inline JS)
├── assistant.py           # Autopilot, config store, quota guard, inbox management
├── analyzer.py            # Competitor analysis, digital presence detection, AI writer
├── ai_pool.py             # Free AI provider rotation (10 providers)
├── opportunities.py       # Blueprint lead scoring + opportunity engine
├── pipeline.py            # Suppression list, deduplication, blueprint config
├── dorking.py             # Google CSE query template engine
├── emailverify.py         # Full SMTP email verification pipeline
├── contacts.py            # Contact enrichment, Hunter.io integration
├── identity.py            # Digital identity score, owner lookup, sender check
├── hiring.py              # Hiring post monitor (HN, Remotive, WWR)
├── jobsearch.py           # Job search (BeBee, SerpApi)
├── career.py              # AI career pipeline (fit score, tailor resume, cover letter)
├── dashboard.py           # Analytics and pipeline metrics
├── sheets_export.py       # Google Sheets OAuth export
├── imap_monitor.py        # IMAP reply monitoring and classification
├── pagespeed.py           # Google PageSpeed Insights adapter
├── webcrawler.py          # CSE discovery + batch URL scraping
├── nichefinder.py         # Niche/city analysis, SMTP send
│
├── static/
│   ├── report.js          # Competitor analysis slide-in panel
│   ├── niche.js           # Niche finder tab
│   ├── outreach.js        # Cold email composer tab
│   ├── social.js          # Social media outreach extensions on lead cards
│   ├── assistant.js       # Daily inbox / autopilot / AI pool config tab
│   ├── identity.js        # Digital identity score slide-in panel
│   ├── hiring.js          # Hiring monitor tab
│   ├── jobsearch.js       # Job search tab
│   ├── career.js          # Career pipeline tab
│   ├── dashboard.js       # Dashboard analytics tab
│   ├── integrations.js    # Sheets / IMAP / PageSpeed / WebCrawler tab
│   ├── opportunities.js   # Opportunities scoring tab
│   ├── pipeline.js        # Suppression list / blueprint config tab
│   └── dorking.js         # Dorking tab
│
├── data/                  # Created automatically on first run
│   ├── config.json        # API keys, jobs, AI pool, quota caps
│   ├── usage.json         # Monthly API call counters
│   ├── inbox.json         # Autopilot lead inbox
│   ├── seen.json          # All-time seen lead IDs
│   ├── suppression.json   # Do-not-contact domains
│   ├── bp_config.json     # Blueprint configuration
│   ├── hiring.json        # Hiring post cache
│   ├── career_profile.json
│   ├── career_jobs.json
│   ├── activity_log.json
│   ├── sheets_token.json
│   ├── sheets_config.json
│   ├── imap_config.json
│   ├── imap_replies.json
│   └── crawl_schedule.json
│
├── CHANGES.md             # Changelog
├── INTEGRATION_PLAN.md    # Integration blueprint notes
└── SYSTEM_DOCUMENTATION.md  # This file
```

---

## 12. Limitations & Known Constraints

**My list is browser-only.** Lead data, stages, and notes are stored in `localStorage`. Clearing browser data deletes your entire CRM. Export to CSV or Google Sheets regularly as a backup.

**OpenStreetMap website data is sparse.** Many businesses listed in OSM don't have their website tagged. "No website" results from OSM are less reliable than from Google Maps — always click "Google" research link to verify.

**Google Places API costs money.** While there is a ~$200/month free credit, heavy use (many deep searches or competitor analyses) will exhaust it. The monthly cap in Settings protects you.

**Email verification is probabilistic.** SMTP verification can give false positives if a mail server is catch-all, and false negatives if a mail server blocks probing. The `deliverable-domain` status (MX exists) is more reliable than the full SMTP probe.

**AI accuracy.** All AI-generated content (emails, resume tailoring, cover letters, weekly summaries) uses prompts with strict accuracy constraints, but AI can still make mistakes. Always review AI output before sending.

**No mobile app.** The app is designed for desktop browsers. It works in mobile browsers but the tables and layouts are optimized for wider screens.

**Single user.** There is no multi-user support, login system, or access control. One person, one machine.

**Google Sheets export requires initial manual browser step.** The OAuth flow opens a browser window on first use. If the machine has no browser or is headless, the Sheets export cannot be authorized.

**IMAP password stored in plaintext.** `data/imap_config.json` stores the IMAP password. Use a Gmail App Password or a dedicated email account, not your main account password.

**Port 8765 must be free.** If another application is using port 8765, the server will fail to start. Change the port with the `LEADFINDER_PORT` environment variable.
