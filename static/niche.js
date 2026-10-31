/* LeadFinder: Niche finder tab. Suggests niches and cities, and tests them with live map data */
(function(){
const $ = s => document.querySelector(s);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const fmt = n => Number(n).toLocaleString();

/* value: how much a new customer is typically worth to the business (qualitative)
   fit: which of your services they usually need */
const NICHES = [
  {n:"Roofers", q:"roofing contractor", g:"Home services", value:"Very high", why:"Each job is big; homeowners search Google after storms and pick who looks trustworthy.", sell:"Website + quote form + before/after gallery + service-area pages"},
  {n:"HVAC / heating & AC", q:"HVAC contractor", g:"Home services", value:"Very high", why:"Urgent, seasonal searches ('AC repair near me'); a single install is worth a lot.", sell:"Website + click-to-call + emergency page + financing info"},
  {n:"Plumbers", q:"plumber", g:"Home services", value:"High", why:"Emergency calls go to whoever appears first and looks reliable.", sell:"Website + click-to-call + service pages + reviews"},
  {n:"Electricians", q:"electrician", g:"Home services", value:"High", why:"Mostly one-person businesses that rely on word of mouth and miss online searches.", sell:"Website + quote form + licensing/insurance badges"},
  {n:"Landscapers / lawn care", q:"landscaping company", g:"Home services", value:"Medium–high", why:"Recurring contracts; photos of work sell the service.", sell:"Website + gallery + seasonal booking"},
  {n:"Tree services", q:"tree service", g:"Home services", value:"High", why:"Large one-off jobs, strong local search demand, many operators without sites.", sell:"Website + quote form + emergency storm page"},
  {n:"Painters", q:"house painter", g:"Home services", value:"Medium–high", why:"Visual work; portfolio drives trust.", sell:"Website + portfolio + estimate form"},
  {n:"General contractors / remodelers", q:"general contractor", g:"Home services", value:"Very high", why:"Remodels are big purchases; buyers research online carefully.", sell:"Website + project gallery + consultation booking"},
  {n:"House cleaning", q:"house cleaning service", g:"Home services", value:"Medium", why:"Recurring customers; online booking is a big advantage.", sell:"Website + instant quote + booking"},
  {n:"Pest control", q:"pest control", g:"Home services", value:"High", why:"Urgent searches and recurring plans.", sell:"Website + click-to-call + plan pricing"},
  {n:"Moving companies", q:"moving company", g:"Home services", value:"High", why:"Customers compare quotes online before booking.", sell:"Website + quote calculator + reviews"},
  {n:"Auto repair shops", q:"auto repair shop", g:"Auto", value:"Medium–high", why:"Many independent garages have loyal customers but no site.", sell:"Website + booking + services & prices"},
  {n:"Auto detailing", q:"car detailing", g:"Auto", value:"Medium", why:"Visual, Instagram-friendly, often mobile businesses without sites.", sell:"Website + packages + booking"},
  {n:"Dentists", q:"dentist", g:"Health", value:"Very high", why:"High patient value; new patients choose clinics that allow online booking.", sell:"Website + online booking + service pages"},
  {n:"Chiropractors / physio", q:"chiropractor", g:"Health", value:"High", why:"Repeat visits; online booking and reviews matter.", sell:"Website + booking + new-patient offer"},
  {n:"Med spas / aesthetics", q:"med spa", g:"Beauty", value:"Very high", why:"High-ticket treatments sold through visuals and trust.", sell:"Website + booking + treatment pages + Instagram"},
  {n:"Hair salons", q:"hair salon", g:"Beauty", value:"Medium", why:"Clients book 24/7; many salons rely only on Instagram.", sell:"Website + booking + price list"},
  {n:"Barbershops", q:"barber shop", g:"Beauty", value:"Low–medium", why:"Very common without websites; easy to sell a simple booking site.", sell:"Simple site + booking"},
  {n:"Tattoo studios", q:"tattoo shop", g:"Beauty", value:"Medium", why:"Portfolio-driven; artists often only use Instagram.", sell:"Website + artist portfolios + booking form"},
  {n:"Dog grooming / pet services", q:"dog groomer", g:"Retail", value:"Medium", why:"Loyal repeat customers; booking is the main need.", sell:"Website + booking + price list"},
  {n:"Restaurants", q:"restaurant", g:"Food", value:"Medium", why:"Menu, hours and ordering are checked online first.", sell:"Website + menu + online ordering + reservations"},
  {n:"Food trucks / caterers", q:"catering service", g:"Food", value:"Medium–high", why:"Catering orders are large; clients need menus and a quote form.", sell:"Website + menu + event quote form"},
  {n:"Personal trainers / gyms", q:"personal trainer", g:"Fitness", value:"Medium", why:"Programs sell online; sign-ups and payments can be automated.", sell:"Website + booking + payments"},
  {n:"Small law firms", q:"lawyer", g:"Professional", value:"Very high", why:"A single client is worth a lot; credibility comes from the website.", sell:"Professional website + consultation form + practice-area pages"},
  {n:"Accountants / tax preparers", q:"tax preparation service", g:"Professional", value:"High", why:"Seasonal demand; clients search and book appointments online.", sell:"Website + booking + secure document upload"},
  {n:"Real estate agents", q:"real estate agent", g:"Professional", value:"High", why:"Personal brand sites and listings generate leads.", sell:"Personal website + listings + lead capture"},
  {n:"Wedding & event photographers", q:"wedding photographer", g:"Creative", value:"High", why:"Portfolio is everything; couples compare sites.", sell:"Portfolio website + packages + enquiry form"},
  {n:"Daycares / tutoring", q:"daycare", g:"Education", value:"High", why:"Parents research carefully; trust and information matter.", sell:"Website + enrollment form + photo tour"},
  {n:"Driving schools", q:"driving school", g:"Education", value:"Medium", why:"Students compare prices and book lessons online.", sell:"Website + packages + booking"},
];

const TIP_SIZE = {
  big: "Big city: lots of businesses but more agencies competing. Pick a specific niche and neighborhood.",
  mid: "Mid-size city (100k–1M): a good balance, with many businesses and fewer web agencies targeting them.",
  small: "Smaller city: fewer leads but less competition, and personal/local outreach works well.",
};
const sizeOf = p => p >= 1000000 ? "big" : p >= 100000 ? "mid" : "small";

let cities = [], samples = store("lf-samples", {});
function store(k, d, v){
  try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; }
        const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; }
}

function mount(){
  const sec = document.createElement("section");
  sec.id = "tab-niche"; sec.hidden = true;
  sec.innerHTML = `
  <div class="panel">
    <h2>Find the best niche and city</h2>
    <p class="sub" style="margin-top:-4px">Pick a country, see the biggest cities, then run a live market check: LeadFinder samples Google Maps and shows how many established businesses have no website.</p>
    <div class="grid">
      <div><label for="nfCountry">Country</label><select id="nfCountry"></select></div>
      <div><label for="nfMin">Minimum population</label>
        <select id="nfMin"><option value="50000">50,000+</option><option value="100000" selected>100,000+</option><option value="250000">250,000+</option><option value="500000">500,000+</option><option value="1000000">1 million+</option></select></div>
      <div><label for="nfSize">City size focus</label>
        <select id="nfSize"><option value="all">All sizes</option><option value="big">Big (1M+)</option><option value="mid">Mid-size (100k–1M)</option><option value="small">Smaller (under 100k)</option></select></div>
      <div><button class="btn primary" id="nfLoad" style="width:100%">Load cities</button></div>
    </div>
    <div id="nfMsg"></div>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">1. Choose niches to test</h3>
    <p class="sub">Niches where a website clearly brings more customers. "Value" is how much one new customer is typically worth to that business: higher value means clients can pay more for a website.</p>
    <div class="toolbar"><select id="nfGroup" style="max-width:220px"><option value="">All groups</option></select>
      <button class="btn sm" id="nfPickHigh">Select high-value niches</button><button class="btn sm" id="nfPickNone">Clear</button>
      <span class="sub" id="nfPicked"></span></div>
    <div class="tablewrap"><table style="min-width:760px">
      <thead><tr><th></th><th>Niche</th><th>Value</th><th>Why they need a website</th><th>What to sell</th></tr></thead>
      <tbody id="nfNiches"></tbody></table></div>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">2. Cities</h3>
    <div class="toolbar">
      <input id="nfCitySearch" placeholder="Filter cities or states" style="max-width:260px">
      <div class="grow"></div>
      <span class="sub">Tick cities, then test.</span>
      <button class="btn sm primary" id="nfTest">Test selected niches in selected cities</button>
    </div>
    <p class="note" id="nfCost"></p>
    <div class="tablewrap" style="max-height:420px;overflow:auto"><table style="min-width:640px">
      <thead><tr><th></th><th>City</th><th>Region</th><th>Population</th><th>Size tip</th><th>Best tested niche</th></tr></thead>
      <tbody id="nfCities"><tr><td colspan="6" class="empty">Press "Load cities".</td></tr></tbody></table></div>
    <p class="note">Population from Wikidata (latest value recorded there; may differ slightly from the newest census).</p>
  </div>

  <div class="panel">
    <h3 style="margin-top:0">3. Results: where the opportunities are</h3>
    <div class="toolbar"><span class="sub grow" id="nfResInfo">No tests yet.</span><button class="btn sm" id="nfClear">Clear results</button></div>
    <div class="tablewrap"><table style="min-width:820px">
      <thead><tr><th>Rank</th><th>Niche + city</th><th>Opportunity</th><th>No website</th><th>Established, no website</th><th>Avg reviews</th><th>Examples</th><th></th></tr></thead>
      <tbody id="nfResults"></tbody></table></div>
    <p class="note">Opportunity = no-website businesses weighted by reviews and phone availability, from a sample of up to 20 businesses per niche and city. Use it to compare options, then search the winners in full.</p>
  </div>`;
  document.querySelector(".wrap").appendChild(sec);
  const nav = document.querySelector("nav");
  const b = document.createElement("button");
  b.setAttribute("role","tab"); b.dataset.tab = "niche"; b.setAttribute("aria-selected","false"); b.textContent = "Niche finder";
  nav.insertBefore(b, nav.children[0]);
  window.LF.bindTab(b);
}

let picked = new Set(store("lf-niche-picked", ["Roofers","Plumbers","Dentists","Auto repair shops"]));
function renderNiches(){
  const g = $("#nfGroup").value;
  $("#nfNiches").innerHTML = NICHES.filter(x => !g || x.g === g).map(x => `<tr>
    <td><input type="checkbox" data-niche="${esc(x.n)}" ${picked.has(x.n)?"checked":""} aria-label="Select ${esc(x.n)}"></td>
    <td><div class="nm">${esc(x.n)}</div><div class="sub">${esc(x.g)}</div></td>
    <td><span class="tag ${/Very high|^High/.test(x.value)?"t-no":/Medium/.test(x.value)?"t-weak":"t-yes"}">${esc(x.value)}</span></td>
    <td>${esc(x.why)}</td><td class="sub">${esc(x.sell)}</td></tr>`).join("");
  $("#nfPicked").textContent = `${picked.size} selected`;
  store("lf-niche-picked", null, [...picked]);
  cost();
}
let pickedCities = new Set();
function renderCities(){
  const f = $("#nfCitySearch").value.toLowerCase(), sz = $("#nfSize").value;
  const best = {};
  Object.values(samples).forEach(s => { if (!best[s.city] || s.opportunity > best[s.city].opportunity) best[s.city] = s; });
  const rows = cities.filter(c => (sz === "all" || sizeOf(c.population) === sz) && (!f || (c.name + " " + c.region).toLowerCase().includes(f)));
  $("#nfCities").innerHTML = rows.length ? rows.map(c => {
    const key = cityKey(c), b = best[key];
    return `<tr><td><input type="checkbox" data-city="${esc(key)}" ${pickedCities.has(key)?"checked":""} aria-label="Select ${esc(c.name)}"></td>
      <td class="nm">${esc(c.name)}</td><td class="sub">${esc(c.region)}</td><td>${fmt(c.population)}</td>
      <td class="sub">${TIP_SIZE[sizeOf(c.population)]}</td>
      <td>${b ? `${esc(b.niche)} <span class="sub">(${b.opportunity})</span>` : '<span class="sub">Not tested</span>'}</td></tr>`;
  }).join("") : '<tr><td colspan="6" class="empty">No cities match.</td></tr>';
  cost();
}
const cityKey = c => `${c.name}${c.region ? ", " + c.region : ""}, ${$("#nfCountry").value}`;
function cost(){
  const n = picked.size * pickedCities.size;
  $("#nfCost").textContent = n ? `This test runs ${n} map search${n===1?"":"es"} (one per niche per city). Start small, e.g. 4 niches × 3 cities.` : "";
}

function renderResults(){
  const arr = Object.values(samples).sort((a,b) => b.opportunity - a.opportunity);
  $("#nfResInfo").textContent = arr.length ? `${arr.length} niche + city combinations tested. Best first.` : "No tests yet.";
  const max = arr.length ? arr[0].opportunity || 1 : 1;
  $("#nfResults").innerHTML = arr.map((s,i) => `<tr>
    <td class="score">${i+1}</td>
    <td><div class="nm">${esc(s.niche)}</div><div class="sub">${esc(s.city)}</div></td>
    <td><span class="score ${s.opportunity/max > .7 ? "hot" : ""}">${s.opportunity}</span>
      <div style="height:6px;border-radius:3px;background:var(--chip);margin-top:4px;width:110px"><div style="height:6px;border-radius:3px;background:var(--go);width:${Math.round(110*s.opportunity/max)}px"></div></div></td>
    <td>${s.noWebsite}/${s.sampled} <span class="sub">(${s.pctNoWebsite}%)</span></td>
    <td>${s.establishedNoWebsite}</td><td>${s.avgReviews}</td>
    <td class="sub">${s.examples.map(e => `${esc(e.name)} (${e.reviews})`).join("<br>") || "–"}</td>
    <td><button class="btn sm primary" data-go="${esc(s.nicheQuery)}" data-city="${esc(s.city)}">Search leads</button></td></tr>`).join("")
    || '<tr><td colspan="8" class="empty">Select niches and cities above, then press Test.</td></tr>';
}

function init(){
  mount();
  $("#nfGroup").innerHTML += [...new Set(NICHES.map(x => x.g))].map(g => `<option>${esc(g)}</option>`).join("");
  $("#nfCountry").innerHTML = ["United States","United Kingdom","Canada","Australia","New Zealand","Ireland","Germany","United Arab Emirates","Saudi Arabia","Pakistan","India","South Africa"].map(c => `<option>${c}</option>`).join("");
  $("#nfGroup").onchange = renderNiches;
  $("#nfNiches").onchange = e => { const n = e.target.dataset.niche; if (!n) return; e.target.checked ? picked.add(n) : picked.delete(n); renderNiches(); };
  $("#nfPickHigh").onclick = () => { NICHES.filter(x => /High/i.test(x.value) && !/Low/.test(x.value)).forEach(x => picked.add(x.n)); renderNiches(); };
  $("#nfPickNone").onclick = () => { picked.clear(); renderNiches(); };
  $("#nfCitySearch").oninput = renderCities; $("#nfSize").onchange = renderCities;
  $("#nfCities").onchange = e => { const c = e.target.dataset.city; if (!c) return; e.target.checked ? pickedCities.add(c) : pickedCities.delete(c); cost(); };
  $("#nfLoad").onclick = async () => {
    const btn = $("#nfLoad"); btn.disabled = true; btn.innerHTML = '<span class="spin"></span> Loading…'; $("#nfMsg").innerHTML = "";
    try {
      const minPop = $("#nfSize").value === "small" ? 20000 : +$("#nfMin").value;
      const j = await window.LF.api("/api/cities", {country: $("#nfCountry").value, minPop, limit: 200});
      cities = j.cities; pickedCities.clear();
      $("#nfMsg").innerHTML = `<div class="msg ok">${cities.length} cities loaded, largest first.</div>`;
      renderCities();
    } catch(err){ $("#nfMsg").innerHTML = `<div class="msg err">${esc(err.message)}</div>`; }
    btn.disabled = false; btn.textContent = "Load cities";
  };
  $("#nfTest").onclick = async () => {
    if (!picked.size || !pickedCities.size){ alert("Select at least one niche and one city."); return; }
    const S = window.LF.settings();
    const src = S.apiKey ? "google" : S.serpKey ? "serpapi" : "google";
    const jobs = [];
    [...pickedCities].forEach(city => [...picked].forEach(n => jobs.push({city, niche: NICHES.find(x => x.n === n)})));
    if (jobs.length > 30 && !confirm(`This runs ${jobs.length} map searches. Continue?`)) return;
    const btn = $("#nfTest"); btn.disabled = true; let done = 0, errs = 0, lastErr = "";
    const q = [...jobs];
    const worker = async () => { while (q.length){ const j = q.shift();
      try {
        const r = await window.LF.api("/api/market-sample", {source: src, apiKey: S.apiKey, serpKey: S.serpKey, niche: j.niche.q, city: j.city});
        r.niche = j.niche.n; r.nicheQuery = j.niche.q;
        samples[j.niche.n + "|" + j.city] = r;
      } catch(e){ errs++; lastErr = e.message; }
      done++; btn.textContent = `Testing ${done}/${jobs.length}…`; renderResults(); } };
    await Promise.all([worker(), worker(), worker()]);
    store("lf-samples", null, samples);
    btn.disabled = false; btn.textContent = "Test selected niches in selected cities";
    renderCities(); renderResults();
    if (errs) $("#nfMsg").innerHTML = `<div class="msg err">${errs} test(s) failed: ${esc(lastErr)}</div>`;
  };
  $("#nfClear").onclick = () => { samples = {}; store("lf-samples", null, samples); renderResults(); renderCities(); };
  $("#nfResults").onclick = e => { const b = e.target.closest("[data-go]"); if (b) window.LF.startSearch(b.dataset.go, b.dataset.city); };
  renderNiches(); renderResults();
}
window.LFNiche = {NICHES};
if (window.LF) init(); else document.addEventListener("lf-ready", init);
})();
