// =========================================================
// Column filter popup: provides sort controls and text-based
// filtering for a single table column via a modal dialog
// =========================================================

// site/src/ui/table/columnFilterPopup.js

// =========================================================
// Imports
// =========================================================

import { el } from '../common/dom.js';
import { openModal } from '../common/modal.js';

// =========================================================
// Popup entry point
// =========================================================

// ---------- Open a modal popup for sorting and filtering a column ----------
export function openColumnFilterPopup({
  column,
  tableState,
  onApply,
}) {
  // ---------- Root container for popup content ----------
  const wrap = el('div', 'filter-popup');

  // =========================================================
  // Sort controls
  // =========================================================

  // ---------- Row containing sort buttons ----------
  const sortRow = el('div', 'filter-popup__row');
  const sortAsc = el('button', 'btn btn-secondary', 'Sort A → Z');
  const sortDesc = el('button', 'btn btn-secondary', 'Sort Z → A');

  // ---------- Apply ascending sort ----------
  sortAsc.onclick = () => {
    if (tableState.setSort) {
      tableState.setSort(column, 'asc');
    } else {
      tableState.toggleSort(column);
    }
    onApply();
  };

  // ---------- Apply descending sort ----------
  sortDesc.onclick = () => {
    if (tableState.setSort) {
      tableState.setSort(column, 'desc');
    } else {
      tableState.toggleSort(column);
      tableState.toggleSort(column); // force desc
    }
    onApply();
  };

  sortRow.append(sortAsc, sortDesc);

  // =========================================================
  // Filter input
  // =========================================================

  // ---------- Row containing text filter input ----------
  const filterRow = el('div', 'filter-popup__row');
  const input = el('input');
  input.type = 'text';
  input.placeholder = `Filter ${column}`;

  filterRow.appendChild(input);

  // =========================================================
  // Action buttons
  // =========================================================

  // ---------- Row containing apply/clear actions ----------
  const actionRow = el('div', 'filter-popup__row filter-popup__actions');
  const applyBtn = el('button', 'btn btn-primary', 'Apply');
  const clearBtn = el('button', 'btn', 'Clear');

  // ---------- Apply filter value ----------
  applyBtn.onclick = () => {
    tableState.setFilter(column, input.value);
    onApply();
  };

  // ---------- Clear filter value ----------
  clearBtn.onclick = () => {
    tableState.setFilter(column, '');
    onApply();
  };

  actionRow.append(applyBtn, clearBtn);

  // =========================================================
  // Assemble popup content and display modal
  // =========================================================

  wrap.append(sortRow, filterRow, actionRow);

  openModal({
    title: `Filter: ${column}`,
    contentEl: wrap,
  });

  // ---------- Focus input for immediate typing ----------
  input.focus();
}
