// =========================================================
// URL state management helpers for reading and updating
// application state via query string parameters
// =========================================================

// site/src/app/urlState.js

// =========================================================
// Core helpers
// =========================================================

// ---------- Get URLSearchParams for the current location ----------
export function getSearchParams() {
  return new URL(window.location.href).searchParams;
}

// ---------- Retrieve and normalize a single query parameter ----------
export function getParam(name) {
  return (getSearchParams().get(name) || '').trim();
}

// ---------- Update one or more query parameters without reloading ----------
export function setSearchParams(updates = {}) {
  const url = new URL(window.location.href);
  for (const [k, v] of Object.entries(updates)) {
    if (v === undefined || v === null || v === '') url.searchParams.delete(k);
    else url.searchParams.set(k, String(v));
  }
  window.history.replaceState({}, '', url.toString());
}

// =========================================================
// Common app params
// =========================================================

// ---------- Read selected database name from the URL ----------
export function getDbFromUrl() {
  return getParam('db');
}

// ---------- Read selected table name from the URL ----------
export function getTableFromUrl() {
  return getParam('table');
}

// ---------- Update the selected table in the URL ----------
export function setTableInUrl(table) {
  setSearchParams({ table: table || '' });
}

// ---------- Persist primary key values for a selected row ----------
export function setPkParamsInUrl(pkCols, row) {
  const updates = {};
  for (const k of pkCols || []) updates[`pk_${k}`] = row?.[k];
  setSearchParams(updates);
}

// ---------- Read primary key values from the URL ----------
export function getPkFromUrl(pkCols) {
  const sp = getSearchParams();
  const pk = {};
  for (const c of pkCols || []) {
    const v = sp.get(`pk_${c}`);
    if (v != null && v !== '') pk[c] = v;
  }
  return pk;
}

// ---------- Clear primary key parameters from the URL ----------
export function clearPkFromUrl(pkCols) {
  const updates = {};
  for (const c of pkCols || []) updates[`pk_${c}`] = '';
  setSearchParams(updates);
}

// ---------- Clear primary key and prefill parameters ----------
export function clearPrefillAndPkFromUrl() {
  const url = new URL(window.location.href);
  const keys = [...url.searchParams.keys()];
  for (const k of keys) {
    if (k.startsWith('pk_') || k.startsWith('prefill_')) {
      url.searchParams.delete(k);
    }
  }
  window.history.replaceState({}, '', url.toString());
}
