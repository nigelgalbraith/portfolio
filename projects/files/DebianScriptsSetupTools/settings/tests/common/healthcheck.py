#!/usr/bin/env python3
import sys
import urllib.request

URL = "http://localhost:8080"
TIMEOUT = 5

print(f"[CHECK] Hitting {URL}")

try:
    with urllib.request.urlopen(URL, timeout=TIMEOUT) as r:
        if r.status == 200:
            print("[OK] Service is responding")
            sys.exit(0)
        print(f"[FAIL] Status {r.status}")
        sys.exit(1)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
