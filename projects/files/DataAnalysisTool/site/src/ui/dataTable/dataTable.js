// =========================================================
// Data table renderer: builds an HTML table from row data with
// configurable summary columns, optional details modal, optional
// per-row actions, and optional header filter triggers
// =========================================================

// site/src/ui/table/dataTable.js

// =========================================================
// Imports
// =========================================================

import { el } from '../common/dom.js';
import { openModal } from '../common/modal.js';
import { renderValueCell } from '../common/renderValue.js';

// =========================================================
// Column definition normalization
// =========================================================

// ---------- Normalize a column definition into { key, label } ----------
function toColDef(c) {
  // Accept: "colKey" OR { key, label }
  if (typeof c === 'string') return { key: c, label: c };
  if (c && typeof c === 'object') {
    const key = String(c.key || '');
    const label = String(c.label || key);
    return { key, label };
  }
  return { key: String(c), label: String(c) };
}

// =========================================================
// Details modal content builder
// =========================================================

// ---------- Build modal content grid for detail fields of a row ----------
function renderDetailsContent(row, detailCols) {
  const wrap = el('div', 'details-grid');

  // ---------- Normalize detail column definitions ----------
  const cols = Array.isArray(detailCols) ? detailCols.map(toColDef) : [];
  if (!cols.length) {
    wrap.appendChild(el('div', 'help', 'No detail fields configured.'));
    return wrap;
  }

  // ---------- Render key/value grid for each detail field ----------
  for (const col of cols) {
    const k = el('div', 'details-grid__k mono', col.label);
    const v = el('div', 'details-grid__v');
    v.appendChild(renderValueCell(row?.[col.key]));
    wrap.appendChild(k);
    wrap.appendChild(v);
  }

  return wrap;
}

// =========================================================
// Main table renderer
// =========================================================

// ---------- Render a data table with optional details/actions/filtering ----------
export function renderTable({
  rows,
  summaryFields,
  detailFields,
  showDetails = true,
  detailsTitle,
  rowActions,
  onHeaderClick,
  filterRowEl
}) {
  // ---------- Outer wrapper for styling/scroll behavior ----------
  const tableWrap = el('div', 'data-table-wrap');
  const table = el('table', 'data-table');

  // ---------- Normalize summary column definitions ----------
  const cols = Array.isArray(summaryFields) ? summaryFields.map(toColDef) : [];

  // =========================================================
  // Table header
  // =========================================================

  const thead = document.createElement('thead');
  const headRow = document.createElement('tr');

  // ---------- Render header cells for each summary column ----------
  for (const col of cols) {
    const th = document.createElement('th');
    const label = el('span', 'table-col-label', col.label);
    th.appendChild(label);

    // ---------- Optional filter/sort trigger button in the header ----------
    if (typeof onHeaderClick === 'function') {
      const filterBtn = el('button', 'table-filter-btn', '▼');
      filterBtn.type = 'button';
      filterBtn.addEventListener('click', (ev) => {
        ev.stopPropagation();
        onHeaderClick(col.key); // IMPORTANT: filter by key, not label
      });
      th.appendChild(filterBtn);
    }

    headRow.appendChild(th);
  }

  // ---------- Optional "Details" column header ----------
  if (showDetails) {
    const thDetails = document.createElement('th');
    thDetails.textContent = 'Details';
    headRow.appendChild(thDetails);
  }

  // ---------- Optional "Actions" column header ----------
  const hasActions = typeof rowActions === 'function';
  if (hasActions) {
    const thA = document.createElement('th');
    thA.textContent = 'Actions';
    headRow.appendChild(thA);
  }

  // ---------- Assemble thead (optional filter row is caller-provided) ----------
  thead.appendChild(headRow);
  if (filterRowEl) thead.appendChild(filterRowEl);
  table.appendChild(thead);

  // =========================================================
  // Table body
  // =========================================================

  const tbody = document.createElement('tbody');

  // ---------- Render each row as a table row ----------
  (rows || []).forEach((row, idx) => {
    const tr = document.createElement('tr');

    // ---------- Render each summary column cell ----------
    for (const col of cols) {
      const td = document.createElement('td');
      td.appendChild(renderValueCell(row?.[col.key]));
      tr.appendChild(td);
    }

    // ---------- Optional details button opens a modal with detail fields ----------
    if (showDetails) {
      const tdBtn = document.createElement('td');
      const btn = el('button', 'btn btn-primary', 'Details');
      btn.type = 'button';

      btn.addEventListener('click', () => {
        openModal({
          title: detailsTitle ? detailsTitle(row, idx) : `Row ${idx + 1} Details`,
          contentEl: renderDetailsContent(row, detailFields),
        });
      });

      tdBtn.appendChild(btn);
      tr.appendChild(tdBtn);
    }

    // ---------- Optional row actions render as buttons in an "Actions" column ----------
    if (hasActions) {
      const tdA = document.createElement('td');
      const actions = rowActions(row, idx) || [];
      for (const a of actions) {
        const btn = el('button', a.className || 'btn btn-primary', a.label || 'Action');
        btn.type = 'button';
        if (a.disabled) btn.disabled = true;
        btn.addEventListener('click', (ev) => {
          ev.stopPropagation();
          try { a.onClick && a.onClick(row, idx); } catch (_) {}
        });
        tdA.appendChild(btn);
      }
      tr.appendChild(tdA);
    }

    tbody.appendChild(tr);
  });

  // =========================================================
  // Assemble and return
  // =========================================================

  table.appendChild(tbody);
  tableWrap.appendChild(table);
  return tableWrap;
}
