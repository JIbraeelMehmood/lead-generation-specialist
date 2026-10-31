# LeadFinder

**Find local businesses that need a website. Research, score, pitch, and track them — all from your own computer.**

LeadFinder is a self-hosted lead generation platform built for freelance web designers and digital agencies. Run one command, open your browser, and start finding clients anywhere in the world. No SaaS subscriptions, no shared database, no pip installs. Everything runs locally on your machine.

---

## What it does

- Searches **Google Maps, SerpApi, and OpenStreetMap** for local businesses in any city
- Automatically flags businesses with **no website, a broken website, or a weak digital presence**
- **Audits every website** it finds: HTTPS, mobile-friendly, speed, SEO, outdated design
- **Finds emails** by scraping business websites and sub-pages
- **Analyzes competitors** to show why a prospect needs to act now
- **Scores every lead** using a 5-component evidence-backed blueprint score
- **Writes cold emails** using free AI (Gemini, Groq, Ollama, and more)
- Tracks your entire pipeline in a **built-in CRM** with stages, follow-up dates, and notes
- **Sends emails** directly via SMTP and monitors replies via IMAP
- Exports everything to **Google Sheets**
- Runs an **autopilot** that finds fresh leads every morning and puts them in your inbox

---

## Quick start

**Requirements:** Python 3.8 or newer. No other packages needed.

```bash
# Clone or download the project, then:
cd leadfinder-updated-2
python3 leadfinder.py
```

Your browser opens to `http://localhost:8765`. That's it.

To stop the server, press `Ctrl+C` in the terminal.

### Optional: set API keys via environment variables

```bash
GOOGLE_PLACES_API_KEY="AIza..." python3 leadfinder.py
SERPAPI_KEY="your-key-here" python3 leadfinder.py
```

Or paste them in the **Settings** tab once the app is open.

### Change the port

```bash
LEADFINDER_PORT=9000 python3 leadfinder.py
```

---

## First-time setup (5 minutes)

1. Start the server and open `http://localhost:8765`
2. Go to the **Settings** tab
3. Paste your **Google Places API key** (see setup guide below) or **SerpApi key**
4. Click **Save settings**
5. Go to **Find leads**, enter a business type and city, click **Search**

To unlock AI email writing (free):
1. Get a free key from [Google AI Studio](https://aistudio.google.com/apikey) (takes 30 seconds)
2. Go to the **Today** tab → **Free AI pool** → Add provider → Gemini → paste key → Save

To use the completely free path with no API keys at all:
- Set the source to **OpenStreetMap** in Find leads — no key required
- Install [Ollama](https://ollama.com) locally for AI writing — no key required

---

## Features at a glance

### 17 tabs — one platform

| Tab | What you can do |
|-----|----------------|
| **Find leads** | Search Google Maps / SerpApi / OpenStreetMap. Filter by no website, weak website, or all. Bulk email find, site audit, best-target analysis. |
| **My list** | Full CRM. Stage pipeline (New → Won). Follow-up dates. Notes. CSV import and export. |
| **Niche finder** | Pick a country and niche, sample cities to find which have the most no-website businesses. |
| **Outreach** | AI-written cold emails. Niche templates. 3-step sequence builder. SMTP send. Outbox tracking. |
| **Social** | WhatsApp and Instagram DM templates pre-filled with each lead's details. |
| **Opportunities** | Evidence-backed 5-component score (0–100) for every lead. Package recommendations. Export to CSV. |
| **Pipeline** | Suppression / do-not-contact list. Blueprint config (daily targets, project value). Domain dedup check. |
| **Dorking** | Google CSE query templates to find business websites not on Maps. 6 templates, key rotation. |
| **Today** | Daily inbox from the autopilot. Follow-ups due today. Call session timer. Activity goals. |
| **Identity** | 10-component digital identity score for any business. Owner lookup. Sender domain check (SPF/DKIM/DMARC). |
| **Hiring** | Monitor Hacker News, Remotive, and We Work Remotely for freelance web design gigs. |
| **Job search** | Search BeBee and Google/JobLeads for web design jobs. |
| **Career** | AI-powered pipeline: fit scoring, resume tailoring, cover letter writing, application tracking. |
| **Dashboard** | Pipeline funnel, activity chart, source performance, AI weekly summary. |
| **Integrations** | Google Sheets export, IMAP reply monitor, PageSpeed analyzer, WebCrawler CSE discovery. |
| **How to get clients** | Practical guide: outreach channels by country, message templates, follow-up cadence. |
| **Settings** | API keys, AI provider config, search preferences. |

---

## Lead discovery — 3 sources

### Google Maps (Google Places API)
Best quality. Returns business name, phone, website, address, rating, review count, and exact coordinates. Supports deep search (split the city into a 2×2 or 3×3 grid) to find up to 540 businesses per search instead of 60.

Needs a Google Cloud account with the **Places API (New)** enabled. See [API key setup](#api-key-setup) below.

### SerpApi
Same Google Maps data, fetched through SerpApi — no Google Cloud account needed. Sign up at [serpapi.com](https://serpapi.com) for 100 free searches/month.

### OpenStreetMap (free, no key)
Completely free. Uses the Overpass API with 37 built-in business type mappings (plumber, restaurant, dentist, salon, car repair, etc.). Coverage varies by city. Website data is sparse — use the research links to verify.

---

## Lead scoring

Every lead gets an instant score (0–100) based on:
- No website: +50 pts
- Social page only: +40 pts
- Weak website (audit score ≥ 20): +20–40 pts
- 100+ Google reviews: +20 pts
- Rating 4.5+: +10 pts
- Has phone: +10 pts
- Has email: +10 pts

The **Opportunities tab** goes deeper with a 5-component blueprint score:

| Component | Max | What it measures |
|-----------|-----|-----------------|
| Opportunity | 30 | Weighted issues found on the website |
| Service fit | 20 | How well the business type fits web design |
| Commercial | 20 | Review count and rating |
| Contactability | 15 | Phone + verified email |
| Confidence | 15 | Data source quality + completeness |

Score bands: **Review first** (80+) · **Normal review** (65+) · **Nurture** (50+) · **Skip** (<50)

---

## AI email writing (free)

LeadFinder supports 10 AI providers. Add one free key and AI email writing works everywhere in the app.

| Provider | Free tier | Sign up |
|----------|-----------|---------|
| Google Gemini | Generous free tier | [aistudio.google.com/apikey](https://aistudio.google.com/apikey) |
| Groq | Free tier | [console.groq.com/keys](https://console.groq.com/keys) |
| OpenRouter | Free `:free` models | [openrouter.ai/keys](https://openrouter.ai/keys) |
| Mistral | Free Experiment plan | [console.mistral.ai](https://console.mistral.ai/api-keys) |
| GitHub Models | Free with GitHub account | GitHub Settings → Tokens |
| NVIDIA NIM | Free tier | [build.nvidia.com](https://build.nvidia.com) |
| Cerebras | Free tier | [cloud.cerebras.ai](https://cloud.cerebras.ai) |
| Ollama | Completely free, runs locally | [ollama.com](https://ollama.com) |

Providers are tried in priority order. If one rate-limits, the next one is used automatically — you never get a permanent failure.

---

## Autopilot

Configure saved searches (niche + city + source). The autopilot runs them once a day at 8am (configurable), collects new leads you've never seen before, and puts them in your **Today** inbox. It remembers every lead it has ever shown you, so you'll never see the same business twice.

Set a monthly API call cap (default: 900 Google calls, 90 SerpApi calls) to prevent surprise charges. The system stops and notifies you when the cap is reached.

---

## API key setup

### Google Places API (for Google Maps source)

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a project
2. Enable billing (Google requires a card; there is a monthly free credit)
3. Go to **APIs & Services → Library** → search **"Places API (New)"** → Enable
4. Go to **Credentials → Create Credentials → API Key**
5. Set API restriction to **Places API (New)**, Application restriction to **None**
6. Paste the key in **Settings → Google Places API key**

> Tip: set a daily quota limit in Google Cloud to cap unexpected charges.

### Google Custom Search (for Dorking + WebCrawler)

1. Enable the **Custom Search API** in Google Cloud Console
2. Create an API key (same project is fine)
3. Go to [cse.google.com](https://cse.google.com), create a new search engine
4. Under "Sites to search": enter `*` to search the whole web
5. Copy the **Search Engine ID (cx)**
6. In **Settings → Additional API keys**: paste the CSE key and the CX

### Google Sheets export

1. Enable the **Google Sheets API** in Google Cloud Console
2. Create an **OAuth client ID** (application type: Desktop app)
3. Download the `credentials.json` file
4. In **Integrations → Google Sheets**: enter the path to that file
5. On first export, a browser window opens to authorize — then it works automatically

### IMAP reply monitor (Gmail)

1. In Gmail: **Settings → See all settings → Forwarding and POP/IMAP → Enable IMAP**
2. Go to **Google Account → Security → App passwords** → create one for "Mail"
3. In **Integrations → Reply Monitor**: use `imap.gmail.com`, your Gmail address, and the App Password

---

## How the autopilot scores and routes leads

```
Search (Google / SerpApi / OSM)
    │
    ▼
Filter: already seen? → skip
Filter: has website? → based on job's filter setting
Filter: min reviews? → based on job config
    │
    ▼
Optional enrichment (if filter = "weak websites"):
  - Audit the website
  - Find emails on the site
    │
    ▼
New leads → data/inbox.json
    │
Open "Today" tab → review inbox → Accept or Dismiss
```

---

## Data and privacy

- **Everything stays on your machine.** No data is sent to any external server except the specific API calls you make (Google, SerpApi, etc.).
- **My list** (your CRM) is stored in your browser's `localStorage`. Export to CSV or Google Sheets regularly — clearing browser data will delete it.
- **API keys** are stored in `data/config.json` (server-side keys) and `localStorage` (browser-side keys). They are never transmitted to anything other than their respective APIs.
- **The server only accepts requests from localhost.** Any request from a different origin is blocked with a 403 error.

---

## Persistent data files

All server-side data is stored in the `data/` folder (created automatically on first run):

```
data/
├── config.json          ← API keys, jobs, AI pool, monthly caps
├── inbox.json           ← Autopilot-found leads awaiting review
├── seen.json            ← All-time seen lead IDs (prevents duplicates)
├── suppression.json     ← Do-not-contact domains
├── usage.json           ← Monthly API call counters
├── hiring.json          ← Hiring post cache and status
├── career_profile.json  ← Resume and job preferences
├── career_jobs.json     ← Job applications and tailored documents
├── activity_log.json    ← Daily call/email/lead counts
├── imap_config.json     ← IMAP server config and password
├── imap_replies.json    ← Classified reply records
├── sheets_token.json    ← Google OAuth token
└── ...
```

---

## Project structure

```
leadfinder-updated-2/
├── leadfinder.py        ← Entry point: HTTP server + Google/SerpApi/OSM search engines
├── app.html             ← Single-page frontend (all tabs load from here)
├── assistant.py         ← Autopilot, config, quota guard, inbox
├── analyzer.py          ← Competitor analysis, digital presence detection
├── ai_pool.py           ← Free AI provider rotation (10 providers)
├── opportunities.py     ← Lead scoring + opportunity engine
├── pipeline.py          ← Suppression list, dedup, blueprint config
├── dorking.py           ← Google CSE query templates
├── emailverify.py       ← SMTP email verification
├── contacts.py          ← Contact enrichment, Hunter.io
├── identity.py          ← Digital identity score, owner lookup
├── hiring.py            ← HN / Remotive / WWR job monitor
├── jobsearch.py         ← BeBee + SerpApi job search
├── career.py            ← AI career pipeline
├── dashboard.py         ← Analytics
├── sheets_export.py     ← Google Sheets OAuth export
├── imap_monitor.py      ← IMAP reply monitoring
├── pagespeed.py         ← Google PageSpeed Insights
├── webcrawler.py        ← CSE discovery + batch URL scraping
├── nichefinder.py       ← City/niche analysis + SMTP send
├── static/              ← JavaScript tab modules (one file per tab)
├── data/                ← All persistent data (auto-created)
└── SYSTEM_DOCUMENTATION.md  ← Full technical reference
```

---

## What you need (and don't need)

| | Required | Optional |
|--|---------|---------|
| **Python** | 3.8+ | — |
| **pip / virtual env** | ❌ No | — |
| **Google Places key** | For Google Maps source | Can use SerpApi or OpenStreetMap instead |
| **SerpApi key** | For SerpApi source | Free: 100 searches/month |
| **CSE key + CX** | For Dorking + WebCrawler | — |
| **AI key** | For email writing | Free providers available; Ollama works offline |
| **Hunter.io key** | For email pattern lookup | — |
| **Companies House key** | For UK owner lookup | — |
| **Google credentials.json** | For Sheets export | — |
| **SMTP credentials** | To send emails | Any Gmail, Outlook, or SMTP server |
| **IMAP credentials** | To monitor replies | Any Gmail, Outlook, or IMAP server |

---

## Troubleshooting

**The app won't start — "Address already in use"**
Port 8765 is taken by another process. Run with a different port:
```bash
LEADFINDER_PORT=8766 python3 leadfinder.py
```

**Google search fails: "Places API (New) is not enabled"**
In Google Cloud Console: APIs & Services → Library → search "Places API (New)" → Enable. Wait 2–5 minutes before trying again.

**Google search fails: "API key not valid"**
Double-check the key is copied correctly (no extra spaces). In Credentials, make sure the API restriction includes Places API (New) and Application restriction is set to None.

**Google search fails: "Monthly safety cap reached"**
The monthly call limit was reached. Go to **Today tab → Settings → Monthly caps** and raise the limit, or wait until next month.

**Ollama AI fails: "Couldn't reach Ollama"**
Make sure Ollama is running: open a terminal and run `ollama serve`. Also confirm the model is downloaded: `ollama pull llama3.2`.

**OpenStreetMap returns no results**
OSM coverage varies. Try a larger city, or switch to Google Maps or SerpApi. Also try a different business category from the dropdown list.

**Emails not sending**
For Gmail: use an [App Password](https://myaccount.google.com/apppasswords), not your main password. For other providers, check that SMTP is enabled and use port 587 (STARTTLS) or 465 (SSL).

**My list data disappeared**
My list is stored in browser localStorage. If you cleared browser data or used a different browser profile, the data is gone. Export to CSV or Google Sheets regularly to back it up.

---

## Full documentation

See **[SYSTEM_DOCUMENTATION.md](SYSTEM_DOCUMENTATION.md)** for the complete technical reference: every feature, every API endpoint, every data file, how the server works, detailed module descriptions, and the full data flow.

---

## License

See the individual tool folders (`DOrky/`, `LeadMapAI/`, `LeadGenPy/`, etc.) for their respective licenses. The integrated LeadFinder platform code is provided as-is for personal and commercial use.
