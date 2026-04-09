from __future__ import annotations

from functools import lru_cache

from services.scenario_generator.builtin import (
    CoverageTaskOverlay,
    Continuous2DFamilyGenerator,
    DefaultScenarioValidator,
    GridFamilyGenerator,
    PatrolTaskOverlay,
    ReforestationTaskOverlay,
    Simulator3DFamilyGenerator,
    TrailTaskOverlay,
)
from services.scenario_generator.registry import GeneratorRegistry
from services.scenario_generator.service import EnvironmentGenerationService


@lru_cache(maxsize=1)
def get_default_environment_generation_service() -> EnvironmentGenerationService:
    registry = GeneratorRegistry()
    registry.register_family(GridFamilyGenerator())
    registry.register_family(Continuous2DFamilyGenerator())
    registry.register_family(Simulator3DFamilyGenerator())

    registry.register_overlay(PatrolTaskOverlay())
    registry.register_overlay(ReforestationTaskOverlay())
    registry.register_overlay(TrailTaskOverlay())
    registry.register_overlay(CoverageTaskOverlay())

    registry.register_validator(DefaultScenarioValidator())
    return EnvironmentGenerationService(registry)
