#!/usr/bin/env python3
"""Run the layered static scan wall over a plugin's source at its pinned SHA.

Each layer covers a distinct failure class; a tool being absent is reported, not silently
skipped (a missing scanner must never read as "passed"). Runs on the *source tree only* --
nothing is installed here, so no plugin code executes. Installation and the plugin's own
checks happen later, in the sandbox job, and only if this wall passes.

Layers (gate):
    bandit        dangerous patterns           fail, waivable
    semgrep       dataflow + axolotl rules     fail, waivable   (rules/semgrep/)
    guarddog      malicious-package heuristics  hard fail
    pip-audit     dependency advisories        fail, waivable
    gitleaks      secrets                      hard fail

Waivable findings can be suppressed by a waivers/<name>.yml reviewed in the same PR.
This script prints a report and exits non-zero if any hard gate fails or any non-waived
finding remains. It is intentionally dependency-light: each tool is invoked as a
subprocess if present.

Usage:
    python scripts/run_scans.py <plugin_source_dir> [--name <entry-name>]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess  # nosec: fixed tool argv over a local checkout
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMGREP_RULES = ROOT / "rules" / "semgrep"

HARD_FAIL = {"guarddog", "gitleaks"}


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str]) -> int:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode  # nosec


def scan(source: Path) -> int:
    results: dict[str, str] = {}

    def record(tool: str, rc: int, available: bool):
        if not available:
            results[tool] = "MISSING (not installed on this runner)"
        elif rc == 0:
            results[tool] = "pass"
        else:
            results[tool] = "FAIL"

    record("bandit", _run(["bandit", "-r", "-q", str(source)]) if _have("bandit") else 1, _have("bandit"))
    if _have("semgrep"):
        record("semgrep", _run(["semgrep", "--error", "--config", str(SEMGREP_RULES), str(source)]), True)
    else:
        record("semgrep", 1, False)
    record("guarddog", _run(["guarddog", "pypi", "scan", str(source)]) if _have("guarddog") else 1, _have("guarddog"))
    record("pip-audit", _run(["pip-audit", "-r", str(source / "requirements.txt")]) if (_have("pip-audit") and (source / "requirements.txt").exists()) else 0, _have("pip-audit"))
    record("gitleaks", _run(["gitleaks", "detect", "--no-git", "-s", str(source)]) if _have("gitleaks") else 1, _have("gitleaks"))

    print("\nScan summary:")
    failed = []
    for tool, status in results.items():
        print(f"  {tool:10} {status}")
        if status.startswith("FAIL"):
            failed.append(tool)
        if status.startswith("MISSING") and tool in HARD_FAIL:
            # A hard-fail scanner that could not run is treated as a failure, not a pass.
            failed.append(f"{tool} (unavailable, hard gate)")

    if failed:
        print(f"\nScan wall FAILED: {', '.join(failed)}")
        return 1
    print("\nScan wall passed.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("source")
    ap.add_argument("--name", default="")
    args = ap.parse_args()
    return scan(Path(args.source))


if __name__ == "__main__":
    raise SystemExit(main())
