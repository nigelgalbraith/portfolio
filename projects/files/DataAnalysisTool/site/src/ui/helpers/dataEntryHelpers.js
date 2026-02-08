// ==================================================
// Helpers for data entry UI
// ==================================================

// ---------- Normalize values for text inputs ----------
function normalizeValueForInput(v) {
  if (v == null) return '';
  return String(v);
}

// ---------- Fill a <datalist> with values ----------
function fillDatalist(dl, values) {
  if (!dl) return;
  dl.innerHTML = '';
  for (const v of (values || [])) {
    const opt = document.createElement('option');
    opt.value = v == null ? '' : String(v);
    dl.appendChild(opt);
  }
}

// ---------- Fill a <select> for FK options ----------
function fillFkSelect(sel, rows) {
  if (!sel) return;

  const current = sel.value;
  const placeholder = sel.querySelector('option[value=""]');

  sel.innerHTML = '';

  if (placeholder) sel.appendChild(placeholder);
  else {
    const opt0 = document.createElement('option');
    opt0.value = '';
    opt0.textContent = '— select —';
    sel.appendChild(opt0);
  }

  for (const r of (rows || [])) {
    const opt = document.createElement('option');
    opt.value = r.value == null ? '' : String(r.value);
    opt.textContent = r.label == null ? String(r.value ?? '') : String(r.label);
    sel.appendChild(opt);
  }

  sel.value = current;
}

// ---------- Fill a multi-select with options and selected values ----------
function fillMultiSelect(sel, rows, selectedValues) {
  if (!sel) return;
  const selected = new Set((selectedValues || []).map(v => String(v)));
  sel.innerHTML = '';

  for (const r of (rows || [])) {
    const opt = document.createElement('option');
    const value = r.value == null ? '' : String(r.value);
    opt.value = value;
    opt.textContent = r.label == null ? String(r.value ?? '') : String(r.label);
    opt.selected = selected.has(value);
    sel.appendChild(opt);
  }
}

// ==================================================
// Exports
// ==================================================

export {
  normalizeValueForInput,
  fillDatalist,
  fillFkSelect,
  fillMultiSelect,
};
