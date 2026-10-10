"""CLI version reporting follows the installed package metadata."""

from __future__ import annotations

import tomllib
from importlib.metadata import version
from pathlib import Path

from click.testing import CliRunner

from tableau_cli.cli import cli


def test_version_option_reads_package_metadata() -> None:
    project_version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    assert version("tableau-cli") == project_version

    result = CliRunner().invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"cli, version {project_version}\n"
