// =========================================================
// Relationships UI helpers: build table option lists and
// reusable <select> controls for table/constraint selection,
// plus small helpers for relationship counts and FK name lookup
// =========================================================

// relationshipsHelpers.js

// =========================================================
// Imports
// =========================================================

import { foreignKeysApi } from '../../api/foreignKeys.js';

// =========================================================
// Table option helpers
// =========================================================

// ---------- Return table names from cfg, optionally requiring a primary key ----------
function tableOptions(cfg, { requirePk = false } = {}) {
  const names = Object.keys(cfg.tables || {}).sort();
  return names.filter((t) => {
    if (!requirePk) return true;
    const pk = cfg.tables?.[t]?.primaryKey || [];
    return pk.length > 0;
  });
}

// =========================================================
// Select element builders
// =========================================================

// ---------- Build a generic <select> from option strings with an optional placeholder ----------
function buildSelect(options, currentValue = '', placeholder = '— select —') {
  const sel = document.createElement('select');
  sel.className = 'form-control';

  const opt0 = document.createElement('option');
  opt0.value = '';
  opt0.textContent = placeholder;
  sel.appendChild(opt0);

  for (const v of options) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    if (v === currentValue) opt.selected = true;
    sel.appendChild(opt);
  }

  return sel;
}

// ---------- Build a <select> for FK rules (on delete / on update behaviors) ----------
function buildRuleSelect(currentValue) {
  const sel = document.createElement('select');
  sel.className = 'form-control';

  ['RESTRICT', 'CASCADE', 'SET NULL', 'NO ACTION'].forEach(v => {
    const o = document.createElement('option');
    o.value = v;
    o.textContent = v;
    if (v === currentValue) o.selected = true;
    sel.appendChild(o);
  });

  return sel;
}

// =========================================================
// Relationships helpers
// =========================================================

// ---------- Default junction table name from two table names ----------
function defaultJunctionName(a, b) {
  if (!a || !b) return '';
  return `${a}_${b}`;
}

// ---------- Count total FK relationships across all tables in schema ----------
function countRelationships(cfg) {
  let n = 0;
  for (const t of Object.values(cfg.tables || {})) {
    n += (t.foreignKeys || []).length;
  }
  return n;
}

// ---------- Resolve a foreign key constraint name by matching its column + ref target ----------
async function resolveFkConstraintName(db, table, fk) {
  const list = await foreignKeysApi.list(db, table);
  const match = (list || []).find(x =>
    x.column === fk.column &&
    x.refTable === fk.refTable &&
    x.refColumn === fk.refColumn
  );
  return match?.name || '';
}

// =========================================================
// Exports
// =========================================================

export {
  defaultJunctionName,
  countRelationships,
  resolveFkConstraintName,
  tableOptions,
  buildSelect,
  buildRuleSelect,
};
