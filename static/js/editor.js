/**
 * editor.js — Markdown editor with live preview, slug generation,
 * toolbar formatting shortcuts, and unsaved-changes guard.
 *
 * Requires: a <textarea id="content-editor"> and a <div id="preview-pane">
 * in the edit form.
 */

(function () {
  'use strict';

  // ── Minimal Markdown → HTML renderer (client-side preview only) ──────────

  /**
   * A lightweight regex-based Markdown renderer for the live preview.
   * Not as full-featured as mistune on the server but sufficient for preview.
   */
  function renderMarkdown(md) {
    if (!md) return '';

    let html = md;

    // Escape HTML entities first (except we WANT to render markdown)
    // We only escape < and > that aren't part of markdown constructs.
    html = html
      // Tables (must be before paragraph processing)
      .replace(/^\|(.+)\|\s*\n\|[-| :]+\|\s*\n((?:\|.+\|\s*\n?)+)/gm, function (_, header, rows) {
        const ths = header.split('|').filter(Boolean).map(h => `<th>${h.trim()}</th>`).join('');
        const trs = rows.trim().split('\n').map(row => {
          const tds = row.split('|').filter(Boolean).map(c => `<td>${c.trim()}</td>`).join('');
          return `<tr>${tds}</tr>`;
        }).join('\n');
        return `<table>\n<thead><tr>${ths}</tr></thead>\n<tbody>${trs}</tbody>\n</table>\n`;
      })

      // Headings
      .replace(/^###### (.+)$/gm, '<h6>$1</h6>')
      .replace(/^##### (.+)$/gm, '<h5>$1</h5>')
      .replace(/^#### (.+)$/gm, '<h4>$1</h4>')
      .replace(/^### (.+)$/gm, '<h3>$1</h3>')
      .replace(/^## (.+)$/gm, '<h2>$1</h2>')
      .replace(/^# (.+)$/gm, '<h1>$1</h1>')

      // Blockquotes
      .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')

      // Horizontal rules
      .replace(/^---+$/gm, '<hr>')

      // Unordered lists (simple, single-level)
      .replace(/((?:^[-*+] .+\n?)+)/gm, function (match) {
        const items = match.trim().split('\n').map(l => `<li>${l.replace(/^[-*+] /, '').trim()}</li>`).join('');
        return `<ul>${items}</ul>\n`;
      })

      // Ordered lists
      .replace(/((?:^\d+\. .+\n?)+)/gm, function (match) {
        const items = match.trim().split('\n').map(l => `<li>${l.replace(/^\d+\. /, '').trim()}</li>`).join('');
        return `<ol>${items}</ol>\n`;
      })

      // Fenced code blocks
      .replace(/```[\w]*\n([\s\S]*?)```/g, '<pre><code>$1</code></pre>')

      // Inline code
      .replace(/`([^`]+)`/g, '<code>$1</code>')

      // Bold & Italic
      .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
      .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.+?)\*/g, '<em>$1</em>')
      .replace(/__(.+?)__/g, '<strong>$1</strong>')
      .replace(/_(.+?)_/g, '<em>$1</em>')

      // Strikethrough
      .replace(/~~(.+?)~~/g, '<del>$1</del>')

      // Links & images
      .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, '<img src="$2" alt="$1">')
      .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')

      // Paragraphs: double newlines → <p>
      .replace(/\n{2,}/g, '\n\n')
      .split('\n\n')
      .map(block => {
        block = block.trim();
        if (!block) return '';
        const isBlock = /^(<h[1-6]|<ul|<ol|<pre|<blockquote|<table|<hr)/.test(block);
        return isBlock ? block : `<p>${block.replace(/\n/g, '<br>')}</p>`;
      })
      .join('\n');

    return html;
  }

  // ── Slug helpers ─────────────────────────────────────────────────────────

  function generateSlug(title) {
    return title
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '')
      .replace(/[\s_]+/g, '-')
      .replace(/^-+|-+$/g, '');
  }

  // ── Editor toolbar actions ────────────────────────────────────────────────

  function wrapSelection(textarea, before, after) {
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = textarea.value.substring(start, end) || 'text';
    const replacement = before + selected + after;
    textarea.setRangeText(replacement, start, end, 'select');
    textarea.focus();
    // Fire input event to trigger preview update
    textarea.dispatchEvent(new Event('input'));
  }

  function insertLine(textarea, prefix) {
    const start = textarea.selectionStart;
    const lineStart = textarea.value.lastIndexOf('\n', start - 1) + 1;
    const lineEnd = textarea.value.indexOf('\n', start);
    const end = lineEnd === -1 ? textarea.value.length : lineEnd;
    const currentLine = textarea.value.substring(lineStart, end);
    textarea.setRangeText(prefix + currentLine, lineStart, end, 'end');
    textarea.focus();
    textarea.dispatchEvent(new Event('input'));
  }

  const TOOLBAR_ACTIONS = {
    bold:        (ta) => wrapSelection(ta, '**', '**'),
    italic:      (ta) => wrapSelection(ta, '*', '*'),
    strike:      (ta) => wrapSelection(ta, '~~', '~~'),
    code:        (ta) => wrapSelection(ta, '`', '`'),
    codeblock:   (ta) => wrapSelection(ta, '```\n', '\n```'),
    link:        (ta) => wrapSelection(ta, '[', '](url)'),
    h2:          (ta) => insertLine(ta, '## '),
    h3:          (ta) => insertLine(ta, '### '),
    ul:          (ta) => insertLine(ta, '- '),
    ol:          (ta) => insertLine(ta, '1. '),
    blockquote:  (ta) => insertLine(ta, '> '),
    hr:          (ta) => {
      const pos = ta.selectionEnd;
      ta.setRangeText('\n---\n', pos, pos, 'end');
      ta.dispatchEvent(new Event('input'));
    },
  };

  // ── Main init ────────────────────────────────────────────────────────────

  function init() {
    const form = document.getElementById('wiki-edit-form');
    if (!form) return;

    const titleInput     = document.getElementById('title-input');
    const slugInput      = document.getElementById('slug-input');
    const contentEditor  = document.getElementById('content-editor');
    const previewPane    = document.getElementById('preview-pane');
    const charCount      = document.getElementById('char-count');
    const slugPreview    = document.getElementById('slug-preview');
    const isNewPage      = form.dataset.isNew === 'true';

    let originalContent  = contentEditor ? contentEditor.value : '';
    let isDirty          = false;

    // ── Slug auto-generation ─────────────────────────────────────────────
    if (titleInput && slugInput && isNewPage) {
      titleInput.addEventListener('input', function () {
        const slug = generateSlug(this.value);
        slugInput.value = slug;
        if (slugPreview) slugPreview.textContent = `/wiki/${slug}`;
      });
    }

    if (slugInput && slugPreview) {
      slugInput.addEventListener('input', function () {
        // Sanitize slug while typing
        const safe = generateSlug(this.value.replace(/-/g, ' '));
        if (slugPreview) slugPreview.textContent = `/wiki/${safe || '...'}`;
      });
    }

    // ── Live preview ─────────────────────────────────────────────────────
    if (contentEditor && previewPane) {
      function updatePreview() {
        const md = contentEditor.value;
        if (!md.trim()) {
          previewPane.innerHTML = '<p class="editor-preview-placeholder">Your formatted preview will appear here as you type…</p>';
        } else {
          previewPane.innerHTML = renderMarkdown(md);
        }
        if (charCount) {
          charCount.textContent = `${md.length.toLocaleString()} chars`;
        }
      }

      contentEditor.addEventListener('input', function () {
        updatePreview();
        isDirty = this.value !== originalContent;
      });

      // Initial render
      updatePreview();

      // Tab key inserts spaces instead of navigating away
      contentEditor.addEventListener('keydown', function (e) {
        if (e.key === 'Tab') {
          e.preventDefault();
          const start = this.selectionStart;
          const end = this.selectionEnd;
          this.setRangeText('  ', start, end, 'end');
          this.dispatchEvent(new Event('input'));
        }
      });
    }

    // ── Toolbar ──────────────────────────────────────────────────────────
    const toolbar = document.getElementById('editor-toolbar');
    if (toolbar && contentEditor) {
      toolbar.querySelectorAll('[data-action]').forEach((btn) => {
        btn.addEventListener('click', function (e) {
          e.preventDefault();
          const action = this.dataset.action;
          if (TOOLBAR_ACTIONS[action]) {
            TOOLBAR_ACTIONS[action](contentEditor);
          }
        });
      });
    }

    // ── Unsaved changes guard ─────────────────────────────────────────────
    window.addEventListener('beforeunload', function (e) {
      if (isDirty) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
      }
    });

    // When the form submits, clear the dirty flag so we don't trigger the guard.
    form.addEventListener('submit', function () {
      isDirty = false;
    });

    // ── Keyboard shortcut: Ctrl+S / Cmd+S to save ─────────────────────
    document.addEventListener('keydown', function (e) {
      if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        form.requestSubmit();
      }
    });
  }

  document.addEventListener('DOMContentLoaded', init);
})();
