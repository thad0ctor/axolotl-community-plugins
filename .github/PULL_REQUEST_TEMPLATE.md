<!--
Adding or updating a plugin listing? This template doubles as your capability
declaration. Fill in every field. CI validates the JSON entry, runs the scan
wall over your source at the pinned SHA, and runs your own `checks:` in a
sandbox. See docs/submitting.md for the full walkthrough.

Contributing to the client or scripts instead? See CONTRIBUTING.md and delete
this template.
-->

## Plugin

- **Registry name** (`registry/plugins/<name>.json`, lowercase/digits/hyphens):
- **Source repo** (GitHub HTTPS URL):
- **Pinned commit SHA** (full 40 chars — no branches or tags):
- **Subdir** (if the package is not at the repo root, else `none`):
- **Plugin class path(s)** (`cls`, dotted BasePlugin subclass):
- **License** (SPDX identifier, e.g. `Apache-2.0`):
- **Maintainer** (GitHub handle responsible for this entry):

## What it does

<!-- One or two sentences. What does the plugin add to a training run? -->

## Capabilities

The `capabilities` array must match what the code actually does — CI's capability
check fails the PR if the code reaches outside what you declare here. Check only
the hook surfaces this plugin uses:

- [ ] `callbacks`
- [ ] `cli_commands`
- [ ] `config_args`
- [ ] `model_patches`
- [ ] `trainers`
- [ ] `datasets`
- [ ] `rewards`

## What your `checks` verify

<!--
Your `checks:` are how you prove your hooks fire against a real axolotl in the
sandbox. Describe what each check asserts. They run with the network disabled and
your repo (at the pinned SHA) as the working directory, so they must be fast,
offline, and deterministic.
-->

## Waivers (if any)

<!--
If the scan wall flags a finding you believe is a false positive or an accepted
risk, add a `waivers/<name>.yml` in THIS PR with a written justification. Leave
this blank if you have none. Reviewers sign off on waivers via CODEOWNERS.
-->

## Confirmations

- [ ] I have read [SECURITY.md](../SECURITY.md) and understand that a listed plugin runs
      with the training process's privileges — vetting raises the floor, it is not a full code review.
- [ ] I am the author of this code, or I am authorized to list it here.
- [ ] `ref` is a full 40-character commit SHA, and `last_scan` is left `null` (CI writes it on merge).
- [ ] I ran `python scripts/validate_entry.py registry/plugins/<name>.json` and `python scripts/build_index.py` locally, and both pass.
- [ ] My `checks` are offline and deterministic (they run with `--network` disabled).
