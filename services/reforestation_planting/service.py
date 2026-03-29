from stable_baselines3.common.env_util import make_vec_env

from apps.api.sb3.sb3_trainer import SB3Trainer
from services.reforestation_planting.callback import PlantingCallback
from services.reforestation_planting.environment import SeedlingPlantingEnv
from services.reforestation_planting.models import PlantingEnvConfig, PlantingTrainState
from services.scenario_generator import (
    build_reforestation_request,
    extract_reforestation_runtime_layout,
    get_default_environment_generation_service,
)


class SeedlingPlantingService(SB3Trainer):
    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = PlantingTrainState()

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "reforestation")
        super().start(params)

    def stop(self) -> None:
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state = PlantingTrainState()

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
        config = PlantingEnvConfig.model_validate(params)
        generation_service = get_default_environment_generation_service()
        scenario = generation_service.generate(build_reforestation_request(config))
        generated_layout = extract_reforestation_runtime_layout(scenario)

        def factory():
            env = SeedlingPlantingEnv(config, generated_layout=generated_layout)
            env.train_state = self.training_state
            return env

        return make_vec_env(factory, n_envs=1)

    def _make_callback(self) -> PlantingCallback:
        return PlantingCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.reset_counters()
