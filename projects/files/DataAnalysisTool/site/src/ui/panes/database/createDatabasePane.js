// =========================================================
// Create Database pane: UI for creating a new database by
// entering a validated name and submitting it to the backend
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el, createCenteredButtonRow } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { databasesApi } from '../../../api/databases.js';
import { normalizeId } from '../../common/ids.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render pane for creating a new database ----------
export function renderCreateDatabasePane({ onCreated }) {
  // ---------- Root body element for pane content ----------
  const bodyEl = el('div');

  // =========================================================
  // Input section
  // =========================================================

  const section = el('div', 'pane-section');
  const label = el('div', 'pane-section__title centre-heading', 'New Database Name');

  // ---------- Database name input ----------
  const input = el('input', 'form-control');
  input.type = 'text';
  input.placeholder = 'e.g. jobtracker';
  input.autocomplete = 'off';

  // =========================================================
  // Action buttons
  // =========================================================

  const buttons = createCenteredButtonRow();
  const createBtn = el('button', 'btn btn-primary', 'Create Database');
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

  // ---------- Validate input, create database, and notify caller ----------
  createBtn.addEventListener('click', async () => {
    const res = normalizeId(input.value, { type: 'db' });
    if (!res.ok) {
      alert(res.error);
      return;
    }

    try {
      await databasesApi.create(res.id);
      alert(`Database ${res.id} created.`);
      onCreated?.(res.id);
    } catch (err) {
      console.error(err);
      alert('Failed to create database.');
    }
  });

  // =========================================================
  // Pane shell assembly
  // =========================================================

  const paneEl = renderPaneShell({
    title: 'Create Database',
    bodyEl,
    className: 'pane--create-database',
  });

  // ---------- Expose pane element and input for external use ----------
  return { paneEl, dbInputEl: input };
}
