from __future__ import annotations

from typing import Any, Callable, Optional


def paginate(
    *,
    page_size: Optional[int] = None,
    limit: Optional[int] = None,
    get_data_fn: Callable[[Optional[int], Optional[int]], dict[str, Any]],
) -> list[Any]:
    """Paginate through Tableau REST API results.

    get_data_fn(page_size, page_number) should return {"pagination": {...}, "data": [...]}.
    """
    response = get_data_fn(page_size, None)
    pagination = response["pagination"]
    result = list(response["data"])

    total_available: int = pagination["totalAvailable"]
    page_number: int = pagination["pageNumber"]

    while total_available > len(result) and (not limit or limit > len(result)):
        response = get_data_fn(page_size, page_number + 1)
        next_data = response["data"]

        if len(next_data) == 0:
            raise RuntimeError(
                f"No more data available. Last fetched page number: {page_number}, "
                f"Total available: {total_available}, Total fetched: {len(result)}"
            )

        pagination = response["pagination"]
        total_available = pagination["totalAvailable"]
        page_number = pagination["pageNumber"]
        result.extend(next_data)

    if limit and limit < len(result):
        result = result[:limit]

    return result
