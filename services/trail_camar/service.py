from __future__ import annotations

from typing import Any

from apps.api.sb3.sb3_trainer import SB3Trainer
from services.scenario_generator.models import GeneratedScenario
from services.trail_camar.callback import CamarCallback
from services.trail_camar.wrapper import CamarGymWrapper


class CamarService(SB3Trainer):

    def __init__(self):
        super().__init__()
        self.env: CamarGymWrapper | None = None
        self.model = None
        self.training_state = self._make_state()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_wrapper_kwargs: dict[str, Any] | None = None

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

    def load_scenario(
        self,
        scenario: GeneratedScenario,
        runtime_config: dict[str, Any] | None = None,
    ) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario

        # Достаём wrapper_kwargs из сценария
        ctx = scenario.runtime_context.get("continuous_2d", {})
        self.loaded_wrapper_kwargs = dict(ctx.get("wrapper_kwargs", {}))

        self._apply_preview_state(scenario)

    def get_state(self) -> dict[str, Any]:
        s = self.training_state
        return {
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
            "trajectory": s.get("trajectory", []),
        }

    def _build_env(self, params: dict) -> CamarGymWrapper:
        if self.loaded_wrapper_kwargs is None:
            raise RuntimeError("Call load_scenario() before start()")

        # Фильтруем только известные параметры
        filtered = {
            k: v
            for k, v in self.loaded_wrapper_kwargs.items()
            if k in CamarGymWrapper._KNOWN_PARAMS
        }
        return CamarGymWrapper(**filtered)

    def _make_callback(self) -> CamarCallback:
        return CamarCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.update({
            "episode": 0,
            "step": 0,
            "total_reward": 0.0,
            "last_episode_reward": 0.0,
            "new_episode": False,
            "goal_count": 0,
            "collision_count": 0,
            "trajectory": [],
        })

    def validate_scenario(
        self,
        scenario: GeneratedScenario,
        runtime_config: dict[str, Any] | None = None,
    ) -> list[str]:
        messages = []
        if scenario.environment_kind.value != "continuous_2d":
            messages.append("CamarService supports only continuous_2d")
        ctx = scenario.runtime_context.get("continuous_2d", {})
        if not ctx.get("wrapper_kwargs"):
            messages.append("Missing wrapper_kwargs in runtime_context")
        return messages

    @staticmethod
    def _make_state() -> dict[str, Any]:
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
        }

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        self.training_state.update({
            "running": False,
            "agent_pos": list(preview.get("agent_pos") or []),
            "goal_pos": list(preview.get("goal_pos") or []),
            "landmark_pos": list(preview.get("landmark_pos") or []),
            "trajectory": [],
            "is_collision": False,
            "new_episode": False,
        })