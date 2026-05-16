#!/usr/bin/env python3
"""Feed a JSONL file of synthetic alerts to a running webhook service.

Usage:
    python scripts/replay_alerts.py path/to/zones.jsonl --url http://localhost:8080 --secret test-secret

JSONL format — one alert per line, matching AlertPayload fields:
    {"symbol":"CME_MINI:MNQ1!","tf":"240","event":"new_zone","id":"bar-100","direction":"long",
     "entry":20000.0,"sl":19995.0,"ts":1700000000,"secret":"<replaced>"}
"""

import argparse
import json
import sys
import time
from pathlib import Path

import httpx


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", type=Path)
    ap.add_argument("--url", default="http://localhost:8080")
    ap.add_argument("--secret", required=True)
    ap.add_argument("--delay", type=float, default=1.0)
    args = ap.parse_args()

    if not args.path.exists():
        print(f"error: {args.path} not found", file=sys.stderr)
        return 2

    with httpx.Client(timeout=10) as client:
        for line in args.path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            payload = json.loads(line)
            payload["secret"] = args.secret
            r = client.post(f"{args.url}/webhook/tradingview", json=payload)
            print(f"{payload.get('event')}/{payload.get('id')} → {r.status_code} {r.text}")
            time.sleep(args.delay)
    return 0


if __name__ == "__main__":
    sys.exit(main())
