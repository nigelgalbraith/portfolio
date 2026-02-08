// ==================================================
// Identifier validation
// ==================================================

const ID_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;

function isValidIdentifier(str) {
  return ID_RE.test(str || '');
}

// ==================================================
// ID normalization
// ==================================================

/**
 * Normalize user input into a safe identifier
 * and optionally derive a filename.
 */
export function normalizeId(raw, opts = {}) {
  const {
    type = 'id',               // 'db' | 'table' | 'column' | 'config'
    stripJsonExtension = true,
    makeFilename = false,
  } = opts;

  const s = (raw || '').trim();
  if (!s) return { ok: false, error: 'Enter a name.' };

  let base = s;

  if (stripJsonExtension && base.toLowerCase().endsWith('.json')) {
    base = base.slice(0, -5);
  }

  if (!isValidIdentifier(base)) {
    const label =
      type === 'db' ? 'database name' :
      type === 'table' ? 'table name' :
      type === 'column' ? 'column name' :
      type === 'config' ? 'config name' :
      'name';

    return {
      ok: false,
      error: `Invalid ${label}. Use letters/numbers/underscore, and don’t start with a number.`,
    };
  }

  const out = { ok: true, id: base };

  if (makeFilename) {
    out.filename = `${base}.json`;
  }

  return out;
}
