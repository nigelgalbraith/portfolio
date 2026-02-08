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
        print("[SKIP] No databases returned; skipping tables test")
        sys.exit(0)
    db_id = dbs[0].get("id", "")
    if not db_id:
        print(f"[FAIL] Database entry missing id: {dbs[0]}")
        sys.exit(1)
    db_enc = urllib.parse.quote(db_id, safe="")
    url = f"{BASE}/api/databases/{db_enc}/tables"
    print(f"[CHECK] {url}")
    tables = get_json(url)
    if not isinstance(tables, list):
        print(f"[FAIL] Expected list, got {type(tables)}")
        sys.exit(1)
    print("[OK] Tables endpoint responds for first database")
    sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
