from __future__ import annotations

from typing import Any

import numpy as np

from services.agrocare_coverage.generator import build_runtime_config
from services.patrol_planning.assets.envs.models import GridForestConfig
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.reforestation_planting.models import PlantingEnvConfig
from services.scenario_generator.models import EnvironmentKind, GeneratedScenario, GenerationRequest, TaskKind


def build_patrol_grid_request(config: GridForestConfig) -> GenerationRequest:
    map_seed = config.map_seed if hasattr(config, "map_seed") else 0
    return GenerationRequest(
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        seed=map_seed,
        terrain_params={
            "grid_size": config.grid_size,
        },
        forest_params={
            "map_seed": map_seed,
            "passability_low": getattr(config, "passability_low", 0.1),
            "passability_high": getattr(config, "passability_high", 1.0),
            "impassable_prob": getattr(config, "impassable_prob", 0.15),
            "max_value": getattr(config, "max_value", 1000.0),
            "value_density": getattr(config, "value_density", 0.7),
        },
        task_params={
            "grid_size": config.grid_size,
            "max_steps": config.max_steps,
            "intruder_count": len(config.intruder_config),
            "agent_pos": list(config.agent_config.pos),
            "agent_random_spawn": config.agent_config.is_random_spawned,
            "intruder_positions": [list(item.pos) for item in config.intruder_config],
            "intruder_random_spawn": [item.is_random_spawned for item in config.intruder_config],
            "intruder_types": [item.type for item in config.intruder_config],
        },
    )


def apply_patrol_generation(
    config: GridForestConfig,
    scenario: GeneratedScenario,
) -> tuple[GridForestConfig, dict[str, np.ndarray]]:
    updated = config.model_copy(deep=True)
    patrol_ctx = scenario.runtime_context.get("patrol", {})
    
    scenario_seed = scenario.seed
    if scenario.runtime_context.get("seed") is not None:
        scenario_seed = scenario.runtime_context["seed"]
    
    if hasattr(updated, "map_seed"):
        updated.map_seed = scenario_seed
    
    agent_pos = patrol_ctx.get("agent_pos")
    
    if agent_pos is not None:
        updated.agent_config.pos = list(agent_pos)
        updated.agent_config.is_random_spawned = False
    
    intruder_positions = patrol_ctx.get("intruder_positions", [])
    
    if intruder_positions:
        intruder_types = patrol_ctx.get("intruder_types", [])
        
        new_intruders = []
        
        for i in range(len(intruder_positions)):
            if i < len(updated.intruder_config):
                new_intruder = updated.intruder_config[i].model_copy(deep=True)
                config_random_spawn = new_intruder.is_random_spawned
            else:
                new_intruder = WandererConfig()
                config_random_spawn = True
            
            if i < len(intruder_positions):
                new_intruder.pos = list(intruder_positions[i])
                new_intruder.is_random_spawned = False
            else:
                new_intruder.is_random_spawned = config_random_spawn
            
            if i < len(intruder_types):
                new_intruder.type = intruder_types[i]
            
            new_intruders.append(new_intruder)
        
        updated.intruder_config = new_intruders
    
    static_layers = {}
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

def extract_patrol_runtime_context(scenario: GeneratedScenario) -> dict[str, Any]:
    return dict(scenario.runtime_context.get("patrol", {}))

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
        },
        task_params=dict(params),
    )


def build_continuous_coverage_request(params: dict[str, Any]) -> GenerationRequest:
    source = dict(params)
    grid_size = int(source.get("grid_size", 32))
    forest_params = {
        "obstacle_density": 0.0,
        "curvature_level": source.get("curvature_level", "low"),
        "gap_probability": source.get("gap_probability", 0.0),
    }
    if source.get("obstacle_count") is not None:
        forest_params["obstacle_count"] = source.get("obstacle_count")
    if source.get("obstacle_count_range") is not None:
        forest_params["obstacle_count_range"] = source.get("obstacle_count_range")
    if source.get("field_profile") is not None:
        forest_params["field_profile"] = source.get("field_profile")
    return GenerationRequest(
        environment_kind=EnvironmentKind.CONTINUOUS_2D,
        task_kind=TaskKind.COVERAGE,
        seed=source.get("seed"),
        terrain_params={
            "grid_size": grid_size,
        },
        forest_params=forest_params,
        task_params=dict(source),
        metadata={
            "family": source.get("family"),
            "split": source.get("split"),
        },
    )


def extract_continuous_runtime_kwargs(scenario: GeneratedScenario) -> dict[str, Any]:
    return dict(scenario.runtime_context["continuous_2d"]["wrapper_kwargs"])


def extract_coverage_runtime_layout(scenario: GeneratedScenario) -> dict[str, Any]:
    return dict(scenario.runtime_context["coverage"])


def build_coverage_runtime_config(params: dict[str, Any], scenario: GeneratedScenario) -> dict[str, Any]:
    return build_runtime_config(params, scenario).model_dump(mode="json")


def build_simulator_3d_request(params: dict[str, Any], *, task_kind: TaskKind) -> GenerationRequest:
    map_config = _build_3d_map_config(params)
    robot_config = _build_3d_robot_config(params)
    target_config = _build_3d_target_config(params)

    try:
        seed = int(map_config.get("seed", 0))
    except (TypeError, ValueError):
        seed = 0
    map_config["seed"] = seed
    task_params = {
        key: value
        for key, value in dict(params).items()
        if key not in {"map_config", "robot_config", "target_config"}
    }
    task_params.update(
        {
            "robot": robot_config,
            "target": target_config,
        }
    )

    tree_density = params.get("tree_density")
    if tree_density is None and map_config.get("density") is not None:
        tree_density = float(map_config.get("density", 0)) / 100.0
    forest_params: dict[str, Any] = {
        "object_density": map_config.get("density", 10),
    }
    if tree_density is not None:
        forest_params["tree_density"] = tree_density
    if params.get("terrain_hilliness") is not None:
        forest_params["terrain_hilliness"] = params.get("terrain_hilliness")

    return GenerationRequest(
        environment_kind=EnvironmentKind.SIMULATOR_3D,
        task_kind=task_kind,
        seed=seed,

        terrain_params={
            "uniform_scale": map_config.get("uniform_scale", 0.1),
            "mesh_height_multiplayer": map_config.get("mesh_height_multiplayer", 15),
            "noise_scale": map_config.get("noise_scale", 50),
            "octaves": map_config.get("octaves", 4),
            "persistance": map_config.get("persistance", 0.5),
            "lacunarity": map_config.get("lacunarity", 2.0),
            "seed": seed,
            "offset_x": map_config.get("offset_x", 0),
            "offset_y": map_config.get("offset_y", 0),
            "density": map_config.get("density", 10),
            "max_view_dst": map_config.get("max_view_dst", 1) * 125,
            "noise_normalize_mode": map_config.get("noise_normalize_mode", 1),
        },
        forest_params=forest_params,
        task_params=task_params,
    )


def extract_simulator_3d_runtime_config(scenario: GeneratedScenario) -> dict[str, Any]:
    ctx = scenario.runtime_context.get("simulator_3d") or {}

    return {
        "map_config": ctx.get("map_config", {}),
        "robot_config": ctx.get("robot_config", {}),
        "target_config": ctx.get("target_config", {}),
    }


def _build_3d_map_config(params: dict[str, Any]) -> dict[str, Any]:
    source = dict(params.get("map_config") or {})

    if "seed" not in source and params.get("seed") is not None:
        source["seed"] = params.get("seed")
    if "density" not in source:
        if params.get("density") is not None:
            source["density"] = params.get("density")
        elif params.get("tree_density") is not None:
            source["density"] = int(round(float(params["tree_density"]) * 100))

    for key in (
        "uniform_scale",
        "mesh_height_multiplayer",
        "noise_scale",
        "octaves",
        "persistance",
        "lacunarity",
        "offset_x",
        "offset_y",
        "max_view_dst",
        "noise_normalize_mode",
    ):
        if key not in source and params.get(key) is not None:
            source[key] = params.get(key)

    if "mesh_height_multiplayer" not in source and params.get("terrain_hilliness") is not None:
        source["mesh_height_multiplayer"] = 1.0 + 4.0 * float(params["terrain_hilliness"])

    return source


def _build_3d_robot_config(params: dict[str, Any]) -> dict[str, Any]:
    source = dict(params.get("robot_config") or {})
    if "robot_type" not in source and "type" in source:
        source["robot_type"] = source["type"]

    flat_mapping = {
        "robot_type": "robot_type",
        "robot_position_x": "position_x",
        "robot_position_y": "position_y",
        "robot_position_z": "position_z",
        "robot_rotation_y": "rotation_y",
    }
    for flat_key, target_key in flat_mapping.items():
        if target_key not in source and params.get(flat_key) is not None:
            source[target_key] = params.get(flat_key)

    return source


def _build_3d_target_config(params: dict[str, Any]) -> dict[str, Any]:
    source = dict(params.get("target_config") or {})
    flat_mapping = {
        "target_position_x": "position_x",
        "target_position_y": "position_y",
        "target_position_z": "position_z",
        "radius": "radius",
    }
    for flat_key, target_key in flat_mapping.items():
        if target_key not in source and params.get(flat_key) is not None:
            source[target_key] = params.get(flat_key)

    return source
