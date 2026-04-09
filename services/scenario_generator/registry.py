from __future__ import annotations

from typing import Protocol

from services.scenario_generator.models import EnvironmentKind, GeneratedScenario, GenerationRequest, TaskKind


class FamilyGenerator(Protocol):
    environment_kind: EnvironmentKind

    def generate(self, request: GenerationRequest, seed: int) -> GeneratedScenario:
        ...


class TaskOverlay(Protocol):
    task_kind: TaskKind
    supported_environments: set[EnvironmentKind] | None

    def apply(self, scenario: GeneratedScenario, request: GenerationRequest) -> None:
        ...


class ScenarioValidator(Protocol):
    supported_tasks: set[TaskKind] | None
    supported_environments: set[EnvironmentKind] | None

    def validate(self, scenario: GeneratedScenario) -> list[str]:
        ...


class GeneratorRegistry:
    def __init__(self) -> None:
        self._family_generators: dict[EnvironmentKind, FamilyGenerator] = {}
        self._task_overlays: dict[TaskKind, list[TaskOverlay]] = {}
        self._validators: list[ScenarioValidator] = []

    def register_family(self, generator: FamilyGenerator) -> None:
        self._family_generators[generator.environment_kind] = generator

    def register_overlay(self, overlay: TaskOverlay) -> None:
        self._task_overlays.setdefault(overlay.task_kind, []).append(overlay)

    def register_validator(self, validator: ScenarioValidator) -> None:
        self._validators.append(validator)

    def get_family(self, environment_kind: EnvironmentKind) -> FamilyGenerator:
        try:
            return self._family_generators[environment_kind]
        except KeyError as exc:
            raise KeyError(f"No family generator registered for environment '{environment_kind.value}'") from exc

    def get_overlays(
        self,
        task_kind: TaskKind,
        environment_kind: EnvironmentKind,
    ) -> list[TaskOverlay]:
        overlays = self._task_overlays.get(task_kind, [])
        return [
            overlay
            for overlay in overlays
            if overlay.supported_environments is None or environment_kind in overlay.supported_environments
        ]

    def get_validators(
        self,
        task_kind: TaskKind,
        environment_kind: EnvironmentKind,
    ) -> list[ScenarioValidator]:
        matched: list[ScenarioValidator] = []
        for validator in self._validators:
            task_ok = validator.supported_tasks is None or task_kind in validator.supported_tasks
            env_ok = validator.supported_environments is None or environment_kind in validator.supported_environments
            if task_ok and env_ok:
                matched.append(validator)
        return matched
