#!/usr/bin/env python3
"""Regenerate registry/index.json from the entry files.

The index is the flat list of names the client fetches first, so it can then pull each
entry by name. Kept in the repo (not computed by the client) so a client release resolves
against a fixed snapshot. CI checks it is up to date with `--check`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PLUGINS_DIR = ROOT / "registry" / "plugins"
INDEX = ROOT / "registry" / "index.json"


def build() -> dict:
    names = sorted(p.stem for p in PLUGINS_DIR.glob("*.json"))
    return {"plugins": names}


def main(argv: list[str]) -> int:
    content = json.dumps(build(), indent=2) + "\n"
    if "--check" in argv:
        current = INDEX.read_text() if INDEX.exists() else ""
        if current != content:
            print("registry/index.json is out of date; run scripts/build_index.py")
            return 1
        print("registry/index.json is up to date")
        return 0
    INDEX.write_text(content)
    print(f"Wrote {INDEX.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
