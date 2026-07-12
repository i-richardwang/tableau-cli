"""Shared helpers for converting TDSX / HYPER files to Parquet or CSV.

The heavy conversion dependencies (pantab / polars / pyarrow) are optional. When
they are not importable in the current interpreter — e.g. the CLI was installed
via `uv tool install` without the `[convert]` extra — conversion transparently
falls back to running a self-contained worker in an ephemeral `uv run --with ...`
environment, so the heavy packages never land in the host Python.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import TYPE_CHECKING
from zipfile import ZipFile

from ..errors.cli_error import CliError

if TYPE_CHECKING:
    import polars as pl

# Import names used to detect in-process availability.
CONVERT_DEPS = ("pantab", "polars", "pyarrow")
# PEP 508 requirements handed to `uv run --with` (keep in sync with pyproject [convert]).
CONVERT_REQUIREMENTS = ("pantab>=4.0", "polars>=1.0", "pyarrow>=15.0")
SUPPORTED_FORMATS = ("parquet", "csv")

_WORKER = Path(__file__).parent / "_convert_worker.py"


def _is_importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except ImportError:
        return False


def _deps_available() -> bool:
    return all(_is_importable(pkg) for pkg in CONVERT_DEPS)


def _uv_available() -> bool:
    return shutil.which("uv") is not None


def ensure_convert_available() -> None:
    """Fail fast if conversion can run neither in-process nor via uv.

    Used by callers that do expensive work (e.g. downloading a datasource) before
    converting, so they can bail out before spending that effort.
    """
    if _deps_available() or _uv_available():
        return
    raise CliError(
        error_type="missing-dependencies",
        message=f"Convert requires packages not installed: {', '.join(CONVERT_DEPS)}",
        hint=(
            "Install uv (https://docs.astral.sh/uv/) to convert without installing these packages, "
            "or run `pip install tableau-cli[convert]`."
        ),
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
    """Read .hyper file and return as Polars DataFrame (in-process path)."""
    import pantab

    frames = pantab.frames_from_hyper(str(hyper_path), return_type="polars")
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
    return next(iter(frames.values()))


def write_df(df: pl.DataFrame, output_path: Path, to: str) -> None:
    """Write DataFrame to the specified format (in-process path)."""
    if to == "parquet":
        df.write_parquet(output_path)
    elif to == "csv":
        df.write_csv(output_path)


def _convert_via_uv(hyper_path: Path, output_path: Path, to_fmt: str) -> None:
    """Convert by running the worker in an ephemeral uv environment.

    uv's own progress (provisioning the environment on first run) is streamed to
    stderr so long first runs are visible; only the worker's stdout is captured,
    where it emits a structured JSON error on failure.
    """
    cmd = ["uv", "run"]
    for req in CONVERT_REQUIREMENTS:
        cmd += ["--with", req]
    cmd += ["python", str(_WORKER), str(hyper_path), str(output_path), to_fmt]

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, text=True)
    if proc.returncode == 0:
        return

    payload = None
    out = (proc.stdout or "").strip()
    if out:
        try:
            payload = json.loads(out.splitlines()[-1])
        except (ValueError, IndexError):
            payload = None

    if isinstance(payload, dict) and payload.get("error_type"):
        raise CliError(
            error_type=payload["error_type"],
            message=payload.get("message", "Conversion failed"),
            hint=payload.get("hint", ""),
        )
    raise CliError(
        error_type="convert-error",
        message="Conversion via uv failed. See the uv output above for details.",
    )


def run_conversion(hyper_path: Path, output_path: Path, to_fmt: str) -> None:
    """Convert a .hyper file to parquet/csv, in-process if deps are present,
    otherwise via an ephemeral uv environment."""
    if _deps_available():
        df = read_hyper(hyper_path)
        write_df(df, output_path, to_fmt)
        return
    if _uv_available():
        _convert_via_uv(hyper_path, output_path, to_fmt)
        return
    ensure_convert_available()  # raises with an actionable hint


def convert_tdsx_bytes(data: bytes, output_path: Path, to_fmt: str) -> None:
    """Convert raw TDSX bytes directly to parquet/csv without persisting the intermediate file."""
    with TemporaryDirectory() as td:
        tmp_dir = Path(td)
        tdsx_path = tmp_dir / "datasource.tdsx"
        tdsx_path.write_bytes(data)
        hyper_path = extract_hyper_from_tdsx(tdsx_path, tmp_dir)
        # Keep the temp dir alive through conversion: the uv worker reads the file from disk.
        run_conversion(hyper_path, output_path, to_fmt)
