// =========================================================
// Centralized API client for handling HTTP requests, response
// parsing, and consistent error handling across the app
// =========================================================

// site/src/api/client.js

// ---------- Core request wrapper used by all API methods ----------
async function request(method, path, body = null, opts = {}) {
  const headers = opts.headers ?? {};
  const init = { method, headers };

  // ---------- Configure request body and headers ----------
  if (body !== null) {
    if (body instanceof FormData) {
      init.body = body; // browser sets multipart boundary
    } else {
      init.headers = { ...headers, "Content-Type": "application/json" };
      init.body = JSON.stringify(body);
    }
  }

  // ---------- Execute fetch request ----------
  const res = await fetch(path, init);

  // ---------- Read response and safely parse JSON if present ----------
  const text = await res.text();
  const payload = text
    ? (() => {
        try {
          return JSON.parse(text);
        } catch {
          return { ok: false, error: { message: text || "Invalid JSON response" } };
        }
      })()
    : null;

  // ---------- Return early for HEAD requests (no response body expected) ----------
  if (method === "HEAD") return payload;

  // ---------- Normalize HTTP-level errors ----------
  if (!res.ok) {
    const msg =
      payload?.error?.message ||
      payload?.message ||
      payload?.error ||
      res.statusText ||
      "Request failed";
    throw new Error(`${res.status} ${msg}`);
  }

  // ---------- Handle API-level errors using response envelope ----------
  if (payload && payload.ok === false) {
    const msg = payload?.error?.message || "Request failed";
    throw new Error(msg);
  }

  // ---------- Extract and return data from standard API envelope ----------
  if (payload && Object.prototype.hasOwnProperty.call(payload, "data")) {
    return payload.data;
  }

  // ---------- Enforce API response contract ----------
  throw new Error("API response missing envelope");
}

// =========================================================
// Public API client exposing typed HTTP helpers
// =========================================================

export const apiClient = {
  // ---------- Standard CRUD operations ----------
  get: (path) => request("GET", path),
  post: (path, body) => request("POST", path, body),
  put: (path, body) => request("PUT", path, body),
  patch: (path, body) => request("PATCH", path, body),
  del: (path) => request("DELETE", path),

  // ---------- Resource existence check using HEAD ----------
  head: async (path) => {
    const res = await fetch(path, { method: "HEAD" });
    if (res.status === 404) return false;
    if (!res.ok) {
      const text = await res.text().catch(() => "");
      throw new Error(`${res.status} ${text || res.statusText}`);
    }
    return true;
  },
};
