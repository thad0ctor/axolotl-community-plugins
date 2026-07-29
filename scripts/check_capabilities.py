#!/usr/bin/env python3
"""Enforce that a plugin's declared `capabilities` cover the hooks its code overrides.

Static (AST-only, no execution): finds classes that subclass ``BasePlugin`` and maps the
BasePlugin hook methods they override to capability tokens. If the code hooks a surface
the entry did not declare, the submission fails -- so the `capabilities` array is a real
statement about what the plugin does, not a self-asserted label.

Best-effort by construction: an AST cannot see dynamically-injected methods or
monkeypatching. It catches honest under-declaration and the obvious dishonest case; it is
one layer, not a proof. `cli_commands` is declared via packaging entry points, not a
BasePlugin hook, so it is not inferred here.

Usage:
    python scripts/check_capabilities.py registry/plugins/<name>.json <plugin_source_dir>
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

# BasePlugin hook method -> the capability token overriding it implies.
# Sourced from axolotl.integrations.base.BasePlugin.
HOOK_CAPABILITY = {
    "get_input_args": "config_args",
    "get_training_args_mixin": "config_args",
    "get_training_args": "config_args",
    "get_lora_config_kwargs": "config_args",
    "add_callbacks_pre_trainer": "callbacks",
    "add_callbacks_post_trainer": "callbacks",
    "post_train": "callbacks",
    "post_train_unload": "callbacks",
    "pre_model_load": "model_patches",
    "post_model_build": "model_patches",
    "pre_lora_load": "model_patches",
    "post_lora_load": "model_patches",
    "post_model_load": "model_patches",
    "get_adapter_capabilities": "model_patches",
    "get_trainer_cls": "trainers",
    "post_trainer_create": "trainers",
    "create_optimizer": "trainers",
    "create_lr_scheduler": "trainers",
    "get_collator_cls_and_kwargs": "datasets",
}

_SKIP_DIRS = {"tests", "test", "docs", "examples", "build", "dist", ".git"}


def _is_baseplugin_subclass(node: ast.ClassDef) -> bool:
    for base in node.bases:
        name = base.id if isinstance(base, ast.Name) else getattr(base, "attr", None)
        if name == "BasePlugin":
            return True
    return False


def required_capabilities(source_dir: Path) -> dict[str, set[str]]:
    """Map each capability the code hooks to the set of hook methods that imply it."""
    needed: dict[str, set[str]] = {}
    for path in source_dir.rglob("*.py"):
        if _SKIP_DIRS & set(path.parts):
            continue
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not (isinstance(node, ast.ClassDef) and _is_baseplugin_subclass(node)):
                continue
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cap = HOOK_CAPABILITY.get(item.name)
                    if cap:
                        needed.setdefault(cap, set()).add(item.name)
    return needed


def check(entry: dict, source_dir: Path) -> list[str]:
    declared = set(entry.get("capabilities", []))
    needed = required_capabilities(source_dir)
    violations = []
    for cap, methods in sorted(needed.items()):
        if cap not in declared:
            violations.append(
                f"code overrides {sorted(methods)} (capability '{cap}'), "
                f"which is not in the declared capabilities {sorted(declared)}"
            )
    return violations


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    entry = json.loads(Path(argv[0]).read_text())
    violations = check(entry, Path(argv[1]))
    if violations:
        print(f"Capability check FAILED for {entry.get('name')}:")
        for v in violations:
            print(f"  - {v}")
        print(
            "\nAdd the missing capabilities to the entry, or remove the hooks. The "
            "declared surface must match what the code does."
        )
        return 1
    print(f"Capability check passed for {entry.get('name')}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
