// =========================================================
// Value cell renderer for data tables: displays scalars,
// arrays, or links with appropriate formatting
// =========================================================

import { el } from './dom.js';

// =========================================================
// Link detection helper
// =========================================================

// ---------- Determine whether a value should be treated as a link ----------
function looksLikeLink(v) {
  if (v == null) return false;
  const s = String(v).trim();
  if (!s) return false;

  // ---------- Absolute URLs ----------
  if (/^https?:\/\//i.test(s)) return true;

  // ---------- App-internal or root-relative links ----------
  if (s.startsWith('#/') || s.startsWith('/')) return true;

  return false;
}

// =========================================================
// Cell renderer
// =========================================================

// ---------- Render a table cell value as text or a link ----------
export function renderValueCell(value) {

  // ---------- Handle array values by joining entries with line breaks ----------
  if (Array.isArray(value)) {
    const text = value
      .map(v => (v == null ? '' : String(v)))
      .join('\n');

    return document.createTextNode(text);
  }

  // ---------- Normalize scalar value to trimmed string ----------
  const s = value == null ? '' : String(value).trim();

  // ---------- Render plain text when value is not a link ----------
  if (!looksLikeLink(s)) {
    return document.createTextNode(s);
  }

  // ---------- Render link for URL-like values ----------
  const a = el('a', 'link-view', 'View');
  a.href = s;

  // ---------- Open external links in a new tab with safe rel attributes ----------
  if (/^https?:\/\//i.test(s)) {
    a.target = '_blank';
    a.rel = 'noopener noreferrer';
  }

  return a;
}
