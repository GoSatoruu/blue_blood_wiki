/**
 * search.js — Live search with debounce, keyboard navigation, and dropdown UI.
 *
 * Works with any <input> that has [data-search-input] and a sibling or
 * adjacent element with [data-search-dropdown].
 *
 * Each search input must also have a [data-search-base-url] attribute set
 * to the URL of the search page (e.g. "/search") so that "See all results"
 * links work correctly.
 */

(function () {
  'use strict';

  const API_URL = '/api/search';
  const DEBOUNCE_MS = 280;
  const MIN_CHARS = 2;

  /** Debounce helper. */
  function debounce(fn, ms) {
    let timer;
    return function (...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), ms);
    };
  }

  /** Escape HTML special chars. */
  function esc(str) {
    return String(str)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /** Highlight the query within a string. */
  function highlight(text, query) {
    if (!query) return esc(text);
    const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const re = new RegExp(`(${escaped})`, 'gi');
    return esc(text).replace(
      new RegExp(`(${escaped.replace(/&/g, '&amp;').replace(/</g, '&lt;')})`, 'gi'),
      '<mark style="background:var(--accent-subtle);color:var(--accent-primary);border-radius:2px;padding:0 2px;">$1</mark>'
    );
  }

  /** Fetch search results from the API. */
  async function fetchResults(query) {
    const url = `${API_URL}?q=${encodeURIComponent(query)}`;
    const res = await fetch(url, { headers: { Accept: 'application/json' } });
    if (!res.ok) throw new Error(`Search API error: ${res.status}`);
    return res.json();
  }

  /** Render a dropdown from results array. */
  function renderDropdown(dropdown, results, query, baseUrl) {
    dropdown.innerHTML = '';

    if (results.length === 0) {
      dropdown.innerHTML = `<div class="search-dropdown-empty">No results for "<strong>${esc(query)}</strong>"</div>`;
      return;
    }

    results.forEach((r, idx) => {
      const a = document.createElement('a');
      a.className = 'search-result-item';
      a.href = r.url;
      a.setAttribute('data-idx', idx);
      a.innerHTML = `
        <span class="search-result-title">${highlight(r.title, query)}</span>
        <span class="search-result-meta">
          <span class="search-result-category">${esc(r.category)}</span>
        </span>
        ${r.snippet ? `<span class="search-result-snippet">${esc(r.snippet)}</span>` : ''}
      `;
      dropdown.appendChild(a);
    });

    // "See all results" footer link
    const footer = document.createElement('a');
    footer.className = 'search-result-item';
    footer.href = `${baseUrl}?q=${encodeURIComponent(query)}`;
    footer.style.cssText = 'background:var(--bg-elevated);justify-content:center;font-size:0.8rem;font-weight:600;color:var(--accent-primary);';
    footer.textContent = `See all results for "${query}" →`;
    dropdown.appendChild(footer);
  }

  /** Show dropdown. */
  function showDropdown(dropdown) {
    dropdown.style.display = 'block';
  }

  /** Hide dropdown. */
  function hideDropdown(dropdown) {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
  }

  /** Set active item by index. */
  function setActive(dropdown, idx) {
    const items = dropdown.querySelectorAll('.search-result-item');
    items.forEach((item, i) => {
      item.classList.toggle('is-active', i === idx);
    });
  }

  /** Initialize a single search input + dropdown pair. */
  function initSearchPair(input, dropdown) {
    const baseUrl = input.dataset.searchBaseUrl || '/search';
    let activeIdx = -1;
    let lastQuery = '';
    let isLoading = false;

    const doSearch = debounce(async function (query) {
      if (query.length < MIN_CHARS) {
        hideDropdown(dropdown);
        return;
      }
      isLoading = true;
      try {
        const results = await fetchResults(query);
        lastQuery = query;
        activeIdx = -1;
        renderDropdown(dropdown, results, query, baseUrl);
        showDropdown(dropdown);
      } catch (e) {
        console.error('[search.js]', e);
      } finally {
        isLoading = false;
      }
    }, DEBOUNCE_MS);

    input.addEventListener('input', function () {
      const q = this.value.trim();
      if (!q) { hideDropdown(dropdown); return; }
      doSearch(q);
    });

    input.addEventListener('keydown', function (e) {
      const items = dropdown.querySelectorAll('.search-result-item');
      if (!items.length) return;

      if (e.key === 'ArrowDown') {
        e.preventDefault();
        activeIdx = Math.min(activeIdx + 1, items.length - 1);
        setActive(dropdown, activeIdx);
        items[activeIdx]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        activeIdx = Math.max(activeIdx - 1, -1);
        setActive(dropdown, activeIdx);
        if (activeIdx >= 0) items[activeIdx]?.scrollIntoView({ block: 'nearest' });
      } else if (e.key === 'Enter') {
        if (activeIdx >= 0 && items[activeIdx]) {
          e.preventDefault();
          items[activeIdx].click();
        } else if (this.value.trim()) {
          e.preventDefault();
          window.location.href = `${baseUrl}?q=${encodeURIComponent(this.value.trim())}`;
        }
      } else if (e.key === 'Escape') {
        hideDropdown(dropdown);
        this.blur();
      }
    });

    // Hide dropdown when clicking outside
    document.addEventListener('click', function (e) {
      if (!input.contains(e.target) && !dropdown.contains(e.target)) {
        hideDropdown(dropdown);
      }
    });

    // Re-show dropdown on re-focus if there's a query
    input.addEventListener('focus', function () {
      if (this.value.trim().length >= MIN_CHARS && dropdown.innerHTML) {
        showDropdown(dropdown);
      }
    });
  }

  /** Initialize all search pairs on the page. */
  function init() {
    const inputs = document.querySelectorAll('[data-search-input]');
    inputs.forEach((input) => {
      const dropdownId = input.dataset.searchDropdown;
      const dropdown = dropdownId
        ? document.getElementById(dropdownId)
        : input.parentElement.querySelector('[data-search-dropdown]');

      if (!dropdown) {
        console.warn('[search.js] No dropdown found for input', input);
        return;
      }

      hideDropdown(dropdown);
      initSearchPair(input, dropdown);
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
