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
python3 -m pip install "bandit==1.7.9" "semgrep==1.86.0" "pip-audit==2.7.3" "guarddog==1.13.0"
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
