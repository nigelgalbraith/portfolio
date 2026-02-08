// =========================================================
// Import Database pane: UI for importing a .sql file into the
// currently selected database
// =========================================================

// =========================================================
// Imports
// =========================================================

import { el, createCenteredButtonRow } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { tablesApi } from '../../../api/tables.js';

// =========================================================
// Pane rendering
// =========================================================

// ---------- Render pane for importing a database from a .sql file ----------
export function renderImportDatabasePane({ getSelectedDb, onImported }) {
  // ---------- Root body element for pane content ----------
  const bodyEl = el('div');

  // =========================================================
  // File selection section
  // =========================================================

  const section = el('div', 'pane-section');
  const label = el('div', 'pane-section__title centre-heading', 'Choose .sql File');

  // ---------- File input (SQL only) ----------
  const fileInput = el('input', 'form-control');
  fileInput.type = 'file';
  fileInput.accept = '.sql';

  // =========================================================
  // Action buttons
  // =========================================================

  const buttons = createCenteredButtonRow();
  const importBtn = el('button', 'btn btn-success', 'Import DB');
  importBtn.type = 'button';
  buttons.appendChild(importBtn);

  // ---------- Help text ----------
  const help = el('div', 'help small centre-heading');
  help.textContent = 'This will run the .sql file against the currently selected database.';

  // ---------- Assemble section ----------
  section.appendChild(label);
  section.appendChild(fileInput);
  section.appendChild(buttons);
  section.appendChild(help);
  bodyEl.appendChild(section);

  // =========================================================
  // Import action handler
  // =========================================================

  // ---------- Validate input and import SQL into selected database ----------
  importBtn.addEventListener('click', async () => {
    const file = fileInput.files && fileInput.files[0];
    if (!file) {
      alert('Pick a .sql file first.');
      return;
    }

    const targetDb = (getSelectedDb?.() || '').trim();
    if (!targetDb) {
      alert('Select or create a database first.');
      return;
    }

    try {
      await tablesApi.importSql(targetDb, file);
      alert(`Imported into ${targetDb}.`);
      onImported?.(targetDb);
    } catch (err) {
      console.error(err);
      alert('Import failed.');
    }
  });

  // =========================================================
  // Pane shell assembly
  // =========================================================

  const paneEl = renderPaneShell({
    title: 'Import Database (.sql)',
    bodyEl,
    className: 'pane--import-database',
  });

  // ---------- Expose pane element and file input for external use ----------
  return { paneEl, fileInputEl: fileInput };
}
