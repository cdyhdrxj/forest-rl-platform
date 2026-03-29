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

    def add_layer(self, layer: GeneratedLayer) -> None:
        self.layers[layer.name] = layer

    def get_layer_data(self, name: str) -> np.ndarray | None:
        layer = self.layers.get(name)
        if layer is None:
            return None
        return np.asarray(layer.data, dtype=np.float32)
