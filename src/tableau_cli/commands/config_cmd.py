from __future__ import annotations

import json
import sys

import click

from ..config.store import load_file_config, save_file_config


@click.group("config")
def config_group():
    """Manage CLI configuration."""


@config_group.command("set")
@click.option("--server", default=None, help="Tableau server URL")
@click.option("--site-name", default=None, help="Tableau site name")
@click.option("--pat-name", default=None, help="Personal Access Token name")
@click.option("--pat-value", default=None, help="Personal Access Token value")
def config_set(server, site_name, pat_name, pat_value):
    """Set configuration values."""
    existing = load_file_config()
    if server is not None:
        existing.server = server
    if site_name is not None:
        existing.site_name = site_name
    if pat_name is not None:
        existing.pat_name = pat_name
    if pat_value is not None:
        existing.pat_value = pat_value
    save_file_config(existing)
    sys.stderr.write("Configuration saved.\n")


@config_group.command("show")
def config_show():
    """Show current configuration."""
    config = load_file_config()
    display = {}
    if config.server is not None:
        display["server"] = config.server
    if config.site_name is not None:
        display["siteName"] = config.site_name
    if config.pat_name is not None:
        display["patName"] = config.pat_name
    display["patValue"] = "****" if config.pat_value else None
    print(json.dumps(display, indent=2))
