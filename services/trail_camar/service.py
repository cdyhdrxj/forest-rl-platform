from apps.api.sb3.sb3_trainer import SB3Trainer
from services.scenario_generator import (
    build_continuous_trail_request,
    extract_continuous_runtime_kwargs,
    get_default_environment_generation_service,
)
from services.trail_camar.callback import CamarCallback
from services.trail_camar.wrapper import CamarGymWrapper


class CamarService(SB3Trainer):
    """Training service for the CAMAR environment."""

    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = self._make_state()

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "trail")
        super().start(params)

    def stop(self) -> None:
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state = self._make_state()

    def get_state(self) -> dict:
        s = self.training_state
        base = {
            "running": s["running"],
            "episode": s["episode"],
            "step": s["step"],
            "total_reward": s["total_reward"],
            "last_episode_reward": s["last_episode_reward"],
            "new_episode": s["new_episode"],
            "agent_pos": s["agent_pos"],
            "goal_pos": s["goal_pos"],
            "landmark_pos": s["landmark_pos"],
            "is_collision": s["is_collision"],
            "goal_count": s["goal_count"],
            "collision_count": s["collision_count"],
            "terrain_map": s["terrain_map"],
        }
        if s["mode"] == "trail":
            base["trajectory"] = s["trajectory"]
        return base

    def _build_env(self, params: dict) -> CamarGymWrapper:
        generation_service = get_default_environment_generation_service()
        scenario = generation_service.generate(build_continuous_trail_request(params))
        return CamarGymWrapper(**extract_continuous_runtime_kwargs(scenario))

    def _make_callback(self) -> CamarCallback:
        return CamarCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.update(
            {
                "episode": 0,
                "step": 0,
                "total_reward": 0.0,
                "last_episode_reward": 0.0,
                "new_episode": False,
                "goal_count": 0,
                "collision_count": 0,
                "trajectory": [],
                "terrain_map": None,
            }
        )

    @staticmethod
    def _make_state() -> dict:
        return {
            "running": False,
            "mode": "trail",
            "episode": 0,
            "step": 0,
            "total_reward": 0.0,
            "last_episode_reward": 0.0,
            "new_episode": False,
            "agent_pos": [],
            "goal_pos": [],
            "landmark_pos": [],
            "is_collision": False,
            "goal_count": 0,
            "collision_count": 0,
            "trajectory": [],
            "terrain_map": None,
        }
