#!/usr/bin/env python3
import sys
import urllib.request
import json

URL = "http://localhost:8080/api/pages"
TIMEOUT = 5

def unwrap_ok_payload(obj):
    if isinstance(obj, dict):
        if "data" in obj:
            return obj["data"]
        if "result" in obj:
            return obj["result"]
        if "payload" in obj:
            return obj["payload"]
    return obj

print(f"[CHECK] {URL}")

try:
    with urllib.request.urlopen(URL, timeout=TIMEOUT) as r:
        if r.status != 200:
            print(f"[FAIL] HTTP {r.status}")
            sys.exit(1)
        obj = json.load(r)
        data = unwrap_ok_payload(obj)
        if not isinstance(data, list):
            print(f"[FAIL] Expected list payload, got {type(data)}")
            sys.exit(1)
        if data and not isinstance(data[0], dict):
            print(f"[FAIL] Expected list of dicts, got {type(data[0])}")
            sys.exit(1)
        print("[OK] /api/pages responded with valid data")
        sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
