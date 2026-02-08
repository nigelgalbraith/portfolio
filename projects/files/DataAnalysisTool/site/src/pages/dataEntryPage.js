// =========================================================
// Data Entry page: select a database + main table, then create,
// edit, and delete records with FK lookups and junction relations
// =========================================================

// /src/pages/dataEntryPage.js

// =========================================================
// Imports: DOM helpers, UI panes, URL state helpers, and APIs
// =========================================================

import { el } from '../ui/common/dom.js';
import { renderSelectDatabasePane } from '../ui/panes/database/selectDatabasePane.js';
import { renderSelectMainTablePane } from '../ui/panes/table/selectMainTablePane.js';
import { renderDataEntryPane } from '../ui/panes/table/dataEntryPane.js';
import {
  getSearchParams,
  getTableFromUrl,
  getPkFromUrl,
  setTableInUrl,
  setSearchParams,
  clearPkFromUrl,
  clearPrefillAndPkFromUrl,
} from '../app/urlState.js';
import { databasesApi } from '../api/databases.js';
import { recordsApi } from '../api/records.js';

// =========================================================
// Page factory (used by router/page loader)
// =========================================================

export function createPage() {
  return {
    // ---------- Page ID used for routing/navigation ----------
    id: 'dataEntry',

    // ---------- Cleanup URL state when leaving the page ----------
    unmount() {
      clearPrefillAndPkFromUrl();
    },

    // =========================================================
    // Page mount: renders UI into rootEl and wires up callbacks
    // =========================================================
    async mount({ rootEl, dbId, setDbInUrl, setHeaderTitle }) {
      // =========================================================
      // Local page state (single source of truth for render)
      // =========================================================
      const state = {
        db: (dbId || '').trim(),
        databases: [],
        table: getTableFromUrl(),
        schema: null,
        tableSchema: null,

        columns: [],
        pkCols: [],
        fks: [],
        junctionRelations: [],
        junctionSelections: new Map(),
        junctionOptions: new Map(),

        mode: 'new',
        pk: {},
        values: {},

        distinctCache: new Map(),
        fkOptions: new Map(),

        loading: false,
        error: '',
        message: '',
      };

      // =========================================================
      // Header + small accessors
      // =========================================================

      // ---------- Update page title shown in header (if provided) ----------
      const setHeader = () => {
        if (!setHeaderTitle) return;
        setHeaderTitle(
          `Data Analysis — Data Entry${state.db ? ` — ${state.db}` : ''}`
        );
      };

      // ---------- Find foreign key metadata for a column name ----------
      const getFkForColumn = (colName) =>
        (state.fks || []).find(f => f?.column === colName) || null;

      // =========================================================
      // Database-level loading helpers
      // =========================================================

      // ---------- Load database schema/config (tables + meta) ----------
      const loadSchema = async () => {
        state.schema = null;
        if (!state.db) return;
        state.schema = await databasesApi.schema(state.db);
      };

      // ---------- Load list of databases for the selector pane ----------
      const loadDatabasesList = async () => {
        try {
          state.databases = await databasesApi.list();
        } catch {
          state.databases = [];
        }
      };

      // =========================================================
      // Table-level reset + metadata loading
      // =========================================================

      // ---------- Clear all state that is specific to the selected table ----------
      const resetTableState = () => {
        state.columns = [];
        state.pkCols = [];
        state.fks = [];
        state.tableSchema = null;
        state.distinctCache.clear();
        state.fkOptions.clear();
        state.junctionRelations = [];
        state.junctionSelections.clear();
        state.junctionOptions.clear();

        state.mode = 'new';
        state.pk = {};
        state.values = {};

        state.error = '';
        state.message = '';
      };

      // ---------- Load schema, PKs, and FKs for the selected table ----------
      const loadTableMeta = async () => {
        resetTableState();
        if (!state.db || !state.table) return;

        const [tableSchema, fks] = await Promise.all([
          recordsApi.schema(state.db, state.table),
          recordsApi.foreignKeys(state.db, state.table),
        ]);

        // ---------- Normalize FK shape to a consistent internal format ----------
        const normalizeFk = (fk) => ({
          name: fk?.name || fk?.constraint_name || '',
          column: fk?.column || fk?.column_name,
          refTable: fk?.refTable || fk?.ref_table,
          refColumn: fk?.refColumn || fk?.ref_column,
          onDelete: fk?.onDelete || fk?.delete_rule,
          onUpdate: fk?.onUpdate || fk?.update_rule,
        });

        state.tableSchema = tableSchema || null;
        state.columns = Array.isArray(tableSchema?.columns)
          ? tableSchema.columns.map(c => ({ name: c.name, type: c.type }))
          : [];
        state.pkCols = Array.isArray(tableSchema?.primaryKey)
          ? tableSchema.primaryKey
          : [];
        state.fks = Array.isArray(fks) ? fks.map(normalizeFk) : [];

        // ---------- Derive many-to-many relations via junction table detection ----------
        state.junctionRelations = buildJunctionRelations();
      };

      // =========================================================
      // Record loading via PK in URL (edit mode)
      // =========================================================

      // ---------- If URL includes pk_* params, load the matching record for editing ----------
      const loadRecordIfPkInUrl = async () => {
        if (!state.db || !state.table) return;

        const pk = getPkFromUrl(state.pkCols);
        const hasPk =
          Object.keys(pk).length === state.pkCols.length &&
          state.pkCols.length > 0;

        state.pk = hasPk ? pk : {};
        state.mode = hasPk ? 'edit' : 'new';
        state.values = {};

        if (!hasPk) return;

        const resp = await recordsApi.get(state.db, state.table, pk);
        const row = resp?.row || null;

        // ---------- If record no longer exists, fall back to new mode and clear URL PK ----------
        if (!row) {
          state.error = 'Record not found.';
          state.mode = 'new';
          state.pk = {};
          clearPkFromUrl(state.pkCols);
          return;
        }

        // ---------- Populate editable values from the loaded row ----------
        for (const c of state.columns) {
          state.values[c.name] = row[c.name];
        }
      };

      // =========================================================
      // Lookup utilities (labels, distinct values, FK options)
      // =========================================================

      // ---------- Choose a human-friendly label column for a referenced table ----------
      const pickLabelColumn = (tableName, fallbackCol) => {
        const meta = state.schema?.tableMeta?.[tableName] || null;
        if (meta?.labelColumn) return meta.labelColumn;
        const cols = (state.schema?.tables?.[tableName]?.columns || []).map(c => c.name);
        const candidates = ['name', 'title', 'label'];
        const picked = candidates.find(c => cols.includes(c));
        return picked || fallbackCol;
      };

      // ---------- Cache distinct values to reduce repeated server calls ----------
      const ensureDistinctForColumn = async (colName) => {
        if (!state.db || !state.table) return;
        if (state.distinctCache.has(colName)) return;
        const rows = await recordsApi.distinct(state.db, state.table, colName, 50);
        state.distinctCache.set(colName, Array.isArray(rows) ? rows : []);
      };

      // ---------- Cache foreign key dropdown options per FK definition ----------
      const ensureFkOptions = async (fk) => {
        if (!state.db || !fk?.refTable || !fk?.refColumn) return;
        const key = `${fk.column}::${fk.refTable}::${fk.refColumn}`;
        if (state.fkOptions.has(key)) return;

        const labelCol = pickLabelColumn(fk.refTable, fk.refColumn);
        const rows = await recordsApi.lookup(state.db, fk.refTable, {
          valueCol: fk.refColumn,
          labelCol,
          limit: 100,
          search: '',
        });

        state.fkOptions.set(key, Array.isArray(rows) ? rows : []);
      };

      // ---------- Cache option lists used for junction (many-to-many) selectors ----------
      const ensureJunctionOptions = async (rel) => {
        if (!state.db || !rel?.farTable || !rel?.farRefColumn) return;
        const key = rel.key;
        if (state.junctionOptions.has(key)) return;

        const labelCol = pickLabelColumn(rel.farTable, rel.farRefColumn);
        const rows = await recordsApi.lookup(state.db, rel.farTable, {
          valueCol: rel.farRefColumn,
          labelCol,
          limit: 200,
          search: '',
        });

        state.junctionOptions.set(key, Array.isArray(rows) ? rows : []);
      };

      // =========================================================
      // Junction relationship discovery + selection loading
      // =========================================================

      // ---------- Detect junction tables and build relationship descriptors for UI ----------
      const buildJunctionRelations = () => {
        const cfg = state.schema;
        if (!cfg || !state.table) return [];

        const tables = cfg.tables || {};
        const tableMeta = cfg.tableMeta || {};
        const junctionTables = new Set();

        // ---------- Prefer explicit tableType = 'junction' when provided ----------
        for (const [t, meta] of Object.entries(tableMeta)) {
          if (meta?.tableType === 'junction') junctionTables.add(t);
        }

        // ---------- Fallback heuristic: tables with 2+ foreign keys are likely junction tables ----------
        for (const [t, tcfg] of Object.entries(tables || {})) {
          const fkCount = (tcfg?.foreignKeys || []).length;
          if (fkCount >= 2) junctionTables.add(t);
        }

        const rels = [];

        // ---------- For each junction table, pair main-table FK(s) with far-table FK(s) ----------
        for (const jt of junctionTables) {
          const jtCfg = tables[jt];
          if (!jtCfg) continue;
          const fks = jtCfg.foreignKeys || [];
          const mainFks = fks.filter(f => f.refTable === state.table);
          const otherFks = fks.filter(f => f.refTable !== state.table);
          if (!mainFks.length || !otherFks.length) continue;

          for (const mainFk of mainFks) {
            for (const farFk of otherFks) {
              if (!tables?.[farFk.refTable]) continue;
              const key = `${jt}::${mainFk.column}::${farFk.column}`;
              rels.push({
                key,
                junctionTable: jt,
                mainFkColumn: mainFk.column,
                mainRefColumn: mainFk.refColumn,
                farTable: farFk.refTable,
                farFkColumn: farFk.column,
                farRefColumn: farFk.refColumn,
              });
            }
          }
        }

        return rels;
      };

      // ---------- Load current junction selections for the record in edit mode ----------
      const loadJunctionSelections = async () => {
        state.junctionSelections.clear();
        if (state.mode !== 'edit') return;

        for (const rel of state.junctionRelations || []) {
          const mainId = state.pk?.[rel.mainRefColumn];
          if (mainId == null) {
            state.junctionSelections.set(rel.key, []);
            continue;
          }

          const rows = await recordsApi.junctionSelection(state.db, {
            junctionTable: rel.junctionTable,
            mainFkColumn: rel.mainFkColumn,
            mainId,
            farFkColumn: rel.farFkColumn,
          });

          state.junctionSelections.set(rel.key, Array.isArray(rows) ? rows : []);
        }
      };

      // =========================================================
      // Table init orchestration (meta + record + junctions)
      // =========================================================

      // ---------- Load everything needed after a table selection/change ----------
      const initAfterTable = async () => {
        state.loading = true;
        await render();
        try {
          await loadTableMeta();
          await loadRecordIfPkInUrl();
          await loadJunctionSelections();
        } finally {
          state.loading = false;
          await render();
        }
      };

      // =========================================================
      // Render function: rebuilds the whole page from current state
      // =========================================================
      const render = async () => {
        // ---------- Clear and rebuild page content ----------
        rootEl.innerHTML = '';
        setHeader();

        // ---------- Page heading ----------
        rootEl.appendChild(el('h2', 'centre-heading', 'Data Entry'));

        // ---------- Database selector pane ----------
        const { paneEl: dbPane } = renderSelectDatabasePane({
          databases: state.databases,
          currentDb: state.db,
          onDbChange: async (db) => {
            if (typeof setDbInUrl === 'function') {
              setDbInUrl(db, { remount: true });
            }
          },
        });
        rootEl.appendChild(dbPane);

        // ---------- Stop if no database selected ----------
        if (!state.db) return;

        // ---------- Schema loading placeholder ----------
        if (!state.schema) {
          rootEl.appendChild(
            el('div', 'empty-state', 'Loading database schema…')
          );
          return;
        }

        // ---------- Main table selector pane ----------
        const { paneEl: tablePane } = renderSelectMainTablePane({
          cfg: state.schema,
          currentTable: state.table,
          onTableChange: async (t) => {
            // ---------- Persist selected table to URL and reset table-dependent state ----------
            state.table = (t || '').trim();
            setTableInUrl(state.table);
            clearPrefillAndPkFromUrl();
            resetTableState();
            if (state.table) await initAfterTable();
            else await render();
          },
        });
        rootEl.appendChild(tablePane);

        // ---------- Stop if no table selected ----------
        if (!state.table) return;

        // ---------- Data entry pane for record editing/creation ----------
        const { paneEl } = renderDataEntryPane({
          state,
          getFkForColumn,
          ensureFkOptions,
          ensureDistinctForColumn,
          ensureJunctionOptions,

          junctionRelations: state.junctionRelations,

          // ---------- Switch to new record mode (clears PK + selections) ----------
          onNewRecord: () => {
            state.mode = 'new';
            state.pk = {};
            state.values = {};
            state.junctionSelections.clear();
            clearPkFromUrl(state.pkCols);
            state.message = '';
            state.error = '';
            render();
          },

          // ---------- Create or update record, then apply junction selections ----------
          onSave: async () => {
            state.error = '';
            state.message = '';

            const wasNew = state.mode === 'new';

            // ---------- Validate required fields on create ----------
            if (wasNew) {
              const required = state.tableSchema?.requiredOnCreate || [];
              const missing = required.filter(k => {
                const v = state.values[k];
                return v === null || v === undefined || String(v).trim() === '';
              });
              if (missing.length) {
                state.error = `Missing required fields: ${missing.join(', ')}`;
                await render();
                return;
              }
            }

            state.loading = true;
            await render();

            try {
              // ---------- Build changes object (exclude PK columns) ----------
              const values = { ...state.values };
              const changes = { ...values };
              for (const c of state.pkCols) delete changes[c];

              // ---------- Persist record via API (create vs update) ----------
              let resp;
              if (wasNew) {
                resp = await recordsApi.create(state.db, state.table, values);
              } else {
                resp = await recordsApi.update(state.db, state.table, state.pk, changes);
              }

              // ---------- Ensure PK is reflected back into the URL for edit mode ----------
              const pkOut = resp?.pk || state.pk || {};
              if (resp?.pk) {
                for (const c of state.pkCols) {
                  if (resp.pk[c] != null) {
                    setSearchParams({ [`pk_${c}`]: resp.pk[c] });
                  }
                }
              }

              // ---------- Apply many-to-many selections via junction tables ----------
              for (const rel of state.junctionRelations || []) {
                const mainId = pkOut?.[rel.mainRefColumn];
                if (mainId == null) continue;
                const farIds = state.junctionSelections.get(rel.key) || [];

                await recordsApi.applyJunctionSelection(state.db, {
                  junctionTable: rel.junctionTable,
                  mainFkColumn: rel.mainFkColumn,
                  mainId,
                  farFkColumn: rel.farFkColumn,
                  farIds,
                });
              }

              // ---------- Refresh metadata + record view after save ----------
              await loadTableMeta();
              await loadRecordIfPkInUrl();
              await loadJunctionSelections();

              state.message = wasNew
                ? 'Record created.'
                : 'Record updated.';
            } catch (e) {
              state.error = e?.message || 'Save failed.';
            } finally {
              state.loading = false;
              await render();
            }
          },

          // ---------- Delete current record and clear edit state ----------
          onDelete: async () => {
            if (!confirm('Delete this record?')) return;

            state.loading = true;
            state.error = '';
            state.message = '';
            await render();

            try {
              await recordsApi.remove(state.db, state.table, state.pk);
              state.message = 'Deleted.';
              state.mode = 'new';
              state.pk = {};
              state.values = {};
              clearPkFromUrl(state.pkCols);
            } catch (e) {
              state.error = e?.message || 'Delete failed.';
            } finally {
              state.loading = false;
              await render();
            }
          },
        });

        // ---------- Append data entry UI ----------
        rootEl.appendChild(paneEl);
      };

      // =========================================================
      // URL hygiene: clear stale PK/prefill when not explicitly present
      // =========================================================

      const sp = getSearchParams();
      const hasPkInUrl = [...sp.keys()].some(k => k.startsWith('pk_'));
      if (!hasPkInUrl) clearPrefillAndPkFromUrl();

      // =========================================================
      // Initial load + first render
      // =========================================================

      // ---------- Populate database selector options ----------
      await loadDatabasesList();

      // ---------- Load schema if DB is already selected via URL ----------
      if (state.db) {
        state.loading = true;
        await render();
        try {
          await loadSchema();
        } finally {
          state.loading = false;
        }
      }

      // ---------- If a table is already selected, initialize table context ----------
      if (state.db && state.table) await initAfterTable();
      else await render();
    },
  };
}
