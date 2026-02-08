// =========================================================
// Select Database pane: renders a database dropdown wrapped in
// a standard pane shell and emits selection changes to caller
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render pane containing a database selector dropdown ----------
export function renderSelectDatabasePane({
  databases = [],
  currentDb = '',
  placeholder = 'Select database…',
  onDbChange,
}) {
  // ---------- Root body element for pane content ----------
  const bodyEl = el('div');

  // ---------- Database <select> control ----------
  const select = el('select', 'form-control');

  // ---------- Placeholder option (shown when no DB selected) ----------
  const placeholderOpt = document.createElement('option');
  placeholderOpt.value = '';
  placeholderOpt.textContent = placeholder;
  placeholderOpt.disabled = true;
  placeholderOpt.selected = !currentDb;
  select.appendChild(placeholderOpt);

  // ---------- Populate options and preselect currentDb ----------
  for (const db of databases) {
    const opt = document.createElement('option');
    opt.value = db.id;
    opt.textContent = db.label;
    if (db.id === currentDb) opt.selected = true;
    select.appendChild(opt);
  }

  // ---------- Notify caller when selection changes ----------
  select.addEventListener('change', () => {
    const val = select.value;
    if (val) onDbChange?.(val);
  });

  bodyEl.appendChild(select);

  // =========================================================
  // Pane shell assembly
  // =========================================================

  const paneEl = renderPaneShell({
    title: 'Database',
    bodyEl,
    className: 'pane--select-database',
  });

  // ---------- Expose pane element and select for external use ----------
  return { paneEl, dbSelectEl: select };
}
