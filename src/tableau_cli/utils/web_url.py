from __future__ import annotations

from typing import Any


def construct_view_web_url(server: str, site_name: str, content_url: str) -> str:
    """Construct the web URL for opening a Tableau view in a browser.

    The API returns contentUrl as 'workbook/sheets/Sheet1' while the web URL
    uses 'workbook/Sheet1'. The default site omits the /site/{siteName} segment.
    """
    url_path = content_url.replace("/sheets/", "/")

    if not site_name or site_name == "Default":
        return f"{server.rstrip('/')}/#/views/{url_path}"
    return f"{server.rstrip('/')}/#/site/{site_name}/views/{url_path}"


def get_default_view_web_url(workbook: dict[str, Any], server: str, site_name: str) -> str | None:
    """Web URL for a workbook's default view, falling back to its first view."""
    views = (workbook.get("views") or {}).get("view") or []
    if not views:
        return None

    default_view_id = workbook.get("defaultViewId")
    target_view = next((v for v in views if v.get("id") == default_view_id), None) if default_view_id else None
    if target_view is None:
        target_view = views[0]

    if not target_view.get("contentUrl"):
        return None

    return construct_view_web_url(server, site_name, target_view["contentUrl"])
