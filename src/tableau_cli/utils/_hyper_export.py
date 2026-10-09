"""Local Hyper exports, shared by the CLI and isolated Python execution."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

HYPER_REQUIREMENT = "tableauhyperapi>=0.0.26479"
SUPPORTED_FORMATS = ("parquet", "csv")


def _start_hyper():
    from tableauhyperapi import HyperException, HyperProcess, Telemetry

    try:
        return HyperProcess(
            Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU,
            parameters={"log_config": "", "date_style": "YMD"},
        )
    except HyperException as exc:
        raise RuntimeError(
            "Unable to start the local Hyper engine. Use a native 64-bit Python on a supported platform "
            f"and reinstall tableau-cli[convert]. Details: {exc}"
        ) from exc


def check_runtime() -> None:
    """Verify that the installed Hyper engine can start."""
    with _start_hyper():
        pass


def export_hyper(hyper_path: Path, output_path: Path, to_fmt: str) -> None:
    """Export a single-table Hyper file, replacing the destination only on success."""
    from tableauhyperapi import Connection, escape_string_literal

    if to_fmt not in SUPPORTED_FORMATS:
        raise ValueError(f"Unsupported format: {to_fmt}")
    source = hyper_path.resolve()
    destination = output_path.absolute()
    if source == destination.resolve():
        raise ValueError("The output path must differ from the input Hyper file.")

    with TemporaryDirectory(prefix=".tableau-export-", dir=destination.parent) as td:
        staged = Path(td) / f"data.{to_fmt}"
        with _start_hyper() as hyper, Connection(hyper.endpoint, str(source)) as connection:
            tables = [
                table
                for schema in connection.catalog.get_schema_names()
                for table in connection.catalog.get_table_names(schema)
            ]
            if not tables:
                raise ValueError(f"No tables found in {hyper_path.name}")
            if len(tables) != 1:
                raise ValueError(f"Found {len(tables)} tables in {hyper_path.name}, expected 1")

            options = f"FORMAT => {escape_string_literal(to_fmt)}"
            if to_fmt == "csv":
                options += ", HEADER => true"
            connection.execute_command(f"COPY {tables[0]} TO {escape_string_literal(str(staged))} WITH ({options})")
        staged.replace(destination)


def main() -> None:
    """Report worker failures as structured JSON for the parent CLI."""
    try:
        if sys.argv[1:] == ["--check"]:
            check_runtime()
        elif len(sys.argv) == 4:
            export_hyper(Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3])
        else:
            raise ValueError("Expected --check or <hyper_path> <output_path> <parquet|csv>")
    except Exception as exc:
        print(json.dumps({"error_type": "convert-error", "message": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
