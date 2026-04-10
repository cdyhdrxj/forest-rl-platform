from __future__ import annotations

from importlib import import_module
from typing import Any


_EXPORT_MAP = {
    "build_continuous_coverage_request": ("services.scenario_generator.adapters", "build_continuous_coverage_request"),
    "apply_patrol_generation": ("services.scenario_generator.adapters", "apply_patrol_generation"),
    "build_continuous_trail_request": ("services.scenario_generator.adapters", "build_continuous_trail_request"),
    "build_coverage_runtime_config": ("services.scenario_generator.adapters", "build_coverage_runtime_config"),
    "build_patrol_grid_request": ("services.scenario_generator.adapters", "build_patrol_grid_request"),
    "build_reforestation_request": ("services.scenario_generator.adapters", "build_reforestation_request"),
    "build_simulator_3d_request": ("services.scenario_generator.adapters", "build_simulator_3d_request"),
    "extract_coverage_runtime_layout": ("services.scenario_generator.adapters", "extract_coverage_runtime_layout"),
    "extract_continuous_runtime_kwargs": ("services.scenario_generator.adapters", "extract_continuous_runtime_kwargs"),
    "extract_reforestation_runtime_layout": ("services.scenario_generator.adapters", "extract_reforestation_runtime_layout"),
    "extract_simulator_3d_runtime_config": ("services.scenario_generator.adapters", "extract_simulator_3d_runtime_config"),
    "get_default_environment_generation_service": (
        "services.scenario_generator.defaults",
        "get_default_environment_generation_service",
    ),
    "EnvironmentKind": ("services.scenario_generator.models", "EnvironmentKind"),
    "GeneratedLayer": ("services.scenario_generator.models", "GeneratedLayer"),
    "GeneratedScenario": ("services.scenario_generator.models", "GeneratedScenario"),
    "GenerationRequest": ("services.scenario_generator.models", "GenerationRequest"),
    "TaskKind": ("services.scenario_generator.models", "TaskKind"),
    "ValidationIssue": ("services.scenario_generator.models", "ValidationIssue"),
    "ValidationReport": ("services.scenario_generator.models", "ValidationReport"),
    "merge_reports": ("services.scenario_generator.validation", "merge_reports"),
    "validate_generation_request": ("services.scenario_generator.validation", "validate_generation_request"),
}

__all__ = list(_EXPORT_MAP.keys())


def __getattr__(name: str) -> Any:
    try:
        module_name, attr_name = _EXPORT_MAP[name]
    except KeyError as exc:
        raise AttributeError(f"module 'services.scenario_generator' has no attribute {name!r}") from exc
    module = import_module(module_name)
    return getattr(module, attr_name)
