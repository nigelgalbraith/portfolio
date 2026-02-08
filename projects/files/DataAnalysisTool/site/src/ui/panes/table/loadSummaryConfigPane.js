// =========================================================
// Load Summary Config pane: fetches available saved configs,
// renders a selector + load/refresh controls, validates the
// chosen id, and returns the loaded config payload to caller
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
export function renderLoadSummaryConfigPane({
  onLoad,
  title = 'Load Summary Configuration',
  showRefresh = true,
}) {
  // ---------- Pane shell + body container ----------
  const body = el('div');
  const paneEl = renderPaneShell({ title, bodyEl: body, className: 'pane--load-summary' });

  // =========================================================
  // Section layout
  // =========================================================

  const section = el('div', 'pane-section');
  section.appendChild(
    el('div', 'pane-section__title centre-heading', 'Load an existing summary configuration')
  );

  // ---------- Config dropdown ----------
  const select = el('select', 'form-control');
  section.appendChild(select);

  // =========================================================
  // Buttons
  // =========================================================

  const buttons = createCenteredButtonRow();

  // ---------- Load selected config ----------
  const loadBtn = el('button', 'btn btn-primary', 'Load');
  loadBtn.type = 'button';
  buttons.appendChild(loadBtn);

  // ---------- Optional refresh list button ----------
  let refreshBtn = null;
  if (showRefresh) {
    refreshBtn = el('button', 'btn btn-secondary', 'Refresh');
    refreshBtn.type = 'button';
    buttons.appendChild(refreshBtn);
  }

  section.appendChild(buttons);

  // ---------- Help text ----------
  const help = el('div', 'help small centre-heading');
  help.textContent = 'Choose a saved config from the server configs folder.';
  section.appendChild(help);

  body.appendChild(section);

  // =========================================================
  // Options builder
  // =========================================================

  // ---------- Replace dropdown options from server list ----------
  const setOptions = (items) => {
    select.innerHTML = '';

    const placeholder = document.createElement('option');
    placeholder.value = '';
    placeholder.textContent = items.length ? 'Select a config…' : 'No configs found';
    select.appendChild(placeholder);

    items.forEach(({ id, label }) => {
      const opt = document.createElement('option');
      opt.value = id; // IMPORTANT: base id (no .json)
      opt.textContent = label || id;
      select.appendChild(opt);
    });
  };

  // =========================================================
  // Data loading
  // =========================================================

  // ---------- Fetch config list from server and populate dropdown ----------
  const loadList = async () => {
    try {
      const items = await configsApi.list();
      const list = Array.isArray(items) ? items : [];
      setOptions(list);
    } catch (e) {
      console.error(e);
      setOptions([]);
      alert('Failed to list configs.');
    }
  };

  // ---------- Refresh handler (if enabled) ----------
  if (refreshBtn) refreshBtn.addEventListener('click', loadList);

  // =========================================================
  // Load selected config
  // =========================================================

  // ---------- Validate selection id, fetch config, and emit to onLoad ----------
  loadBtn.addEventListener('click', async () => {
    const res = normalizeId(select.value, { type: 'config' });
    if (!res.ok) return alert(res.error);

    try {
      const resp = await configsApi.get(res.id);
      const cfg = resp?.data; // unwrap
      if (!cfg) return alert('Loaded file had no data.');

      onLoad?.(cfg);
    } catch (e) {
      console.error(e);
      alert('Failed to load config.');
    }
  });

  // ---------- Initial list population ----------
  loadList();

  return { paneEl, selectEl: select };
}
