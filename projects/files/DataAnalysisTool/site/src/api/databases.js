// =========================================================
// API helper for database-level operations, including listing
// databases, creating new ones, retrieving schemas, and
// managing table metadata
// =========================================================

import { apiClient } from "./client.js";

// =========================================================
// Database-related API methods
// =========================================================

export const databasesApi = {
  // ---------- Retrieve all available databases ----------
  list: () => apiClient.get("/api/databases"),

  // ---------- Create a new database ----------
  create: (db) => apiClient.post("/api/databases", { db }),

  // ---------- Fetch schema information for a database ----------
  schema: (db) =>
    apiClient.get(`/api/databases/${encodeURIComponent(db)}/schema`),

  // ---------- Update table metadata (roles / display semantics) ----------
  setTableMeta: (db, meta) =>
    apiClient.post(`/api/databases/${encodeURIComponent(db)}/table-meta`, meta),
};
