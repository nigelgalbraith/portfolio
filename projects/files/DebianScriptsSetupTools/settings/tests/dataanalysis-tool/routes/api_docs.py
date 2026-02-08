#!/usr/bin/env python3
import sys
import urllib.request

URL = "http://localhost:8080/api/docs"
TIMEOUT = 5

print(f"[CHECK] {URL}")

try:
    with urllib.request.urlopen(URL, timeout=TIMEOUT) as r:
        if r.status != 200:
            print(f"[FAIL] HTTP {r.status}")
            sys.exit(1)
        print("[OK] Docs endpoint responds")
        sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
