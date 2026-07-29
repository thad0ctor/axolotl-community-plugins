#!/usr/bin/env python3
"""Validate registry entries against the schema and the rules CI enforces.

Run on every PR before anything is fetched or executed. Fast, offline, no network.

Usage:
    python scripts/validate_entry.py [registry/plugins/foo.json ...]

With no arguments, validates every entry under registry/plugins/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError:  # pragma: no cover
    sys.exit("jsonschema is required: pip install jsonschema")

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = json.loads((ROOT / "registry" / "schema.json").read_text())
PLUGINS_DIR = ROOT / "registry" / "plugins"

# Fields a submitter may never set: CI writes them so a listing cannot self-certify.
_CI_OWNED = {"last_scan"}


def _entry_files(argv: list[str]) -> list[Path]:
    if argv:
        return [Path(a) for a in argv]
    return sorted(PLUGINS_DIR.glob("*.json"))


def validate_file(path: Path, allow_stamped: bool = False) -> list[str]:
    errors: list[str] = []
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{path.name}: invalid JSON: {exc}"]

    for err in jsonschema.Draft202012Validator(SCHEMA).iter_errors(data):
        loc = "/".join(str(p) for p in err.path) or "(root)"
        errors.append(f"{path.name}: {loc}: {err.message}")

    # Rules the schema cannot express.
    if data.get("name") and path.stem != data["name"]:
        errors.append(
            f"{path.name}: filename must match the `name` field ({data['name']}.json)."
        )
    # The CI-owned fields must be null in a *submission*; stamp/rescan operate on
    # already-stamped entries and pass --allow-stamped to exempt them.
    if not allow_stamped:
        for field in _CI_OWNED:
            if data.get(field) not in (None, {}, []):
                errors.append(
                    f"{path.name}: `{field}` is written by CI on merge; leave it null."
                )
    return errors


def main(argv: list[str]) -> int:
    allow_stamped = "--allow-stamped" in argv
    argv = [a for a in argv if a != "--allow-stamped"]

    errors: list[str] = []
    files = _entry_files(argv)
    if not files:
        print("No entries to validate.")
        return 0
    for path in files:
        errors.extend(validate_file(path, allow_stamped=allow_stamped))

    if errors:
        print("Registry validation FAILED:")
        for err in errors:
            print(f"  - {err}")
        return 1
    print(f"Validated {len(files)} entr{'y' if len(files) == 1 else 'ies'}: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
