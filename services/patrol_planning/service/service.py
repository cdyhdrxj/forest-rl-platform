from stable_baselines3.common.env_util import make_vec_env
import numpy as np

from apps.api.sb3.sb3_trainer import SB3Trainer
from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.service.callback import GridWorldCallback
from services.patrol_planning.service.models import GridWorldTrainState
from services.scenario_generator.models import GeneratedScenario


class GridWorldService(SB3Trainer):
    """Training service for the grid patrol environment."""

    def __init__(self):
        self.env: GridWorld = None
        self.model = None
        self.training_state: GridWorldTrainState = self._make_state()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_config: GridWorldConfig | None = None
        self.loaded_static_layers: dict[str, np.ndarray] = {}

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
        self.loaded_config = GridWorldConfig.model_validate(runtime_config or {})

        self.loaded_static_layers = {}
        terrain = scenario.get_layer_data("terrain")
        if terrain is not None:
            self.loaded_static_layers["terrain"] = terrain

        self._apply_preview_state(scenario)

    def get_state(self) -> dict:
        s = self.training_state
        base = {
            "running": s.running,
            "episode": s.episode,
            "step": s.step,
            "total_reward": s.total_reward,
            "last_episode_reward": s.last_episode_reward,
            "new_episode": s.new_episode,
            "agent_pos": s.agent_pos,
            "goal_pos": s.goal_pos,
            "landmark_pos": s.landmark_pos,
            "is_collision": s.is_collision,
            "goal_count": s.goal_count,
            "collision_count": s.collision_count,
            "intruders_remaining": s.i_count,
            "terrain_map": s.terrain_map,
        }
        if s.mode == "trail":
            base["trajectory"] = s.trajectory
        return base

    def _build_env(self, params: dict) -> GridWorld:
        if self.loaded_config is None:
            raise RuntimeError("GridWorldService.start() requires a scenario loaded by the dispatcher")

        env = GridWorld.load(self.loaded_config, static_layers=self.loaded_static_layers)
        env.train_state = self.training_state
        return make_vec_env(lambda: env, n_envs=1)

    def _make_callback(self) -> GridWorldCallback:
        return GridWorldCallback(self.training_state)

    def _reset_counters(self) -> None:
        self.training_state.reset_counters()

    @staticmethod
    def _make_state() -> GridWorldTrainState:
        return GridWorldTrainState()

    def validate_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> list[str]:
        messages: list[str] = []
        if scenario.environment_kind.value != "grid":
            messages.append("GridWorld runtime can load only grid scenarios")
        if scenario.runtime_context.get("patrol") is None:
            messages.append("GridWorld runtime requires patrol runtime context")
        terrain = scenario.get_layer_data("terrain")
        if terrain is None:
            messages.append("GridWorld runtime requires a terrain layer")
        if runtime_config is None:
            messages.append("GridWorld runtime requires serialized runtime config")
        return messages

    def _apply_preview_state(self, scenario: GeneratedScenario) -> None:
        preview = scenario.preview_payload
        terrain = scenario.get_layer_data("terrain")

        self.training_state.agent_pos = list(preview.get("agent_pos") or [])
        self.training_state.goal_pos = list(preview.get("goal_pos") or [])
        self.training_state.landmark_pos = list(preview.get("landmark_pos") or [])
        self.training_state.trajectory = []
        self.training_state.is_collision = False
        self.training_state.new_episode = False
        self.training_state.running = False
        self.training_state.i_count = len(preview.get("goal_pos") or [])
        if terrain is not None:
            self.training_state.terrain_map = np.asarray(terrain, dtype=np.float32).tolist()
        else:
            self.training_state.terrain_map = preview.get("terrain_map")
