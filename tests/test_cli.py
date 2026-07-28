"""Tests for the `axolotl market` CLI (search / info / install)."""

import json

import pytest
from click.testing import CliRunner

from axolotl_market.cli import market
from axolotl_market.registry import REGISTRY_PATH_ENV

ENTRY = {
    "name": "example-callback",
    "description": "A reference callback plugin.",
    "source": "https://github.com/org/repo",
    "ref": "b" * 40,
    "subdir": None,
    "cls": ["pkg.ExamplePlugin"],
    "capabilities": ["callbacks"],
    "install_mode": "auto",
    "maintainer": "someone",
    "license": "Apache-2.0",
    "checks": [{"name": "x", "run": "true"}],
    "last_scan": None,
}


@pytest.fixture
def registry(tmp_path, monkeypatch):
    plugins = tmp_path / "registry" / "plugins"
    plugins.mkdir(parents=True)
    (plugins / "example-callback.json").write_text(json.dumps(ENTRY))
    monkeypatch.setenv(REGISTRY_PATH_ENV, str(tmp_path))
    return tmp_path


def test_search_lists_entries(registry):
    result = CliRunner().invoke(market, ["search"])
    assert result.exit_code == 0
    assert "example-callback" in result.output


def test_search_filters_by_term(registry):
    assert "example-callback" in CliRunner().invoke(market, ["search", "callback"]).output
    assert "No matching" in CliRunner().invoke(market, ["search", "zzz-nope"]).output


def test_info_shows_pinned_source(registry):
    result = CliRunner().invoke(market, ["info", "example-callback"])
    assert result.exit_code == 0
    assert "https://github.com/org/repo" in result.output
    assert "b" * 40 in result.output


def test_info_unknown_name_errors(registry):
    result = CliRunner().invoke(market, ["info", "nope"])
    assert result.exit_code != 0
    assert "No plugin named" in result.output


def test_install_dry_run_prints_resolved_axolotl_command(registry):
    result = CliRunner().invoke(market, ["install", "example-callback", "--dry-run"])
    assert result.exit_code == 0
    assert result.output.strip() == (
        "axolotl plugins install https://github.com/org/repo "
        f"--ref {'b' * 40} --mode auto --cls pkg.ExamplePlugin"
    )


def test_install_dry_run_never_shells_out(registry, monkeypatch):
    called = []
    monkeypatch.setattr("subprocess.call", lambda *a, **k: called.append(a))
    CliRunner().invoke(market, ["install", "example-callback", "--dry-run"])
    assert not called
