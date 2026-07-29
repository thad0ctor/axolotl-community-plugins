"""Tests for the AST capability check (scripts/check_capabilities.py)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from check_capabilities import check, required_capabilities  # noqa: E402

CALLBACK_PLUGIN = """
from axolotl.integrations.base import BasePlugin

class MyPlugin(BasePlugin):
    def add_callbacks_pre_trainer(self, cfg, trainer):
        return []
"""

MODEL_PATCH_IN_CLASS_BODY = """
from axolotl.integrations.base import BasePlugin

class MyPlugin(BasePlugin):
    def pre_model_load(self, cfg):
        pass
"""


def _write(tmp_path, body, name="plug.py"):
    (tmp_path / name).write_text(body)
    return tmp_path


def test_required_capabilities_maps_overridden_hooks(tmp_path):
    _write(tmp_path, CALLBACK_PLUGIN)
    needed = required_capabilities(tmp_path)
    assert "callbacks" in needed
    assert needed["callbacks"] == {"add_callbacks_pre_trainer"}


def test_declared_covers_overridden_passes(tmp_path):
    _write(tmp_path, CALLBACK_PLUGIN)
    entry = {"name": "x", "capabilities": ["callbacks"]}
    assert check(entry, tmp_path) == []


def test_underdeclared_capability_is_a_violation(tmp_path):
    _write(tmp_path, MODEL_PATCH_IN_CLASS_BODY)
    entry = {"name": "x", "capabilities": ["callbacks"]}  # declares callbacks, hooks model
    violations = check(entry, tmp_path)
    assert len(violations) == 1
    assert "model_patches" in violations[0]


def test_non_baseplugin_class_is_ignored(tmp_path):
    _write(tmp_path, "class NotAPlugin:\n    def pre_model_load(self, cfg): pass\n")
    entry = {"name": "x", "capabilities": []}
    assert check(entry, tmp_path) == []


def test_tests_directory_is_skipped(tmp_path):
    (tmp_path / "tests").mkdir()
    _write(tmp_path / "tests", MODEL_PATCH_IN_CLASS_BODY, name="test_x.py")
    entry = {"name": "x", "capabilities": []}
    assert check(entry, tmp_path) == []


@pytest.mark.parametrize("bad_syntax", ["def (:\n", "class ??\n"])
def test_unparseable_file_does_not_crash(tmp_path, bad_syntax):
    _write(tmp_path, bad_syntax)
    assert required_capabilities(tmp_path) == {}
