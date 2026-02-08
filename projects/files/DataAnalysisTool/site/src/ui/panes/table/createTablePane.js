// =========================================================
// Create Table pane: UI for creating a new table in the
// currently selected database with name validation
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el, createCenteredButtonRow } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { tablesApi } from '../../../api/tables.js';
import { normalizeId } from '../../common/ids.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render pane for creating a new table ----------
export function renderCreateTablePane({ getSelectedDb, onCreated }) {
  // ---------- Root body element for pane content ----------
  const bodyEl = el('div');

  // =========================================================
  // Input section
  // =========================================================

  const section = el('div', 'pane-section');
  const label = el('div', 'pane-section__title centre-heading', 'New Table Name');

  // ---------- Table name input ----------
  const input = el('input', 'form-control');
  input.type = 'text';
  input.placeholder = 'e.g. users';
  input.autocomplete = 'off';

  // =========================================================
  // Action buttons
  // =========================================================

  const buttons = createCenteredButtonRow();
  const createBtn = el('button', 'btn btn-primary', 'Create Table');
  createBtn.type = 'button';
  buttons.appendChild(createBtn);

  // ---------- Assemble input section ----------
  section.appendChild(label);
  section.appendChild(input);
  section.appendChild(buttons);
  bodyEl.appendChild(section);

  // =========================================================
  // Create action handler
  // =========================================================

  // ---------- Validate target DB + table name, then create table ----------
  createBtn.addEventListener('click', async () => {
    const targetDb = (getSelectedDb?.() || '').trim();
    if (!targetDb) {
      alert('Select a database first.');
      return;
    }

    const res = normalizeId(input.value, { type: 'table' });
    if (!res.ok) {
      alert(res.error);
      return;
    }

    try {
      await tablesApi.create(targetDb, res.id);
      alert(`Table ${res.id} created.`);
      onCreated?.(res.id);
    } catch (err) {
      console.error(err);
      alert('Failed to create table.');
    }
  });

  // =========================================================
  // Pane shell assembly
  // =========================================================

  const paneEl = renderPaneShell({
    title: 'Create Table',
    bodyEl,
    className: 'pane--create-table',
  });

  // ---------- Expose pane element and input for external use ----------
  return { paneEl, tableInputEl: input };
}
