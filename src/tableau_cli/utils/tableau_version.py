from __future__ import annotations


def is_tableau_version_at_least(product_version: str, min_version: str) -> bool:
    """Check whether a Tableau product version meets a minimum release version.

    Mirrors the TS isTableauVersionAtLeast helper: builds from the main branch
    ("main") or unrecognized version formats are assumed to be fresh builds and
    pass the check.
    """
    if product_version == "main":
        return True

    try:
        year, major, minor = (int(part) for part in product_version.split("."))
    except ValueError:
        return True

    min_year, min_major, min_minor = (int(part) for part in min_version.split("."))

    return (year, major, minor) >= (min_year, min_major, min_minor)
