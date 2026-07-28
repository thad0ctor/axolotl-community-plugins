"""Tests for the marketplace registry resolver."""

import json

import pytest

from axolotl_market.registry import (
    REGISTRY_PATH_ENV,
    PluginEntry,
    RegistryError,
    load_entries,
    resolve,
)

ENTRY = {
    "name": "example-callback",
    "description": "A reference callback plugin.",
    "source": "https://github.com/org/repo",
    "ref": "a" * 40,
    "subdir": "src",
    "cls": ["pkg.AlphaPlugin", "pkg.BetaPlugin"],
    "capabilities": ["callbacks"],
    "install_mode": "auto",
    "maintainer": "someone",
    "license": "Apache-2.0",
    "checks": [{"name": "x", "run": "true"}],
    "last_scan": None,
}


@pytest.fixture
def local_registry(tmp_path, monkeypatch):
    plugins = tmp_path / "registry" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "example-callback.json").write_text(json.dumps(ENTRY))
    monkeypatch.setenv(REGISTRY_PATH_ENV, str(tmp_path))
    return tmp_path


def test_from_dict_ignores_ci_only_and_unknown_fields():
    entry = PluginEntry.from_dict(ENTRY)
    assert entry.name == "example-callback"
    assert entry.cls == ["pkg.AlphaPlugin", "pkg.BetaPlugin"]
    # last_scan / checks are not client concerns and must not blow up construction
    assert not hasattr(entry, "last_scan")


def test_install_args_is_the_exact_axolotl_argv():
    entry = PluginEntry.from_dict(ENTRY)
    assert entry.install_args() == [
        "https://github.com/org/repo",
        "--ref",
        "a" * 40,
        "--mode",
        "auto",
        "--subdir",
        "src",
        "--cls",
        "pkg.AlphaPlugin",
        "--cls",
        "pkg.BetaPlugin",
    ]


def test_load_and_resolve_from_local_checkout(local_registry):
    entries = load_entries()
    assert [e.name for e in entries] == ["example-callback"]
    assert resolve("example-callback").source == "https://github.com/org/repo"


def test_resolve_unknown_name_raises(local_registry):
    with pytest.raises(RegistryError, match="No plugin named"):
        resolve("does-not-exist")


def test_the_shipped_seed_entry_loads(monkeypatch):
    # Point at the real repo checkout so a broken seed entry fails loudly here.
    from pathlib import Path

    repo_root = Path(__file__).resolve().parent.parent
    monkeypatch.setenv(REGISTRY_PATH_ENV, str(repo_root))
    names = [e.name for e in load_entries()]
    assert "example-callback" in names
