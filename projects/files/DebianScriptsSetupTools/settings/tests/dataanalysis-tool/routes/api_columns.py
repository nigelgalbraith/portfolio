#!/usr/bin/env python3
import sys
import urllib.request
import json
import urllib.parse

BASE = "http://localhost:8080"
TIMEOUT = 5

def get_json(url: str):
    with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
        if r.status != 200:
            raise RuntimeError(f"HTTP {r.status}")
        return json.load(r)

try:
    dbs = get_json(f"{BASE}/api/databases")
    if not isinstance(dbs, list) or not dbs:
        print("[SKIP] No databases returned; skipping columns test")
        sys.exit(0)
    db_id = dbs[0].get("id", "")
    if not db_id:
        print(f"[FAIL] Database entry missing id: {dbs[0]}")
        sys.exit(1)
    db_enc = urllib.parse.quote(db_id, safe="")
    tables = get_json(f"{BASE}/api/databases/{db_enc}/tables")
    if not isinstance(tables, list) or not tables:
        print("[SKIP] No tables returned; skipping columns test")
        sys.exit(0)
    table_id = tables[0].get("id") if isinstance(tables[0], dict) else None
    table_name = table_id or (tables[0] if isinstance(tables[0], str) else "")
    if not table_name:
        print(f"[FAIL] Unexpected table entry shape: {tables[0]}")
        sys.exit(1)
    table_enc = urllib.parse.quote(table_name, safe="")
    url = f"{BASE}/api/databases/{db_enc}/tables/{table_enc}/columns"
    print(f"[CHECK] {url}")
    cols = get_json(url)
    if not isinstance(cols, list):
        print(f"[FAIL] Expected list, got {type(cols)}")
        sys.exit(1)
    print("[OK] Columns endpoint responds for first table")
    sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
