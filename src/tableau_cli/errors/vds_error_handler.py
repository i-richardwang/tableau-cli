from __future__ import annotations

from .cli_error import CliError

# condition and details texts are aligned word-for-word with MCP's queryDatasourceErrorHandler.ts.
# hint is CLI-specific added value (agent-friendly actionable guidance).
VDS_ERROR_MAP: dict[str, dict[str, str | None]] = {
    "400000": {
        "condition": "Bad request",
        "details": "The content of the request body is invalid. Check for missing or incomplete JSON.",
        "hint": "Verify the --query JSON is valid and complete.",
    },
    "400800": {
        "condition": "Invalid formula for calculation",
        "details": "Invalid custom calculation syntax. For help, see https://help.tableau.com/current/pro/desktop/en-us/functions_operators.htm",
        "hint": None,
    },
    "400802": {
        "condition": "Invalid API request",
        "details": "The incoming request isn't valid per the OpenAPI specification.",
        "hint": None,
    },
    "400803": {
        "condition": "Validation failed",
        "details": "The incoming request isn't valid per the validation rules.",
        "hint": (
            "Check that all field names and filter values match the datasource metadata. "
            "Use `tableau-cli datasources metadata <luid>` to verify available fields."
        ),
    },
    "400804": {
        "condition": "Response too large",
        "details": "The response value exceeds the limit. You must apply a filter in your request.",
        "hint": "Use --limit to restrict row count, or add filters to your query.",
    },
    "401001": {
        "condition": "Login error",
        "details": "The login failed for the given user.",
        "hint": "Check your PAT credentials with `tableau-cli config show`.",
    },
    "401002": {
        "condition": "Invalid authorization credentials",
        "details": "The provided auth token is formatted incorrectly.",
        "hint": (
            "Re-authenticate by updating your PAT with `tableau-cli config set --pat-name <name> --pat-value <value>`."
        ),
    },
    "403157": {
        "condition": "Feature disabled",
        "details": "The feature is disabled.",
        "hint": (
            "Ask your Tableau Server admin to enable VizQL Data Service via TSM. "
            "See https://help.tableau.com/current/server-linux/en-us/cli_configuration-set_tsm.htm"
        ),
    },
    "403800": {
        "condition": "API access permission denied",
        "details": (
            "The user doesn't have API Access granted on the given data source. "
            "Set the API Access capability for the given data source to Allowed. "
            "For help, see https://help.tableau.com/current/online/en-us/permissions_capabilities.htm"
        ),
        "hint": None,
    },
    "404934": {
        "condition": "Unknown field",
        "details": "The requested field doesn't exist.",
        "hint": ("Use `tableau-cli datasources metadata <luid>` to see available fields and their exact names."),
    },
    "404950": {
        "condition": "API endpoint not found",
        "details": "The request endpoint doesn't exist.",
        "hint": "This feature may not be available on your Tableau Server version.",
    },
    "408000": {
        "condition": "Request timeout",
        "details": "The request timed out.",
        "hint": "Try adding filters to reduce the data volume, or simplify your query.",
    },
    "429000": {
        "condition": "Too many requests",
        "details": (
            "Too many requests in the allotted amount of time. "
            "For help, see https://help.tableau.com/current/api/vizql-data-service/en-us/docs/vds_limitations.html#licensing-and-data-transfer"
        ),
        "hint": "Wait before retrying.",
    },
    "409000": {
        "condition": "User already on site",
        "details": "HTTP status conflict.",
        "hint": None,
    },
    "500000": {
        "condition": "Internal server error",
        "details": "The request could not be completed.",
        "hint": None,
    },
    "500810": {
        "condition": "VDS empty table response",
        "details": "The underlying data engine returned empty data value response.",
        "hint": "The datasource may have no data, or your filters may be too restrictive.",
    },
    "500811": {
        "condition": "VDS missing table",
        "details": "The underlying data engine returned empty metadata associated with response.",
        "hint": None,
    },
    "500812": {
        "condition": "Error while processing an error",
        "details": "Internal processing error.",
        "hint": None,
    },
    "501000": {
        "condition": "Not implemented",
        "details": "Can't find response from upstream server.",
        "hint": None,
    },
    "503800": {
        "condition": "VDS unavailable",
        "details": "The underlying data engine is unavailable.",
        "hint": "The server may be under maintenance. Try again later.",
    },
    "503801": {
        "condition": "VDS discovery error",
        "details": "The upstream service can't be found.",
        "hint": "The server may be under maintenance. Try again later.",
    },
    "504000": {
        "condition": "Gateway timeout",
        "details": "The upstream service response timed out.",
        "hint": "Try a simpler query with fewer fields or more restrictive filters.",
    },
}


def handle_vds_error(
    error_message: str,
    http_status: int,
    tableau_error_code: str | None,
) -> CliError:
    entry = VDS_ERROR_MAP.get(tableau_error_code or "")

    if entry:
        condition = entry["condition"]
        return CliError(
            error_type=condition or "tableau-error",
            message=f"{condition}: {error_message}" if condition else error_message,
            details=entry.get("details"),
            hint=entry.get("hint"),
        )

    return CliError(
        error_type="tableau-error",
        message=error_message,
    )
