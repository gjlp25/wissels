/* Isolated appearance preference: never reads or writes team/match records.
   Runs in the head before paint; the native control is wired after parsing. */
(() => {
  'use strict';
  const KEY = 'pupillentrainer-theme';
  const valid = value => ['system', 'light', 'dark'].includes(value) ? value : 'system';
  const media = window.matchMedia('(prefers-color-scheme: dark)');
  let preference = 'system';
  try { preference = valid(localStorage.getItem(KEY)); } catch { /* Storage may be blocked. */ }
  const apply = () => {
    document.documentElement.setAttribute('data-theme', preference === 'system' ? (media.matches ? 'dark' : 'light') : preference);
    const select = document.querySelector('#themeChoice');
    if (select) select.value = preference;
  };
  apply();
  media.addEventListener('change', apply);
  window.addEventListener('storage', event => {
    if (event.key !== KEY && event.key !== null) return;
    // Ignore sessionStorage and synthetic updates from another storage area.
    try { if (event.storageArea !== localStorage) return; } catch { return; }
    preference = valid(event.newValue);
    apply();
  });
  document.addEventListener('DOMContentLoaded', () => {
    const select = document.querySelector('#themeChoice');
    if (!select) return;
    select.value = preference;
    select.addEventListener('change', () => {
      preference = valid(select.value);
      apply();
      try { localStorage.setItem(KEY, preference); } catch { /* Keep the choice for this page. */ }
    });
  });
})();
