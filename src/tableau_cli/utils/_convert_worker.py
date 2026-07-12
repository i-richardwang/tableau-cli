"""Standalone hyper -> parquet/csv worker, run in an ephemeral uv environment.

Invoked as:  python _convert_worker.py <hyper_path> <output_path> <parquet|csv>

Must stay self-contained: only pantab / polars + stdlib, no `tableau_cli` imports,
because it runs in a fresh `uv run --with ...` interpreter where this package is
not installed. Known errors are reported as a single JSON line on stdout plus a
non-zero exit; the parent process (utils/convert.py) turns them into CliError.
"""

from __future__ import annotations

import json
import os
import sys


def _fail(error_type: str, message: str, hint: str = "") -> None:
    payload = {"error_type": error_type, "message": message}
    if hint:
        payload["hint"] = hint
    print(json.dumps(payload))
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 4:
        _fail("convert-error", "worker expects <hyper_path> <output_path> <format>")

    hyper_path, output_path, to_fmt = sys.argv[1], sys.argv[2], sys.argv[3]
    name = os.path.basename(hyper_path)

    import pantab

    frames = pantab.frames_from_hyper(hyper_path, return_type="polars")
    if not frames:
        _fail("convert-error", f"No tables found in {name}")
    if len(frames) != 1:
        _fail(
            "convert-error",
            f"Found {len(frames)} tables in {name}, expected 1",
            "Multi-table hyper files are not supported yet.",
        )

    df = next(iter(frames.values()))
    if to_fmt == "parquet":
        df.write_parquet(output_path)
    elif to_fmt == "csv":
        df.write_csv(output_path)
    else:
        _fail("convert-error", f"Unsupported format: {to_fmt}")


if __name__ == "__main__":
    main()
