// =========================================================
// Relationships page: select a database, load its schema, then
// define and manage 1:N foreign keys and N:M/M:N junction links
// =========================================================

// /src/pages/relationships.js

// =========================================================
// Imports: DOM helpers, UI panes, and database API
// =========================================================

import { el } from '../ui/common/dom.js';

import { renderSelectDatabasePane } from '../ui/panes/database/selectDatabasePane.js';
import { renderRelationshipsFkPane } from '../ui/panes/relationships/relationshipsFkPane.js';
import { renderRelationshipsJunctionPane } from '../ui/panes/relationships/relationshipsJunctionPane.js';
import { databasesApi } from '../api/databases.js';

// =========================================================
// Page factory (used by router/page loader)
// =========================================================

export function createPage() {
  return {
    // ---------- Page ID used for routing/navigation ----------
    id: 'relationships',

    // =========================================================
    // Page mount: renders UI into rootEl and wires up pane callbacks
    // =========================================================
    async mount({ rootEl, dbId, setDbInUrl, setHeaderTitle }) {
      // ---------- helpers ----------
      // ---------- Update page title shown in header (if provided) ----------
      const setHeader = () => {
        if (!setHeaderTitle) return;
        setHeaderTitle(`Data Analysis — Relationships${dbId ? ` — ${dbId}` : ''}`);
      };

      // ---------- Switch active DB by updating URL and remounting page ----------
      const changeDb = (newDb) => {
        if (typeof setDbInUrl === 'function') {
          setDbInUrl(newDb, { remount: true });
        }
      };

      // ---------- render shell ----------
      // ---------- Reset page content before rendering panes ----------
      rootEl.innerHTML = '';
      setHeader();

      // ---------- Page heading ----------
      rootEl.appendChild(el('h2', 'centre-heading', 'Relationships'));

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
      // PANE 1: Select Database  (SAME AS DATABASE SETTINGS)
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
      // Stop if no db selected
      // =========================================================
      // ---------- Prevent rendering relationship panes until a DB is selected ----------
      if (!currentDb) {
        rootEl.appendChild(
          el('div', 'empty-state', 'Select a database to define relationships.')
        );
        return;
      }

      // =========================================================
      // Load schema once for this DB
      // =========================================================
      // ---------- Fetch schema/config used by relationship panes ----------
      let cfg;
      try {
        cfg = await databasesApi.schema(currentDb);
      } catch (e) {
        console.error(e);
        rootEl.appendChild(
          el('div', 'empty-state', 'Failed to load database schema.')
        );
        return;
      }

      // ---------- Normalize schema shape to avoid undefined checks in panes ----------
      cfg.tables = cfg.tables || {};

      // =========================================================
      // PANE: Relationships (1:N)
      // =========================================================
      // ---------- Manage foreign keys between tables (one-to-many) ----------
      rootEl.appendChild(
        renderRelationshipsFkPane({
          cfg,
          getSelectedDb,
          onChanged: () => changeDb(getSelectedDb()),
        }).paneEl
      );

      // =========================================================
      // PANE: Relationships (N:M)
      // =========================================================
      // ---------- Manage junction relationships in N:M orientation ----------
      rootEl.appendChild(
        renderRelationshipsJunctionPane({
          cfg,
          getSelectedDb,
          mode: 'N:M',
          onChanged: () => changeDb(getSelectedDb()),
        }).paneEl
      );

      // =========================================================
      // PANE: Relationships (M:N)
      // =========================================================
      // ---------- Manage junction relationships in M:N orientation ----------
      rootEl.appendChild(
        renderRelationshipsJunctionPane({
          cfg,
          getSelectedDb,
          mode: 'M:N',
          onChanged: () => changeDb(getSelectedDb()),
        }).paneEl
      );
    }
  };
}
