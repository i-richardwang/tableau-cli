"""Shared helpers for converting TDSX / HYPER files to Parquet or CSV."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import ZipFile

from ..errors.cli_error import CliError

if TYPE_CHECKING:
    import polars as pl

CONVERT_DEPS = ("pantab", "polars", "pyarrow")
SUPPORTED_FORMATS = ("parquet", "csv")


def _is_importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def check_convert_deps() -> None:
    """Check that optional convert dependencies are installed."""
    missing = [pkg for pkg in CONVERT_DEPS if not _is_importable(pkg)]
    if missing:
        raise CliError(
            error_type="missing-dependencies",
            message=f"Convert requires packages not installed: {', '.join(missing)}",
            hint="Run `pip install tableau-cli[convert]` to install conversion dependencies.",
        )


def extract_hyper_from_tdsx(tdsx_path: Path, target_dir: Path) -> Path:
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


def read_hyper(hyper_path: Path) -> pl.DataFrame:
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


def write_df(df: pl.DataFrame, output_path: Path, to: str) -> None:
    """Write DataFrame to the specified format."""
    if to == "parquet":
        df.write_parquet(output_path)
    elif to == "csv":
        df.write_csv(output_path)


def convert_tdsx_bytes(data: bytes, output_path: Path, to_fmt: str) -> None:
    """Convert raw TDSX bytes directly to parquet/csv without persisting the intermediate file."""
    with TemporaryDirectory() as td:
        tmp_dir = Path(td)
        tdsx_path = tmp_dir / "datasource.tdsx"
        tdsx_path.write_bytes(data)
        hyper_path = extract_hyper_from_tdsx(tdsx_path, tmp_dir)
        df = read_hyper(hyper_path)
    write_df(df, output_path, to_fmt)
