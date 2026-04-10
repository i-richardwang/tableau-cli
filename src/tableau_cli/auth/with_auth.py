from __future__ import annotations

from typing import Any, Callable, TypeVar

import httpx

from ..api.client import RestApi
from ..config.types import Config
from ..errors.cli_error import AuthenticationError

T = TypeVar("T")


def with_auth(config: Config, fn: Callable[[RestApi], T]) -> T:
    api = RestApi(config.server)
    try:
        api.sign_in(
            site_name=config.site_name,
            pat_name=config.pat_name,
            pat_value=config.pat_value,
        )
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        if status in (401, 403):
            raise AuthenticationError(
                f"Sign-in failed (HTTP {status}). The PAT may be expired or invalid."
            )
        raise
    except httpx.ConnectError as e:
        raise AuthenticationError(
            f"Cannot connect to Tableau Server at {config.server}: {e}. Check the server URL."
        )
    try:
        return fn(api)
    finally:
        api.sign_out()
        api.close()
