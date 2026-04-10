from __future__ import annotations

from typing import Any

from .json_output import output_json
from .table_output import output_table


def output(data: Any, fmt: str) -> None:
    if fmt == "table" and isinstance(data, list):
        output_table(data)
    else:
        output_json(data)
