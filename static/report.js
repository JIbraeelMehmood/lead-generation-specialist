/* LeadFinder prospect report: competitors, digital gaps, benefits, call priority, AI script */
(function(){
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const SOC = {facebook:"Facebook", instagram:"Instagram", tiktok:"TikTok", youtube:"YouTube", linkedin:"LinkedIn", x:"X"};

/* benefits by industry: what digital tools boost sales for this kind of business */
const INDUSTRY = [
  {k:/restaurant|cafe|coffee|bakery|food|pizza|burger|diner|bar|grill|kitchen|takeaway|fast food/i, name:"food business",
   tools:["Website with menu, prices and photos","Online ordering or delivery links","Table reservations","Instagram and TikTok food videos","WhatsApp ordering"],
   benefits:["People check the menu online before choosing where to eat; no menu often means they pick a competitor.",
     "Direct online orders avoid part of the commission paid to delivery apps.",
     "Food photos and short videos on Instagram/TikTok bring in new customers for free.",
     "A reservation button fills tables on quiet days."]},
  {k:/dent|clinic|doctor|medical|physio|chiro|vet|optic|pharma|health|therap/i, name:"healthcare practice",
   tools:["Website with services and prices","Online appointment booking","WhatsApp / chat for questions","Google reviews","Patient reminder app or SMS"],
   benefits:["Patients search 'near me' and book the practice they can book online, often at night.",
     "Online booking reduces phone time for staff.",
     "Service pages (e.g. braces, implants, whitening) attract higher-value patients from Google.",
     "Automatic reminders cut missed appointments."]},
  {k:/salon|beauty|barber|hair|nail|spa|lash|brow|makeup|massage/i, name:"beauty business",
   tools:["Website with price list","24/7 online booking","Instagram portfolio","Packages and gift cards online","Loyalty offers"],
   benefits:["Clients want to book at any hour; online booking captures bookings while the salon is closed.",
     "An Instagram portfolio is the #1 way clients choose a stylist.",
     "Gift cards and packages sold online bring in cash upfront.",
     "Rebooking reminders keep clients coming back."]},
  {k:/gym|fitness|yoga|pilates|crossfit|martial|boxing|dance/i, name:"fitness business",
   tools:["Website with membership plans","Online sign-up and payments","Class timetable and booking","Member app","Transformation posts on social"],
   benefits:["People compare gyms online first: prices, photos and timings.",
     "Online sign-up turns late-night interest into paid memberships.",
     "Class booking and an app keep members engaged, so fewer cancel.",
     "Before/after stories on social are strong free advertising."]},
  {k:/plumb|electric|roof|builder|contract|construct|hvac|heating|air con|clean|landscap|garden|paint|decor|carpent|handyman|pest|lock|mov|glaz|floor|tile|repair|mechanic|auto|car|garage|tyre|tire/i, name:"home or auto service business",
   tools:["Website with services and service areas","Click-to-call and quote request form","Before/after photo gallery","Google reviews on the site","WhatsApp for photos of the problem"],
   benefits:["Customers with an urgent problem search Google and call the first business that looks trustworthy.",
     "A quote form collects jobs 24/7, even while the owner is on a job.",
     "Service-area pages help them show up in nearby towns and districts.",
     "Photos of past work and reviews make it easier to charge fair prices."]},
  {k:/law|legal|solicit|attorney|account|tax|bookkeep|financ|insur|real estate|estate agent|realtor|mortgage|consult/i, name:"professional services firm",
   tools:["Professional website with team and services","Consultation booking form","Helpful articles (SEO)","LinkedIn presence","Client reviews and case results"],
   benefits:["Clients judge credibility by the website before they ever call.",
     "A consultation form turns visitors into leads.",
     "Helpful articles bring in people searching for answers to their problem.",
     "LinkedIn builds trust and referrals."]},
  {k:/hotel|guest|hostel|bnb|resort|lodge|motel/i, name:"accommodation business",
   tools:["Website with photos and rooms","Direct booking engine","Google Hotel listing","Instagram","WhatsApp enquiries"],
   benefits:["Direct bookings avoid the commission paid to booking sites.",
     "Good photos and a booking button raise conversions.",
     "Guests message on WhatsApp before booking; quick replies win the booking."]},
  {k:/store|shop|boutique|cloth|fashion|jewel|florist|furniture|hardware|pet|gift|book|electronic|mobile|phone|tailor/i, name:"retail business",
   tools:["Website or online store","Instagram / Facebook shop","WhatsApp catalog","Delivery or click-and-collect","Stock and price info online"],
   benefits:["An online store sells 24/7 to people outside walking distance.",
     "Instagram and WhatsApp catalogs turn followers into orders.",
     "Showing stock and prices online brings in ready-to-buy customers.",
     "Delivery options reach customers who won't travel."]},
];
const GENERIC = {name:"local business",
  tools:["Mobile-friendly website","Google Business Profile with photos","Social media page","Contact / enquiry form","WhatsApp chat"],
  benefits:["Most customers look a business up online before visiting or calling.",
    "A website builds trust and shows services, prices and reviews in one place.",
    "An enquiry form captures customers outside opening hours.",
    "Social media keeps the business in front of past customers."]};

function industryFor(lead){
  const txt = `${lead.category||""} ${lead.searchQuery||""} ${lead.name||""}`;
  return INDUSTRY.find(i => i.k.test(txt)) || GENERIC;
}

function has(p, what){
  if (!p) return false;
  if (what === "website") return p.website && p.siteLoads;
  if (what === "social") return Object.keys(p.socials||{}).length > 0;
  if (what === "app") return Object.keys(p.apps||{}).length > 0;
  if (what === "booking") return p.booking || p.ordering || p.quoteForm;
  return !!p[what];
}

function buildInsights(lead, a){
  const me = a.lead, comps = a.competitors, p = me.presence;
  // manual overrides the user ticked (e.g. found their Instagram by hand)
  const man = lead.manualPresence || {};
  const mine = {
    website: has(p,"website"), mobile: !!p.mobile,
    social: has(p,"social") || man.facebook || man.instagram || man.tiktok,
    app: has(p,"app") || man.app, booking: has(p,"booking") || man.booking,
  };
  const n = comps.length;
  const cnt = w => comps.filter(c => has(c.presence, w)).length;
  const gaps = [], strengths = [];
  const check = (w, label) => {
    const c = cnt(w);
    if (!mine[w] && c > 0) gaps.push({w, text:`${c} of ${n} nearby competitors have ${label}; this business doesn't.`, weight: c / Math.max(1,n)});
    if (mine[w]) strengths.push(label);
  };
  check("website","a working website");
  if (mine.website && !p.mobile && comps.some(c => c.presence.mobile)) gaps.push({w:"mobile", text:"Their website isn't mobile-friendly, but competitors' sites are.", weight:.6});
  check("social","social media linked");
  check("booking","online booking, ordering or a quote form");
  check("app","a mobile app");
  if (!mine.website && n && cnt("website") === 0) gaps.push({w:"first", text:"No nearby competitor has a proper website either. First mover advantage: they'd stand out immediately.", weight:.7});
  const avg = n ? Math.round(comps.reduce((s,c) => s + c.digitalScore, 0) / n) : null;
  const top = comps.slice().sort((x,y) => y.digitalScore - x.digitalScore)[0];

  // call priority
  const reasons = []; let pts = 0;
  if (!mine.website){ pts += 40; reasons.push("No website"); }
  else if (!p.mobile || !p.https){ pts += 20; reasons.push("Website has problems"); }
  if (me.reviews >= 50){ pts += 25; reasons.push(`${me.reviews} reviews: established and busy`); }
  else if (me.reviews >= 15){ pts += 15; reasons.push(`${me.reviews} reviews: active business`); }
  else if (me.reviews > 0 && me.reviews < 5){ pts -= 5; reasons.push("Very few reviews: may be small or new"); }
  if ((me.rating||0) >= 4.3){ pts += 10; reasons.push(`${me.rating}★ rating: they care about quality`); }
  if (avg !== null && avg - me.digitalScore >= 20){ pts += 15; reasons.push(`Competitors are ahead online (avg ${avg} vs ${me.digitalScore})`); }
  if (lead.phone || me.phone){ pts += 10; } else { pts -= 20; reasons.push("No phone number listed"); }
  const priority = pts >= 60 ? "Hot" : pts >= 35 ? "Warm" : "Low";

  const ind = industryFor(lead);
  const missingTools = ind.tools.filter(t => {
    const tl = t.toLowerCase();
    if (/website|online store/.test(tl) && !/booking|order/.test(tl)) return !mine.website;
    if (/instagram|social|tiktok|facebook|linkedin/.test(tl)) return !mine.social;
    if (/review/.test(tl)) return (me.reviews||0) < 20;
    if (/whatsapp|chat/.test(tl)) return !p.chat;
    if (/app\b/.test(tl)) return !mine.app;
    if (/book|order|sign-up|form|reservation/.test(tl)) return !mine.booking;
    return true;
  });
  return {mine, gaps: gaps.sort((x,y) => y.weight - x.weight), strengths, avg, top, priority, pts, reasons, ind, missingTools};
}

function tick(v){ return v ? '<span class="tag t-no">Yes</span>' : '<span class="tag t-yes">No</span>'; }
function socialsText(p){
  const s = Object.entries(p.socials||{});
  return s.length ? s.map(([k,u]) => `<a target="_blank" rel="noopener" href="${esc(u)}">${SOC[k]||k}</a>`).join(", ") : '<span class="sub">None found</span>';
}
function row(b, isLead){
  const p = b.presence;
  return `<tr ${isLead ? 'style="background:var(--go-soft)"' : ""}>
    <td><div class="nm">${esc(b.name)}${isLead ? " (prospect)" : ""}</div>
      <div class="sub">${b.distanceKm != null ? b.distanceKm + " km away" : ""}${b.mapsUrl ? ` <a target="_blank" rel="noopener" href="${esc(b.mapsUrl)}">map</a>` : ""}</div></td>
    <td>${b.rating ? b.rating + "★" : ""} <span class="sub">${b.reviews || 0}</span></td>
    <td>${has(p,"website") ? `<a target="_blank" rel="noopener" href="${esc(b.website)}">Yes</a>${p.mobile ? "" : ' <span class="sub">(not mobile)</span>'}` : (p.socialOnly ? "Social page only" : tick(false))}</td>
    <td>${socialsText(p)}</td>
    <td>${has(p,"app") ? Object.keys(p.apps).map(k => `<a target="_blank" rel="noopener" href="${esc(p.apps[k])}">${k==="ios"?"iPhone":"Android"}</a>`).join(", ") : tick(false)}</td>
    <td>${tick(has(p,"booking"))}</td>
    <td><span class="score">${b.digitalScore}</span></td>
  </tr>`;
}

function reportText(lead, a, ins){
  const L = [];
  L.push(`PROSPECT REPORT: ${lead.name}`);
  L.push(`${lead.category || ""} | ${lead.address || ""} | ${lead.phone || ""}`);
  L.push(`Call priority: ${ins.priority} (${ins.reasons.join("; ")})`);
  L.push(`Digital score: ${a.lead.digitalScore}/100${ins.avg != null ? ` vs nearby average ${ins.avg}` : ""}`);
  L.push("", "Gaps:"); ins.gaps.forEach(g => L.push("- " + g.text));
  L.push("", "What to offer:"); ins.missingTools.forEach(t => L.push("- " + t));
  L.push("", "Why it helps:"); ins.ind.benefits.forEach(b => L.push("- " + b));
  L.push("", "Nearby competitors:");
  a.competitors.forEach(c => L.push(`- ${c.name} (${c.distanceKm ?? "?"} km, ${c.reviews} reviews, score ${c.digitalScore}): website ${has(c.presence,"website")?"yes":"no"}, social ${Object.keys(c.presence.socials).join("/")||"none"}, app ${has(c.presence,"app")?"yes":"no"}, booking ${has(c.presence,"booking")?"yes":"no"}`));
  return L.join("\n");
}

function aiPrompt(lead, a, ins, kind, me){
  const data = reportText(lead, a, ins);
  const who = me && me.name ? `My name is ${me.name}${me.business ? " from " + me.business : ""}.` : "Use [Your name] as a placeholder for my name.";
  const asks = {
    call: "Write a cold-call script (under 170 words): a 1-sentence opener, 2 specific observations from the data, one question to get them talking, a soft offer of a free sample homepage, and 3 short answers to common objections (no time, too expensive, we get enough customers).",
    email: "Write a cold email (under 140 words) with a subject line. Mention 1-2 specific gaps versus named competitors, one clear benefit, and offer a free sample homepage. End with an easy yes/no question and a one-line opt-out.",
    whatsapp: "Write a short, friendly WhatsApp message (under 60 words) offering a free sample website, mentioning one specific observation. No hard selling.",
    plan: "Write a simple digital growth plan for this business in 5 numbered steps (what to build first, second, etc.) with one sentence each on how it brings more customers. Then suggest a starter package and 2 add-ons I could sell.",
  };
  return `${who}\nI am a web designer contacting this local business.\n\nDATA:\n${data}\n\nTASK: ${asks[kind]}\nOnly use facts from the DATA.`;
}

let dlg;
function ensureDialog(){
  if (dlg) return dlg;
  dlg = document.createElement("dialog");
  dlg.id = "reportDlg";
  dlg.innerHTML = `<div id="reportBody"></div>`;
  document.body.appendChild(dlg);
  const st = document.createElement("style");
  st.textContent = `#reportDlg{border:1px solid var(--line);border-radius:14px;padding:0;max-width:1000px;width:calc(100% - 24px);background:var(--panel);color:var(--ink)}
  #reportDlg::backdrop{background:rgba(10,20,18,.55)}
  #reportBody{padding:18px 20px 22px}
  .rp-head{display:flex;justify-content:space-between;gap:10px;align-items:start;flex-wrap:wrap}
  .prio{font-family:var(--display);font-weight:700;font-size:15px;padding:4px 12px;border-radius:999px}
  .prio.Hot{background:var(--go);color:#fff}.prio.Warm{background:var(--warn-soft);color:var(--warn)}.prio.Low{background:var(--chip);color:var(--muted)}
  .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px;margin:14px 0}
  .cols ul{margin:4px 0;padding-left:18px}.cols li{margin:3px 0}
  .aiout{white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:8px;font-size:14px}
  .man label{display:inline-flex;gap:5px;align-items:center;margin:0 10px 0 0;color:var(--ink)} .man input{width:auto}`;
  document.head.appendChild(st);
  dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
  return dlg;
}

async function openReport(lead, onSave){
  ensureDialog();
  const body = dlg.querySelector("#reportBody");
  dlg.showModal();
  if (!lead.analysis){
    body.innerHTML = `<p><span class="spin"></span> Finding nearby competitors and checking websites, social media and apps for <b>${esc(lead.name)}</b>… (10–40 seconds)</p>`;
    try {
      const S = window.LF.settings();
      lead.analysis = await window.LF.api("/api/analyze", {lead, source: window.LF.sourceOf(lead),
        apiKey: S.apiKey, serpKey: S.serpKey, radius: +(S.radius || 3000)});
    } catch(err){
      body.innerHTML = `<div class="msg err">${esc(err.message)}</div><button class="btn" onclick="this.closest('dialog').close()">Close</button>`;
      return;
    }
  }
  render(lead, onSave);
}

function render(lead, onSave){
  const a = lead.analysis, ins = buildInsights(lead, a);
  lead.priority = ins.priority;
  onSave && onSave(lead);
  const body = dlg.querySelector("#reportBody");
  const man = lead.manualPresence || {};
  body.innerHTML = `
  <div class="rp-head">
    <div><h2 style="margin:0">${esc(lead.name)}</h2>
      <div class="sub">${esc(lead.category)} · ${esc(lead.address)}</div>
      <div class="sub">${esc(lead.phone || "No phone")} ${lead.email ? " · " + esc(lead.email) : ""}</div></div>
    <div style="text-align:right"><span class="prio ${ins.priority}">${ins.priority} lead</span>
      <div class="sub" style="margin-top:6px">Digital score ${a.lead.digitalScore}/100${ins.avg != null ? ` · competitors avg ${ins.avg}` : ""}</div></div>
  </div>
  <p class="sub" style="margin:8px 0 0">Why: ${esc(ins.reasons.join(" · ") || "Not enough data")}</p>
  ${a.competitorError ? `<div class="msg err">Competitors: ${esc(a.competitorError)}</div>` : ""}

  <div class="cols">
    <div class="panel" style="margin:0"><h3 style="margin-top:0">Gaps vs competitors</h3>
      ${ins.gaps.length ? `<ul>${ins.gaps.map(g => `<li>${esc(g.text)}</li>`).join("")}</ul>` : '<p class="sub">No clear gaps found. Pitch improvements (speed, design, SEO) instead.</p>'}
      ${ins.top && ins.top.digitalScore > a.lead.digitalScore ? `<p class="sub">Strongest online nearby: <b>${esc(ins.top.name)}</b> (score ${ins.top.digitalScore}). Use them as the example in your pitch.</p>` : ""}
    </div>
    <div class="panel" style="margin:0"><h3 style="margin-top:0">What to offer (${esc(ins.ind.name)})</h3>
      <ul>${ins.missingTools.map(t => `<li>${esc(t)}</li>`).join("") || "<li>Redesign, speed and SEO improvements</li>"}</ul></div>
    <div class="panel" style="margin:0"><h3 style="margin-top:0">How it boosts their sales</h3>
      <ul>${ins.ind.benefits.map(b => `<li>${esc(b)}</li>`).join("")}</ul></div>
  </div>

  <h3>Nearby competitors (${a.competitors.length}, within about ${a.radiusKm} km)</h3>
  <div class="tablewrap"><table style="min-width:760px">
    <thead><tr><th>Business</th><th>Reviews</th><th>Website</th><th>Social media</th><th>App</th><th>Booking / order</th><th>Score</th></tr></thead>
    <tbody>${row(a.lead, true)}${a.competitors.map(c => row(c, false)).join("") || '<tr><td colspan="7" class="empty">No competitors found nearby.</td></tr>'}</tbody>
  </table></div>
  <p class="note">Social media and apps are detected from each business's website. Businesses without a website may still have Facebook or Instagram. Check with the Research links and tick below.</p>
  <div class="man sub">Found by hand:
    ${["facebook","instagram","tiktok","app","booking"].map(k => `<label><input type="checkbox" data-man="${k}" ${man[k]?"checked":""}> ${k==="app"?"App":k==="booking"?"Online booking":SOC[k]}</label>`).join("")}
    <a class="btn sm" target="_blank" rel="noopener" href="https://www.facebook.com/search/pages?q=${encodeURIComponent(lead.name)}">Search Facebook</a>
    <a class="btn sm" target="_blank" rel="noopener" href="https://www.google.com/search?q=${encodeURIComponent(lead.name + " " + (lead.address||"").split(",").slice(-2).join(" ") + " instagram OR tiktok")}">Search Instagram/TikTok</a>
  </div>

  <h3>Write outreach with AI</h3>
  <div class="toolbar">
    <button class="btn sm primary" data-ai="call">Call script</button>
    <button class="btn sm" data-ai="email">Cold email</button>
    <button class="btn sm" data-ai="whatsapp">WhatsApp message</button>
    <button class="btn sm" data-ai="plan">Growth plan + package</button>
    <span class="sub">Uses the free AI set in Settings (Ollama by default).</span>
  </div>
  <div id="aiOut"></div>

  <div class="toolbar" style="margin-top:16px">
    <button class="btn sm" id="rpCopy">Copy report</button>
    <button class="btn sm" id="rpRefresh">Re-run analysis</button>
    ${window.LF.inList(lead) ? "" : '<button class="btn sm primary" id="rpAdd">Add to my list</button>'}
    <div class="grow"></div>
    <button class="btn sm" id="rpClose">Close</button>
  </div>`;

  body.querySelectorAll("[data-man]").forEach(cb => cb.onchange = () => {
    lead.manualPresence = {...(lead.manualPresence||{}), [cb.dataset.man]: cb.checked};
    render(lead, onSave);
  });
  body.querySelector("#rpClose").onclick = () => dlg.close();
  body.querySelector("#rpRefresh").onclick = () => { delete lead.analysis; openReport(lead, onSave); };
  body.querySelector("#rpCopy").onclick = async e => {
    try { await navigator.clipboard.writeText(reportText(lead, a, ins)); e.target.textContent = "Copied"; } catch(_){ alert(reportText(lead, a, ins)); }
  };
  const add = body.querySelector("#rpAdd");
  if (add) add.onclick = () => { window.LF.addToList(lead); add.remove(); };
  body.querySelectorAll("[data-ai]").forEach(b => b.onclick = async () => {
    const out = body.querySelector("#aiOut");
    out.innerHTML = '<p class="sub"><span class="spin"></span> Writing… (local AI can take up to a minute)</p>';
    const S = window.LF.settings();
    try {
      const j = await window.LF.api("/api/ai", {prompt: aiPrompt(lead, a, ins, b.dataset.ai, {name:S.myName, business:S.myBusiness}), ai: S.ai || {}});
      out.innerHTML = `<div class="aiout">${esc(j.text)}</div><button class="btn sm" id="aiCopy" style="margin-top:6px">Copy</button>`;
      out.querySelector("#aiCopy").onclick = e => { navigator.clipboard.writeText(j.text).then(() => e.target.textContent = "Copied"); };
      lead.aiNotes = {...(lead.aiNotes||{}), [b.dataset.ai]: j.text};
      onSave && onSave(lead);
    } catch(err){
      out.innerHTML = `<div class="msg err">${esc(err.message)}</div><p class="sub">No AI set up? Use "Copy report" and paste it into any free AI chat with: "Write a cold-call script from this report."</p>`;
    }
  });
}

window.LFReport = {open: openReport, insights: buildInsights};
})();
