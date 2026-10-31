/* LeadFinder: Emails tab. Niche-specific cold email templates, drafts, manual approval, sending */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function store(k, d, v){
  try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; }
        const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; }
}
const today = () => new Date().toISOString().slice(0,10);
const addDays = n => { const d = new Date(); d.setDate(d.getDate()+n); return d.toISOString().slice(0,10); };

const GROUPS = [
  ["Home services", /roof|plumb|hvac|heat|air con|electric|landscap|lawn|tree|paint|contract|remodel|build|clean|pest|mov|handyman|lock|floor|fenc|pool|gutter|window|garage door/i],
  ["Auto", /auto|car|mechanic|garage|tyre|tire|detail|body shop/i],
  ["Health", /dent|clinic|doctor|chiro|physio|vet|optom|optic|therap|medical|health/i],
  ["Beauty", /salon|beauty|barber|hair|nail|spa|lash|brow|tattoo|makeup|massage|groom/i],
  ["Food", /restaurant|cafe|coffee|bakery|food|cater|pizza|grill|bar\b|diner|truck/i],
  ["Fitness", /gym|fitness|trainer|yoga|pilates|martial|boxing|dance/i],
  ["Professional", /law|attorney|legal|account|tax|bookkeep|real estate|realtor|estate agent|insur|mortgage|financ|consult/i],
  ["Creative & education", /photo|wedding|video|daycare|tutor|school|driving|music|lesson/i],
  ["Retail", /shop|store|boutique|florist|jewel|furniture|pet|gift|cloth/i],
];
const groupOf = l => (GROUPS.find(([,rx]) => rx.test(`${l.category||""} ${l.searchQuery||""} ${l.name||""}`)) || ["General"])[0];

const FOOTER = `

{my_name}
{my_business} | {my_phone} | {my_website}
{my_address}

If you'd rather not hear from me, just reply "no thanks" and I won't email again.`;

const DEFAULT_TEMPLATES = {
  "Home services": {
    subject: "Quick question about {business}",
    body: `Hi {first_name},

I was looking for a {type} in {city} and came across {business}. {reviews_line}

{gap_line} When someone has a leak, a broken AC or storm damage, they usually call the first company that looks trustworthy online, and a simple website with your services, service areas and a "get a quote" button is often what makes that happen.

I build websites for local contractors. I've put together a free sample homepage idea for {business}; you can see it here: {demo_link}

Would you be open to a quick 10-minute call this week to see if it's a fit?`},
  "Auto": {
    subject: "Idea for {business}",
    body: `Hi {first_name},

I found {business} while searching for auto repair in {city}. {reviews_line}

{gap_line} Drivers usually compare shops on their phone before calling, so a site with your services, rough prices and an "book a service" button can bring in customers who don't know you yet.

I made a free sample homepage for {business}: {demo_link}

Worth a quick look?`},
  "Health": {
    subject: "New patients for {business}",
    body: `Hi {first_name},

I came across {business} while looking for a {type} in {city}. {reviews_line}

{gap_line} Many patients now search late in the evening and choose the practice where they can see services and book an appointment online right away.

I design websites for clinics, with online booking and service pages that help you show up for searches like "{type} near me". Here's a free sample I prepared for you: {demo_link}

Could we find 10 minutes to talk this week?`},
  "Beauty": {
    subject: "Bookings for {business}",
    body: `Hi {first_name},

I found {business} on Google. {reviews_line}

{gap_line} Clients love booking at 11pm when you're closed, and a website with your price list, photos and a "Book now" button captures those bookings automatically.

I made a free sample site for {business} that links to your Instagram and booking: {demo_link}

Would you like me to set it up for you?`},
  "Food": {
    subject: "Your menu online, {business}",
    body: `Hi {first_name},

I was looking for places to eat in {city} and found {business}. {reviews_line}

{gap_line} Most people check the menu, photos and hours online before deciding where to go, and a website with online ordering lets you take orders directly instead of paying high app commissions on every one.

Here's a free sample site I made for you with your menu layout: {demo_link}

Can I show you how it works?`},
  "Fitness": {
    subject: "More sign-ups for {business}",
    body: `Hi {first_name},

I came across {business} while searching for fitness in {city}. {reviews_line}

{gap_line} People compare gyms and trainers online first: prices, class times and photos. A website with online sign-up turns that interest into paying members, even outside opening hours.

I made a free sample homepage for {business}: {demo_link}

Open to a quick chat?`},
  "Professional": {
    subject: "{business}: first impressions online",
    body: `Hi {first_name},

I came across {business} while researching {type} services in {city}. {reviews_line}

{gap_line} Before contacting a firm, most clients check the website to judge credibility, and a clear site with your services, team and a consultation form turns that research into enquiries.

I build websites for professional firms. I've prepared a free sample homepage for {business}: {demo_link}

Would a short call next week be useful?`},
  "Creative & education": {
    subject: "Showcasing {business}",
    body: `Hi {first_name},

I found {business} while searching in {city}. {reviews_line}

{gap_line} Clients and parents compare options online before they get in touch, and a website with your work, packages and an enquiry form makes that decision easy.

I created a free sample site for {business}: {demo_link}

Would you like to take a look together?`},
  "Retail": {
    subject: "Selling online, {business}",
    body: `Hi {first_name},

I came across {business} in {city}. {reviews_line}

{gap_line} A simple online store or catalog lets customers browse your products, message you on WhatsApp and order for pickup or delivery, including people who can't visit in person.

Here's a free sample site I made for {business}: {demo_link}

Worth a quick chat?`},
  "General": {
    subject: "Quick idea for {business}",
    body: `Hi {first_name},

I found {business} on Google while searching in {city}. {reviews_line}

{gap_line} Most customers look businesses up online before calling or visiting, and a clear, mobile-friendly website helps them choose you.

I made a free sample homepage for {business}: {demo_link}

Would you be open to a quick 10-minute call?`},
  "Digital identity": {
    subject: "{business}: a quick look at your online presence",
    body: `Hi {first_name},

I looked at how {business} shows up online. {reviews_line} Even so, {business} scores {identity_score}/100 on my digital identity check: right now {missing_line}.

{competitor_line} That usually means some people who search for a {type} in {city} end up choosing someone else.

I help local businesses get a complete digital identity: {offer_line}. {app_line}

I've prepared a short proposal and a free homepage preview for {business}: {demo_link}

Would you like me to send it over?`},
  "Follow-up 1": {
    subject: "Re: {subject}",
    body: `Hi {first_name},

Just bringing this back to the top of your inbox. I made a free sample website for {business}: {demo_link}

Happy to adjust it with your photos and services, no obligation. Would a quick call on {weekday} work?`},
  "Follow-up 2": {
    subject: "Should I close this, {first_name}?",
    body: `Hi {first_name},

I haven't heard back, so I'll assume now isn't the right time and I won't follow up again.

If you'd ever like more customers finding {business} online, the sample is still here: {demo_link}

All the best with the business!`},
};

let T = Object.assign({}, DEFAULT_TEMPLATES, store("lf-templates", {}));
let outbox = store("lf-outbox", []);
let mail = store("lf-mail", {delay: 60, dailyCap: 30, demoBase: ""});
const saveOutbox = () => store("lf-outbox", null, outbox);

function cityOf(addr){
  const p = String(addr||"").split(",").map(s => s.trim()).filter(Boolean);
  if (p.length >= 3) return /\d/.test(p[p.length-2]) && p.length >= 4 ? p[p.length-3] : p[p.length-2].replace(/\s*[A-Z]{2}\s*\d{5}.*$/,"").trim() || p[p.length-3];
  return p[0] || "your area";
}
function fill(text, lead, extra){
  const S = window.LF.settings();
  let gap = "";
  if (lead.analysis && window.LFReport){
    const ins = window.LFReport.insights(lead, lead.analysis);
    const top = ins.top && ins.top.name !== lead.name ? ins.top.name : "";
    if (!ins.mine.website && top) gap = `I noticed ${lead.name} doesn't have a website yet, while nearby competitors like ${top} do.`;
    else if (!ins.mine.website) gap = `I noticed ${lead.name} doesn't have a website yet.`;
    else if (ins.gaps.length) gap = "I noticed " + ins.gaps[0].text.charAt(0).toLowerCase() + ins.gaps[0].text.slice(1);
  } else if (!lead.website) gap = `I couldn't find a website for ${lead.name}.`;
  else gap = `I had a look at your website and saw a few quick wins that could bring in more enquiries.`;
  const rv = lead.reviews || 0;
  const reviewsLine = rv >= 10 && lead.rating ? `${rv} reviews at ${lead.rating} stars is impressive; customers clearly like your work.`
                    : rv >= 10 ? `${rv} reviews shows customers clearly like your work.` : "";
  const idn = lead.identity;
  const missList = missingPhrases(idn, 3);
  const missingLine = missList.length ? "there's " + (missList.length > 1 ? missList.slice(0,-1).join(", ") + " and " + missList.slice(-1) : missList[0]) : "there are a few quick wins";
  const offerLine = idn ? (!idn.presence.website ? "a mobile-friendly website" : "a faster, mobile-friendly website") + ", a polished Google profile, matching social pages and a professional email" : "a website, Google profile, social pages and professional email";
  const appLine = idn && idn.appFit.level === "High" ? `Because your customers come back often, a simple installable app (${idn.appFit.idea.replace(/^PWA with /i,"with ").toLowerCase()}) could be a great next step.` : "";
  let competitorLine = "";
  if (lead.analysis && lead.analysis.competitors && lead.analysis.competitors.length){
    const top = lead.analysis.competitors.slice().sort((a,b) => b.digitalScore - a.digitalScore)[0];
    const bits = [];
    if (top.presence.website && top.presence.siteLoads) bits.push("a website");
    if (top.presence.booking || top.presence.ordering || top.presence.quoteForm) bits.push("online booking");
    if (Object.keys(top.presence.socials||{}).length) bits.push("active social pages");
    if (bits.length && top.digitalScore > (idn ? idn.score : 0)) competitorLine = `Nearby, ${top.name} already has ${bits.join(", ")}.`;
  }
  const slug = String(lead.name||"").toLowerCase().replace(/[^a-z0-9]+/g,"-").replace(/^-|-$/g,"");
  const days = ["Tuesday","Wednesday","Thursday"];
  const v = {
    first_name: lead.contactName || "there",
    identity_score: idn ? idn.score : "{identity_score}", missing_line: missingLine, offer_line: offerLine, app_line: appLine,
    competitor_line: competitorLine,
    owner: lead.ownerName || "", business: lead.name, city: cityOf(lead.address),
    type: (lead.searchQuery || lead.category || "business").toLowerCase(), reviews: rv, rating: lead.rating || "",
    reviews_line: reviewsLine, gap_line: gap,
    competitor: lead.analysis?.competitors?.[0]?.name || "other local businesses",
    my_name: S.myName || "{my_name}", my_business: S.myBusiness || "{my_business}",
    my_phone: mail.phone || "{my_phone}", my_website: mail.website || "{my_website}", my_address: mail.address || "{my_address}",
    demo_link: mail.demoBase ? mail.demoBase.replace(/\/$/,"") + "/" + slug : "{demo_link}",
    weekday: days[new Date().getDate() % 3], ...extra,
  };
  return text.replace(/\{(\w+)\}/g, (m,k) => v[k] !== undefined && v[k] !== "" ? v[k] : (k in v ? "" : m))
             .replace(/\n +/g, "\n").replace(/\n{3,}/g, "\n\n").replace(/ +\n/g, "\n");
}
function missingPhrases(idn, max){
  if (!idn) return [];
  const miss = new Set(idn.parts.filter(p => !p.ok).map(p => p.key));
  if (miss.has("website")) miss.delete("quality");
  if (miss.has("social")) miss.delete("social2");
  if (idn.appFit.level !== "High") miss.delete("app");
  const nice = {website:"no website", quality:"a website that isn't mobile-friendly or secure", google:"no Google Business Profile",
    booking:"no online booking or ordering", social:"no social media pages", email: idn.email.freeProvider ? "a free Gmail/Yahoo address instead of a business email" : "no business email",
    chat:"no WhatsApp chat button", reviews:"few reviews online", social2:"only one social channel", app:"no app for repeat customers"};
  const order = ["website","quality","google","booking","social","email","chat","reviews","app","social2"];
  return order.filter(k => miss.has(k)).map(k => nice[k]).slice(0, max || 3);
}
const unresolved = s => (String(s).match(/\{\w+\}/g) || []);

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-emails"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Cold emails with manual approval</h2>
    <p class="sub" style="margin-top:-4px">1. Create drafts from My list, using a template for each lead's niche. 2. Read and edit each one. 3. Approve. 4. Send, or open in your email app. Nothing is sent until you approve it.</p>
    <div class="toolbar">
      <label style="margin:0">Create</label>
      <select id="emStep" style="max-width:200px"><option value="0">First email</option><option value="1">Follow-up 1</option><option value="2">Follow-up 2</option></select>
      <label style="margin:0">for</label>
      <select id="emWho" style="max-width:260px">
        <option value="new">List leads at stage "New"</option>
        <option value="hot">Hot and Warm leads only</option>
        <option value="due">Follow-ups due today</option>
        <option value="all">Everyone in My list</option>
      </select>
      <label style="display:flex;gap:5px;align-items:center;margin:0;color:var(--ink)"><input type="checkbox" id="emNoEmail" style="width:auto"> include leads without email</label>
      <label style="margin:0">template</label>
      <select id="emTplMode" style="max-width:250px"><option value="auto">Auto (digital identity if checked)</option><option value="niche">By niche</option><option value="identity">Digital identity</option></select>
      <button class="btn primary" id="emCreate">Create drafts</button>
    </div>
    <div id="emMsg"></div>
  </div>

  <div class="panel">
    <div class="toolbar">
      <h3 style="margin:0" class="grow">Outbox</h3>
      <select id="emFilter" style="max-width:170px"><option value="draft">Drafts</option><option value="approved">Approved</option><option value="sent">Sent</option><option value="failed">Failed</option><option value="rejected">Rejected</option><option value="">All</option></select>
      <button class="btn sm primary" id="emSendAll">Send all approved</button>
      <button class="btn sm" id="emExport">Download approved CSV</button>
      <button class="btn sm" id="emClearDone">Clear sent & rejected</button>
    </div>
    <div id="emCounts" class="sub"></div>
    <div id="emList"></div>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">Templates by niche</h3>
    <p class="sub">Placeholders: {first_name} {business} {city} {type} {reviews_line} {gap_line} {competitor} {demo_link} {my_name} {my_business} {weekday}. {gap_line} uses the prospect report when you've analyzed the lead. Your signature and opt-out line are added automatically.</p>
    <div class="toolbar"><select id="emTpl" style="max-width:260px"></select><button class="btn sm" id="emTplReset">Reset to default</button></div>
    <label for="emTplSubj">Subject</label><input id="emTplSubj">
    <label for="emTplBody" style="margin-top:8px">Body</label><textarea id="emTplBody" rows="12"></textarea>
    <button class="btn primary" id="emTplSave" style="margin-top:8px">Save template</button>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">Sender setup</h3>
    <div class="grid">
      <div><label for="emPhone">Your phone</label><input id="emPhone"></div>
      <div><label for="emWebsite">Your website / portfolio</label><input id="emWebsite"></div>
      <div><label for="emAddress">Business postal address</label><input id="emAddress" placeholder="Required for US emails (CAN-SPAM)"></div>
      <div><label for="emDemo">Demo link base (optional)</label><input id="emDemo" placeholder="e.g. https://demo.yoursite.com"></div>
    </div>
    <p class="note">Demo link = base + business name, e.g. https://demo.yoursite.com/joes-plumbing. Leave empty and {demo_link} stays in the draft for you to fill in.</p>
    <h3>Sending through your email (SMTP)</h3>
    <div class="grid">
      <div><label for="smHost">SMTP server</label><input id="smHost" placeholder="smtp.gmail.com"></div>
      <div><label for="smPort">Port</label><input id="smPort" placeholder="587"></div>
      <div><label for="smUser">Username / email</label><input id="smUser"></div>
      <div><label for="smPass">Password / App password</label><input id="smPass" type="password" autocomplete="off"></div>
      <div><label for="smFromName">From name</label><input id="smFromName"></div>
      <div><label for="smDelay">Seconds between emails</label><input id="smDelay" type="number" min="20"></div>
      <div><label for="smCap">Max emails per day</label><input id="smCap" type="number" min="1"></div>
    </div>
    <p class="note">Gmail: turn on 2-Step Verification, then create an App Password (Google Account → Security → App passwords) and use smtp.gmail.com, port 587. Outlook: smtp.office365.com, port 587. Use a separate domain or mailbox for cold email, start with 10–20 per day and increase slowly to protect your main address from spam filters. Saved only in this browser.</p>
    <button class="btn primary" id="emSaveSender">Save sender setup</button>
    <div id="emSenderMsg"></div>
  </div>`;
  document.querySelector(".wrap").appendChild(sec);
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "emails"; b.setAttribute("aria-selected","false"); b.textContent = "Emails";
  nav.insertBefore(b, nav.querySelector('[data-tab="guide"]'));
  window.LF.bindTab(b, () => renderOutbox());
}

function renderTpl(){
  const k = $("#emTpl").value;
  $("#emTplSubj").value = T[k].subject; $("#emTplBody").value = T[k].body;
}

function counts(){
  const c = s => outbox.filter(o => o.status === s).length;
  const sentToday = outbox.filter(o => o.status === "sent" && (o.sentAt||"").startsWith(today())).length;
  $("#emCounts").textContent = `${c("draft")} drafts · ${c("approved")} approved · ${c("sent")} sent (${sentToday} today, limit ${mail.dailyCap}) · ${c("failed")} failed`;
  return sentToday;
}

function renderOutbox(){
  counts();
  const f = $("#emFilter").value;
  const rows = outbox.filter(o => !f || o.status === f);
  $("#emList").innerHTML = rows.length ? rows.map(o => {
    const un = unresolved(o.subject + o.body);
    const locked = o.status === "sent";
    const tagc = o.status==="approved" ? "t-no" : o.status==="sent" ? "t-yes" : o.status==="failed"||o.status==="rejected" ? "t-weak" : "t-weak";
    return `<div class="panel" style="margin:10px 0 0;padding:12px" data-oid="${o.id}">
      <div class="toolbar" style="margin:0 0 6px">
        <div class="grow"><b>${esc(o.business)}</b> <span class="sub">· ${esc(o.group)} · ${["First email","Follow-up 1","Follow-up 2"][o.step]}</span></div>
        <span class="tag ${tagc}" style="font-weight:600">${o.status.toUpperCase()}</span>
        ${o.sentAt ? `<span class="sub">${esc(o.sentAt)}</span>` : ""}
      </div>
      ${o.error ? `<div class="msg err">${esc(o.error)}</div>` : ""}
      ${un.length && !locked ? `<div class="msg err">Fill in before approving: ${esc([...new Set(un)].join(" "))}</div>` : ""}
      <div class="grid" style="grid-template-columns:1fr 2fr">
        <div><label>To</label><input data-f="to" value="${esc(o.to)}" placeholder="email@business.com" ${locked?"disabled":""}></div>
        <div><label>Subject</label><input data-f="subject" value="${esc(o.subject)}" ${locked?"disabled":""}></div>
      </div>
      <label style="margin-top:6px">Message</label>
      <textarea data-f="body" rows="${Math.min(18, o.body.split("\n").length + 1)}" ${locked?"disabled":""}>${esc(o.body)}</textarea>
      <div class="toolbar" style="margin-top:6px">
        ${o.status === "draft" || o.status === "rejected" || o.status === "failed" ? `<button class="btn sm primary" data-a="approve">Approve</button>` : ""}
        ${o.status === "draft" ? `<button class="btn sm" data-a="reject">Reject</button>` : ""}
        ${o.status === "approved" ? `<button class="btn sm primary" data-a="send">Send now</button><button class="btn sm" data-a="unapprove">Back to draft</button>` : ""}
        ${!locked ? `<button class="btn sm" data-a="ai">Personalize with AI</button>` : ""}
        <a class="btn sm" href="mailto:${encodeURIComponent(o.to)}?subject=${encodeURIComponent(o.subject)}&body=${encodeURIComponent(o.body)}" data-a="mailto">Open in email app</a>
        <button class="btn sm" data-a="copy">Copy</button>
        ${o.status === "approved" ? `<button class="btn sm" data-a="marksent">Mark as sent</button>` : ""}
        <div class="grow"></div>
        <button class="del btn sm" data-a="delete">Delete</button>
      </div>
    </div>`;
  }).join("") : `<div class="empty">Nothing here. ${f === "draft" ? "Press Create drafts above." : ""}</div>`;
}

function createDrafts(){
  const step = +$("#emStep").value, who = $("#emWho").value, noEmail = $("#emNoEmail").checked;
  const list = window.LF.getList();
  const already = new Set(outbox.filter(o => o.step === step && o.status !== "rejected").map(o => o.leadId));
  const firstSent = new Map(outbox.filter(o => o.step === 0 && o.status === "sent").map(o => [o.leadId, o]));
  const pool = list.filter(l => {
    if (already.has(l.id)) return false;
    if (!noEmail && !l.email) return false;
    if (["Won","Not interested"].includes(l.stage)) return false;
    if (step > 0 && !firstSent.has(l.id)) return false;
    if (who === "new") return step > 0 ? true : l.stage === "New";
    if (who === "hot") return ["Hot","Warm"].includes(l.priority);
    if (who === "due") return l.followUp && l.followUp <= today();
    return true;
  });
  const mode = $("#emTplMode") ? $("#emTplMode").value : "niche";
  pool.forEach(l => {
    const group = step === 0 ? (mode === "identity" || (mode === "auto" && l.identity) ? "Digital identity" : groupOf(l)) : `Follow-up ${step}`;
    const t = T[group];
    const prevSubj = firstSent.get(l.id)?.subject || "";
    outbox.unshift({
      id: Date.now().toString(36) + Math.random().toString(36).slice(2,6),
      leadId: l.id, business: l.name, group: step === 0 ? group : groupOf(l), step,
      to: l.email || "", subject: fill(t.subject, l, {subject: prevSubj}),
      body: fill(t.body + FOOTER, l), status: "draft", createdAt: today(),
    });
  });
  saveOutbox();
  $("#emFilter").value = "draft";
  $("#emMsg").innerHTML = pool.length
    ? `<div class="msg ok">${pool.length} draft${pool.length===1?"":"s"} created. Review each one below, then approve.</div>`
    : `<div class="msg err">No matching leads. ${step>0 ? "Follow-ups need a sent first email." : "Add leads with emails to My list (use Find emails), or tick 'include leads without email'."}</div>`;
  renderOutbox();
}

function markSent(o){
  if (window.LF.log) window.LF.log("emails");
  o.status = "sent"; o.sentAt = new Date().toISOString().slice(0,16).replace("T"," "); o.error = "";
  const l = window.LF.getList().find(x => x.id === o.leadId);
  if (l){
    const patch = {followUp: addDays(o.step === 0 ? 3 : o.step === 1 ? 4 : 0) , notes: `${l.notes ? l.notes + "\n" : ""}${today()}: ${["Email 1","Follow-up 1","Follow-up 2"][o.step]} sent`};
    if (l.stage === "New") patch.stage = "Contacted";
    if (o.step === 2) patch.followUp = "";
    window.LF.updateLead(l.id, patch);
  }
}

async function sendOne(o){
  const sentToday = counts();
  if (sentToday >= mail.dailyCap) throw new Error(`Daily limit reached (${mail.dailyCap}). Increase it in Sender setup or send tomorrow.`);
  if (unresolved(o.subject + o.body).length) throw new Error("This email still has {placeholders}.");
  await window.LF.api("/api/send-email", {smtp: mail.smtp || {}, to: o.to, subject: o.subject, body: o.body, replyTo: mail.smtp?.user});
  markSent(o);
}

let sending = false;
function init(){
  mount();
  $("#emTpl").innerHTML = Object.keys(T).map(k => `<option>${esc(k)}</option>`).join("");
  renderTpl();
  $("#emTpl").onchange = renderTpl;
  $("#emTplSave").onclick = () => {
    const k = $("#emTpl").value; T[k] = {subject: $("#emTplSubj").value, body: $("#emTplBody").value};
    const custom = store("lf-templates", {}); custom[k] = T[k]; store("lf-templates", null, custom);
    $("#emTplSave").textContent = "Saved"; setTimeout(() => $("#emTplSave").textContent = "Save template", 1500);
  };
  $("#emTplReset").onclick = () => {
    const k = $("#emTpl").value; T[k] = DEFAULT_TEMPLATES[k];
    const custom = store("lf-templates", {}); delete custom[k]; store("lf-templates", null, custom); renderTpl();
  };
  const sm = mail.smtp || {};
  [["emPhone","phone"],["emWebsite","website"],["emAddress","address"],["emDemo","demoBase"]].forEach(([id,k]) => $("#"+id).value = mail[k] || "");
  [["smHost","host"],["smPort","port"],["smUser","user"],["smPass","password"],["smFromName","fromName"]].forEach(([id,k]) => $("#"+id).value = sm[k] || "");
  $("#smDelay").value = mail.delay; $("#smCap").value = mail.dailyCap;
  $("#emSaveSender").onclick = () => {
    mail = {phone: $("#emPhone").value.trim(), website: $("#emWebsite").value.trim(), address: $("#emAddress").value.trim(),
      demoBase: $("#emDemo").value.trim(), delay: Math.max(20, +$("#smDelay").value || 60), dailyCap: Math.max(1, +$("#smCap").value || 30),
      smtp: {host: $("#smHost").value.trim(), port: $("#smPort").value.trim() || "587", user: $("#smUser").value.trim(),
             password: $("#smPass").value, fromName: $("#smFromName").value.trim(), fromEmail: $("#smUser").value.trim(),
             unsubEmail: $("#smUser").value.trim()}};
    store("lf-mail", null, mail);
    $("#emSenderMsg").innerHTML = '<div class="msg ok">Saved. New drafts will use these details.</div>';
  };
  $("#emCreate").onclick = createDrafts;
  $("#emFilter").onchange = renderOutbox;

  $("#emList").addEventListener("change", e => {
    const f = e.target.dataset.f; if (!f) return;
    const o = outbox.find(x => x.id === e.target.closest("[data-oid]").dataset.oid);
    o[f] = e.target.value;
    saveOutbox();
    if (o.status === "approved"){ o.status = "draft"; saveOutbox(); setTimeout(renderOutbox, 0); } // edited after approval → approve again
  });
  $("#emList").addEventListener("click", async e => {
    const b = e.target.closest("[data-a]"); if (!b) return;
    const card = b.closest("[data-oid]");
    const o = outbox.find(x => x.id === card.dataset.oid);
    const a = b.dataset.a;
    // take unsaved edits from the card first
    if (o.status !== "sent") card.querySelectorAll("[data-f]").forEach(i => o[i.dataset.f] = i.value);
    if (a === "approve"){
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(o.to)) { alert("Add a valid recipient email first."); return; }
      if (unresolved(o.subject + o.body).length){ alert("Replace the {placeholders} first: " + [...new Set(unresolved(o.subject+o.body))].join(" ")); return; }
      o.status = "approved"; o.error = "";
    }
    if (a === "reject") o.status = "rejected";
    if (a === "unapprove") o.status = "draft";
    if (a === "delete"){ if (!confirm("Delete this email?")) return; outbox = outbox.filter(x => x !== o); }
    if (a === "marksent") markSent(o);
    if (a === "copy"){ try { await navigator.clipboard.writeText(`Subject: ${o.subject}\n\n${o.body}`); b.textContent = "Copied"; } catch(_){} return; }
    if (a === "mailto"){ return; }
    if (a === "send"){
      b.disabled = true; b.innerHTML = '<span class="spin"></span> Sending';
      try { await sendOne(o); } catch(err){ o.error = err.message; if (!/limit|placeholder/i.test(err.message)) o.status = "failed"; }
    }
    if (a === "ai"){
      b.disabled = true; b.innerHTML = '<span class="spin"></span> Writing';
      const l = window.LF.getList().find(x => x.id === o.leadId) || {};
      const S = window.LF.settings();
      try {
        const j = await window.LF.api("/api/ai", {ai: S.ai || {}, prompt:
          `Improve this cold email to make it more personal and natural for this business. Keep it under 150 words, keep the same facts, links, signature and opt-out line. Do not invent facts or statistics. Return only the email body, no subject.\n\nBUSINESS DATA: ${l.name}, ${l.category}, ${l.address}, rating ${l.rating||"n/a"}, ${l.reviews||0} reviews, website: ${l.website||"none"}.\n\nEMAIL:\n${o.body}`});
        o.body = j.text.replace(/^subject:.*\n+/i, ""); o.status = "draft";
      } catch(err){ o.error = err.message; }
    }
    saveOutbox(); renderOutbox();
  });

  $("#emSendAll").onclick = async () => {
    if (sending){ sending = false; return; }
    const queue = outbox.filter(o => o.status === "approved");
    if (!queue.length){ alert("No approved emails."); return; }
    if (!mail.smtp || !mail.smtp.host){ alert("Set up SMTP in Sender setup first, or use 'Open in email app' on each email."); return; }
    if (!confirm(`Send ${queue.length} approved email(s), one every ${mail.delay} seconds? Keep this tab open.`)) return;
    sending = true; const btn = $("#emSendAll");
    for (let i = 0; i < queue.length && sending; i++){
      const o = queue[i];
      btn.textContent = `Sending ${i+1}/${queue.length}… (click to stop)`;
      try { await sendOne(o); } catch(err){ o.error = err.message; if (/limit/i.test(err.message)){ saveOutbox(); renderOutbox(); break; } o.status = "failed"; }
      saveOutbox(); renderOutbox();
      if (i < queue.length - 1 && sending){
        for (let s = mail.delay; s > 0 && sending; s--){ btn.textContent = `Next in ${s}s (${i+1}/${queue.length} sent), click to stop`; await new Promise(r => setTimeout(r, 1000)); }
      }
    }
    sending = false; btn.textContent = "Send all approved"; renderOutbox();
  };
  $("#emExport").onclick = () => {
    const rows = outbox.filter(o => o.status === "approved");
    const q = v => `"${String(v ?? "").replace(/"/g,'""')}"`;
    const csv = ["Business,Email,Subject,Body", ...rows.map(o => [o.business,o.to,o.subject,o.body].map(q).join(","))].join("\r\n");
    const a = document.createElement("a"); a.href = URL.createObjectURL(new Blob(["\ufeff"+csv], {type:"text/csv"})); a.download = "approved-emails.csv"; a.click();
  };
  $("#emClearDone").onclick = () => { outbox = outbox.filter(o => !["sent","rejected"].includes(o.status)); saveOutbox(); renderOutbox(); };
  renderOutbox();
}
function addDraft(lead, group){
  const l = window.LF.getList().find(x => x.id === lead.id);
  if (!l || outbox.some(o => o.leadId === l.id && o.step === 0 && o.status !== "rejected")) return 0;
  const t = T[group] || T[groupOf(l)];
  outbox.unshift({id: Date.now().toString(36) + Math.random().toString(36).slice(2,6), leadId: l.id, business: l.name,
    group, step: 0, to: l.email || "", subject: fill(t.subject, l, {}), body: fill(t.body + FOOTER, l), status: "draft", createdAt: today()});
  saveOutbox(); renderOutbox(); return 1;
}
window.LFOutreach = {fill, groupOf, cityOf, DEFAULT_TEMPLATES, addDraft, missingPhrases};
if (window.LF) init(); else document.addEventListener("lf-ready", init);
})();
