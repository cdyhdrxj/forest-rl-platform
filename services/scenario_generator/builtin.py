from __future__ import annotations

from typing import Any

import numpy as np

from services.agrocare_coverage.families import resolve_coverage_family_params
from services.agrocare_coverage.generator import apply_coverage_layout_to_scenario
from services.agrocare_coverage.models import CoverageEnvConfig
from services.scenario_generator.models import (
    EnvironmentKind,
    GeneratedLayer,
    GeneratedScenario,
    GenerationRequest,
    TaskKind,
)


def _get_number(source: dict[str, Any], key: str, default: float) -> float:
    value = source.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)


def _get_int(source: dict[str, Any], key: str, default: int) -> int:
    value = source.get(key, default)
    try:
        return int(value)
    except (TypeError, ValueError):
        return int(default)


def _sample_unique_positions(
    rng: np.random.Generator,
    grid_size: int,
    count: int,
    occupied: set[tuple[int, int]] | None = None,
) -> list[list[int]]:
    occupied = set() if occupied is None else set(occupied)
    all_positions = [(x, y) for x in range(grid_size) for y in range(grid_size) if (x, y) not in occupied]
    if count > len(all_positions):
        raise ValueError("Requested more unique positions than the grid can provide")
    indices = rng.choice(len(all_positions), size=count, replace=False)
    sampled: list[list[int]] = []
    for idx in np.atleast_1d(indices):
        x, y = all_positions[int(idx)]
        occupied.add((x, y))
        sampled.append([x, y])
    return sampled


class GridFamilyGenerator:
    environment_kind = EnvironmentKind.GRID

    def generate(self, request: GenerationRequest, seed: int) -> GeneratedScenario:
        grid_size = _get_int(request.task_params, "grid_size", _get_int(request.terrain_params, "grid_size", 20))
        terrain_hilliness = _get_number(request.forest_params, "terrain_hilliness", 0.35)
        rng = np.random.default_rng(seed)
        terrain = rng.random((grid_size, grid_size), dtype=np.float32)
        terrain = np.clip(terrain * max(terrain_hilliness, 0.05), 0.0, 1.0).astype(np.float32)

        scenario = GeneratedScenario(
            environment_kind=request.environment_kind,
            task_kind=request.task_kind,
            seed=seed,
            generator_name="grid_family_generator",
            generator_version="v1",
            effective_params={
                "grid_size": grid_size,
                "terrain_hilliness": terrain_hilliness,
            },
            preview_payload={
                "terrain_map": terrain.tolist(),
                "agent_pos": [],
                "goal_pos": [],
                "landmark_pos": [],
            },
            runtime_context={
                "grid": {
                    "grid_size": grid_size,
                },
            },
        )
        scenario.add_layer(
            GeneratedLayer(
                name="terrain",
                layer_type="terrain",
                data=terrain,
                description="Base terrain layer for grid environments",
            )
        )
        return scenario


class Continuous2DFamilyGenerator:
    environment_kind = EnvironmentKind.CONTINUOUS_2D

    _WRAPPER_KEYS = (
        "action_scale",
        "goal_reward",
        "collision_penalty",
        "grid_size",
        "max_steps",
        "frameskip",
        "max_speed",
        "accel",
        "damping",
        "dt",
        "terrain_penalty",
        "step_penalty",
    )

    def generate(self, request: GenerationRequest, seed: int) -> GeneratedScenario:
        grid_size = _get_int(request.task_params, "grid_size", 10)
        obstacle_density = _get_number(
            request.forest_params,
            "obstacle_density",
            _get_number(request.task_params, "obstacle_density", 0.2),
        )
        terrain_hilliness = _get_number(request.forest_params, "terrain_hilliness", 0.35)

        rng = np.random.default_rng(seed)
        terrain = rng.random((grid_size, grid_size), dtype=np.float32)
        terrain = np.clip(terrain * max(terrain_hilliness, 0.05), 0.0, 1.0).astype(np.float32)
        obstacles = (rng.random((grid_size, grid_size)) < obstacle_density).astype(np.float32)

        wrapper_kwargs = {key: request.task_params[key] for key in self._WRAPPER_KEYS if key in request.task_params}
        wrapper_kwargs.update(
            {
                "seed": seed,
                "grid_size": grid_size,
                "obstacle_density": obstacle_density,
            }
        )

        scenario = GeneratedScenario(
            environment_kind=request.environment_kind,
            task_kind=request.task_kind,
            seed=seed,
            generator_name="continuous_2d_family_generator",
            generator_version="v1",
            effective_params={
                "grid_size": grid_size,
                "obstacle_density": obstacle_density,
                "terrain_hilliness": terrain_hilliness,
                **wrapper_kwargs,
            },
            preview_payload={
                "terrain_map": terrain.tolist(),
                "agent_pos": [],
                "goal_pos": [],
                "landmark_pos": [[int(x), int(y)] for x, y in np.argwhere(obstacles == 1)[:128]],
            },
            runtime_context={
                "continuous_2d": {
                    "wrapper_kwargs": wrapper_kwargs,
                },
            },
        )
        scenario.add_layer(GeneratedLayer("terrain", "terrain", terrain, description="Continuous terrain preview"))
        scenario.add_layer(GeneratedLayer("obstacles", "obstacles", obstacles, description="Continuous obstacle preview"))
        return scenario


class Simulator3DFamilyGenerator:
    environment_kind = EnvironmentKind.SIMULATOR_3D

    def generate(self, request: GenerationRequest, seed: int) -> GeneratedScenario:
        preview_size = _get_int(request.terrain_params, "preview_size", 32)
        tree_density = _get_number(request.forest_params, "tree_density", 0.25)
        terrain_hilliness = _get_number(request.forest_params, "terrain_hilliness", 0.45)

        rng = np.random.default_rng(seed)
        terrain = rng.random((preview_size, preview_size), dtype=np.float32)
        terrain = np.clip(terrain * max(terrain_hilliness, 0.05), 0.0, 1.0).astype(np.float32)

        world_descriptor = {
            "seed": seed,
            "preview_size": preview_size,
            "tree_density": tree_density,
            "terrain_hilliness": terrain_hilliness,
            "task_params": dict(request.task_params),
        }

        scenario = GeneratedScenario(
            environment_kind=request.environment_kind,
            task_kind=request.task_kind,
            seed=seed,
            generator_name="simulator_3d_family_generator",
            generator_version="v1",
            effective_params=world_descriptor.copy(),
            preview_payload={
                "terrain_map": terrain.tolist(),
                "agent_pos": [],
                "goal_pos": [],
                "landmark_pos": [],
            },
            runtime_context={
                "simulator_3d": {
                    "world_descriptor": world_descriptor,
                },
            },
        )
        scenario.add_layer(
            GeneratedLayer(
                name="terrain_preview",
                layer_type="terrain_preview",
                data=terrain,
                description="Low-resolution 3D terrain preview",
            )
        )
        return scenario


class PatrolTaskOverlay:
    task_kind = TaskKind.PATROL
    supported_environments = {EnvironmentKind.GRID, EnvironmentKind.SIMULATOR_3D}

    def apply(self, scenario: GeneratedScenario, request: GenerationRequest) -> None:
        grid_size = int(scenario.runtime_context.get("grid", {}).get("grid_size") or 0)
        if grid_size <= 0:
            terrain = scenario.get_layer_data("terrain_preview")
            if terrain is None:
                terrain = scenario.get_layer_data("terrain")
            if terrain is None:
                raise ValueError("Patrol overlay requires either a grid size or a terrain layer")
            grid_size = int(terrain.shape[0])
        rng = np.random.default_rng(scenario.seed + 101)
        occupied: set[tuple[int, int]] = set()

        agent_pos = request.task_params.get("agent_pos")
        agent_random_spawn = bool(request.task_params.get("agent_random_spawn", True))
        if agent_pos is None or agent_random_spawn:
            agent_pos = _sample_unique_positions(rng, grid_size, 1, occupied)[0]
        else:
            agent_pos = [int(agent_pos[0]), int(agent_pos[1])]
        occupied.add((int(agent_pos[0]), int(agent_pos[1])))

        requested_intruder_positions = request.task_params.get("intruder_positions", [])
        requested_intruder_random = request.task_params.get("intruder_random_spawn", [])
        requested_intruder_types = request.task_params.get("intruder_types", [])
        intruder_count = _get_int(request.task_params, "intruder_count", len(requested_intruder_positions) or 1)

        intruder_positions: list[list[int]] = []
        for index in range(intruder_count):
            use_requested = (
                index < len(requested_intruder_positions)
                and index < len(requested_intruder_random)
                and not bool(requested_intruder_random[index])
            )
            if use_requested:
                position = [int(requested_intruder_positions[index][0]), int(requested_intruder_positions[index][1])]
                if tuple(position) in occupied:
                    position = _sample_unique_positions(rng, grid_size, 1, occupied)[0]
            else:
                position = _sample_unique_positions(rng, grid_size, 1, occupied)[0]
            occupied.add((position[0], position[1]))
            intruder_positions.append(position)

        intruder_layer = np.zeros((grid_size, grid_size), dtype=np.float32)
        for x, y in intruder_positions:
            intruder_layer[x, y] = 1.0

        scenario.runtime_context["patrol"] = {
            "agent_pos": agent_pos,
            "intruder_positions": intruder_positions,
        }
        scenario.runtime_context["request_intruder_types"] = list(requested_intruder_types)
        if scenario.environment_kind is EnvironmentKind.SIMULATOR_3D:
            descriptor = dict(scenario.runtime_context.get("simulator_3d", {}).get("world_descriptor") or {})
            descriptor["intruder_positions"] = intruder_positions
            descriptor["agent_start"] = agent_pos
            scenario.runtime_context.setdefault("simulator_3d", {})["world_descriptor"] = descriptor
        scenario.preview_payload["agent_pos"] = [[float(agent_pos[0]), float(agent_pos[1])]]
        scenario.preview_payload["goal_pos"] = [[float(x), float(y)] for x, y in intruder_positions]
        scenario.add_layer(
            GeneratedLayer(
                name="intruders_initial",
                layer_type="intruders_initial",
                data=intruder_layer,
                description="Initial intruder positions for grid patrol",
            )
        )


class ReforestationTaskOverlay:
    task_kind = TaskKind.REFORESTATION
    supported_environments = {EnvironmentKind.GRID}

    def apply(self, scenario: GeneratedScenario, request: GenerationRequest) -> None:
        grid_size = int(scenario.runtime_context["grid"]["grid_size"])
        rng = np.random.default_rng(scenario.seed + 301)

        obstacle_density = _get_number(request.forest_params, "obstacle_density", 0.12)
        plantable_density = _get_number(request.forest_params, "plantable_density", 0.7)
        quality_noise = _get_number(request.forest_params, "quality_noise", 0.25)
        success_probability_noise = _get_number(request.forest_params, "success_probability_noise", 0.2)

        free_mask = (rng.random((grid_size, grid_size)) > obstacle_density).astype(np.float32)
        if int(np.count_nonzero(free_mask)) == 0:
            free_mask[0, 0] = 1.0

        plantable_mask = ((rng.random((grid_size, grid_size)) < plantable_density) & (free_mask == 1)).astype(np.float32)
        if int(np.count_nonzero(plantable_mask)) == 0:
            x, y = np.argwhere(free_mask == 1)[0]
            plantable_mask[x, y] = 1.0

        quality_map = np.where(
            plantable_mask == 1,
            np.clip(1.0 - quality_noise + rng.random((grid_size, grid_size)) * quality_noise, 0.0, 1.0),
            0.0,
        ).astype(np.float32)
        success_prob_map = np.where(
            plantable_mask == 1,
            np.clip(1.0 - success_probability_noise + rng.random((grid_size, grid_size)) * success_probability_noise, 0.05, 1.0),
            0.0,
        ).astype(np.float32)

        random_start = bool(request.task_params.get("random_start", True))
        start_position = request.task_params.get("start_pos")
        free_cells = np.argwhere(free_mask == 1)
        if start_position is None or random_start:
            index = int(rng.integers(0, len(free_cells)))
            x, y = free_cells[index]
            start_position = [int(x), int(y)]
        else:
            start_position = [int(start_position[0]), int(start_position[1])]
            if free_mask[start_position[0], start_position[1]] != 1:
                x, y = free_cells[0]
                start_position = [int(x), int(y)]

        scenario.runtime_context["reforestation"] = {
            "free_mask": free_mask,
            "plantable_mask": plantable_mask,
            "quality_map": quality_map,
            "success_prob_map": success_prob_map,
            "start_position": start_position,
        }
        scenario.preview_payload["agent_pos"] = [[float(start_position[0]), float(start_position[1])]]
        scenario.preview_payload["goal_pos"] = [[float(x), float(y)] for x, y in np.argwhere(plantable_mask == 1)]
        scenario.preview_payload["landmark_pos"] = [[float(x), float(y)] for x, y in np.argwhere(free_mask == 0)]
        scenario.preview_payload["terrain_map"] = (1.0 - free_mask).tolist()

        scenario.add_layer(GeneratedLayer("free_mask", "free_mask", free_mask, description="Reforestation free cells"))
        scenario.add_layer(
            GeneratedLayer("plantable_mask", "plantable_mask", plantable_mask, description="Plantable cells")
        )
        scenario.add_layer(GeneratedLayer("quality_map", "quality_map", quality_map, description="Plant quality map"))
        scenario.add_layer(
            GeneratedLayer(
                "success_prob_map",
                "success_prob_map",
                success_prob_map,
                description="Seedling success probability map",
            )
        )


class CoverageTaskOverlay:
    task_kind = TaskKind.COVERAGE
    supported_environments = {EnvironmentKind.CONTINUOUS_2D}

    def apply(self, scenario: GeneratedScenario, request: GenerationRequest) -> None:
        family = str(request.metadata.get("family") or request.task_params.get("family") or "")
        task_params = resolve_coverage_family_params(family, dict(request.task_params or {}))
        forest_params = dict(task_params)
        forest_params.update(dict(request.forest_params or {}))
        rng = np.random.default_rng(scenario.seed + 401)
        effective_params = {
            "grid_size": _get_int(task_params, "grid_size", _get_int(request.terrain_params, "grid_size", 32)),
            "row_count": _resolve_coverage_count(rng, task_params, "row_count", "row_count_range", default=8),
            "curvature_level": str(forest_params.get("curvature_level") or task_params.get("curvature_level", "low")),
            "field_profile": str(forest_params.get("field_profile") or task_params.get("field_profile", "simple")),
            "gap_probability": _get_number(forest_params, "gap_probability", _get_number(task_params, "gap_probability", 0.0)),
            "obstacle_count": _resolve_coverage_count(rng, forest_params, "obstacle_count", "obstacle_count_range", default=0),
            "max_steps": _get_int(task_params, "max_steps", 24),
            "seed": scenario.seed,
        }
        passthrough_keys = (
            "max_rows",
            "gap_segment_length",
            "obstacle_radius_min",
            "obstacle_radius_max",
            "alpha_new_coverage",
            "beta_repeat_coverage",
            "beta_transition",
            "beta_path",
            "beta_turn",
            "beta_invalid_action",
            "success_bonus",
            "failure_penalty",
        )
        for key in passthrough_keys:
            if key in task_params:
                effective_params[key] = task_params[key]

        config = CoverageEnvConfig.model_validate(effective_params)
        apply_coverage_layout_to_scenario(
            scenario,
            config,
            family=family,
            split=str(request.metadata.get("split") or task_params.get("split") or ""),
        )


class TrailTaskOverlay:
    task_kind = TaskKind.TRAIL
    supported_environments = {EnvironmentKind.CONTINUOUS_2D, EnvironmentKind.SIMULATOR_3D}

    def apply(self, scenario: GeneratedScenario, request: GenerationRequest) -> None:
        terrain_layer = scenario.get_layer_data("terrain")
        if terrain_layer is None:
            terrain_layer = scenario.get_layer_data("terrain_preview")
        if terrain_layer is None:
            return

        grid_size = terrain_layer.shape[0]
        rng = np.random.default_rng(scenario.seed + 211)
        agent_pos = _sample_unique_positions(rng, grid_size, 1)[0]
        goal_pos = _sample_unique_positions(rng, grid_size, 1, {(agent_pos[0], agent_pos[1])})[0]
        scenario.runtime_context["trail"] = {
            "agent_pos": agent_pos,
            "goal_pos": goal_pos,
        }
        scenario.preview_payload["agent_pos"] = [[float(agent_pos[0]), float(agent_pos[1])]]
        scenario.preview_payload["goal_pos"] = [[float(goal_pos[0]), float(goal_pos[1])]]


class DefaultScenarioValidator:
    supported_tasks = None
    supported_environments = None

    def validate(self, scenario: GeneratedScenario) -> list[str]:
        messages: list[str] = []

        for name, layer in scenario.layers.items():
            data = np.asarray(layer.data)
            if data.size == 0:
                messages.append(f"Layer '{name}' is empty")

        if scenario.task_kind == TaskKind.PATROL:
            patrol_ctx = scenario.runtime_context.get("patrol")
            grid_ctx = scenario.runtime_context.get("grid", {})
            if patrol_ctx is None:
                messages.append("Patrol scenario has no patrol runtime context")
            else:
                grid_size = int(grid_ctx.get("grid_size", 0))
                if grid_size <= 0:
                    terrain = scenario.get_layer_data("terrain_preview")
                    if terrain is None:
                        terrain = scenario.get_layer_data("terrain")
                    grid_size = int(terrain.shape[0]) if terrain is not None else 0
                positions = [tuple(patrol_ctx["agent_pos"])] + [tuple(pos) for pos in patrol_ctx["intruder_positions"]]
                if len(set(positions)) != len(positions):
                    messages.append("Patrol scenario contains overlapping initial positions")
                for x, y in positions:
                    if not (0 <= x < grid_size and 0 <= y < grid_size):
                        messages.append("Patrol scenario contains out-of-bounds positions")

        if scenario.environment_kind == EnvironmentKind.SIMULATOR_3D:
            sim_ctx = scenario.runtime_context.get("simulator_3d")
            if sim_ctx is None or "world_descriptor" not in sim_ctx:
                messages.append("3D scenario has no world descriptor")
            if scenario.get_layer_data("terrain_preview") is None:
                messages.append("3D scenario has no terrain preview layer")

        if scenario.task_kind == TaskKind.REFORESTATION:
            ctx = scenario.runtime_context.get("reforestation")
            if ctx is None:
                messages.append("Reforestation scenario has no runtime layout")
            else:
                free_mask = np.asarray(ctx["free_mask"])
                plantable_mask = np.asarray(ctx["plantable_mask"])
                if np.any(plantable_mask > free_mask):
                    messages.append("Plantable cells must be a subset of free cells")
                x, y = ctx["start_position"]
                if free_mask[x, y] != 1:
                    messages.append("Reforestation start position must be placed on a free cell")

        if scenario.task_kind == TaskKind.COVERAGE:
            ctx = scenario.runtime_context.get("coverage")
            if ctx is None:
                messages.append("Coverage scenario has no runtime layout")
            else:
                field_mask = np.asarray(ctx.get("field_mask"))
                free_mask = np.asarray(ctx["free_mask"])
                coverage_mask = np.asarray(ctx["coverage_mask"])
                start_x, start_y = ctx["start_position"]
                home_x, home_y = ctx["home_position"]
                row_paths = list(ctx.get("row_paths") or [])
                if field_mask.size == 0:
                    messages.append("Coverage scenario must contain a field mask")
                if np.count_nonzero(coverage_mask) == 0:
                    messages.append("Coverage scenario must contain at least one target coverage cell")
                if free_mask[start_x, start_y] != 1:
                    messages.append("Coverage start position must be placed on a free cell")
                if free_mask[home_x, home_y] != 1:
                    messages.append("Coverage home position must be placed on a free cell")
                if len(row_paths) == 0:
                    messages.append("Coverage scenario must contain at least one row path")

        return messages


def _resolve_coverage_count(
    rng: np.random.Generator,
    source: dict[str, Any],
    key: str,
    range_key: str,
    *,
    default: int,
) -> int:
    if key in source:
        return _get_int(source, key, default)
    range_value = source.get(range_key)
    if isinstance(range_value, (list, tuple)) and len(range_value) >= 2:
        try:
            lower = int(range_value[0])
            upper = int(range_value[1])
        except (TypeError, ValueError):
            return default
        if upper < lower:
            lower, upper = upper, lower
        return int(rng.integers(lower, upper + 1))
    return default
