import random
from apps.api.sb3.sb3_trainer import SB3Trainer
# from services.trail_camar.wrapper import CamarGymWrapper
# from services.trail_camar.callback import CamarCallback


class GridWorldService(SB3Trainer):
    """Сервис обучения агента в среде GridWorld"""

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
        """Сброс среды и модели к изначальным параметрам"""
        self.stop()
        self.training_state = self._make_state()

    def get_state(self) -> dict:
        """Снимок состояния для отправки на фронт"""
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
        """Создание среды с параметрами от фронта"""
        return CamarGymWrapper(
            seed=random.randint(0, 100_000),
            obstacle_density=params.get("obstacle_density", 0.2),
            action_scale=params.get("action_scale", 1.0),
            goal_reward=params.get("goal_reward", 1.0),
            collision_penalty=params.get("collision_penalty", 0.3),
            grid_size=params.get("grid_size", 10),
            max_steps=params.get("max_steps", 200),
            frameskip=params.get("frameskip", 5),
            max_speed=params.get("max_speed", 50.0),
            accel=params.get("accel", 40.0),
            damping=params.get("damping", 0.6),
            dt=params.get("dt", 0.01),
            terrain_penalty=params.get("terrain_penalty", 0.3),
        )

    def _make_callback(self) -> CamarCallback:
        return CamarCallback(self.training_state)

    def _reset_counters(self) -> None:
        """Сброс счётчиков и буферов между запусками"""
        self.training_state.update({
            "episode": 0, "step": 0,
            "total_reward": 0.0, "last_episode_reward": 0.0,
            "new_episode": False, "goal_count": 0,
            "collision_count": 0, "trajectory": [],
            "terrain_map": None,
        })

    @staticmethod
    def _make_state() -> dict:
        return {
            "running": False, "mode": "trail",
            "episode": 0, "step": 0,
            "total_reward": 0.0, "last_episode_reward": 0.0,
            "new_episode": False,
            "agent_pos": [], "goal_pos": [], "landmark_pos": [],
            "is_collision": False,
            "goal_count": 0, "collision_count": 0,
            "trajectory": [], "terrain_map": None,
        }