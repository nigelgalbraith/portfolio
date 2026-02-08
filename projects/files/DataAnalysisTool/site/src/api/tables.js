// =========================================================
// API helper for managing database tables, including listing,
// creation, deletion, and SQL import operations
// =========================================================

import { apiClient } from "./client.js";

// ---------- Encode database names for safe URL usage ----------
const encDb = (db) => encodeURIComponent(db);

// =========================================================
// Table-related API methods scoped to a database
// =========================================================

export const tablesApi = {
    // ---------- Retrieve all tables for a database ----------
    list: (db) =>
        apiClient.get(`/api/databases/${encDb(db)}/tables`),

    // ---------- Create a new table ----------
    create: (db, table) =>
        apiClient.post(`/api/databases/${encDb(db)}/tables`, { table }),

    // ---------- Remove a table ----------
    remove: (db, table) =>
        apiClient.del(`/api/databases/${encDb(db)}/tables/${encodeURIComponent(table)}`),

    // ---------- Import tables from an uploaded SQL file ----------
    importSql: (db, file) => {
        const fd = new FormData();
        fd.append("file", file);
        return apiClient.post(`/api/databases/${encDb(db)}/tables/import`, fd);
    },
};
