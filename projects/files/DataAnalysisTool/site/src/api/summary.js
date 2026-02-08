// =========================================================
// API helper for running summary operations based on a
// provided configuration
// =========================================================

// /site/src/api/summary.js
import { apiClient } from './client.js';

// =========================================================
// Summary-related API methods
// =========================================================

export const summaryApi = {
  // ---------- Execute a summary job using the given configuration ----------
  run: (config) => apiClient.post('/api/summary/run', { config }),
};
