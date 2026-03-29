from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


class EnvironmentKind(str, Enum):
    GRID = "grid"
    CONTINUOUS_2D = "continuous_2d"
    SIMULATOR_3D = "simulator_3d"


class TaskKind(str, Enum):
    TRAIL = "trail"
    PATROL = "patrol"
    REFORESTATION = "reforestation"
    ROBOT = "robot"


@dataclass(slots=True)
class GenerationRequest:
    environment_kind: EnvironmentKind
    task_kind: TaskKind
    seed: int | None = None
    terrain_params: dict[str, Any] = field(default_factory=dict)
    forest_params: dict[str, Any] = field(default_factory=dict)
    task_params: dict[str, Any] = field(default_factory=dict)
    visualization_options: dict[str, Any] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ValidationIssue:
    stage: str
    code: str
    message: str
    severity: str = "error"
    details: dict[str, Any] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        payload = {
            "stage": self.stage,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }
        if self.details:
            payload["details"] = dict(self.details)
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "ValidationIssue":
        return cls(
            stage=str(payload.get("stage") or "unknown"),
            code=str(payload.get("code") or "unknown"),
            message=str(payload.get("message") or ""),
            severity=str(payload.get("severity") or "error"),
            details=dict(payload.get("details") or {}),
        )


@dataclass(slots=True)
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not any(issue.severity == "error" for issue in self.issues)

    @property
    def messages(self) -> list[str]:
        return [issue.message for issue in self.issues]

    def add(
        self,
        *,
        stage: str,
        code: str,
        message: str,
        severity: str = "error",
        details: dict[str, Any] | None = None,
    ) -> None:
        self.issues.append(
            ValidationIssue(
                stage=stage,
                code=code,
                message=message,
                severity=severity,
                details=dict(details or {}),
            )
        )

    def extend(self, issues: list[ValidationIssue]) -> None:
        self.issues.extend(issues)

    def merge(self, other: "ValidationReport | None") -> "ValidationReport":
        merged = ValidationReport(list(self.issues))
        if other is not None:
            merged.extend(list(other.issues))
        return merged

    def to_payload(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "issues": [issue.to_payload() for issue in self.issues],
        }

    @classmethod
    def from_payload(cls, payload: dict[str, Any] | None) -> "ValidationReport":
        if not isinstance(payload, dict):
            return cls()
        return cls(
            issues=[
                ValidationIssue.from_payload(item)
                for item in list(payload.get("issues") or [])
                if isinstance(item, dict)
            ]
        )


@dataclass(slots=True)
class GeneratedLayer:
    name: str
    layer_type: str
    data: np.ndarray
    file_format: str = "npy"
    description: str | None = None

    def to_serializable(self) -> list[list[float]]:
        return np.asarray(self.data, dtype=np.float32).tolist()


@dataclass(slots=True)
class GeneratedScenario:
    environment_kind: EnvironmentKind
    task_kind: TaskKind
    seed: int
    generator_name: str
    generator_version: str
    effective_params: dict[str, Any] = field(default_factory=dict)
    layers: dict[str, GeneratedLayer] = field(default_factory=dict)
    preview_payload: dict[str, Any] = field(default_factory=dict)
    runtime_context: dict[str, Any] = field(default_factory=dict)
    validation_messages: list[str] = field(default_factory=list)
    validation_passed: bool = True
    validation_report: ValidationReport = field(default_factory=ValidationReport)

    def add_layer(self, layer: GeneratedLayer) -> None:
        self.layers[layer.name] = layer

    def get_layer_data(self, name: str) -> np.ndarray | None:
        layer = self.layers.get(name)
        if layer is None:
            return None
        return np.asarray(layer.data, dtype=np.float32)

    def apply_validation_report(self, report: ValidationReport) -> None:
        self.validation_report = report
        self.validation_messages = report.messages
        self.validation_passed = report.passed
