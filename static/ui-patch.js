/**
 * static/ui-patch.js — Design system patch for dynamically-created tab panels.
 *
 * All tab JS files create their panels with inline styles or old .card/.btn-primary
 * class names. This file:
 *   1. Rewrites .btn-primary → .btn.primary and .btn-secondary → .btn
 *   2. Applies the new CSS variable color tokens to old inline style references
 *   3. Patches tab panels to use the .page wrapper and correct card styles
 *
 * Loaded LAST (after all tab JS files) so it can safely patch their output.
 */
(function () {
  'use strict';

  /* ── Map old class names from dynamic JS tabs to new design system ── */
  function patchClasses(root) {
    // btn-primary → btn primary
    root.querySelectorAll('.btn-primary').forEach(el => {
      el.classList.remove('btn-primary');
      el.classList.add('btn', 'primary');
    });
    // btn-secondary → btn
    root.querySelectorAll('.btn-secondary').forEach(el => {
      el.classList.remove('btn-secondary');
      el.classList.add('btn');
    });
    // .card without .panel → keep .card (already defined)
    // Fix any hardcoded white backgrounds
    root.querySelectorAll('[style]').forEach(el => {
      let s = el.getAttribute('style') || '';
      s = s
        .replace(/background\s*:\s*#fff(;|$|\s)/gi, 'background:var(--surface)$1')
        .replace(/background\s*:\s*white(;|$|\s)/gi, 'background:var(--surface)$1')
        .replace(/background\s*:\s*#f8fafc(;|$|\s)/gi, 'background:var(--surface-2)$1')
        .replace(/background\s*:\s*#f1f5f9(;|$|\s)/gi, 'background:var(--surface-3)$1')
        .replace(/background\s*:\s*#f0f9ff(;|$|\s)/gi, 'background:var(--blue-bg)$1')
        .replace(/background\s*:\s*#ecfdf5(;|$|\s)/gi, 'background:var(--green-bg)$1')
        .replace(/background\s*:\s*#fef9c3(;|$|\s)/gi, 'background:var(--yellow-bg)$1')
        .replace(/background\s*:\s*#fee2e2(;|$|\s)/gi, 'background:var(--red-bg)$1')
        .replace(/background\s*:\s*#fffbeb(;|$|\s)/gi, 'background:var(--yellow-bg)$1')
        .replace(/background\s*:\s*#f0fdf4(;|$|\s)/gi, 'background:var(--green-bg)$1')
        .replace(/color\s*:\s*#374151(;|$|\s)/gi, 'color:var(--ink)$1')
        .replace(/color\s*:\s*#1e293b(;|$|\s)/gi, 'color:var(--ink)$1')
        .replace(/color\s*:\s*#64748b(;|$|\s)/gi, 'color:var(--ink-3)$1')
        .replace(/color\s*:\s*#9ca3af(;|$|\s)/gi, 'color:var(--ink-3)$1')
        .replace(/color\s*:\s*#94a3b8(;|$|\s)/gi, 'color:var(--ink-3)$1')
        .replace(/color\s*:\s*#6b7280(;|$|\s)/gi, 'color:var(--ink-3)$1')
        .replace(/color\s*:\s*#666(;|$|\s)/gi, 'color:var(--ink-2)$1')
        .replace(/color\s*:\s*#888(;|$|\s)/gi, 'color:var(--ink-3)$1')
        .replace(/color\s*:\s*#059669(;|$|\s)/gi, 'color:var(--green)$1')
        .replace(/color\s*:\s*#16a34a(;|$|\s)/gi, 'color:var(--green)$1')
        .replace(/color\s*:\s*#15803d(;|$|\s)/gi, 'color:var(--green)$1')
        .replace(/color\s*:\s*#ef4444(;|$|\s)/gi, 'color:var(--red)$1')
        .replace(/color\s*:\s*#f59e0b(;|$|\s)/gi, 'color:var(--yellow)$1')
        .replace(/color\s*:\s*#2563eb(;|$|\s)/gi, 'color:var(--blue)$1')
        .replace(/color\s*:\s*#0369a1(;|$|\s)/gi, 'color:var(--blue)$1')
        .replace(/border\s*:\s*1px solid #e2e8f0/gi, 'border:1px solid var(--border)')
        .replace(/border\s*:\s*1px solid #d1d5db/gi, 'border:1px solid var(--border)')
        .replace(/border-radius\s*:\s*8px/gi, 'border-radius:var(--r-md)')
        .replace(/border-radius\s*:\s*10px/gi, 'border-radius:var(--r-lg)')
        .replace(/border-radius\s*:\s*12px/gi, 'border-radius:var(--r-lg)')
        .replace(/border-radius\s*:\s*6px/gi, 'border-radius:var(--r-sm)');
      el.setAttribute('style', s);
    });

    // Fix h2/h3 inside panels to use display font
    root.querySelectorAll('.card h2, .card h3, .panel h2, .panel h3').forEach(el => {
      el.style.fontFamily = 'var(--font-display)';
    });

    // Fix input/select/textarea references that have hardcoded background
    root.querySelectorAll('input, select, textarea').forEach(el => {
      const s = el.getAttribute('style') || '';
      if (s.includes('background:#fff') || s.includes('background: #fff') || s.includes('background:white')) {
        el.style.background = 'var(--surface-2)';
      }
    });
  }

  /* ── Wrap dynamically-created sections in .page if missing ── */
  function ensurePageWrapper(section) {
    if (!section.classList.contains('page')) {
      section.classList.add('page');
    }
  }

  /* ── Remove duplicate nav buttons created by dynamic JS tab modules ── */
  function dedupNavButtons(){
    const nav = document.querySelector('nav.sidebar');
    if (!nav) return;
    const seen = new Set();
    nav.querySelectorAll('[data-tab]').forEach(btn => {
      const tab = btn.dataset.tab;
      if (seen.has(tab)){
        btn.remove();
      } else {
        seen.add(tab);
      }
    });
  }

  /* ── Watch for new tab panels being created ── */
  const observer = new MutationObserver(mutations => {
    mutations.forEach(m => {
      m.addedNodes.forEach(node => {
        if (node.nodeType !== 1) return;
        // If it's a section with tab- id, it's a new panel
        if (node.tagName === 'SECTION' && node.id && node.id.startsWith('tab-')) {
          ensurePageWrapper(node);
          setTimeout(() => { patchClasses(node); dedupNavButtons(); }, 50);
        }
        // Also patch any card/panel children
        if (node.classList && (node.classList.contains('card') || node.classList.contains('panel'))) {
          setTimeout(() => patchClasses(node), 50);
        }
      });
    });
  });

  document.addEventListener('DOMContentLoaded', () => {
    // Patch all existing panels
    document.querySelectorAll('section[id^="tab-"]').forEach(s => {
      ensurePageWrapper(s);
      patchClasses(s);
    });

    // Dedup any nav buttons already created by dynamic JS
    setTimeout(dedupNavButtons, 100);
    setTimeout(dedupNavButtons, 500);
    setTimeout(dedupNavButtons, 1500);

    // Watch for future panels
    const main = document.querySelector('.main-content');
    if (main) observer.observe(main, { childList: true, subtree: true });
    // Also watch the sidebar nav for dynamically added tab buttons
    const nav = document.querySelector('nav.sidebar');
    if (nav) {
      const navObs = new MutationObserver(() => dedupNavButtons());
      navObs.observe(nav, { childList: true, subtree: true });
    }
  });

  // Also expose as global for manual use
  window.LFUIPatch = patchClasses;
})();
