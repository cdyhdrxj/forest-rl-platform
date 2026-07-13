import numpy as np

from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.reforestation_planting.models import PlantingEnvConfig
from services.scenario_generator import (
    apply_patrol_generation,
    build_continuous_coverage_request,
    build_continuous_trail_request,
    build_patrol_grid_request,
    build_reforestation_request,
    build_simulator_3d_request,
    extract_coverage_runtime_layout,
    extract_continuous_runtime_kwargs,
    extract_reforestation_runtime_layout,
    extract_simulator_3d_runtime_config,
    get_default_environment_generation_service,
)
from services.scenario_generator.models import TaskKind


def test_grid_patrol_generation_is_deterministic_and_unique():
    service = get_default_environment_generation_service()
    config = GridWorldConfig(
        grid_size=8,
        seed=17,
        terrain_hilliness=0.4,
        agent_config=AgentConfig(pos=[0, 0], is_random_spawned=True),
        intruder_config=[
            WandererConfig(pos=[1, 1], is_random_spawned=True),
            WandererConfig(pos=[2, 2], is_random_spawned=True),
        ],
    )

    scenario_a = service.generate(build_patrol_grid_request(config))
    scenario_b = service.generate(build_patrol_grid_request(config))

    assert np.array_equal(scenario_a.get_layer_data("terrain"), scenario_b.get_layer_data("terrain"))
    assert scenario_a.runtime_context["patrol"] == scenario_b.runtime_context["patrol"]

    positions = [
        tuple(scenario_a.runtime_context["patrol"]["agent_pos"]),
        *[tuple(pos) for pos in scenario_a.runtime_context["patrol"]["intruder_positions"]],
    ]
    assert len(set(positions)) == len(positions)

    updated_config, static_layers = apply_patrol_generation(config, scenario_a)
    assert updated_config.agent_config.is_random_spawned is False
    assert "terrain" in static_layers
    assert scenario_a.validation_passed is True


def test_reforestation_generation_produces_valid_layout():
    service = get_default_environment_generation_service()
    config = PlantingEnvConfig(
        grid_size=10,
        seed=23,
        obstacle_density=0.2,
        plantable_density=0.65,
        quality_noise=0.15,
        success_probability_noise=0.1,
    )

    scenario = service.generate(build_reforestation_request(config))
    layout = extract_reforestation_runtime_layout(scenario)

    free_mask = layout["free_mask"]
    plantable_mask = layout["plantable_mask"]
    x, y = layout["start_position"]

    assert free_mask.shape == (10, 10)
    assert plantable_mask.shape == (10, 10)
    assert np.all(plantable_mask <= free_mask)
    assert free_mask[x, y] == 1
    assert scenario.validation_passed is True


def test_continuous_generation_returns_wrapper_kwargs():
    service = get_default_environment_generation_service()
    scenario = service.generate(
        build_continuous_trail_request(
            {
                "seed": 31,
                "grid_size": 12,
                "obstacle_density": 0.3,
                "frameskip": 4,
                "max_steps": 150,
            }
        )
    )

    wrapper_kwargs = extract_continuous_runtime_kwargs(scenario)
    assert wrapper_kwargs["seed"] == 31
    assert wrapper_kwargs["grid_size"] == 12
    assert wrapper_kwargs["obstacle_density"] == 0.3
    assert wrapper_kwargs["frameskip"] == 4


def test_continuous_coverage_generation_produces_valid_layout():
    service = get_default_environment_generation_service()
    scenario = service.generate(
        build_continuous_coverage_request(
            {
                "seed": 41,
                "grid_size": 28,
                "row_count": 7,
                "curvature_level": "medium",
                "gap_probability": 0.2,
                "obstacle_count": 2,
                "max_steps": 10,
            }
        )
    )

    layout = extract_coverage_runtime_layout(scenario)
    coverage_mask = layout["coverage_mask"]
    free_mask = layout["free_mask"]
    start_x, start_y = layout["start_position"]
    home_x, home_y = layout["home_position"]

    assert coverage_mask.shape == (28, 28)
    assert free_mask.shape == (28, 28)
    assert int(np.count_nonzero(coverage_mask)) > 0
    assert free_mask[start_x, start_y] == 1
    assert free_mask[home_x, home_y] == 1
    assert len(layout["row_paths"]) == 7
    assert scenario.validation_passed is True


def test_continuous_coverage_family_preset_applies_split_and_field_profile():
    service = get_default_environment_generation_service()
    scenario = service.generate(
        build_continuous_coverage_request(
            {
                "seed": 43,
                "family": "S4",
                "split": "test",
            }
        )
    )

    layout = extract_coverage_runtime_layout(scenario)

    assert scenario.effective_params["family"] == "S4"
    assert scenario.effective_params["split"] == "test"
    assert scenario.effective_params["field_profile"] == "concave"
    assert layout["field_mask"].shape == (36, 36)
    assert 8 <= int(layout["row_count"]) <= 12
    assert layout["split"] == "test"
    assert layout["family"] == "S4"
    assert scenario.validation_passed is True


def test_simulator_3d_generation_uses_nested_ros_payload_for_preview():
    service = get_default_environment_generation_service()
    scenario = service.generate(
        build_simulator_3d_request(
            {
                "map_config": {
                    "seed": 51,
                    "mesh_height_multiplayer": 1.5,
                    "noise_scale": 150.0,
                    "density": 10,
                    "max_view_dst": 2,
                },
                "robot_config": {
                    "type": 1,
                    "position_x": 1.0,
                    "position_y": 2.0,
                    "position_z": 3.0,
                },
                "target_config": {
                    "position_x": 10.0,
                    "position_y": 20.0,
                    "position_z": 30.0,
                    "radius": 5.0,
                },
            },
            task_kind=TaskKind.TRAIL,
        )
    )

    runtime_config = extract_simulator_3d_runtime_config(scenario)

    assert scenario.seed == 51
    assert runtime_config["map_config"]["seed"] == 51
    assert runtime_config["map_config"]["density"] == 10
    assert runtime_config["map_config"]["max_view_dst"] == 250
    assert runtime_config["robot_config"]["robot_type"] == 1
    assert scenario.preview_payload["agent_pos"] == [[1.0, 3.0]]
    assert scenario.preview_payload["goal_pos"] == [[10.0, 30.0]]
    assert "terrain_map" not in scenario.preview_payload
    assert scenario.validation_passed is True


def test_simulator_3d_generation_accepts_flat_legacy_density_alias():
    service = get_default_environment_generation_service()
    scenario = service.generate(
        build_simulator_3d_request(
            {
                "seed": 52,
                "tree_density": 0.25,
                "terrain_hilliness": 0.4,
                "intruder_count": 2,
            },
            task_kind=TaskKind.PATROL,
        )
    )

    runtime_config = extract_simulator_3d_runtime_config(scenario)

    assert scenario.seed == 52
    assert runtime_config["map_config"]["density"] == 25
    assert runtime_config["map_config"]["mesh_height_multiplayer"] == 2.6
    assert len(scenario.preview_payload["goal_pos"]) == 2
    assert scenario.validation_passed is True
