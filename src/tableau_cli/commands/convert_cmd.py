from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

import click

from ..errors.cli_error import CliError
from ..output.format import output
from ..utils.convert import (
    SUPPORTED_FORMATS,
    check_convert_deps,
    extract_hyper_from_tdsx,
    read_hyper,
    write_df,
)


@click.command("convert")
@click.argument("input_path", type=click.Path(exists=True))
@click.option(
    "--to", "to_fmt", default="parquet", type=click.Choice(SUPPORTED_FORMATS), help="Output format (default: parquet)"
)
@click.option("-o", "--output", "output_path", default=None, help="Output file or directory (default: same as input)")
def convert_command(input_path, to_fmt, output_path):
    """Convert TDSX/HYPER files to Parquet or CSV format."""
    check_convert_deps()

    input_p = Path(input_path)
    suffix = input_p.suffix.lower()

    if suffix not in (".tdsx", ".hyper"):
        raise CliError(
            error_type="invalid-input",
            message=f"Unsupported file type: {suffix}",
            hint="Supported formats: .tdsx, .hyper",
        )

    # Resolve output path
    ext = f".{to_fmt}"
    if output_path is None:
        out_p = input_p.with_suffix(ext)
    elif os.path.isdir(output_path):
        out_p = Path(output_path) / f"{input_p.stem}{ext}"
    else:
        out_p = Path(output_path)

    # Read hyper data
    if suffix == ".hyper":
        df = read_hyper(input_p)
    else:
        with TemporaryDirectory() as td:
            hyper_path = extract_hyper_from_tdsx(input_p, Path(td))
            df = read_hyper(hyper_path)

    write_df(df, out_p, to_fmt)

    abs_path = os.path.abspath(out_p)
    sys.stderr.write(f"Converted to {abs_path}\n")
    output({"filePath": abs_path}, "json")
