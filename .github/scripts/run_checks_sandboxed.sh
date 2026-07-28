#!/usr/bin/env bash
# Run ONE entry's author-provided checks against a real axolotl, with the
# untrusted check code executing under a network-disabled namespace.
#
# run_plugin_checks.py is staged, so the network split is clean:
#   * fetch,install,smoke -- needs the network (clone + pip install + import).
#     Safe here: this only runs after the static scan wall passed.
#   * checks              -- the schema promises this runs with the network
#     DISABLED, so we run it under `unshare --net` (loopback only, no egress).
# Both invocations share one persistent --workdir, so the checks run against the
# checkout the networked stages already installed.
#
# Never invoke this on an unvetted entry outside CI: it executes the plugin's
# build backend and its tests.
#
# Usage: run_checks_sandboxed.sh <entry.json>
set -euo pipefail

entry="${1:?entry json path required}"
workdir="$(mktemp -d)"

echo "::group::fetch + install + smoke (network on)"
python3 scripts/run_plugin_checks.py "${entry}" --workdir "${workdir}" \
  --stages fetch,install,smoke
echo "::endgroup::"

echo "::group::author checks (network disabled)"
if unshare --map-root-user --net -- true 2>/dev/null; then
  echo "Running author checks under unshare -rn (network disabled)."
  # New user+network namespace: only loopback (brought up for checks that bind
  # 127.0.0.1); there is no route off the box. --map-root-user is what lets an
  # unprivileged runner create the namespace at all.
  unshare --map-root-user --net -- bash -c '
    ip link set lo up 2>/dev/null || true
    exec python3 scripts/run_plugin_checks.py "$1" --workdir "$2" --stages checks
  ' _ "${entry}" "${workdir}"
else
  # TODO(hardening): this runner does not permit unprivileged user+net
  # namespaces, so the author checks run WITH network reachable. The scan wall
  # still gated this, deps are pinned, and no secrets are exposed (read-only,
  # fork PR), but egress during the checks is the residual gap. A rootless
  # container with `--network none`, or a runner that allows `unshare -rn`,
  # closes it. We do NOT silently skip the checks.
  echo "::warning::unshare -rn unavailable; running author checks WITH network (see TODO(hardening) in run_checks_sandboxed.sh)."
  python3 scripts/run_plugin_checks.py "${entry}" --workdir "${workdir}" --stages checks
fi
echo "::endgroup::"
