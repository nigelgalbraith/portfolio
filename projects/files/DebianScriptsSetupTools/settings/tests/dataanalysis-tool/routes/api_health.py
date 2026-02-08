#!/usr/bin/env python3
import sys
import urllib.request
import json

URL = "http://localhost:8080/api/health"
TIMEOUT = 5

print(f"[CHECK] {URL}")

try:
    with urllib.request.urlopen(URL, timeout=TIMEOUT) as r:
        if r.status != 200:
            print(f"[FAIL] HTTP {r.status}")
            sys.exit(1)

        data = json.load(r)

        if not isinstance(data, dict) or data.get("ok") is not True:
            print(f"[FAIL] Unexpected response: {data}")
            sys.exit(1)

        print("[OK] API health check passed")
        sys.exit(0)

except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
