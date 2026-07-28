"""The `axolotl market` command group, contributed via the axolotl CLI entry points."""

from __future__ import annotations

import shutil
import subprocess  # nosec: only ever runs the axolotl console script with fixed argv

import click

from axolotl_market.registry import RegistryError, load_entries, resolve


@click.group(name="market")
def market():
    """Search and install community plugins from the Axolotl marketplace."""


@market.command(name="search")
@click.argument("term", required=False)
def search(term: str | None):
    """List marketplace plugins, optionally filtered by a search term."""
    try:
        entries = load_entries()
    except RegistryError as exc:
        raise click.ClickException(str(exc))

    if term:
        needle = term.lower()
        entries = [
            e for e in entries
            if needle in e.name.lower() or needle in e.description.lower()
        ]
    if not entries:
        click.echo("No matching plugins.")
        return

    width = max(len(e.name) for e in entries)
    for entry in sorted(entries, key=lambda e: e.name):
        click.echo(f"{entry.name.ljust(width)}  {entry.description}")


@market.command(name="info")
@click.argument("name")
def info(name: str):
    """Show everything the registry records about one plugin."""
    try:
        entry = resolve(name)
    except RegistryError as exc:
        raise click.ClickException(str(exc))

    click.echo(f"name         : {entry.name}")
    click.echo(f"description  : {entry.description}")
    click.echo(f"source       : {entry.source}")
    click.echo(f"ref          : {entry.ref}")
    click.echo(f"cls          : {', '.join(entry.cls)}")
    click.echo(f"capabilities : {', '.join(entry.capabilities)}")
    click.echo(f"maintainer   : {entry.maintainer}")
    click.echo(f"license      : {entry.license}")
    click.echo(f"\nInstall with:\n  axolotl market install {entry.name}")


@market.command(name="install")
@click.argument("name")
@click.option("--yes", "-y", is_flag=True, help="Pass through to skip the install prompt")
@click.option("--dry-run", is_flag=True, help="Print the resolved install command, do not run it")
def install(name: str, yes: bool, dry_run: bool):
    """Resolve NAME and hand it to `axolotl plugins install` (the explicit, confirmed path)."""
    try:
        entry = resolve(name)
    except RegistryError as exc:
        raise click.ClickException(str(exc))

    cmd = ["axolotl", "plugins", "install", *entry.install_args()]
    if yes:
        cmd.append("--yes")

    printable = " ".join(cmd)
    if dry_run:
        click.echo(printable)
        return

    axolotl = shutil.which("axolotl")
    if axolotl is None:
        raise click.ClickException(
            "The `axolotl` command was not found. The marketplace client resolves a "
            "name to a pinned source; axolotl performs the actual install.\n"
            f"Resolved command:\n  {printable}"
        )

    click.echo(f"Resolved {name!r} -> {printable}\n")
    # We only ever exec the axolotl console script with a fixed-shape argv built from a
    # schema-validated entry; nothing from the network reaches a shell.
    raise SystemExit(subprocess.call([axolotl, *cmd[1:]]))  # nosec
