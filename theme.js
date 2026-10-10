/* Isolated appearance preference: never reads or writes team/match records.
   Runs in the head before paint; the native control is wired after parsing. */
(() => {
  'use strict';
  const KEY = 'pupillentrainer-theme';
  const valid = value => ['light', 'dark'].includes(value) ? value : 'light';
  let preference = 'light';
  try { preference = valid(localStorage.getItem(KEY)); } catch { /* Storage may be blocked. */ }
  const apply = () => {
    document.documentElement.setAttribute('data-theme', preference);
    for (const button of document.querySelectorAll('[data-theme-choice]')) {
      button.setAttribute('aria-pressed', String(button.dataset.themeChoice === preference));
    }
  };
  apply();
  window.addEventListener('storage', event => {
    if (event.key !== KEY && event.key !== null) return;
    // Ignore sessionStorage and synthetic updates from another storage area.
    try { if (event.storageArea !== localStorage) return; } catch { return; }
    preference = valid(event.newValue);
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    for (const button of document.querySelectorAll('[data-theme-choice]')) {
      button.addEventListener('click', () => {
        preference = valid(button.dataset.themeChoice);
        apply();
        try { localStorage.setItem(KEY, preference); } catch { /* Keep the choice for this page. */ }
      });
      button.disabled = false;
    }
    apply();
  });
})();
