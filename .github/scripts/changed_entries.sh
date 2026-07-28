#!/usr/bin/env bash
# Print the registry entry files a PR touched, one path per line.
#
# On a pull_request we diff the PR base against HEAD and keep only
# registry/plugins/*.json. If nothing under there changed (or we are not in a
# PR), fall back to every entry -- validating/scanning all of them is always safe
# and is what a manual/scheduled run wants.
#
# Fork-safe: uses only the checkout and the base SHA the event already gives us;
# no tokens, no API calls.
set -euo pipefail

base_sha="${1:-}"

list_all() {
  # Deterministic order; nothing to diff against.
  find registry/plugins -maxdepth 1 -name '*.json' | sort
}

if [[ -z "${base_sha}" ]]; then
  list_all
  exit 0
fi

# The base commit may not be in a shallow checkout; fetch it best-effort.
git fetch --no-tags --depth=1 origin "${base_sha}" >/dev/null 2>&1 || true

if ! git cat-file -e "${base_sha}^{commit}" 2>/dev/null; then
  # Base not reachable -> cannot compute a diff; scan everything rather than nothing.
  list_all
  exit 0
fi

changed="$(git diff --name-only "${base_sha}" HEAD -- 'registry/plugins/*.json' || true)"
if [[ -z "${changed}" ]]; then
  list_all
else
  printf '%s\n' "${changed}"
fi
