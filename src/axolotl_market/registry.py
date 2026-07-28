"""Resolve a marketplace plugin name to a concrete install spec.

The registry is a set of JSON entries (one per plugin) validated by CI before merge.
The client reads them either from a local checkout (for development and tests) or from
a pinned raw URL of the registry repo. Resolution is the seam the design calls for: a
name in, a concrete ``source``/``ref``/``cls`` out, which the install command then hands
straight to ``axolotl plugins install`` -- the same explicit, confirmed path a user would
type by hand.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

REGISTRY_URL_ENV = "AXOLOTL_MARKET_REGISTRY_URL"
REGISTRY_PATH_ENV = "AXOLOTL_MARKET_REGISTRY_PATH"
# A specific tag/commit of the registry repo is pinned here per client release, so a
# client version always resolves against a known registry snapshot rather than main.
DEFAULT_REGISTRY_REF = "main"
DEFAULT_REGISTRY_RAW = (
    "https://raw.githubusercontent.com/axolotl-ai-cloud/"
    f"axolotl-community-plugins/{DEFAULT_REGISTRY_REF}"
)


class RegistryError(RuntimeError):
    """The registry could not be read, or a name did not resolve."""


@dataclass
class PluginEntry:
    name: str
    description: str
    source: str
    ref: str
    cls: list[str]
    capabilities: list[str]
    subdir: str | None = None
    install_mode: str = "auto"
    min_axolotl_version: str | None = None
    maintainer: str = ""
    license: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "PluginEntry":
        fields = {
            "name", "description", "source", "ref", "cls", "capabilities",
            "subdir", "install_mode", "min_axolotl_version", "maintainer", "license",
        }
        return cls(**{k: v for k, v in data.items() if k in fields})

    def install_args(self) -> list[str]:
        """The exact `axolotl plugins install` argv this entry resolves to."""
        args = [self.source, "--ref", self.ref, "--mode", self.install_mode]
        if self.subdir:
            args += ["--subdir", self.subdir]
        for cls_path in self.cls:
            args += ["--cls", cls_path]
        return args


def _local_root() -> Path | None:
    raw = os.environ.get(REGISTRY_PATH_ENV)
    return Path(raw).expanduser() if raw else None


def load_entries() -> list[PluginEntry]:
    """Every plugin entry, from a local checkout if configured, else the pinned URL."""
    root = _local_root()
    if root is not None:
        return _load_local(root)
    return _load_remote()


def resolve(name: str) -> PluginEntry:
    for entry in load_entries():
        if entry.name == name:
            return entry
    raise RegistryError(
        f"No plugin named {name!r} in the registry. Run `axolotl market search` to list."
    )


def _load_local(root: Path) -> list[PluginEntry]:
    plugins_dir = root / "registry" / "plugins" if (root / "registry").is_dir() else root
    if not plugins_dir.is_dir():
        raise RegistryError(f"Registry path {plugins_dir} does not exist.")
    entries = []
    for path in sorted(plugins_dir.glob("*.json")):
        entries.append(PluginEntry.from_dict(json.loads(path.read_text())))
    return entries


def _load_remote() -> list[PluginEntry]:
    import requests  # imported lazily so `search`/`info` work offline against a checkout

    base = os.environ.get(REGISTRY_URL_ENV, DEFAULT_REGISTRY_RAW).rstrip("/")
    index_url = f"{base}/registry/index.json"
    try:
        resp = requests.get(index_url, timeout=20)
        resp.raise_for_status()
        names = resp.json()["plugins"]
    except Exception as exc:  # noqa: BLE001  surfaced as a clean RegistryError
        raise RegistryError(f"Could not read the registry index at {index_url}: {exc}")

    entries = []
    for name in names:
        entry_url = f"{base}/registry/plugins/{name}.json"
        try:
            resp = requests.get(entry_url, timeout=20)
            resp.raise_for_status()
            entries.append(PluginEntry.from_dict(resp.json()))
        except Exception as exc:  # noqa: BLE001
            raise RegistryError(f"Could not read entry {name} at {entry_url}: {exc}")
    return entries
