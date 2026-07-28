#!/usr/bin/env python3
"""Print the axolotl version to install for a set of entries: the highest
`min_axolotl_version` among them, or an empty line if none declare one (install
latest).

Usage:  axolotl_pin.py <entry.json> [<entry.json> ...]
"""

from __future__ import annotations

import json
import sys


def _key(version: str) -> list[int]:
    out: list[int] = []
    for part in version.split("."):
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        out.append(int(num) if num else 0)
    return out


def main(paths: list[str]) -> int:
    best = ""
    for path in paths:
        version = json.load(open(path)).get("min_axolotl_version")
        if version and (not best or _key(version) > _key(best)):
            best = version
    print(best)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
