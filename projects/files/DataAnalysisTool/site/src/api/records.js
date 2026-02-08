// =========================================================
// API helper for working with table records, schemas, and
// relational data, including querying, CRUD operations,
// lookups, and junction table interactions
// =========================================================

import { apiClient } from "./client.js";

// =========================================================
// Record- and table-level API methods
// =========================================================

export const recordsApi = {
  // ---------- Retrieve table schema definition ----------
  schema: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/schema`
    ),

  // ---------- Retrieve primary key information for a table ----------
  primaryKey: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/primary-key`
    ),

  // ---------- Retrieve column definitions for a table ----------
  columns: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/columns`
    ),

  // ---------- Retrieve foreign key definitions for a table ----------
  foreignKeys: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/foreign-keys`
    ),

  // ---------- Query records with filters and pagination ----------
  query: (db, table, { filters = {}, limit = 50, offset = 0 } = {}) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/records/query`,
      { filters, limit, offset }
    ),

  // ---------- Retrieve a single record by primary key ----------
  get: (db, table, pk) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/records/get`,
      { pk }
    ),

  // ---------- Create a new record ----------
  create: (db, table, values = {}) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/records`,
      { values }
    ),

  // ---------- Update an existing record by primary key ----------
  update: (db, table, pk, changes = {}) =>
    apiClient.patch(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/records`,
      { pk, changes }
    ),

  // ---------- Delete a record by primary key ----------
  remove: (db, table, pk) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/records/delete`,
      { pk }
    ),

  // ---------- Retrieve distinct values for a column ----------
  distinct: (db, table, column, limit = 50) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/distinct/${encodeURIComponent(column)}?limit=${encodeURIComponent(limit)}`
    ),

  // ---------- Retrieve lookup data for value/label pairs ----------
  lookup: (db, table, { valueCol, labelCol = "", limit = 50, search = "" } = {}) => {
    const qs = new URLSearchParams();
    qs.set("value_col", valueCol);
    if (labelCol) qs.set("label_col", labelCol);
    if (limit) qs.set("limit", String(limit));
    if (search) qs.set("search", search);
    return apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/lookup?${qs.toString()}`
    );
  },

  // ---------- Retrieve selected relationships from a junction table ----------
  junctionSelection: (db, { junctionTable, mainFkColumn, mainId, farFkColumn }) => {
    const qs = new URLSearchParams();
    qs.set("junction_table", junctionTable);
    qs.set("main_fk_column", mainFkColumn);
    qs.set("main_id", String(mainId));
    qs.set("far_fk_column", farFkColumn);
    return apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/junctions/selection?${qs.toString()}`
    );
  },

  // ---------- Apply relationship updates to a junction table ----------
  applyJunctionSelection: (
    db,
    { junctionTable, mainFkColumn, mainId, farFkColumn, farIds = [] }
  ) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/junctions/selection`,
      {
        junctionTable,
        mainFkColumn,
        mainId,
        farFkColumn,
        farIds,
      }
    ),
};
