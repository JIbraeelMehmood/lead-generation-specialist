# 🚀 MASTER PLAN — Unified Advanced Lead Generation System
## Deep Analysis, Synergy Map & Merge Strategy

**Authored:** November 10, 2026  
**Scope:** 27 projects across the `leadfinder-updated-2` workspace  
**Goal:** Understand every project, map how they support each other, and define a path to merge them into the most advanced, full-stack lead generation platform possible.

---

## TABLE OF CONTENTS

1. [Executive Summary](#1-executive-summary)
2. [Project-by-Project Deep Analysis](#2-project-by-project-deep-analysis)
3. [Capability Matrix](#3-capability-matrix)
4. [How Projects Support Each Other](#4-how-projects-support-each-other)
5. [The 7-Layer Lead Generation Pipeline](#5-the-7-layer-lead-generation-pipeline)
6. [What's Missing — Enhancement Opportunities](#6-whats-missing--enhancement-opportunities)
7. [Unified System Architecture](#7-unified-system-architecture)
8. [Merge Strategy & Action Plan](#8-merge-strategy--action-plan)
9. [Technology Decisions](#9-technology-decisions)
10. [Feature Roadmap by Phase](#10-feature-roadmap-by-phase)
11. [Final Vision: The Unified Platform](#11-final-vision-the-unified-platform  )

---

## 1. EXECUTIVE SUMMARY

After deep analysis of all 27 projects, a clear picture emerges: **you already own every puzzle piece of a world-class lead generation system.** The projects span every layer of the sales pipeline — from multi-source discovery and AI-powered qualification, to automated outreach via email, phone, WhatsApp, and social media, to CRM tracking and reply automation. What they lack individually is **integration, shared state, and a unified control plane.**

**The core insight:**  
`LeadFinder` (the root-level Python server) is already the designated hub and is 70% of the way to being that unified system. The remaining 27 projects provide:
- 6 Google Maps scrapers with different technical approaches (browser extensions, Python/Playwright, Apify, Next.js, Jupyter) → consolidate into one best-of-breed scraping layer
- 2 Google Dorking engines → already merged into `dorking.py`
- 1 LinkedIn automation extension → adds a source LeadFinder doesn't have
- 2 Social/meta automation systems (Instagram, Facebook, Threads) → adds an outreach channel
- 1 AI call agent (n8n + Vapi + Twilio) → adds voice outreach LeadFinder doesn't have
- 1 B2B buyer discovery system (TypeScript, multi-market) → adds international targeting
- 1 Intent Engine (FastAPI + Celery + AI) → adds background job processing and decision-maker enrichment
- 1 Prospex / business-leads-ai-automation (NestJS + WhatsApp Baileys) → adds real WhatsApp sending
- 1 AI Lead Capture & Onboarding (n8n + Groq) → adds inbound automation
- 1 LeadGenius AI (Next.js + Gemini) → adds structured strategy generation
- Tracking, CRM, and email outreach blueprints → already absorbed

**The recommended architecture:** Keep LeadFinder as the Python orchestration core. Build a Next.js dashboard on top. Integrate the specialized tools as swappable adapters. Add the missing channels (voice calls, WhatsApp, LinkedIn) as first-class features.

---

## 2. PROJECT-BY-PROJECT DEEP ANALYSIS

### 🏗️ TIER 1 — The Core Platform (Already the Hub)

---

#### `leadfinder-updated-2/` (Root — LeadFinder)
**Type:** Full-stack local-first lead generation platform  
**Language:** Python 3.8+ (stdlib only), vanilla JS frontend  
**Status:** Most advanced single project — the designated hub  

**What it does:**
- 17-tab single-page app served from a Python HTTP server on `localhost:8765`
- Lead discovery from 3 sources: Google Maps (Places API), SerpApi, OpenStreetMap
- Website audit: HTTPS, mobile, speed, copyright age, free-builder detection
- Email finder: regex scrape of business websites and sub-pages
- 5-component evidence-backed lead scoring (Opportunity/ServiceFit/Commercial/Contactability/Confidence)
- AI email writing with 10 free-tier providers (Gemini, Groq, Ollama, etc.) with automatic failover
- Built-in CRM (browser localStorage) with pipeline stages
- Autopilot: daily job scheduler that finds new leads and deposits them in a Today inbox
- Google Dorking via CSE query templates
- Email verification: syntax → MX → SMTP mailbox check
- IMAP reply monitor with auto-stage updates
- Google Sheets export with OAuth
- Hiring monitor (HN, Remotive, WWR)
- AI career pipeline (fit scoring, resume tailoring, cover letters)
- Dashboard analytics
- Digital identity scoring + owner lookup
- PageSpeed audit integration
- WebCrawler (CSE discovery + batch scraping)
- Social outreach templates (WhatsApp, Instagram DM)

**Unique strengths:** Zero pip dependencies, runs anywhere Python 3.8 runs, shared page cache, quota guard, suppression list, 10-provider AI pool with failover, structured scoring engine.

**Gaps:** No real WhatsApp sending, no LinkedIn automation, no voice calls, no background job queue, no multi-user support, frontend is vanilla JS (no React/component framework).

---

### 🗺️ TIER 2 — Google Maps Scrapers (6 Projects)

These 6 projects all solve the same core problem — extracting Google Maps business data beyond the 60-result API cap — using different technical approaches. Each has at least one unique idea worth absorbing.

---

#### `LeadMapAI/`
**Type:** Python Streamlit app + Playwright scraper  
**Language:** Python  
**Key contribution:** Clean modular architecture (scraper/exporter/models separation). Excel + JSON export. Browser-based scraping with scroll automation.  
**Best idea to adopt:** Modular scraper architecture pattern. Excel export format.  
**Already absorbed by LeadFinder?** Partially — the architecture pattern informed the existing module structure.

---

#### `google-maps-extractor/` (Chrome Extension)
**Type:** Chrome browser extension (Manifest V3)  
**Language:** JavaScript  
**Key contribution:** Browser-side extraction — works inside the user's logged-in Google Maps session, so it gets data the API doesn't expose. Auto-pagination. Email + social profile extraction. CSV/XLSX export.  
**Best idea to adopt:** Browser-side extraction for data not available in the API (business description, owner responses to reviews, photo count). The extension approach lets you use YOUR Google session.  
**Already absorbed by LeadFinder?** No — this is a unique channel. Can be bundled as a companion extension.

---

#### `Google-Maps-Scraper-for-Lead-Generation/` (Jupyter Notebook)
**Type:** Jupyter/Colab notebook  
**Language:** Python (Selenium)  
**Key contribution:** Google Colab compatibility — anyone can run it without local setup.  
**Best idea to adopt:** Colab/hosted notebook deployment mode for onboarding new users.  
**Already absorbed by LeadFinder?** No — different deployment model.

---

#### `google-maps-leads-scraper-python/` (Apify Actor)
**Type:** Python client for an Apify cloud actor  
**Language:** Python  
**Key contribution:** **Geo-drilling** (recursive bounding box subdivision to bypass the 120-place cap), website email/social extraction, review scraping, the idea of using a cloud-hosted scraper actor.  
**Best idea to adopt:** Geo-drilling algorithm is already in LeadFinder's deep grid. Social handle extraction (Facebook, Instagram, TikTok, LinkedIn, YouTube) alongside email.  
**Already absorbed by LeadFinder?** Geo-drilling yes. Social extraction partially.

---

#### `google-maps-scraper/`
**Type:** Documentation/reference for a Go-based Maps scraper  
**Language:** Markdown + reference docs  
**Key contribution:** Extensive notes on advanced scraping (server deployment, field documentation, security).  
**Best idea to adopt:** Field documentation — systematic list of every extractable field.  
**Already absorbed by LeadFinder?** Used as reference.

---

#### `Google-Maps-Lead-Generation/` (Mapleads — Next.js)
**Type:** Full-stack Next.js web app  
**Language:** TypeScript, Next.js, MongoDB, Playwright  
**Key contribution:** **Interactive map UI** (click a point to search radius), **deep scan** (Playwright extracts data Places API doesn't expose), **Indeed job scraping** as a buying-intent signal, OpenAI-generated outreach, MongoDB lead storage, full pipeline management.  
**Best idea to adopt:** Interactive map interface (huge UX upgrade), deep scan per listing, Indeed hiring signals as intent data, MongoDB persistence vs localStorage.  
**Already absorbed by LeadFinder?** No — this is a significant UX and architecture upgrade.

---

### 🔍 TIER 3 — Google Dorking Tools (2 Projects)

---

#### `DOrky/`
**Type:** CLI tool  
**Language:** Python  
**Key contribution:** Google Custom Search API → automated dork queries → HTML report with screenshots per result.  
**Already absorbed by LeadFinder?** Yes — `dorking.py` absorbed this idea (CSE queries with key rotation).

---

#### `Google-Dorking-Automation/`
**Type:** CLI tool with CSV dork templates  
**Language:** Python  
**Key contribution:** Configurable CSV dork list with `{domain}` and `{company}` variables, multi-key rotation, company name support, quiet/verbose modes.  
**Already absorbed by LeadFinder?** Yes — `dorking.py` has 6 built-in templates and key rotation.

---

### 🤖 TIER 4 — AI-Powered Discovery & Qualification (3 Projects)

---

#### `ai-lead-generator/` (Bright Data + OpenAI + Streamlit)
**Type:** Python Streamlit app  
**Language:** Python  
**Key contribution:** Natural language lead query ("Find marketing managers in fintech in Kenya"), Bright Data for LinkedIn scraping, OpenAI for AI qualification scoring + outreach tips per lead.  
**Best idea to adopt:** **Natural language query interface** — user types what they want, AI extracts the structured filters. AI-generated per-lead outreach tips displayed inline. Debug mode showing every API call.  
**Already absorbed by LeadFinder?** No — NL query interface and per-lead AI tips are new features.

---

#### `b2b-buyer-discovery/` (TypeScript, Multi-Market B2B)
**Type:** TypeScript Node.js CLI tool  
**Language:** TypeScript  
**Key contribution:** Multi-country, multi-keyword batch search targeting B2B buyers (not just local businesses). Dual-layer scoring: rule engine (11 filters) + AI deep scoring. AI-generated bilingual outreach emails (Spanish/English for LATAM markets). 12-point composite score. WhatsApp direct links in CSV output. JSON file database with deduplication.  
**Best idea to adopt:** **B2B international buyer targeting** (vs local services focus), dual-layer scoring (rule engine first, then AI), bilingual outreach generation, WhatsApp direct links in export, intent labels (🔥price inquiry / ⭐distributor / 📧has email / 💬has WhatsApp).  
**Already absorbed by LeadFinder?** No — international B2B buyer discovery is a distinct mode.

---

#### `intent-engine/` (FastAPI + Celery + Next.js)
**Type:** Full-stack web app  
**Language:** Python (FastAPI), TypeScript (Next.js), Celery/Redis  
**Key contribution:** **Background job processing** via Celery + Redis (scrape without blocking UI), **decision-maker extraction** (LLM extracts CEO/founder name + title + tech stack from /about and /team pages), Hunter.io + Apollo fallback for email enrichment, **3-step AI cold email sequences**, CRM webhooks (Zapier, Make), Clerk authentication, per-user scrape history in PostgreSQL, proxy rotation, SMTP email validation.  
**Best idea to adopt:** Background job processing, decision-maker LLM extraction, Hunter/Apollo fallback, 3-step sequence generation, webhooks to CRM, proxy rotation.  
**Already absorbed by LeadFinder?** Decision-maker extraction partially (`identity.py`). Background jobs — no. Webhooks — no. 3-step sequences — yes (outreach tab).

---

### 📧 TIER 5 — Outreach & Email Automation (3 Projects)

---

#### `Free-email-outreach-tool/` (CogWorkLabs Blueprint)
**Type:** Reference blueprint / methodology documentation  
**Language:** Markdown  
**Key contribution:** The most comprehensive **cold email campaign methodology** in the collection: ICP definition → prospect research → validation → personalization → launch → reply classification → optimization feedback loop. Guardrails framework (sending controls, opt-out handling, reputation protection). Reference architecture table (tool stack options per layer).  
**Best idea to adopt:** The methodology itself as a guide for the outreach tab. Reply classification framework (interested/referral/objection/unsubscribe/OOO/invalid). Campaign optimization feedback loop linking open rates → reply quality → booked meetings.  
**Already absorbed by LeadFinder?** IMAP reply classification is absorbed. The full methodology framework — not explicitly.

---

#### `WebCrawler-and-Email-Automation-System/`
**Type:** Python production tool  
**Language:** Python  
**Key contribution:** Google CSE → website scraping → email extraction → CSV export → Gmail SMTP campaigns. Mode 1 (crawl) and Mode 2 (CSV import then send). Production logging.  
**Already absorbed by LeadFinder?** Yes — `webcrawler.py` absorbed this.

---

#### `OutLead/` (Full Loop: Scrape → Enrich → Verify → Score → Send → IMAP)
**Type:** Full-stack lead generation and outreach engine  
**Language:** Python (Flask), React  
**Key contribution:** The most complete **end-to-end pipeline** in the collection. Live email verification (syntax → MX → placeholder filter → SMTP mailbox check). **Two-key send gate** (both `dry_run=False` in config AND `--live` on CLI required — prevents accidental sends). Auto-stop sequence on IMAP reply. Rule-based qualifier (no LLM, instant, free). React dashboard with tactical **live map** showing businesses being pinned in real time. 3-email sequence per lead written from their actual website content. SQLite crash-resume. Suppression list checked before every single send.  
**Best idea to adopt:** Two-key send gate philosophy. Live map view. AI email writing from the lead's actual website data. SMTP mailbox verification is already in `emailverify.py`.  
**Already absorbed by LeadFinder?** Email verification yes. The map view — no. The send gate concept — partially.

---

### 📱 TIER 6 — Social Media & Multi-Platform Automation (3 Projects)

---

#### `linkedin-autopilot/` (Chrome Extension)
**Type:** Chrome browser extension (Manifest V3)  
**Language:** JavaScript  
**Key contribution:** Automated LinkedIn connection growth — 1-click connect via `/mynetwork/grow/`, infinite suggestion loading, 24-hour sleep mode when weekly limit is hit, anti-ban randomized delays (8-16s), human pointer event simulation, 100% client-side.  
**Best idea to adopt:** LinkedIn as a lead discovery AND outreach channel. The technical pattern (CDP + human simulation) for LinkedIn is unique.  
**Already absorbed by LeadFinder?** No — LinkedIn automation is completely absent from LeadFinder.

---

#### `meta-automation/` + `meta-automation-branch-1/` (Agentic Social Automation)
**Type:** Autonomous social media agent  
**Language:** Node.js  
**Key contribution:** Most sophisticated social automation in the collection. Autonomous agent with principal awareness (reads `founder.md`, `company.md`, `services.md` as source of truth). Selector-free DOM (uses accessibility tree, never CSS). CDP cloaking + Bezier mouse + jitter typing. Platforms: Threads, Instagram, Facebook, LinkedIn. AI intent qualification (6 buyer categories, strict disqualification of recruiters/job seekers/out-of-scope). 3-tier AI fallback (local → cloud → rule engine). Android Termux support (24/7 mobile daemon). Freelancer.com proposal engine. Portfolio card generator.  
**Best idea to adopt:** Principal-awareness architecture (source-of-truth knowledge base files). Selector-free DOM approach. AI intent qualification categories. Multi-platform coverage. Android/mobile operation mode.  
**Already absorbed by LeadFinder?** No — social media automation is completely absent.

---

#### `Client-Koi/` (Browser Extension)
**Type:** Chrome browser extension (side panel)  
**Language:** JavaScript  
**Key contribution:** Side panel extension for lead research. Built documentation site (docs/). Animation assets.  
**Best idea to adopt:** Side panel UX pattern for lead research while browsing.  
**Already absorbed by LeadFinder?** No.

---

### 📞 TIER 7 — Voice & Workflow Automation (2 Projects)

---

#### `n8n-ai-call-agent/`
**Type:** n8n workflow + Vapi + Twilio  
**Language:** n8n visual workflow  
**Key contribution:** **AI voice agent that calls leads, holds a real conversation, extracts email from speech, writes transcript+summary to Google Sheets, Slack notification on every call.** Handles no-answer gracefully. Status polling loop. Email extraction from spoken words ("tugui dragos at gmail dot com" → clean address). 25-node workflow tested on 100+ real leads. GoHighLevel full version books appointments automatically.  
**Best idea to adopt:** Voice outreach as a channel (many local businesses ignore email but answer the phone). Email extraction from speech transcript. Slack notifications on call outcomes. The pattern of AI calling before human follow-up.  
**Already absorbed by LeadFinder?** No — voice outreach is completely absent.

---

#### `AI-Lead-Capture-Onboarding/` (n8n + Groq + Gmail)
**Type:** n8n workflow  
**Language:** n8n visual workflow  
**Key contribution:** Inbound lead capture automation. Form submission → Google Sheets logging → AI-written personalized welcome email (Groq Llama 3.1) → Gmail send. Fully automated onboarding for anyone who signs up via a form.  
**Best idea to adopt:** **Inbound capture pipeline** — when a prospect fills a form or responds to outreach, automatically log them and send a personalized onboarding sequence. This flips LeadFinder from outbound-only to outbound+inbound.  
**Already absorbed by LeadFinder?** No — inbound automation is absent.

---

### 🏢 TIER 8 — CRM, Intelligence & Full-Stack Platforms (5 Projects)

---

#### `business-leads-ai-automation/` (Prospex — Full SaaS Platform)
**Type:** Full production SaaS platform  
**Language:** TypeScript (NestJS + Next.js), PostgreSQL + pgvector, Redis, BullMQ  
**Key contribution:** The most feature-complete platform in the collection (after LeadFinder). Multi-workspace, multi-user. **Real WhatsApp sending via Baileys** (linked device, not Business API). Human approval before every message. Rate limiting (10/hour, 80/day). Quiet hours. STOP handling. AI style learning from WhatsApp exports. Marketing brief from websites. Knowledge base (pgvector). Lead map (coordinates → province/city/district). Multi-source scraping (Google Maps + Overture Maps + OpenStreetMap). Official WhatsApp Business Cloud API planned. Email channel via SMTP. Pipeline tracking to closing. Reply understanding (interested/meeting/price/question/referral/not-now/not-interested).  
**Best idea to adopt:** **WhatsApp as a real sending channel (Baileys integration)**. AI style learning from chat exports. Marketing brief generation from your website. Knowledge base for AI drafts. Multi-workspace architecture. Reply classification into 7 categories. STOP permanent suppression.  
**Already absorbed by LeadFinder?** LeadFinder has WhatsApp template generation but no actual WhatsApp sending. Prospex's Baileys integration is the key addition.

---

#### `leadgenius-ai/` (Next.js + Gemini)
**Type:** Next.js web app  
**Language:** TypeScript, Next.js 15, Google GenAI SDK  
**Key contribution:** Structured workflow: business profile intake → Magic Auto-Fill (Gemini fills form from plain English) → AI strategy generation (business model, 30-day plan, 90-day scaling) → lead discovery → qualification labels (Hot/Warm/Cold) → CSV export → outreach templates → final report. Role-based login (admin/member).  
**Best idea to adopt:** **Structured strategy generation** (30-day plan, 90-day scaling path). Magic Auto-Fill pattern (describe your business in plain English, AI fills the structured form). Revenue potential framing in reports.  
**Already absorbed by LeadFinder?** No — strategy generation and business model analysis are absent.

---

#### `local-leads-finder/` (Python + Decodo API)
**Type:** Python CLI + Flask web app  
**Language:** Python  
**Key contribution:** Decodo Web Scraping API integration (proxy-backed scraping service), real-time progress display, batch city processing, clean CLI interface.  
**Best idea to adopt:** Batch city processing CLI pattern, Decodo as a proxy-backed alternative source.  
**Already absorbed by LeadFinder?** Partially — batch processing exists in niche finder.

---

#### `my-lead-finder-crm/`
**Type:** Full-stack CRM concept (Blazor WASM + .NET + EF Core)  
**Language:** C# / Blazor  
**Key contribution:** Enterprise CRM architecture concept: unlimited lead extraction, FIFO batch handling, cloud deployment (Azure/GCP), Entity Framework persistence.  
**Best idea to adopt:** FIFO queue pattern for batch processing, cloud deployment architecture.  
**Already absorbed by LeadFinder?** No — but it's C# which doesn't fit the Python stack.

---

#### `lead-tracker/`
**Type:** Single-file HTML/CSS/JS lead tracker  
**Language:** Vanilla JavaScript  
**Key contribution:** Minimal, zero-dependency, browser-only lead tracker. Pipeline stages, live stats bar (total/win rate), search + filter, CSV export, localStorage.  
**Best idea to adopt:** The simplicity principle — a lightweight embeddable tracker that works in any browser with no backend.  
**Already absorbed by LeadFinder?** Yes — My List tab implements the same concept.

---

### 🎓 TIER 9 — Career & Job Intelligence (1 Project)

---

#### `proficiently-claude-skills/` (Claude Code Plugin)
**Type:** Claude Code plugin  
**Language:** Markdown skill files  
**Key contribution:** Complete job search pipeline: setup → job search → tailor resume → cover letter → network scan → apply (Greenhouse/Lever/Workday). Telegram bot loop. ATS navigation patterns. Fit scoring framework. LinkedIn contacts network scan.  
**Already absorbed by LeadFinder?** Yes — `career.py` absorbed the core skills (profile, fit, tailor, cover letter, tracker). Browser automation parts not absorbed (require Claude in Chrome).

---

#### `LeadGenPy/`
**Type:** Python tool  
**Language:** Python (Selenium + OpenAI)  
**Key contribution:** Google Maps extraction → ChatGPT personalized email generation → Google Sheets integration → SMTP send. 5 modes of operation (extract / view / sheets / generate email / full production pipeline).  
**Best idea to adopt:** Google Sheets as a live collaborative CRM (OAuth2 write). The 5-mode operation concept.  
**Already absorbed by LeadFinder?** Google Sheets export yes. The combined extract→AI→sheets→send single-command pipeline — not as a single flow.

---

## 3. CAPABILITY MATRIX

| Capability | Projects That Have It | Best Implementation |
|---|---|---|
| **Google Maps scraping (API)** | LeadFinder, Google-Maps-Lead-Generation, local-leads-finder | LeadFinder (deep grid, 3 sources) |
| **Google Maps scraping (browser)** | LeadMapAI, google-maps-extractor, Google-Maps-Scraper-for-Lead-Generation, OutLead, business-leads-ai-automation, Mapleads | OutLead (Playwright + stealth + crash-resume) |
| **Google Maps deep data (beyond API)** | Mapleads (deep scan), google-maps-extractor (extension) | Mapleads deep scan via Playwright |
| **Google Dorking** | DOrky, Google-Dorking-Automation, LeadFinder | LeadFinder (absorbed both) |
| **LinkedIn automation** | linkedin-autopilot, meta-automation | meta-automation (most advanced) |
| **Social media automation** | meta-automation, business-leads-ai-automation | meta-automation (Threads/FB/IG/LinkedIn) |
| **B2B international discovery** | b2b-buyer-discovery, ai-lead-generator | b2b-buyer-discovery (multi-market, bilingual) |
| **Email verification** | OutLead, emailverify.py (LeadFinder), intent-engine | LeadFinder emailverify.py (SMTP check) |
| **Decision-maker extraction** | intent-engine, LeadFinder (identity.py) | intent-engine (LLM from about/team pages) |
| **AI email writing** | LeadFinder (10 providers), business-leads-ai-automation, OutLead, b2b-buyer-discovery, intent-engine, LeadGenius | LeadFinder (10-provider pool with failover) |
| **3-step email sequences** | OutLead, intent-engine, LeadFinder (outreach tab) | intent-engine / OutLead (best structure) |
| **WhatsApp automation** | business-leads-ai-automation (Baileys), LeadFinder (templates only) | business-leads-ai-automation (real sending) |
| **Voice call automation** | n8n-ai-call-agent | n8n-ai-call-agent (Vapi + Twilio) |
| **Inbound lead capture** | AI-Lead-Capture-Onboarding | AI-Lead-Capture-Onboarding (n8n workflow) |
| **Lead scoring** | LeadFinder (5-component), b2b-buyer-discovery (12-point), Prospex (0-100), intent-engine | LeadFinder (most comprehensive) |
| **CRM pipeline** | LeadFinder, Prospex, Mapleads, OutLead, lead-tracker | Prospex (most stages, reply handling) |
| **Reply monitoring** | LeadFinder (IMAP), OutLead (IMAP), Prospex (WhatsApp+email) | Prospex (multi-channel reply reading) |
| **Background jobs** | intent-engine (Celery+Redis), Prospex (BullMQ+Redis) | Prospex (BullMQ pattern) |
| **Google Sheets CRM export** | LeadFinder, LeadGenPy | LeadFinder (OAuth2 export) |
| **Dashboard analytics** | LeadFinder, Prospex, OutLead | Prospex (most comprehensive) |
| **Multi-user / workspace** | Prospex | Prospex |
| **Strategy generation** | LeadGenius AI | LeadGenius AI (30/90 day plans) |
| **Career pipeline** | proficiently-claude-skills, LeadFinder | LeadFinder (absorbed) |
| **Hiring signals (Indeed)** | Mapleads (Indeed scraper), LeadFinder (hiring tab) | Mapleads (buying intent signal) |
| **Docker deployment** | Prospex, OutLead, local-leads-finder, intent-engine | Prospex (most complete compose) |

---

## 4. HOW PROJECTS SUPPORT EACH OTHER

The 27 projects form natural dependency chains. When mapped against the full lead generation pipeline, each project plugs a specific gap:

```
╔══════════════════════════════════════════════════════════════════════════════════════╗
║                     THE COMPLETE LEAD GENERATION PIPELINE                           ║
║                                                                                      ║
║  DISCOVER → QUALIFY → ENRICH → SCORE → OUTREACH → TRACK → CLOSE → REPEAT           ║
╚══════════════════════════════════════════════════════════════════════════════════════╝

DISCOVER (finding leads)
├── Google Maps API ............... LeadFinder (3 sources, deep grid)
├── Browser-based Maps scraping ... LeadMapAI → OutLead → google-maps-extractor
├── International B2B buyers ...... b2b-buyer-discovery (multi-market)
├── LinkedIn prospects ............. linkedin-autopilot → meta-automation
├── Social media .................. meta-automation (Threads, FB, IG)
├── Google Dorking ................ LeadFinder/dorking.py (absorbed DOrky + GDA)
├── Web Crawling ................... LeadFinder/webcrawler.py (absorbed WebCrawler repo)
├── Indeed hiring signals ......... Mapleads (buying intent), LeadFinder/hiring.py
└── Inbound (forms) ............... AI-Lead-Capture-Onboarding (n8n workflow)
           │
           ▼ feeds common Lead record into...
           
QUALIFY (is this lead worth pursuing?)
├── Rule-based scoring ............ OutLead (11-rule instant engine)
├── AI deep scoring ............... b2b-buyer-discovery (OpenAI/DeepSeek)
├── Buying intent detection ........ meta-automation (6 buyer categories)
├── Fit scoring ................... LeadGenius AI (Hot/Warm/Cold labels)
├── 5-component blueprint score ... LeadFinder/opportunities.py
└── NL query filtering ............ ai-lead-generator (Bright Data + OpenAI)
           │
           ▼ qualified leads go into...
           
ENRICH (get contact data + context)
├── Email finder .................. LeadFinder/find_emails() + emailverify.py
├── Decision-maker extraction ...... intent-engine/llm_extractor.py
├── Hunter.io fallback ............ intent-engine, LeadFinder/contacts.py
├── Apollo.io fallback ............ intent-engine
├── Social profiles (FB/IG/TikTok)  google-maps-leads-scraper-python
├── Website audit ................. LeadFinder/audit_site(), pagespeed.py
├── Digital identity score ........ LeadFinder/identity.py
├── Owner lookup .................. LeadFinder/identity.py (+ Companies House)
├── Tech stack detection .......... intent-engine/scraper.py
└── Bilingual outreach prep ........ b2b-buyer-discovery (ES/EN)
           │
           ▼ enriched leads go into...
           
OUTREACH (making contact)
├── Cold email (AI-written) ....... LeadFinder/outreach tab (10-provider AI pool)
├── 3-step email sequence ......... intent-engine, OutLead, LeadFinder
├── WhatsApp sending .............. business-leads-ai-automation (Baileys)
├── WhatsApp templates ............ LeadFinder/social tab (copy-paste)
├── Voice calls ................... n8n-ai-call-agent (Vapi + Twilio)
├── LinkedIn connections .......... linkedin-autopilot
├── Social media comments/DMs ..... meta-automation (Threads/FB/IG/LinkedIn)
├── Inbound welcome email ......... AI-Lead-Capture-Onboarding
└── Freelance proposals ........... meta-automation (Freelancer.com engine)
           │
           ▼ outreach tracked in...
           
TRACK (CRM and pipeline)
├── Full CRM pipeline ............. LeadFinder/My list (localStorage)
├── Multi-user CRM ................ business-leads-ai-automation (PostgreSQL)
├── Reply classification .......... LeadFinder/IMAP, Prospex (7 categories)
├── WhatsApp reply reading ........ business-leads-ai-automation
├── Sequence auto-stop ............ OutLead (IMAP), Prospex (WhatsApp)
├── Call transcripts .............. n8n-ai-call-agent (Google Sheets)
├── Google Sheets sync ............ LeadFinder/sheets_export.py, LeadGenPy
├── Dashboard analytics ........... LeadFinder/dashboard.py, Prospex
└── Simple browser tracker ........ lead-tracker (zero-dep HTML)
           │
           ▼ closed deals feed...
           
STRATEGY & OPTIMIZATION
├── Strategy generation ........... LeadGenius AI (30/90 day plans)
├── Niche/city analysis ........... LeadFinder/niche finder tab
├── Campaign optimization ......... Free-email-outreach-tool (methodology)
├── A/B sequence analysis ......... Prospex (opening variant tracking)
└── Career parallel track ......... proficiently-claude-skills (absorbed)
```

### Key Synergy Relationships

**LeadFinder ↔ OutLead:**  
OutLead's `emailverify.py` logic (SMTP mailbox check) is already absorbed into LeadFinder. OutLead's two-key send gate philosophy should inform LeadFinder's outreach safety model. OutLead's live map view complements LeadFinder's list view.

**LeadFinder ↔ intent-engine:**  
intent-engine's Celery background jobs solve LeadFinder's main architectural weakness (all operations are synchronous, blocking the UI). Its decision-maker LLM extraction is deeper than LeadFinder's `identity.py`. Its Hunter/Apollo fallback adds contacts LeadFinder can't find itself.

**LeadFinder ↔ business-leads-ai-automation (Prospex):**  
Prospex adds the two most important missing channels: real WhatsApp sending and multi-user workspaces. Its Baileys integration, reply understanding, and pipeline-to-close tracking are the most sophisticated in the collection.

**LeadFinder ↔ n8n-ai-call-agent:**  
Voice outreach is completely absent from every project except n8n-ai-call-agent. Local businesses (the core target market) ignore email but answer the phone. This integration adds the highest-ROI missing channel.

**LeadFinder ↔ meta-automation:**  
Social media lead discovery and outreach are absent from LeadFinder. meta-automation's AI intent qualification (filtering real buyers from recruiters/spam) adds signal quality. Its principal-awareness architecture (knowledge base files) is the right model for a personalized agent.

**LeadFinder ↔ b2b-buyer-discovery:**  
LeadFinder targets local service businesses (plumbers, restaurants). b2b-buyer-discovery targets international product buyers (mining equipment, industrial goods). They target different markets but share the same pipeline infrastructure. Adding a "B2B Buyer Mode" to LeadFinder doubles the addressable market.

**AI-Lead-Capture-Onboarding ↔ everything:**  
Currently everything is outbound (you go find leads). The n8n inbound capture workflow flips this — when someone responds or signs up, they get logged and auto-nurtured. This completes the loop from outbound discovery to inbound conversion.

---

## 5. THE 7-LAYER LEAD GENERATION PIPELINE

After mapping all 27 projects, the full pipeline has 7 layers. Here is what each layer currently has, what's the best implementation, and what's missing:

| Layer | Have | Best Source | Missing |
|---|---|---|---|
| **1. Discovery** | Google Maps (3 modes), Dorking, WebCrawler, OSM | LeadFinder | LinkedIn discovery, Social media discovery, International B2B buyer mode |
| **2. Qualification** | 5-component score, AI scoring, rule engine | LeadFinder + OutLead | NL query interface, intent signal from hiring posts |
| **3. Enrichment** | Email find, verify, audit, identity, owner | LeadFinder + intent-engine | Decision-maker LLM extraction, Apollo fallback, tech stack detection |
| **4. Outreach** | Email (AI-written), templates, SMTP send | LeadFinder + intent-engine | WhatsApp sending, Voice calls, LinkedIn automation, Social DMs |
| **5. Tracking** | CRM pipeline, IMAP replies, Sheets export | LeadFinder + Prospex | Multi-user, WhatsApp replies, call log, background jobs |
| **6. Conversion** | Pipeline stages, notes, follow-up dates | LeadFinder | Appointment booking, deal value tracking, revenue reporting |
| **7. Optimization** | Dashboard, activity log, source performance | LeadFinder + Prospex | Strategy generation, A/B outreach testing, campaign analytics |

---

## 6. WHAT'S MISSING — ENHANCEMENT OPPORTUNITIES

Based on the gap analysis, these are the highest-impact features that **none or very few** of the 27 projects fully implement:

### 🔴 Critical Gaps (High Impact, Currently Absent)

1. **Real WhatsApp Sending Channel**  
   Currently: templates only (copy-paste). Needed: Baileys linked-device integration.  
   Source: business-leads-ai-automation's WhatsApp sender.  
   Impact: 3-5x higher response rates vs email for local businesses.

2. **Background Job Processing**  
   Currently: all operations block the UI thread. Needed: async job queue.  
   Source: intent-engine (Celery+Redis) or Prospex (BullMQ+Redis).  
   Impact: can run 1,000-lead enrichment jobs overnight.

3. **Voice Call Channel**  
   Currently: absent. Needed: AI voice agent for initial contact.  
   Source: n8n-ai-call-agent (Vapi + Twilio).  
   Impact: highest-ROI outreach for businesses that ignore email.

4. **LinkedIn Lead Discovery & Outreach**  
   Currently: absent. Needed: profile scraping + connection automation.  
   Source: linkedin-autopilot + meta-automation.  
   Impact: access to decision-makers not on Google Maps.

5. **Inbound Lead Automation**  
   Currently: 100% outbound. Needed: form capture → auto-log → AI welcome.  
   Source: AI-Lead-Capture-Onboarding (n8n workflow).  
   Impact: converts inbound interest automatically, 24/7.

### 🟡 Important Gaps (Medium Impact)

6. **Interactive Map Discovery UI**  
   Currently: text search only. Needed: click on map to search radius.  
   Source: Mapleads (react-google-maps + radius circle UI).

7. **Decision-Maker LLM Extraction**  
   Currently: regex-based owner finder. Needed: LLM over /about + /team pages.  
   Source: intent-engine/llm_extractor.py.

8. **B2B International Buyer Mode**  
   Currently: local service businesses only. Needed: global product buyer discovery.  
   Source: b2b-buyer-discovery (multi-market, bilingual).

9. **Deep Lead Scan (Beyond API Data)**  
   Currently: Places API data. Needed: owner response rate, description, photos.  
   Source: Mapleads deep scan (Playwright extracts what API doesn't expose).

10. **AI Strategy Generation**  
    Currently: absent. Needed: 30-day plan, 90-day scaling, revenue potential.  
    Source: LeadGenius AI.

### 🟢 Nice-to-Have Gaps

11. Natural language query interface (ai-lead-generator approach)
12. Per-lead AI outreach tips shown inline in results
13. Social media automation for organic discovery (meta-automation)
14. Proxy rotation for high-volume scraping
15. Multi-workspace / multi-user support
16. Webhook delivery to external CRMs (Zapier/Make)
17. Android/mobile operation mode (Termux, meta-automation)
18. Marketing brief generation from your own website

---

## 7. UNIFIED SYSTEM ARCHITECTURE

The proposed unified architecture keeps LeadFinder as the Python backend core, adds a modern React/Next.js frontend, and integrates the specialized tools as adapters:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                     UNIFIED LEAD INTELLIGENCE PLATFORM                          │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                        REACT DASHBOARD (Next.js)                         │   │
│  │  Map View │ Pipeline │ Outreach │ Analytics │ Strategy │ Settings        │   │
│  └────────────────────────────────┬─────────────────────────────────────────┘   │
│                                   │ REST API / WebSocket                         │
│  ┌────────────────────────────────▼─────────────────────────────────────────┐   │
│  │                    PYTHON ORCHESTRATION CORE (LeadFinder)                │   │
│  │                                                                           │   │
│  │  DISCOVERY LAYER          ENRICHMENT LAYER       OUTREACH LAYER          │   │
│  │  ├─ Google Places API     ├─ emailverify.py       ├─ SMTP email          │   │
│  │  ├─ SerpApi               ├─ contacts.py          ├─ WhatsApp (Baileys)  │   │
│  │  ├─ OpenStreetMap         ├─ identity.py          ├─ Voice (Vapi/Twilio) │   │
│  │  ├─ dorking.py            ├─ opportunities.py     ├─ LinkedIn adapter    │   │
│  │  ├─ webcrawler.py         └─ pagespeed.py         └─ Social adapter      │   │
│  │  └─ [NEW] B2B buyer mode                                                 │   │
│  │                                                                           │   │
│  │  INTELLIGENCE LAYER       TRACKING LAYER          AUTOMATION LAYER       │   │
│  │  ├─ ai_pool.py (10 LLMs) ├─ pipeline.py          ├─ assistant.py        │   │
│  │  ├─ [NEW] LLM decisions  ├─ imap_monitor.py      ├─ [NEW] job queue     │   │
│  │  └─ [NEW] strategy gen   ├─ sheets_export.py     └─ [NEW] n8n webhooks  │   │
│  │                           └─ dashboard.py                                │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                   │                                              │
│  ┌────────────────────────────────▼─────────────────────────────────────────┐   │
│  │                     ADAPTER LAYER (Pluggable)                            │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │  WhatsApp   │  │  Voice Call  │  │   LinkedIn    │  │   Social    │  │   │
│  │  │  (Baileys)  │  │(Vapi+Twilio) │  │   Autopilot   │  │  Agentic   │  │   │
│  │  │  from       │  │  from        │  │   Chrome Ext  │  │  meta-auto  │  │   │
│  │  │  Prospex    │  │  n8n workflow│  │   from L-AP   │  │  Node.js   │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  └─────────────┘  │   │
│  │                                                                           │   │
│  │  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  ┌─────────────┐  │   │
│  │  │   Inbound   │  │  Background  │  │  B2B Buyer    │  │  Decision   │  │   │
│  │  │   Capture   │  │  Job Queue   │  │  Discovery    │  │  Maker      │  │   │
│  │  │  (n8n flow) │  │(Celery/Redis)│  │  (b2b-buyer)  │  │  Extractor  │  │   │
│  │  └─────────────┘  └──────────────┘  └───────────────┘  └─────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐   │
│  │                    STORAGE LAYER                                          │   │
│  │  SQLite (leads, sequences, pipeline) │ Redis (jobs, cache) │ JSON files  │   │
│  │  Optional: PostgreSQL (multi-user)   │ localStorage (browser CRM)        │   │
│  └──────────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 8. MERGE STRATEGY & ACTION PLAN

The merge strategy follows a **Hub-and-Spoke model**:
- LeadFinder is the hub (keeps its zero-dependency philosophy for core features)
- Specialized projects are spokes (opt-in adapters — installed separately, connected via API)
- No project is force-merged in a way that breaks the "run with just Python" promise

### PHASE 1 — Foundation Hardening (Weeks 1-2)
**Goal:** Make LeadFinder production-grade before adding features.

- [ ] **1.1** Replace localStorage CRM with SQLite persistence (`leads.db`)  
  Source: OutLead's SQLite pattern (additive migrations, crash-resume, stage status)  
  Why: localStorage is lost on browser clear; SQLite survives reboots and supports multi-tab

- [ ] **1.2** Add WebSocket support for real-time UI updates  
  Source: OutLead's live map (live event stream)  
  Why: long-running tasks (batch enrichment, autopilot) need progress feedback without polling

- [ ] **1.3** Upgrade to async background jobs  
  Source: intent-engine's Celery pattern (or simpler: Python `concurrent.futures` + task queue)  
  Why: bulk email finding and site audits block the UI; must run in background

- [ ] **1.4** Add two-key send gate  
  Source: OutLead's send gate philosophy  
  Why: accidental mass-email sends are catastrophic; require explicit confirmation + config flag

- [ ] **1.5** Migrate frontend to React (or at minimum add a component layer)  
  Source: LeadGenius AI, Mapleads (Next.js patterns)  
  Why: vanilla JS becomes unmaintainable at 17+ tabs; React components enable reuse

---

### PHASE 2 — Discovery Expansion (Weeks 2-3)
**Goal:** Add the missing lead sources.

- [ ] **2.1** Add interactive map discovery UI  
  Source: Mapleads (`@vis.gl/react-google-maps`, radius circle, bottom sheet results)  
  Implementation: new `/tools/map-discovery` page with click-to-search, existing Places API

- [ ] **2.2** Add LinkedIn lead discovery  
  Source: linkedin-autopilot Chrome extension  
  Implementation: package as a companion extension; LeadFinder receives leads via local HTTP POST

- [ ] **2.3** Add B2B international buyer mode  
  Source: b2b-buyer-discovery TypeScript tool  
  Implementation: new "B2B Buyer Hunt" tab with multi-market search, dual-layer scoring, bilingual export

- [ ] **2.4** Add social media discovery  
  Source: meta-automation's Threads/Facebook/LinkedIn scanner  
  Implementation: adapter that posts qualified leads to LeadFinder via webhook

- [ ] **2.5** Add Playwright deep scan  
  Source: Mapleads `mapsScraper.js`  
  Implementation: opt-in "Deep Scan" per lead — extracts description, owner response rate, photo count, review text

- [ ] **2.6** Add Indeed hiring signal integration  
  Source: Mapleads `indeed.js`  
  Implementation: existing `hiring.py` already monitors HN/Remotive/WWR; add Indeed as a 4th source with company data fed back to lead discovery

---

### PHASE 3 — Enrichment Upgrade (Week 3)
**Goal:** Get deeper, more accurate contact data.

- [ ] **3.1** Add LLM decision-maker extraction  
  Source: intent-engine/llm_extractor.py  
  Implementation: enhance `identity.py` — after regex owner finder, run an LLM pass over /about + /team pages  
  Prompt: extract CEO, Founder, Owner name, job title from page text

- [ ] **3.2** Add Hunter.io domain search + Apollo fallback  
  Source: intent-engine/enrichment.py  
  Implementation: when email not found by scraping, call Hunter `/domain-search` endpoint, then Apollo as fallback

- [ ] **3.3** Add tech stack detection  
  Source: intent-engine/scraper.py (Wappalyzer-style fingerprinting)  
  Implementation: check response headers + HTML for known signatures (WordPress, Shopify, GA4, FB Pixel)

- [ ] **3.4** Add social handle extraction  
  Source: google-maps-leads-scraper-python (Facebook, Instagram, TikTok, LinkedIn, YouTube)  
  Implementation: extend `find_emails()` to also extract social links from business websites

- [ ] **3.5** Add AI strategy brief generation  
  Source: LeadGenius AI (Gemini strategy generation)  
  Implementation: new "Strategy" tab — input business type + city → AI generates 30-day plan + package recommendations

---

### PHASE 4 — Outreach Channels (Weeks 3-4)
**Goal:** Add the missing high-ROI outreach channels.

- [ ] **4.1** Add real WhatsApp sending (Baileys)  
  Source: business-leads-ai-automation's WhatsApp sender  
  Implementation: Python bridge to Node.js Baileys process via local HTTP  
  Safety: human approval before every message, rate limits (10/hour, 80/day), quiet hours, STOP handling

- [ ] **4.2** Add AI voice call agent  
  Source: n8n-ai-call-agent (Vapi + Twilio)  
  Implementation: LeadFinder calls n8n webhook with lead phone number + campaign context; call result (transcript, email extracted, interest level) written back to lead record

- [ ] **4.3** Add LinkedIn outreach  
  Source: linkedin-autopilot + meta-automation  
  Implementation: companion Chrome extension; LeadFinder queues LinkedIn connection requests; extension executes them when user opens LinkedIn

- [ ] **4.4** Add social media DM and comment outreach  
  Source: meta-automation  
  Implementation: adapter mode — LeadFinder exports leads with social profiles; meta-automation's social agents pick them up

- [ ] **4.5** Add inbound lead capture workflow  
  Source: AI-Lead-Capture-Onboarding (n8n)  
  Implementation: expose a webhook endpoint in LeadFinder; when anyone fills a form or responds via any channel, POST to this endpoint → logs lead → triggers AI welcome email

---

### PHASE 5 — Intelligence & Automation (Week 4+)
**Goal:** Make the system self-improving and autonomous.

- [ ] **5.1** Add principal-awareness architecture  
  Source: meta-automation's knowledge base pattern  
  Implementation: `.leadfinder/knowledge/` folder with `about.md` (your business), `services.md` (what you offer), `style.md` (your writing voice) — all AI email writing reads from these

- [ ] **5.2** Add AI style learning  
  Source: Prospex (AI Style from WhatsApp exports)  
  Implementation: upload your own email conversations; AI learns your voice for drafts

- [ ] **5.3** Add campaign optimization feedback loop  
  Source: Free-email-outreach-tool methodology  
  Implementation: track open/reply/meeting rate per campaign; dashboard shows which sequences/segments/niches produce booked conversations

- [ ] **5.4** Add marketing brief generation  
  Source: Prospex's Marketing Brief feature  
  Implementation: input your website URL → AI reads all pages → generates who-you-are, what-you-offer, what's-proven brief used in all outreach

- [ ] **5.5** Add CRM webhook delivery  
  Source: intent-engine webhooks  
  Implementation: when a lead reaches "Interested" or "Proposal Sent" stage, POST to Zapier/Make webhook for HubSpot, Salesforce, GoHighLevel, Pipedrive

- [ ] **5.6** Add multi-user workspace support  
  Source: Prospex (workspace isolation)  
  Implementation: JWT-based auth, per-user data isolation, team sharing mode

---

## 9. TECHNOLOGY DECISIONS

### What to Keep (from LeadFinder)
- Python backend (stdlib-only for core)
- Zero-pip-dependency philosophy for base installation
- 10-provider AI pool with failover
- Quota guard system
- 5-component scoring engine
- IMAP/SMTP integration
- Google Sheets OAuth export
- Suppression/do-not-contact enforcement

### What to Add
- **SQLite** for lead persistence (replacing localStorage CRM)
- **Redis** for background job queue (optional, only needed for heavy workloads)
- **React/Next.js** for the frontend (replacing vanilla JS)
- **WebSockets** for real-time job progress
- **Baileys** (Node.js WhatsApp library) as an optional service
- **Playwright** (optional) for deep scans and social automation

### Architecture Principle: Layered Optionality

```
TIER 0 — Zero dependencies
  python3 leadfinder.py  → discovery, scoring, email writing, CRM
  
TIER 1 — Optional: SQLite persistence  
  pip install nothing — SQLite is in Python stdlib
  
TIER 2 — Optional: Playwright scraping
  playwright install chromium  → deep scans, Playwright Maps scraping
  
TIER 3 — Optional: WhatsApp channel
  npm install baileys  → real WhatsApp sending
  
TIER 4 — Optional: Voice channel
  n8n + Vapi + Twilio account  → AI voice calls
  
TIER 5 — Optional: Background jobs
  redis-server + pip install celery  → async job processing
  
TIER 6 — Optional: Full cloud deployment
  Docker + PostgreSQL + pgvector  → multi-user, production scale
```

This means a freelancer can run Tier 0 on their laptop for free, while an agency can deploy Tier 6 on a cloud server for the team.

---

## 10. FEATURE ROADMAP BY PHASE

### Phase 1 — Production Foundation (2 weeks)
| Feature | From | Priority |
|---|---|---|
| SQLite lead persistence | OutLead | 🔴 Critical |
| WebSocket real-time updates | OutLead | 🔴 Critical |
| Background job queue | intent-engine | 🔴 Critical |
| Two-key send gate | OutLead | 🔴 Critical |
| React frontend migration | Mapleads / LeadGenius AI | 🟡 High |
| Docker deployment config | Prospex / intent-engine | 🟡 High |

### Phase 2 — Discovery Expansion (2 weeks)
| Feature | From | Priority |
|---|---|---|
| Interactive map UI (click-to-search) | Mapleads | 🟡 High |
| Playwright deep scan per listing | Mapleads | 🟡 High |
| B2B international buyer mode | b2b-buyer-discovery | 🟡 High |
| LinkedIn companion extension | linkedin-autopilot | 🟡 High |
| Social media discovery adapter | meta-automation | 🟢 Medium |
| Indeed hiring signal source | Mapleads | 🟢 Medium |

### Phase 3 — Enrichment Upgrade (1 week)
| Feature | From | Priority |
|---|---|---|
| LLM decision-maker extraction | intent-engine | 🟡 High |
| Hunter.io + Apollo fallback | intent-engine | 🟡 High |
| Tech stack detection | intent-engine | 🟢 Medium |
| Social handle extraction | google-maps-leads-scraper | 🟢 Medium |
| AI strategy brief generation | LeadGenius AI | 🟢 Medium |

### Phase 4 — Outreach Channels (2 weeks)
| Feature | From | Priority |
|---|---|---|
| Real WhatsApp sending (Baileys) | Prospex | 🔴 Critical |
| AI voice call agent | n8n-ai-call-agent | 🟡 High |
| LinkedIn outreach extension | linkedin-autopilot | 🟡 High |
| Inbound lead capture webhook | AI-Lead-Capture-Onboarding | 🟡 High |
| Social DM/comment outreach | meta-automation | 🟢 Medium |

### Phase 5 — Intelligence & Automation (2 weeks)
| Feature | From | Priority |
|---|---|---|
| Principal-awareness knowledge base | meta-automation | 🟡 High |
| AI style learning | Prospex | 🟡 High |
| Campaign optimization feedback loop | Free-email-outreach-tool | 🟡 High |
| Marketing brief generation | Prospex | 🟢 Medium |
| CRM webhook delivery | intent-engine | 🟢 Medium |
| Multi-user workspace | Prospex | 🟢 Medium |

---

## 11. FINAL VISION: THE UNIFIED PLATFORM

When all phases are complete, the unified system will be:

```
╔═══════════════════════════════════════════════════════════════════════════════════╗
║          UNIFIED ADVANCED LEAD INTELLIGENCE PLATFORM — FINAL VISION              ║
╠═══════════════════════════════════════════════════════════════════════════════════╣
║                                                                                   ║
║  DISCOVER LEADS FROM EVERYWHERE                                                   ║
║  ✓ Google Maps (API + deep scan)   ✓ OpenStreetMap (free)                        ║
║  ✓ Google Dorking (6 templates)    ✓ LinkedIn profiles                           ║
║  ✓ Social media (Threads/FB/IG)    ✓ B2B international buyers                   ║
║  ✓ Indeed hiring signals           ✓ Inbound form captures                       ║
║  ✓ Web crawling (CSE)              ✓ Interactive map click-to-search             ║
║                                                                                   ║
║  QUALIFY WITH AI INTELLIGENCE                                                     ║
║  ✓ 5-component evidence-backed score (0–100)                                     ║
║  ✓ AI intent qualification (real buyer vs noise)                                 ║
║  ✓ Decision-maker LLM extraction from about/team pages                           ║
║  ✓ Tech stack detection                                                           ║
║  ✓ Dual-layer scoring: rule engine + AI deep analysis                             ║
║  ✓ Hot/Warm/Cold labels with reasoning                                           ║
║                                                                                   ║
║  ENRICH WITH VERIFIED CONTACT DATA                                                ║
║  ✓ Email finder + SMTP mailbox verification                                      ║
║  ✓ Hunter.io + Apollo.io fallback                                                ║
║  ✓ Owner/founder name extraction                                                  ║
║  ✓ Social profiles (FB/IG/TikTok/LinkedIn)                                       ║
║  ✓ WhatsApp numbers + direct links                                               ║
║  ✓ Full website audit + PageSpeed                                                ║
║  ✓ Digital identity score (10 components)                                        ║
║                                                                                   ║
║  REACH OUT THROUGH EVERY CHANNEL                                                  ║
║  ✓ Cold email (AI-written, 10-provider pool, 3-step sequences)                   ║
║  ✓ WhatsApp (Baileys, human approval, rate-limited, STOP-aware)                  ║
║  ✓ Voice calls (Vapi + Twilio, AI conversation, transcript → CRM)               ║
║  ✓ LinkedIn (connection + message automation)                                     ║
║  ✓ Social DMs & comments (Threads, Facebook, Instagram)                          ║
║  ✓ Inbound welcome automation (form → AI email → CRM)                            ║
║                                                                                   ║
║  TRACK EVERY INTERACTION                                                          ║
║  ✓ Full CRM pipeline (New → Won) with SQLite persistence                         ║
║  ✓ IMAP reply monitoring with auto-stage updates                                 ║
║  ✓ WhatsApp reply reading and classification                                     ║
║  ✓ Call transcript logging and interest scoring                                  ║
║  ✓ Sequence auto-stop on reply/unsubscribe                                       ║
║  ✓ Suppression list (permanent opt-out enforcement)                              ║
║  ✓ Google Sheets export + live sync                                              ║
║                                                                                   ║
║  OPTIMIZE WITH INTELLIGENCE                                                       ║
║  ✓ Dashboard: pipeline funnel, activity charts, source performance               ║
║  ✓ Strategy generation: 30-day plan, 90-day scaling, revenue potential          ║
║  ✓ AI marketing brief from your own website                                      ║
║  ✓ AI style learning from your own writing                                       ║
║  ✓ Campaign optimization: open → reply → meeting → won feedback loop            ║
║  ✓ CRM webhooks to HubSpot, Salesforce, GoHighLevel, Pipedrive                  ║
║                                                                                   ║
║  RUN ANYWHERE, SCALE TO ANY SIZE                                                  ║
║  ✓ Tier 0: python3 leadfinder.py (zero dependencies)                             ║
║  ✓ Tier 3: +WhatsApp (npm install baileys)                                       ║
║  ✓ Tier 6: Docker + PostgreSQL + pgvector (multi-user cloud)                     ║
║  ✓ Android/Termux 24/7 mobile operation                                          ║
║                                                                                   ║
║  SAFETY BY DESIGN                                                                 ║
║  ✓ Two-key send gate (can't mass-email by accident)                              ║
║  ✓ Monthly API quota guard (no surprise charges)                                 ║
║  ✓ Per-channel rate limits (WhatsApp, email, voice)                              ║
║  ✓ Permanent suppression list (opt-outs respected forever)                       ║
║  ✓ Human approval before every WhatsApp message                                  ║
║  ✓ Dry-run mode that changes nothing                                             ║
║  ✓ STOP handling on every channel                                                ║
║                                                                                   ║
╚═══════════════════════════════════════════════════════════════════════════════════╝
```

### Why This System Would Be Best-in-Class

| Competing SaaS Tool | Monthly Cost | What This Platform Has That They Don't |
|---|---|---|
| Apollo.io | $49–$149/mo | Voice calls, WhatsApp, social automation, local map search |
| Instantly.ai | $37–$97/mo | Multi-channel (not email-only), lead discovery, map view |
| Hunter.io | $34–$408/mo | Full pipeline, outreach, CRM, voice, WhatsApp |
| Waalaxy | $30–$80/mo | Email + WhatsApp + voice, not just LinkedIn |
| GoHighLevel | $97–$297/mo | No SaaS fee, runs on your machine, your data |
| Prospex (Prospex) | Hosted fee | Zero pip, runs locally, 10 AI providers free |

**Combined monthly cost of equivalent tools: $300–$800/mo**  
**Cost of this unified platform: $0 (open source, runs locally)**

---

## QUICK REFERENCE: PROJECT → FEATURE MAPPING

| Feature to Build | Primary Source | Secondary Source | Integration Effort |
|---|---|---|---|
| SQLite leads db | OutLead/storage/ | LeadMapAI/models/ | 🟢 Low |
| WebSocket updates | OutLead/core/ | — | 🟢 Low |
| Background jobs | intent-engine/tasks.py | Prospex BullMQ | 🟡 Medium |
| Interactive map UI | Mapleads/app/ | LeadGenius UI | 🟡 Medium |
| Deep scan (Playwright) | Mapleads/lib/ | OutLead/scraper/ | 🟡 Medium |
| LLM decision maker | intent-engine/llm_extractor.py | — | 🟢 Low |
| Hunter/Apollo fallback | intent-engine/enrichment.py | — | 🟢 Low |
| WhatsApp sending | Prospex/apps/api/ | — | 🔴 High |
| Voice call agent | n8n-ai-call-agent workflow | — | 🟡 Medium |
| LinkedIn extension | linkedin-autopilot/ | meta-automation/platforms/ | 🟡 Medium |
| Social automation | meta-automation/ | — | 🔴 High |
| Inbound capture | AI-Lead-Capture-Onboarding/ | — | 🟢 Low |
| B2B buyer mode | b2b-buyer-discovery/src/ | — | 🟡 Medium |
| Strategy generation | leadgenius-ai/app/ | — | 🟢 Low |
| AI style learning | Prospex/apps/api/src/style/ | — | 🟡 Medium |
| CRM webhooks | intent-engine/app/main.py | — | 🟢 Low |
| Marketing brief | Prospex/docs/marketing-brief | — | 🟡 Medium |
| Docker deployment | Prospex/docker-compose.yml | intent-engine/docker-compose | 🟢 Low |
| Multi-user workspace | Prospex architecture | — | 🔴 High |

---

*This document was generated from deep analysis of all 27 projects in the leadfinder-updated-2 workspace on November 10, 2026.*

*Next step: Begin Phase 1 implementation — SQLite persistence, WebSocket updates, and background job queue.*







What was implemented
  
  New modules created / activated
  
  db.py — SQLite persistence layer (was written but not wired)
  - 5 tables: leads, outreach_log, sequences, tasks, events
  - Full CRUD for the CRM, outreach log, 3-step sequences, background task queue, SSE event bus
  - Now initialized at server startup via db.init() and jobs.start()
  
  jobs.py — Background job worker (was written but not wired)
  - 4-thread pool, polls SQLite queue every 2 seconds
  - Handles: bulk_enrich, bulk_audit, bulk_score, decision_maker, b2b_hunt, send_sequence
  - Publishes SSE events at every step for live frontend progress
  
  enrich.py — Advanced enrichment (was written but not wired)
  - Social handles (7 platforms), tech stack (20 signatures), quick/LLM decision-maker extraction, Hunter.io, Apollo.io
  fallback, full pipeline
  
  b2b.py — B2B buyer discovery (was written but not wired)
  - Multi-country search, dual-layer scoring, bilingual email generation
  
  strategy.py — NEW module created from scratch
  - Magic Auto-Fill, 30/90-day plan, ICP, lead sources, qualification criteria, revenue potential, marketing brief from
  your website
  
  Wired into leadfinder.py
  
  6 new route groups: /api/db/*, /api/jobs/*, /api/enrich/*, /api/b2b/*, /api/strategy/*, GET /api/events/stream (SSE
  stream)
  
  New frontend
  - static/b2b.js — B2B Buyer Hunt tab with live SSE progress bar, results table, email draft modal, CSV export
  - static/strategy.js — Strategy tab with auto-fill, full plan display, marketing brief, saved strategies list
  - Two new nav buttons added to app.html
  
  Documentation created
  
  IMPLEMENTATION_STATUS.md — 250-line tracking document covering every feature from MASTER_PLAN.md: what's ✅ implemented
  (with module name + API endpoints), what's ❌ still to do (with phase + source project), plus a full capability matrix
  and prioritized next steps.
 


  What was just built
  
  1. inbound.py + static/inbound.js — Inbound Lead Capture
  
  Ported from the n8n workflow (all 4 nodes in pure Python): form trigger → SQLite log → AI welcome email (identical system
  prompt to the Groq agent) → SMTP send. Field normaliser maps 20+ webhook field aliases (Typeform, Tally, Webflow,
  GoHighLevel). Webhook URL POST /api/inbound/webhook accepts any JSON payload. Reply classifier with 6 categories built
  in. Tab shows manual capture form, webhook URL to copy, reply classifier, config panel, recent leads list.
  
  2. knowledge.py + static/knowledgebase.js — Knowledge Base
  
  Ported from meta-automation's KnowledgeEngine.js: reads .leadfinder/knowledge/*.md with mtime-based caching (re-reads
  every 2s if changed). Files: about.md, founder.md, services.md, style.md, lead-rules.md. Parsers extract structured
  founder info, company info, approved/excluded services. build_system_prompt() injects all files into every AI call.
  Bootstrap creates 5 example files on first run. Tab has file editor, structured info view, AI prompt preview.
  
  3. webhooks.py + wired into campaigns.js — CRM Webhooks
  
  Ported from intent-engine's webhook_delivery.py + webhook_store.py but using JSON instead of Redis. Stage triggers:
  lead_interested, lead_won, lead_new, inbound_captured, sequence_sent, b2b_hunt_done. Monkey-patches db.update_lead_field
  so stage changes auto-fire webhooks. Payload is HubSpot/Zapier/Make compatible. Test delivery button. Last 200 delivery
  attempts logged in memory.
  
  4. indeed.py — Indeed Hiring Signals
  
  Ported from Mapleads indeed.js: two modes — HTTP fallback (stdlib only, works immediately) and Playwright mode (optional,
  full browser). Same CSS selectors, same anti-bot jitter delays, same 403-retry logic. Cross-references job company names
  against your lead pipeline — companies in your pipeline that are hiring get flagged in_pipeline: true. API:
  /api/indeed/search, /api/indeed/score.
  
  5. campaign.py + static/campaigns.js — Campaign Optimization
  
  Built from scratch from the Free-email-outreach-tool methodology. Tracks: sends, opens, replies, interested, referrals,
  objections, unsubscribes, bounces, meetings, won — per campaign, variant, and segment. Reply classifier with keyword
  patterns + AI fallback. Auto-stops sequences on reply. Auto-fires webhooks on positive reply and won. Computed rates:
  reply_rate, positive_rate, meeting_rate, win_rate. Actionable insights generated from metric thresholds.
  
  6. static/mapview.js — Interactive Map Discovery UI
  
  Ported from Mapleads page.js but in vanilla JS using the Google Maps JavaScript API. Click anywhere → drops pin → draws
  radius circle → opens search panel. Keyword, radius slider (1–50 km), source selector, filters (hasWebsite, noWebsite,
  hasPhone, openNow, minRating, minReviews). Results in expandable bottom sheet. Per-lead Enrich button calls
  /api/enrich/full. Add to My List saves to SQLite. Location autocomplete via Places API.
  
  Remaining ❌ items (genuinely require external services or separate installs): Real WhatsApp/Baileys, AI voice calls
  (Vapi+Twilio), LinkedIn Chrome extension, Playwright deep scan, multi-user workspace, Docker.
 

 6 features built
  
  whatsapp_bridge.py + static/whatsapp.js Full WhatsApp bridge with the complete Prospex send policy ported from
  TypeScript: hourly limit (10/hr), daily limit (80/day), quiet hours (22:00–08:00), random gap between sends, typing delay
  proportional to message length, human approval queue, STOP opt-out detection → permanent suppression. Auto-scaffolds the
  Node.js whatsapp_bridge/server.js on first run. QR code display for device linking. Setup: cd whatsapp_bridge && npm
  install && node server.js, then scan QR.
  
  voice_agent.py + static/voice.js Two modes: n8n workflow mode (POST lead data to your n8n trigger URL, n8n handles
  Vapi+Twilio) and Vapi direct API mode (builds inline assistant from your knowledge base). Email extraction from speech
  transcripts (handles "john at gmail dot com"). Auto-updates lead stage and fires webhooks on call outcomes. Accepts
  result callbacks from n8n/Vapi.
  
  style_learning.py + static/style.js Learns your writing voice from examples you paste. Import from WhatsApp chat exports
  (extracts only your messages). AI analyzes examples and writes a style profile to .leadfinder/knowledge/style.md — which
  is then read by every AI email draft. get_style_instructions() returns a one-line style description for prompt injection.
  
  deepscan.py Playwright deep scan for Google Maps listings (description, photo count, owner responses) and business
  websites (visits /about, /contact, /team pages in parallel). HTTP fallback always works with zero installs — Playwright
  is optional. pip install playwright && playwright install chromium to unlock full mode.
  
  Dockerfile + docker-compose.yml + docker-start.sh Multi-stage Docker build (Node.js WhatsApp bridge + Python app).
  Volumes persist data/, .wa-auth/, .leadfinder/knowledge/. Healthcheck on /api/health. Passes Google/SerpApi keys as env
  vars. Run with docker compose up -d → open http://localhost:8765.
  
  IMPLEMENTATION_STATUS.md updated — only one item remains ❌: multi-user workspace (requires JWT auth + per-user data
  isolation, an architectural change). Everything else from the MASTER_PLAN is now ✅ or 🔧 (LinkedIn/social automation
  source exists in the repo, just needs Chrome extension packing).
  
  Final counts: 33 Python modules, 23 JS tabs, 24 API route groups.
 
 All tests pass. Let me update the session status and provide a summary.Here's everything I implemented:
  
  Remaining Features Implemented
  
  Multi-user workspace (auth.py + static/auth.js)
  - Register/login/logout with username + password
  - Token-based sessions (7-day TTL, auto-extend)
  - First user becomes admin, subsequent users are members
  - Enable/disable in Settings → Multi-User Workspace section
  - Login overlay appears when multi-user is enabled
  - User dropdown shows logout option when authenticated
  - API: /api/auth/status, /enable, /disable, /register, /login, /logout, /verify, /users
  
  LinkedIn automation (static/linkedin.js)
  - Setup guide for Chrome extension installation
  - Configurable daily limits, delay range, connection note, filter by role
  - Connection stats display and CSV export
  - Integrates with the linkedin-autopilot/ reference repo
  
  Social media outreach (static/social-auto.js)
  - Platform status for Threads, Instagram, Facebook, LinkedIn
  - AI intent qualification with 6 buyer categories (configurable)
  - Interaction settings: daily limit, delays, quiet hours, action type
  - DM template with variable substitution ({name}, {topic}, {your_name})
  - Integrates with the meta-automation/ reference repo
  
  System & Functionality Improvements
  
  Command palette (Ctrl+K) — search tabs, leads, and actions from anywhere. Arrow-key navigation, Enter to execute.
  
  Toast notifications — success/error/warning/info toasts with 4s auto-dismiss. window.LF.toast() available to all modules.
  Short alert() calls auto-routed to toasts.
  
  Keyboard shortcuts — G+key tab navigation (G→F=Find, G→L=List, etc.), Ctrl+K palette, Ctrl+J theme toggle, Esc to close.
  
  Data backup/restore — export all settings + lead list as JSON, import to restore.
  
  Connection monitoring — online/offline detection with toast notifications.
  
  Nav button deduplication — ui-patch.js removes duplicate nav buttons created by dynamic JS tab modules, keeping the
  pre-organized HTML sidebar.
  
  Modal system — reusable dialog for profile, shortcuts, about.
  
  Mobile responsive — hamburger menu with sidebar overlay, touch-friendly.
  
  Design & Color Scheme
  
  Dark theme — refined palette: deeper base (#0B0F16), vibrant teal accent (#00D9A6), gradient logo, glow effects, better
  contrast on status colors.
  
  Light theme — full light mode via CSS variables. Toggle with button, Ctrl+J, or user menu. Persists to localStorage.
  
  New UI components — toast container, command palette overlay, modal dialogs, skeleton loaders, connection badges, user
  avatar, dropdown menus, glassmorphism utility.
  
  Improved sidebar — active item has left accent bar + gradient, hover transform effect, gradient divider line, all 22 tabs
  organized in 6 groups (Discovery, Pipeline, Outreach, Intelligence, Tools, Account).
  
  Animations — fade-in-up on tab switches, scale-in on modals, toast slide animations, shimmer on skeletons, smooth
  transitions throughout.
  
  Topbar — mobile menu button, theme toggle, command palette button, health indicator, user avatar dropdown (Profile,
  Backup, Restore, Theme, Shortcuts, About, Logout).
  
  Files
  
  ┌──────────────────────────┬─────────┬──────────────────────────────────────────────────────────────────────────────┐
  │ File                     │ Action  │ Description                                                                  │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ auth.py                  │ New     │ Multi-user auth module                                                       │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ static/auth.js           │ New     │ Login/register UI overlay                                                    │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ static/linkedin.js       │ New     │ LinkedIn automation config tab                                               │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ static/social-auto.js    │ New     │ Social outreach automation config tab                                        │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ app.html                 │ Updated │ CSS redesign, light theme, all new UI components, sidebar reorganization,    │
  │                          │         │ multi-user settings, TAB_META additions                                      │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ static/ui-patch.js       │ Updated │ Nav button dedup + sidebar observer                                          │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ leadfinder.py            │ Updated │ Auth routes (GET + POST for /api/auth/*)                                     │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ IMPLEMENTATION_STATUS.md │ Updated │ Status reflects new features                                                 │
  ├──────────────────────────┼─────────┼──────────────────────────────────────────────────────────────────────────────┤
  │ CHANGES.md               │ Updated │ Changelog entry for this update                                              │
  └──────────────────────────┴─────────┴──────────────────────────────────────────────────────────────────────────────┘
  
  The only remaining ❌ is React frontend migration (deferred — vanilla JS works well and all new features follow the same
  pattern) and a few Phase 2 items (interactive map UI, Playwright deep scan) that require external dependencies.
 



 How to Run LeadFinder
  
  Prerequisites
  
  - Python 3.8 or newer (check with python3 --version)
  - No pip installs needed — everything uses Python standard library
  
  Start the Server
  
  cd "/home/lenovo/Downloads/MY AI---LEAD-ASSITANT/LeadFinder/leadfinder-updated-2"
  python3 leadfinder.py
  
  Your browser opens to http://localhost:8765. Press Ctrl+C in the terminal to stop.
  
  Options:
  
  # Different port
  LEADFINDER_PORT=9000 python3 leadfinder.py
  
  # Don't open browser
  python3 leadfinder.py --no-browser
  
  # Pre-load API keys
  GOOGLE_PLACES_API_KEY="AIza..." python3 leadfinder.py
  SERPAPI_KEY="your-key" python3 leadfinder.py
  
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  
  Which APIs You Need
  
  Required (pick at least one for lead discovery)
  
  ┌─────────────────────────┬─────────────────────────┬───────────────────┬──────────────────────────────────────────┐
  │ API                     │ Cost                    │ What it gives you │ How to get                               │
  ├─────────────────────────┼─────────────────────────┼───────────────────┼──────────────────────────────────────────┤
  │ OpenStreetMap           │ Free, no key            │ Business names,   │ Nothing — works out of the box           │
  │                         │                         │ addresses, some   │                                          │
  │                         │                         │ phones/websites   │                                          │
  ├─────────────────────────┼─────────────────────────┼───────────────────┼──────────────────────────────────────────┤
  │ Google Places API (New) │ Free tier + paid        │ Best data: name,  │ console.cloud.google.com                 │
  │                         │                         │ phone, website,   │ (https://console.cloud.google.com) →     │
  │                         │                         │ rating, reviews,  │ create project → enable billing → enable │
  │                         │                         │ coordinates       │ "Places API (New)" → create API key      │
  ├─────────────────────────┼─────────────────────────┼───────────────────┼──────────────────────────────────────────┤
  │ SerpApi                 │ 100 free searches/month │ Same Google Maps  │ serpapi.com (https://serpapi.com) → sign │
  │                         │                         │ data without      │ up → get API key                         │
  │                         │                         │ Google Cloud      │                                          │
  │                         │                         │ account           │                                          │
  └─────────────────────────┴─────────────────────────┴───────────────────┴──────────────────────────────────────────┘
  
  Optional (unlock specific features)
  
  ┌────────────────────────────┬──────────────────┬──────────────────────────────────────────────────────────────────┐
  │ API                        │ What it unlocks  │ How to get                                                       │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Google Gemini (free)       │ AI cold email    │ aistudio.google.com/apikey (https://aistudio.google.com/apikey)  │
  │                            │ writing          │ → create key (30 seconds)                                        │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Groq (free)                │ AI email writing │ console.groq.com/keys (https://console.groq.com/keys)            │
  │                            │ (faster)         │                                                                  │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Ollama (free, local)       │ AI email writing │ Install from ollama.com (https://ollama.com), run ollama pull    │
  │                            │ offline          │ llama3.2                                                         │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Google CSE (Custom Search) │ Google Dorking + │ Enable Custom Search API in Google Cloud → create key → go to    │
  │                            │ WebCrawler       │ cse.google.com (https://cse.google.com) → create search engine   │
  │                            │ discovery        │ with * → copy CX ID                                              │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Hunter.io                  │ Email pattern    │ hunter.io (https://hunter.io) → free tier available              │
  │                            │ lookup for       │                                                                  │
  │                            │ domains          │                                                                  │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Google PageSpeed           │ Website          │ Same Google Cloud key as Places, or free without key (limited)   │
  │                            │ performance      │                                                                  │
  │                            │ audit reports    │                                                                  │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Companies House            │ UK business      │ developer-companies-house                                        │
  │                            │ owner/director   │ (https://developer.company-information.service.gov.uk)           │
  │                            │ lookup           │                                                                  │
  ├────────────────────────────┼──────────────────┼──────────────────────────────────────────────────────────────────┤
  │ Apollo.io                  │ Decision-maker   │ apollo.io (https://apollo.io) → free tier                        │
  │                            │ contact fallback │                                                                  │
  └────────────────────────────┴──────────────────┴──────────────────────────────────────────────────────────────────┘
  
  For Outreach (sending emails)
  
  ┌─────────────────────────┬─────────────────────────────────────────────────────────────────────────────────────────┐
  │ What                    │ How                                                                                     │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ SMTP (send emails)      │ Any Gmail/Outlook/SMTP server. For Gmail: use an App Password                           │
  │                         │ (https://myaccount.google.com/apppasswords), not your main password                     │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ IMAP (monitor replies)  │ Gmail: Settings → Forwarding and POP/IMAP → Enable IMAP → create App Password           │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ Google Sheets (export)  │ Enable Google Sheets API in Cloud Console → create OAuth Desktop client → download      │
  │                         │ credentials.json                                                                        │
  ├─────────────────────────┼─────────────────────────────────────────────────────────────────────────────────────────┤
  │ WhatsApp (real sending) │ Requires Node.js + Baileys (linked device). Setup guide in the WhatsApp tab             │
  └─────────────────────────┴─────────────────────────────────────────────────────────────────────────────────────────┘
  
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  
  Step-by-Step Usage Guide
  
  Step 1 — First-Time Setup (5 minutes)
  
  1. Start the server: python3 leadfinder.py
  2. Browser opens to http://localhost:8765
  3. Go to Settings (⚙️ in sidebar, bottom)
  4. Paste your API keys:
    - Google Places key → "Google Places API Key" field
    - SerpApi key → "SerpApi Key" field
    - CSE key + CX → "Google Custom Search Key" + "Custom Search Engine ID"
  
  5. Click Save All Settings
  6. Set your name and business name (used in AI-generated emails)
  
  Step 2 — Configure Free AI (for email writing)
  
  1. Go to Today tab (📅 in sidebar → Outreach group)
  2. Find the Free AI Pool section
  3. Click Add Provider
  4. Choose a provider:
    - Gemini (recommended) — paste your free Google AI Studio key
    - Groq — paste your free Groq key
    - Ollama — no key needed, just make sure it's running (ollama serve)
  
  5. Click Save and Test
  6. You can add multiple providers — if one rate-limits, the next is used automatically
  
  Step 3 — Find Leads
  
  1. Go to Find Leads (🔍 in sidebar)
  2. Choose a source:
    - Google Maps — best data, needs API key
    - SerpApi — same data, no Google Cloud needed
    - OpenStreetMap — free, no key (limited website data)
  
  3. Enter:
    - Business type: e.g., "plumber", "dentist", "restaurant"
    - Location: e.g., "Austin TX", "Leeds UK", "Karachi PK"
  
  4. Choose filter:
    - No website only — best prospects (businesses with no online presence)
    - No website + weak sites — also includes businesses with bad websites
    - All businesses — everything
  
  5. For Google Maps, choose search depth:
    - Normal (up to 60 results)
    - Deep 4 areas (240+)
    - Deeper 9 areas (540+) — uses more API quota
  
  6. Click Search
  
  Step 4 — Work the Results
  
  For each lead in the results table:
  
  - Score (0-100) — higher = better prospect. No website + many reviews = established business missing online presence
  - Click Find email (📧) — scrapes the business website for email addresses
  - Click Audit (🔎) — checks the website: HTTPS, mobile-friendly, speed, SEO, outdated design
  - Click Analyze (⚡) — full competitor analysis, labels as Hot/Warm/Low
  - Click Add (➕) — adds to My List CRM
  
  Bulk actions (toolbar above results):
  - Analyze best targets — analyzes top N leads against competitors
  - Find all emails — bulk email scrape (5 parallel workers)
  - Audit all sites — bulk website audit
  - Add all to list — add every visible result to CRM
  - CSV — export visible results
  
  Step 5 — Manage Your Pipeline (My List)
  
  1. Go to My List (📋 in sidebar)
  2. See the tally bar: total leads, not contacted, follow-ups due, warm leads, won
  3. For each lead you can:
    - Search by name, address, email
    - Filter by stage
    - Change stage: New → Contacted → No answer → Interested → Follow up → Proposal sent → Won → Not interested
    - Set Follow-up date (turns red when overdue)
    - Add Notes
    - Delete (✕)
  
  4. Import CSV from external tools (OutLead, LeadMapAI, etc.)
  5. Export CSV for backup
  
  Step 6 — Score Opportunities
  
  1. Go to Opportunities (💎 in sidebar → Pipeline group)
  2. Click Analyze My list
  3. Each lead gets a 5-component score (0-100):
    - Opportunity (30 pts) — website issues found
    - Service fit (20 pts) — how well they need web design
    - Commercial (20 pts) — review count and rating
    - Contactability (15 pts) — phone + verified email
    - Confidence (15 pts) — data source quality
  
  4. Score bands: Review first (80+) → Normal review (65+) → Nurture (50+) → Skip (<50)
  5. Each lead gets a recommended package: 3-page refresh ($349), 5-page professional ($699), 8-page growth ($999)
  6. Export CSV with all scores
  
  Step 7 — Write & Send Cold Emails
  
  1. Go to Email Outreach (✉️ in sidebar → Outreach group)
  2. Select a lead from your list
  3. Choose:
    - Template — niche-specific templates auto-fill business name, city, issues
    - AI Writer — generates a personalized cold email using the lead's real data
  
  4. Edit the email as needed
  5. Build a 3-step sequence (initial + 2 follow-ups)
  6. To send via SMTP:
    - Enter SMTP credentials (Gmail: use App Password, port 587)
    - Click Send
    - The system uses a two-key send gate — both dry_run=False in config AND explicit send required
  
  Step 8 — Monitor Replies
  
  1. Go to Integrations (🔗 in sidebar → Tools group)
  2. Reply Monitor (IMAP) section:
    - Enter IMAP server (e.g., imap.gmail.com)
    - Enter your email and App Password
    - Click Check now
  
  3. The system scans your inbox for replies and classifies them:
    - Positive → auto-promotes lead to "Interested" stage
    - Unsubscribe → auto-marks as "Not interested" + adds to suppression list
    - Out of office → logged, no action
    - Generic reply → logged for manual review
  
  Step 9 — Use Autopilot (Daily Lead Generation)
  
  1. Go to Today tab (📅 in sidebar)
  2. Autopilot jobs section:
    - Click Add job
    - Enter niche + city + source + filter + min reviews
    - Save
  
  3. The autopilot runs every day at 8am (configurable):
    - Runs all saved searches
    - Filters out leads you've already seen
    - Filters out suppressed domains
    - Deposits new leads in your Today inbox
  
  4. Review the inbox → Accept (add to My List) or Dismiss
  5. Set Monthly caps to prevent surprise API charges (default: 900 Google, 90 SerpApi)
  
  Step 10 — Track Everything on the Dashboard
  
  1. Go to Dashboard (📈 in sidebar → Tools group)
  2. See:
    - Pipeline funnel — leads at each stage
    - Activity chart — daily calls, emails, new leads (past 30 days)
    - Source performance — which discovery source produces the most wins
    - Top opportunities — highest-scoring leads not yet won
    - Streak — consecutive days with activity
    - AI weekly summary — AI-generated paragraph of your week's activity
  
  Step 11 — Export to Google Sheets
  
  1. Go to Integrations → Google Sheets
  2. Enter path to your credentials.json (from Google Cloud OAuth)
  3. Click Export
  4. First time: browser opens for Google consent
  5. Exports 3 tabs: Leads, Suppressed domains, Blueprint config
  
  ─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────
  
  Quick Reference — Keyboard Shortcuts
  
  ┌──────────┬────────────────────────────────────────────────────┐
  │ Shortcut │ Action                                             │
  ├──────────┼────────────────────────────────────────────────────┤
  │ Ctrl+K   │ Open command palette (search tabs, leads, actions) │
  ├──────────┼────────────────────────────────────────────────────┤
  │ Ctrl+J   │ Toggle dark/light theme                            │
  ├──────────┼────────────────────────────────────────────────────┤
  │ Esc      │ Close any dialog                                   │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then F │ Go to Find Leads                                   │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then L │ Go to My List                                      │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then D │ Go to Dashboard                                    │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then S │ Go to Settings                                     │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then O │ Go to Email Outreach                               │
  ├──────────┼────────────────────────────────────────────────────┤
  │ G then B │ Go to B2B Buyer Hunt                               │
  └──────────┴────────────────────────────────────────────────────┘
  
  Free Path (Zero Cost)
  
  If you want to use LeadFinder without spending any money:
  
  1. Use OpenStreetMap as source (free, no key)
  2. Install Ollama for AI email writing (ollama pull llama3.2)
  3. Use Gmail App Password for SMTP sending (free)
  4. Skip Google Sheets export — use CSV export instead
  
  This gives you lead discovery + email writing + email sending + CRM pipeline, all for free.
 