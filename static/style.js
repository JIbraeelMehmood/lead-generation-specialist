/**
 * static/style.js — AI Style Learning tab
 * Connects to style_learning.py via /api/style/*.
 */
(function () {
  const TAB = "style";

  function ensurePanel() {
    if (document.getElementById("tab-style")) return;
    const p = document.createElement("section");
    p.id = "tab-style"; p.setAttribute("role","tabpanel"); p.style.display = "none";
    p.innerHTML = `
<div style="max-width:960px;margin:0 auto">
  <div class="card">
    <h2 style="margin-top:0">✍️ My Writing Style</h2>
    <p style="color:#666;margin-top:0">Add your own emails and messages as examples. AI analyzes them and learns your unique voice — then every draft sounds like <em>you</em>, not like a generic chatbot.</p>
  </div>

  <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-top:16px">

    <!-- Add example -->
    <div class="card">
      <h3 style="margin-top:0">➕ Add a Writing Example</h3>
      <label><b>Your email or message</b>
        <textarea id="stExample" rows="6" style="width:100%;margin-top:4px" placeholder="Paste one of your own emails or WhatsApp messages here…"></textarea>
      </label>
      <label style="display:block;margin-top:8px"><b>Type</b>
        <select id="stLabel" style="width:100%;margin-top:4px">
          <option value="email">Email</option>
          <option value="whatsapp">WhatsApp</option>
          <option value="linkedin">LinkedIn message</option>
          <option value="other">Other</option>
        </select>
      </label>
      <button id="stAddBtn" class="btn-primary" style="margin-top:10px;width:100%">➕ Add example</button>
    </div>

    <!-- Import from export -->
    <div class="card">
      <h3 style="margin-top:0">📂 Import from Chat Export</h3>
      <p style="font-size:13px;color:#666;margin-top:0">Paste your WhatsApp export text or email conversation. Only your own messages will be extracted.</p>
      <label><b>Your name in the chat</b>
        <input id="stYourName" type="text" placeholder="Your Name (as it appears in the chat)" style="width:100%;margin-top:4px;margin-bottom:8px">
      </label>
      <label><b>Chat export text</b>
        <textarea id="stImport" rows="6" style="width:100%;margin-top:4px" placeholder="Paste WhatsApp export or email thread here…"></textarea>
      </label>
      <button id="stImportBtn" class="btn-secondary" style="margin-top:10px;width:100%">📂 Import</button>
      <div id="stImportStatus" style="font-size:12px;color:#666;margin-top:6px"></div>
    </div>
  </div>

  <!-- Learned profile -->
  <div class="card" style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="margin:0">🤖 Learned Style Profile</h3>
      <div style="display:flex;gap:8px">
        <button id="stLearnBtn" class="btn-primary">🧠 Analyze my style</button>
        <button class="btn-secondary" onclick="window._stLoad()">🔄 Refresh</button>
      </div>
    </div>
    <div id="stProfile"><em style="color:#9ca3af">Add at least 3 examples, then click "Analyze my style".</em></div>
  </div>

  <!-- Examples list -->
  <div class="card" style="margin-top:16px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
      <h3 style="margin:0">📝 My Examples (<span id="stCount">0</span>)</h3>
      <button class="btn-secondary" style="font-size:12px;color:#ef4444" id="stClearBtn">🗑️ Clear all</button>
    </div>
    <div id="stExamples"><em style="color:#9ca3af">No examples yet.</em></div>
  </div>
</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(p);
    _init(p);
    _loadAll();
    window._stLoad = _loadAll;
  }

  async function api(path, body) {
    const r = await fetch(path, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify(body||{}) });
    return r.json();
  }

  function _init(p) {
    p.querySelector("#stAddBtn").onclick    = () => _addExample(p);
    p.querySelector("#stImportBtn").onclick = () => _importChat(p);
    p.querySelector("#stLearnBtn").onclick  = () => _learnStyle(p);
    p.querySelector("#stClearBtn").onclick  = () => { if (confirm("Clear all examples?")) api("/api/style/clear",{}).then(_loadAll); };
  }

  async function _addExample(p) {
    const text  = p.querySelector("#stExample").value.trim();
    const label = p.querySelector("#stLabel").value;
    if (!text) { alert("Paste an example first."); return; }
    await api("/api/style/add", { text, label });
    p.querySelector("#stExample").value = "";
    _loadAll();
  }

  async function _importChat(p) {
    const text = p.querySelector("#stImport").value.trim();
    const name = p.querySelector("#stYourName").value.trim();
    if (!text) { alert("Paste chat export first."); return; }
    const btn = p.querySelector("#stImportBtn");
    btn.disabled = true;
    const data = await api("/api/style/import", { text, your_name: name });
    p.querySelector("#stImportStatus").textContent = data.error ? "❌ " + data.error : `✅ Added ${data.added} examples (total: ${data.total})`;
    btn.disabled = false;
    _loadAll();
  }

  async function _learnStyle(p) {
    const btn = p.querySelector("#stLearnBtn");
    btn.disabled = true; btn.textContent = "⏳ Analyzing…";
    const data = await api("/api/style/learn", {});
    btn.disabled = false; btn.textContent = "🧠 Analyze my style";
    if (data.error) { document.getElementById("stProfile").innerHTML = `<p style="color:#ef4444">${_esc(data.error)}</p>`; return; }
    _renderProfile(data.profile);
  }

  async function _loadAll() {
    const data = await api("/api/style/list", {});
    const examples = data.examples || [];
    document.getElementById("stCount").textContent = examples.length;
    _renderExamples(examples);
    if (data.profile?.tone) _renderProfile(data.profile);
  }

  function _renderProfile(p) {
    if (!p) return;
    document.getElementById("stProfile").innerHTML = `
<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px">
  <div><b>Tone:</b> ${_esc(p.tone||"–")}</div>
  <div><b>Sentence length:</b> ${_esc(p.sentence_length||"–")}</div>
  <div><b>Greeting:</b> ${_esc(p.greeting_style||"–")}</div>
  <div><b>Sign-off:</b> ${_esc(p.signature||"–")}</div>
</div>
${p.avoid?.length ? `<div style="margin-top:10px"><b>Avoid:</b> ${p.avoid.map(_esc).join(", ")}</div>` : ""}
${p.patterns?.length ? `<div style="margin-top:8px"><b>Patterns:</b><ul style="margin:4px 0 0 20px;font-size:13px">${p.patterns.map(x=>`<li>${_esc(x)}</li>`).join("")}</ul></div>` : ""}
${p.sample_opener ? `<div style="margin-top:10px;background:#f0f9ff;border-radius:6px;padding:10px;font-size:13px"><b>Sample opener:</b> "${_esc(p.sample_opener)}"</div>` : ""}
${p.summary ? `<div style="margin-top:8px;font-size:13px;color:#374151">${_esc(p.summary)}</div>` : ""}`;
  }

  function _renderExamples(examples) {
    const c = document.getElementById("stExamples"); if (!c) return;
    if (!examples.length) { c.innerHTML = `<em style="color:#9ca3af">No examples yet.</em>`; return; }
    c.innerHTML = examples.map((e,i) => `
<div style="border:1px solid #e2e8f0;border-radius:6px;padding:10px;margin-bottom:8px;font-size:13px">
  <div style="display:flex;justify-content:space-between">
    <span style="font-size:11px;background:#f1f5f9;padding:2px 6px;border-radius:4px">${_esc(e.label)}</span>
    <button class="btn-secondary" style="font-size:11px;color:#ef4444" onclick="window._stRemove(${i})">Remove</button>
  </div>
  <div style="margin-top:6px;color:#374151">${_esc(e.text.substring(0,150))}${e.text.length>150?"…":""}</div>
</div>`).join("");
    window._stRemove = async (i) => { await api("/api/style/remove",{index:i}); _loadAll(); };
  }

  function _esc(s) { return String(s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }

  document.addEventListener("DOMContentLoaded", () => {
    const btn = document.querySelector(`[data-tab="${TAB}"]`);
    if (!btn) return;
    window.LF.bindTab(btn, () => ensurePanel());
  });
})();
