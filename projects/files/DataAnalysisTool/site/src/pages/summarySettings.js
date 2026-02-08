// =========================================================
// Summary Settings page: load an existing summary config or
// build a new one by selecting DB, main table, summary fields,
// and detail fields, then save the configuration
// =========================================================

// /src/pages/summarySettings.js

// =========================================================
// Imports: DOM helper, UI panes, database API, and shared helpers
// =========================================================

import { el } from '../ui/common/dom.js';

import { renderLoadSummaryConfigPane } from '../ui/panes/table/loadSummaryConfigPane.js';
import { renderSelectDatabasePane } from '../ui/panes/database/selectDatabasePane.js';
import { renderSelectMainTablePane } from '../ui/panes/table/selectMainTablePane.js';
import { renderFieldPickerPane } from '../ui/panes/table/fieldPickerPane.js';
import { renderSaveSummaryConfigPane } from '../ui/panes/table/saveSummaryConfigPane.js';

import { databasesApi } from '../api/databases.js';

import { normalizePicked } from '../ui/helpers/SummaryHelpers.js';

// =========================================================
// Page factory (used by router/page loader)
// =========================================================

export function createPage() {
  return {
    // ---------- Page ID used for routing/navigation ----------
    id: 'sumSet',

    // =========================================================
    // Page mount: renders UI into rootEl and orchestrates rerenders
    // =========================================================
    async mount({ rootEl }) {
      // ---------- Initial shell render ----------
      rootEl.innerHTML = '';
      rootEl.appendChild(el('h2', 'centre-heading', 'Summary Settings'));

      // =========================================================
      // Local state for building/saving a summary configuration
      // =========================================================
      const state = {
        db: '',
        mainTable: '',
        summaryFields: [],
        detailFields: [],
      };

      // =========================================================
      // Rerender function: rebuilds the whole page from current state
      // =========================================================
      const rerender = async () => {
        // ---------- Clear and rebuild page content ----------
        rootEl.innerHTML = '';
        rootEl.appendChild(el('h2', 'centre-heading', 'Summary Settings'));

        // =========================================================
        // PANE: Load existing summary configuration
        // =========================================================
        const loader = renderLoadSummaryConfigPane({
          onLoad: (cfg) => {
            // ---------- Apply loaded config into local state ----------
            state.db = cfg.db;
            state.mainTable = cfg.mainTable;
            state.summaryFields = cfg.summaryFields || [];
            state.detailFields = cfg.detailFields || [];
            rerender();
          }
        });
        rootEl.appendChild(loader.paneEl);

        // =========================================================
        // PANE: Select database
        // =========================================================

        // ---------- Load DB list for selector pane ----------
        let databases = [];
        try {
          databases = await databasesApi.list();
        } catch (e) {
          console.error(e);
          databases = [];
        }

        const { paneEl: dbPane } = renderSelectDatabasePane({
          databases,
          currentDb: state.db,
          onDbChange: (db) => {
            // ---------- Reset dependent selections when DB changes ----------
            state.db = db;
            state.mainTable = '';
            state.summaryFields = [];
            state.detailFields = [];
            rerender();
          },
        });
        rootEl.appendChild(dbPane);

        // ---------- Stop until a database is selected ----------
        if (!state.db) return;

        // =========================================================
        // Load schema for selected DB (used by table + field pickers)
        // =========================================================
        let cfg;
        try {
          cfg = await databasesApi.schema(state.db);
        } catch (e) {
          console.error(e);
          alert('Failed to load database schema.');
          return;
        }

        // =========================================================
        // PANE: Select main table
        // =========================================================
        const { paneEl: tablePane } = renderSelectMainTablePane({
          cfg,
          currentTable: state.mainTable,
          onTableChange: (t) => {
            // ---------- Reset field selections when main table changes ----------
            state.mainTable = t;
            state.summaryFields = [];
            state.detailFields = [];
            rerender();
          },
        });
        rootEl.appendChild(tablePane);

        // ---------- Stop until a main table is selected ----------
        if (!state.mainTable) return;

        // =========================================================
        // PANE: Pick summary fields
        // =========================================================
        const summaryPicker = renderFieldPickerPane({
          cfg,
          mainTable: state.mainTable,
          title: 'Summary Fields',
          initialSelected: state.summaryFields,
          selectAllMode: 'all',
          allowReorder: true,
          showFieldMeta: false,
        });
        rootEl.appendChild(summaryPicker.paneEl);

        // =========================================================
        // PANE: Pick detail fields
        // =========================================================
        const detailPicker = renderFieldPickerPane({
          cfg,
          mainTable: state.mainTable,
          title: 'Detail Fields',
          initialSelected: state.detailFields,
          selectAllMode: 'all',
          allowReorder: true,
          showFieldMeta: false,
        });
        rootEl.appendChild(detailPicker.paneEl);

        // =========================================================
        // PANE: Save summary configuration
        // =========================================================
        const saver = renderSaveSummaryConfigPane({
          getConfig: () => ({
            db: state.db,
            mainTable: state.mainTable,

            // ---------- Normalize selections into stable descriptor objects ----------
            summaryFields: normalizePicked(summaryPicker.getSelected(), state.mainTable),
            detailFields: normalizePicked(detailPicker.getSelected(), state.mainTable),

            // ---------- Config version for backward-compatible evolution ----------
            version: 2,
          }),
        });
        rootEl.appendChild(saver.paneEl);
      };

      // =========================================================
      // Initial render
      // =========================================================
      rerender();
    }
  };
}
