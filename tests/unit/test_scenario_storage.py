import numpy as np

from services.scenario_generator.models import (
    EnvironmentKind,
    GeneratedLayer,
    GeneratedScenario,
    GenerationRequest,
    TaskKind,
)
from services.scenario_generator.storage import load_stored_scenario, store_generated_scenario


def test_stored_scenario_roundtrip(tmp_path):
    request = GenerationRequest(
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        seed=17,
        terrain_params={"grid_size": 4},
        forest_params={"terrain_hilliness": 0.4},
        task_params={"intruder_count": 1},
        metadata={"source": "unit-test"},
    )
    scenario = GeneratedScenario(
        environment_kind=EnvironmentKind.GRID,
        task_kind=TaskKind.PATROL,
        seed=17,
        generator_name="unit",
        generator_version="v1",
        effective_params={"grid_size": 4},
        preview_payload={"terrain_map": [[0.0, 1.0], [1.0, 0.0]], "agent_pos": [[1.0, 1.0]]},
        runtime_context={"patrol": {"agent_pos": [1, 1], "intruder_positions": [[2, 2]]}},
    )
    scenario.add_layer(
        GeneratedLayer(
            name="terrain",
            layer_type="terrain",
            data=np.arange(16, dtype=np.float32).reshape(4, 4),
        )
    )

    stored = store_generated_scenario(
        scenario=scenario,
        request=request,
        runtime_config={"seed": 17, "grid_size": 4},
        target_dir=tmp_path / "scenario",
    )
    loaded = load_stored_scenario(stored.manifest_path)

    assert loaded.scenario.environment_kind is EnvironmentKind.GRID
    assert loaded.scenario.task_kind is TaskKind.PATROL
    assert loaded.scenario.seed == 17
    assert loaded.runtime_config == {"seed": 17, "grid_size": 4}
    assert loaded.request.metadata == {"source": "unit-test"}
    assert np.array_equal(loaded.scenario.get_layer_data("terrain"), scenario.get_layer_data("terrain"))
