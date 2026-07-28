# Contributing

This file is about contributing to **the repo itself** — the `axolotl market` client, the
scan scripts, the semgrep rules, and the docs.

> **Listing a plugin is different.** To add or update a plugin entry you do *not* edit code
> here — you add one `registry/plugins/<name>.json` file and open a PR. That flow is
> documented in **[docs/submitting.md](docs/submitting.md)**, not here.

## Dev setup

```bash
git clone https://github.com/axolotl-ai-cloud/axolotl-community-plugins
cd axolotl-community-plugins
pip install -e ".[dev]"
pytest
```

The `dev` extra pulls in `pytest` and `jsonschema` (used by `scripts/validate_entry.py`).

## What lives where

- `src/axolotl_market/` — the client. `cli.py` is the `axolotl market` command group;
  `registry.py` resolves a name to an install spec.
- `scripts/` — CI's building blocks: `validate_entry.py` (schema + rules), `run_scans.py`
  (the static scan wall), `run_plugin_checks.py` (sandboxed author checks), and
  `build_index.py` (regenerates `registry/index.json`).
- `registry/schema.json` — the entry format. It is the source of truth; if you change it,
  update `docs/submitting.md` and the PR template to match.
- `rules/semgrep/` — Axolotl-specific scan rules.

## Ground rules

- Keep the client dependency-light. `requests` is imported lazily so `search`/`info` work
  offline against a local checkout.
- The security invariants are contracts, not conveniences: `last_scan` is CI-written only,
  every entry pins a full SHA, and untrusted plugin code runs only in the sandbox and only
  after the scan wall passes. Don't loosen these without a discussion.
- Run `pytest` before opening a PR. If you touch the schema or a scan script, add or
  update a test.

## Reporting security issues

Vulnerabilities in the client, the scan scripts, or a *listed plugin* go through the
process in [SECURITY.md](SECURITY.md) — not a public issue.
