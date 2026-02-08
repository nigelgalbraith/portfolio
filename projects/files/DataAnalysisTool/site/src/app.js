// =========================================================
// App bootstrap + router: loads available pages from server,
// renders nav, mounts/unmounts page modules on hash changes,
// and treats URL params (db/table/pk/etc.) as the canonical
// source of truth for navigation + selection state
// =========================================================

import { apiClient } from './api/client.js';
import { pagesApi } from './api/pages.js';
import { getDbFromUrl, setSearchParams } from './app/urlState.js';

// =========================================================
// State (declare ONCE)
// =========================================================
let currentPage = null;
let currentPageId = null;
let pagesCache = [];

// =========================================================
// DOM
// =========================================================
const els = {
  title: document.getElementById('app-title'),
  nav: document.getElementById('nav-list'),
  app: document.getElementById('app'),
};

// =========================================================
// URL helpers (URL is canonical)
// =========================================================

function setDbInUrl(dbId, opts = {}) {
  const next = (dbId || '').trim();

  // Replace so we don't spam history just because db changed
  setSearchParams({ db: next || '' });

  // Default: do NOT remount. Some pages (e.g. Summary) keep local state that we
  // don't want to blow away just because db in the URL changed.
  const shouldRemount = !!opts.remount;
  if (!shouldRemount) return;

  // Remount current page so everything re-renders against the new db
  if (currentPageId) {
    mountPage(currentPageId).catch(e => {
      console.error(e);
      setStatus(`Error: ${e.message}`);
    });
    return;
  }

  // If we somehow don't have a mounted page yet, fall back to routing
  onRouteChange().catch(e => {
    console.error(e);
    setStatus(`Error: ${e.message}`);
  });
}

function getRouteId() {
  const hash = (window.location.hash || '').trim();
  const cleaned = hash.replace(/^#\/?/, '');
  const [routeOnly] = cleaned.split('?');
  return routeOnly || '';
}

function setRouteId(pageId) {
  window.location.hash = `#/${pageId}`;
}

// =========================================================
// UI helpers
// =========================================================
function clear(el) {
  el.innerHTML = '';
}

function setStatus(msg) {
  if (els.title) els.title.textContent = msg ? `Data Analysis — ${msg}` : 'Data Analysis';
}

function renderNav(pages, activeId) {
  clear(els.nav);

  for (const p of pages) {
    const li = document.createElement('li');

    const a = document.createElement('a');
    a.href = `#/${p.id}`;
    a.textContent = p.label || p.id;
    if (p.id === activeId) a.className = 'active';

    li.appendChild(a);
    els.nav.appendChild(li);
  }
}

// =========================================================
// Page mounting
// =========================================================
async function unmountCurrent() {
  if (currentPage && typeof currentPage.unmount === 'function') {
    try { currentPage.unmount(); } catch (_) {}
  }
  currentPage = null;
  currentPageId = null;
}

async function importWithRetry(path, retries = 1) {
  try {
    return await import(path);
  } catch (e) {
    // Firefox often throws on aborted module fetches; retry once
    if (retries > 0) return importWithRetry(path, retries - 1);
    throw e;
  }
}

async function mountPage(pageId) {
  const pageMeta = pagesCache.find(p => p && p.id === pageId);
  if (!pageMeta) throw new Error(`Unknown page: ${pageId}`);

  await unmountCurrent();

  renderNav(pagesCache, pageId);
  clear(els.app);

  const mod = await importWithRetry(pageMeta.module);
  if (!mod || typeof mod.createPage !== 'function') {
    throw new Error(`Page module missing createPage(): ${pageMeta.module}`);
  }

  const page = mod.createPage();
  if (!page || typeof page.mount !== 'function') {
    throw new Error(`createPage() did not return a mountable page: ${pageMeta.id}`);
  }

  if (page.id && page.id !== pageMeta.id) {
    console.warn(
      `Page id mismatch: module returned "${page.id}" but server expects "${pageMeta.id}". Module: ${pageMeta.module}`
    );
  }

  currentPage = page;
  currentPageId = pageId;

  const dbId = getDbFromUrl();
  const label = pageMeta.label || pageMeta.id;

  // Header status: include db if present, otherwise prompt
  if (dbId) setStatus(`${label} — ${dbId}`);
  else setStatus(`${label} — Select a database`);

  await page.mount({
    rootEl: els.app,
    apiClient,
    dbId,
    setDbInUrl,
    setHeaderTitle: (t) => {
      if (els.title) els.title.textContent = t ? String(t) : 'Data Analysis';
    }
  });
}

async function onRouteChange() {
  const routeId = getRouteId();
  const target = routeId || (pagesCache[0] ? pagesCache[0].id : '');
  if (!target) throw new Error('No pages available.');
  if (!routeId) setRouteId(target);
  await mountPage(target);
}

// =========================================================
// Init (define ONCE)
// =========================================================
async function init() {
  try {
    setStatus('Loading…');

    pagesCache = await pagesApi.list();
    if (!Array.isArray(pagesCache) || pagesCache.length === 0) {
      throw new Error('No pages returned from /api/pages.');
    }

    await onRouteChange();

    window.addEventListener('hashchange', () => {
      onRouteChange().catch(e => {
        console.error(e);
        setStatus(`Error: ${e.message}`);
      });
    });

    // NOTE: We intentionally do NOT read/write db from anywhere except the URL.
    // Pages must call setDbInUrl(dbId) when the user selects a database.

  } catch (e) {
    console.error(e);
    setStatus(`Error: ${e.message}`);
    clear(els.app);
    els.app.textContent = `Init failed: ${e.message}`;
  }
}

init();
