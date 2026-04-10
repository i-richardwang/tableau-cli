from __future__ import annotations

import json

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..output.format import output
from ..utils.paginate import paginate


@click.group("datasources")
def datasources_group():
    """Manage data sources."""


# Alias: allow 'ds' as well
ds_group = datasources_group


@datasources_group.command("list")
@click.option("--filter", "filter_", default=None, help="Filter string (e.g., name:eq:Superstore)")
@click.option("--page-size", default=None, type=int, help="Page size for API requests")
@click.option("--limit", default=None, type=int, help="Max total results")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def datasources_list(filter_, page_size, limit, fmt):
    """List published data sources."""
    config = resolve_config()

    def fn(api):
        def get_data_fn(ps, pn):
            result = api.list_datasources(
                site_id=api.site_id,
                filter_=filter_ or "",
                page_size=ps,
                page_number=pn,
            )
            return {"pagination": result["pagination"], "data": result["datasources"]}

        return paginate(page_size=page_size, limit=limit, get_data_fn=get_data_fn)

    result = with_auth(config, fn)
    output(result, fmt)


@datasources_group.command("metadata")
@click.argument("luid")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def datasources_metadata(luid, fmt):
    """Get data source field metadata."""
    config = resolve_config()

    def fn(api):
        from ..utils.datasource_metadata_utils import (
            combine_fields,
            get_graphql_query,
            simplify_read_metadata_result,
        )

        read_metadata_result = api.read_metadata(datasource_luid=luid)

        # Try to enrich with Metadata API (GraphQL)
        try:
            graphql_result = api.graphql(get_graphql_query(luid))
        except Exception:
            # Metadata API may not be available
            return simplify_read_metadata_result(read_metadata_result)

        return combine_fields(read_metadata_result, graphql_result)

    result = with_auth(config, fn)
    output(result, fmt)


@datasources_group.command("query")
@click.argument("luid")
@click.option("--query", "query_json", required=True, help="Query JSON (fields, filters, etc.)")
@click.option("--limit", default=None, type=int, help="Row limit")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def datasources_query(luid, query_json, limit, fmt):
    """Query a data source using VizQL Data Service."""
    config = resolve_config()
    query = json.loads(query_json)

    def fn(api):
        # Note: rowLimit is NOT sent to the API (consistent with MCP default behavior
        # for Tableau versions < 2026.1.0 where server-side row limits are unsupported).
        # Instead, truncation is done client-side after the response.
        query_result = api.query_datasource(
            datasource_luid=luid,
            query=query,
            options={
                "returnFormat": "OBJECTS",
                "debug": True,
                "disaggregate": False,
            },
        )

        if limit and query_result.get("data") and len(query_result["data"]) > limit:
            query_result["data"] = query_result["data"][:limit]

        return query_result

    result = with_auth(config, fn)
    output(result, fmt)
