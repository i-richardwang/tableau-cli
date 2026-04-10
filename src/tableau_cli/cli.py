from __future__ import annotations

import json
import sys
from typing import Any

import click
import httpx

from .errors.cli_error import CliError


def to_error_output(err: Exception) -> dict[str, Any]:
    # Our own structured errors
    if isinstance(err, CliError):
        return err.to_output()

    # httpx HTTP errors (from Tableau REST API)
    if isinstance(err, httpx.HTTPStatusError):
        status = err.response.status_code
        try:
            data = err.response.json()
        except Exception:
            data = None

        # Tableau REST API error format: { error: { summary, detail, code } }
        if isinstance(data, dict) and data.get("error"):
            error_info = data["error"]
            summary = error_info.get("summary", "")
            detail = error_info.get("detail", "")
            code = error_info.get("code")
            return {
                "isError": True,
                "errorType": "tableau-api-error",
                "message": f"{summary}: {detail}" if detail else (summary or str(err)),
                **({"details": f"Tableau error code: {code}"} if code else {}),
            }

        return {
            "isError": True,
            "errorType": "http-error",
            "message": f"HTTP {status}: {err}",
            **({"details": err.response.text} if err.response.text else {}),
        }

    # httpx transport errors (network unreachable, timeout, DNS failure, etc.)
    # Equivalent to TS: isAxiosError(err) && !err.response
    if isinstance(err, httpx.TransportError):
        return {
            "isError": True,
            "errorType": "http-error",
            "message": f"Network error: {err}",
        }

    # Config validation errors
    if isinstance(err, RuntimeError) and str(err).startswith("Missing required config:"):
        return {
            "isError": True,
            "errorType": "config-error",
            "message": str(err),
            "hint": "Run `tableau-cli config set` to configure, or set environment variables.",
        }

    # JSON parse errors (bad --query input)
    if isinstance(err, json.JSONDecodeError):
        return {
            "isError": True,
            "errorType": "invalid-input",
            "message": str(err),
            "hint": "Check that your --query argument is valid JSON.",
        }

    # Fallback
    return {
        "isError": True,
        "errorType": "unknown-error",
        "message": str(err),
    }


class TableauCli(click.Group):
    def invoke(self, ctx: click.Context) -> Any:
        try:
            return super().invoke(ctx)
        except click.exceptions.Exit:
            raise
        except click.exceptions.Abort:
            raise
        except click.UsageError:
            raise
        except Exception as exc:
            output = to_error_output(exc)
            sys.stdout.write(json.dumps(output, indent=2, ensure_ascii=False) + "\n")
            ctx.exit(1)


@click.group(cls=TableauCli)
@click.version_option("0.1.0")
def cli():
    """CLI tool for interacting with Tableau Server/Cloud."""


def main() -> None:
    from .commands.config_cmd import config_group
    from .commands.datasources_cmd import datasources_group
    from .commands.search_cmd import search_command
    from .commands.views_cmd import views_group
    from .commands.workbooks_cmd import workbooks_group

    cli.add_command(config_group)
    cli.add_command(datasources_group)
    cli.add_command(datasources_group, name="ds")  # alias
    cli.add_command(views_group)
    cli.add_command(workbooks_group)
    cli.add_command(workbooks_group, name="wb")  # alias
    cli.add_command(search_command)

    cli()
