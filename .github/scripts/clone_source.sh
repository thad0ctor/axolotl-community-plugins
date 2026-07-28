#!/usr/bin/env bash
# Clone ONE registry entry's plugin source at its pinned SHA into <dest>.
#
# Used by the static scan wall. This only fetches the *source tree*; it never
# installs or imports anything, so no plugin code runs here. The pinned 40-char
# SHA (schema-enforced) means the tree we scan is exactly the tree that was
# reviewed -- an entry can never point at a moving branch.
#
# Usage:   clone_source.sh <entry.json> <dest_dir>
# Prints:  the directory to scan (dest, or dest/<subdir>) on stdout; logs to stderr.
set -euo pipefail

entry="${1:?entry json path required}"
dest="${2:?destination dir required}"

read -r source ref subdir < <(python3 - "$entry" <<'PY'
import json, sys
e = json.load(open(sys.argv[1]))
print(e["source"], e["ref"], e.get("subdir") or "-")
PY
)

echo "cloning ${source} @ ${ref}" >&2
# Full clone + checkout: a pinned SHA is often not a branch tip, so a --depth 1
# clone of the default branch would not contain it.
git clone --quiet -- "${source}" "${dest}" >&2
git -C "${dest}" checkout --quiet "${ref}" -- >&2

scan_dir="${dest}"
if [[ "${subdir}" != "-" ]]; then
  scan_dir="${dest}/${subdir}"
fi
echo "${scan_dir}"
