// =========================================================
// API helper for retrieving application pages metadata
// =========================================================

// /site/src/api/pages.js
import { apiClient } from './client.js';

// =========================================================
// Page-related API methods
// =========================================================

export const pagesApi = {
  // ---------- Retrieve all registered pages ----------
  list: () => apiClient.get('/api/pages'),
};
