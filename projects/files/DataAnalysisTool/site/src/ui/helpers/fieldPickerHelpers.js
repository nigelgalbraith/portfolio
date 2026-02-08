// ==================================================
// Helpers for field picker
// ==================================================

// ---------- Field/list identification ----------
function isFieldObj(v) {
  return !!v && typeof v === 'object' && typeof v.table === 'string' && typeof v.column === 'string';
}

function isListObj(v) {
  return !!v && typeof v === 'object' && v.kind === 'list' && typeof v.field === 'string';
}

// ---------- Field/list tokens and labels ----------
function itemKey(item) {
  if (isListObj(item)) return `list:${item.field}`;
  if (isFieldObj(item)) return `field:${item.table}.${item.column}`;
  return '';
}

function itemLabel(item) {
  if (isListObj(item)) return `LIST:${item.field}`;
  if (isFieldObj(item)) return `${item.table}.${item.column}`;
  return '';
}

// ---------- Normalize initial selected values (v2 only) ----------
function normalizeIncomingInitialSelected(list, mainTable) {
  // Strict mode: accept only v2 objects.
  // If you pass strings in here, they will be dropped (on purpose).
  const out = [];
  const seen = new Set();

  for (const v of (Array.isArray(list) ? list : [])) {
    let item = null;

    if (isListObj(v)) {
      item = { kind: 'list', field: String(v.field).trim() };
    } else if (isFieldObj(v)) {
      item = { table: String(v.table).trim(), column: String(v.column).trim() };
    } else {
      continue;
    }

    const k = itemKey(item);
    if (!k || seen.has(k)) continue;
    seen.add(k);
    out.push(item);
  }

  return out;
}

// ==================================================
// Exports
// ==================================================

export {
  isFieldObj,
  isListObj,
  itemKey,
  itemLabel,
  normalizeIncomingInitialSelected,
};
