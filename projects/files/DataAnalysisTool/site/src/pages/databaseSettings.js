// =========================================================
// Database Settings page: database selection/creation/import,
// plus table creation and table list rendering for the active DB
// =========================================================

// /src/pages/databaseSettings.js

// =========================================================
// DOM + UI pane imports
// =========================================================
import { el } from '../ui/common/dom.js';

import { renderSelectDatabasePane } from '../ui/panes/database/selectDatabasePane.js';
import { renderCreateDatabasePane } from '../ui/panes/database/createDatabasePane.js';
import { renderImportDatabasePane } from '../ui/panes/database/importDatabasePane.js';
import { renderCreateTablePane } from '../ui/panes/table/createTablePane.js';
import { renderTableCardPane } from '../ui/panes/table/tableCardPane.js';

// =========================================================
// API imports
// =========================================================
import { databasesApi } from '../api/databases.js';

// =========================================================
// Page factory (used by router/page loader)
// =========================================================
export function createPage() {
  return {
    // ---------- Page ID used for routing/navigation ----------
    id: 'database',

    // =========================================================
    // Page mount: renders UI into rootEl and wires up pane callbacks
    // =========================================================
    async mount({ rootEl, dbId, setDbInUrl, setHeaderTitle }) {
      // ---------- helpers ----------
      const setHeader = () => {
        if (!setHeaderTitle) return;
        setHeaderTitle(`Data Analysis — Database Settings${dbId ? ` — ${dbId}` : ''}`);
      };

      const changeDb = (newDb) => {
        // One method: URL is canonical, and app owns updating it.
        // This page *does* want a remount so all panes refresh for the new db.
        if (typeof setDbInUrl === 'function') setDbInUrl(newDb, { remount: true });
      };

      // ---------- render shell ----------
      // ---------- Reset page content before rendering panes ----------
      rootEl.innerHTML = '';
      setHeader();

      // ---------- Page heading ----------
      rootEl.appendChild(el('h2', 'centre-heading', 'Database Settings'));

      // ---------- Load DB list ----------
      // ---------- Fetch list of available databases for selector pane ----------
      let databases = [];
      try {
        databases = await databasesApi.list();
      } catch (e) {
        console.error(e);
        databases = [];
      }

      // ---------- Validate current dbId against known DBs ----------
      const dbIds = new Set(databases.map(d => d.id));
      const currentDb = (dbId && dbIds.has(dbId)) ? dbId : '';

      // =========================================================
      // PANE 1: Select Database
      // =========================================================
      // ---------- Database dropdown for switching active DB ----------
      const { paneEl: selectPaneEl, dbSelectEl } = renderSelectDatabasePane({
        databases,
        currentDb,
        onDbChange: changeDb,
      });

      rootEl.appendChild(selectPaneEl);

      // ---------- Read current selection from the selector pane ----------
      const getSelectedDb = () => (dbSelectEl.value || '').trim();

      // =========================================================
      // PANE 2: Create Database
      // =========================================================
      // ---------- Create DB UI; on success, switch to the newly created DB ----------
      const { paneEl: createDbPaneEl } = renderCreateDatabasePane({
        onCreated: changeDb,
      });

      rootEl.appendChild(createDbPaneEl);

      // =========================================================
      // Stop if no db available yet
      // =========================================================
      // ---------- Prevent rendering table-related panes until a DB is selected ----------
      if (!currentDb) {
        rootEl.appendChild(
          el('div', 'empty-state', 'Select a database to begin (or create one above).')
        );
        return;
      }

      // =========================================================
      // TABLES container (create once, repopulate on refresh)
      // =========================================================
      // ---------- Holds the table cards for the currently selected DB ----------
      const tablesContainer = el('div', 'tables-container');

      // =========================================================
      // Refresh function (re-fetch schema + rebuild table cards)
      // =========================================================
      // ---------- Central refresh used after imports, creates, deletes, meta changes ----------
      const refreshDatabaseView = async () => {
        // ---------- Resolve active DB from selector (URL may remount later) ----------
        const targetDb = getSelectedDb();
        if (!targetDb) return;

        // ---------- Fetch latest schema + metadata from server ----------
        let freshCfg;
        try {
          freshCfg = await databasesApi.schema(targetDb);
        } catch (e) {
          console.error(e);
          alert('Failed to refresh database schema.');
          return;
        }

        // ---------- Normalize schema shape to avoid undefined checks downstream ----------
        freshCfg.tables = freshCfg.tables || {};

        // clear and rebuild table cards
        // ---------- Rebuild table list from scratch to stay consistent with schema ----------
        tablesContainer.innerHTML = '';

        // ---------- Extract table names from schema ----------
        const tableNames = Object.keys(freshCfg.tables);

        // Sort tables by declared type: entity → lookup → junction, then name.
        // ---------- Keep display order stable and semantically grouped ----------
        const typeOrder = { entity: 0, lookup: 1, junction: 2 };
        tableNames.sort((a, b) => {
          const aType = (freshCfg.tableMeta?.[a]?.tableType || 'entity');
          const bType = (freshCfg.tableMeta?.[b]?.tableType || 'entity');

          const aRank = (aType in typeOrder) ? typeOrder[aType] : 99;
          const bRank = (bType in typeOrder) ? typeOrder[bType] : 99;

          if (aRank !== bRank) return aRank - bRank;
          return a.localeCompare(b);
        });

        // ---------- Empty-state when the selected DB has no tables ----------
        if (tableNames.length === 0) {
          tablesContainer.appendChild(
            el('div', 'empty-state', 'No tables yet. Create one above.')
          );
          return;
        }

        // ---------- Render a card pane per table and wire each card to refresh on change ----------
        tableNames.forEach((tableName) => {
          const { cardEl } = renderTableCardPane({
            cfg: freshCfg,
            tableName,
            getSelectedDb,
            onChanged: refreshDatabaseView,
          });
          tablesContainer.appendChild(cardEl);
        });
      };

      // =========================================================
      // PANE 3: Import Database (tables import)
      // =========================================================
      // ---------- Import SQL / schema into the selected database ----------
      const { paneEl: importPaneEl } = renderImportDatabasePane({
        getSelectedDb,
        onImported: refreshDatabaseView,
      });

      rootEl.appendChild(importPaneEl);

      // =========================================================
      // PANE 4: Create Table
      // =========================================================
      // ---------- Create new tables in the selected database ----------
      const { paneEl: createTablePaneEl } = renderCreateTablePane({
        getSelectedDb,
        onCreated: refreshDatabaseView,
      });

      // ---------- Append panes and the tables list container ----------
      rootEl.appendChild(createTablePaneEl);
      rootEl.appendChild(tablesContainer);

      // =========================================================
      // Initial render of tables
      // =========================================================
      // ---------- Populate table cards for the first time on mount ----------
      await refreshDatabaseView();
    }
  };
}
