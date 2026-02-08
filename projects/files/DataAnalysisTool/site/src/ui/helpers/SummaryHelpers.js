// =========================================================
// Summary helpers: internal utilities and a small public API
// used by summary pages for column definitions, value lookup,
// and normalization of picked fields
// =========================================================

// site/src/ui/helpers/SummaryHelpers.js

// =========================================================
// Internal helpers (NOT exported)
// =========================================================

// ---------- Check if value represents a table.field object ----------
function isFieldObj(v) {
  return !!v && typeof v === 'object' && typeof v.table === 'string' && typeof v.column === 'string';
}

// ---------- Check if value represents a list descriptor ----------
function isListObj(v) {
  return !!v && typeof v === 'object' && v.kind === 'list' && typeof v.field === 'string';
}

// ---------- Build a stable token used for alias lookup ----------
function tokenFor(item) {
  if (isListObj(item)) return `list:${item.field}`;
  if (isFieldObj(item)) return `field:${item.table}.${item.column}`;
  return '';
}

// ---------- Build a human-readable label for UI display ----------
function labelFor(item) {
  if (isListObj(item)) return `LIST:${item.field}`;
  if (isFieldObj(item)) return `${item.table}.${item.column}`;
  return String(item);
}

// ---------- Normalize a picked value into a field/list descriptor ----------
function toFieldItem(v, mainTable) {
  if (typeof v !== 'string') return v;

  const s = v.trim();
  if (!s) return null;

  // support list token if you ever add it back
  if (s.startsWith('LIST:')) {
    return { kind: 'list', field: s.slice(5).trim() };
  }

  const i = s.indexOf('.');
  if (i >= 0) {
    return { table: s.slice(0, i), column: s.slice(i + 1) };
  }

  // bare column => main table
  return { table: mainTable, column: s };
}

// =========================================================
// Public API (exported)
// =========================================================

// ---------- Retrieve a value from a row, handling aliased keys ----------
export function getRowValue(row, key, mainTable) {
  if (row?.[key] != null) return row[key];
  const aliased = `${mainTable}__${key}`;
  if (row?.[aliased] != null) return row[aliased];
  return null;
}

// ---------- Build column definitions from summary/detail field descriptors ----------
export function buildColDefs(fields, aliasMap) {
  const list = Array.isArray(fields) ? fields : [];
  const map = aliasMap || {};
  return list.map((item) => {
    const tok = tokenFor(item);
    const key = map[tok];
    if (!key) {
      // If this happens, backend + frontend are out of sync.
      // Better to show something obvious than [object Object].
      return { key: '__MISSING_ALIAS__', label: `MISSING: ${labelFor(item)}` };
    }
    return { key, label: labelFor(item) };
  });
}

// ---------- Remove the implicit main-table id column from summary output ----------
export function filterSummaryCols(cols, mainTable) {
  const mainId = `${mainTable}.id`;
  return (cols || []).filter(c => c.label !== mainId);
}

// ---------- Normalize picked fields into a de-duplicated descriptor list ----------
export function normalizePicked(list, mainTable) {
  const out = [];
  const seen = new Set();

  for (const v of (Array.isArray(list) ? list : [])) {
    const item = toFieldItem(v, mainTable);
    if (!item) continue;

    const key =
      item.kind === 'list'
        ? `list:${item.field}`
        : `field:${item.table}.${item.column}`;

    if (seen.has(key)) continue;
    seen.add(key);
    out.push(item);
  }
  return out;
}
