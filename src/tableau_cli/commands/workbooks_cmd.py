from __future__ import annotations

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..output.format import output
from ..utils.paginate import paginate


@click.group("workbooks")
def workbooks_group():
    """Manage workbooks."""


@workbooks_group.command("list")
@click.option("--filter", "filter_", default=None, help="Filter string (e.g., name:eq:Finance)")
@click.option("--page-size", default=None, type=int, help="Page size for API requests")
@click.option("--limit", default=None, type=int, help="Max total results")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def workbooks_list(filter_, page_size, limit, fmt):
    """List workbooks on the site."""
    config = resolve_config()

    def fn(api):
        def get_data_fn(ps, pn):
            result = api.query_workbooks_for_site(
                site_id=api.site_id,
                filter_=filter_ or "",
                page_size=ps,
                page_number=pn,
            )
            return {"pagination": result["pagination"], "data": result["workbooks"]}

        return paginate(page_size=page_size, limit=limit, get_data_fn=get_data_fn)

    result = with_auth(config, fn)
    output(result, fmt)


@workbooks_group.command("get")
@click.argument("workbook_id")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def workbooks_get(workbook_id, fmt):
    """Get workbook details."""
    config = resolve_config()

    def fn(api):
        workbook = api.get_workbook(workbook_id=workbook_id, site_id=api.site_id)

        # Enrich views with usage statistics (consistent with MCP behavior)
        if workbook.get("views"):
            views = api.query_views_for_workbook(workbook_id=workbook_id, site_id=api.site_id)
            workbook["views"]["view"] = views

        return workbook

    result = with_auth(config, fn)
    output(result, fmt)
