from __future__ import annotations

from typing import Any


def _get_reduced_search_item_content(content: dict[str, Any]) -> dict[str, Any]:
    r: dict[str, Any] = {}
    if content.get("modifiedTime"):
        r["modifiedTime"] = content["modifiedTime"]
    if content.get("sheetType"):
        r["sheetType"] = content["sheetType"]
    if content.get("caption"):
        r["caption"] = content["caption"]
    if content.get("workbookDescription"):
        r["workbookDescription"] = content["workbookDescription"]
    if content.get("type"):
        r["type"] = content["type"]
    if content.get("ownerId"):
        r["ownerId"] = content["ownerId"]
    if content.get("title"):
        r["title"] = content["title"]
    if content.get("ownerName"):
        r["ownerName"] = content["ownerName"]
    if content.get("containerName"):
        if content.get("type") == "view":
            r["parentWorkbookName"] = content["containerName"]
        else:
            r["containerName"] = content["containerName"]
    if content.get("luid"):
        r["luid"] = content["luid"]
    if content.get("locationName"):
        r["locationName"] = content["locationName"]
    if isinstance(content.get("comments"), list) and content["comments"]:
        r["comments"] = content["comments"]
    if content.get("hitsTotal") is not None:
        r["totalViewCount"] = content["hitsTotal"]
    if content.get("favoritesTotal") is not None:
        r["favoritesTotal"] = content["favoritesTotal"]
    if isinstance(content.get("tags"), list) and content["tags"]:
        r["tags"] = content["tags"]
    if content.get("projectId"):
        r["projectId"] = content["projectId"]
    if content.get("projectName"):
        r["projectName"] = content["projectName"]
    if content.get("hitsSmallSpanTotal") is not None:
        r["viewCountLastMonth"] = content["hitsSmallSpanTotal"]
    if content.get("downstreamWorkbookCount") is not None:
        r["downstreamWorkbookCount"] = content["downstreamWorkbookCount"]
    if content.get("isConnectable") is not None:
        r["isConnectable"] = content["isConnectable"]
    if content.get("datasourceIsPublished") is not None:
        r["datasourceIsPublished"] = content["datasourceIsPublished"]
    if content.get("connectionType"):
        r["connectionType"] = content["connectionType"]
    if content.get("isCertified") is not None:
        r["isCertified"] = content["isCertified"]
    if content.get("hasExtracts") is not None:
        r["hasExtracts"] = content["hasExtracts"]
    if content.get("extractRefreshedAt"):
        r["extractRefreshedAt"] = content["extractRefreshedAt"]
    if content.get("extractUpdatedAt"):
        r["extractUpdatedAt"] = content["extractUpdatedAt"]
    if content.get("connectedWorkbooksCount") is not None:
        r["connectedWorkbooksCount"] = content["connectedWorkbooksCount"]
    if content.get("extractCreationPending") is not None:
        r["extractCreationPending"] = content["extractCreationPending"]
    if content.get("hasSevereDataQualityWarning") is not None:
        r["hasSevereDataQualityWarning"] = content["hasSevereDataQualityWarning"]
    if content.get("datasourceLuid"):
        r["datasourceLuid"] = content["datasourceLuid"]
    if content.get("hasActiveDataQualityWarning") is not None:
        r["hasActiveDataQualityWarning"] = content["hasActiveDataQualityWarning"]
    return r


def reduce_search_content_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    search_results: list[dict[str, Any]] = []
    items = response.get("items") or []
    for item in items:
        search_results.append(_get_reduced_search_item_content(item.get("content", {})))

    # Remove duplicate datasources with luid matching a unifieddatasource's datasourceLuid
    unified_datasource_luids: set[str] = set()
    for item in search_results:
        if item.get("type") == "unifieddatasource" and isinstance(item.get("datasourceLuid"), str):
            unified_datasource_luids.add(item["datasourceLuid"])

    search_results = [
        item
        for item in search_results
        if not (
            item.get("type") == "datasource"
            and isinstance(item.get("luid"), str)
            and item["luid"] in unified_datasource_luids
        )
    ]

    # Normalize unifieddatasource entries to datasource entries
    for item in search_results:
        if item.get("type") == "unifieddatasource":
            item["type"] = "datasource"
            item["luid"] = item.pop("datasourceLuid", None)

    return search_results
