from __future__ import annotations

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..errors.cli_error import CliError
from ..output.format import output
from ..utils.paginate import paginate


@click.group("projects")
def projects_group():
    """Manage projects."""


@projects_group.command("list")
@click.option("--filter", "filter_", default=None, help="Filter string (e.g., name:eq:Default)")
@click.option(
    "--capability",
    default=None,
    type=click.Choice(["Write"]),
    help="Only return projects the current user has this capability on: "
    "Write lists the projects you can publish or create content into. Requires REST API >= 3.30.",
)
@click.option("--page-size", default=None, type=int, help="Page size for API requests")
@click.option("--limit", default=None, type=int, help="Max total results")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def projects_list(filter_, capability, page_size, limit, fmt):
    """List projects on the site."""
    config = resolve_config()

    def fn(api):
        # Older servers ignore the parameter and return every viewable project; fail loudly instead.
        if capability and not api.version_is_at_least("3.30"):
            raise CliError(
                error_type="validation-error",
                message=f"--capability requires Tableau REST API 3.30 or later; this server reports {api.version}.",
                hint="Omit --capability to list all viewable projects.",
            )

        def get_data_fn(ps, pn):
            result = api.query_projects(
                site_id=api.site_id,
                filter_=filter_ or "",
                capability=capability,
                page_size=ps,
                page_number=pn,
            )
            return {"pagination": result["pagination"], "data": result["projects"]}

        return paginate(page_size=page_size, limit=limit, get_data_fn=get_data_fn)

    result = with_auth(config, fn)
    output(result, fmt)
