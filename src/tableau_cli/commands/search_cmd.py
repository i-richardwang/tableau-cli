from __future__ import annotations

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..output.format import output
from ..utils.search_content_utils import reduce_search_content_response


@click.command("search")
@click.argument("terms", required=False, default=None)
@click.option("--type", "type_", default=None, help="Comma-separated content types (e.g., workbook,view,datasource)")
@click.option("--limit", default=100, type=int, help="Max results")
@click.option("--order-by", default=None, help="Sort method (e.g., hitsTotal:desc)")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def search_command(terms, type_, limit, order_by, fmt):
    """Search across all content types."""
    config = resolve_config()
    filter_parts: list[str] = []
    if type_:
        types = type_.split(",")
        if len(types) == 1:
            filter_parts.append(f"type:eq:{types[0]}")
        else:
            filter_parts.append(f"type:in:[{','.join(types)}]")

    def fn(api):
        response = api.search_content(
            terms=terms,
            page=0,
            limit=limit,
            order_by=order_by,
            filter_=",".join(filter_parts) if filter_parts else None,
        )
        return reduce_search_content_response(response)

    result = with_auth(config, fn)
    output(result, fmt)
