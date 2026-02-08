// =========================================================
// Table Card pane: renders one table "card" showing columns,
// PK/FK badges, and actions to remove table/columns, add new
// columns, and set the table’s semantic type (entity/lookup/
// junction) stored in database metadata
// =========================================================

// ==================================================
// Imports
// ==================================================
import { el, createCenteredButtonRow } from '../../common/dom.js';
import { tablesApi } from '../../../api/tables.js';
import { columnsApi } from '../../../api/columns.js';
import { databasesApi } from '../../../api/databases.js';
import { normalizeId } from '../../common/ids.js';

// ==================================================
// Pane Rendering
// ==================================================
export function renderTableCardPane({
  cfg,
  tableName,
  getSelectedDb,
  onChanged, // refresh schema + rerender cards
}) {
  // ---------- Root card element ----------
  const tableCard = el('div', 'table-card');

  // ---------- Table schema snapshot + key maps ----------
  const tableCfg = cfg.tables[tableName] || {};
  const pkSet = new Set(tableCfg.primaryKey || []);
  const fkByCol = new Map((tableCfg.foreignKeys || []).map(fk => [fk.column, fk]));

  // ---------- Small badge helper for PK/FK/ref labels ----------
  const badge = (text, cls) => el('span', `key-badge ${cls}`, text);

  // ---------- Unified "refresh and rerender" callback ----------
  const runChanged = async () => {
    if (typeof onChanged === 'function') {
      await onChanged();
    }
  };

  // ---------- Get selected DB or show a user-facing warning ----------
  const getDbOrWarn = () => {
    const db = getSelectedDb?.();
    if (!db) {
      alert('No database selected.');
      return null;
    }
    return db;
  };

  // ----------------------------------
  // Header
  // ----------------------------------

  // ---------- Centered header region ----------
  const headerBlock = el('div', 'table-card__header-center');
  const tableHeading = el('h3', 'centre-heading table-card__title', tableName);

  // ---------- Table type selector (semantic role stored in DB metadata) ----------
  const meta = (cfg.tableMeta && cfg.tableMeta[tableName]) ? cfg.tableMeta[tableName] : null;
  const tableTypeSelect = el('select', 'form-control table-type-select');
  ['entity', 'lookup', 'junction'].forEach((t) => {
    const opt = el('option', '', t);
    opt.value = t;
    if (meta && meta.tableType === t) opt.selected = true;
    tableTypeSelect.appendChild(opt);
  });

  // ---------- Remove entire table button ----------
  const removeTableBtn = el('button', 'btn btn-danger table-card__remove', 'Remove Table');
  removeTableBtn.type = 'button';

  headerBlock.appendChild(tableHeading);
  headerBlock.appendChild(tableTypeSelect);
  headerBlock.appendChild(removeTableBtn);
  tableCard.appendChild(headerBlock);

  // ---------- Delete table action ----------
  removeTableBtn.addEventListener('click', async () => {
    const db = getDbOrWarn();
    if (!db) return;

    try {
      await tablesApi.remove(db, tableName);
      alert(`Table ${tableName} removed.`);
      await runChanged();
    } catch (err) {
      console.error(err);
      alert('Failed to remove table (it may not be empty).');
    }
  });

  // ---------- Persist table type metadata ----------
  tableTypeSelect.addEventListener('change', async () => {
    const db = getDbOrWarn();
    if (!db) return;

    const tableType = (tableTypeSelect.value || '').trim();
    try {
      await databasesApi.setTableMeta(db, {
        tableName,
        tableType,
      });
      await runChanged();
    } catch (err) {
      console.error(err);
      alert('Failed to update table type.');
    }
  });

  // ----------------------------------
  // Fields
  // ----------------------------------

  // ---------- Field list container ----------
  const fieldsList = el('div', 'fields-list');

  // ---------- Render each existing column row ----------
  (tableCfg.columns || []).forEach((field) => {
    const fieldRow = el('div', 'field-row');

    // ---------- Read-only field name ----------
    const fieldNameInput = el('input', 'field-name-input form-control');
    fieldNameInput.type = 'text';
    fieldNameInput.value = field.name;
    fieldNameInput.disabled = true;

    // ---------- Column type label ----------
    const typeText = el('span', 'field-type', field.type);

    // ---------- Key badges container (PK/FK/reference) ----------
    const keysCell = el('div', 'field-keys');
    let hasKeys = false;

    if (pkSet.has(field.name)) {
      keysCell.appendChild(badge('PK', 'key-badge--pk'));
      hasKeys = true;
    }

    const fk = fkByCol.get(field.name);
    if (fk) {
      keysCell.appendChild(badge('FK', 'key-badge--fk'));
      keysCell.appendChild(badge(`${fk.refTable}.${fk.refColumn}`, 'key-badge--ref'));
      hasKeys = true;
    }

    if (hasKeys) keysCell.classList.add('has-keys');

    // ---------- Remove column button ----------
    const removeFieldBtn = el('button', 'btn btn-danger', 'Remove');
    removeFieldBtn.type = 'button';

    removeFieldBtn.addEventListener('click', async () => {
      const db = getDbOrWarn();
      if (!db) return;

      try {
        await columnsApi.remove(db, tableName, field.name);
        alert(`Field ${field.name} removed.`);
        await runChanged();
      } catch (err) {
        console.error(err);
        alert('Failed to remove field.');
      }
    });

    fieldRow.appendChild(fieldNameInput);
    fieldRow.appendChild(typeText);
    fieldRow.appendChild(keysCell);
    fieldRow.appendChild(removeFieldBtn);

    fieldsList.appendChild(fieldRow);
  });

  tableCard.appendChild(fieldsList);

  // ----------------------------------
  // Actions
  // ----------------------------------

  // ---------- Bottom action row ----------
  const actionsRow = createCenteredButtonRow();
  const addFieldBtn = el('button', 'btn btn-primary', 'Add Field');

  addFieldBtn.type = 'button';

  actionsRow.appendChild(addFieldBtn);
  tableCard.appendChild(actionsRow);

  // ----------------------------------
  // Add Field
  // ----------------------------------

  // ---------- Insert "add field" form row inline under fields list ----------
  addFieldBtn.addEventListener('click', () => {
    const newRow = el('div', 'add-field-row');

    // ---------- New column name input ----------
    const nameInput = el('input', 'form-control');
    nameInput.placeholder = 'Field Name';

    // ---------- Column type dropdown ----------
    const typeDropdown = el('select', 'form-control');
    ['VARCHAR(255)', 'INT', 'BIGINT', 'BOOLEAN', 'DATE', 'TEXT'].forEach(type => {
      const opt = document.createElement('option');
      opt.value = type;
      opt.textContent = type;
      typeDropdown.appendChild(opt);
    });

    // ---------- Inline add button ----------
    const btnRow = createCenteredButtonRow();
    const addBtn = el('button', 'btn btn-success', 'Add Column');
    addBtn.type = 'button';
    btnRow.appendChild(addBtn);

    // ---------- Validate name, create column, and refresh card list ----------
    addBtn.addEventListener('click', async () => {
      const db = getDbOrWarn();
      if (!db) return;

      const raw = (nameInput.value || '').trim();
      const res = normalizeId(raw, { type: 'column' });

      if (!res.ok) {
        alert(res.error);
        return;
      }

      const fieldName = res.id;

      try {
        await columnsApi.create(db, tableName, fieldName, typeDropdown.value);
        alert(`Field ${fieldName} added.`);

        // remove the input row immediately (prevents duplicates if refresh is slow)
        newRow.remove();

        await runChanged();
      } catch (err) {
        console.error(err);
        alert('Failed to add column.');
      }
    });

    newRow.appendChild(nameInput);
    newRow.appendChild(typeDropdown);
    newRow.appendChild(btnRow);
    fieldsList.appendChild(newRow);
  });

  return { cardEl: tableCard };
}
