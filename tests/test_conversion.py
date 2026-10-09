"""Exercise local Hyper exports and the isolated execution contract."""

from __future__ import annotations

import csv
import io
import json
import subprocess
import sys
import tomllib
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from zipfile import ZipFile

import pyarrow as pa
import pyarrow.parquet as pq
import pytest
from tableauhyperapi import (
    Connection,
    CreateMode,
    HyperProcess,
    Inserter,
    SqlType,
    TableDefinition,
    TableName,
    Telemetry,
)

from tableau_cli.errors.cli_error import CliError
from tableau_cli.utils import convert
from tableau_cli.utils._hyper_export import HYPER_REQUIREMENT, export_hyper

ROOT = Path(__file__).resolve().parents[1]
EXPORTER = ROOT / "src/tableau_cli/utils/_hyper_export.py"


@pytest.fixture
def hyper_file(tmp_path):
    path = tmp_path / "input.hyper"
    with (
        HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hyper,
        Connection(hyper.endpoint, str(path), CreateMode.CREATE_AND_REPLACE) as connection,
    ):
        connection.catalog.create_schema('Data " schema')
        table = TableDefinition(
            TableName('Data " schema', "table's data"),
            [
                TableDefinition.Column("id", SqlType.int()),
                TableDefinition.Column("text", SqlType.text()),
                TableDefinition.Column("amount", SqlType.numeric(12, 2)),
                TableDefinition.Column("day", SqlType.date()),
                TableDefinition.Column("timestamp", SqlType.timestamp()),
                TableDefinition.Column("instant", SqlType.timestamp_tz()),
                TableDefinition.Column("active", SqlType.bool()),
                TableDefinition.Column("bytes", SqlType.bytes()),
            ],
        )
        connection.catalog.create_table(table)
        with Inserter(connection, table) as inserter:
            inserter.add_rows(
                [
                    [
                        1,
                        '中文,"quote"\nline',
                        Decimal("123.45"),
                        date(2026, 10, 9),
                        datetime(2026, 10, 9, 12, 34, 56, 123456),
                        datetime(2026, 10, 9, 12, 34, 56, tzinfo=UTC),
                        True,
                        b"\x00\xff",
                    ],
                    [2, None, None, None, None, None, None, None],
                ]
            )
            inserter.execute()
    return path


def assert_parquet(path):
    table = pq.read_table(path)
    assert table.column_names == ["id", "text", "amount", "day", "timestamp", "instant", "active", "bytes"]
    assert table.schema.field("id").type == pa.int32()
    assert table.schema.field("amount").type == pa.decimal128(12, 2)
    rows = table.to_pylist()
    assert len(rows) == 2
    assert rows[0] == {
        "id": 1,
        "text": '中文,"quote"\nline',
        "amount": Decimal("123.45"),
        "day": date(2026, 10, 9),
        "timestamp": datetime(2026, 10, 9, 12, 34, 56, 123456),
        "instant": datetime(2026, 10, 9, 12, 34, 56, tzinfo=UTC),
        "active": True,
        "bytes": b"\x00\xff",
    }
    assert rows[1] == {name: 2 if name == "id" else None for name in table.column_names}


@pytest.mark.parametrize("to_fmt", ["parquet", "csv"])
def test_export(hyper_file, tmp_path, to_fmt):
    destination = tmp_path / f"output ' 中文.{to_fmt}"
    convert.run_conversion(hyper_file, destination, to_fmt)
    if to_fmt == "parquet":
        assert_parquet(destination)
    else:
        with destination.open(newline="", encoding="utf-8") as stream:
            rows = list(csv.DictReader(stream))
        assert len(rows) == 2
        assert rows[0]["text"] == '中文,"quote"\nline'
        assert rows[0]["amount"] == "123.45"
        assert rows[0]["day"] == "2026-10-09"
        assert rows[1]["text"] == ""


def test_downloaded_tdsx(hyper_file, tmp_path):
    archive = io.BytesIO()
    with ZipFile(archive, "w") as zf:
        zf.write(hyper_file, "Data/Extracts/input.hyper")
    destination = tmp_path / "download.parquet"
    convert.convert_tdsx_bytes(archive.getvalue(), destination, "parquet")
    assert_parquet(destination)


@pytest.mark.parametrize("count", [0, 2])
def test_table_count_preserves_destination(tmp_path, count):
    source = tmp_path / "tables.hyper"
    destination = tmp_path / "result.parquet"
    destination.write_bytes(b"existing output")
    with (
        HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hyper,
        Connection(hyper.endpoint, str(source), CreateMode.CREATE_AND_REPLACE) as connection,
    ):
        for index in range(count):
            connection.catalog.create_table(
                TableDefinition(
                    TableName(f"table{index}"),
                    [
                        TableDefinition.Column("id", SqlType.int()),
                    ],
                )
            )
    with pytest.raises(CliError, match="No tables|expected 1"):
        convert.run_conversion(source, destination, "parquet")
    assert destination.read_bytes() == b"existing output"
    assert not list(tmp_path.glob(".tableau-export-*"))


def test_empty_table(hyper_file, tmp_path):
    with (
        HyperProcess(Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU, parameters={"log_config": ""}) as hyper,
        Connection(hyper.endpoint, str(hyper_file)) as connection,
    ):
        connection.execute_command('DELETE FROM "Data "" schema"."table\'s data"')
    destination = tmp_path / "empty.parquet"
    export_hyper(hyper_file, destination, "parquet")
    assert pq.read_table(destination).num_rows == 0


def test_source_cannot_be_overwritten(hyper_file):
    original = hyper_file.read_bytes()
    with pytest.raises(ValueError, match="must differ"):
        export_hyper(hyper_file, hyper_file, "parquet")
    assert hyper_file.read_bytes() == original


def test_failed_export_preserves_destination(hyper_file, tmp_path, monkeypatch):
    destination = tmp_path / "result.parquet"
    destination.write_bytes(b"existing output")

    def fail_copy(self, command):
        raise RuntimeError("export failed")

    monkeypatch.setattr(Connection, "execute_command", fail_copy)
    with pytest.raises(CliError, match="export failed"):
        convert.run_conversion(hyper_file, destination, "parquet")
    assert destination.read_bytes() == b"existing output"
    assert not list(tmp_path.glob(".tableau-export-*"))


def test_worker(hyper_file, tmp_path):
    destination = tmp_path / "worker.parquet"
    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(hyper_file), str(destination), "parquet"], capture_output=True, text=True
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout == ""
    assert_parquet(destination)


def test_worker_error(tmp_path):
    result = subprocess.run(
        [sys.executable, str(EXPORTER), str(tmp_path / "missing.hyper"), str(tmp_path / "result.parquet"), "parquet"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert json.loads(result.stdout)["error_type"] == "convert-error"


def test_uv_conversion(hyper_file, tmp_path, monkeypatch):
    monkeypatch.setattr(convert, "_hyper_available", lambda: False)
    convert.ensure_convert_available()
    destination = tmp_path / "uv.parquet"
    convert.run_conversion(hyper_file, destination, "parquet")
    assert_parquet(destination)


def test_dependency_contract():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert project["project"]["optional-dependencies"]["convert"] == [HYPER_REQUIREMENT]


@pytest.mark.parametrize("suffix", ["hyper", "tdsx"])
def test_cli_output(hyper_file, tmp_path, suffix):
    from click.testing import CliRunner

    from tableau_cli.cli import cli
    from tableau_cli.commands.convert_cmd import convert_command

    cli.add_command(convert_command)
    source = hyper_file
    if suffix == "tdsx":
        source = tmp_path / "input.tdsx"
        with ZipFile(source, "w") as archive:
            archive.write(hyper_file, "Data/input.hyper")
    destination = tmp_path / "result.parquet"
    result = CliRunner().invoke(cli, ["convert", str(source), "-o", str(destination)])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout) == {"filePath": str(destination.resolve())}
    assert "Converted to" in result.stderr
    assert_parquet(destination)


def test_missing_dependencies(monkeypatch, tmp_path):
    monkeypatch.setattr(convert, "_hyper_available", lambda: False)
    monkeypatch.setattr(convert.shutil, "which", lambda name: None)
    with pytest.raises(CliError) as error:
        convert.run_conversion(tmp_path / "input.hyper", tmp_path / "output.parquet", "parquet")
    assert error.value.error_type == "missing-dependencies"


def test_engine_check_precedes_download(monkeypatch):
    from click.testing import CliRunner

    from tableau_cli.cli import cli
    from tableau_cli.commands import datasources_cmd

    cli.add_command(datasources_cmd.datasources_group)
    monkeypatch.setattr(datasources_cmd, "resolve_config", lambda: None)

    def fail_startup():
        raise RuntimeError("engine startup failed")

    def unexpected_download(*args, **kwargs):
        pytest.fail("Download must not run when engine startup fails")

    monkeypatch.setattr(convert, "check_runtime", fail_startup)
    monkeypatch.setattr(datasources_cmd, "with_auth", unexpected_download)
    result = CliRunner().invoke(cli, ["datasources", "download", "test-id", "--to", "parquet"])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["errorType"] == "convert-error"
    assert "engine startup failed" in result.stdout


@pytest.mark.parametrize("suffix", ["hyper", "tdsx"])
def test_cli_preserves_input(hyper_file, tmp_path, suffix):
    from click.testing import CliRunner

    from tableau_cli.cli import cli
    from tableau_cli.commands.convert_cmd import convert_command

    cli.add_command(convert_command)
    source = hyper_file
    if suffix == "tdsx":
        source = tmp_path / "input.tdsx"
        with ZipFile(source, "w") as archive:
            archive.write(hyper_file, "Data/input.hyper")
    original = source.read_bytes()
    result = CliRunner().invoke(cli, ["convert", str(source), "-o", str(source)])
    assert result.exit_code == 1
    assert json.loads(result.stdout)["errorType"] == "invalid-input"
    assert source.read_bytes() == original
