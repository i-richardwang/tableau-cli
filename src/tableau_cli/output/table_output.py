from __future__ import annotations

import json
import sys
from typing import Any


def _format_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    if isinstance(value, list):
        if len(value) == 0:
            return ""
        # Handle tags: [{"label": "x"}, ...]
        if isinstance(value[0], dict) and "label" in value[0]:
            return ", ".join(v.get("label", "") for v in value)
        return ", ".join(_format_value(v) for v in value)
    if isinstance(value, dict):
        # Handle tags object: {"tag": [{"label": "x"}, ...]}
        if "tag" in value:
            tag = value["tag"]
            if isinstance(tag, list):
                return ", ".join(t.get("label", "") for t in tag)
            return ""
        # Handle empty-like objects
        non_null = {k: v for k, v in value.items() if v is not None}
        if not non_null:
            return ""
        # Handle common nested objects
        if "name" in value and value["name"]:
            return str(value["name"])
        if "id" in value and value["id"]:
            return str(value["id"])
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def output_table(rows: list[dict[str, Any]]) -> None:
    if not rows:
        sys.stdout.write("(no results)\n")
        return

    columns = list(rows[0].keys())
    formatted = [
        {col: _format_value(row.get(col)) for col in columns} for row in rows
    ]

    widths = [
        max(len(col), *(len(row[col]) for row in formatted)) for col in columns
    ]

    header = "  ".join(col.upper().ljust(w) for col, w in zip(columns, widths))
    separator = "  ".join("-" * w for w in widths)

    sys.stdout.write(header + "\n")
    sys.stdout.write(separator + "\n")

    for row in formatted:
        line = "  ".join(row[col].ljust(w) for col, w in zip(columns, widths))
        sys.stdout.write(line + "\n")
