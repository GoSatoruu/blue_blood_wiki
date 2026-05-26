/**
 * theme.js — Dark / Light theme toggle with localStorage persistence.
 *
 * Reads the user's stored preference or OS preference on page load.
 * Toggles `data-theme="dark"` on the <html> element.
 * Updates the toggle button icon accordingly.
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'bbwiki-theme';
  const DARK = 'dark';
  const LIGHT = 'light';

  /** Return the currently active theme string. */
  function getTheme() {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored === DARK || stored === LIGHT) return stored;
    // Fall back to OS preference
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? DARK : LIGHT;
  }

  /** Apply a theme to the <html> element and update all toggle buttons. */
  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    updateButtons(theme);
  }

  /** Update all theme-toggle buttons on the page. */
  function updateButtons(theme) {
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach((btn) => {
      btn.setAttribute('aria-label', theme === DARK ? 'Switch to light mode' : 'Switch to dark mode');
      btn.setAttribute('title', theme === DARK ? 'Light mode' : 'Dark mode');
      btn.textContent = theme === DARK ? '☀️' : '🌙';
    });
  }

  /** Toggle between dark and light. */
  function toggle() {
    const current = getTheme();
    applyTheme(current === DARK ? LIGHT : DARK);
  }

  // Apply theme immediately (before DOM is fully ready) to prevent flash.
  applyTheme(getTheme());

  // Wire up buttons once DOM is ready.
  document.addEventListener('DOMContentLoaded', function () {
    document.querySelectorAll('[data-theme-toggle]').forEach((btn) => {
      btn.addEventListener('click', toggle);
    });
    // Re-apply to ensure button text is correct after DOM is ready.
    updateButtons(getTheme());
  });

  // Expose for programmatic use.
  window.wikiTheme = { toggle, getTheme, applyTheme };
})();
