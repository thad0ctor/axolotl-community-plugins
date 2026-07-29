"""Tests for the registry entry validator (scripts/validate_entry.py)."""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_entry  # noqa: E402

VALID = {
    "name": "good-plugin",
    "description": "A valid entry for tests.",
    "source": "https://github.com/org/repo",
    "ref": "a" * 40,
    "subdir": None,
    "cls": ["pkg.Plugin"],
    "capabilities": ["callbacks"],
    "install_mode": "auto",
    "maintainer": "someone",
    "license": "Apache-2.0",
    "checks": [{"name": "x", "run": "true"}],
    "last_scan": None,
}


def _write(tmp_path, data, name="good-plugin.json"):
    path = tmp_path / name
    path.write_text(json.dumps(data))
    return path


def test_valid_entry_passes(tmp_path):
    assert validate_entry.validate_file(_write(tmp_path, VALID)) == []


def test_filename_must_match_name(tmp_path):
    errors = validate_entry.validate_file(_write(tmp_path, VALID, name="wrong.json"))
    assert any("filename must match" in e for e in errors)


@pytest.mark.parametrize(
    "field,value",
    [
        ("source", "https://evil.com/a/b"),
        ("ref", "nope"),
        ("subdir", "../escape"),
        ("subdir", "-flag"),
        ("capabilities", []),
        ("cls", []),
    ],
)
def test_schema_rejects_unsafe_fields(tmp_path, field, value):
    bad = {**VALID, field: value}
    assert validate_entry.validate_file(_write(tmp_path, bad)) != []


def test_submitter_may_not_set_last_scan(tmp_path):
    stamped = {**VALID, "last_scan": {"date": "2026-07-29", "status": "pass"}}
    errors = validate_entry.validate_file(_write(tmp_path, stamped))
    assert any("last_scan" in e for e in errors)


def test_stamp_context_allows_last_scan(tmp_path):
    stamped = {**VALID, "last_scan": {"date": "2026-07-29", "status": "pass"}}
    path = _write(tmp_path, stamped)
    assert validate_entry.validate_file(path, allow_stamped=True) == []
