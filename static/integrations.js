/* LeadFinder: Integrations tab
   - Google Sheets export
   - IMAP reply monitor
   - PageSpeed analyzer
   - WebCrawler (CSE + batch scrape)
*/
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const api = (p, b) => window.LF.api(p, b || {});

// ---------------------------------------------------------------- mount
function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-integrations"; sec.hidden = true;
  sec.innerHTML = `
  <!-- ========================= GOOGLE SHEETS ========================= -->
  <div class="panel">
    <h2>Google Sheets Export</h2>
    <p class="sub" style="margin-top:-4px">Export your full lead list, suppression list and blueprint config to a Google Spreadsheet. Creates a new sheet on first use, then overwrites it on subsequent exports.</p>
    <div class="grid">
      <div>
        <label for="sheetsCredsPath">Path to credentials.json</label>
        <input id="sheetsCredsPath" placeholder="/home/you/Downloads/credentials.json">
        <p class="note">Download from <a href="https://console.cloud.google.com/apis/credentials" target="_blank" rel="noopener">Google Cloud Console</a> → Credentials → your Desktop app OAuth client → Download JSON.</p>
      </div>
      <div>
        <label for="sheetsTitle">Spreadsheet title</label>
        <input id="sheetsTitle" value="LeadFinder Export">
      </div>
      <div><button class="btn primary" id="sheetsExport" style="width:100%;margin-top:20px">Export to Google Sheets</button></div>
    </div>
    <div id="sheetsMsg"></div>
    <div id="sheetsStatus" class="sub" style="margin-top:8px"></div>
    <details style="margin-top:10px"><summary class="sub">Setup instructions</summary>
      <ol class="guide" style="font-size:13px">
        <li>Go to <a href="https://console.cloud.google.com" target="_blank" rel="noopener">Google Cloud Console</a> and create (or select) a project.</li>
        <li>Enable the <b>Google Sheets API</b> (APIs &amp; Services → Library → search "Google Sheets API").</li>
        <li>Go to APIs &amp; Services → Credentials → Create Credentials → <b>OAuth client ID</b>.</li>
        <li>Application type: <b>Desktop app</b>. Download the JSON and note its path.</li>
        <li>On first export, a browser window opens for you to authorize. Subsequent exports use a saved token.</li>
        <li>Also add <code>http://localhost:28765/</code> to the OAuth client's Authorized redirect URIs.</li>
      </ol>
    </details>
  </div>

  <!-- ========================= IMAP REPLY MONITOR ========================= -->
  <div class="panel">
    <h2>Reply Monitor (IMAP)</h2>
    <p class="sub" style="margin-top:-4px">Watch your outreach inbox for replies. Positive replies and unsubscribe requests are detected and shown here so you can act on them without missing one.</p>
    <div class="grid">
      <div><label for="imapHost">IMAP server</label><input id="imapHost" placeholder="imap.gmail.com"></div>
      <div><label for="imapEmail">Your email</label><input id="imapEmail" type="email"></div>
      <div><label for="imapPass">Password / App password</label><input id="imapPass" type="password" autocomplete="off"></div>
      <div><label for="imapDays">Look back (days)</label><input id="imapDays" type="number" value="7" min="1" max="90"></div>
      <div><button class="btn primary" id="imapCheck" style="width:100%;margin-top:20px">Check replies</button></div>
      <div><button class="btn" id="imapSave" style="width:100%;margin-top:20px">Save config</button></div>
    </div>
    <div id="imapMsg"></div>
    <div id="imapReplies"></div>
    <p class="note">Gmail: enable IMAP in Gmail settings, create an App Password (Google Account → Security → App passwords). Outlook: use <code>imap-mail.outlook.com</code>.</p>
  </div>

  <!-- ========================= PAGESPEED ========================= -->
  <div class="panel">
    <h2>PageSpeed Analyzer</h2>
    <p class="sub" style="margin-top:-4px">Get Google Lighthouse performance scores for any website — useful for pitching improvements to prospects.</p>
    <div class="grid" style="align-items:end">
      <div><label for="psUrl">Website URL</label><input id="psUrl" placeholder="https://example.com"></div>
      <div><label for="psStrategy">Strategy</label><select id="psStrategy"><option value="mobile">Mobile</option><option value="desktop">Desktop</option><option value="both">Both</option></select></div>
      <div><button class="btn primary" id="psRun" style="width:100%">Analyze</button></div>
    </div>
    <p class="note" style="margin-top:4px">You can also run this from the Find leads tab on any lead's website by clicking "Check site" → "Full PageSpeed report".</p>
    <div id="psMsg"></div>
    <div id="psResult"></div>
  </div>

  <!-- ========================= WEBCRAWLER ========================= -->
  <div class="panel">
    <h2>WebCrawler — CSE Discovery</h2>
    <p class="sub" style="margin-top:-4px">Use Google Custom Search to find business websites by keyword, then scrape each for emails, phone and address. Requires a Google Custom Search API key and Search Engine ID (set in Settings → Dorking).</p>
    <div class="grid" style="align-items:end">
      <div><label for="wcKeyword">Keyword</label><input id="wcKeyword" placeholder="plumber in Austin Texas"></div>
      <div><label for="wcLimit">Max results</label><input id="wcLimit" type="number" value="20" min="5" max="100"></div>
      <div><button class="btn primary" id="wcCrawl" style="width:100%">Crawl &amp; Scrape</button></div>
    </div>
    <div id="wcMsg"></div>
    <div id="wcResult"></div>
    <h3>Batch URL scraper</h3>
    <p class="sub">Paste one URL per line, click Scrape.</p>
    <textarea id="wcUrls" rows="4" placeholder="https://business1.com&#10;https://business2.com"></textarea>
    <button class="btn" id="wcScrape" style="margin-top:6px">Scrape URLs</button>
    <div id="wcBatchResult"></div>

    <h3>CSV import</h3>
    <p class="sub">Import a CSV from an external tool (OutLead, LeadMapAI, etc.) and add leads to My list. Expected columns: name, category, address, phone, email, website.</p>
    <label class="btn sm" style="margin:0;color:var(--ink)">Choose CSV file<input type="file" id="wcImport" accept=".csv" hidden></label>
    <div id="wcImportMsg"></div>
  </div>`;

  document.querySelector(".wrap").appendChild(sec);
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "integrations"; b.textContent = "Integrations";
  b.setAttribute("aria-selected","false");
  nav.appendChild(b);
  window.LF.bindTab(b, loadStatus);
}

// ---------------------------------------------------------------- Sheets
async function sheetsExport(){
  const btn = $("#sheetsExport"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Exporting…';
  const msg = $("#sheetsMsg");
  try {
    const creds = $("#sheetsCredsPath").value.trim();
    const title = $("#sheetsTitle").value.trim() || "LeadFinder Export";
    const leads = window.LF.getList();
    // Save credsPath for next time
    await api("/api/sheets/config", {save: {credsPath: creds}});
    const r = await api("/api/sheets/export", {credsPath: creds, leads, title});
    msg.innerHTML = `<div class="msg ok">✓ Exported ${r.rows} leads at ${esc(r.exportedAt)}. <a href="${esc(r.url)}" target="_blank" rel="noopener">Open spreadsheet ↗</a></div>`;
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Export to Google Sheets";
}

async function loadSheetsStatus(){
  try {
    const s = await api("/api/sheets/status");
    const c = s.config || {};
    if (c.credsPath) $("#sheetsCredsPath").value = c.credsPath;
    if (s.spreadsheetId)
      $("#sheetsStatus").innerHTML = `Last export: <a href="https://docs.google.com/spreadsheets/d/${esc(s.spreadsheetId)}/edit" target="_blank" rel="noopener">Open spreadsheet ↗</a> · Authorized: ${s.authorized ? "✓" : "No (will prompt on first export)"}`;
  } catch(e){}
}

// ---------------------------------------------------------------- IMAP
async function imapCheck(){
  const btn = $("#imapCheck"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Checking…';
  const msg = $("#imapMsg");
  try {
    const outbox = (() => { try { return JSON.parse(localStorage.getItem("lf-outbox") || "[]"); } catch(e){ return []; } })();
    const sentEmails = outbox.filter(o => o.status === "sent" && o.to).map(o => o.to.toLowerCase());
    const r = await api("/api/imap/check", {
      host: $("#imapHost").value.trim(),
      email: $("#imapEmail").value.trim(),
      password: $("#imapPass").value,
      lookbackDays: parseInt($("#imapDays").value) || 7,
      sentEmails,
    });
    const s = r.summary;
    msg.innerHTML = `<div class="msg ok">Found ${s.total} emails: ${s.positive} positive, ${s.reply} replies, ${s.unsubscribe} unsubscribe, ${s.ooo} out-of-office.</div>`;
    renderReplies(r.replies);
    // Auto-update list for unsubscribers
    r.replies.filter(rep => rep.kind === "unsubscribe").forEach(rep => {
      const list = window.LF.getList();
      const lead = list.find(l => (l.email || "").toLowerCase() === rep.from_email);
      if (lead) window.LF.updateLead(lead.id, {stage: "Not interested", notes: (lead.notes ? lead.notes + "\n" : "") + rep.date + ": unsubscribed"});
    });
    // Mark positive replies as Interested
    r.replies.filter(rep => rep.kind === "positive").forEach(rep => {
      const list = window.LF.getList();
      const lead = list.find(l => (l.email || "").toLowerCase() === rep.from_email);
      if (lead && lead.stage === "Contacted") window.LF.updateLead(lead.id, {stage: "Interested", notes: (lead.notes ? lead.notes + "\n" : "") + rep.date + ": replied positively"});
    });
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Check replies";
}

async function imapSave(){
  await api("/api/imap/config", {save: {
    host: $("#imapHost").value.trim(),
    email: $("#imapEmail").value.trim(),
    password: $("#imapPass").value,
    lookbackDays: parseInt($("#imapDays").value) || 7,
    enabled: true,
  }});
  $("#imapMsg").innerHTML = '<div class="msg ok">IMAP config saved.</div>';
}

function renderReplies(replies){
  if (!replies || !replies.length){ $("#imapReplies").innerHTML = ""; return; }
  const kindTag = k => k === "positive" ? '<span class="tag t-no">Positive</span>' :
                       k === "unsubscribe" ? '<span class="tag t-weak">Unsubscribe</span>' :
                       k === "ooo" ? '<span class="tag t-yes">Out of office</span>' :
                       '<span class="tag t-yes">Reply</span>';
  $("#imapReplies").innerHTML = `<div class="tablewrap" style="margin-top:10px"><table>
    <thead><tr><th>From</th><th>Kind</th><th>Subject</th><th>Preview</th><th>Date</th></tr></thead>
    <tbody>${replies.slice(0,50).map(r => `<tr>
      <td class="sub">${esc(r.from_email)}</td>
      <td>${kindTag(r.kind)}</td>
      <td>${esc(r.subject.slice(0,50))}</td>
      <td class="sub">${esc(r.body.slice(0,100))}</td>
      <td class="sub">${esc(r.date.slice(0,16))}</td>
    </tr>`).join("")}</tbody>
  </table></div>`;
}

async function loadImapStatus(){
  try {
    const s = await api("/api/imap/status");
    if (s.configured) {
      renderReplies(s.recentReplies);
    }
  } catch(e){}
}

// ---------------------------------------------------------------- PageSpeed
function renderPSResult(data, label){
  const scoreCol = n => n >= 90 ? "var(--go)" : n >= 50 ? "var(--warn)" : "var(--stop)";
  const cats = data.scores || {};
  return `<div style="margin-top:10px"><b>${esc(label)}</b>
    <div class="tally" style="margin:8px 0">
      ${Object.entries(cats).map(([cat, v]) =>
        `<div><b style="color:${scoreCol(v.score)};font-family:var(--display);font-size:20px">${v.score ?? "?"}</b><span>${esc(cat)}</span></div>`
      ).join("")}
    </div>
    ${data.cwv ? `<div class="sub" style="margin-bottom:6px">
      <b>Core Web Vitals:</b>
      ${Object.entries(data.cwv).map(([k, v]) => `${k}: ${esc(v.displayValue || "?")} (${esc(v.grade)})`).join(" · ")}
    </div>` : ""}
    ${data.opportunities && data.opportunities.length ? `<div class="sub"><b>Top opportunities:</b></div>
      <ul style="font-size:13px;margin:4px 0;padding-left:18px">
        ${data.opportunities.slice(0,5).map(o => `<li>${esc(o.title)}${o.displayValue ? " — " + esc(o.displayValue) : ""}</li>`).join("")}
      </ul>` : ""}
  </div>`;
}

async function psRun(){
  const btn = $("#psRun"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Analyzing…';
  const msg = $("#psMsg"), res = $("#psResult");
  try {
    const url = $("#psUrl").value.trim();
    const strategy = $("#psStrategy").value;
    if (!url){ throw new Error("Enter a URL first."); }
    let html = "";
    if (strategy === "both"){
      const r = await api("/api/pagespeed/both", {url});
      html = renderPSResult(r.mobile, "Mobile") + renderPSResult(r.desktop, "Desktop");
    } else {
      const r = await api("/api/pagespeed", {url, strategy});
      html = renderPSResult(r, strategy === "mobile" ? "Mobile" : "Desktop");
    }
    msg.innerHTML = "";
    res.innerHTML = `<div class="panel" style="margin-top:8px">${html}<div class="sub" style="margin-top:8px">Data from Google PageSpeed Insights · <a href="https://pagespeed.web.dev/report?url=${encodeURIComponent(url)}" target="_blank" rel="noopener">Full report ↗</a></div></div>`;
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Analyze";
}

// ---------------------------------------------------------------- WebCrawler
async function wcCrawl(){
  const btn = $("#wcCrawl"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Crawling…';
  const msg = $("#wcMsg"), res = $("#wcResult");
  try {
    const kw = $("#wcKeyword").value.trim();
    const limit = parseInt($("#wcLimit").value) || 20;
    if (!kw){ throw new Error("Enter a keyword."); }
    const r = await api("/api/webcrawler/crawl", {keyword: kw, limit});
    msg.innerHTML = `<div class="msg ok">Found ${r.urlsFound} URLs, scraped ${r.leads.length} businesses, ${r.withEmail} have an email.</div>`;
    if (r.leads.length){
      res.innerHTML = `<div class="toolbar" style="margin-top:10px">
        <button class="btn sm primary" id="wcAddAll">Add all ${r.leads.length} to My list</button>
        <button class="btn sm" id="wcExportCsv">Download CSV</button>
      </div>
      <div class="tablewrap" style="margin-top:8px"><table style="min-width:600px">
        <thead><tr><th>Business</th><th>Email</th><th>Phone</th><th>Website</th></tr></thead>
        <tbody>${r.leads.map(l => `<tr>
          <td class="nm">${esc(l.name||"(unknown)")}</td>
          <td class="sub">${esc(l.email||"—")}</td>
          <td class="sub">${esc(l.phone||"—")}</td>
          <td><a class="sub" href="${esc(l.website)}" target="_blank" rel="noopener">${esc((l.website||"").slice(0,40))}</a></td>
        </tr>`).join("")}</tbody>
      </table></div>`;
      document.getElementById("wcAddAll").onclick = () => { window.LF.addLeads(r.leads); document.getElementById("wcAddAll").textContent = "Added ✓"; };
      document.getElementById("wcExportCsv").onclick = async () => {
        const c = await api("/api/webcrawler/export-csv", {leads: r.leads});
        const a = document.createElement("a"); a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(c.csv);
        a.download = "webcrawler-leads.csv"; a.click();
      };
    }
  } catch(e){
    msg.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Crawl & Scrape";
}

async function wcScrapeUrls(){
  const btn = $("#wcScrape"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Scraping…';
  const res = $("#wcBatchResult");
  try {
    const urls = $("#wcUrls").value.split("\n").map(s => s.trim()).filter(Boolean);
    if (!urls.length){ throw new Error("Paste at least one URL."); }
    const r = await api("/api/webcrawler/scrape", {urls});
    const withEmail = r.leads.filter(l => l.email).length;
    res.innerHTML = `<div class="msg ok">${r.count} URLs scraped, ${withEmail} have an email.</div>
      <button class="btn sm primary" id="wcBatchAdd" style="margin-top:6px">Add all to My list</button>`;
    document.getElementById("wcBatchAdd").onclick = () => {
      window.LF.addLeads(r.leads.map(l => ({
        ...l, id: "wc:" + (l.website||"").replace(/^https?:\/\/(www\.)?/,"").replace(/\W+/g,"-").slice(0,30),
        source: "WebCrawler", category: "Scraped"
      })));
      document.getElementById("wcBatchAdd").textContent = "Added ✓";
    };
  } catch(e){
    res.innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
  }
  btn.disabled = false; btn.textContent = "Scrape URLs";
}

function wcImport(file){
  if (!file) return;
  const reader = new FileReader();
  reader.onload = async e => {
    const csv = e.target.result;
    try {
      const r = await api("/api/webcrawler/import-csv", {csv});
      if (r.leads.length){
        window.LF.addLeads(r.leads);
        $("#wcImportMsg").innerHTML = `<div class="msg ok">Imported ${r.count} leads and added to My list.</div>`;
      } else {
        $("#wcImportMsg").innerHTML = `<div class="msg err">No valid rows found. Check the CSV has a 'name' column.</div>`;
      }
    } catch(e){
      $("#wcImportMsg").innerHTML = `<div class="msg err">${esc(e.message)}</div>`;
    }
  };
  reader.readAsText(file);
}

// ---------------------------------------------------------------- status load
async function loadStatus(){
  await Promise.all([loadSheetsStatus(), loadImapStatus()]);
}

// ---------------------------------------------------------------- init
function init(){
  mount();
  $("#sheetsExport").onclick = sheetsExport;
  $("#imapCheck").onclick = imapCheck;
  $("#imapSave").onclick = imapSave;
  $("#psRun").onclick = psRun;
  $("#wcCrawl").onclick = wcCrawl;
  $("#wcScrape").onclick = wcScrapeUrls;
  $("#wcImport").onchange = e => wcImport(e.target.files[0]);
  // PS from lead card: "Full PageSpeed" button (added by report.js)
  window.LFPageSpeed = {run: (url) => {
    window.LF.showTab && window.LF.showTab("integrations");
    const el = $("#psUrl"); if(el) el.value = url;
    psRun();
  }};
}

document.addEventListener("DOMContentLoaded", init);
})();
