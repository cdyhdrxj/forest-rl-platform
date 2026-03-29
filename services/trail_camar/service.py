from apps.api.sb3.sb3_trainer import SB3Trainer
from services.scenario_generator import extract_continuous_runtime_kwargs
from services.scenario_generator.models import GeneratedScenario
from services.trail_camar.callback import CamarCallback
from services.trail_camar.wrapper import CamarGymWrapper


class CamarService(SB3Trainer):
    """Training service for the CAMAR environment."""

    def __init__(self):
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_runtime_kwargs: dict | None = None

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "trail")
        super().start(params)

    def stop(self) -> None:
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state = self._make_state()
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario
        self.loaded_runtime_kwargs = dict(runtime_config or extract_continuous_runtime_kwargs(scenario))
        self._apply_preview_state(scenario)

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
        if self.loaded_runtime_kwargs is None:
            raise RuntimeError("CamarService.start() requires a scenario loaded by the dispatcher")

        return CamarGymWrapper(**self.loaded_runtime_kwargs)

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

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "continuous_2d":
            messages.append("Continuous trail runtime can load only continuous_2d scenarios")
        if scenario.runtime_context.get("trail") is None:
            messages.append("Continuous trail runtime requires trail runtime context")
        if scenario.get_layer_data("terrain") is None:
            messages.append("Continuous trail runtime requires a terrain layer")
        if runtime_config is None:
            messages.append("Continuous trail runtime requires serialized runtime config")
        return messages

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

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        self.training_state.update(
            {
                "running": False,
                "agent_pos": list(preview.get("agent_pos") or []),
                "goal_pos": list(preview.get("goal_pos") or []),
                "landmark_pos": list(preview.get("landmark_pos") or []),
                "trajectory": [],
                "is_collision": False,
                "new_episode": False,
                "terrain_map": preview.get("terrain_map"),
            }
        )
