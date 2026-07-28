# Submitting a plugin

This is the authoritative guide to listing a plugin in the registry. Listing a plugin
means adding **one JSON file** — `registry/plugins/<name>.json` — and opening a PR. CI does
the rest: it validates the entry, scans your source at the pinned SHA, and runs your own
`checks:` against a real Axolotl in a sandbox.

Read [SECURITY.md](../SECURITY.md) first. A listed plugin runs with the training process's
privileges; the vetting pipeline raises the floor, it is not a code review.

## Prerequisites

- Your plugin is a real [`BasePlugin`](https://github.com/axolotl-ai-cloud/axolotl)
  subclass, installable with `pip install` from a public GitHub repo.
- You have a **published commit** you want to pin — you will list its full 40-character
  SHA, not a branch or tag.
- Your repo has tests (or at least import-level assertions) you can run as `checks:` to
  prove your hooks fire.

## 1. Fork and branch

```bash
# Fork axolotl-ai-cloud/axolotl-community-plugins on GitHub, then:
git clone https://github.com/<you>/axolotl-community-plugins
cd axolotl-community-plugins
git checkout -b add-<your-plugin>
pip install -e ".[dev]"          # gives you validate_entry.py's dependencies
```

## 2. Add `registry/plugins/<name>.json`

The filename must equal the `name` field: a plugin named `trainer-metrics` lives at
`registry/plugins/trainer-metrics.json`. A complete entry:

```json
{
  "name": "trainer-metrics",
  "description": "Extra per-step trainer metrics via a TrainerCallback.",
  "source": "https://github.com/someuser/axolotl-trainer-metrics",
  "ref": "4f2a9c1e0b7d3a6f8c2e1d9b0a5c4e3f2a1b0c9d",
  "subdir": null,
  "cls": ["trainer_metrics.TrainerMetricsPlugin"],
  "capabilities": ["callbacks"],
  "install_mode": "auto",
  "min_axolotl_version": "0.18.0",
  "maintainer": "someuser",
  "license": "Apache-2.0",
  "checks": [
    {
      "name": "imports-and-subclasses-baseplugin",
      "run": "python -c \"import trainer_metrics as m; from axolotl.integrations.base import BasePlugin; assert issubclass(m.TrainerMetricsPlugin, BasePlugin)\"",
      "timeout_seconds": 120
    },
    {
      "name": "callback-fires",
      "run": "pytest -q tests/test_callback_fires.py",
      "timeout_seconds": 300
    }
  ],
  "last_scan": null
}
```

JSON does not allow comments, so the field-by-field reference is below. The schema is
[`registry/schema.json`](../registry/schema.json) — it is the source of truth if anything
here drifts.

### Fields

| Field | Required | What it is |
|---|---|---|
| `name` | yes | Unique registry key and install-by-name key. Lowercase letters, digits, hyphens; must match `^[a-z0-9][a-z0-9-]{2,40}$` and equal the filename. |
| `description` | yes | 8–200 chars. Shown in `axolotl market search`. |
| `source` | yes | GitHub HTTPS URL of the plugin repo. GitHub-only in v1. |
| `ref` | yes | **Full 40-char commit SHA.** No branches, no tags, no short SHAs — an entry may never point at a moving ref, so the scan that approved it always describes the exact code. |
| `subdir` | no | Subdirectory holding the package, if not the repo root. `null` if it is the root. |
| `cls` | yes | Array of dotted paths to your `BasePlugin` subclass(es), e.g. `["trainer_metrics.TrainerMetricsPlugin"]`. CI imports each and asserts it is a `BasePlugin` subclass. |
| `capabilities` | yes | Array of the hook surfaces you use, from: `callbacks`, `cli_commands`, `config_args`, `model_patches`, `trainers`, `datasets`, `rewards`. **Must match the code** — CI's capability check fails if the code reaches outside what you declare. |
| `install_mode` | no | How `axolotl plugins install` installs it, passed through as `--mode`: `auto` (default), `pip`, or `syspath`. |
| `min_axolotl_version` | no | Lowest Axolotl version known to work, e.g. `"0.18.0"`, or `null`. |
| `maintainer` | yes | GitHub handle of the person responsible for this entry. |
| `license` | yes | SPDX identifier, e.g. `Apache-2.0`. |
| `checks` | yes | Your own verification steps. See [Writing good checks](#4-writing-good-checks). |
| `last_scan` | no | **Leave it `null`.** CI writes it on merge — see [Why `last_scan` must be null](#why-last_scan-must-be-null). |

## 3. Validate locally and refresh the index

```bash
python scripts/validate_entry.py registry/plugins/trainer-metrics.json
python scripts/build_index.py          # regenerates registry/index.json
git add registry/plugins/trainer-metrics.json registry/index.json
```

`validate_entry.py` runs the exact schema-and-rules check CI runs (schema conformance,
SHA pinning, name/filename match, `last_scan` null). `build_index.py` regenerates
`registry/index.json` — the flat list of names the client fetches first; CI rejects the PR
if it is stale (it runs `build_index.py --check`).

You can also point the client at your local checkout to try `search`/`info` before you
open the PR (these work offline against a checkout):

```bash
AXOLOTL_MARKET_REGISTRY_PATH=. axolotl market search metrics
AXOLOTL_MARKET_REGISTRY_PATH=. axolotl market info trainer-metrics
```

## 4. Writing good `checks`

`checks:` are **your plugin's own tests that CI runs against a real Axolotl in a sandbox —
this is how you prove your hooks fire.** The generic scanners can tell that your code is
not obviously dangerous; they cannot tell that your callback actually gets called. Your
checks close that gap.

For each check, CI (`scripts/run_plugin_checks.py`) has already:

1. cloned your repo at the pinned SHA,
2. `pip install`ed the package (from `subdir` if set), and
3. imported each `cls` and asserted it is a `BasePlugin` subclass.

Then it runs each check as `bash -lc "<run>"` with:

- **the working directory set to your repo at the pinned SHA** (the `subdir`, if you set
  one), so relative paths like `tests/test_callback_fires.py` resolve;
- **the network disabled** (`--network` off) — a check that reaches the network fails;
- a **timeout** of `timeout_seconds` (default 300, max 1800). A timeout fails the check.

A non-zero exit from any check fails the submission. Each check is an object:

```json
{ "name": "callback-fires", "run": "pytest -q tests/test_callback_fires.py", "timeout_seconds": 300 }
```

Guidelines for checks that pass reliably in CI:

- **Fast.** Keep well under the timeout. No model downloads, no multi-epoch training. Use a
  tiny stub model or a mocked trainer step.
- **Offline.** No network at all — no downloading datasets or weights, no telemetry. If
  your test needs a fixture, commit it to your repo at the pinned SHA.
- **Deterministic.** No reliance on wall-clock timing, random ports, or external services.
  Seed anything stochastic.
- **Self-contained.** Everything a check needs must exist in your repo at the pinned SHA,
  since that checkout is the working directory.
- **Actually exercise the hook.** The strongest check instantiates the plugin, drives the
  hook (e.g. runs a couple of trainer steps against a stub), and asserts the observable
  effect — not just that the class imports.

At least one check is required. A minimal but honest pair is an import/subclass assertion
plus one test that fires the hook (as in the example above).

## 5. Open the PR

Push your branch and open a PR against this repo. The
[pull request template](../.github/PULL_REQUEST_TEMPLATE.md) doubles as your **capability
declaration**: plugin name/source/SHA, what it does, the `capabilities` you use (which must
match the code), what your checks verify, license, maintainer, and confirmations that you
have read SECURITY.md and are authorized to list the code.

### What CI does, in order

1. **Validate** — schema + rules on the changed entry, and the index freshness check.
   Offline; no plugin code runs. Fails fast.
2. **Fetch** — clone your source at the pinned SHA. Clone only — nothing installed, nothing
   imported.
3. **Static scan wall** (`run_scans.py`) — over the source tree only, no execution:
   bandit, semgrep (with the Axolotl rules in `rules/semgrep/`), guarddog, pip-audit,
   gitleaks. guarddog and gitleaks are **hard fails**; the rest are waivable. A hard-fail
   scanner that cannot run counts as a failure.
4. **Sandboxed checks** (`run_plugin_checks.py`) — only if the wall passed. Install in the
   sandbox, assert each `cls` is a `BasePlugin` subclass, then run your `checks:` with the
   network disabled.
5. **Report** — the gate results are summarized on the PR.

The ordering is a security invariant, not a convenience: **no untrusted plugin code
executes before the static wall passes**, because `pip install` runs arbitrary build code.

After the maintainers merge, a trusted post-merge job re-runs the scans and writes
`last_scan` on your entry.

## 6. Waivers

If the scan wall flags a finding you believe is a false positive or an accepted risk, you
do not edit the scanners — you add a **`waivers/<name>.yml`** in the *same PR*, with a
written justification for each finding you want suppressed. That file lives under a path
that [CODEOWNERS](../.github/CODEOWNERS) puts under mandatory review, so a reviewer makes
one small, focused judgment call instead of auditing the whole plugin.

Notes and current limits:

- Only **waivable** findings can be waived. guarddog and gitleaks are hard fails and are
  **not** waivable — a genuine malicious-package hit or a committed secret blocks the
  listing, full stop.
- A waiver is a documented human decision, not proof of safety. Keep justifications
  specific ("bandit B404 flags the `subprocess` import; it is only ever called with a
  fixed argv, see `foo.py:42`"), not hand-wavy.
- The exact `waivers/<name>.yml` field layout is not yet pinned by a committed schema; add
  the finding identifier and a justification per finding, and expect reviewers to ask for
  the shape they want. This will be formalized as the registry matures.

## Updating an entry

Shipping a new version of your plugin means **bumping `ref`** to the new commit SHA in your
entry, then opening a PR. That re-runs every gate against the new SHA — validation, the
scan wall, and your checks. Because an entry never points at a moving ref, a listed plugin
can never change out from under the scan that approved it: the only way the installed code
changes is a PR that re-vets it.

Update other fields (description, `capabilities`, `checks`, `min_axolotl_version`) the same
way — any edit is a PR that re-validates and re-scans.

## Why `last_scan` must be null

`last_scan` records what scans ran and when. It is **written by CI on merge, never by the
submitter** — `validate_entry.py` rejects any PR that sets it. If submitters could write it,
a listing could self-certify: claim a clean scan it never passed. Leaving it `null` and
letting a trusted post-merge job stamp it is what makes the scan record trustworthy. Set it
to `null` (or omit it) and let CI fill it in.
