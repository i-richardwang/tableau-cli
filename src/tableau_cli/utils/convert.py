"""TDSX extraction and dispatch to the local Hyper export runtime."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from ..errors.cli_error import CliError
from ._hyper_export import HYPER_REQUIREMENT, check_runtime, export_hyper
from ._hyper_export import SUPPORTED_FORMATS as SUPPORTED_FORMATS

_EXPORTER = Path(__file__).parent / "_hyper_export.py"


def _hyper_available() -> bool:
    try:
        import tableauhyperapi  # noqa: F401
    except ImportError:
        return False
    return True


def _run_via_uv(*args: str) -> None:
    command = [
        "uv",
        "run",
        "--no-project",
        "--isolated",
        "--python",
        ">=3.11",
        "--with",
        HYPER_REQUIREMENT,
        "python",
        str(_EXPORTER),
        *args,
    ]
    process = subprocess.run(command, stdout=subprocess.PIPE, text=True)
    if process.returncode == 0:
        return
    try:
        payload = json.loads(process.stdout.strip())
    except ValueError:
        payload = None
    if isinstance(payload, dict) and payload.get("error_type"):
        raise CliError(error_type=payload["error_type"], message=payload.get("message", "Conversion failed"))
    raise CliError(error_type="convert-error", message="Hyper export via uv failed. See stderr for details.")


def _execute(*args: str) -> None:
    try:
        if _hyper_available():
            if not args:
                check_runtime()
            else:
                export_hyper(Path(args[0]), Path(args[1]), args[2])
        elif shutil.which("uv"):
            _run_via_uv(*(args or ("--check",)))
        else:
            raise CliError(
                error_type="missing-dependencies",
                message="Conversion requires tableauhyperapi or uv.",
                hint="Install uv (https://docs.astral.sh/uv/) or run `pip install 'tableau-cli[convert]'`.",
            )
    except CliError:
        raise
    except Exception as exc:
        raise CliError(error_type="convert-error", message=str(exc)) from exc


def ensure_convert_available() -> None:
    """Check engine startup before downloading a datasource for conversion."""
    _execute()


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
        extracted = target_dir / Path(member).name
        with zf.open(member) as source, extracted.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        return extracted


def run_conversion(hyper_path: Path, output_path: Path, to_fmt: str) -> None:
    """Export locally using installed dependencies or an isolated uv environment."""
    _execute(str(hyper_path.absolute()), str(output_path.absolute()), to_fmt)


def convert_tdsx_bytes(data: bytes, output_path: Path, to_fmt: str) -> None:
    """Extract and export downloaded TDSX bytes without retaining intermediate files."""
    with TemporaryDirectory() as td:
        tmp_dir = Path(td)
        tdsx_path = tmp_dir / "datasource.tdsx"
        tdsx_path.write_bytes(data)
        hyper_path = extract_hyper_from_tdsx(tdsx_path, tmp_dir)
        run_conversion(hyper_path, output_path, to_fmt)
