#!/usr/bin/env python3
"""Write the CI-owned `last_scan` field on a registry entry.

Only CI ever sets this (stamp on merge, and the weekly re-scan) -- which is why
validate_entry.py rejects a non-null `last_scan` on submission: a listing must not
be able to self-certify. Records {date, tools, status}, preserving the repo's
2-space + trailing-newline JSON style.

Usage:
    set_last_scan.py <entry.json> --status <status> [--tools a,b,c] [--date YYYY-MM-DD]
"""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--status", required=True)
    ap.add_argument("--tools", default="")
    ap.add_argument("--date", default="")
    args = ap.parse_args()

    path = Path(args.entry)
    data = json.loads(path.read_text())
    date = args.date or datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    tools = [t for t in args.tools.split(",") if t]
    data["last_scan"] = {"date": date, "tools": tools, "status": args.status}
    path.write_text(json.dumps(data, indent=2) + "\n")
    print(f"{path.name}: last_scan -> {data['last_scan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
