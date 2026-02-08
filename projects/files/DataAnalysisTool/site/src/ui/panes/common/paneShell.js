// =========================================================
// Pane shell renderer: provides a consistent container with
// a centered header/title and a body area for arbitrary content
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el } from '../../common/dom.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render a pane wrapper with optional width and extra classes ----------
export function renderPaneShell({ title, bodyEl, wide = false, className = '' }) {
  // ---------- Determine base pane classes ----------
  const base = wide ? 'pane pane--wide' : 'pane';
  const extra = (className || '').trim();
  const pane = el('div', extra ? `${base} ${extra}` : base);

  // =========================================================
  // Pane header
  // =========================================================

  const header = el('div', 'pane__header pane__header--center');
  header.appendChild(el('div', 'pane__title pane__title--center', title));

  // =========================================================
  // Pane body
  // =========================================================

  const body = el('div', 'pane__body');
  body.appendChild(bodyEl);

  // ---------- Assemble pane ----------
  pane.appendChild(header);
  pane.appendChild(body);
  return pane;
}
