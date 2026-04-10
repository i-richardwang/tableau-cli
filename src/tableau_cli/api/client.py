from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import httpx

from ..errors.cli_error import CliError, FeatureDisabledError
from ..errors.vds_error_handler import handle_vds_error

API_VERSION = "3.24"
TIMEOUT_S = 120

VDS_DISABLED_MESSAGE = (
    "The VizQL Data Service is disabled on this Tableau Server. "
    "To enable it, use TSM using the instructions at "
    "https://help.tableau.com/current/server-linux/en-us/cli_configuration-set_tsm.htm"
    "#featuresvizqldataservicedeploywithtsm."
)


@dataclass
class Credentials:
    site_id: str
    user_id: str
    token: str


class RestApi:
    def __init__(self, host: str) -> None:
        self._host = host.rstrip("/")
        self._creds: Optional[Credentials] = None
        self._client = httpx.Client(
            timeout=TIMEOUT_S,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    @property
    def _base_url(self) -> str:
        return f"{self._host}/api/{API_VERSION}"

    @property
    def _base_url_no_version(self) -> str:
        return f"{self._host}/api/-"

    @property
    def _creds_required(self) -> Credentials:
        if not self._creds:
            raise RuntimeError("Not authenticated. Call sign_in() first.")
        return self._creds

    @property
    def site_id(self) -> str:
        return self._creds_required.site_id

    @property
    def user_id(self) -> str:
        return self._creds_required.user_id

    def _auth_headers(self) -> dict[str, str]:
        return {"X-Tableau-Auth": self._creds_required.token}

    # ── Authentication ──────────────────────────────────────────────

    def sign_in(self, *, site_name: str, pat_name: str, pat_value: str) -> None:
        url = f"{self._base_url}/auth/signin"
        body = {
            "credentials": {
                "site": {"contentUrl": site_name},
                "personalAccessTokenName": pat_name,
                "personalAccessTokenSecret": pat_value,
            }
        }
        resp = self._client.post(url, json=body)
        resp.raise_for_status()
        creds = resp.json()["credentials"]
        self._creds = Credentials(
            site_id=creds["site"]["id"],
            user_id=creds["user"]["id"],
            token=creds["token"],
        )

    def sign_out(self) -> None:
        if not self._creds:
            return
        url = f"{self._base_url}/auth/signout"
        try:
            self._client.post(url, headers=self._auth_headers())
        except Exception:
            pass
        self._creds = None

    # ── Datasources (REST API) ──────────────────────────────────────

    def list_datasources(
        self,
        *,
        site_id: str,
        filter_: str = "",
        page_size: Optional[int] = None,
        page_number: Optional[int] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/datasources"
        params: dict[str, Any] = {}
        if filter_:
            params["filter"] = filter_
        if page_size is not None:
            params["pageSize"] = page_size
        if page_number is not None:
            params["pageNumber"] = page_number
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("datasources", {}).get("datasource") or []
        return {
            "pagination": _parse_pagination(data["pagination"]),
            "datasources": [_shape_datasource(d) for d in raw_list],
        }

    # ── Views (REST API) ────────────────────────────────────────────

    def query_views_for_site(
        self,
        *,
        site_id: str,
        filter_: str = "",
        page_size: Optional[int] = None,
        page_number: Optional[int] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/views"
        params: dict[str, Any] = {"includeUsageStatistics": "true"}
        if filter_:
            params["filter"] = filter_
        if page_size is not None:
            params["pageSize"] = page_size
        if page_number is not None:
            params["pageNumber"] = page_number
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("views", {}).get("view") or []
        return {
            "pagination": _parse_pagination(data["pagination"]),
            "views": [_shape_view(v) for v in raw_list],
        }

    def query_view_data(self, *, view_id: str, site_id: str) -> str:
        url = f"{self._base_url}/sites/{site_id}/views/{view_id}/data"
        resp = self._client.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.text

    def query_view_image(
        self,
        *,
        view_id: str,
        site_id: str,
        width: Optional[int] = None,
        height: Optional[int] = None,
        format_: str = "PNG",
    ) -> bytes:
        url = f"{self._base_url}/sites/{site_id}/views/{view_id}/image"
        params: dict[str, Any] = {"resolution": "high"}
        if width is not None:
            params["vizWidth"] = width
        if height is not None:
            params["vizHeight"] = height
        if format_:
            params["format"] = format_
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        if resp.status_code >= 400:
            error_data: dict[str, Any] = {}
            try:
                error_data = resp.json()
            except Exception:
                try:
                    error_data = {"error": None}
                    text = resp.text
                    import json as _json
                    error_data = _json.loads(text)
                except Exception:
                    resp.raise_for_status()
            if error_data.get("error", {}).get("code") == "403157":
                is_svg = format_ == "SVG"
                raise FeatureDisabledError(
                    "SVG format is not supported on this Tableau Server. It requires Tableau 2026.2.0 or later."
                    if is_svg
                    else "The image format feature is disabled on this Tableau Server.",
                    hint="Retry with --img-format PNG instead." if is_svg else None,
                )
            if error_data.get("error"):
                err = error_data["error"]
                summary = err.get("summary", "")
                detail = err.get("detail", "")
                raise CliError(
                    error_type="view-image-error",
                    message=f"{summary}: {detail}" if detail else summary,
                )
            resp.raise_for_status()
        return resp.content

    def query_views_for_workbook(
        self, *, workbook_id: str, site_id: str
    ) -> list[dict[str, Any]]:
        url = f"{self._base_url}/sites/{site_id}/workbooks/{workbook_id}/views"
        params = {"includeUsageStatistics": "true"}
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        raw_list = resp.json()["views"]["view"]
        return [_shape_view(v) for v in raw_list]

    # ── Workbooks (REST API) ────────────────────────────────────────

    def get_workbook(self, *, workbook_id: str, site_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/workbooks/{workbook_id}"
        resp = self._client.get(url, headers=self._auth_headers())
        resp.raise_for_status()
        return _shape_workbook(resp.json()["workbook"])

    def query_workbooks_for_site(
        self,
        *,
        site_id: str,
        filter_: str = "",
        page_size: Optional[int] = None,
        page_number: Optional[int] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/workbooks"
        params: dict[str, Any] = {}
        if filter_:
            params["filter"] = filter_
        if page_size is not None:
            params["pageSize"] = page_size
        if page_number is not None:
            params["pageNumber"] = page_number
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("workbooks", {}).get("workbook") or []
        return {
            "pagination": _parse_pagination(data["pagination"]),
            "workbooks": [_shape_workbook(w) for w in raw_list],
        }

    # ── Content Exploration (Search) ────────────────────────────────

    def search_content(
        self,
        *,
        terms: Optional[str] = None,
        page: Optional[int] = None,
        limit: Optional[int] = None,
        order_by: Optional[str] = None,
        filter_: Optional[str] = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url_no_version}/search"
        params: dict[str, Any] = {}
        if terms is not None:
            params["terms"] = terms
        if page is not None:
            params["page"] = page
        if limit is not None:
            params["limit"] = limit
        if order_by is not None:
            params["order_by"] = order_by
        if filter_ is not None:
            params["filter"] = filter_
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.json()["hits"]

    # ── VizQL Data Service ──────────────────────────────────────────

    def read_metadata(self, *, datasource_luid: str) -> dict[str, Any]:
        url = f"{self._host}/api/v1/vizql-data-service/read-metadata"
        body = {"datasource": {"datasourceLuid": datasource_luid}}
        try:
            resp = self._client.post(url, json=body, headers=self._auth_headers())
        except httpx.TransportError:
            raise FeatureDisabledError(VDS_DISABLED_MESSAGE)
        if resp.status_code == 404:
            raise FeatureDisabledError(VDS_DISABLED_MESSAGE)
        resp.raise_for_status()
        return resp.json()

    def query_datasource(self, *, datasource_luid: str, query: dict, options: Optional[dict] = None) -> dict[str, Any]:
        url = f"{self._host}/api/v1/vizql-data-service/query-datasource"
        body: dict[str, Any] = {
            "datasource": {"datasourceLuid": datasource_luid},
            "query": query,
        }
        if options:
            body["options"] = options
        try:
            resp = self._client.post(url, json=body, headers=self._auth_headers())
        except httpx.TransportError:
            raise FeatureDisabledError(VDS_DISABLED_MESSAGE)
        if resp.status_code == 404:
            raise FeatureDisabledError(VDS_DISABLED_MESSAGE)
        if resp.status_code >= 400:
            try:
                data = resp.json()
            except Exception:
                resp.raise_for_status()
                return {}  # unreachable
            error_message = data.get("message", "Unknown Tableau error")
            error_code = data.get("errorCode") or data.get("tab-error-code")
            raise handle_vds_error(error_message, resp.status_code, error_code)
        return resp.json()

    # ── Metadata API (GraphQL) ──────────────────────────────────────

    def graphql(self, query: str) -> dict[str, Any]:
        url = f"{self._host}/api/metadata/graphql"
        resp = self._client.post(
            url, json={"query": query}, headers=self._auth_headers()
        )
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._client.close()


def _parse_pagination(p: dict[str, Any]) -> dict[str, int]:
    return {
        "pageNumber": int(p["pageNumber"]),
        "pageSize": int(p["pageSize"]),
        "totalAvailable": int(p["totalAvailable"]),
    }


# ── Response shaping (equivalent to Zod schemas in TS version) ──────────


def _shape_project(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {"name": "", "id": ""}
    return {"name": raw.get("name", ""), "id": raw.get("id", "")}


def _shape_tags(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    tag = raw.get("tag")
    if isinstance(tag, list):
        return {"tag": [{"label": t["label"]} for t in tag if isinstance(t, dict) and "label" in t]}
    return {}


def _shape_datasource(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS dataSourceSchema: {id, name, description?, project, tags}"""
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
    }
    if "description" in raw:
        result["description"] = raw["description"]
    result["project"] = _shape_project(raw.get("project"))
    result["tags"] = _shape_tags(raw.get("tags"))
    return result


def _shape_view(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS viewSchema: {id, name, createdAt, updatedAt, workbook?, owner?, project?, tags, usage?}"""
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "createdAt": raw.get("createdAt", ""),
        "updatedAt": raw.get("updatedAt", ""),
    }
    if "workbook" in raw and isinstance(raw["workbook"], dict):
        result["workbook"] = {"id": raw["workbook"].get("id", "")}
    if "owner" in raw and isinstance(raw["owner"], dict):
        result["owner"] = {"id": raw["owner"].get("id", "")}
    if "project" in raw and isinstance(raw["project"], dict):
        result["project"] = {"id": raw["project"].get("id", "")}
    result["tags"] = _shape_tags(raw.get("tags"))
    if "usage" in raw and isinstance(raw["usage"], dict):
        result["usage"] = {"totalViewCount": int(raw["usage"].get("totalViewCount", 0))}
    return result


def _shape_workbook(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS workbookSchema: {id, name, description?, webpageUrl?, contentUrl, project?, showTabs, defaultViewId?, tags, views?}"""
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
    }
    if "description" in raw:
        result["description"] = raw["description"]
    if "webpageUrl" in raw:
        result["webpageUrl"] = raw["webpageUrl"]
    result["contentUrl"] = raw.get("contentUrl", "")
    if "project" in raw:
        result["project"] = _shape_project(raw.get("project"))
    # z.coerce.boolean() — convert string "true"/"false" to bool
    show_tabs = raw.get("showTabs", False)
    if isinstance(show_tabs, str):
        result["showTabs"] = show_tabs.lower() == "true"
    else:
        result["showTabs"] = bool(show_tabs)
    if "defaultViewId" in raw:
        result["defaultViewId"] = raw["defaultViewId"]
    result["tags"] = _shape_tags(raw.get("tags"))
    if "views" in raw and isinstance(raw["views"], dict):
        views_list = raw["views"].get("view", [])
        result["views"] = {
            "view": [_shape_view(v) for v in views_list] if isinstance(views_list, list) else []
        }
    return result
