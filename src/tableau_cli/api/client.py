from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from typing import Any

import httpx

from ..errors.cli_error import CliError, FeatureDisabledError, WorkbookDatasourceNotEnabledError
from ..errors.vds_error_handler import handle_vds_error

# REST API version used for the unauthenticated serverinfo call. Every later request uses the
# version the server reports there (restApiVersion), so version-gated features key off the server.
MIN_API_VERSION = "3.24"
TIMEOUT_S = 120

VDS_DISABLED_MESSAGE = (
    "The VizQL Data Service is disabled on this Tableau Server. "
    "To enable it, use TSM using the instructions at "
    "https://help.tableau.com/current/server-linux/en-us/cli_configuration-set_tsm.htm"
    "#featuresvizqldataservicedeploywithtsm."
)

# Appended to the VDS-disabled message by query_datasource on REST API < 3.30: there a 404 can also
# mean the target is an embedded (workbook) datasource, which those versions do not support.
EMBEDDED_DATASOURCE_VERSION_HINT = (
    "This can also occur when querying an embedded (workbook) datasource on Tableau Server REST API "
    "versions below 3.30, which do not support embedded datasource queries. Published datasources are unaffected."
)

# Site-scoped opt-in flag required to query embedded (workbook) datasources. The server enforces it as
# HTTP 403 / errorCode 403800 on every VDS endpoint; 403800 alone is a generic denial, so the flag name
# in the message is what identifies this gate (equivalent to isWorkbookDatasourceNotEnabled in TS).
WORKBOOK_DS_NOT_ENABLED_FLAG = "VDSForWorkbookDatasources"


@dataclass
class Credentials:
    site_id: str
    user_id: str
    token: str


class RestApi:
    def __init__(self, host: str) -> None:
        self._host = host.rstrip("/")
        self._creds: Credentials | None = None
        self._version = MIN_API_VERSION
        self._server_info: dict[str, Any] | None = None
        self._client = httpx.Client(
            timeout=TIMEOUT_S,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )

    @property
    def version(self) -> str:
        """REST API version in use: the one reported by the server once sign_in() has run."""
        return self._version

    def version_is_at_least(self, version: str) -> bool:
        """Compare the REST API version in use against a "major.minor" string (e.g. "3.30")."""
        return _major_minor(self._version) >= _major_minor(version)

    @property
    def _base_url(self) -> str:
        return f"{self._host}/api/{self._version}"

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
        self._load_server_info()
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
        with contextlib.suppress(Exception):
            self._client.post(url, headers=self._auth_headers())
        self._creds = None

    # ── Server (REST API) ───────────────────────────────────────────

    def _load_server_info(self) -> None:
        """GET /serverinfo (needs no authentication) and adopt the REST API version it reports."""
        url = f"{self._host}/api/{MIN_API_VERSION}/serverinfo"
        try:
            resp = self._client.get(url)
            resp.raise_for_status()
            info = resp.json()["serverInfo"]
            version = info["restApiVersion"]
            if not re.fullmatch(r"\d+\.\d+", version):
                raise ValueError(f"unexpected restApiVersion {version!r}")
        except (httpx.HTTPError, KeyError, TypeError, ValueError) as exc:
            raise CliError(error_type="tableau-api-error", message=f"Failed to get server info: {exc}") from exc
        self._server_info = info
        self._version = version

    def get_server_info(self) -> dict[str, Any]:
        """Server info ({productVersion: {value, build}, restApiVersion, ...}) fetched during sign-in."""
        if self._server_info is None:
            raise RuntimeError("Not authenticated. Call sign_in() first.")
        return self._server_info

    # ── Datasources (REST API) ──────────────────────────────────────

    def list_datasources(
        self,
        *,
        site_id: str,
        filter_: str = "",
        page_size: int | None = None,
        page_number: int | None = None,
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

    def resolve_datasource_type(self, *, datasource_id: str, site_id: str) -> str | None:
        """Classify a LUID as "published" or "embedded" (workbook) via the Query Data Source endpoint.

        Servers with workbook-datasource querying enabled return embedded datasources here too
        (parentType "Workbook", no project); published ones carry a project. Older servers answer
        404 for embedded LUIDs, so a 404 for a LUID that VizQL Data Service already resolved also
        means embedded. Any other failure returns None: classification is best-effort and must never
        break the caller's response.
        """
        url = f"{self._base_url}/sites/{site_id}/datasources/{datasource_id}"
        try:
            resp = self._client.get(url, headers=self._auth_headers())
            if resp.status_code == 404:
                return "embedded"
            resp.raise_for_status()
            datasource = _shape_datasource(resp.json()["datasource"])
        except (httpx.HTTPError, KeyError, TypeError, ValueError):
            return None
        return "embedded" if _is_embedded_datasource(datasource) else "published"

    def download_datasource(self, *, datasource_id: str, site_id: str) -> tuple[bytes, str]:
        """Download datasource content. Returns (data, filename)."""
        url = f"{self._base_url}/sites/{site_id}/datasources/{datasource_id}/content"
        resp = self._client.get(url, headers=self._auth_headers())
        resp.raise_for_status()

        # Extract filename from Content-Disposition header
        filename = f"{datasource_id}.tdsx"
        cd = resp.headers.get("content-disposition", "")
        if "filename*=" in cd:
            # RFC 5987: filename*=UTF-8''encoded_name.tdsx
            part = cd.split("filename*=", 1)[1].split(";", 1)[0].strip()
            if "''" in part:
                from urllib.parse import unquote

                filename = unquote(part.split("''", 1)[1])
        elif "filename=" in cd:
            from urllib.parse import unquote_plus

            part = cd.split("filename=", 1)[1].split(";", 1)[0].strip()
            filename = unquote_plus(part.strip('"'))

        return resp.content, filename

    # ── Views (REST API) ────────────────────────────────────────────

    def query_views_for_site(
        self,
        *,
        site_id: str,
        filter_: str = "",
        page_size: int | None = None,
        page_number: int | None = None,
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

    def get_view(self, *, view_id: str, site_id: str) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/views/{view_id}"
        params = {"includeUsageStatistics": "true"}
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        return _shape_view(resp.json()["view"])

    def query_view_data(self, *, view_id: str, site_id: str, view_filters: dict[str, str] | None = None) -> str:
        url = f"{self._base_url}/sites/{site_id}/views/{view_id}/data"
        params = _view_filter_params(view_filters)
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        return resp.text

    def query_view_image(
        self,
        *,
        view_id: str,
        site_id: str,
        width: int | None = None,
        height: int | None = None,
        format_: str = "PNG",
        view_filters: dict[str, str] | None = None,
    ) -> bytes:
        url = f"{self._base_url}/sites/{site_id}/views/{view_id}/image"
        params: dict[str, Any] = {"resolution": "high"}
        if width is not None:
            params["vizWidth"] = width
        if height is not None:
            params["vizHeight"] = height
        if format_:
            params["format"] = format_
        params.update(_view_filter_params(view_filters))
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

    def query_views_for_workbook(self, *, workbook_id: str, site_id: str) -> list[dict[str, Any]]:
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
        page_size: int | None = None,
        page_number: int | None = None,
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

    # ── Projects (REST API) ─────────────────────────────────────────

    def query_projects(
        self,
        *,
        site_id: str,
        filter_: str = "",
        capability: str | None = None,
        page_size: int | None = None,
        page_number: int | None = None,
    ) -> dict[str, Any]:
        url = f"{self._base_url}/sites/{site_id}/projects"
        params: dict[str, Any] = {}
        if filter_:
            params["filter"] = filter_
        if capability:
            params["capability"] = capability
        if page_size is not None:
            params["pageSize"] = page_size
        if page_number is not None:
            params["pageNumber"] = page_number
        resp = self._client.get(url, params=params, headers=self._auth_headers())
        resp.raise_for_status()
        data = resp.json()
        raw_list = data.get("projects", {}).get("project") or []
        return {
            "pagination": _parse_pagination(data["pagination"]),
            "projects": [_shape_project_detail(p) for p in raw_list],
        }

    # ── Content Exploration (Search) ────────────────────────────────

    def search_content(
        self,
        *,
        terms: str | None = None,
        page: int | None = None,
        limit: int | None = None,
        order_by: str | None = None,
        filter_: str | None = None,
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

    def _vds_post(
        self, endpoint: str, body: dict[str, Any], *, not_found_message: str = VDS_DISABLED_MESSAGE
    ) -> dict[str, Any]:
        """POST to a VizQL Data Service endpoint and return the JSON body, translating failures.

        The workbook-datasource gate is detected by message (not status) and is checked before the
        404 branch so it is never mislabeled as "VizQL Data Service disabled". Any 404 means the
        service is disabled; `not_found_message` lets an endpoint add context to that error.
        """
        url = f"{self._host}/api/v1/vizql-data-service/{endpoint}"
        try:
            resp = self._client.post(url, json=body, headers=self._auth_headers())
        except httpx.TransportError as exc:
            raise FeatureDisabledError(VDS_DISABLED_MESSAGE) from exc
        if resp.status_code < 400:
            return resp.json()
        error = _safe_json(resp) or {}
        if _is_workbook_datasource_not_enabled(error):
            raise WorkbookDatasourceNotEnabledError()
        if resp.status_code == 404:
            raise FeatureDisabledError(not_found_message)
        raise handle_vds_error(
            error.get("message", "Unknown Tableau error"),
            resp.status_code,
            error.get("errorCode") or error.get("tab-error-code"),
        )

    def read_metadata(self, *, datasource_luid: str) -> dict[str, Any]:
        return self._vds_post("read-metadata", {"datasource": {"datasourceLuid": datasource_luid}})

    def get_datasource_model(self, *, datasource_luid: str) -> dict[str, Any]:
        return self._vds_post("get-datasource-model", {"datasource": {"datasourceLuid": datasource_luid}})

    def query_datasource(self, *, datasource_luid: str, query: dict, options: dict | None = None) -> dict[str, Any]:
        body: dict[str, Any] = {
            "datasource": {"datasourceLuid": datasource_luid},
            "query": query,
        }
        if options:
            body["options"] = options
        # Below REST API 3.30 a 404 here can also mean an embedded datasource rather than a disabled service.
        not_found_message = (
            VDS_DISABLED_MESSAGE
            if self.version_is_at_least("3.30")
            else f"{VDS_DISABLED_MESSAGE} {EMBEDDED_DATASOURCE_VERSION_HINT}"
        )
        return self._vds_post("query-datasource", body, not_found_message=not_found_message)

    # ── Metadata API (GraphQL) ──────────────────────────────────────

    def graphql(self, query: str) -> dict[str, Any]:
        url = f"{self._host}/api/metadata/graphql"
        resp = self._client.post(url, json={"query": query}, headers=self._auth_headers())
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


def _major_minor(version: str) -> tuple[int, int]:
    major, minor = version.split(".")
    return int(major), int(minor)


def _safe_json(resp: httpx.Response) -> dict[str, Any] | None:
    try:
        data = resp.json()
    except Exception:
        return None
    return data if isinstance(data, dict) else None


def _is_workbook_datasource_not_enabled(error_body: dict[str, Any]) -> bool:
    message = error_body.get("message")
    return isinstance(message, str) and WORKBOOK_DS_NOT_ENABLED_FLAG.lower() in message.lower()


def _tableau_boolean(value: Any) -> bool:
    """Tableau REST may deliver booleans as the strings "true"/"false"; never treat "false" as true."""
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return value is True


def _view_filter_params(view_filters: dict[str, str] | None) -> dict[str, str]:
    """Map view filter field names to `vf_`-prefixed query parameters."""
    if not view_filters:
        return {}
    return {(key if key.startswith("vf_") else f"vf_{key}"): value for key, value in view_filters.items()}


# ── Response shaping (equivalent to Zod schemas in TS version) ──────────


def _shape_project(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict):
        return {"name": "", "id": ""}
    return {"name": raw.get("name", ""), "id": raw.get("id", "")}


def _shape_project_detail(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS projectSchema: {id, name, description?, parentProjectId?, contentPermissions?, ...}"""
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
    }
    for key in (
        "description",
        "parentProjectId",
        "contentPermissions",
        "controllingPermissionsProjectId",
        "createdAt",
        "updatedAt",
    ):
        if key in raw:
            result[key] = raw[key]
    if "topLevelProject" in raw:
        result["topLevelProject"] = _tableau_boolean(raw["topLevelProject"])
    if isinstance(raw.get("owner"), dict) and raw["owner"].get("id"):
        result["owner"] = {"id": raw["owner"]["id"]}
    return result


def _shape_tags(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    tag = raw.get("tag")
    if isinstance(tag, list):
        return {"tag": [{"label": t["label"]} for t in tag if isinstance(t, dict) and "label" in t]}
    return {}


def _shape_datasource(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS dataSourceSchema:
    {id, name, contentUrl?, description?, createdAt?, isCertified?, project?, parentType?, owner?, tags}

    `project` is optional: embedded (workbook) datasources carry `parentType: "Workbook"` and no project.
    """
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
    }
    for key in ("contentUrl", "description", "createdAt"):
        if key in raw:
            result[key] = raw[key]
    if "isCertified" in raw:
        result["isCertified"] = _tableau_boolean(raw["isCertified"])
    if isinstance(raw.get("project"), dict):
        result["project"] = _shape_project(raw["project"])
    if "parentType" in raw:
        result["parentType"] = raw["parentType"]
    if isinstance(raw.get("owner"), dict) and raw["owner"].get("id"):
        result["owner"] = {"id": raw["owner"]["id"]}
    result["tags"] = _shape_tags(raw.get("tags"))
    return result


def _is_embedded_datasource(datasource: dict[str, Any]) -> bool:
    """Some servers return a `project` on embedded datasources too, so `parentType` is checked first."""
    return datasource.get("parentType") == "Workbook" or not datasource.get("project")


def _shape_view(raw: dict[str, Any]) -> dict[str, Any]:
    """Match TS viewSchema: {id, name, contentUrl, createdAt, updatedAt, workbook?, owner?, project?, tags, usage?}"""
    result: dict[str, Any] = {
        "id": raw.get("id", ""),
        "name": raw.get("name", ""),
        "contentUrl": raw.get("contentUrl", ""),
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
    """Match TS workbookSchema: id, name, description?, webpageUrl?, contentUrl, project?, showTabs, etc."""
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
    result["showTabs"] = _tableau_boolean(raw.get("showTabs"))
    if "defaultViewId" in raw:
        result["defaultViewId"] = raw["defaultViewId"]
    result["tags"] = _shape_tags(raw.get("tags"))
    if "views" in raw and isinstance(raw["views"], dict):
        views_list = raw["views"].get("view", [])
        result["views"] = {"view": [_shape_view(v) for v in views_list] if isinstance(views_list, list) else []}
    return result
