// =========================================================
// API helper for managing junction (join) tables, typically
// used to model many-to-many relationships
// =========================================================

import { apiClient } from "./client.js";

// ---------- Encode database names for safe URL usage ----------
const encDb = (db) => encodeURIComponent(db);

// =========================================================
// Junction table–related API methods
// =========================================================

export const junctionsApi = {
  // ---------- Create a new junction table using the provided definition ----------
  create: (db, payload) =>
    apiClient.post(`/api/databases/${encDb(db)}/junctions`, payload),

  // ---------- Remove an existing junction table ----------
  remove: (db, table) =>
    apiClient.del(
      `/api/databases/${encDb(db)}/junctions/${encodeURIComponent(table)}`
    ),
};
