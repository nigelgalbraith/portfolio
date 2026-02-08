// =========================================================
// Select Main Table pane: lists tables from the loaded schema,
// lets the user choose an anchor table for summary/detail views,
// and notifies the parent when the selection changes
// =========================================================

// ==================================================
// Imports
// ==================================================
import { el } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';

// ==================================================
// Pane Rendering
// ==================================================
export function renderSelectMainTablePane({
  cfg,
  currentTable = '',
  onTableChange,
  title = 'Select Main Table',
}) {
  // ---------- Pane body wrapper ----------
  const bodyEl = el('div');

  // ---------- Section container ----------
  const section = el('div', 'pane-section');

  section.appendChild(el('div', 'pane-section__title centre-heading', 'Main Table'));

  // ---------- Table selector control ----------
  const tableSelectEl = el('select', 'form-control');

  const tables = Object.keys(cfg?.tables || {});
  tableSelectEl.innerHTML = '';

  // =========================================================
  // Populate options
  // =========================================================

  // ---------- Empty state when no tables exist ----------
  if (tables.length === 0) {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'No tables found';
    tableSelectEl.appendChild(opt);
    tableSelectEl.disabled = true;
  } else {
    // ---------- Placeholder option ----------
    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = 'Select a table...';
    tableSelectEl.appendChild(placeholder);

    // ---------- Add table name options ----------
    for (const t of tables) {
      const opt = document.createElement('option');
      opt.value = t;
      opt.textContent = t;
      tableSelectEl.appendChild(opt);
    }

    // ---------- Restore current selection when valid ----------
    if (currentTable && tables.includes(currentTable)) {
      tableSelectEl.value = currentTable;
    }
  }

  // ---------- Help text describing purpose ----------
  const help = el('div', 'help small centre-heading');
  help.textContent = 'This table is the anchor for the summary and detail views.';

  section.appendChild(tableSelectEl);
  section.appendChild(help);

  bodyEl.appendChild(section);

  // =========================================================
  // Events
  // =========================================================

  // ---------- Notify parent when a valid table is chosen ----------
  tableSelectEl.addEventListener('change', () => {
    const picked = (tableSelectEl.value || '').trim();
    if (!picked) return;
    if (typeof onTableChange === 'function') onTableChange(picked);
  });

  // ---------- Wrap in shared pane shell ----------
  const paneEl = renderPaneShell({
    title,
    bodyEl,
    className: 'pane--select-main-table',
  });

  return { paneEl, tableSelectEl };
}
