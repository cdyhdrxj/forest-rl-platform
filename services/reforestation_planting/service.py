from stable_baselines3.common.env_util import make_vec_env
import numpy as np

from apps.api.sb3.sb3_trainer import SB3Trainer
from services.reforestation_planting.callback import PlantingCallback
from services.reforestation_planting.environment import SeedlingPlantingEnv
from services.reforestation_planting.models import PlantingEnvConfig, PlantingTrainState
from services.scenario_generator import extract_reforestation_runtime_layout
from services.scenario_generator.models import GeneratedScenario


class SeedlingPlantingService(SB3Trainer):
    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = PlantingTrainState()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_config: PlantingEnvConfig | None = None
        self.loaded_layout: dict | None = None

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "reforestation")
        super().start(params)

    def stop(self) -> None:
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state = PlantingTrainState()
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = PlantingTrainState()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario
        self.loaded_config = PlantingEnvConfig.model_validate(runtime_config or {})
        self.loaded_layout = extract_reforestation_runtime_layout(scenario)
        self._apply_preview_state(scenario)

    def get_state(self) -> dict:
        s = self.training_state
        return {
            "running": s.running,
            "episode": s.episode,
            "step": s.step,
            "total_reward": s.total_reward,
            "last_episode_reward": s.last_episode_reward,
            "new_episode": s.new_episode,
            "agent_pos": s.agent_pos,
            "goal_pos": s.goal_pos,
            "landmark_pos": s.landmark_pos,
            "planted_pos": s.planted_pos,
            "is_collision": s.is_collision,
            "goal_count": s.successful_plant_count,
            "collision_count": s.collision_count,
            "terrain_map": s.terrain_map,
            "trajectory": s.trajectory,
            "coverage_ratio": s.coverage_ratio,
            "remaining_seedlings": s.remaining_seedlings,
            "invalid_plant_count": s.invalid_plant_count,
            "plantable_map": s.plantable_map,
            "planted_map": s.planted_map,
        }

    def _build_env(self, params: dict):
        if self.loaded_config is None or self.loaded_layout is None:
            raise RuntimeError("SeedlingPlantingService.start() requires a scenario loaded by the dispatcher")

        def factory():
            env = SeedlingPlantingEnv(self.loaded_config, generated_layout=self.loaded_layout)
            env.train_state = self.training_state
            return env

        return make_vec_env(factory, n_envs=1)

    def _make_callback(self) -> PlantingCallback:
        return PlantingCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.reset_counters()

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "grid":
            messages.append("Reforestation runtime can load only grid scenarios")
        if scenario.runtime_context.get("reforestation") is None:
            messages.append("Reforestation runtime requires reforestation layout in runtime context")
        if scenario.get_layer_data("free_mask") is None:
            messages.append("Reforestation runtime requires a free_mask layer")
        if runtime_config is None:
            messages.append("Reforestation runtime requires serialized runtime config")
        return messages

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        layout = dict(scenario.runtime_context.get("reforestation") or {})
        free_mask = np.asarray(layout.get("free_mask")) if "free_mask" in layout else None
        plantable_mask = np.asarray(layout.get("plantable_mask")) if "plantable_mask" in layout else None

        self.training_state.agent_pos = list(preview.get("agent_pos") or [])
        self.training_state.goal_pos = list(preview.get("goal_pos") or [])
        self.training_state.landmark_pos = list(preview.get("landmark_pos") or [])
        self.training_state.planted_pos = []
        self.training_state.trajectory = []
        self.training_state.is_collision = False
        self.training_state.new_episode = False
        self.training_state.running = False
        self.training_state.coverage_ratio = 0.0
        self.training_state.remaining_seedlings = int(self.loaded_config.initial_seedlings) if self.loaded_config else 0
        if free_mask is not None and free_mask.size:
            self.training_state.terrain_map = (1.0 - free_mask).tolist()
        else:
            self.training_state.terrain_map = preview.get("terrain_map")
        self.training_state.plantable_map = plantable_mask.tolist() if plantable_mask is not None else None
        self.training_state.planted_map = (
            np.zeros_like(plantable_mask, dtype=np.float32).tolist() if plantable_mask is not None else None
        )
