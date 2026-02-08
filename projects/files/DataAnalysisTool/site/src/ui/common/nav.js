// ==================================================
// Navigation Rendering
// ==================================================

/**
 * Build the top navigation bar from the page registry returned by the API.
 * All pages returned by /api/pages are shown in the nav.
 */
export function renderNav(navListEl, pages, { dbId, activeRouteId }) {
  if (!navListEl) return;
  if (!Array.isArray(pages)) return;

  // -----------------------------
  // Reset
  // -----------------------------
  navListEl.innerHTML = '';

  // -----------------------------
  // Render page links
  // -----------------------------
  for (const p of pages) {
    if (!p || !p.id) continue;

    const li = document.createElement('li');
    const a = document.createElement('a');

    const hrefDb = dbId ? `?db=${encodeURIComponent(dbId)}` : '';
    a.href = `${hrefDb}#/${encodeURIComponent(p.id)}`;
    a.textContent = p.label || p.id;

    if (p.id === activeRouteId) {
      a.classList.add('active');
    }

    li.appendChild(a);
    navListEl.appendChild(li);
  }
}
