from __future__ import annotations

from typing import Any


def is_tableau_version_at_least(product_version: dict[str, Any], min_version: str) -> bool:
    """Check whether the server's product version meets a minimum release version.

    `product_version` is the serverinfo object: {"value": "2025.3.0", "build": "20253.25.0101.1234"}.
    Development servers report "0.0.0" or a build from the main branch (e.g. main.26.1005.0759);
    both are treated as fresh builds and pass the check, as are unrecognized version formats.
    """
    value = str(product_version.get("value") or "")
    build = str(product_version.get("build") or "")

    if value == "0.0.0" or "main" in build:
        return True

    try:
        year, major, minor = (int(part) for part in value.split(".")[:3])
    except ValueError:
        return True

    min_year, min_major, min_minor = (int(part) for part in min_version.split("."))

    return (year, major, minor) >= (min_year, min_major, min_minor)
