#!/usr/bin/env python3
import sys
import urllib.request
import json

URL = "http://localhost:8080/api/databases"
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
        if data:
            first = data[0]
            if not isinstance(first, dict):
                print(f"[FAIL] Expected dict entries, got {type(first)}")
                sys.exit(1)
            if "id" not in first or "label" not in first:
                print(f"[FAIL] Missing keys in first entry: {first}")
                sys.exit(1)
        print("[OK] /api/databases responded with valid data")
        sys.exit(0)
except Exception as e:
    print(f"[FAIL] {e}")
    sys.exit(1)
