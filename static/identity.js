/* LeadFinder: Digital identity check, owner finder, package builder and proposals */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function store(k, d, v){
  try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; }
        const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; }
}
const api = (p, b) => window.LF.api(p, b || {});

/* ------------------------------------------------------------------ pricing */
const DEFAULT_ITEMS = [
  {k:"website",  name:"Mobile-friendly website (up to 5 pages)", price:600, when:["website"], note:"Home, services, about, reviews, contact"},
  {k:"redesign", name:"Website redesign (mobile, HTTPS, speed)", price:450, when:["quality"], note:"Replaces an outdated or broken site"},
  {k:"gbp",      name:"Google Business Profile setup & optimisation", price:120, when:["google"], note:"Photos, categories, hours, services"},
  {k:"reviews",  name:"Review booster (QR code + WhatsApp review link)", price:60, when:["reviews"], note:"Helps collect more 5★ reviews"},
  {k:"email",    name:"Professional email (name@business)", price:80, when:["email"], note:"Setup on their own domain"},
  {k:"social",   name:"Branded Facebook & Instagram pages", price:150, when:["social","social2"], note:"Profile, cover, bio, first posts"},
  {k:"booking",  name:"Online booking / ordering / quote form", price:250, when:["booking"], note:"Captures customers 24/7"},
  {k:"whatsapp", name:"WhatsApp chat button & catalog", price:60, when:["chat"], note:"One-tap messaging from the site"},
  {k:"logo",     name:"Logo & brand kit", price:180, when:[], note:"Logo, colours, fonts"},
  {k:"seo",      name:"Local SEO starter", price:250, when:["website","quality"], note:"Service pages, speed, Google indexing"},
  {k:"pwa",      name:"Installable web app (PWA)", price:1200, when:["app"], note:"Home-screen app with booking / loyalty"},
  {k:"care",     name:"Monthly care plan", price:60, monthly:true, when:[], note:"Hosting, updates, backups, 4 social posts"},
];
const DEFAULT_TIERS = {
  Starter: {items:["website","redesign","gbp","whatsapp","email"], discount:0},
  Growth:  {items:["website","redesign","gbp","whatsapp","email","social","booking","logo","seo","reviews"], discount:10},
  Premium: {items:["website","redesign","gbp","whatsapp","email","social","booking","logo","seo","reviews","pwa","care"], discount:15},
};
let pricing = store("lf-pricing", {currency:"USD", symbol:"$", items: DEFAULT_ITEMS, tiers: DEFAULT_TIERS, validDays: 14, timeline:"7–14 days", terms:"50% to start, 50% on launch."});
pricing.items = DEFAULT_ITEMS.map(d => Object.assign({}, d, (pricing.items||[]).find(x => x.k === d.k) || {}));
const money = n => `${pricing.symbol}${Math.round(n).toLocaleString()}`;

function suggestedItems(lead){
  const id = lead.identity; if (!id) return new Set();
  const miss = new Set(id.missing);
  const s = new Set();
  const hasSite = id.presence && id.presence.website && id.presence.siteLoads;
  pricing.items.forEach(it => {
    if (it.k === "website" && hasSite) return;
    if (it.k === "redesign" && (!hasSite || !miss.has("quality"))) return;
    if (it.k === "seo" && hasSite && !miss.has("quality")) return;
    if (it.k === "pwa" && id.appFit.level === "Low") return;
    if (it.when.some(w => miss.has(w))) s.add(it.k);
  });
  if (!hasSite) { s.add("seo"); }
  s.add("care");
  return s;
}
function tiers(lead, selected){
  // Each tier must add something real over the one before it; otherwise it is dropped,
  // and a tier only gets its bigger discount if it adds one-time work.
  const out = {}; let prev = null;
  Object.entries(pricing.tiers).forEach(([name, t]) => {
    const items = pricing.items.filter(it => t.items.includes(it.k) && selected.has(it.k));
    const once = items.filter(i => !i.monthly).reduce((a,i) => a + (+i.price||0), 0);
    const monthly = items.filter(i => i.monthly).reduce((a,i) => a + (+i.price||0), 0);
    if (!items.length) return;
    if (prev && items.length === prev.items.length) return;          // nothing new: skip tier
    let disc = t.discount || 0;
    if (prev && once <= prev.once) disc = prev.discount;             // only monthly added: keep discount
    const total = once * (1 - disc/100);
    if (prev && total < prev.total) disc = prev.discount;
    out[name] = {items, once, total: once * (1 - disc/100), discount: disc, monthly};
    prev = out[name];
  });
  return out;
}
const recName = T => T.Growth ? "Growth" : Object.keys(T).slice(-1)[0];
function shownMissing(id){
  const miss = id.parts.filter(p => !p.ok);
  const keys = new Set(miss.map(p => p.key));
  return miss.filter(p => !(p.key === "quality" && keys.has("website")) && !(p.key === "social2" && keys.has("social"))
                        && !(p.key === "app" && id.appFit.level === "Low"));
}
const lcFirst = t => t.replace(/^PWA\b/, "an installable web app").replace(/^([A-Z])(?=[a-z])/, m => m.toLowerCase());

/* ------------------------------------------------------------------ identity check */
async function check(lead, withOwner = true){
  const S = window.LF.settings();
  const r = await api("/api/identity", {lead, owner: withOwner, useAI: store("lf-owner-ai", true)});
  lead.identity = Object.assign({}, r); delete lead.identity.owner;
  if (r.owner){
    lead.ownerInfo = r.owner;
    if (r.owner.name && !lead.ownerLocked){ lead.ownerName = r.owner.name; lead.contactName = r.owner.first; }
  }
  if (!lead.email && r.email && r.email.emails && r.email.emails[0]) lead.email = r.email.emails[0];
  window.LF.saveLead(lead);
  return lead;
}
function badge(l){
  if (!l.identity) return "";
  const s = l.identity.score, c = s < 40 ? "t-no" : s < 70 ? "t-weak" : "t-yes";
  return `<div style="margin-top:4px"><button class="tag ${c}" data-idopen="${esc(l.id)}" style="border:0;cursor:pointer" title="Digital identity score">ID ${s}/100</button></div>`;
}

/* ------------------------------------------------------------------ dialog */
let dlg;
function ensure(){
  if (dlg) return;
  dlg = document.createElement("dialog"); dlg.id = "idDlg";
  dlg.style.cssText = "border:1px solid var(--line);border-radius:14px;padding:0;max-width:1000px;width:calc(100% - 24px);background:var(--panel);color:var(--ink)";
  document.body.appendChild(dlg);
  dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
}
async function open(lead){
  ensure(); dlg.showModal();
  if (!lead.identity){
    dlg.innerHTML = `<div style="padding:22px"><span class="spin"></span> Checking ${esc(lead.name)}'s website, social media, email and owner… (10–30 seconds)</div>`;
    try { await check(lead, true); }
    catch(err){ dlg.innerHTML = `<div style="padding:22px"><div class="msg err">${esc(err.message)}</div><button class="btn" onclick="this.closest('dialog').close()">Close</button></div>`; return; }
  }
  render(lead);
}
function ring(score){
  const r = 34, c = 2 * Math.PI * r, col = score < 40 ? "var(--go)" : score < 70 ? "var(--warn)" : "var(--muted)";
  return `<svg width="92" height="92" viewBox="0 0 92 92" role="img" aria-label="Score ${score} of 100">
    <circle cx="46" cy="46" r="${r}" fill="none" stroke="var(--chip)" stroke-width="9"/>
    <circle cx="46" cy="46" r="${r}" fill="none" stroke="${col}" stroke-width="9" stroke-linecap="round"
      stroke-dasharray="${c * score / 100} ${c}" transform="rotate(-90 46 46)"/>
    <text x="46" y="52" text-anchor="middle" font-family="var(--display)" font-weight="700" font-size="22" fill="var(--ink)">${score}</text></svg>`;
}
function render(lead){
  const id = lead.identity, o = lead.ownerInfo || {};
  const sel = lead.pkgSelected ? new Set(lead.pkgSelected) : suggestedItems(lead);
  const T = tiers(lead, sel);
  const fitCol = id.appFit.level === "High" ? "t-no" : id.appFit.level === "Medium" ? "t-weak" : "t-yes";
  dlg.innerHTML = `<div style="padding:18px 20px 22px">
  <div class="toolbar" style="margin:0;align-items:center">
    ${ring(id.score)}
    <div class="grow"><h2 style="margin:0">${esc(lead.name)}</h2>
      <div class="sub">${esc(lead.category||"")} · ${esc(lead.address||"")}</div>
      <div class="sub">Digital identity: <b>${esc(id.grade)}</b> · checked ${esc(id.checkedAt)} · lower score means a bigger opportunity for you</div></div>
    <button class="btn sm" data-x="recheck">Re-check</button><button class="btn sm" data-x="close">Close</button>
  </div>

  <div class="cols" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:14px;margin-top:14px">
    <div class="panel" style="margin:0">
      <h3 style="margin-top:0">What they have</h3>
      ${id.parts.map(p => `<div style="display:flex;gap:8px;align-items:flex-start;margin:5px 0">
        <span aria-hidden="true" style="color:${p.ok ? "var(--go)" : "var(--stop)"};font-weight:700">${p.ok ? "✓" : "✗"}</span>
        <div style="flex:1">${esc(p.label)} <span class="sub">${p.points}/${p.max}</span>
        ${p.key === "app" && id.appFit.level === "Low" ? '<div class="sub">Not needed for this business</div>' : !p.ok && p.tip ? `<div class="sub">${esc(p.tip)}</div>` : ""}</div></div>`).join("")}
      <div class="sub" style="margin-top:6px">Email: ${id.email.provider ? esc(id.email.provider) : "no mail on their domain"}${id.email.freeProvider ? " · uses a free address" : ""}</div>
      <div class="sub">Social: ${Object.keys(id.presence.socials).map(esc).join(", ") || "none found on the website"}</div>
    </div>

    <div class="panel" style="margin:0">
      <h3 style="margin-top:0">Owner</h3>
      <label for="idOwner">Name used in emails and scripts</label>
      <input id="idOwner" value="${esc(lead.ownerName || "")}" placeholder="Not found yet: type it if you know it">
      <div class="sub" style="margin-top:4px">${o.name ? `Found: <b>${esc(o.name)}</b>${o.role ? " (" + esc(o.role) + ")" : ""} · source: ${esc(o.source)}` : "No owner name found automatically."}</div>
      ${(o.candidates||[]).length > 1 ? `<div class="sub">Other names: ${o.candidates.slice(1).map(c => `<button class="tag t-yes" style="border:0;cursor:pointer" data-pick="${esc(c.name)}">${esc(c.name)}</button>`).join(" ")}</div>` : ""}
      ${(o.candidates||[])[0] && o.candidates[0].context ? `<div class="sub" style="margin-top:4px">“…${esc(o.candidates[0].context)}…”</div>` : ""}
      ${o.note ? `<div class="sub" style="color:var(--warn)">${esc(o.note)}</div>` : ""}
      <div class="acts" style="margin-top:6px">${(o.links||[]).map(k => `<a class="btn sm" target="_blank" rel="noopener" href="${esc(k.url)}">${esc(k.label)}</a>`).join("")}</div>
      <p class="note">Use names only to personalise business outreach. Always check before sending.</p>

      <h3>App fit <span class="tag ${fitCol}">${esc(id.appFit.level)}</span></h3>
      <div class="sub">${esc(id.appFit.why)}. ${esc(id.appFit.idea)}.</div>
      ${id.hasManifest ? '<div class="sub">Their site is already installable (has a web app manifest).</div>' : ""}
    </div>
  </div>

  <h3>Package builder</h3>
  <p class="sub" style="margin-top:0">Pre-ticked items match what's missing. Prices come from Settings → Packages & pricing.</p>
  <div class="tablewrap"><table style="min-width:640px"><thead><tr><th></th><th>Item</th><th>Why</th><th>Price</th></tr></thead><tbody>
    ${pricing.items.map(it => `<tr><td><input type="checkbox" data-item="${it.k}" ${sel.has(it.k) ? "checked" : ""} style="width:auto" aria-label="${esc(it.name)}"></td>
      <td class="nm">${esc(it.name)}</td><td class="sub">${esc(it.note)}</td><td>${money(it.price)}${it.monthly ? "/mo" : ""}</td></tr>`).join("")}
  </tbody></table></div>
  <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px;margin-top:10px">
    ${Object.keys(T).length ? "" : '<p class="sub">Tick at least one item.</p>'}${Object.entries(T).map(([n, t]) => `<div class="panel" style="margin:0;${n===recName(T) ? "border-color:var(--go)" : ""}">
      <div class="nm">${n}${n===recName(T) ? ' <span class="tag t-no">recommended</span>' : ""}</div>
      <div class="score" style="font-size:24px">${t.items.length ? money(t.total) : "–"}</div>
      <div class="sub">${t.discount && t.items.length ? `<s>${money(t.once)}</s> save ${t.discount}%` : ""}${t.monthly ? ` + ${money(t.monthly)}/mo` : ""}</div>
      <div class="sub">${t.items.map(i => esc(i.name)).join(" · ") || "Nothing selected in this tier"}</div></div>`).join("")}
  </div>

  <div class="toolbar" style="margin-top:14px">
    <button class="btn primary" data-x="proposal">Create proposal</button>
    <button class="btn" data-x="draft">Add "digital identity" email draft</button>
    <button class="btn" data-x="aiintro">Write proposal intro with AI</button>
    ${window.LF.inList(lead) ? "" : '<button class="btn" data-x="add">Add to my list</button>'}
    <span class="sub" id="idMsg"></span>
  </div>
  <textarea id="idIntro" rows="4" placeholder="Proposal intro (optional). Leave empty for the default." style="margin-top:6px">${esc(lead.proposalIntro || "")}</textarea>
  </div>`;

  dlg.querySelector("#idOwner").onchange = e => {
    lead.ownerName = e.target.value.trim(); lead.ownerLocked = true;
    const n = lead.ownerName.replace(/^Dr\.?\s+/, "");
    lead.contactName = /^Dr/.test(lead.ownerName) ? "Dr. " + n.split(" ").pop() : n.split(" ")[0] || "";
    window.LF.saveLead(lead);
  };
  dlg.querySelector("#idIntro").onchange = e => { lead.proposalIntro = e.target.value; window.LF.saveLead(lead); };
  dlg.querySelectorAll("[data-pick]").forEach(b => b.onclick = () => {
    dlg.querySelector("#idOwner").value = b.dataset.pick; dlg.querySelector("#idOwner").dispatchEvent(new Event("change"));
  });
  dlg.querySelectorAll("[data-item]").forEach(cb => cb.onchange = () => {
    const s = new Set(lead.pkgSelected || suggestedItems(lead));
    cb.checked ? s.add(cb.dataset.item) : s.delete(cb.dataset.item);
    lead.pkgSelected = [...s]; window.LF.saveLead(lead); render(lead);
  });
  dlg.onclick = async e => {
    if (e.target === dlg) return;
    const x = e.target.dataset.x; if (!x) return;
    const msg = dlg.querySelector("#idMsg");
    if (x === "close") return dlg.close();
    if (x === "recheck"){ delete lead.identity; open(lead); return; }
    if (x === "add"){ window.LF.addLeads([lead]); e.target.remove(); return; }
    if (x === "proposal") return proposal(lead);
    if (x === "draft"){
      if (!window.LFOutreach || !window.LFOutreach.addDraft) return;
      const n = window.LFOutreach.addDraft(lead, "Digital identity");
      msg.textContent = n ? "Draft added to Emails → Outbox." : "This lead isn't in My list yet, or already has a first-email draft.";
      return;
    }
    if (x === "aiintro"){
      msg.innerHTML = '<span class="spin"></span>';
      const S = window.LF.settings();
      const missing = shownMissing(id).map(p => p.label).join(", ");
      try {
        const r = await api("/api/ai", {ai:{provider:"pool"}, prompt:
          `Write a warm, specific 70-word introduction for a website/digital-identity proposal from ${S.myName||"[your name]"} (${S.myBusiness||"web studio"}) to ${lead.ownerName || "the owner"} of ${lead.name}, a ${lead.category} with ${lead.reviews||0} reviews. Currently missing online: ${missing || "a few improvements"}. Explain in plain words how fixing this brings them more customers. No invented numbers.`});
        dlg.querySelector("#idIntro").value = r.text; lead.proposalIntro = r.text; window.LF.saveLead(lead); msg.textContent = "";
      } catch(err){ msg.textContent = err.message; }
    }
  };
}

/* ------------------------------------------------------------------ proposal */
function proposal(lead){
  const S = window.LF.settings(), M = store("lf-mail", {}), id = lead.identity;
  const sel = lead.pkgSelected ? new Set(lead.pkgSelected) : suggestedItems(lead);
  const T = tiers(lead, sel);
  const date = new Date(), valid = new Date(Date.now() + (pricing.validDays||14) * 864e5);
  const fmt = d => d.toLocaleDateString(undefined, {day:"numeric", month:"long", year:"numeric"});
  const missing = shownMissing(id);
  const have = id.parts.filter(p => p.ok && !(p.key === "app" && id.appFit.level === "Low"));
  const comp = lead.analysis && lead.analysis.competitors ? lead.analysis.competitors.slice().sort((a,b) => b.digitalScore - a.digitalScore)[0] : null;
  const intro = lead.proposalIntro || `Thank you for taking the time to look at this. ${lead.name} has a great reputation${lead.reviews ? ` (${lead.reviews} reviews${lead.rating ? " at " + lead.rating + "★" : ""})` : ""}, but today some customers searching online can't find or book you easily. This proposal shows what's missing and three simple packages to give ${lead.name} a complete digital identity.`;
  const doc = `<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Digital identity proposal – ${esc(lead.name)}</title>
<style>
:root{--ink:#16302B;--muted:#5B6F6A;--line:#D3DEDA;--go:#0B7A55;--soft:#DDF1E8;--warn:#9A5B00}
*{box-sizing:border-box}body{margin:0;font-family:"Segoe UI",system-ui,sans-serif;color:var(--ink);background:#fff;line-height:1.55}
.page{max-width:820px;margin:0 auto;padding:40px 36px}
h1{font-size:34px;line-height:1.1;margin:6px 0 4px;letter-spacing:-.01em}h2{font-size:19px;margin:28px 0 8px;border-bottom:2px solid var(--soft);padding-bottom:4px}
.muted{color:var(--muted);font-size:14px}.kicker{text-transform:uppercase;letter-spacing:.12em;font-size:12px;color:var(--go);font-weight:700}
.score{display:flex;gap:18px;align-items:center;background:var(--soft);border-radius:12px;padding:14px 18px;margin:18px 0}
.big{font-size:40px;font-weight:800;color:var(--go);line-height:1}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}ul{margin:4px 0;padding-left:20px}li{margin:3px 0}
.tiers{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.tier{border:1px solid var(--line);border-radius:12px;padding:14px}
.tier.rec{border:2px solid var(--go)}.price{font-size:26px;font-weight:800;margin:4px 0}
table{border-collapse:collapse;width:100%;font-size:14px}td{border-bottom:1px solid var(--line);padding:6px 4px;vertical-align:top}
.cta{background:var(--ink);color:#fff;border-radius:12px;padding:16px 20px;margin-top:22px}
@media (max-width:640px){.two,.tiers{grid-template-columns:1fr}.page{padding:24px 18px}}
@media print{.noprint{display:none}.page{padding:0}}
</style></head><body><div class="page">
<div class="noprint" style="text-align:right;margin-bottom:10px"><button onclick="print()" style="padding:8px 14px;border-radius:8px;border:1px solid #ccc;background:#fff;cursor:pointer">Print / Save as PDF</button></div>
<div class="kicker">Digital identity proposal</div>
<h1>${esc(lead.name)}</h1>
<div class="muted">Prepared for ${esc(lead.ownerName || "the owner")} · ${fmt(date)} · by ${esc(S.myName || "")}${S.myBusiness ? ", " + esc(S.myBusiness) : ""}</div>
<p>${esc(intro)}</p>
<div class="score"><div class="big">${id.score}<span style="font-size:18px">/100</span></div>
<div><b>Your digital identity today: ${esc(id.grade)}</b><div class="muted">Based on a check of your website, Google listing, social media, booking options and email${comp ? `. For comparison, ${esc(comp.name)} nearby scores ${comp.digitalScore}/100 on our competitor check.` : "."}</div></div></div>
<div class="two"><div><h2>What's working</h2><ul>${have.map(p => `<li>${esc(p.label)}</li>`).join("") || "<li>Your reputation with customers</li>"}</ul></div>
<div><h2>What's missing</h2><ul>${missing.map(p => `<li><b>${esc(p.label)}</b><br><span class="muted">${esc(p.tip)}</span></li>`).join("") || "<li>Only small improvements</li>"}</ul></div></div>
${id.appFit.level !== "Low" ? `<h2>About an app</h2><p>${esc(id.appFit.why)}, so an installable web app makes sense later: ${esc(lcFirst(id.appFit.idea))}. It installs on customers' phones from your website, without app-store fees, and costs far less than a traditional app.</p>` : ""}
<h2>Packages</h2>
<div class="tiers" style="grid-template-columns:repeat(${Math.max(1, Object.keys(T).length)},1fr)">${Object.entries(T).map(([n,t]) => `<div class="tier ${n===recName(T)?"rec":""}"><div class="kicker">${n}${n===recName(T)?" · recommended":""}</div>
<div class="price">${t.items.length ? money(t.total) : "–"}</div><div class="muted">${t.discount && t.items.length ? `includes ${t.discount}% bundle saving` : "one-time"}${t.monthly ? ` + ${money(t.monthly)}/month` : ""}</div>
<ul>${t.items.map(i => `<li>${esc(i.name)}</li>`).join("")}</ul></div>`).join("")}</div>
<h2>Details</h2><table>${pricing.items.filter(i => sel.has(i.k)).map(i => `<tr><td><b>${esc(i.name)}</b><br><span class="muted">${esc(i.note)}</span></td><td style="text-align:right;white-space:nowrap">${money(i.price)}${i.monthly ? "/mo" : ""}</td></tr>`).join("")}</table>
<h2>Timeline & terms</h2><p>Typical delivery: ${esc(pricing.timeline)}. ${esc(pricing.terms)} Prices in ${esc(pricing.currency)}, valid until ${fmt(valid)}.</p>
<div class="cta"><b>Next step:</b> reply to this email or call ${esc(M.phone || "[your phone]")} and tell me which package you'd like. I'll send a free homepage preview before you pay anything.<br>
<span style="opacity:.8">${esc(S.myName||"")} · ${esc(S.myBusiness||"")} · ${esc(M.website||"")}</span></div>
</div></body></html>`;
  const blob = new Blob([doc], {type:"text/html"});
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = `proposal-${String(lead.name).toLowerCase().replace(/[^a-z0-9]+/g,"-")}.html`; a.click();
  window.open(url, "_blank");
  lead.proposalAt = new Date().toISOString().slice(0,10); window.LF.saveLead(lead);
}

/* ------------------------------------------------------------------ bulk + settings + sender check */
async function bulk(leads, btn){
  const targets = leads.filter(l => !l.identity);
  if (!targets.length){ alert("All shown businesses are already checked."); return; }
  if (targets.length > 40 && !confirm(`Check ${targets.length} businesses? This reads their websites and can take a few minutes.`)) return;
  const label = btn.textContent; btn.disabled = true; let done = 0;
  const q = [...targets];
  const worker = async () => { while (q.length){ const l = q.shift(); try { await check(l, true); } catch(e){} done++; btn.textContent = `Checking ${done}/${targets.length}…`; } };
  await Promise.all([worker(), worker(), worker()]);
  btn.disabled = false; btn.textContent = label; window.LF.refresh();
}
function mountSettings(){
  const p = document.createElement("div");
  p.className = "panel guide"; p.style.maxWidth = "none";
  p.innerHTML = `<h2>Packages & pricing</h2>
    <p class="sub" style="margin-top:-4px">Used by the package builder and proposals. The defaults are only examples: set prices for your market.</p>
    <div class="grid"><div><label>Currency code</label><input id="prCur"></div><div><label>Symbol</label><input id="prSym"></div>
      <div><label>Delivery time</label><input id="prTime"></div><div><label>Quote valid (days)</label><input id="prValid" type="number" min="1"></div></div>
    <label style="margin-top:8px">Payment terms</label><input id="prTerms">
    <div class="tablewrap" style="margin-top:10px"><table style="min-width:760px"><thead><tr><th>Item</th><th>Price</th>
      ${Object.keys(DEFAULT_TIERS).map(t => `<th>${t}</th>`).join("")}</tr></thead><tbody id="prRows"></tbody></table></div>
    <div class="grid" style="margin-top:8px">${Object.keys(DEFAULT_TIERS).map(t => `<div><label>${t} bundle discount %</label><input type="number" min="0" max="50" data-disc="${t}"></div>`).join("")}</div>
    <button class="btn primary" id="prSave" style="margin-top:10px">Save pricing</button> <button class="btn" id="prReset" style="margin-top:10px">Reset to defaults</button>
    <h2 style="margin-top:22px">Owner finder</h2>
    <div class="grid"><div><label for="chKey">Companies House API key (UK directors, free)</label><input id="chKey" type="password" autocomplete="off"></div>
      <div><label style="display:flex;gap:6px;align-items:center;color:var(--ink)"><input type="checkbox" id="ownerAI" style="width:auto"> Use free AI to read About pages when no name is found</label></div>
      <div><button class="btn" id="chSave" style="width:100%">Save</button></div></div>
    <p class="note">Get a key: developer.company-information.service.gov.uk → create account → create application (Live) → create REST key.</p>`;
  $("#tab-settings").appendChild(p);
  const fill = () => {
    $("#prCur").value = pricing.currency; $("#prSym").value = pricing.symbol; $("#prTime").value = pricing.timeline;
    $("#prValid").value = pricing.validDays; $("#prTerms").value = pricing.terms;
    $("#prRows").innerHTML = pricing.items.map(it => `<tr data-k="${it.k}"><td>${esc(it.name)}${it.monthly ? ' <span class="sub">(monthly)</span>' : ""}</td>
      <td><input type="number" min="0" value="${it.price}" data-price style="max-width:110px"></td>
      ${Object.keys(DEFAULT_TIERS).map(t => `<td><input type="checkbox" data-tier="${t}" style="width:auto" ${pricing.tiers[t].items.includes(it.k) ? "checked" : ""} aria-label="${t}"></td>`).join("")}</tr>`).join("");
    document.querySelectorAll("[data-disc]").forEach(i => i.value = pricing.tiers[i.dataset.disc].discount);
  };
  fill();
  $("#prSave").onclick = () => {
    pricing.currency = $("#prCur").value.trim() || "USD"; pricing.symbol = $("#prSym").value; pricing.timeline = $("#prTime").value;
    pricing.validDays = +$("#prValid").value || 14; pricing.terms = $("#prTerms").value;
    const tiersNew = {}; Object.keys(DEFAULT_TIERS).forEach(t => tiersNew[t] = {items: [], discount: +document.querySelector(`[data-disc="${t}"]`).value || 0});
    document.querySelectorAll("#prRows tr").forEach(tr => {
      const it = pricing.items.find(i => i.k === tr.dataset.k); it.price = +tr.querySelector("[data-price]").value || 0;
      tr.querySelectorAll("[data-tier]").forEach(cb => { if (cb.checked) tiersNew[cb.dataset.tier].items.push(it.k); });
    });
    pricing.tiers = tiersNew; store("lf-pricing", null, pricing); $("#prSave").textContent = "Saved";
    setTimeout(() => $("#prSave").textContent = "Save pricing", 1500);
  };
  $("#prReset").onclick = () => { pricing = {currency:"USD", symbol:"$", items: JSON.parse(JSON.stringify(DEFAULT_ITEMS)), tiers: JSON.parse(JSON.stringify(DEFAULT_TIERS)), validDays:14, timeline:"7–14 days", terms:"50% to start, 50% on launch."}; store("lf-pricing", null, pricing); fill(); };
  $("#ownerAI").checked = store("lf-owner-ai", true);
  api("/api/assistant/config").then(r => { $("#chKey").value = r.config.keys.ch || ""; }).catch(()=>{});
  $("#chSave").onclick = async () => {
    store("lf-owner-ai", null, $("#ownerAI").checked);
    await api("/api/assistant/config", {save: {keys: {ch: $("#chKey").value.trim()}}});
    $("#chSave").textContent = "Saved";
  };
}
function mountSenderCheck(){
  const btn = $("#emSaveSender"); if (!btn) return;
  btn.insertAdjacentHTML("afterend", ' <button class="btn" id="emCheckDomain">Check my sending domain</button><div id="emDomainOut"></div>');
  $("#emCheckDomain").onclick = async () => {
    const email = $("#smUser").value.trim() || $("#emWebsite").value.trim();
    if (!email){ alert("Enter your SMTP username/email first."); return; }
    const out = $("#emDomainOut"); out.innerHTML = '<p class="sub"><span class="spin"></span> Checking DNS…</p>';
    try {
      const r = await api("/api/sender-check", {email});
      out.innerHTML = `<div class="tablewrap" style="margin-top:8px"><table style="min-width:560px"><thead><tr><th>Check</th><th>Result</th><th>Details / fix</th></tr></thead><tbody>
        ${r.checks.map(c => `<tr><td class="nm">${esc(c.name)}</td><td><span class="tag ${c.status==="pass"?"t-no":c.status==="warn"?"t-weak":"t-yes"}">${c.status.toUpperCase()}</span></td>
        <td class="sub">${esc(c.detail)}${c.fix ? `<br><b>Fix:</b> ${esc(c.fix)}` : ""}</td></tr>`).join("")}</tbody></table></div>
        <p class="note">Mailbox providers expect SPF or DKIM on every sender and a very low spam-report rate. Keep volumes small, personal and easy to opt out of.</p>`;
    } catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  };
}

function init(){
  window.LFIdentity = {badge, open, check, bulk};
  mountSettings(); mountSenderCheck();
  $("#bulkEmail").insertAdjacentHTML("beforebegin", '<button class="btn sm primary" id="idBulk">Digital identity check</button>');
  $("#idBulk").onclick = e => bulk(window.LF.getShown(), e.target);
  $("#exportList").insertAdjacentHTML("beforebegin", '<button class="btn sm" id="idBulkList">Identity check</button>');
  $("#idBulkList").onclick = e => bulk(window.LF.getList(), e.target);
  document.addEventListener("click", e => {
    const b = e.target.closest("[data-idopen]"); if (!b) return;
    const id = b.dataset.idopen;
    const l = window.LF.getList().find(x => x.id === id) || window.LF.getResults().find(x => x.id === id);
    if (l) open(l);
  });
  window.LF.refresh();
}
if (window.LF) init(); else document.addEventListener("lf-ready", init);
})();
