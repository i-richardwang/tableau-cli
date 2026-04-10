from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Config:
    server: str
    site_name: str
    pat_name: str
    pat_value: str


@dataclass
class PartialConfig:
    server: str | None = None
    site_name: str | None = None
    pat_name: str | None = None
    pat_value: str | None = None
