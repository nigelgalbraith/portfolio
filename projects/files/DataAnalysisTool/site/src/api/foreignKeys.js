// =========================================================
// API helper for managing foreign key relationships between
// tables, including listing, creation, and removal
// =========================================================

import { apiClient } from "./client.js";

// =========================================================
// Foreign key–related API methods scoped to a database and table
// =========================================================

export const foreignKeysApi = {
  // ---------- Retrieve all foreign keys for a table ----------
  list: (db, table) =>
    apiClient.get(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/foreign-keys`
    ),

  // ---------- Create a simple foreign key using existing columns ----------
  createSimple: (db, table, fromColumn, toTable, toColumn) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/foreign-keys`,
      {
        fromColumn,
        toTable,
        toColumn
      }
    ),

  // ---------- Automatically create a foreign key column and constraint ----------
  createAuto: (
    db,
    table,
    fkColumn,
    toTable,
    toColumn,
    onDelete = "RESTRICT",
    onUpdate = "RESTRICT"
  ) =>
    apiClient.post(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/foreign-keys`,
      {
        auto: true,
        fkColumn,
        toTable,
        toColumn,
        onDelete,
        onUpdate
      }
    ),

  // ---------- Remove a foreign key constraint by name ----------
  remove: (db, table, fkName) =>
    apiClient.del(
      `/api/databases/${encodeURIComponent(db)}/tables/${encodeURIComponent(table)}/foreign-keys/${encodeURIComponent(fkName)}`
    ),
};
