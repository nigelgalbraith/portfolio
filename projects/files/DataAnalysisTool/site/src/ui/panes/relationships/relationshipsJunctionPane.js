// =========================================================
// Relationships (N:M / M:N) pane: lists existing junction-table
// relationships and provides a form to create a new junction
// table linking two PK-backed tables with FK rule controls
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { junctionsApi } from '../../../api/junctions.js';
import {
  buildRuleSelect,
  buildSelect,
  defaultJunctionName,
  tableOptions,
} from '../../helpers/relationshipsHelpers.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render a pane for managing junction relationships (N:M or M:N) ----------
export function renderRelationshipsJunctionPane({ cfg, getSelectedDb, onChanged, mode = 'N:M' }) {
  // =========================================================
  // Local UI state for the "Add junction relationship" form
  // =========================================================
  const state = {
    message: '',
    error: '',

    leftTable: '',
    rightTable: '',
    junctionTable: '',

    onDeleteA: 'RESTRICT',
    onUpdateA: 'RESTRICT',
    onDeleteB: 'RESTRICT',
    onUpdateB: 'RESTRICT',
  };

  // =========================================================
  // Mode normalization + labels (M:N is a UI mirror of N:M)
  // =========================================================
  const normalizedMode = mode === 'M:N' ? 'M:N' : 'N:M';
  const swapSides = normalizedMode === 'M:N';

  // ---------- Map displayed left/right to canonical ordering when needed ----------
  const orderTables = (left, right) => (swapSides ? [right, left] : [left, right]);

  // ---------- UI labels depend on whether sides are swapped ----------
  const leftLabel = swapSides ? 'Right table (has PK)' : 'Left table (has PK)';
  const rightLabel = swapSides ? 'Left table (has PK)' : 'Right table (has PK)';
  const leftFkLabel = swapSides ? 'Right FK: ON DELETE' : 'Left FK: ON DELETE';
  const leftFkUpdLabel = swapSides ? 'Right FK: ON UPDATE' : 'Left FK: ON UPDATE';
  const rightFkLabel = swapSides ? 'Left FK: ON DELETE' : 'Right FK: ON DELETE';
  const rightFkUpdLabel = swapSides ? 'Left FK: ON UPDATE' : 'Right FK: ON UPDATE';

  // ---------- Pane shell + body container ----------
  const bodyEl = el('div');
  const paneEl = renderPaneShell({
    title: `Relationships (${normalizedMode})`,
    bodyEl,
  });

  // ---------- Resolve currently selected DB once for this pane instance ----------
  const db = typeof getSelectedDb === 'function' ? getSelectedDb() : '';

  // =========================================================
  // Render function: rebuilds the pane body from cfg + state
  // =========================================================
  const render = () => {
    bodyEl.innerHTML = '';

    // ---------- Context header ----------
    bodyEl.appendChild(
      el('div', 'help centre-heading', `DB: ${db || ''} | Junction tables`)
    );

    // =========================================================
    // Existing junction relationships
    // =========================================================
    bodyEl.appendChild(
      el(
        'div',
        'pane-section__title centre-heading',
        `Existing junction relationships (${normalizedMode})`
      )
    );

    const list = el('div', 'fields-list');
    let hasAny = false;

    // ---------- List tables marked as junction in meta and show their two FKs ----------
    Object.entries(cfg.tables || {}).forEach(([jtName, jt]) => {
      const meta = cfg.tableMeta?.[jtName];
      if (!meta || meta.tableType !== 'junction') return;

      const fks = jt.foreignKeys || [];
      if (fks.length !== 2) return;

      hasAny = true;

      const row = el('div', 'relationship-item-row');

      // ---------- Display relationship using mode-aware ordering ----------
      const [fkA, fkB] = orderTables(fks[0], fks[1]);

      const left = el('div', 'relationship-item-box mono');
      left.appendChild(el('div', '', fkA.refTable));
      left.appendChild(el('div', 'arrow-line', `⇄ via ${jtName}`));
      left.appendChild(el('div', '', fkB.refTable));

      const rules = el('div', 'relationship-item-box');
      rules.appendChild(el('div', '', `DEL ${fkA.onDelete} / UPD ${fkA.onUpdate}`));
      rules.appendChild(el('div', 'spacer-line', ''));
      rules.appendChild(el('div', '', `DEL ${fkB.onDelete} / UPD ${fkB.onUpdate}`));

      // NOTE: remove is intentionally “delete table” and will be blocked by backend right now.
      // You said that’s fine for now.
      const removeBtn = el('button', 'btn btn-danger', 'Remove');
      removeBtn.onclick = async () => {
        state.message = '';
        state.error = '';

        if (!db) return;
        if (!confirm(`Delete junction table?\n\n${jtName}`)) return;

        try {
          await junctionsApi.remove(db, jtName);
          state.message = `Deleted table: ${jtName}`;
          onChanged?.();
        } catch (e) {
          console.error(e);
          state.error = 'Delete blocked by backend guards (expected right now).';
          render();
        }
      };

      row.append(left, rules, removeBtn);
      list.appendChild(row);
    });

    // ---------- Empty-state when no junction relationships exist ----------
    if (!hasAny) list.appendChild(el('div', 'empty-state', 'No junction relationships.'));
    bodyEl.appendChild(list);

    // =========================================================
    // Add junction relationship (N:M / M:N)
    // =========================================================
    bodyEl.appendChild(
      el(
        'div',
        'pane-section__title centre-heading',
        `Add junction relationship (${normalizedMode})`
      )
    );

    const form = el('div');

    // ---------- Only allow tables with PKs to participate in junction creation ----------
    const pkTables = tableOptions(cfg, { requirePk: true });

    // ---------- Left table selector ----------
    form.appendChild(el('div', 'help', leftLabel));
    const leftSel = buildSelect(pkTables, state.leftTable);
    leftSel.onchange = () => {
      state.leftTable = leftSel.value;
      const [leftTable, rightTable] = orderTables(state.leftTable, state.rightTable);
      state.junctionTable = defaultJunctionName(leftTable, rightTable);
      render();
    };
    form.appendChild(leftSel);

    // ---------- Right table selector ----------
    form.appendChild(el('div', 'help', rightLabel));
    const rightSel = buildSelect(pkTables, state.rightTable);
    rightSel.onchange = () => {
      state.rightTable = rightSel.value;
      const [leftTable, rightTable] = orderTables(state.leftTable, state.rightTable);
      state.junctionTable = defaultJunctionName(leftTable, rightTable);
      render();
    };
    form.appendChild(rightSel);

    // ---------- Junction table name input ----------
    form.appendChild(el('div', 'help', 'Junction table name'));
    const jtInp = document.createElement('input');
    jtInp.type = 'text';
    jtInp.className = 'form-control';
    jtInp.value = state.junctionTable;
    jtInp.oninput = () => (state.junctionTable = jtInp.value);
    form.appendChild(jtInp);

    // ---------- FK rules for side A ----------
    form.appendChild(el('div', 'help', leftFkLabel));
    const delA = buildRuleSelect(state.onDeleteA);
    delA.onchange = () => (state.onDeleteA = delA.value);
    form.appendChild(delA);

    form.appendChild(el('div', 'help', leftFkUpdLabel));
    const updA = buildRuleSelect(state.onUpdateA);
    updA.onchange = () => (state.onUpdateA = updA.value);
    form.appendChild(updA);

    // ---------- FK rules for side B ----------
    form.appendChild(el('div', 'help', rightFkLabel));
    const delB = buildRuleSelect(state.onDeleteB);
    delB.onchange = () => (state.onDeleteB = delB.value);
    form.appendChild(delB);

    form.appendChild(el('div', 'help', rightFkUpdLabel));
    const updB = buildRuleSelect(state.onUpdateB);
    updB.onchange = () => (state.onUpdateB = updB.value);
    form.appendChild(updB);

    // =========================================================
    // Create junction action
    // =========================================================

    // ---------- Add relationship button ----------
    const addBtn = el('button', 'btn btn-primary', 'Add Relationship');
    addBtn.type = 'button';
    addBtn.onclick = async () => {
      state.message = '';
      state.error = '';

      // ---------- Guard: DB must be selected ----------
      if (!db) {
        state.error = 'No database selected.';
        render();
        return;
      }

      // ---------- Canonicalize tables based on mode (swap for M:N) ----------
      const [leftTable, rightTable] = orderTables(
        (state.leftTable || '').trim(),
        (state.rightTable || '').trim()
      );
      const junctionTable = (state.junctionTable || '').trim();

      // ---------- Guard: required selections ----------
      if (!leftTable || !rightTable || !junctionTable) {
        state.error = 'Select left table, right table, and enter a junction table name.';
        render();
        return;
      }

      // ---------- Guard: both tables must have PKs ----------
      const leftPk = cfg.tables?.[leftTable]?.primaryKey?.[0];
      const rightPk = cfg.tables?.[rightTable]?.primaryKey?.[0];
      if (!leftPk || !rightPk) {
        state.error = 'Both tables must have a primary key.';
        render();
        return;
      }

      // Column naming rule (simple and consistent)
      const leftCol = `${leftTable}_id`;
      const rightCol = `${rightTable}_id`;

      try {
        await junctionsApi.create(db, {
          table: junctionTable,
          leftTable,
          rightTable,
          leftPk,
          rightPk,
          leftCol,
          rightCol,
          onDeleteA: state.onDeleteA,
          onUpdateA: state.onUpdateA,
          onDeleteB: state.onDeleteB,
          onUpdateB: state.onUpdateB,
        });

        state.message = `Added Relationship: ${leftTable} ⇄ ${rightTable} (via ${junctionTable})`;
        onChanged?.();
      } catch (e) {
        console.error(e);
        state.error = 'Failed to create junction relationship.';
        render();
      }
    };

    // ---------- Centered button row ----------
    const btnRow = el('div', 'center-buttons');
    btnRow.appendChild(addBtn);
    form.appendChild(btnRow);

    bodyEl.appendChild(form);

    // =========================================================
    // Status messages
    // =========================================================

    if (state.message) bodyEl.appendChild(el('div', 'help centre-heading', state.message));
    if (state.error) {
      const err = el('div', 'help centre-heading');
      err.dataset.kind = 'error';
      err.textContent = state.error;
      bodyEl.appendChild(err);
    }
  };

  // =========================================================
  // Initial render
  // =========================================================

  render();
  return { paneEl };
}
