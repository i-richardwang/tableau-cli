from __future__ import annotations

import json
import sys
from typing import Any


def output_json(data: Any) -> None:
    sys.stdout.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
