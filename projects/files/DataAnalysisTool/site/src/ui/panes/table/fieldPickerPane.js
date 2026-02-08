// =========================================================
// Field picker pane: builds a grouped field dropdown from the
// schema (main/FK/junction options), allows selecting fields
// into an ordered list, and exposes get/set helpers
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el, createCenteredButtonRow } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import {
  isFieldObj,
  isListObj,
  itemKey,
  itemLabel,
  normalizeIncomingInitialSelected,
} from '../../helpers/fieldPickerHelpers.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render a field picker pane for choosing summary/detail fields ----------
export function renderFieldPickerPane({
  cfg,
  mainTable,
  title = 'Pick Fields',
  subtitle = 'Choose fields to include',
  initialSelected = [],
  selectAllMode = 'none', // 'none' | 'main' | 'all'
  allowReorder = false, // show ▲ ▼ buttons (and preserve order)
  showFieldMeta = true,
}) {
  // ---------- Pane shell + body container ----------
  const body = el('div');
  const paneEl = renderPaneShell({ title, bodyEl: body, className: 'pane--field-picker' });

  // ---------- Primary section wrapper ----------
  const section = el('div', 'pane-section');
  section.appendChild(el('div', 'pane-section__title centre-heading', subtitle));

  // ----------------------------------
  // Guards
  // ----------------------------------

  // ---------- Must have a valid main table loaded before building options ----------
  if (!mainTable || !cfg?.tables?.[mainTable]) {
    const msg = el('div', 'empty-state');
    msg.textContent = 'Select a main table first.';
    body.appendChild(msg);
    return {
      paneEl,
      getSelected: () => [],
      setSelected: () => {},
      refresh: () => {},
    };
  }

  // =========================================================
  // Schema extracts used to build options
  // =========================================================

  const tables = cfg.tables || {};
  const tableCfg = tables[mainTable] || {};
  const columns = tableCfg.columns || [];
  const foreignKeys = tableCfg.foreignKeys || [];
  const tableMeta = cfg.tableMeta || {};

  const fkCols = new Set((foreignKeys || []).map(f => f.column));

  // ---------- Pick a friendly label column from a table (meta override, then common names) ----------
  const pickLabelColumn = (tableName, fallbackCol) => {
    const meta = tableMeta?.[tableName] || null;
    if (meta?.labelColumn) return meta.labelColumn;

    const cols = (tables?.[tableName]?.columns || []).map(c => c.name);
    const candidates = ['name', 'title', 'label', 'value', 'document', 'description'];
    const picked = candidates.find(c => cols.includes(c));
    return picked || fallbackCol;
  };

  // ----------------------------------
  // Options
  // ----------------------------------

  // =========================================================
  // Main table options (raw columns)
  // =========================================================

  const mainOptions = columns.map((c) => {
    const isFk = fkCols.has(c.name);
    return {
      value: `${mainTable}.${c.name}`,
      label: `${mainTable}.${c.name}${isFk ? ' (FK id)' : ''}`,
      group: isFk ? `Main FK (raw): ${mainTable}` : `Main: ${mainTable}`,
    };
  });

  // =========================================================
  // FK display options (friendly label column from referenced table)
  // =========================================================

  const fkDisplayOptions = [];
  for (const fk of foreignKeys || []) {
    const refTable = fk.refTable;
    if (!refTable || !tables?.[refTable]) continue;
    const labelCol = pickLabelColumn(refTable, fk.refColumn);
    fkDisplayOptions.push({
      value: `${refTable}.${labelCol}`,
      label: `${mainTable}.${fk.column} → ${refTable}.${labelCol}`,
      group: 'FK display',
      priority: 2,
    });
  }

  // =========================================================
  // Linked table options (outgoing + incoming relations)
  // =========================================================

  const fkOptions = [];
  const mainKey = String(mainTable);

  // ---------- Outgoing FKs: fields from referenced tables ----------
  for (const fk of foreignKeys || []) {
    const refTable = fk.refTable;
    if (!refTable || !tables?.[refTable]) continue;

    const refCols = (tables?.[refTable]?.columns || []).map((c) => c.name);
    for (const refCol of refCols) {
      fkOptions.push({
        value: `${refTable}.${refCol}`,
        label: `${refTable}.${refCol} (via ${mainTable}.${fk.column} → ${refTable}.${fk.refColumn})`,
        group: `Linked: ${refTable}`,
      });
    }
  }

  // ---------- Incoming FKs: fields from tables that point at the main table ----------
  for (const [tname, tcfg] of Object.entries(tables)) {
    if (tname === mainTable) continue;

    const fks = tcfg.foreignKeys || [];
    const incoming = fks.filter((fk) => String(fk.refTable) === mainKey);
    if (!incoming.length) continue;

    const childCols = (tcfg.columns || []).map((c) => c.name);
    for (const fk of incoming) {
      for (const col of childCols) {
        fkOptions.push({
          value: `${tname}.${col}`,
          label: `${tname}.${col} (via ${tname}.${fk.column} → ${mainTable}.${fk.refColumn})`,
          group: `Linked: ${tname}`,
        });
      }
    }
  }

  // =========================================================
  // Junction options (tables marked as junction in meta)
  // =========================================================

  const junctionOptions = [];
  const junctionTables = Object.entries(tableMeta)
    .filter(([, meta]) => meta?.tableType === 'junction')
    .map(([t]) => t);

  // ---------- Build FK edge list for quick relationship checks ----------
  const fkEdges = [];
  for (const [tname, tcfg] of Object.entries(tables)) {
    for (const fk of (tcfg.foreignKeys || [])) {
      fkEdges.push({
        table: tname,
        column: fk.column,
        refTable: fk.refTable,
        refColumn: fk.refColumn,
      });
    }
  }

  // ---------- Find whether there's a FK edge between two tables (either direction) ----------
  const edgeBetween = (a, b) =>
    fkEdges.find(e => e.table === a && e.refTable === b) ||
    fkEdges.find(e => e.table === b && e.refTable === a) ||
    null;

  // ---------- Add junction table fields, and fields reachable via that junction ----------
  for (const jt of junctionTables) {
    if (!tables?.[jt]) continue;
    if (!edgeBetween(jt, mainTable)) continue;

    const jtCols = (tables?.[jt]?.columns || []).map(c => c.name);
    for (const col of jtCols) {
      junctionOptions.push({
        value: `${jt}.${col}`,
        label: `${jt}.${col} (via ${mainTable} ⇄ ${jt})`,
        group: `Junction: ${jt}`,
      });
    }

    const edgesFromJt = fkEdges.filter(e => e.table === jt || e.refTable === jt);
    for (const e of edgesFromJt) {
      const far = e.table === jt ? e.refTable : e.table;
      if (!far || far === mainTable) continue;
      if (!tables?.[far]) continue;

      const farCols = (tables?.[far]?.columns || []).map(c => c.name);
      const farRefCol = e.table === jt ? e.refColumn : e.column;
      const farLabelCol = pickLabelColumn(far, farRefCol);

      // ---------- Prefer a friendly label column if available ----------
      if (farLabelCol) {
        junctionOptions.push({
          value: `${far}.${farLabelCol}`,
          label: `${far}.${farLabelCol} (via ${jt})`,
          group: `Linked via ${jt}: ${far}`,
          priority: 1,
        });
      }

      // ---------- Also allow selecting any column from the far table ----------
      for (const col of farCols) {
        junctionOptions.push({
          value: `${far}.${col}`,
          label: `${far}.${col} (via ${jt})`,
          group: `Linked via ${jt}: ${far}`,
        });
      }
    }
  }

  // =========================================================
  // Merge options by value (keep highest priority label)
  // =========================================================

  const optionMap = new Map();
  for (const o of [...fkDisplayOptions, ...mainOptions, ...fkOptions, ...junctionOptions]) {
    const existing = optionMap.get(o.value);
    const nextPriority = o.priority || 0;
    const existingPriority = existing?.priority || 0;
    if (!existing || nextPriority > existingPriority) optionMap.set(o.value, o);
  }
  const allOptions = Array.from(optionMap.values());

  // =========================================================
  // Group options for <optgroup> rendering
  // =========================================================

  const groups = new Map();
  for (const o of allOptions) {
    const g = o.group || 'Fields';
    if (!groups.has(g)) groups.set(g, []);
    groups.get(g).push(o);
  }

  // ----------------------------------
  // Selected State
  // ----------------------------------

  // ---------- Normalize initial selection into object items (table/column or list) ----------
  let selected = normalizeIncomingInitialSelected(initialSelected, mainTable);

  // ---------- Check whether a candidate item already exists in selection ----------
  const has = (item) => {
    const k = itemKey(item);
    if (!k) return false;
    return selected.some((x) => itemKey(x) === k);
  };

  // ----------------------------------
  // UI
  // ----------------------------------

  const pickerRow = el('div', 'pane-section');

  // ---------- Dropdown for picking a single option ----------
  const optionSelect = el('select', 'form-control');
  optionSelect.innerHTML = '';

  {
    const opt = document.createElement('option');
    opt.value = '';
    opt.textContent = 'Select a field...';
    optionSelect.appendChild(opt);
  }

  // ---------- Build grouped dropdown options ----------
  for (const [gname, opts] of groups.entries()) {
    const og = document.createElement('optgroup');
    og.label = gname;

    for (const o of opts) {
      const opt = document.createElement('option');
      opt.value = o.value;
      opt.textContent = o.label;
      og.appendChild(opt);
    }

    optionSelect.appendChild(og);
  }

  // ---------- Button row (add/select-all/clear) ----------
  const btnRow = createCenteredButtonRow();

  const addBtn = el('button', 'btn btn-success', 'Add Field');
  addBtn.type = 'button';
  btnRow.appendChild(addBtn);

  let selectAllBtn = null;
  let clearBtn = null;

  // ---------- Optional select-all controls ----------
  if (selectAllMode !== 'none') {
    selectAllBtn = el(
      'button',
      'btn btn-primary',
      selectAllMode === 'main' ? 'Select All MAIN' : 'Select ALL'
    );
    selectAllBtn.type = 'button';

    clearBtn = el('button', 'btn btn-secondary', 'Clear');
    clearBtn.type = 'button';

    btnRow.appendChild(selectAllBtn);
    btnRow.appendChild(clearBtn);
  }

  // =========================================================
  // Selected list rendering
  // =========================================================

  const selectedWrap = el('div', 'pane-section');
  selectedWrap.appendChild(el('div', 'pane-section__title centre-heading', 'Selected Fields'));

  const selectedList = el('div', 'fields-list');

  // ---------- Rebuild selected list rows ----------
  const renderSelected = () => {
    selectedList.innerHTML = '';

    if (selected.length === 0) {
      selectedList.appendChild(el('div', 'empty-state', 'No fields selected yet.'));
      return;
    }

    selected.forEach((item, idx) => {
      const classes = ['field-row'];
      if (allowReorder) classes.push('field-row--reorder');
      if (!showFieldMeta) classes.push('field-row--compact');
      const row = el('div', classes.join(' '));

      const labelText = itemLabel(item);

      // ---------- Read-only display of item label ----------
      const name = el('input', 'field-name-input form-control');
      name.type = 'text';
      name.value = labelText;
      name.disabled = true;

      let typeText = null;

      // ---------- Optional MAIN/FK indicator ----------
      if (showFieldMeta) {
        const isMain = isFieldObj(item) && item.table === mainTable;
        typeText = el('span', 'field-type', isMain ? 'MAIN' : 'FK');
      }

      let upBtn = null;
      let downBtn = null;

      // ---------- Optional reorder controls ----------
      if (allowReorder) {
        upBtn = el('button', 'btn btn-secondary btn--icon reorder-btn', '▲');
        upBtn.type = 'button';
        upBtn.disabled = idx === 0;
        upBtn.addEventListener('click', () => {
          if (idx <= 0) return;
          const tmp = selected[idx - 1];
          selected[idx - 1] = selected[idx];
          selected[idx] = tmp;
          renderSelected();
        });

        downBtn = el('button', 'btn btn-secondary btn--icon reorder-btn', '▼');
        downBtn.type = 'button';
        downBtn.disabled = idx === selected.length - 1;
        downBtn.addEventListener('click', () => {
          if (idx >= selected.length - 1) return;
          const tmp = selected[idx + 1];
          selected[idx + 1] = selected[idx];
          selected[idx] = tmp;
          renderSelected();
        });
      }

      // ---------- Remove item from selection ----------
      const removeBtn = el('button', 'btn btn-danger', 'Remove');
      removeBtn.type = 'button';
      removeBtn.addEventListener('click', () => {
        const k = itemKey(item);
        selected = selected.filter((x) => itemKey(x) !== k);
        renderSelected();
      });

      row.appendChild(name);
      if (typeText) row.appendChild(typeText);
      if (allowReorder) row.appendChild(upBtn);
      if (allowReorder) row.appendChild(downBtn);
      row.appendChild(removeBtn);

      selectedList.appendChild(row);
    });
  };

  // =========================================================
  // Selection parsing and actions
  // =========================================================

  // ---------- Convert "table.column" strings into {table, column} items ----------
  const parsePickedToItem = (picked) => {
    const s = String(picked || '').trim();
    if (!s) return null;

    // NOTE: no LIST: strings accepted anymore, unless you later add list UI.
    const i = s.indexOf('.');
    if (i < 0) return null;

    const table = s.slice(0, i).trim();
    const column = s.slice(i + 1).trim();
    if (!table || !column) return null;

    return { table, column };
  };

  // ---------- Add a single picked field to selection ----------
  addBtn.addEventListener('click', () => {
    const picked = optionSelect.value;
    const item = parsePickedToItem(picked);
    if (!item) return;

    if (!has(item)) selected.push(item);

    optionSelect.value = '';
    renderSelected();
  });

  // ---------- Select all (main or all) / clear ----------
  if (selectAllMode !== 'none') {
    selectAllBtn.addEventListener('click', () => {
      const src = selectAllMode === 'main' ? mainOptions : allOptions;

      for (const o of src) {
        const item = parsePickedToItem(o.value);
        if (!item) continue;
        if (!has(item)) selected.push(item);
      }

      renderSelected();
    });

    clearBtn.addEventListener('click', () => {
      selected = [];
      renderSelected();
    });
  }

  // ---------- Assemble picker controls ----------
  pickerRow.appendChild(optionSelect);
  pickerRow.appendChild(btnRow);

  section.appendChild(pickerRow);
  selectedWrap.appendChild(selectedList);

  body.appendChild(section);
  body.appendChild(selectedWrap);

  // ---------- Initial selected list render ----------
  renderSelected();

  // ----------------------------------
  // Public API
  // ----------------------------------

  // ---------- Return selected items as shallow copies ----------
  const getSelected = () => selected.map((x) => ({ ...x })); // return copies

  // ---------- Replace selection and rerender ----------
  const setSelected = (list) => {
    selected = normalizeIncomingInitialSelected(list, mainTable);
    renderSelected();
  };

  // ---------- No-op placeholder (kept for interface consistency) ----------
  const refresh = () => {
    // No-op by design.
  };

  return { paneEl, getSelected, setSelected, refresh };
}
