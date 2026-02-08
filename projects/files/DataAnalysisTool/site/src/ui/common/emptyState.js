// =========================================================
// Empty state UI helper for displaying centered placeholder
// messages when no data or selection is available
// =========================================================

// site/src/ui/common/emptyState.js

// =========================================================
// Imports
// =========================================================

import { el } from './dom.js';

// =========================================================
// Render helpers
// =========================================================

// ---------- Create a standard empty-state container ----------
export function renderEmptyState(text) {
  return el('div', 'empty-state', text);
}
