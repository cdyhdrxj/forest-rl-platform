from __future__ import annotations

from typing import Any

from services.scenario_generator.models import (
    EnvironmentKind,
    GeneratedScenario,
    GenerationRequest,
    TaskKind,
    ValidationReport,
)
from services.scenario_generator.registry import GeneratorRegistry


def merge_reports(*reports: ValidationReport | None) -> ValidationReport:
    merged = ValidationReport()
    for report in reports:
        if report is not None:
            merged.extend(list(report.issues))
    return merged


def validate_generation_request(
    registry: GeneratorRegistry,
    request: GenerationRequest,
    *,
    stage: str = "dispatcher.request",
) -> ValidationReport:
    report = ValidationReport()

    try:
        registry.get_family(request.environment_kind)
    except KeyError:
        report.add(
            stage=stage,
            code="unsupported_environment",
            message=f"Environment '{request.environment_kind.value}' is not supported",
        )
        return report

    overlays = registry.get_overlays(request.task_kind, request.environment_kind)
    if request.task_kind is not TaskKind.ROBOT and not overlays:
        report.add(
            stage=stage,
            code="unsupported_task_environment",
            message=(
                f"Task '{request.task_kind.value}' is not supported for "
                f"environment '{request.environment_kind.value}'"
            ),
        )

    _validate_positive_int(
        report,
        stage=stage,
        code="grid_size_invalid",
        message="Grid size must be at least 2",
        value=_resolve_int(request.task_params, "grid_size", request.terrain_params, default=0),
        minimum=2,
        enabled=request.environment_kind in {EnvironmentKind.GRID, EnvironmentKind.CONTINUOUS_2D},
    )
    _validate_positive_int(
        report,
        stage=stage,
        code="preview_size_invalid",
        message="3D preview size must be at least 4",
        value=_resolve_int(request.terrain_params, "preview_size", request.task_params, default=0),
        minimum=4,
        enabled=request.environment_kind is EnvironmentKind.SIMULATOR_3D,
    )
    _validate_range(
        report,
        stage=stage,
        code="terrain_hilliness_invalid",
        message="Terrain hilliness must be in range [0, 1]",
        value=_resolve_float(request.forest_params, "terrain_hilliness", request.terrain_params, default=0.5),
    )
    _validate_range(
        report,
        stage=stage,
        code="tree_density_invalid",
        message="Tree density must be in range [0, 1]",
        value=_resolve_float(request.forest_params, "tree_density", request.task_params, default=0.25),
        enabled=request.environment_kind is EnvironmentKind.SIMULATOR_3D,
    )
    _validate_range(
        report,
        stage=stage,
        code="obstacle_density_invalid",
        message="Obstacle density must be in range [0, 1]",
        value=_resolve_float(request.forest_params, "obstacle_density", request.task_params, default=0.0),
        enabled=request.environment_kind is EnvironmentKind.CONTINUOUS_2D or request.task_kind is TaskKind.REFORESTATION,
    )
    _validate_range(
        report,
        stage=stage,
        code="plantable_density_invalid",
        message="Plantable density must be in range [0, 1]",
        value=_resolve_float(request.forest_params, "plantable_density", request.task_params, default=1.0),
        enabled=request.task_kind is TaskKind.REFORESTATION,
    )

    if request.seed is not None and int(request.seed) < 0:
        report.add(
            stage=stage,
            code="seed_negative",
            message="Seed must be greater than or equal to zero",
        )

    if (
        request.task_kind is TaskKind.REFORESTATION
        and request.environment_kind is not EnvironmentKind.GRID
    ):
        report.add(
            stage=stage,
            code="reforestation_environment_invalid",
            message="Reforestation is currently supported only for grid environments",
        )

    return report


def report_from_messages(
    messages: list[str],
    *,
    stage: str,
    code_prefix: str,
) -> ValidationReport:
    report = ValidationReport()
    for index, message in enumerate(messages):
        report.add(
            stage=stage,
            code=f"{code_prefix}_{index + 1}",
            message=message,
        )
    return report


def report_for_runtime_validation(
    scenario: GeneratedScenario,
    messages: list[str],
    *,
    stage: str = "simulator.load",
) -> ValidationReport:
    report = report_from_messages(
        messages,
        stage=stage,
        code_prefix=f"{scenario.environment_kind.value}_{scenario.task_kind.value}_runtime",
    )
    if scenario.validation_passed and not report.issues:
        return report
    return report


def _validate_positive_int(
    report: ValidationReport,
    *,
    stage: str,
    code: str,
    message: str,
    value: int,
    minimum: int,
    enabled: bool = True,
) -> None:
    if enabled and int(value) < minimum:
        report.add(stage=stage, code=code, message=message, details={"value": int(value)})


def _validate_range(
    report: ValidationReport,
    *,
    stage: str,
    code: str,
    message: str,
    value: float,
    enabled: bool = True,
) -> None:
    if enabled and not (0.0 <= float(value) <= 1.0):
        report.add(stage=stage, code=code, message=message, details={"value": float(value)})


def _resolve_int(primary: dict[str, Any], key: str, secondary: dict[str, Any], *, default: int) -> int:
    for source in (primary, secondary):
        if key not in source:
            continue
        try:
            return int(source[key])
        except (TypeError, ValueError):
            return default
    return default


def _resolve_float(primary: dict[str, Any], key: str, secondary: dict[str, Any], *, default: float) -> float:
    for source in (primary, secondary):
        if key not in source:
            continue
        try:
            return float(source[key])
        except (TypeError, ValueError):
            return default
    return default
