from __future__ import annotations

import os
import sys

import click

from ..auth.with_auth import with_auth
from ..config.store import resolve_config
from ..output.format import output
from ..utils.paginate import paginate


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

        return paginate(page_size=page_size, limit=limit, get_data_fn=get_data_fn)

    result = with_auth(config, fn)
    output(result, fmt)


@views_group.command("data")
@click.argument("view_id")
def views_data(view_id):
    """Get view data as CSV."""
    config = resolve_config()
    csv = with_auth(config, lambda api: api.query_view_data(view_id=view_id, site_id=api.site_id))
    sys.stdout.write(csv)


@views_group.command("image")
@click.argument("view_id")
@click.option("--width", default=None, type=int, help="Image width in pixels")
@click.option("--height", default=None, type=int, help="Image height in pixels")
@click.option("--img-format", default="PNG", help="Image format: PNG | SVG")
@click.option("-o", "--output", "output_path", default=None, help="Output file path")
def views_image(view_id, width, height, img_format, output_path):
    """Download view image."""
    config = resolve_config()

    image_data = with_auth(
        config,
        lambda api: api.query_view_image(
            view_id=view_id,
            site_id=api.site_id,
            width=width,
            height=height,
            format_=img_format,
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
