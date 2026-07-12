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


def _workbooks_connection_query(workbook_luids: list[str]) -> str:
    return f"""workbooksConnection(filter: {{ luidWithin: {_to_graphql_string_array(workbook_luids)} }}) {{
        nodes {{
          luid
          upstreamDatasources {{
            luid
            name
          }}
        }}
      }}"""


def _sheets_connection_query(view_luids: list[str]) -> str:
    return f"""sheetsConnection(filter: {{ luidWithin: {_to_graphql_string_array(view_luids)} }}) {{
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


def get_view_lineage_query(view_luids: list[str]) -> str:
    return f"""
    query viewLineage {{
      {_sheets_connection_query(view_luids)}
    }}"""


def get_search_content_lineage_query(workbook_luids: list[str], view_luids: list[str]) -> str:
    return f"""
    query searchContentLineage {{
      {_workbooks_connection_query(workbook_luids) if workbook_luids else ""}
      {_sheets_connection_query(view_luids) if view_luids else ""}
    }}"""


def _normalize_lineage_contents(contents: Any) -> list[dict[str, str]]:
    if not isinstance(contents, list):
        return []
    return [
        {"luid": c["luid"], "name": c.get("name") or c["luid"]}
        for c in contents
        if isinstance(c, dict) and c.get("luid")
    ]


def get_workbook_lineage_by_luid(response: dict[str, Any]) -> dict[str, list[dict[str, str]]]:
    nodes = response.get("data", {}).get("workbooksConnection", {}).get("nodes") or []
    return {
        node["luid"]: _normalize_lineage_contents(node.get("upstreamDatasources"))
        for node in nodes
        if isinstance(node, dict) and node.get("luid")
    }


def get_view_lineage_by_luid(response: dict[str, Any]) -> dict[str, dict[str, Any]]:
    nodes = response.get("data", {}).get("sheetsConnection", {}).get("nodes") or []
    lineage_by_luid: dict[str, dict[str, Any]] = {}
    for node in nodes:
        if not isinstance(node, dict) or not node.get("luid"):
            continue
        workbook = node.get("workbook") if isinstance(node.get("workbook"), dict) else None
        owner = workbook.get("owner") if workbook and isinstance(workbook.get("owner"), dict) else None
        lineage_by_luid[node["luid"]] = {
            "upstreamDatasources": _normalize_lineage_contents(node.get("upstreamDatasources")),
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
