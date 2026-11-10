/**
 * static/social-auto.js — Social media outreach automation config tab.
 *
 * Configures the meta-automation agent for Threads, Instagram, Facebook, and
 * LinkedIn outreach. The agent reads .leadfinder/knowledge/ files as its
 * source of truth, uses the accessibility tree (not CSS selectors), and
 * qualifies prospects with AI intent detection.
 */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const store = (k, d, v) => { try { if (v !== undefined){ localStorage.setItem(k, JSON.stringify(v)); return v; } const x = localStorage.getItem(k); return x ? JSON.parse(x) : d; } catch(e){ return d; } };

  function mount() {
    const sec = document.createElement('section');
    sec.id = 'tab-social-auto';
    sec.hidden = true;
    sec.innerHTML = `
      <div class="card">
        <div class="card-title"><span class="icon">📱</span> Social Media Automation</div>
        <p class="sub" style="margin-top:-4px;margin-bottom:16px">
          Autonomous social media outreach across Threads, Instagram, Facebook, and LinkedIn.
          The agent reads your knowledge base to understand who you are and what you offer,
          qualifies prospects with AI intent detection, and uses human-like interaction patterns.
        </p>

        <!-- Platform status -->
        <div id="saPlatforms" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:12px;margin-bottom:20px">
          ${['Threads','Instagram','Facebook','LinkedIn'].map(p => `
            <div style="background:var(--surface-2);border:1px solid var(--border);border-radius:var(--r-lg);padding:14px;text-align:center">
              <div style="font-size:24px;margin-bottom:6px">${{'Threads':'🧵','Instagram':'📸','Facebook':'📘','LinkedIn':'💼'}[p]}</div>
              <div style="font-weight:600;font-size:13px">${p}</div>
              <div class="badge gray" style="margin-top:6px" id="sa-${p.toLowerCase()}-status">Not configured</div>
            </div>`).join('')}
        </div>

        <!-- Setup guide -->
        <div class="card" style="margin-bottom:16px;background:var(--surface-2)">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">📦</span> Setup Guide</div>
          <ol style="color:var(--ink-2);font-size:13.5px;line-height:2;padding-left:20px">
            <li>Ensure <a href="https://nodejs.org" target="_blank">Node.js 18+</a> is installed</li>
            <li>Open a terminal in the <code>meta-automation/</code> folder from this project</li>
            <li>Run <code>npm install</code> to install dependencies</li>
            <li>Edit <code>founder.md</code> and <code>services.md</code> in <code>.leadfinder/knowledge/</code> — these tell the agent who you are</li>
            <li>Run <code>npm start</code> to launch the agent</li>
            <li>The agent will open a browser, log into your social accounts, and start finding prospects</li>
          </ol>
          <div class="msg warn" style="margin-top:8px">
            <div>⚠️ Social media platforms have strict automation policies. Use with your own accounts only and keep interaction rates low to protect your accounts.</div>
          </div>
        </div>

        <!-- AI Intent Qualification -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">🤖</span> AI Intent Qualification</div>
          <p class="sub" style="margin-bottom:10px">The agent uses 6 buyer intent categories to qualify prospects. Adjust which categories to pursue:</p>
          <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
            ${[
              ['needs_website','🔥 Needs a website','Business posting about being found online or asking for a website'],
              ['local_business','📍 Local business','Local service business with poor digital presence'],
              ['hiring_designer','💼 Hiring a designer','Actively posting about needing web design help'],
              ['startup_founder','🚀 Startup founder','Building a company that needs a web presence'],
              ['rebranding','🎨 Rebranding','Mentioning rebrand, new look, or website redesign'],
              ['frustrated_online','😤 Frustrated online','Complaining about their website, online presence, or tech'],
            ].map(([id,label,desc]) => `
              <div style="display:flex;gap:10px;align-items:flex-start;padding:10px;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--r-md)">
                <input type="checkbox" id="sa_${id}" checked style="width:auto;margin-top:3px">
                <div><div style="font-size:13px;font-weight:600">${label}</div><div class="sub" style="font-size:11.5px">${desc}</div></div>
              </div>`).join('')}
          </div>
          <div class="msg info" style="margin-top:10px;font-size:12px">
            <div>Recruiters, job seekers, and out-of-scope accounts are automatically disqualified.</div>
          </div>
        </div>

        <!-- Interaction settings -->
        <div class="card" style="margin-bottom:16px">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">⚙️</span> Interaction Settings</div>
          <div class="grid-3">
            <div class="form-group">
              <label>Max interactions per platform / day</label>
              <input id="saDailyLimit" type="number" value="15" min="1" max="50">
            </div>
            <div class="form-group">
              <label>Min delay between actions (sec)</label>
              <input id="saMinDelay" type="number" value="30" min="10" max="120">
            </div>
            <div class="form-group">
              <label>Quiet hours start</label>
              <input id="saQuietStart" type="time" value="22:00">
            </div>
            <div class="form-group">
              <label>Quiet hours end</label>
              <input id="saQuietEnd" type="time" value="08:00">
            </div>
            <div class="form-group">
              <label>AI provider for qualification</label>
              <select id="saAIProvider">
                <option value="pool">Use AI Pool (auto-rotate)</option>
                <option value="local">Local (Ollama)</option>
                <option value="rule">Rule engine (no AI)</option>
              </select>
            </div>
            <div class="form-group">
              <label>Action type</label>
              <select id="saAction">
                <option value="comment">Comment on posts</option>
                <option value="dm">Direct message</option>
                <option value="both">Comment + DM</option>
                <option value="like">Like + follow only</option>
              </select>
            </div>
          </div>
          <button class="btn sm primary" id="saSaveSettings">💾 Save Settings</button>
          <div id="saSettingsMsg"></div>
        </div>

        <!-- DM Template -->
        <div class="card">
          <div class="card-title" style="font-size:14px"><span class="icon" style="font-size:13px">✍️</span> DM Template</div>
          <p class="sub" style="margin-bottom:10px">The agent will personalize this based on the prospect's post and profile. Use variables: {name}, {topic}, {your_name}</p>
          <textarea id="saDMTemplate" style="min-height:100px" placeholder="Hi {name}, I saw your post about {topic}. I help businesses like yours get found online — would you be open to a quick chat?">{your_name}"></textarea>
          <button class="btn sm" id="saSaveDM" style="margin-top:10px">💾 Save Template</button>
          <div id="saDMMsg"></div>
        </div>
      </div>
    `;

    const main = document.querySelector('.main-content') || document.querySelector('.wrap');
    if (main) main.appendChild(sec);

    // Load saved settings
    const cfg = store('lf-social-auto-cfg', {
      dailyLimit: 15, minDelay: 30, quietStart: '22:00', quietEnd: '08:00',
      aiProvider: 'pool', action: 'comment', dm: 'Hi {name}, I saw your post about {topic}. I help businesses like yours get found online — would you be open to a quick chat?\n\n{your_name}',
      intents: { needs_website: true, local_business: true, hiring_designer: true, startup_founder: true, rebranding: true, frustrated_online: true },
    });
    $('#saDailyLimit').value = cfg.dailyLimit;
    $('#saMinDelay').value = cfg.minDelay;
    $('#saQuietStart').value = cfg.quietStart;
    $('#saQuietEnd').value = cfg.quietEnd;
    $('#saAIProvider').value = cfg.aiProvider;
    $('#saAction').value = cfg.action;
    $('#saDMTemplate').value = cfg.dm;
    Object.keys(cfg.intents).forEach(id => {
      const cb = $('#sa_' + id);
      if (cb) cb.checked = cfg.intents[id];
    });

    // Save settings
    $('#saSaveSettings')?.addEventListener('click', () => {
      const intents = {};
      ['needs_website','local_business','hiring_designer','startup_founder','rebranding','frustrated_online'].forEach(id => {
        const cb = $('#sa_' + id);
        if (cb) intents[id] = cb.checked;
      });
      const newCfg = {
        dailyLimit: +$('#saDailyLimit').value,
        minDelay: +$('#saMinDelay').value,
        quietStart: $('#saQuietStart').value,
        quietEnd: $('#saQuietEnd').value,
        aiProvider: $('#saAIProvider').value,
        action: $('#saAction').value,
        dm: $('#saDMTemplate').value,
        intents,
      };
      store('lf-social-auto-cfg', null, newCfg);
      $('#saSettingsMsg').innerHTML = '<div class="msg ok">Settings saved.</div>';
      setTimeout(() => { const el = $('#saSettingsMsg'); if (el) el.innerHTML = ''; }, 3000);
      if (window.LF?.toast) window.LF.toast('Social automation settings saved', 'success');
    });

    // Save DM template
    $('#saSaveDM')?.addEventListener('click', () => {
      const cfg = store('lf-social-auto-cfg', {});
      cfg.dm = $('#saDMTemplate').value;
      store('lf-social-auto-cfg', null, cfg);
      $('#saDMMsg').innerHTML = '<div class="msg ok">Template saved.</div>';
      setTimeout(() => { const el = $('#saDMMsg'); if (el) el.innerHTML = ''; }, 3000);
    });
  }

  function createNavButton() {
    const nav = document.querySelector('nav.sidebar');
    if (!nav) return;
    const groups = nav.querySelectorAll('.nav-group');
    let outreachGroup = null;
    groups.forEach(g => {
      if (g.querySelector('.nav-group-label')?.textContent === 'Outreach') outreachGroup = g;
    });
    const b = document.createElement('button');
    b.className = 'nav-item';
    b.setAttribute('role', 'tab');
    b.dataset.tab = 'social-auto';
    b.innerHTML = '<span class="nav-icon">📱</span> Social Auto';
    if (outreachGroup) outreachGroup.appendChild(b);
    else nav.appendChild(b);
    if (window.LF?.bindTab) window.LF.bindTab(b, null);
  }

  if (window.LF) {
    setTimeout(() => { mount(); createNavButton(); }, 300);
  } else {
    document.addEventListener('DOMContentLoaded', () => {
      setTimeout(() => { mount(); createNavButton(); }, 300);
    });
  }
})();
