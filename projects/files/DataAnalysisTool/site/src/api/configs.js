// =========================================================
// API helper for managing application configuration entries,
// including retrieval, persistence, deletion, and existence checks
// =========================================================

// /site/src/api/configs.js

import { apiClient } from './client.js';

// =========================================================
// Configuration-related API methods
// =========================================================

export const configsApi = {
    // ---------- Retrieve all configuration identifiers ----------
    async list() {
        return apiClient.get('/api/configs');
    },

    // ---------- Fetch a specific configuration by ID ----------
    async get(configId) {
        return apiClient.get(`/api/configs/${encodeURIComponent(configId)}`);
    },

    // ---------- Create or update a configuration entry ----------
    async save(configId, data) {
        return apiClient.put(
            `/api/configs/${encodeURIComponent(configId)}`,
            { data }
        );
    },

    // ---------- Delete a configuration entry ----------
    async remove(configId) {
        return apiClient.del(`/api/configs/${encodeURIComponent(configId)}`);
    },

    // ---------- Check whether a configuration entry exists ----------
    async exists(configId) {
        return apiClient.head(`/api/configs/${encodeURIComponent(configId)}`);
    },
};
