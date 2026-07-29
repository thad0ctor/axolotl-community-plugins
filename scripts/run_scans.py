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
import json
import shutil
import subprocess  # nosec: fixed tool argv over a local checkout
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEMGREP_RULES = ROOT / "rules" / "semgrep"

sys.path.insert(0, str(ROOT / "scripts"))
from check_capabilities import check as capability_violations  # noqa: E402

HARD_FAIL = {"guarddog", "gitleaks", "capabilities"}


def _have(tool: str) -> bool:
    return shutil.which(tool) is not None


def _run(cmd: list[str]) -> int:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.run(cmd, check=False).returncode  # nosec


def scan(source: Path, entry: dict | None = None) -> int:
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
        # --no-git-ignore: a committed .gitignore/.semgrepignore must not let an author
        # hide a file from semgrep that pip will still install.
        record("semgrep", _run(["semgrep", "--error", "--no-git-ignore", "--config", str(SEMGREP_RULES), str(source)]), True)
    else:
        record("semgrep", 1, False)
    record("guarddog", _run(["guarddog", "pypi", "scan", str(source)]) if _have("guarddog") else 1, _have("guarddog"))

    # pip-audit only audits an explicit requirements list here; pyproject/setup deps are
    # resolved and audited in the sandbox install stage. Record SKIP (not pass) when it
    # did not run, so an unaudited plugin never reads as clean.
    if not _have("pip-audit"):
        results["pip-audit"] = "MISSING (not installed on this runner)"
    elif (source / "requirements.txt").exists():
        record("pip-audit", _run(["pip-audit", "-r", str(source / "requirements.txt")]), True)
    else:
        results["pip-audit"] = "SKIP (no requirements.txt; deps audited in sandbox)"

    record("gitleaks", _run(["gitleaks", "detect", "--no-git", "-s", str(source)]) if _have("gitleaks") else 1, _have("gitleaks"))

    # Capability check is pure-Python (AST only), so it always runs when we have an entry.
    if entry is not None:
        violations = capability_violations(entry, source)
        if violations:
            for v in violations:
                print(f"  capability: {v}")
        results["capabilities"] = "FAIL" if violations else "pass"

    print("\nScan summary:")
    failed = []
    for tool, status in results.items():
        print(f"  {tool:12} {status}")
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
    ap.add_argument("--entry", default=None, help="Path to the registry entry JSON (enables the capability check)")
    args = ap.parse_args()
    entry = json.loads(Path(args.entry).read_text()) if args.entry else None
    return scan(Path(args.source), entry)


if __name__ == "__main__":
    raise SystemExit(main())
