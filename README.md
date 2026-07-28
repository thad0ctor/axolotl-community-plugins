# Axolotl Community Plugins

A registry of vetted community plugins for [Axolotl](https://github.com/axolotl-ai-cloud/axolotl),
plus `axolotl market` — the client that lets you find and install them by name.

The registry is a set of JSON entries (one file per plugin under `registry/plugins/`).
Every entry pins a plugin repo to a full commit SHA and is added by a pull request that
CI validates, scans, and runs the plugin's own tests against. Getting listed is how a
plugin earns discoverability; the scan pipeline is how it earns a baseline of trust.

> **Scope, honestly.** The automated gates raise the floor — they are not a line-by-line
> code review. Installing any plugin runs third-party code with your training process's
> privileges. The model is *informed, pinned, explicit* installs, not sandboxed
> execution at runtime. Read [SECURITY.md](SECURITY.md) before you install anything.

## Two audiences

- **Plugin users** install the client, then search and install plugins by name. The
  client resolves a name to a pinned source and hands off to Axolotl's own installer.
- **Plugin authors** open a PR adding one `registry/plugins/<name>.json` file. That
  triggers the scan wall plus the author-provided `checks:` that prove the plugin's
  hooks actually fire.

---

## For plugin users

```bash
pip install axolotl-marketplace          # provides the `axolotl market` command group
axolotl market search metrics            # search names + descriptions
axolotl market info trainer-metrics      # show everything the registry records
axolotl market install trainer-metrics   # resolve + hand off to `axolotl plugins install`
```

`axolotl market install <name>` does not install anything itself. It looks the name up in
the registry, then runs the explicit, confirmed install path you would otherwise type by
hand:

```bash
axolotl plugins install <source> --ref <sha> --mode <mode> [--subdir <dir>] --cls <ClassPath>
```

Useful flags:

- `axolotl market install <name> --dry-run` — print the resolved command without running it.
- `axolotl market install <name> --yes` — pass `--yes` through to skip the install prompt.

The client requires a recent Axolotl that exposes the CLI entry points (see
[Relationship to Axolotl](#relationship-to-axolotl)). The `axolotl market` group is
contributed through Axolotl's `axolotl.cli_commands` entry point — installing
`axolotl-marketplace` needs no changes to Axolotl core.

## For plugin authors

You list a plugin by adding a single JSON file and opening a PR. Quick version:

```bash
# 1. Fork this repo and branch
git checkout -b add-my-plugin

# 2. Add registry/plugins/my-plugin.json  (see docs/submitting.md for every field)

# 3. Validate locally and refresh the index
python scripts/validate_entry.py registry/plugins/my-plugin.json
python scripts/build_index.py            # regenerates registry/index.json

# 4. Open a PR — the template doubles as your capability declaration
```

The authoritative, field-by-field guide — including how to write good `checks`, how
waivers work, and how to update an entry — is **[docs/submitting.md](docs/submitting.md)**.

---

## How vetting works

Adding or updating an entry is a PR. CI runs, in order:

1. **Validation** — `scripts/validate_entry.py` checks the entry against
   [`registry/schema.json`](registry/schema.json): the `ref` is a full 40-char SHA (no
   moving refs), the name is unique and well-formed, the filename matches `name`, and
   `last_scan` is left null. `scripts/build_index.py --check` confirms the index is up to
   date. No plugin code runs at this stage.

2. **Static scan wall** — `scripts/run_scans.py` runs a layered set of scanners over the
   plugin's *source tree* at the pinned SHA. Nothing is installed and no plugin code
   executes here.

   | Layer | Catches | Gate |
   |---|---|---|
   | bandit | dangerous patterns (`eval`/`exec`, `pickle`, `shell=True`, …) | fail, waivable |
   | semgrep (+ Axolotl rules) | network-at-import, monkeypatching internals, undeclared capabilities | fail, waivable |
   | guarddog | malicious-package heuristics | **hard fail** |
   | pip-audit | known CVEs in declared dependencies | fail, waivable |
   | gitleaks | committed secrets | **hard fail** |

   A hard-fail scanner that cannot run is treated as a failure, never a pass. Waivable
   findings can be suppressed only by a `waivers/<name>.yml` reviewed in the same PR.

3. **Sandboxed author checks** — only if the wall passes. `scripts/run_plugin_checks.py`
   clones the plugin at the pinned SHA, installs it in a sandbox, confirms each declared
   class is a `BasePlugin` subclass, then runs your `checks:` with the network disabled.
   This is where a plugin proves *its own* hooks fire — something the generic scanners
   cannot do.

4. **Post-merge stamping** — after merge, CI records `last_scan` on the entry (what ran,
   when). Submitters never write this field; a listing cannot self-certify.

5. **Weekly re-scan** — every listed SHA is re-scanned on a schedule, because advisory
   databases are retroactive: a `pip-audit` result can change even when the code hasn't.

## Relationship to Axolotl

Two upstream pieces make this registry possible, and it builds on both without forking
Axolotl:

- **CLI entry points — [axolotl-ai-cloud/axolotl#3840](https://github.com/axolotl-ai-cloud/axolotl/pull/3840).**
  `axolotl-marketplace` registers the `axolotl market` command group through the
  `axolotl.cli_commands` entry point group that #3840 introduced. It is an independent,
  pip-installable app that plugs into the Axolotl CLI.
- **External plugin sources (`axolotl plugins install`).** The installer that resolves a
  git URL + SHA to an installed plugin already exists as an explicit, user-confirmed,
  SHA-pinned command. `axolotl market install <name>` is just a resolver in front of it —
  a name in, the same confirmed install path out.

## Repository layout

```
registry/
  schema.json            # entry format (source of truth)
  index.json             # flat list of names the client fetches first (generated)
  plugins/<name>.json    # one entry per plugin
waivers/<name>.yml       # allowlisted scanner findings + written justification
rules/semgrep/           # Axolotl-specific scan rules
scripts/                 # validate, scan, run author checks, build index
src/axolotl_market/       # the `axolotl market` client
```

## Documentation

- **[docs/submitting.md](docs/submitting.md)** — the authoritative guide to listing a plugin.
- **[CONTRIBUTING.md](CONTRIBUTING.md)** — contributing to the client and scripts themselves.
- **[SECURITY.md](SECURITY.md)** — the threat model, what vetting does and does not promise, and how to report a bad listing.

## Status

This registry is early. Some policy is deliberately still open — trust tiers
(automated-gate "community" vs maintainer-reviewed "verified"), namespace ownership, and
the takedown / yank process. Those are called out as open questions in
[SECURITY.md](SECURITY.md) rather than presented as settled.

## License

[Apache-2.0](LICENSE). Each listed plugin is licensed by its own author under the terms
its repository declares.
