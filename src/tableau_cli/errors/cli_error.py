from __future__ import annotations

from typing import Any, Optional


class CliError(Exception):
    def __init__(
        self,
        *,
        error_type: str,
        message: str,
        details: Optional[str] = None,
        hint: Optional[str] = None,
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
    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(error_type="feature-disabled", message=message, hint=hint)


class AuthenticationError(CliError):
    def __init__(self, message: str):
        super().__init__(
            error_type="authentication-error",
            message=message,
            hint=(
                "Check your PAT credentials with `tableau-cli config show`. "
                "Ensure the token has not expired."
            ),
        )
