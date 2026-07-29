#!/usr/bin/env bash
# Install the static scan-wall tools onto the runner.
#
# run_scans.py deliberately treats a MISSING tool as a failure (guarddog and
# gitleaks are hard gates), so a scanner that silently fails to install can never
# be mistaken for a clean scan. We still let a genuine install failure through to
# run_scans.py rather than aborting here, so its report names exactly what is
# missing.
#
# pip tools: bandit, semgrep, pip-audit, guarddog.
# gitleaks:  released static binary (not on PyPI).
set -uo pipefail

GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.18.4}"

echo "::group::pip scanners"
python3 -m pip install --upgrade pip
# Versions live in .github/scanners/requirements.txt (Dependabot bumps them there).
# Install each line independently: one scanner that fails to resolve must not take the
# others down with it (a single bundled install means one bad pin => all MISSING).
# run_scans.py reports whatever ended up unavailable and hard-fails on the hard gates.
req="$(dirname "$0")/../scanners/requirements.txt"
grep -vE '^\s*(#|$)' "$req" | while read -r pkg; do
  python3 -m pip install "$pkg" || echo "::warning::${pkg} failed to install"
done
echo "::endgroup::"

echo "::group::gitleaks ${GITLEAKS_VERSION}"
tmp="$(mktemp -d)"
url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_x64.tar.gz"
if curl -fsSL "${url}" -o "${tmp}/gitleaks.tar.gz"; then
  tar -xzf "${tmp}/gitleaks.tar.gz" -C "${tmp}" gitleaks
  sudo install -m 0755 "${tmp}/gitleaks" /usr/local/bin/gitleaks
  gitleaks version
else
  # Leave it uninstalled; run_scans.py will report gitleaks MISSING and hard-fail,
  # which is the correct outcome -- a secrets scan that could not run is not a pass.
  echo "WARNING: could not download gitleaks; run_scans.py will hard-fail on it." >&2
fi
echo "::endgroup::"
