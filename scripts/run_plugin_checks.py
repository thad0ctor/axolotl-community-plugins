#!/usr/bin/env python3
"""Run a plugin's own author-provided checks, inside the sandbox, against a real axolotl.

This is what the generic scanners cannot do: prove that *this* plugin's hooks actually
fire. Each registry entry declares `checks:` (e.g. `pytest tests/test_hooks.py`); this
runner clones the plugin at the pinned SHA, installs it, imports the class to confirm it
is a BasePlugin, then runs each declared check with the plugin repo as the working
directory. A non-zero exit -- or a check reaching the network -- fails the submission.

Runs in stages so CI can isolate the network:

    --stages fetch,install,smoke   # with network, to clone + pip install + smoke import
    --stages checks                # with network DISABLED, to run the author checks

Pass a persistent ``--workdir`` to share the checkout between the two invocations. With
no ``--stages`` it runs all of them in one temp dir (fine for local use, not for a
network-isolated CI split). Never run this on an unvetted entry outside a sandbox: it
executes the plugin's build backend and its tests.

Usage:
    python scripts/run_plugin_checks.py registry/plugins/<name>.json [--workdir DIR] [--stages ...]
"""

from __future__ import annotations

import argparse
import json
import subprocess  # nosec: commands come from a schema-validated entry, run in a sandbox
import sys
import tempfile
from pathlib import Path

ALL_STAGES = ("fetch", "install", "smoke", "checks")


def _run(cmd: list[str], cwd: Path | None = None, timeout: int | None = None) -> int:
    print(f"    $ {' '.join(cmd)}", flush=True)
    try:
        return subprocess.run(  # nosec
            cmd, cwd=str(cwd) if cwd else None, timeout=timeout, check=False
        ).returncode
    except subprocess.TimeoutExpired:
        print(f"    TIMEOUT after {timeout}s")
        return 124


def _checkout_dir(workdir: Path) -> Path:
    return workdir / "plugin"


def _root(entry: dict, workdir: Path) -> Path:
    checkout = _checkout_dir(workdir)
    return checkout / entry["subdir"] if entry.get("subdir") else checkout


def stage_fetch(entry: dict, workdir: Path) -> int:
    checkout = _checkout_dir(workdir)
    name, source, ref = entry["name"], entry["source"], entry["ref"]
    print(f"[{name}] clone {source} @ {ref}")
    # Full clone, then check out the exact SHA. A shallow clone cannot reach a pinned
    # commit that is not the default-branch tip, which is precisely the common case.
    if _run(["git", "clone", "--", source, str(checkout)]):
        print(f"[{name}] FAIL: could not clone source")
        return 1
    if _run(["git", "checkout", ref, "--"], cwd=checkout):
        print(f"[{name}] FAIL: ref {ref} not found in source")
        return 1
    return 0


def stage_install(entry: dict, workdir: Path) -> int:
    print(f"[{entry['name']}] install")
    if _run([sys.executable, "-m", "pip", "install", str(_root(entry, workdir))]):
        print(f"[{entry['name']}] FAIL: pip install failed")
        return 1
    return 0


def stage_smoke(entry: dict, workdir: Path) -> int:
    print(f"[{entry['name']}] smoke: import class(es), confirm BasePlugin subclass")
    for cls_path in entry["cls"]:
        module, _, attr = cls_path.rpartition(".")
        code = (
            "import importlib; from axolotl.integrations.base import BasePlugin; "
            f"obj = getattr(importlib.import_module({module!r}), {attr!r}); "
            f"assert isinstance(obj, type) and issubclass(obj, BasePlugin), "
            f"{cls_path!r} + ' is not a BasePlugin subclass'"
        )
        if _run([sys.executable, "-c", code]):
            print(f"[{entry['name']}] FAIL: smoke check for {cls_path}")
            return 1
    return 0


def stage_checks(entry: dict, workdir: Path) -> int:
    root = _root(entry, workdir)
    for check in entry["checks"]:
        print(f"[{entry['name']}] check: {check['name']}")
        rc = _run(
            ["bash", "-lc", check["run"]],
            cwd=root,
            timeout=check.get("timeout_seconds", 300),
        )
        if rc != 0:
            print(f"[{entry['name']}] FAIL: check {check['name']!r} exited {rc}")
            return 1
    return 0


_STAGE_FUNCS = {
    "fetch": stage_fetch,
    "install": stage_install,
    "smoke": stage_smoke,
    "checks": stage_checks,
}


def run(entry_path: Path, workdir: Path, stages: tuple[str, ...]) -> int:
    entry = json.loads(entry_path.read_text())
    for stage in stages:
        rc = _STAGE_FUNCS[stage](entry, workdir)
        if rc != 0:
            return rc
    if set(stages) == set(ALL_STAGES):
        print(f"[{entry['name']}] all checks passed")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("entry")
    ap.add_argument("--workdir", default=None, help="Persistent dir shared across stages")
    ap.add_argument(
        "--stages",
        default=",".join(ALL_STAGES),
        help=f"Comma-separated subset of: {', '.join(ALL_STAGES)}",
    )
    args = ap.parse_args()

    stages = tuple(s.strip() for s in args.stages.split(",") if s.strip())
    bad = [s for s in stages if s not in _STAGE_FUNCS]
    if bad:
        print(f"Unknown stage(s): {', '.join(bad)}")
        return 2

    entry_path = Path(args.entry)
    if args.workdir:
        workdir = Path(args.workdir)
        workdir.mkdir(parents=True, exist_ok=True)
        return run(entry_path, workdir, stages)
    with tempfile.TemporaryDirectory() as tmp:
        return run(entry_path, Path(tmp), stages)


if __name__ == "__main__":
    raise SystemExit(main())
