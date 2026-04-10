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
    extract_coverage_runtime_layout,
    extract_continuous_runtime_kwargs,
    extract_reforestation_runtime_layout,
    get_default_environment_generation_service,
)


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
