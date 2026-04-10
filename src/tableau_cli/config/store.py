from __future__ import annotations

import json
import os
from pathlib import Path

from .types import Config, PartialConfig

CONFIG_PATH = Path.home() / ".tableau-cli.json"


def load_file_config() -> PartialConfig:
    try:
        raw = CONFIG_PATH.read_text(encoding="utf-8")
        data = json.loads(raw)
        return PartialConfig(
            server=data.get("server"),
            site_name=data.get("siteName"),
            pat_name=data.get("patName"),
            pat_value=data.get("patValue"),
        )
    except (FileNotFoundError, json.JSONDecodeError):
        return PartialConfig()


def save_file_config(config: PartialConfig) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if config.server is not None:
        data["server"] = config.server
    if config.site_name is not None:
        data["siteName"] = config.site_name
    if config.pat_name is not None:
        data["patName"] = config.pat_name
    if config.pat_value is not None:
        data["patValue"] = config.pat_value
    CONFIG_PATH.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def resolve_config() -> Config:
    file = load_file_config()

    server = os.environ.get("SERVER") or file.server
    site_name = os.environ.get("SITE_NAME") or file.site_name or ""
    pat_name = os.environ.get("PAT_NAME") or file.pat_name
    pat_value = os.environ.get("PAT_VALUE") or file.pat_value

    if not server:
        raise RuntimeError(
            "Missing required config: server. "
            "Set via `tableau-cli config set --server <url>` or SERVER env var."
        )
    if not pat_name or not pat_value:
        raise RuntimeError(
            "Missing required config: patName/patValue. "
            "Set via `tableau-cli config set --pat-name <name> --pat-value <value>` "
            "or PAT_NAME/PAT_VALUE env vars."
        )

    return Config(server=server, site_name=site_name, pat_name=pat_name, pat_value=pat_value)
