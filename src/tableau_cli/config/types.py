from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class Config:
    server: str
    site_name: str
    pat_name: str
    pat_value: str


@dataclass
class PartialConfig:
    server: Optional[str] = None
    site_name: Optional[str] = None
    pat_name: Optional[str] = None
    pat_value: Optional[str] = None
