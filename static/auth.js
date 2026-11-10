/**
 * static/auth.js — Multi-user authentication UI for LeadFinder.
 *
 * On page load, checks if multi-user mode is enabled via /api/auth/status.
 * If enabled and no valid session, shows a login/registration overlay.
 * Stores token in localStorage and sends it with API calls when present.
 */
(function () {
  'use strict';
  const $ = s => document.querySelector(s);
  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
  const AUTH_TOKEN_KEY = 'lf-auth-token';
  const AUTH_USER_KEY = 'lf-auth-user';

  function getToken() { return localStorage.getItem(AUTH_TOKEN_KEY) || ''; }
  function setToken(t) { localStorage.setItem(AUTH_TOKEN_KEY, t); }
  function clearToken() { localStorage.removeItem(AUTH_TOKEN_KEY); localStorage.removeItem(AUTH_USER_KEY); }
  function getUser() { try { return JSON.parse(localStorage.getItem(AUTH_USER_KEY) || 'null'); } catch(e){ return null; } }
  function setUser(u) { localStorage.setItem(AUTH_USER_KEY, JSON.stringify(u)); }

  // Inject auth overlay CSS
  const style = document.createElement('style');
  style.textContent = `
    .auth-overlay {
      position: fixed; top:0; left:0; right:0; bottom:0;
      background: var(--bg); z-index: 10000;
      display: none; align-items: center; justify-content: center;
      padding: 20px;
    }
    .auth-overlay.show { display: flex; }
    .auth-card {
      width: 100%; max-width: 400px;
      background: var(--surface); border: 1px solid var(--border);
      border-radius: var(--r-xl); box-shadow: var(--shadow-lg);
      padding: 36px 32px; animation: fade-in-up 0.3s ease;
    }
    .auth-logo {
      display: flex; align-items: center; gap: 12px; margin-bottom: 28px;
    }
    .auth-logo .logo-icon { width: 44px; height: 44px; font-size: 22px; }
    .auth-logo .logo-text { font-family: var(--font-display); font-size: 20px; font-weight: 800; }
    .auth-tabs {
      display: flex; gap: 0; margin-bottom: 24px;
      background: var(--surface-2); border-radius: var(--r-md); padding: 3px;
    }
    .auth-tab {
      flex: 1; padding: 9px; text-align: center;
      border-radius: var(--r-sm); cursor: pointer;
      font-size: 13.5px; font-weight: 600; color: var(--ink-2);
      transition: all 0.15s; border: none; background: none;
    }
    .auth-tab.active { background: var(--accent); color: var(--accent-text); }
    .auth-form { display: none; }
    .auth-form.active { display: block; }
    .auth-form .form-group { margin-bottom: 16px; }
    .auth-form label { font-size: 12.5px; }
    .auth-form input { font-size: 14px; }
    .auth-form .btn { margin-top: 8px; }
    .auth-msg { margin: 12px 0 0; }
    .auth-note { font-size: 12px; color: var(--ink-3); margin-top: 16px; text-align: center; }
    .auth-banner {
      position: fixed; top: 0; left: 0; right: 0;
      background: var(--blue-bg); color: var(--blue);
      font-size: 12.5px; text-align: center; padding: 6px;
      z-index: 99; display: none; border-bottom: 1px solid var(--blue)22;
    }
    .auth-banner.show { display: block; }
  `;
  document.head.appendChild(style);

  // Build the auth overlay
  const overlay = document.createElement('div');
  overlay.className = 'auth-overlay';
  overlay.id = 'authOverlay';
  overlay.innerHTML = `
    <div class="auth-card">
      <div class="auth-logo">
        <div class="logo-icon">🎯</div>
        <div>
          <div class="logo-text">LeadFinder</div>
          <div class="sub" style="font-size:11px">AI Lead Intelligence</div>
        </div>
      </div>
      <div class="auth-tabs">
        <button class="auth-tab active" id="authTabLogin">Login</button>
        <button class="auth-tab" id="authTabRegister">Register</button>
      </div>
      <form class="auth-form active" id="authLoginForm">
        <div class="form-group">
          <label>Username</label>
          <input id="loginUser" placeholder="Enter username" autocomplete="username">
        </div>
        <div class="form-group">
          <label>Password</label>
          <input id="loginPass" type="password" placeholder="Enter password" autocomplete="current-password">
        </div>
        <button class="btn primary full lg" type="submit">Login →</button>
        <div class="auth-msg" id="loginMsg"></div>
      </form>
      <form class="auth-form" id="authRegisterForm">
        <div class="form-group">
          <label>Display name</label>
          <input id="regName" placeholder="e.g. Ali Raza">
        </div>
        <div class="form-group">
          <label>Username</label>
          <input id="regUser" placeholder="Choose a username" autocomplete="username">
        </div>
        <div class="form-group">
          <label>Password</label>
          <input id="regPass" type="password" placeholder="Choose a password (min 4 chars)" autocomplete="new-password">
        </div>
        <button class="btn primary full lg" type="submit">Create account →</button>
        <div class="auth-msg" id="regMsg"></div>
      </form>
      <div class="auth-note">
        Your data stays on this machine. No cloud, no SaaS.
      </div>
    </div>
  `;
  document.body.appendChild(overlay);

  // Banner for multi-user mode
  const banner = document.createElement('div');
  banner.className = 'auth-banner';
  banner.id = 'authBanner';
  banner.innerHTML = '👥 Multi-user mode — you are logged in as <b id="authBannerUser"></b>';
  document.body.appendChild(banner);

  // Tab switching
  function switchAuthTab(tab) {
    document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.auth-form').forEach(f => f.classList.remove('active'));
    if (tab === 'login') {
      $('#authTabLogin').classList.add('active');
      $('#authLoginForm').classList.add('active');
    } else {
      $('#authTabRegister').classList.add('active');
      $('#authRegisterForm').classList.add('active');
    }
  }
  $('#authTabLogin').onclick = () => switchAuthTab('login');
  $('#authTabRegister').onclick = () => switchAuthTab('register');

  // API helper
  async function authApi(path, body) {
    const r = await fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}) });
    return r.json();
  }

  // Show/hide auth overlay
  function showAuthOverlay() { $('#authOverlay').classList.add('show'); }
  function hideAuthOverlay() { $('#authOverlay').classList.remove('show'); }

  // Login form
  $('#authLoginForm').onsubmit = async (e) => {
    e.preventDefault();
    const msg = $('#loginMsg');
    msg.innerHTML = '<span class="spin"></span> Logging in…';
    try {
      const r = await authApi('/api/auth/login', {
        username: $('#loginUser').value.trim(),
        password: $('#loginPass').value,
      });
      if (r.success) {
        setToken(r.token);
        setUser(r.user);
        hideAuthOverlay();
        updateAuthUI();
        if (window.LF?.toast) window.LF.toast(`Welcome back, ${r.user.display_name}!`, 'success', 'Logged in');
      } else {
        msg.innerHTML = `<div class="msg err">${esc(r.error || 'Login failed')}</div>`;
      }
    } catch (err) {
      msg.innerHTML = `<div class="msg err">${esc(err.message)}</div>`;
    }
  };

  // Register form
  $('#authRegisterForm').onsubmit = async (e) => {
    e.preventDefault();
    const msg = $('#regMsg');
    msg.innerHTML = '<span class="spin"></span> Creating account…';
    try {
      const r = await authApi('/api/auth/register', {
        display_name: $('#regName').value.trim(),
        username: $('#regUser').value.trim(),
        password: $('#regPass').value,
      });
      if (r.success) {
        setToken(r.token);
        setUser(r.user);
        hideAuthOverlay();
        updateAuthUI();
        if (window.LF?.toast) window.LF.toast(`Account created — welcome, ${r.user.display_name}!`, 'success', 'Registered');
      } else {
        msg.innerHTML = `<div class="msg err">${esc(r.error || 'Registration failed')}</div>`;
      }
    } catch (err) {
      msg.innerHTML = `<div class="msg err">${esc(err.message)}</div>`;
    }
  };

  // Update UI with logged-in user
  function updateAuthUI() {
    const user = getUser();
    const banner = $('#authBanner');
    const bannerUser = $('#authBannerUser');
    const avatar = $('#userAvatar');
    if (user) {
      banner?.classList.add('show');
      if (bannerUser) bannerUser.textContent = user.display_name || user.username;
      if (avatar) avatar.textContent = (user.display_name || user.username).charAt(0).toUpperCase();
      avatar?.setAttribute('title', `${user.display_name} (${user.role})`);
    } else {
      banner?.classList.remove('show');
    }
  }

  // Expose auth utilities globally
  window.LFAuth = {
    getToken, getUser, clearToken, showAuthOverlay, hideAuthOverlay, updateAuthUI,
    logout: async () => {
      const token = getToken();
      if (token) await authApi('/api/auth/logout', { token });
      clearToken();
      updateAuthUI();
      showAuthOverlay();
      if (window.LF?.toast) window.LF.toast('Logged out', 'info');
    },
  };

  // Check auth status on load
  async function initAuth() {
    try {
      const r = await fetch('/api/auth/status').then(r => r.json());
      if (r.enabled) {
        // Multi-user mode is on — verify session
        const token = getToken();
        if (token) {
          const v = await authApi('/api/auth/verify', { token });
          if (v.valid) {
            setUser(v.user);
            updateAuthUI();
          } else {
            clearToken();
            showAuthOverlay();
          }
        } else {
          showAuthOverlay();
        }
      }
      // If not enabled, do nothing (single-user mode)
    } catch (e) {
      // Auth not available — single-user mode
    }
  }

  // Run after DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initAuth);
  } else {
    initAuth();
  }
})();
