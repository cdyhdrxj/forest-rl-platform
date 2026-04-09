from __future__ import annotations

from importlib import import_module
from typing import Any


__all__ = [
    "AgrocareCoverageService",
    "CoverageEnvConfig",
    "CoverageTrainState",
]


def __getattr__(name: str) -> Any:
    if name in {"CoverageEnvConfig", "CoverageTrainState"}:
        module = import_module("services.agrocare_coverage.models")
        return getattr(module, name)
    if name == "AgrocareCoverageService":
        module = import_module("services.agrocare_coverage.service")
        return getattr(module, name)
    raise AttributeError(f"module 'services.agrocare_coverage' has no attribute {name!r}")
