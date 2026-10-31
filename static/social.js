/* LeadFinder: Social tab. AI content for your own pages + DMs to leads (uses the free AI pool) */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
function store(k, d, v){
  try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; }
        const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; }
}
let brand = store("lf-brand", {service:"Websites for local businesses", audience:"", city:"", tone:"friendly and professional", offer:"Free sample homepage", proof:""});
let saved = store("lf-social", []);

const TASKS = {
  calendar: {label:"7-day content calendar", needs:[], prompt: b => `Create a 7-day social media content calendar for my business. For each day give: platform (Facebook, Instagram or LinkedIn), post type (tip, before/after, myth, client story, offer, behind the scenes, question), a hook line, and a 2-sentence caption idea. Mix platforms sensibly.`},
  post:     {label:"Single post", needs:["platform","topic"], prompt: (b, f) => `Write one ${f.platform} post about: ${f.topic}. Start with a strong hook, keep it easy to read, end with a clear call to action (${b.offer}). ${f.platform === "Instagram" ? "Add 8 relevant hashtags at the end." : f.platform === "LinkedIn" ? "Professional tone, short paragraphs, no more than 3 hashtags." : "Short and conversational, 1-2 emojis max."}`},
  niche:    {label:"Posts for a niche", needs:["niche"], prompt: (b, f) => `Write 3 short social posts aimed at ${f.niche} owners explaining, in their language, how a website brings them more customers (examples: people searching on Google, booking or quote forms, trust from reviews and photos). Each under 80 words with a call to action: ${b.offer}. Don't invent statistics.`},
  casestudy:{label:"Client win / case study", needs:["lead"], prompt: (b, f, l) => `Write a short before/after case-study post (Facebook + Instagram version) about a website I built for ${l.name}, a ${l.category} in ${l.address}. Before: ${l.website ? "their old website had problems" : "they had no website"}; they had ${l.reviews||0} reviews. Describe what the new site includes (services, contact, mobile-friendly${l.analysis ? ", things their competitors had" : ""}). Do not invent results or numbers; add [RESULT] as a placeholder for me to fill in. Ask the reader to message me.`},
  dm:       {label:"Instagram / Facebook DM to a lead", needs:["lead"], prompt: (b, f, l) => `Write 2 versions of a short, friendly Instagram/Facebook direct message (under 50 words each) to the owner of ${l.name} (${l.category}, ${l.reviews||0} reviews, website: ${l.website||"none"}). Compliment something genuine, mention one specific observation, offer: ${b.offer}. No hard selling, no links in the first message.`},
  comment:  {label:"Reply to a comment / objection", needs:["topic"], prompt: (b, f) => `Someone wrote this to me on social media: "${f.topic}". Write 2 short, polite, helpful replies that keep the conversation going and invite them to a quick chat.`},
  bio:      {label:"Profile bio + highlights", needs:[], prompt: b => `Write 3 options for an Instagram bio (max 150 characters) and a Facebook page "About" (max 255 characters) for my business, plus 5 Instagram story highlight names.`},
};

function brandText(){
  const S = window.LF.settings();
  return `MY BUSINESS: ${S.myBusiness || "(unnamed)"} run by ${S.myName || "me"}. Service: ${brand.service}. Target clients: ${brand.audience || "local businesses"}${brand.city ? " in " + brand.city : ""}. Tone: ${brand.tone}. Main offer: ${brand.offer}. ${brand.proof ? "Proof/experience: " + brand.proof + "." : ""}`;
}

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-social"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Social media assistant</h2>
    <p class="sub" style="margin-top:-4px">Create posts for your own pages to attract clients, and write DMs to leads you found. Uses your free AI pool. Always review before posting.</p>
    <div class="grid">
      <div><label>Your service</label><input id="brService"></div>
      <div><label>Target clients</label><input id="brAudience" placeholder="e.g. roofers and plumbers"></div>
      <div><label>Area</label><input id="brCity" placeholder="e.g. Texas, USA"></div>
      <div><label>Tone</label><input id="brTone"></div>
      <div><label>Main offer</label><input id="brOffer"></div>
      <div><label>Proof / experience</label><input id="brProof" placeholder="e.g. 12 sites built, 5 years"></div>
    </div>
    <button class="btn sm" id="brSave" style="margin-top:8px">Save brand</button>
  </div>
  <div class="panel">
    <div class="grid">
      <div><label>What to create</label><select id="soTask">${Object.entries(TASKS).map(([k,t]) => `<option value="${k}">${t.label}</option>`).join("")}</select></div>
      <div data-need="platform"><label>Platform</label><select id="soPlatform"><option>Facebook</option><option>Instagram</option><option>LinkedIn</option><option>X</option></select></div>
      <div data-need="topic"><label id="soTopicL">Topic</label><input id="soTopic" placeholder="e.g. 3 signs your business needs a new website"></div>
      <div data-need="niche"><label>Niche</label><input id="soNiche" placeholder="e.g. dentists"></div>
      <div data-need="lead"><label>Lead (from My list)</label><select id="soLead"></select></div>
      <div><button class="btn primary" id="soGo" style="width:100%">Create with AI</button></div>
    </div>
    <div id="soOut"></div>
  </div>
  <div class="panel">
    <h3 style="margin-top:0">Saved content</h3>
    <div id="soSaved"></div>
  </div>`;
  document.querySelector(".wrap").appendChild(sec);
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "social"; b.textContent = "Social";
  nav.insertBefore(b, nav.querySelector('[data-tab="guide"]'));
  window.LF.bindTab(b, () => { leadOptions(); showNeeds(); });
}
function leadOptions(){
  const list = window.LF.getList();
  $("#soLead").innerHTML = list.length ? list.map(l => `<option value="${esc(l.id)}">${esc(l.name)} (${esc(l.stage)})</option>`).join("") : '<option value="">Add leads to My list first</option>';
}
function showNeeds(){
  const t = TASKS[$("#soTask").value];
  document.querySelectorAll("#tab-social [data-need]").forEach(d => d.hidden = !t.needs.includes(d.dataset.need));
  $("#soTopicL").textContent = $("#soTask").value === "comment" ? "Their comment" : "Topic";
}
function renderSaved(){
  $("#soSaved").innerHTML = saved.length ? saved.map((s,i) => `<div class="panel" style="margin:8px 0 0;padding:12px">
    <div class="toolbar" style="margin:0"><b class="grow">${esc(s.title)}</b><span class="sub">${esc(s.date)}</span>
    <button class="btn sm" data-sc="${i}">Copy</button><button class="btn sm" data-sd="${i}">Delete</button></div>
    <div style="white-space:pre-wrap;font-size:14px">${esc(s.text)}</div></div>`).join("") : '<p class="sub">Nothing saved yet.</p>';
}
function init(){
  mount();
  const map = {brService:"service", brAudience:"audience", brCity:"city", brTone:"tone", brOffer:"offer", brProof:"proof"};
  Object.entries(map).forEach(([id,k]) => $("#"+id).value = brand[k] || "");
  $("#brSave").onclick = () => { Object.entries(map).forEach(([id,k]) => brand[k] = $("#"+id).value.trim()); store("lf-brand", null, brand); $("#brSave").textContent = "Saved"; };
  $("#soTask").onchange = showNeeds;
  $("#soGo").onclick = async () => {
    const k = $("#soTask").value, t = TASKS[k];
    const f = {platform: $("#soPlatform").value, topic: $("#soTopic").value.trim(), niche: $("#soNiche").value.trim()};
    const l = window.LF.getList().find(x => x.id === $("#soLead").value);
    if (t.needs.includes("lead") && !l){ alert("Pick a lead."); return; }
    if (t.needs.includes("topic") && !f.topic){ alert("Enter a topic."); return; }
    if (t.needs.includes("niche") && !f.niche){ alert("Enter a niche."); return; }
    const out = $("#soOut"); out.innerHTML = '<p class="sub"><span class="spin"></span> Writing…</p>';
    try {
      const r = await window.LF.api("/api/ai", {ai: {provider: "pool"}, prompt: `${brandText()}\n\nTASK: ${t.prompt(brand, f, l)}`});
      const title = `${t.label}${l ? " – " + l.name : f.topic ? " – " + f.topic.slice(0,40) : f.niche ? " – " + f.niche : ""}`;
      out.innerHTML = `<div style="white-space:pre-wrap;background:var(--bg);border-radius:8px;padding:12px;margin-top:12px;font-size:14px" id="soText">${esc(r.text)}</div>
        <div class="toolbar"><span class="sub grow">by ${esc(r.provider||"AI")}</span><button class="btn sm" id="soCopy">Copy</button><button class="btn sm primary" id="soKeep">Save</button></div>`;
      $("#soCopy").onclick = e => navigator.clipboard.writeText(r.text).then(() => e.target.textContent = "Copied");
      $("#soKeep").onclick = e => { saved.unshift({title, text: r.text, date: new Date().toISOString().slice(0,10)}); store("lf-social", null, saved.slice(0,100)); renderSaved(); e.target.textContent = "Saved"; };
    } catch(err){ out.innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
  };
  $("#soSaved").onclick = e => {
    const c = e.target.dataset.sc, d = e.target.dataset.sd;
    if (c !== undefined) navigator.clipboard.writeText(saved[+c].text).then(() => e.target.textContent = "Copied");
    if (d !== undefined){ saved.splice(+d, 1); store("lf-social", null, saved); renderSaved(); }
  };
  leadOptions(); showNeeds(); renderSaved();
}
if (window.LF) init(); else document.addEventListener("lf-ready", init);
})();
