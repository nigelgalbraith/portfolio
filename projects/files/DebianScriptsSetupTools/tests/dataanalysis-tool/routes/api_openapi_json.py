#!/usr/bin/env python3
import sys
import urllib.request
import json

URL = "http://localhost:8080/api/openapi.json"
TIMEOUT = 5

print(f"[CHECK] {URL}")

try:
    with urllib.request.urlopen(URL, timeout=TIMEOUT) as r:
        if r.status != 200:
            print(f"[FAIL] HTTP {r.status}")
            sys.exit(1)
        data = json.load(r)
        if not isinstance(data, dict):
            print(f"[FAIL] Expected dict, got {type(data)}")
            sys.exit(1)
        if "paths" not in data:
            print(f"[FAIL] Missing 'paths' in openapi.json")
            sys.exit(1)
        print("[OK] OpenAPI JSON is present")
        sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
