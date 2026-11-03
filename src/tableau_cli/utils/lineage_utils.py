from __future__ import annotations

import json
import sys
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..api.client import RestApi

# Lineage enrichment (equivalent to lineageUtils.ts in the TS version).
#
# Workbooks, views, and search results are enriched with their upstream published
# datasources via a single batched Metadata API (GraphQL) query. Enrichment is
# best-effort: if the Metadata API is unavailable, the original results are
# returned unchanged and a warning is written to stderr.


def _to_graphql_string_array(values: list[str]) -> str:
    return f"[{', '.join(json.dumps(v) for v in values)}]"


# Published datasources connected via an embedded datasource are only reliably reachable by
# traversing embeddedDatasources -> upstreamDatasources. The Workbook.upstreamDatasources rollup is a
# Catalog-computed field that can be empty even when the embedded -> published lineage edge is
# indexed, so both are queried and unioned (see _collect_published_lineage).
#
# This traversal is workbook-scoped ONLY. A sheet/view must report just the datasources it uses, and
# Workbook.embeddedDatasources is workbook-wide, so unioning it into view lineage would over-attribute
# every published datasource in the workbook to every sheet.
def _workbooks_connection_query(workbook_luids: list[str]) -> str:
    return f"""workbooksConnection(filter: {{ luidWithin: {_to_graphql_string_array(workbook_luids)} }}) {{
        nodes {{
          luid
          upstreamDatasources {{
            luid
            name
          }}
          embeddedDatasources {{
            upstreamDatasources {{
              luid
              name
            }}
          }}
        }}
      }}"""


# REST "views" include worksheets and dashboards; the Metadata API models them separately, so both
# sheetsConnection and dashboardsConnection are queried with the same selection.
_VIEW_CONNECTIONS = ("sheetsConnection", "dashboardsConnection")


def _view_connection_query(connection_name: str, view_luids: list[str]) -> str:
    return f"""{connection_name}(filter: {{ luidWithin: {_to_graphql_string_array(view_luids)} }}) {{
        nodes {{
          luid
          upstreamDatasources {{
            name
            ... on PublishedDatasource {{
              luid
            }}
          }}
          workbook {{
            luid
            name
            projectLuid
            projectName
            owner {{
              luid
              name
              username
            }}
          }}
        }}
      }}"""


def get_workbook_lineage_query(workbook_luids: list[str]) -> str:
    return f"""
    query workbookLineage {{
      {_workbooks_connection_query(workbook_luids)}
    }}"""


def _all_view_connections_query(view_luids: list[str]) -> str:
    return "\n      ".join(_view_connection_query(name, view_luids) for name in _VIEW_CONNECTIONS)


def get_view_lineage_query(view_luids: list[str]) -> str:
    return f"""
    query viewLineage {{
      {_all_view_connections_query(view_luids)}
    }}"""


def get_search_content_lineage_query(workbook_luids: list[str], view_luids: list[str]) -> str:
    return f"""
    query searchContentLineage {{
      {_workbooks_connection_query(workbook_luids) if workbook_luids else ""}
      {_all_view_connections_query(view_luids) if view_luids else ""}
    }}"""


def _collect_published_lineage(
    upstream_datasources: Any,
    embedded_datasources: Any = None,
) -> list[dict[str, str]]:
    """Union the content-level upstream datasources with those reached via embedded datasources.

    Entries without a luid are dropped (embedded datasources carry no luid) and the result is
    deduped by luid preserving first-seen order. When the same luid appears more than once
    (e.g. the content rollup reports a null name but the embedded traversal names it), the first
    non-null name wins so a luid fallback never masks a real name. This is what recovers
    published datasources that the content-level upstreamDatasources rollup omits.
    """
    combined: list[Any] = list(upstream_datasources) if isinstance(upstream_datasources, list) else []
    if isinstance(embedded_datasources, list):
        for embedded in embedded_datasources:
            if isinstance(embedded, dict) and isinstance(embedded.get("upstreamDatasources"), list):
                combined.extend(embedded["upstreamDatasources"])

    by_luid: dict[str, str | None] = {}
    for content in combined:
        if not isinstance(content, dict) or not content.get("luid"):
            continue
        luid = content["luid"]
        name = content.get("name")
        if luid not in by_luid or (by_luid[luid] is None and name is not None):
            by_luid[luid] = name

    return [{"luid": luid, "name": name or luid} for luid, name in by_luid.items()]


def get_workbook_lineage_by_luid(response: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    nodes = (response.get("data") or {}).get("workbooksConnection", {}).get("nodes") or []
    return {
        node["luid"]: _collect_published_lineage(node.get("upstreamDatasources"), node.get("embeddedDatasources"))
        for node in nodes
        if isinstance(node, dict) and node.get("luid")
    }


def get_view_lineage_by_luid(response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data = response.get("data") or {}
    nodes: list[Any] = []
    for connection_name in _VIEW_CONNECTIONS:
        connection = data.get(connection_name)
        if isinstance(connection, dict) and isinstance(connection.get("nodes"), list):
            nodes.extend(connection["nodes"])
    lineage_by_luid: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not node.get("luid"):
            continue
        workbook = node.get("workbook") if isinstance(node.get("workbook"), dict) else None
        owner = workbook.get("owner") if workbook and isinstance(workbook.get("owner"), dict) else None
        lineage_by_luid[node["luid"]] = {
            # View lineage stays sheet-scoped: only the sheet's own upstream (published) datasources,
            # never the parent workbook's full embeddedDatasources set.
            "upstreamDatasources": _collect_published_lineage(node.get("upstreamDatasources")),
            "workbook": (
                {"luid": workbook["luid"], "name": workbook["name"]} if workbook and workbook.get("name") else None
            ),
            "ownerLuid": owner.get("luid") if owner else None,
            "ownerName": (owner.get("name") or owner.get("username")) if owner else None,
            "projectLuid": workbook.get("projectLuid") if workbook else None,
            "projectName": workbook.get("projectName") if workbook else None,
        }
    return lineage_by_luid


def merge_workbook_lineage(
    workbooks: list[dict[str, Any]],
    lineage_by_luid: dict[str, list[dict[str, str]]],
) -> list[dict[str, Any]]:
    for workbook in workbooks:
        upstream_datasources = lineage_by_luid.get(workbook.get("id", ""))
        if upstream_datasources:
            workbook["upstreamDatasources"] = upstream_datasources
    return workbooks


def merge_view_lineage(
    views: list[dict[str, Any]],
    lineage_by_luid: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    for view in views:
        lineage = lineage_by_luid.get(view.get("id", ""))
        if not lineage:
            continue
        if lineage["upstreamDatasources"]:
            view["upstreamDatasources"] = lineage["upstreamDatasources"]
        if lineage["workbook"]:
            workbook = view.setdefault("workbook", {})
            workbook.setdefault("id", lineage["workbook"]["luid"])
            workbook["name"] = lineage["workbook"]["name"]
        if lineage["ownerLuid"] or lineage["ownerName"]:
            owner = view.setdefault("owner", {})
            if lineage["ownerLuid"]:
                owner.setdefault("id", lineage["ownerLuid"])
            if lineage["ownerName"]:
                owner["name"] = lineage["ownerName"]
        if lineage["projectLuid"] or lineage["projectName"]:
            project = view.setdefault("project", {})
            if lineage["projectLuid"]:
                project.setdefault("id", lineage["projectLuid"])
            if lineage["projectName"]:
                project["name"] = lineage["projectName"]
    return views


def _warn_enrichment_failed(subject: str, exc: Exception) -> None:
    sys.stderr.write(f"Warning: failed to enrich {subject} with lineage metadata: {exc}\n")


def enrich_workbooks_with_lineage(api: RestApi, workbooks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not workbooks:
        return workbooks
    try:
        response = api.graphql(get_workbook_lineage_query([w["id"] for w in workbooks]))
        return merge_workbook_lineage(workbooks, get_workbook_lineage_by_luid(response))
    except Exception as exc:
        _warn_enrichment_failed("workbooks", exc)
        return workbooks


def enrich_views_with_lineage(api: RestApi, views: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not views:
        return views
    try:
        response = api.graphql(get_view_lineage_query([v["id"] for v in views]))
        return merge_view_lineage(views, get_view_lineage_by_luid(response))
    except Exception as exc:
        _warn_enrichment_failed("views", exc)
        return views


def enrich_search_results_with_lineage(api: RestApi, search_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Attach upstreamDatasources to workbook and view search results."""

    def luids_of_type(content_type: str) -> list[str]:
        return [r["luid"] for r in search_results if r.get("type") == content_type and isinstance(r.get("luid"), str)]

    workbook_luids = luids_of_type("workbook")
    view_luids = luids_of_type("view")
    if not workbook_luids and not view_luids:
        return search_results

    try:
        response = api.graphql(get_search_content_lineage_query(workbook_luids, view_luids))
        workbook_lineage_by_luid = get_workbook_lineage_by_luid(response)
        view_lineage_by_luid = get_view_lineage_by_luid(response)
    except Exception as exc:
        _warn_enrichment_failed("search results", exc)
        return search_results

    for item in search_results:
        if item.get("type") == "workbook":
            upstream_datasources = workbook_lineage_by_luid.get(item.get("luid", ""))
        elif item.get("type") == "view":
            lineage = view_lineage_by_luid.get(item.get("luid", ""))
            upstream_datasources = lineage["upstreamDatasources"] if lineage else None
        else:
            continue
        if upstream_datasources:
            item["upstreamDatasources"] = upstream_datasources
    return search_results
