from __future__ import annotations

from typing import Any

import numpy as np

from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.reforestation_planting.models import PlantingEnvConfig
from services.scenario_generator.models import EnvironmentKind, GeneratedScenario, GenerationRequest, TaskKind


def build_patrol_grid_request(config: GridWorldConfig) -> GenerationRequest:
    return GenerationRequest(
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        seed=config.seed,
        terrain_params={
            "grid_size": config.grid_size,
        },
        forest_params={
            "terrain_hilliness": config.terrain_hilliness,
        },
        task_params={
            "grid_size": config.grid_size,
            "intruder_count": len(config.intruder_config),
            "agent_pos": list(config.agent_config.pos),
            "agent_random_spawn": config.agent_config.is_random_spawned,
            "intruder_positions": [list(item.pos) for item in config.intruder_config],
            "intruder_random_spawn": [item.is_random_spawned for item in config.intruder_config],
            "intruder_types": [item.type for item in config.intruder_config],
        },
    )


def apply_patrol_generation(
    config: GridWorldConfig,
    scenario: GeneratedScenario,
) -> tuple[GridWorldConfig, dict[str, np.ndarray]]:
    updated = config.model_copy(deep=True)
    patrol_ctx = scenario.runtime_context["patrol"]
    agent_pos = patrol_ctx["agent_pos"]
    intruder_positions = patrol_ctx["intruder_positions"]

    updated.agent_config.pos = list(agent_pos)
    updated.agent_config.is_random_spawned = False

    configs = list(updated.intruder_config)
    while len(configs) < len(intruder_positions):
        configs.append(WandererConfig())

    new_configs = []
    for index, position in enumerate(intruder_positions):
        current = configs[index]
        current.pos = list(position)
        current.is_random_spawned = False
        new_configs.append(current)
    updated.intruder_config = new_configs

    static_layers: dict[str, np.ndarray] = {}
    terrain = scenario.get_layer_data("terrain")
    if terrain is not None:
        static_layers["terrain"] = terrain
    return updated, static_layers


def build_reforestation_request(config: PlantingEnvConfig) -> GenerationRequest:
    return GenerationRequest(
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.REFORESTATION,
        seed=config.seed,
        terrain_params={
            "grid_size": config.grid_size,
        },
        forest_params={
            "obstacle_density": config.obstacle_density,
            "plantable_density": config.plantable_density,
            "quality_noise": config.quality_noise,
            "success_probability_noise": config.success_probability_noise,
        },
        task_params={
            "grid_size": config.grid_size,
            "random_start": config.random_start,
        },
    )


def extract_reforestation_runtime_layout(scenario: GeneratedScenario) -> dict[str, Any]:
    return dict(scenario.runtime_context["reforestation"])


def build_continuous_trail_request(params: dict[str, Any]) -> GenerationRequest:
    return GenerationRequest(
        environment_kind=EnvironmentKind.CONTINUOUS_2D,
        task_kind=TaskKind.TRAIL,
        seed=params.get("seed"),
        terrain_params={
            "grid_size": params.get("grid_size", 10),
        },
        forest_params={
            "obstacle_density": params.get("obstacle_density", 0.2),
            "terrain_hilliness": params.get("terrain_hilliness", 0.35),
        },
        task_params=dict(params),
    )


def extract_continuous_runtime_kwargs(scenario: GeneratedScenario) -> dict[str, Any]:
    return dict(scenario.runtime_context["continuous_2d"]["wrapper_kwargs"])
