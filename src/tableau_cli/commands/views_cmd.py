from __future__ import annotations

import os
import sys
from typing import Any

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..output.format import output
from ..utils.lineage_utils import enrich_views_with_lineage
from ..utils.paginate import paginate
from ..utils.web_url import construct_view_web_url


def _parse_view_filters(vf: tuple[str, ...]) -> dict[str, str] | None:
    """Parse repeated --vf 'Field=Value' options into a view filter map."""
    if not vf:
        return None
    view_filters: dict[str, str] = {}
    for entry in vf:
        field, sep, value = entry.partition("=")
        if not sep or not field:
            raise click.BadParameter(f"Expected 'Field=Value', got '{entry}'.", param_hint="--vf")
        view_filters[field] = value
    return view_filters


def _flatten_view_usage(views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flatten usage statistics into a top-level totalViewCount (consistent with MCP behavior)."""
    for view in views:
        usage = view.pop("usage", None)
        view["totalViewCount"] = usage.get("totalViewCount", 0) if isinstance(usage, dict) else 0
    return views


@click.group("views")
def views_group():
    """Manage views."""


@views_group.command("list")
@click.option("--filter", "filter_", default=None, help="Filter string (e.g., name:has:Sales)")
@click.option("--page-size", default=None, type=int, help="Page size for API requests")
@click.option("--limit", default=None, type=int, help="Max total results")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def views_list(filter_, page_size, limit, fmt):
    """List views on the site."""
    config = resolve_config()

    def fn(api):
        def get_data_fn(ps, pn):
            result = api.query_views_for_site(
                site_id=api.site_id,
                filter_=filter_ or "",
                page_size=ps,
                page_number=pn,
            )
            return {"pagination": result["pagination"], "data": result["views"]}

        views = paginate(page_size=page_size, limit=limit, get_data_fn=get_data_fn)
        return _flatten_view_usage(enrich_views_with_lineage(api, views))

    result = with_auth(config, fn)
    output(result, fmt)


@views_group.command("get")
@click.argument("view_id")
@click.option("--format", "fmt", default="json", help="Output format: json | table")
def views_get(view_id, fmt):
    """Get view details, including upstream datasources and web URL."""
    config = resolve_config()

    def fn(api):
        view = api.get_view(view_id=view_id, site_id=api.site_id)
        view = enrich_views_with_lineage(api, [view])[0]
        view["url"] = construct_view_web_url(config.server, config.site_name, view["contentUrl"])
        return view

    result = with_auth(config, fn)
    output(result, fmt)


@views_group.command("data")
@click.argument("view_id")
@click.option("--vf", multiple=True, help="View filter as 'Field=Value' (repeatable)")
def views_data(view_id, vf):
    """Get view data as CSV."""
    config = resolve_config()
    view_filters = _parse_view_filters(vf)
    csv = with_auth(
        config,
        lambda api: api.query_view_data(view_id=view_id, site_id=api.site_id, view_filters=view_filters),
    )
    sys.stdout.write(csv)


@views_group.command("image")
@click.argument("view_id")
@click.option("--width", default=None, type=int, help="Image width in pixels")
@click.option("--height", default=None, type=int, help="Image height in pixels")
@click.option("--img-format", default="PNG", help="Image format: PNG | SVG")
@click.option("--vf", multiple=True, help="View filter as 'Field=Value' (repeatable)")
@click.option("-o", "--output", "output_path", default=None, help="Output file path")
def views_image(view_id, width, height, img_format, vf, output_path):
    """Download view image."""
    config = resolve_config()
    view_filters = _parse_view_filters(vf)

    image_data = with_auth(
        config,
        lambda api: api.query_view_image(
            view_id=view_id,
            site_id=api.site_id,
            width=width,
            height=height,
            format_=img_format,
            view_filters=view_filters,
        ),
    )

    if output_path:
        with open(output_path, "wb") as f:
            f.write(image_data)
        abs_path = os.path.abspath(output_path)
        sys.stderr.write(f"Image saved to {abs_path}\n")
        output({"filePath": abs_path}, "json")
    else:
        import base64

        sys.stdout.write(base64.b64encode(image_data).decode("ascii"))
