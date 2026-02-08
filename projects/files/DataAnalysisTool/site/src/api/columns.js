// =========================================================
// API helper for managing table columns within a database,
// providing list, create, and delete operations
// =========================================================

import { apiClient } from "./client.js";

// =========================================================
// Column-specific API methods scoped to a database and table
// =========================================================

export const columnsApi = {
  // ---------- Retrieve all columns for a given table ----------
  list: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/columns`
    ),

  // ---------- Create a new column with a specified name and type ----------
  create: (db, table, name, type) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/columns`,
      { name, type }
    ),

  // ---------- Remove a column from the specified table ----------
  remove: (db, table, column) =>
    apiClient.del(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/columns/${encodeURIComponent(column)}`
    ),
};
