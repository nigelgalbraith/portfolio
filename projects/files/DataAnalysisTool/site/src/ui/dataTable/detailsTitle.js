// =========================================================
// Details title helper: generates a human-friendly title for
// the row details modal using common identifier fields
// =========================================================

// site/src/ui/table/detailsTitle.js

// =========================================================
// Title selection logic
// =========================================================

// ---------- Pick a suitable identifier from the row for display ----------
export function pickDetailsTitle(row, idx) {
  const key =
    row?.id ??
    row?.ID ??
    row?.name ??
    row?.Name ??
    row?.title ??
    row?.Title ??
    row?.uuid ??
    row?.UUID;

  // ---------- Prefer a meaningful identifier; fall back to row index ----------
  return key ? `Details: ${key}` : `Row ${idx + 1} Details`;
}
