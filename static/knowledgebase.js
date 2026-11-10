/**
 * static/knowledgebase.js — Principal-Awareness Knowledge Base tab
 *
 * Connects to backend knowledge.py via /api/knowledge/*.
 *
 * Features:
 *   - View and edit all .md knowledge files in-browser
 *   - Bootstrap creates example files on first run
 *   - System prompt preview (what the AI sees)
 *   - Structured info view (founder, company, services)
 *   - File delete
 *
 * Files live at: .leadfinder/knowledge/*.md
 * They are injected into every AI call automatically once configured.
 */
(function () {
  const TAB_ID = "knowledgebase";
  let _selectedFile = null;

  function ensurePanel() {
    if (document.getElementById("tab-knowledgebase")) return;
    const panel = document.createElement("section");
    panel.id = "tab-knowledgebase";
    panel.setAttribute("role", "tabpanel");
    panel.style.display = "none";
    panel.innerHTML = `
<div style="max-width:960px;margin:0 auto">

  <div class="card">
    <h2 style="margin-top:0">🧠 Knowledge Base</h2>
    <p style="color:#666;margin-top:0">These Markdown files tell the AI who you are, what you offer, your writing style,
    and which leads to target. Every AI email, strategy, and decision-maker extraction automatically reads from here.</p>
    <p style="font-size:13px;color:#0369a1">Files location: <code>.leadfinder/knowledge/</code></p>

    <div style="display:flex;gap:8px;margin-bottom:16px;flex-wrap:wrap">
      <button id="kbBootstrapBtn" class="btn-primary">🗂️ Create example files</button>
      <button id="kbNewBtn" class="btn-secondary">➕ New file</button>
      <button id="kbPreviewBtn" class="btn-secondary">👁️ Preview AI system prompt</button>
      <button id="kbRefreshBtn" class="btn-secondary">🔄 Refresh</button>
    </div>
    <div id="kbStatus" style="font-size:13px;color:#666;margin-bottom:8px"></div>
  </div>

  <div style="display:grid;grid-template-columns:220px 1fr;gap:16px;margin-top:16px">

    <!-- File list -->
    <div class="card" style="padding:12px">
      <h4 style="margin:0 0 10px 0">📁 Files</h4>
      <div id="kbFileList"><em style="color:#888;font-size:13px">No files yet.</em></div>
    </div>

    <!-- Editor -->
    <div class="card">
      <div id="kbEditorHeader" style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <span id="kbEditorTitle" style="font-weight:600;font-size:14px">Select a file to edit</span>
        <div style="display:flex;gap:6px" id="kbEditorActions" style="display:none">
          <button id="kbSaveBtn" class="btn-primary" style="font-size:12px" disabled>💾 Save</button>
          <button id="kbDeleteBtn" class="btn-secondary" style="font-size:12px;color:#ef4444" disabled>🗑️ Delete</button>
        </div>
      </div>
      <textarea id="kbEditor" rows="20" style="width:100%;font-family:monospace;font-size:13px;border:1px solid #e2e8f0;border-radius:6px;padding:12px;resize:vertical"
        placeholder="Select a file from the list…" spellcheck="false"></textarea>
    </div>
  </div>

  <!-- Structured view -->
  <div class="card" style="margin-top:16px">
    <h3 style="margin-top:0">📊 Structured Info (parsed from your files)</h3>
    <div id="kbStructured"><em style="color:#888;font-size:13px">Load files to see parsed data.</em></div>
  </div>

  <!-- Prompt preview modal -->
  <div id="kbPromptModal" style="display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:rgba(0,0,0,0.5);z-index:9999;align-items:center;justify-content:center">
    <div style="background:#fff;border-radius:10px;padding:24px;width:700px;max-width:95vw;max-height:80vh;overflow-y:auto">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
        <h3 style="margin:0">🤖 AI System Prompt Preview</h3>
        <button onclick="document.getElementById('kbPromptModal').style.display='none'" style="background:none;border:none;font-size:20px;cursor:pointer">✕</button>
      </div>
      <pre id="kbPromptContent" style="white-space:pre-wrap;font-size:12px;font-family:monospace;background:#f8fafc;padding:12px;border-radius:6px;border:1px solid #e2e8f0;max-height:60vh;overflow-y:auto"></pre>
    </div>
  </div>

</div>`;
    document.querySelector("main") && document.querySelector("main").appendChild(panel);
    _initEvents(panel);
    _loadFiles(panel);
  }

  async function api(path, body) {
    const r = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    return r.json();
  }

  function _initEvents(panel) {
    panel.querySelector("#kbBootstrapBtn").onclick = () => _bootstrap(panel);
    panel.querySelector("#kbRefreshBtn").onclick   = () => _loadFiles(panel);
    panel.querySelector("#kbSaveBtn").onclick       = () => _saveFile(panel);
    panel.querySelector("#kbDeleteBtn").onclick     = () => _deleteFile(panel);
    panel.querySelector("#kbPreviewBtn").onclick    = () => _previewPrompt();
    panel.querySelector("#kbNewBtn").onclick        = () => _newFile(panel);
    panel.querySelector("#kbEditor").addEventListener("input", () => {
      panel.querySelector("#kbSaveBtn").disabled = false;
    });
  }

  async function _loadFiles(panel) {
    const data = await api("/api/knowledge/list", {});
    const container = panel.querySelector("#kbFileList");
    const files = data.files || [];
    if (!files.length) {
      container.innerHTML = `<em style="color:#888;font-size:13px">No files yet.<br>Click "Create example files".</em>`;
      return;
    }
    container.innerHTML = files.map(f => `
<div class="kb-file-item" data-name="${_esc(f.name)}" style="padding:7px 10px;border-radius:6px;cursor:pointer;font-size:13px;border:1px solid transparent;margin-bottom:4px;transition:background 0.15s"
  onclick="window._kbSelectFile('${_esc(f.name)}')">
  📄 ${_esc(f.name.replace(".md",""))}
  <div style="font-size:11px;color:#9ca3af">${f.size} chars</div>
</div>`).join("");

    _loadStructured(panel);
  }

  window._kbSelectFile = async function (fname) {
    _selectedFile = fname;
    const panel = document.getElementById("tab-knowledgebase");
    // Highlight selected
    panel.querySelectorAll(".kb-file-item").forEach(el => {
      el.style.background = el.dataset.name === fname ? "#eff6ff" : "";
      el.style.borderColor = el.dataset.name === fname ? "#bfdbfe" : "transparent";
    });

    const data = await api("/api/knowledge/get", { file: fname });
    const editor = panel.querySelector("#kbEditor");
    editor.value = data.content || "";
    panel.querySelector("#kbEditorTitle").textContent = fname;
    panel.querySelector("#kbSaveBtn").disabled = true;
    panel.querySelector("#kbDeleteBtn").disabled = false;
  };

  async function _saveFile(panel) {
    if (!_selectedFile) return;
    const content = panel.querySelector("#kbEditor").value;
    const btn = panel.querySelector("#kbSaveBtn");
    btn.disabled = true;
    await api("/api/knowledge/save", { file: _selectedFile, content });
    panel.querySelector("#kbStatus").textContent = `✅ Saved ${_selectedFile}`;
    setTimeout(() => { panel.querySelector("#kbStatus").textContent = ""; }, 2000);
    _loadFiles(panel);
  }

  async function _deleteFile(panel) {
    if (!_selectedFile || !confirm(`Delete ${_selectedFile}?`)) return;
    await api("/api/knowledge/delete", { file: _selectedFile });
    panel.querySelector("#kbEditor").value = "";
    panel.querySelector("#kbEditorTitle").textContent = "Select a file to edit";
    panel.querySelector("#kbSaveBtn").disabled = true;
    panel.querySelector("#kbDeleteBtn").disabled = true;
    _selectedFile = null;
    _loadFiles(panel);
  }

  function _newFile(panel) {
    const fname = prompt("New file name (e.g. style.md):");
    if (!fname) return;
    const name = fname.endsWith(".md") ? fname : fname + ".md";
    if (/[/\\.]\./.test(name)) { alert("Invalid file name"); return; }
    _selectedFile = name;
    panel.querySelector("#kbEditor").value = `# ${name.replace(".md","")}\n\n`;
    panel.querySelector("#kbEditorTitle").textContent = name;
    panel.querySelector("#kbSaveBtn").disabled = false;
    panel.querySelector("#kbDeleteBtn").disabled = true;
  }

  async function _bootstrap(panel) {
    const btn = panel.querySelector("#kbBootstrapBtn");
    btn.disabled = true;
    const data = await api("/api/knowledge/bootstrap", {});
    const created = data.created || [];
    panel.querySelector("#kbStatus").textContent = created.length
      ? `✅ Created: ${created.join(", ")}`
      : "Files already exist — nothing overwritten.";
    btn.disabled = false;
    _loadFiles(panel);
  }

  async function _previewPrompt() {
    const data = await api("/api/knowledge/prompt_preview", {});
    const modal = document.getElementById("kbPromptModal");
    document.getElementById("kbPromptContent").textContent =
      data.system_prompt || "(Knowledge base is empty — add files first)";
    modal.style.display = "flex";
  }

  async function _loadStructured(panel) {
    const data = await api("/api/knowledge/structured", {});
    const container = panel.querySelector("#kbStructured");
    const f = data.founder || {};
    const c = data.company || {};
    const svc = data.approved_services || [];
    const excl = data.excluded_services || [];

    container.innerHTML = `
<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">
  <div>
    <b>👤 Founder</b>
    <table style="font-size:13px;margin-top:6px;width:100%">
      ${Object.entries(f).map(([k,v])=>`<tr><td style="color:#9ca3af;padding:3px 8px 3px 0;width:90px">${k}</td><td>${_esc(v)}</td></tr>`).join("")}
      ${!Object.keys(f).length ? "<tr><td colspan=2 style='color:#ccc'>No founder.md yet</td></tr>" : ""}
    </table>
  </div>
  <div>
    <b>🏢 Company</b>
    <table style="font-size:13px;margin-top:6px;width:100%">
      ${Object.entries(c).map(([k,v])=>`<tr><td style="color:#9ca3af;padding:3px 8px 3px 0;width:100px">${k}</td><td>${_esc(v)}</td></tr>`).join("")}
      ${!Object.keys(c).length ? "<tr><td colspan=2 style='color:#ccc'>No company.md yet</td></tr>" : ""}
    </table>
  </div>
</div>
<div style="margin-top:12px;display:grid;grid-template-columns:1fr 1fr;gap:16px">
  <div>
    <b style="color:#16a34a">✅ Approved services</b>
    <ul style="margin:4px 0 0 20px;font-size:13px">${svc.map(s=>`<li>${_esc(s)}</li>`).join("") || "<li style='color:#ccc'>None listed</li>"}</ul>
  </div>
  <div>
    <b style="color:#ef4444">❌ Excluded services</b>
    <ul style="margin:4px 0 0 20px;font-size:13px">${excl.map(s=>`<li>${_esc(s)}</li>`).join("") || "<li style='color:#ccc'>None listed</li>"}</ul>
  </div>
</div>`;
  }

  function _esc(s) {
    return String(s || "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const tabBtn = document.querySelector(`[data-tab="${TAB_ID}"]`);
    if (!tabBtn) return;
    window.LF.bindTab(tabBtn, () => ensurePanel());
  });
})();
