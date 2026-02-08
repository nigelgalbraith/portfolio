// =========================================================
// Save Summary Config pane: validates a config name, checks
// whether it already exists on the server, optionally asks
// to overwrite, then saves the current config payload
// =========================================================

// ==================================================
// Imports
// ==================================================
import { el, createCenteredButtonRow } from '../../common/dom.js';
import { renderPaneShell } from '../common/paneShell.js';
import { configsApi } from '../../../api/configs.js';
import { normalizeId } from '../../common/ids.js';

// ==================================================
// Pane Rendering
// ==================================================
export function renderSaveSummaryConfigPane({
  getConfig,
  title = 'Save Summary Configuration',
}) {
  // ---------- Pane shell + body container ----------
  const body = el('div');
  const paneEl = renderPaneShell({ title, bodyEl: body, className: 'pane--save-summary' });

  // =========================================================
  // Section layout
  // =========================================================

  const section = el('div', 'pane-section');
  section.appendChild(
    el('div', 'pane-section__title centre-heading', 'Save configuration name')
  );

  // ----------------------------------
  // Controls
  // ----------------------------------

  // ---------- Config name input ----------
  const nameInput = el('input', 'form-control');
  nameInput.placeholder = 'Summary name (e.g. customers_basic)';
  nameInput.autocomplete = 'off';

  // ---------- Save button row ----------
  const btnRow = createCenteredButtonRow();
  const saveBtn = el('button', 'btn btn-primary', 'Save Summary Config');
  saveBtn.type = 'button';
  btnRow.appendChild(saveBtn);

  // ---------- Inline status message (info/error/ok) ----------
  const msg = el('div', 'help small centre-heading');
  msg.textContent = '';

  // ---------- Help text ----------
  const help = el('div', 'help small centre-heading');
  help.textContent = 'Saves to the server configs folder. (Stored as <name>.json)';

  // ----------------------------------
  // Helpers
  // ----------------------------------

  // ---------- Update message text + dataset kind for styling hooks ----------
  const setMsg = (text, kind = 'info') => {
    msg.textContent = text || '';
    msg.dataset.kind = kind; // optional CSS hook
  };

  // ---------- Toggle busy UI state to prevent double-submit ----------
  const setBusy = (isBusy) => {
    saveBtn.disabled = !!isBusy;
    nameInput.disabled = !!isBusy;
    saveBtn.textContent = isBusy ? 'Saving…' : 'Save Summary Config';
  };

  // ---------- Validate config name and show computed filename preview ----------
  const validateNow = () => {
    const res = normalizeId(nameInput.value, {
      type: 'config',
      stripJsonExtension: true, // user may type ".json"
      makeFilename: true, // gives res.filename
    });

    if (!res.ok) {
      setMsg(res.error, 'error');
      return null;
    }

    setMsg(`Will save as ${res.filename}`, 'ok');
    return res;
  };

  // ---------- Live validation as user types ----------
  nameInput.addEventListener('input', validateNow);

  // ----------------------------------
  // Save
  // ----------------------------------

  // ---------- Validate, confirm overwrite (if needed), then save config ----------
  saveBtn.addEventListener('click', async () => {
    const res = validateNow();
    if (!res) return;

    const data = getConfig?.();
    if (!data) {
      setMsg('No config data to save.', 'error');
      return;
    }

    setBusy(true);

    try {
      setMsg('Checking for existing config…', 'info');
      const exists = await configsApi.exists(res.id);

      if (exists) {
        const ok = window.confirm(`${res.filename} already exists.\n\nOverwrite it?`);
        if (!ok) {
          setMsg('Save cancelled.', 'info');
          return;
        }
      }

      setMsg('Saving…', 'info');
      await configsApi.save(res.id, data);
      setMsg(`Saved ${res.filename}`, 'ok');
    } catch (e) {
      console.error(e);
      setMsg('Failed to save config.', 'error');
    } finally {
      setBusy(false);
    }
  });

  // ----------------------------------
  // Mount
  // ----------------------------------

  // ---------- Assemble section ----------
  section.appendChild(nameInput);
  section.appendChild(btnRow);
  section.appendChild(msg);
  section.appendChild(help);
  body.appendChild(section);

  // ---------- Initial validation so user sees filename rules immediately ----------
  validateNow();

  return { paneEl, nameInputEl: nameInput };
}
