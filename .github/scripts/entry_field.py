#!/usr/bin/env python3
"""Print one (optionally dotted) field from a registry entry; empty line if absent.

A tiny read helper so workflow steps don't each embed their own JSON parsing.

Usage:  entry_field.py <entry.json> <dotted.path>
Example: entry_field.py registry/plugins/foo.json last_scan.status
"""

from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: entry_field.py <entry.json> <dotted.path>", file=sys.stderr)
        return 2
    cur = json.load(open(sys.argv[1]))
    for part in sys.argv[2].split("."):
        if isinstance(cur, dict) and cur.get(part) is not None:
            cur = cur[part]
        else:
            cur = ""
            break
    print(cur if not isinstance(cur, (dict, list)) else json.dumps(cur))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
