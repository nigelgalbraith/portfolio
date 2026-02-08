// =========================================================
// Table filter/sort state manager: provides in-memory filtering
// and sorting for tabular row data based on column keys
// =========================================================

// src/ui/table/tableFilterSort.js

// =========================================================
// Factory: create filter/sort controller for a table
// =========================================================

// ---------- Initialize filter/sort state for the given columns ----------
export function createTableFilterSort({ columns }) {
  const state = {
    sortKey: null,
    sortDir: 'asc',
    filters: Object.fromEntries(columns.map(c => [c, ''])),
  };

  // =========================================================
  // Apply current filters and sort to a row set
  // =========================================================

  // ---------- Return a new array with filters and sort applied ----------
  function apply(rows) {
    let out = [...rows];

    // ---------- Apply per-column text filters (case-insensitive) ----------
    for (const [key, value] of Object.entries(state.filters)) {
      if (!value) continue;
      const needle = value.toLowerCase();

      out = out.filter(r =>
        String(r?.[key] ?? '').toLowerCase().includes(needle)
      );
    }

    // ---------- Apply sorting when a sort key is active ----------
    if (state.sortKey) {
      const { sortKey, sortDir } = state;

      out.sort((a, b) => {
        const av = a?.[sortKey];
        const bv = b?.[sortKey];

        // ---------- Null/undefined handling ----------
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;

        // ---------- Numeric sort when both values are numbers ----------
        if (typeof av === 'number' && typeof bv === 'number') {
          return sortDir === 'asc' ? av - bv : bv - av;
        }

        // ---------- Fallback to string comparison ----------
        return sortDir === 'asc'
          ? String(av).localeCompare(String(bv))
          : String(bv).localeCompare(String(av));
      });
    }

    return out;
  }

  // =========================================================
  // Sort control helpers
  // =========================================================

  // ---------- Toggle sort direction or activate sort on a new key ----------
  function toggleSort(key) {
    if (state.sortKey === key) {
      state.sortDir = state.sortDir === 'asc' ? 'desc' : 'asc';
    } else {
      state.sortKey = key;
      state.sortDir = 'asc';
    }
  }

  // ---------- Explicitly set sort key and direction ----------
  function setSort(key, dir) {
    state.sortKey = key;
    state.sortDir = dir === 'desc' ? 'desc' : 'asc';
  }

  // =========================================================
  // Filter control helper
  // =========================================================

  // ---------- Set text filter value for a specific column ----------
  function setFilter(key, value) {
    state.filters[key] = value;
  }

  // =========================================================
  // Public API
  // =========================================================

  return {
    state,
    apply,
    toggleSort,
    setSort,
    setFilter,
  };
}
