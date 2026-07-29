#!/usr/bin/env python3
"""Prove the scan wall still detects, after a scanner install/version change.

Runs run_scans.py against two fixtures:
  - benign   -> the wall must PASS (exit 0), and no layer may report FAIL.
  - malicious -> the wall must FAIL, and every layer we expect to catch it must
                 report FAIL (so a single scanner silently ceasing to detect is caught,
                 not masked by another scanner still tripping).

This is what makes automated dependency bumps safe: a bump that breaks a scanner's CLI,
its exit code, or (guarddog<->semgrep) its rule engine turns a real detection into a
silent pass, which a benign-only test would miss. Run in CI on any scanner change and
weekly.
"""

from __future__ import annotations

import subprocess  # nosec: fixed argv over in-repo paths
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES = ROOT / ".github" / "scanners" / "fixtures"
RUN_SCANS = ROOT / "scripts" / "run_scans.py"

# Layers the malicious fixture is built to trip. gitleaks needs its binary; if the
# runner could not install it, run_scans already hard-fails on MISSING, so the wall
# still fails closed -- we assert on the layers that are present.
EXPECT_MALICIOUS_FAIL = ["bandit", "semgrep", "guarddog"]


def _run_wall(target: Path) -> tuple[int, str]:
    proc = subprocess.run(  # nosec
        [sys.executable, str(RUN_SCANS), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout + proc.stderr


def _layer_failed(output: str, layer: str) -> bool:
    for line in output.splitlines():
        stripped = line.strip()
        if stripped.startswith(layer) and "FAIL" in stripped:
            return True
    return False


def main() -> int:
    problems: list[str] = []

    benign_rc, benign_out = _run_wall(FIXTURES / "benign")
    print("=== benign fixture ===\n" + benign_out)
    if benign_rc != 0:
        problems.append("benign fixture did not pass the scan wall (false positive)")

    mal_rc, mal_out = _run_wall(FIXTURES / "malicious")
    print("=== malicious fixture ===\n" + mal_out)
    if mal_rc == 0:
        problems.append("malicious fixture PASSED the scan wall (detection is broken)")
    for layer in EXPECT_MALICIOUS_FAIL:
        if f"{layer} " in mal_out and not _layer_failed(mal_out, layer):
            problems.append(f"{layer} did not flag the malicious fixture")

    if problems:
        print("\nSCANNER SELF-TEST FAILED:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nScanner self-test passed: wall is quiet on benign, loud on malicious.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
