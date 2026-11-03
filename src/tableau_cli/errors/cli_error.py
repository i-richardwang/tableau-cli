from __future__ import annotations

from typing import Any


class CliError(Exception):
    def __init__(
        self,
        *,
        error_type: str,
        message: str,
        details: str | None = None,
        hint: str | None = None,
    ):
        super().__init__(message)
        self.error_type = error_type
        self.details = details
        self.hint = hint

    def to_output(self) -> dict[str, Any]:
        output: dict[str, Any] = {
            "isError": True,
            "errorType": self.error_type,
            "message": str(self),
        }
        if self.details:
            output["details"] = self.details
        if self.hint:
            output["hint"] = self.hint
        return output


class FeatureDisabledError(CliError):
    def __init__(self, message: str, hint: str | None = None):
        super().__init__(error_type="feature-disabled", message=message, hint=hint)


class AuthenticationError(CliError):
    def __init__(self, message: str):
        super().__init__(
            error_type="authentication-error",
            message=message,
            hint=("Check your PAT credentials with `tableau-cli config show`. Ensure the token has not expired."),
        )


class WorkbookDatasourceNotEnabledError(CliError):
    """Raised when a VizQL Data Service call targets an embedded (workbook) datasource on a site
    where workbook-datasource querying is not enabled. This is the expected response on
    non-enabled sites (opt-in per site), not a rare edge case."""

    def __init__(self):
        super().__init__(
            error_type="workbook-datasource-not-enabled",
            message=(
                "This data source is embedded in a workbook, and querying workbook (embedded) data sources "
                "is not enabled on this Tableau site. This capability is opt-in per site: a site administrator "
                "must enable it before this data source can be queried."
            ),
            hint=(
                "Ask a site administrator to enable querying of workbook (embedded) data sources, "
                "or query the published datasource it is built on instead."
            ),
        )
