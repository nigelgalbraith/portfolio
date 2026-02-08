// =========================================================
// Summary page: load a saved summary configuration, run the
// summary query, render results with filter/sort, and provide
// quick navigation to edit a selected row in Data Entry
// =========================================================

// site/src/pages/summaryPage.js

// =========================================================
// Imports: DOM helpers, UI panes/components, URL helpers, APIs,
// and shared summary helper utilities
// =========================================================

import { el } from '../ui/common/dom.js';
import { renderLoadSummaryConfigPane } from '../ui/panes/table/loadSummaryConfigPane.js';
import { renderPaneShell } from '../ui/panes/common/paneShell.js';
import { renderEmptyState } from '../ui/common/emptyState.js';
import { pickDetailsTitle } from '../ui/dataTable/detailsTitle.js';
import { setTableInUrl, setPkParamsInUrl } from '../app/urlState.js';
import { renderTable } from '../ui/dataTable/dataTable.js';
import { createTableFilterSort } from '../ui/dataTable/tableFilterSort.js';
import { openColumnFilterPopup } from '../ui/dataTable/columnFilterPopup.js';
import { summaryApi } from '../api/summary.js';
import { recordsApi } from '../api/records.js';
import {
  buildColDefs,
  filterSummaryCols,
  getRowValue,
} from '../ui/helpers/SummaryHelpers.js';

// =========================================================
// Page factory (used by router/page loader)
// =========================================================

export function createPage() {
  return {
    // ---------- Page ID used for routing/navigation ----------
    id: 'summary',

    // =========================================================
    // Page mount: renders UI into rootEl and wires up callbacks
    // =========================================================
    async mount({ rootEl, dbId, setDbInUrl, setHeaderTitle }) {
      // =========================================================
      // Local page state (single source of truth for render)
      // =========================================================
      const state = {
        cfg: null,
        rows: [],
        pkCols: [],
        loading: false,
        error: '',
        summaryCols: [],
        detailCols: [],
      };

      // ---------- Filter/sort state for the results table (built after a run) ----------
      let tableState = null;

      // =========================================================
      // Header helper
      // =========================================================

      // ---------- Update page title shown in header (if provided) ----------
      const setHeader = () => {
        if (!setHeaderTitle) return;
        setHeaderTitle(`Data Analysis — Summary${dbId ? ` — ${dbId}` : ''}`);
      };

      // =========================================================
      // Summary execution: run backend query and prepare table columns/state
      // =========================================================

      // ---------- Run summary query using the loaded configuration ----------
      const runSummary = async () => {
        if (!state.cfg) return;

        state.loading = true;
        state.error = '';
        await render();

        try {
          // ---------- Execute summary request ----------
          const resp = await summaryApi.run(state.cfg);

          // ---------- Extract rows and alias mapping produced by backend ----------
          const rows = resp?.rows || [];
          const aliasMap = resp?.aliasMap || {};

          // ---------- Build summary/detail columns using shared helper functions ----------
          state.summaryCols = buildColDefs(state.cfg.summaryFields, aliasMap);
          state.detailCols = buildColDefs(state.cfg.detailFields, aliasMap);
          state.rows = rows;

          // ---------- Fetch PK columns for the main table to enable "Edit" actions ----------
          try {
            const pk = await recordsApi.primaryKey(state.cfg.db, state.cfg.mainTable);
            state.pkCols = Array.isArray(pk?.columns) ? pk.columns : [];
          } catch {
            state.pkCols = [];
          }

          // Filters/sort work on KEYS (not labels)
          // ---------- Create filter/sort state from visible summary column keys ----------
          const visibleSummary = filterSummaryCols(state.summaryCols, state.cfg.mainTable);
          tableState = visibleSummary.length
            ? createTableFilterSort({ columns: visibleSummary.map(c => c.key) })
            : null;

        } catch (e) {
          console.error(e);
          state.error = 'Failed to run summary.';
          state.rows = [];
          state.pkCols = [];
          state.summaryCols = [];
          state.detailCols = [];
          tableState = null;
        } finally {
          state.loading = false;
          await render();
        }
      };

      // =========================================================
      // Pane renderers: run controls + results table
      // =========================================================

      // ---------- Render "Run Summary" pane with status and error display ----------
      const renderRunPane = () => {
        const body = el('div');

        // ---------- Show config context for user clarity ----------
        body.appendChild(
          el(
            'div',
            'help centre-heading',
            `DB: ${state.cfg?.db || ''}  |  Table: ${state.cfg?.mainTable || ''}`
          )
        );

        // ---------- Run button ----------
        const btnRow = el('div', 'center-buttons');
        const runBtn = el('button', 'btn btn-primary', state.loading ? 'Running…' : 'Run Summary');
        runBtn.type = 'button';
        runBtn.disabled = !!state.loading;
        runBtn.addEventListener('click', runSummary);
        btnRow.appendChild(runBtn);
        body.appendChild(btnRow);

        // ---------- Error output (if any) ----------
        if (state.error) {
          const err = el('div', 'help centre-heading');
          err.dataset.kind = 'error';
          err.textContent = state.error;
          body.appendChild(err);
        }

        return renderPaneShell({ title: 'Run Summary', bodyEl: body, wide: true });
      };

      // ---------- Render results table pane with filter/sort and row actions ----------
      const renderResultsPane = () => {
        // ---------- Apply active filter/sort state to rows (if enabled) ----------
        const rows = tableState ? tableState.apply(state.rows) : state.rows;

        // ---------- Remove implicit main table id from summary view ----------
        const summaryFields = filterSummaryCols(state.summaryCols, state.cfg.mainTable);

        const tableEl = renderTable({
          rows,
          summaryFields, // [{key,label}]
          detailFields: state.detailCols,   // [{key,label}]
          showDetails: true,
          detailsTitle: pickDetailsTitle,

          // ---------- Column header click opens filter popup when tableState is available ----------
          onHeaderClick: tableState
            ? (colKey) => {
                openColumnFilterPopup({
                  column: colKey,
                  tableState,
                  onApply: () => render(),
                });
              }
            : null,

          // ---------- Per-row actions (enable Edit only when PK values are present) ----------
          rowActions: (row) => {
            if (!state.cfg || !state.pkCols.length) return [];

            const canEdit = state.pkCols.every(k => getRowValue(row, k, state.cfg.mainTable) != null);
            if (!canEdit) return [];

            return [{
              label: 'Edit',
              className: 'btn btn-primary',
              onClick: () => {
                // ---------- Ensure DB selection matches config ----------
                if (typeof setDbInUrl === 'function') setDbInUrl(state.cfg.db);

                // ---------- Ensure table selection matches config ----------
                setTableInUrl(state.cfg.mainTable);

                // ---------- Persist PK into URL so Data Entry opens in edit mode ----------
                const pkRow = Object.fromEntries(
                  state.pkCols.map(k => [k, getRowValue(row, k, state.cfg.mainTable)])
                );
                setPkParamsInUrl(state.pkCols, pkRow);

                // ---------- Navigate to Data Entry page ----------
                window.location.hash = '#/dataEntry';
              }
            }];
          },
        });

        return renderPaneShell({
          title: `Results (${rows.length})`,
          bodyEl: tableEl,
          wide: true,
        });
      };

      // =========================================================
      // Main render: config loader + run pane + results pane
      // =========================================================

      const render = async () => {
        // ---------- Clear and rebuild page content ----------
        rootEl.innerHTML = '';
        setHeader();

        // ---------- Page heading ----------
        rootEl.appendChild(el('h2', 'centre-heading', 'Summary Table'));

        // ---------- Config loader pane (select/load summary config) ----------
        const loader = renderLoadSummaryConfigPane({
          title: 'Load Summary Configuration',
          onLoad: (cfg) => {
            // ---------- Reset state when a new config is loaded ----------
            state.cfg = cfg;
            state.rows = [];
            state.pkCols = [];
            state.error = '';
            state.summaryCols = [];
            state.detailCols = [];
            tableState = null;

            // ---------- Ensure app DB selection matches loaded config ----------
            if (cfg?.db && typeof setDbInUrl === 'function') setDbInUrl(cfg.db);
            render();
          },
          showRefresh: false,
        });

        rootEl.appendChild(loader.paneEl);

        // ---------- Empty-state until a config is loaded ----------
        if (!state.cfg) {
          rootEl.appendChild(renderEmptyState('Load a summary config to run a summary query.'));
          return;
        }

        // ---------- Run controls pane ----------
        rootEl.appendChild(renderRunPane());

        // ---------- Empty-state until results exist ----------
        if (!state.rows.length) {
          rootEl.appendChild(renderEmptyState('No results yet. Click “Run Summary”.'));
          return;
        }

        // ---------- Results table pane ----------
        rootEl.appendChild(renderResultsPane());
      };

      // =========================================================
      // Initial render
      // =========================================================

      await render();
    },
  };
}
