#!/usr/bin/env python3
import json
import urllib.parse
import urllib.request


# =================================================
# CONFIG
# =================================================

BASE = "http://localhost:8080"
TIMEOUT = 5


# =================================================
# CONTRACT CONSTANTS
# =================================================

EXPECTED_PAGES = [
    {"id": "database", "label": "Database Settings"},
    {"id": "relationships", "label": "Relationships"},
    {"id": "sumSet", "label": "Summary Settings"},
    {"id": "summary", "label": "Summary Table"},
    {"id": "dataEntry", "label": "Data Entry"},
]

EXPECTED_OPENAPI_PATHS = [
    "/api/pages",
    "/api/databases",
]


# =================================================
# HELPERS
# =================================================

def enc(value: str) -> str:
    """URL-encode a path segment."""
    return urllib.parse.quote(value, safe="")


def ok(msg: str):
    print(f"[OK]    {msg}")


def fail(msg: str):
    print(f"[FAIL]  {msg}")


def skip(msg: str):
    print(f"[SKIP]  {msg}")


# =================================================
# HTTP HELPERS
# =================================================

def fetch_json(url: str):
    """Fetch JSON from URL and return parsed object."""
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return json.load(r)


def unwrap_ok_payload(obj):
    """Unwrap ok_response-style payloads."""
    if isinstance(obj, dict):
        for k in ("data", "result", "payload"):
            if k in obj:
                return obj[k]
    return obj


# =================================================
# GETTERS
# =================================================

def get_databases():
    """Fetch list of databases."""
    url = f"{BASE}/api/databases"
    print(f"[CHECK] {url}")
    data = unwrap_ok_payload(fetch_json(url))
    if not isinstance(data, list):
        raise RuntimeError("Databases is not a list")
    return data


def get_tables(db_id: str):
    """Fetch tables for a given database."""
    url = f"{BASE}/api/databases/{enc(db_id)}/tables"
    print(f"[CHECK] {url}")
    data = unwrap_ok_payload(fetch_json(url))
    if not isinstance(data, list):
        raise RuntimeError("Tables is not a list")
    return data


def get_columns(db_id: str, table_id: str):
    """Fetch columns for a given database and table."""
    url = f"{BASE}/api/databases/{enc(db_id)}/tables/{enc(table_id)}/columns"
    print(f"[CHECK] {url}")
    data = unwrap_ok_payload(fetch_json(url))
    if not isinstance(data, list):
        raise RuntimeError("Columns is not a list")
    return data


# =================================================
# ROUTE CHECKS
# =================================================

def check_api_health():
    """Check /api/health endpoint."""
    url = f"{BASE}/api/health"
    print(f"[CHECK] {url}")
    data = unwrap_ok_payload(fetch_json(url))
    if not isinstance(data, dict) or data.get("ok") is not True:
        raise RuntimeError("API health not OK")


def check_openapi(expected_paths):
    """Verify OpenAPI document and required paths."""
    url = f"{BASE}/api/openapi.json"
    print(f"[CHECK] {url}")
    openapi_doc = fetch_json(url)
    if not isinstance(openapi_doc, dict):
        raise RuntimeError("OpenAPI is not a dict")
    paths = openapi_doc.get("paths")
    if not isinstance(paths, dict):
        raise RuntimeError("OpenAPI missing 'paths'")
    missing = [p for p in expected_paths if p not in paths]
    if missing:
        raise RuntimeError(f"Missing OpenAPI paths: {missing}")


def check_docs():
    """Check documentation endpoint."""
    url = f"{BASE}/api/docs"
    print(f"[CHECK] {url}")
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")


def check_pages(expected_pages):
    """Verify /api/pages returns required pages."""
    url = f"{BASE}/api/pages"
    print(f"[CHECK] {url}")
    pages = unwrap_ok_payload(fetch_json(url))
    if not isinstance(pages, list):
        raise RuntimeError("Pages is not a list")
    expected_ids = {p["id"] for p in expected_pages}
    actual_ids = {p.get("id") for p in pages if isinstance(p, dict)}
    missing = expected_ids - actual_ids
    extra = actual_ids - expected_ids
    if missing:
        raise RuntimeError(f"Missing pages: {sorted(missing)}")
    if extra:
        skip(f"Extra pages present: {sorted(extra)}")


def check_databases():
    """Validate databases endpoint and shape."""
    dbs = get_databases()
    if dbs and (not isinstance(dbs[0], dict) or "id" not in dbs[0]):
        raise RuntimeError("Database entry missing id")


def check_tables():
    """Validate tables endpoint and shape (using first db if present)."""
    dbs = get_databases()
    db_id = dbs[0].get("id") if dbs and isinstance(dbs[0], dict) else None
    if not db_id:
        skip("No database id; skipping tables")
        return
    tables = get_tables(db_id)
    if tables and not isinstance(tables[0], dict):
        raise RuntimeError("Table entry is not an object")


def check_columns():
    """Validate columns endpoint and shape (using first db + first table if present)."""
    dbs = get_databases()
    db_id = dbs[0].get("id") if dbs and isinstance(dbs[0], dict) else None
    if not db_id:
        skip("No database id; skipping columns")
        return
    tables = get_tables(db_id)
    table_id = tables[0].get("id") if tables and isinstance(tables[0], dict) else None
    if not table_id:
        skip("No table id; skipping columns")
        return
    cols = get_columns(db_id, table_id)
    if cols and not isinstance(cols[0], dict):
        raise RuntimeError("Column entry is not an object")


# =================================================
# MAIN RUNNER
# =================================================

def main() -> int:
    """Run route smoke tests."""
    all_ok = True
    checks = [
        ("api-health", check_api_health, []),
        ("openapi", check_openapi, [EXPECTED_OPENAPI_PATHS]),
        ("docs", check_docs, []),
        ("pages", check_pages, [EXPECTED_PAGES]),
        ("databases", check_databases, []),
        ("tables", check_tables, []),
        ("columns", check_columns, []),
    ]
    for label, fn, args in checks:
        try:
            fn(*args)
            ok(label)
        except Exception as e:
            fail(f"{label}: {e}")
            all_ok = False
    return 0 if all_ok else 1
    


if __name__ == "__main__":
    raise SystemExit(main())
