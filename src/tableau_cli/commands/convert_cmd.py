from __future__ import annotations

import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

import click

from ..errors.cli_error import CliError
from ..output.format import output

CONVERT_DEPS = ("pantab", "polars", "pyarrow")
SUPPORTED_FORMATS = ("parquet", "csv")


def _check_convert_deps() -> None:
    """Check that optional convert dependencies are installed."""
    missing = [pkg for pkg in CONVERT_DEPS if not _is_importable(pkg)]
    if missing:
        raise CliError(
            error_type="missing-dependencies",
            message=f"Convert requires packages not installed: {', '.join(missing)}",
            hint="Run `pip install tableau-cli[convert]` to install conversion dependencies.",
        )


def _is_importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _extract_hyper_from_tdsx(tdsx_path: Path, target_dir: Path) -> Path:
    """Extract the .hyper file from a TDSX archive."""
    with ZipFile(tdsx_path) as zf:
        members = [m for m in zf.namelist() if m.endswith(".hyper")]
        if len(members) == 0:
            raise CliError(
                error_type="convert-error",
                message=f"No .hyper file found in {tdsx_path.name}",
                hint="This datasource may be a live connection with no embedded data.",
            )
        if len(members) != 1:
            raise CliError(
                error_type="convert-error",
                message=f"Found {len(members)} .hyper files in {tdsx_path.name}, expected 1",
            )
        member = members[0]
        zf.extract(member, path=target_dir)
        extracted = target_dir / member
        if extracted.parent != target_dir:
            final_path = target_dir / extracted.name
            extracted.replace(final_path)
            return final_path
        return extracted


def _read_hyper(hyper_path: Path) -> "pl.DataFrame":
    """Read .hyper file and return as Polars DataFrame."""
    import pantab
    import polars as pl

    frames = pantab.frames_from_hyper(str(hyper_path))
    if not frames:
        raise CliError(
            error_type="convert-error",
            message=f"No tables found in {hyper_path.name}",
        )
    if len(frames) != 1:
        raise CliError(
            error_type="convert-error",
            message=f"Found {len(frames)} tables in {hyper_path.name}, expected 1",
            hint="Multi-table hyper files are not supported yet.",
        )
    return pl.from_pandas(next(iter(frames.values())))


def _write_df(df: "pl.DataFrame", output_path: Path, to: str) -> None:
    """Write DataFrame to the specified format."""
    if to == "parquet":
        df.write_parquet(output_path)
    elif to == "csv":
        df.write_csv(output_path)


@click.command("convert")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--to", "to_fmt", default="parquet", type=click.Choice(SUPPORTED_FORMATS), help="Output format (default: parquet)")
@click.option("-o", "--output", "output_path", default=None, help="Output file path or directory (default: same directory as input)")
def convert_command(input_path, to_fmt, output_path):
    """Convert TDSX/HYPER files to Parquet or CSV format."""
    _check_convert_deps()

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
        df = _read_hyper(input_p)
    else:
        with TemporaryDirectory() as td:
            hyper_path = _extract_hyper_from_tdsx(input_p, Path(td))
            df = _read_hyper(hyper_path)

    _write_df(df, out_p, to_fmt)

    abs_path = os.path.abspath(out_p)
    sys.stderr.write(f"Converted to {abs_path}\n")
    output({"filePath": abs_path}, "json")
