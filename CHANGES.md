# LeadFinder changes (17 September 2026)

## Faster
- **Shared page cache** (`leadfinder.fetch_text`). Every website download is kept for 6 hours, so the
  audit, presence check, identity check, email finder and owner finder reuse one download instead of
  fetching the same page again. Dead sites are remembered for 15 minutes, so you don't wait for the
  same timeout twice. The cache holds at most 800 pages.
- **Browser-like headers and one retry.** Fewer small-business sites block the checker. A timeout or
  reset is retried once. A 404, a refused connection or a domain that doesn't exist is not retried.
- **Email finder** reads the home page first, then fetches the contact/about pages in parallel.
- **Owner finder** fetches the About/Team pages in two parallel waves and skips the second wave when
  the first one already found a name.
- **Sending-domain check** looks up the 12 DKIM selectors in parallel.

## Safer
- A Google key (starts with `AIza`) is no longer accepted in the Hunter.io field. It is cleared on save,
  and a Hunter lookup with one gives a clear message.
- `.gitignore` added for `data/`, `__pycache__/`, logs and `kiro--analysis`.

## New (Integration release)

### New Python modules (all stdlib-only, no pip required)

- **`sheets_export.py`** — Google Sheets export (blueprint §12). Exports your full lead list,
  suppression list and blueprint config to a live Google Spreadsheet via the Sheets REST API v4.
  OAuth 2.0 Desktop-app flow: one browser consent screen on first use, then auto-refreshes.
  Endpoints: `POST /api/sheets/export`, `POST /api/sheets/config`, `GET /api/sheets/status`.

- **`imap_monitor.py`** — IMAP reply monitor (ported from OutLead). Watches your outreach inbox for
  replies from leads. Classifies each reply as: positive, unsubscribe, out-of-office or generic reply.
  Unsubscribers are automatically marked "Not interested" in My list; positive replies are promoted to
  "Interested". Uses only `imaplib` + `email`. Endpoints: `POST /api/imap/check`, `POST /api/imap/config`.

- **`pagespeed.py`** — Google PageSpeed Insights adapter (blueprint §8). Returns Core Web Vitals (LCP,
  FCP, CLS, TBT, TTI), Lighthouse category scores (Performance, SEO, Accessibility, Best Practices),
  and top actionable opportunities. No key required for basic use. Endpoints: `POST /api/pagespeed`,
  `POST /api/pagespeed/both` (mobile + desktop).

- **`webcrawler.py`** — WebCrawler integration (from WebCrawler-and-Email-Automation-System repo).
  CSE-driven keyword discovery → parallel URL scraping → email/phone/address extraction using only
  stdlib. Also provides CSV import/export compatible with OutLead, LeadMapAI and external tools.
  Endpoints: `POST /api/webcrawler/crawl`, `/scrape`, `/export-csv`, `/import-csv`, `/schedule`.

- **`dashboard.py`** — Analytics & reporting hub. Aggregates pipeline funnel, 7-day activity chart,
  source performance, email campaign stats, top opportunities by score, outreach streak, and
  AI-powered weekly summary. Endpoints: `POST /api/dashboard`, `/api/dashboard/activity`,
  `/api/dashboard/ai-summary`.

### New frontend tabs & JS

- **Dashboard tab** (`static/dashboard.js`) — Visual pipeline funnel, 7-day bar charts (calls +
  emails), source performance table, email campaign stats, API quota bars, top 10 opportunities table,
  AI weekly summary.

- **Integrations tab** (`static/integrations.js`) — Four panels:
  - Google Sheets: one-click export with OAuth setup guide.
  - Reply Monitor: IMAP check with auto-update of lead stages on positive/unsubscribe replies.
  - PageSpeed Analyzer: run Lighthouse from inside the app for any URL.
  - WebCrawler: CSE keyword crawl + batch URL scraper + CSV import from external tools.

### `window.LF` global API extended
  - `getList()` — returns the full My list array.
  - `getShown()` — returns currently filtered search results.
  - `addLeads(arr)` — adds an array of leads to My list (de-duped).
  - `updateLead(id, patch)` — patch any lead by id.
  - `saveLead(l)` — sync a lead's enrichment fields.
  - `refresh()` — re-render list and results.
  - `showTab(name)` — programmatically switch tabs.
  - `bindTab(b, cb)` — register a tab button + on-show callback.

### Settings (Free quota guard panel) extended
  - Google Custom Search API key + Search Engine ID (cx) — used by `dorking.py` and `webcrawler.py`.
  - Companies House key — used by `identity.py` for UK director lookup.
  - PageSpeed API key — optional, increases PageSpeed quota.

- `GET /api/health`: quota used, caps, last Autopilot run, and number of cached pages.

## Checked and already correct (no change needed)
- Every Google and SerpApi call, including competitor searches, already goes through the quota guard.
- OpenStreetMap leads already have `reviews: 0`, so the app-fit upgrade check works for them.

## Not in this zip
- The `data/` folder: keep your existing one. Copy it into this folder after unzipping.
- `kiro--analysis`: it contains your old API key and real business phone numbers.

# Hiring posts (new tab)

People who are already looking for a developer, checked once a day with Autopilot or when you press
**Check now**. Files: `hiring.py`, `static/hiring.js`; posts are stored in `data/hiring.json`.

**Sources.** All three are public and allow automated reading. Every post links back to its source.
- Hacker News: the latest "Freelancer? Seeking freelancer?" thread (only *SEEKING FREELANCER* posts,
  not other freelancers offering work) and "Who is hiring?", read through the official HN Algolia API.
- Remotive public API, software-dev jobs. Remotive shows jobs 24 hours late and asks you to link back
  to them and not repost their jobs elsewhere.
- We Work Remotely public RSS feeds: back-end and full-stack by default, front-end optional.

**What it does**
- Keeps only posts that mention your skills (whole-word match, so "php" doesn't match "GraphQL")
  and hides posts with excluded words (default: unpaid, equity only, internship).
- Scores each post: skill in the title +3, skill in the text +1, freelance/contract +4,
  direct email +1, posted in the last 3 days +2 (last 7 days +1).
- Optional filter: only freelance / contract work.
- Asks each source at most once every 3 hours, and forgets posts older than 30 days
  unless you saved them or replied.
- Per post: open the original, email the poster (when they gave an address), write a reply with the
  free AI pool, add to My list, save, mark replied, or dismiss.

**What it never does:** log in anywhere, read LinkedIn, Fiverr or Upwork, or send anything for you.


# Job search + Career pipeline (30 October 2026)

## Job search (new tab) — `static/jobsearch.js`, `jobsearch.py`
Find companies actively hiring developers on three sites. Every result links back to its source; nothing logs in or sends anything.
- **BeBee** (bebee.com) — free, no key. Direct scrape of job cards (they expose `data-voice-*` attributes), with your filters: country path (`/pk`), location, contract type, posted-within, remote, job type. ~20 results per search.
- **Google search** and **JobLeads** — JobLeads is behind a Cloudflare bot challenge and Google's results are JS-rendered, so both are surfaced through **SerpApi** (`engine=google`; JobLeads via a `site:jobleads.com` search). They reuse your existing SerpApi key and the monthly quota guard. BeBee works with no key.

## Career pipeline (new tab) — `static/career.js`, `career.py`
Merges the **portable** parts of the Proficiently Claude plugin (`proficiently-claude-skills/`) into LeadFinder, so the whole find-jobs → tailor-resume → cover-letter → track-applications loop runs in the app with no browser automation. All generation uses LeadFinder's free AI pool (Settings > Free AI pool).
- **Profile & preferences** (from the `setup` skill): resume text, job matching rules (target roles, must-haves, nice-to-haves, dealbreakers, salary, location, companies of interest/avoid), and a work-history profile. Stored in `data/career_profile.json`.
- **Fit scoring** (from `fit-scoring.md`): rates each job High / Medium / Low / Skip against your preferences, using the canonical dealbreakers → must-haves → nice-to-haves → rating process. Available on every Job search result and on saved applications.
- **Tailor resume** (from `tailor-resume`): generates a tailored resume for a posting using the faithful tailoring prompt (philosophy, level calibration, strict accuracy rules, no em dashes, QC checklist). Can fetch a posting from a URL. Saved per job in `data/career_jobs.json`.
- **Cover letter** (from `cover-letter`): generates a 250-350 word cover letter using the faithful writing prompt (natural voice, company-attribution lock, tense rules, QC checklist). Saved per job.
- **Job applications**: tracked list of saved jobs, each with posting / tailored resume / cover letter text you can view, edit, copy, download, and status (Saved / Applied / Interview / Offer / Rejected).

**Job search results** now have **Fit**, **Tailor resume** (saves + tailors in one click) and **Save application** buttons that feed the Career tab.

## Not ported (need a live browser / external bot a server app can't run)
- **`apply`** — filling Greenhouse / Lever / Workday application forms requires browser automation (Claude-in-Chrome / Playwright). The ATS detection and field-matching logic in `proficiently-claude-skills/shared/references/ats-patterns.md` is preserved in the repo as reference.
- **`jobsearch-telegram`** — Telegram polling + browser orchestration.
- **`network-scan`** — scanning careers pages needs a browser; `resolve-careers` is portable (a search API) but the scan step is not. Greenhouse/Lever do expose public JSON APIs that could replace the browser scan in a future update.

## New endpoints
`POST /api/jobsearch`, `/api/jobsearch/sources` · `POST /api/career/profile|fit|tailor|cover-letter|job/save|jobs|job|job/text|job/status|delete|fetch-posting`.


# UI/UX Overhaul + Remaining Features (10 November 2026)

## Design system
- **New color palette** — refined dark theme with richer depth (#0B0F16 base, #00D9A6 accent, gradient logo).
  Better contrast, more vibrant status colors, subtle glow effects.
- **Light theme** — full light mode support via `[data-theme="light"]` CSS variables. Toggle with
  the 🌙/☀️ button, Ctrl+J, or the user menu.
- **Improved sidebar** — active item has left accent bar + gradient, hover transform, gradient
  divider line, better grouping with all tabs organized (Discovery, Pipeline, Outreach,
  Intelligence, Tools, Account).
- **New components** — toast notifications, command palette, modal dialogs, skeleton loaders,
  connection status badges, user avatar, dropdown menus, glassmorphism utility.
- **Better animations** — fade-in-up on tab switches, scale-in on modals, toast slide-in/out,
  shimmer on skeletons, smooth transitions on all interactive elements.
- **Mobile responsive** — hamburger menu with sidebar overlay, touch-friendly targets,
  responsive grid breakpoints, command palette adapts to viewport.

## New features
- **Command palette (Ctrl+K)** — search tabs, leads, and actions from anywhere. Arrow-key
  navigation, Enter to execute, Esc to close. Searches My List by name/email/address.
- **Keyboard shortcuts** — G+key navigation (G→F=Find, G→L=List, G→D=Dashboard, etc.),
  Ctrl+K palette, Ctrl+J theme, Esc close dialogs.
- **Toast notifications** — success/error/warning/info toasts with auto-dismiss after 4s.
  Click to dismiss. `window.LF.toast(msg, type, title)` available to all tab modules.
  Short `alert()` calls are auto-routed to toasts.
- **Multi-user auth** — `auth.py` + `static/auth.js`. Enable in Settings. Users register/login
  with username+password. Token-based sessions (7-day TTL). First user is admin. Per-user
  sessions stored in `data/users.json` + `data/sessions.json`. API: `/api/auth/*`.
- **LinkedIn automation config** — `static/linkedin.js`. Setup guide for the Chrome extension,
  daily limits, delay range, connection note, stats display, CSV export of connections.
- **Social media outreach config** — `static/social-auto.js`. AI intent qualification (6 buyer
  categories), platform status (Threads/IG/FB/LinkedIn), interaction settings, quiet hours,
  DM templates with variable substitution.
- **Data backup/restore** — export all settings + lead list as JSON. Import to restore.
  Accessible from user menu or Settings.
- **Connection status monitor** — online/offline detection with toast notifications.
  Health dot in topbar reflects connection state.
- **User dropdown menu** — profile editing, backup/restore, theme toggle, keyboard shortcuts
  reference, about dialog, logout (when multi-user is enabled).

## System improvements
- **Nav button deduplication** — `static/ui-patch.js` now removes duplicate nav buttons created
  by dynamic JS tab modules, keeping only the pre-defined HTML buttons. Sidebar nav observer
  catches dynamically-added buttons and deduplicates them.
- **Smoother tab transitions** — CSS animation on section.page visibility change.
- **Improved card hover** — border-color transition on all cards.
- **Section animations** — `fade-in-up` animation when switching tabs.

## New files
- `auth.py` — multi-user authentication module (register, login, logout, sessions, user management)
- `static/auth.js` — login/register UI overlay, session management, token storage
- `static/linkedin.js` — LinkedIn automation config tab
- `static/social-auto.js` — social media outreach automation config tab

## Updated files
- `app.html` — enhanced CSS design system, light theme, new UI components (toast, command
  palette, modal, theme toggle, mobile menu, user dropdown), updated sidebar with all tabs,
  multi-user settings section, TAB_META additions
- `static/ui-patch.js` — nav button deduplication, sidebar nav MutationObserver
- `leadfinder.py` — auth route handlers (GET + POST) for `/api/auth/*`
