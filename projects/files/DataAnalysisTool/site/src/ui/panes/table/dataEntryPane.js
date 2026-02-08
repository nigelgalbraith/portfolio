// =========================================================
// Data entry pane: renders a record editor form from table
// schema + state, including FK dropdowns, distinct-value
// datalists, optional junction multiselects, and CRUD actions
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import {
  fillDatalist,
  fillFkSelect,
  fillMultiSelect,
  normalizeValueForInput,
} from '../../helpers/dataEntryHelpers.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render a record editor pane for creating/updating/deleting rows ----------
export function renderDataEntryPane({
  state,

  getFkForColumn,
  ensureFkOptions,
  ensureDistinctForColumn,
  ensureJunctionOptions,
  junctionRelations = [],

  onNewRecord,
  onSave,
  onDelete,

  title = 'Record Editor',
}) {
  // ---------- Pane shell + body container ----------
  const body = el('div');
  const paneEl = renderPaneShell({ title, bodyEl: body, className: 'pane--data-entry' });

  // =========================================================
  // Header / context
  // =========================================================

  body.appendChild(
    el(
      'div',
      'help centre-heading',
      `DB: ${state.db || ''}  |  Table: ${state.table || ''}  |  Mode: ${state.mode}`
    )
  );

  // ---------- Warn when table has no PK (safe edit/delete not available) ----------
  if (!state.pkCols?.length) {
    body.appendChild(
      el(
        'div',
        'help',
        `Note: This table has no primary key. You can insert records, but safe edit/delete by record isn't available.`
      )
    );
  }

  // =========================================================
  // Main form grid (columns)
  // =========================================================

  const grid = el('div', 'details-grid');

  // Prefer rich schema data if available (identity, required, editability).
  const schemaByName = new Map(
    (state.tableSchema?.columns || []).map(c => [c.name, c])
  );

  // ---------- Render one input per column ----------
  for (const c of (state.columns || [])) {
    const colName = c.name;
    const meta = schemaByName.get(colName) || null;
    const isIdentity = meta ? !!meta.isIdentity : false;
    const isPk = meta ? !!meta.isPrimaryKey : (state.pkCols || []).includes(colName);

    // ---------- Editability rules come from schema (fallbacks keep current behavior) ----------
    const editableOnCreate = meta ? !!meta.editableOnCreate : true;
    const editableOnUpdate = meta ? !!meta.editableOnUpdate : !isPk;

    // ---------- Skip identity columns during insert (backend auto-assigns) ----------
    if (isIdentity && state.mode === 'new') {
      continue;
    }

    // ---------- Label cell with PK/auto tags ----------
    const label = el(
      'div',
      'details-grid__k mono',
      colName +
        (isPk ? ' (PK)' : '') +
        (isIdentity ? ' (auto)' : '')
    );

    // ---------- Value cell wrapper ----------
    const wrap = el('div', 'details-grid__v');
    const fk = typeof getFkForColumn === 'function' ? getFkForColumn(colName) : null;

    let inputEl;

    // =========================================================
    // FK column: render as <select> populated from lookup cache
    // =========================================================
    if (fk) {
      const sel = document.createElement('select');
      sel.className = 'form-control';
      sel.value = normalizeValueForInput(state.values[colName]);

      // ---------- Default "blank" option ----------
      const opt0 = document.createElement('option');
      opt0.value = '';
      opt0.textContent = '— select —';
      sel.appendChild(opt0);

      // ---------- Populate from cached FK options ----------
      const key = `${fk.column}::${fk.refTable}::${fk.refColumn}`;
      const rows = state.fkOptions?.get?.(key) || [];
      fillFkSelect(sel, rows);

      // ---------- Lazy-load options on focus ----------
      sel.addEventListener('focus', async () => {
        if (!ensureFkOptions) return;
        await ensureFkOptions(fk);
        fillFkSelect(sel, state.fkOptions?.get?.(key) || []);
      });

      // ---------- Write selection back into state.values ----------
      sel.addEventListener('change', () => {
        state.values[colName] = sel.value === '' ? null : sel.value;
      });

      inputEl = sel;
      wrap.appendChild(sel);
      wrap.appendChild(el('div', 'help', `FK → ${fk.refTable}.${fk.refColumn}`));
    } else {
      // =========================================================
      // Normal column: text input with distinct-value <datalist>
      // =========================================================
      const inp = document.createElement('input');
      inp.type = 'text';
      inp.className = 'form-control';
      inp.value = normalizeValueForInput(state.values[colName]);

      // ---------- Attach datalist for distinct suggestions ----------
      const dlId = `dl_${state.table}_${colName}`;
      inp.setAttribute('list', dlId);

      const dl = document.createElement('datalist');
      dl.id = dlId;

      // ---------- Seed suggestions from cache if available ----------
      const cached = state.distinctCache?.get?.(colName) || [];
      if (cached.length) fillDatalist(dl, cached);

      // ---------- Lazy-load distinct values on focus ----------
      inp.addEventListener('focus', async () => {
        if (!ensureDistinctForColumn) return;
        await ensureDistinctForColumn(colName);
        fillDatalist(dl, state.distinctCache?.get?.(colName) || []);
      });

      // ---------- Write input back into state.values ----------
      inp.addEventListener('input', () => {
        state.values[colName] = inp.value === '' ? null : inp.value;
      });

      inputEl = inp;
      wrap.appendChild(inp);
      wrap.appendChild(dl);
    }

    // =========================================================
    // Schema-driven editability and identity handling
    // =========================================================

    // Editability comes from schema rules.
    if (state.mode === 'new' && !editableOnCreate) inputEl.disabled = true;
    if (state.mode === 'edit' && !editableOnUpdate) inputEl.disabled = true;

    // If identity, show it as read-only auto value.
    if (isIdentity) {
      inputEl.disabled = true;
      inputEl.value = normalizeValueForInput(state.values[colName] ?? 'auto');
    }

    grid.appendChild(label);
    grid.appendChild(wrap);
  }

  body.appendChild(grid);

  // =========================================================
  // Junction relationships (many-to-many selection)
  // =========================================================

  if (junctionRelations.length) {
    const related = el('div', 'pane-section');
    related.appendChild(el('div', 'pane-section__title centre-heading', 'Related'));

    // ---------- One multiselect per junction relation ----------
    for (const rel of junctionRelations) {
      const row = el('div', 'details-grid');
      const label = el(
        'div',
        'details-grid__k mono',
        `${rel.farTable} (via ${rel.junctionTable})`
      );

      const wrap = el('div', 'details-grid__v');
      const sel = document.createElement('select');
      sel.className = 'form-control';
      sel.multiple = true;
      sel.size = 6;

      // ---------- Populate from cached options + current selections ----------
      const selected = state.junctionSelections?.get?.(rel.key) || [];
      const rows = state.junctionOptions?.get?.(rel.key) || [];
      fillMultiSelect(sel, rows, selected);

      // ---------- Lazy-load options on focus ----------
      sel.addEventListener('focus', async () => {
        if (!ensureJunctionOptions) return;
        await ensureJunctionOptions(rel);
        fillMultiSelect(
          sel,
          state.junctionOptions?.get?.(rel.key) || [],
          state.junctionSelections?.get?.(rel.key) || []
        );
      });

      // ---------- Write selection list back into state map ----------
      sel.addEventListener('change', () => {
        const vals = Array.from(sel.selectedOptions)
          .map(o => o.value)
          .filter(v => v !== '');
        state.junctionSelections?.set?.(rel.key, vals);
      });

      // ---------- Wrap multiselect for styling ----------
      const multiWrap = el('div', 'multiselect-wrap');
      multiWrap.appendChild(sel);
      wrap.appendChild(multiWrap);
      wrap.appendChild(
        el(
          'div',
          'help',
          `Junction: ${rel.junctionTable} (${rel.mainFkColumn} ↔ ${rel.farFkColumn})`
        )
      );

      row.appendChild(label);
      row.appendChild(wrap);
      related.appendChild(row);
    }

    body.appendChild(related);
  }

  // =========================================================
  // Action buttons (new/save/delete)
  // =========================================================

  const btnRow = el('div', 'center-buttons');

  // ---------- Reset into "new record" mode ----------
  const newBtn = el('button', 'btn', 'New Record');
  newBtn.type = 'button';
  newBtn.addEventListener('click', () => onNewRecord?.());
  btnRow.appendChild(newBtn);

  // ---------- Save/insert action ----------
  const saveBtn = el(
    'button',
    'btn btn-primary',
    state.mode === 'edit' ? 'Save Changes' : 'Insert Record'
  );
  saveBtn.type = 'button';
  saveBtn.disabled = !!state.loading;
  saveBtn.addEventListener('click', () => onSave?.());
  btnRow.appendChild(saveBtn);

  // ---------- Delete action (only enabled when editing a PK-backed record) ----------
  const delBtn = el('button', 'btn btn-danger', 'Delete');
  delBtn.type = 'button';
  delBtn.disabled = !!state.loading || state.mode !== 'edit' || !(state.pkCols || []).length;
  delBtn.addEventListener('click', () => onDelete?.());
  btnRow.appendChild(delBtn);

  body.appendChild(btnRow);

  // =========================================================
  // Status messages
  // =========================================================

  if (state.message) body.appendChild(el('div', 'help centre-heading', state.message));
  if (state.error) {
    const err = el('div', 'help centre-heading');
    err.dataset.kind = 'error';
    err.textContent = state.error;
    body.appendChild(err);
  }

  return { paneEl };
}
