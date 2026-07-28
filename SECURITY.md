# Security

This document is the honest version of what this registry does and does not protect you
from. Read it before you install a plugin, and before you list one.

## The one thing to understand

**Installing a plugin runs third-party code with your training process's privileges.**

A plugin is imported into the Axolotl process. Its top-level code runs during config load;
its hooks run during training, with the same filesystem, network, environment variables,
and credentials your training job has. There is no runtime sandbox around an *installed*
plugin. The security model is **informed, pinned, explicit** — not containment:

- **Informed** — every listing is scanned, and the scan history is recorded on the entry.
- **Pinned** — every entry names a full 40-character commit SHA. It cannot point at a
  branch or tag, so the code you install is exactly the code that was scanned. A new SHA
  is a new PR that re-runs everything.
- **Explicit** — installation is always a command you run and confirm. `axolotl market
  install` only *resolves* a name; the actual install is `axolotl plugins install`, the
  same user-initiated, confirmed path you would type by hand. Installing is never a side
  effect of loading a config.

## What the automated gates do

Listing a plugin runs a layered pipeline (see [README.md](README.md#how-vetting-works) for
the table). Each layer targets a distinct failure class, because Python security tools
overlap very little in what they detect:

- **Static scan wall** (`scripts/run_scans.py`), over the source tree at the pinned SHA,
  with **no plugin code executed**: bandit (dangerous patterns), semgrep with
  Axolotl-specific rules (network-at-import, monkeypatching internals, undeclared
  capabilities), guarddog (malicious-package heuristics), pip-audit (known CVEs in
  declared deps), and gitleaks (committed secrets).
- **Sandboxed author checks** (`scripts/run_plugin_checks.py`), *after* the wall passes:
  install in a sandbox with the network disabled, confirm each class is a `BasePlugin`
  subclass, then run the plugin's own `checks:`.
- **Post-merge stamping** and a **weekly re-scan** so retroactive advisories (new CVEs on
  unchanged code) surface over time.

Hard-fail gates (guarddog, gitleaks) block a listing outright, and a hard-fail scanner
that cannot run is treated as a failure, never a pass. Other findings are waivable only
through a `waivers/<name>.yml` reviewed in the same PR under CODEOWNERS.

## What the gates do NOT guarantee

This is the tension raised in
[axolotl-ai-cloud/axolotl#3840](https://github.com/axolotl-ai-cloud/axolotl/pull/3840),
and we are not going to paper over it:

- **The scan wall is a floor, not a code review.** Automated tools catch known-bad
  patterns and known-vulnerable dependencies. They do not understand intent. A
  sufficiently determined author can write code that is malicious and still passes every
  scanner. Passing the wall means "no gate tripped," not "audited and safe."
- **A passing listing is not an endorsement.** The maintainers do not commit to reading
  every plugin line by line. Trust the scan results for what they are — evidence, not a
  warranty.
- **Waivers are human judgment.** A waived finding is a reviewer deciding a specific
  flagged pattern is acceptable. That is a judgment call, not proof of safety.

## What the sandbox protects — and what it doesn't

The sandbox exists to protect **the registry's CI**, not your machine:

- Untrusted plugin code executes **only** inside the sandbox job, and **only after** the
  static wall has passed. `pip install` runs arbitrary build code, so install never
  happens before the wall.
- Author `checks:` run with the **network disabled**, so a check cannot exfiltrate or
  phone home while it runs in CI.

The sandbox does **not** follow the plugin onto your machine. When *you* install a plugin,
it runs unsandboxed with your privileges. That is the point of the "informed, pinned,
explicit" model above.

## Reporting a malicious or vulnerable listing

If you believe a listed plugin is malicious, has been compromised, or ships a serious
vulnerability:

1. **Do not open a public issue.** Report it privately through this repo's **Security tab
   → "Report a vulnerability"** (GitHub private vulnerability reporting). If that is
   unavailable, contact a maintainer via the reviewer team in
   [`.github/CODEOWNERS`](.github/CODEOWNERS).
   *(A dedicated security contact address is still to be finalized — see open questions.)*
2. Include the plugin name, the pinned SHA, and what you observed or can reproduce.
3. Maintainers verify the report, and if it holds, the listing is pulled — the entry is
   removed and/or marked as withdrawn, and an advisory is posted so anyone who already
   installed it is warned.

Because every install is pinned to a SHA recorded in your local plugin manifest, you can
always tell exactly which revision you installed and whether it is the flagged one.

## Open questions (policy still being decided)

These are deliberately unsettled and are being worked out in the upstream discussion.
Treat them as "not yet decided," not as current behavior:

- **Trust tiers.** Whether scan-passing is enough for a single tier, or whether there are
  two — "community" (automated gates only) and "verified" (maintainer-reviewed) — with the
  tier shown at install time.
- **Namespace ownership and takedown / yank policy.** Who owns a plugin name, and the
  exact mechanism for yanking a listing (a machine-readable flag the client refuses to
  install, versus simple removal) and whether/how the client enforces it.
- **Scan expiry.** Whether a listing whose source repo is deleted or made private should
  auto-yank after repeated failed re-scans, and after how many.

Where this document describes current behavior it reflects the schema and scripts in this
repo. Where it describes tiers, yank enforcement, and expiry, those are proposals under
discussion, not guarantees.
