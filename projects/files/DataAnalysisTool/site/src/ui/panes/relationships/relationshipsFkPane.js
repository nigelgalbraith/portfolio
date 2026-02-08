// =========================================================
// Relationships (1:N) pane: shows existing foreign-key links,
// allows removing them, and provides a form to add a new FK
// relationship with ON DELETE / ON UPDATE rules
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { foreignKeysApi } from '../../../api/foreignKeys.js';
import {
  buildRuleSelect,
  buildSelect,
  countRelationships,
  resolveFkConstraintName,
  tableOptions,
} from '../../helpers/relationshipsHelpers.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render a pane for managing 1:N (foreign key) relationships ----------
export function renderRelationshipsFkPane({ cfg, getSelectedDb, onChanged }) {
  // =========================================================
  // Local UI state for the "Add relationship" form
  // =========================================================
  const state = {
    parentTable: '',
    childTable: '',
    fkColumn: '',
    onDelete: 'RESTRICT',
    onUpdate: 'RESTRICT',
    message: '',
    error: '',
  };

  // ---------- Pane shell + body container ----------
  const bodyEl = el('div');
  const paneEl = renderPaneShell({
    title: 'Relationships (1:N)',
    bodyEl,
  });

  // ---------- Resolve currently selected DB once for this pane instance ----------
  const db = typeof getSelectedDb === 'function' ? getSelectedDb() : '';

  // =========================================================
  // Render function: rebuilds the pane body from cfg + state
  // =========================================================
  const render = () => {
    bodyEl.innerHTML = '';

    // ---------- Schema summary line ----------
    bodyEl.appendChild(
      el(
        'div',
        'help centre-heading',
        `DB: ${db || ''} | Tables: ${Object.keys(cfg.tables || {}).length} | Foreign keys: ${countRelationships(cfg)}`
      )
    );

    // ---------------- Existing FK relationships ----------------
    // ---------- Section title ----------
    bodyEl.appendChild(el('div', 'pane-section__title centre-heading', 'Existing relationships'));

    const list = el('div', 'fields-list');
    let hasAny = false;

    // ---------- Walk all tables and list their foreign keys ----------
    Object.entries(cfg.tables || {}).forEach(([tableName, table]) => {
      (table.foreignKeys || []).forEach((fk) => {
        hasAny = true;

        const row = el('div', 'relationship-item-row');

        // ---------- Left box: from child column to referenced parent column ----------
        const left = el('div', 'relationship-item-box mono');
        left.appendChild(el('div', '', `${tableName}.${fk.column}`));
        left.appendChild(el('div', 'arrow-line', '↓'));
        left.appendChild(el('div', '', `${fk.refTable}.${fk.refColumn}`));

        // ---------- Rules box: ON DELETE / ON UPDATE behavior ----------
        const rules = el('div', 'relationship-item-box');
        rules.appendChild(el('div', '', `ON DELETE ${fk.onDelete}`));
        rules.appendChild(el('div', 'spacer-line', ''));
        rules.appendChild(el('div', '', `ON UPDATE ${fk.onUpdate}`));

        // ---------- Remove button: resolves actual constraint name then deletes ----------
        const removeBtn = el('button', 'btn btn-danger', 'Remove');
        removeBtn.onclick = async () => {
          if (!db) return;

          // ---------- Confirm destructive action ----------
          if (!confirm(`Remove relationship?\n\n${tableName}.${fk.column} → ${fk.refTable}.${fk.refColumn}`)) return;

          // ---------- Find the real constraint name for this FK before removing ----------
          const fkName = await resolveFkConstraintName(db, tableName, fk);
          if (!fkName) return;

          await foreignKeysApi.remove(db, tableName, fkName);
          onChanged?.();
        };

        row.append(left, rules, removeBtn);
        list.appendChild(row);
      });
    });

    // ---------- Empty-state when no relationships exist ----------
    if (!hasAny) list.appendChild(el('div', 'empty-state', 'No relationships defined.'));
    bodyEl.appendChild(list);

    // ---------------- Add FK relationship ----------------
    // ---------- Section title ----------
    bodyEl.appendChild(el('div', 'pane-section__title centre-heading', 'Add relationship'));

    const form = el('div');

    // ---------- Parent table options (must have a PK) + child table options (any table) ----------
    const parents = tableOptions(cfg, { requirePk: true });
    const all = tableOptions(cfg);

    // ---------- Parent table selector ----------
    form.appendChild(el('div', 'help', 'Parent table'));
    const pSel = buildSelect(parents, state.parentTable);
    pSel.onchange = () => {
      state.parentTable = pSel.value;

      // ---------- Default FK column naming convention: {parent}_id ----------
      state.fkColumn = pSel.value ? `${pSel.value}_id` : '';
      render();
    };
    form.appendChild(pSel);

    // ---------- Child table selector ----------
    form.appendChild(el('div', 'help', 'Child table'));
    const cSel = buildSelect(all, state.childTable);
    cSel.onchange = () => {
      state.childTable = cSel.value;
      render();
    };
    form.appendChild(cSel);

    // ---------- FK column input ----------
    form.appendChild(el('div', 'help', 'FK column'));
    const fkInp = el('input', 'form-control');
    fkInp.value = state.fkColumn;
    fkInp.oninput = () => (state.fkColumn = fkInp.value);
    form.appendChild(fkInp);

    // ---------- ON DELETE rule selector ----------
    form.appendChild(el('div', 'help', 'ON DELETE'));
    const delSel = buildRuleSelect(state.onDelete);
    delSel.onchange = () => (state.onDelete = delSel.value);
    form.appendChild(delSel);

    // ---------- ON UPDATE rule selector ----------
    form.appendChild(el('div', 'help', 'ON UPDATE'));
    const updSel = buildRuleSelect(state.onUpdate);
    updSel.onchange = () => (state.onUpdate = updSel.value);
    form.appendChild(updSel);

    // ---------- Add relationship button ----------
    const addBtn = el('button', 'btn btn-primary', 'Add Relationship');
    addBtn.onclick = async () => {
      if (!db) return;

      // ---------- Parent must have a primary key column to reference ----------
      const pk = cfg.tables?.[state.parentTable]?.primaryKey?.[0];
      if (!pk) return;

      await foreignKeysApi.createAuto(
        db,
        state.childTable,
        state.fkColumn,
        state.parentTable,
        pk,
        state.onDelete,
        state.onUpdate
      );

      onChanged?.();
    };

    // ---------- Centered button row ----------
    const btnRow = el('div', 'center-buttons');
    btnRow.appendChild(addBtn);
    form.appendChild(btnRow);

    bodyEl.appendChild(form);
  };

  // =========================================================
  // Initial render
  // =========================================================

  render();
  return { paneEl };
}
