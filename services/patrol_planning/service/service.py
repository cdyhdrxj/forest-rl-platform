from __future__ import annotations

import sys
import os

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)
# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apps.api.sb3.sb3_trainer import SB3Trainer
from stable_baselines3.common.env_util import make_vec_env
import numpy as np

from services.patrol_planning.assets.envs.models import GridForestConfig 
from services.patrol_planning.service.models import GridWorldTrainState
from services.patrol_planning.service.callback import GridWorldCallback
from services.patrol_planning.assets.envs.forest import GridForest
from services.scenario_generator.models import GeneratedScenario
from services.scenario_generator import extract_patrol_runtime_context

class GridWorldService(SB3Trainer):
    """Training service for the grid patrol environment."""

    def __init__(self):
        self.env: GridForest = None
        self.model = None
        self.training_state: GridWorldTrainState = self._make_state()
        self.loaded_scenario: GeneratedScenario | None = None
        self.loaded_config: GridForestConfig | None = None
        self.loaded_static_layers: dict[str, np.ndarray] = {}

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "patrol")
        super().start(params)

    def stop(self) -> None:
        super().stop()

    def reset(self) -> None:
        self.stop()
        self.training_state.reset_counters()  
        self.training_state.running = False
        if self.loaded_scenario is not None:
            self._apply_preview_state(self.loaded_scenario)

    def load_scenario(self, scenario: GeneratedScenario, runtime_config: dict | None = None) -> None:
        self.stop()
        self.env = None
        self.model = None
        self.training_state = self._make_state()
        self.training_state["mode"] = scenario.task_kind.value
        self.loaded_scenario = scenario
        
        self.loaded_config = GridForestConfig.model_validate(runtime_config or {})
        
        if self.loaded_config.map_seed is None:
            self.loaded_config = self.loaded_config.model_copy(update={"map_seed": scenario.seed})

        self.loaded_patrol_context = extract_patrol_runtime_context(scenario)

        _map_config = self.loaded_config.model_copy(deep=True)
        _map_config.intruder_config = []
        _tmp_env = GridForest.load(_map_config)
        self.loaded_static_layers["passability"] = _tmp_env.world_layers["passability"].copy()
        self.loaded_static_layers["value"] = _tmp_env.world_layers["value"].copy()
        del _tmp_env

        self._apply_preview_state(scenario)

    def get_state(self) -> dict:
        s = self.training_state

        def _to_serializable(v):
            if hasattr(v, "tolist"):
                return v.tolist()
            return v

        base = {
            "running": s.running,
            "episode": s.episode,
            "step": s.step,
            "total_reward": float(s.total_reward),
            "total_damage": float(s.total_damage),
            "last_episode_reward": float(s.last_episode_reward),
            "new_episode": s.new_episode,
            "agent_pos": [list(map(float, p)) for p in s.agent_pos],
            "goal_pos": [list(map(float, p)) for p in s.goal_pos],
            "world_layers": {
                k: _to_serializable(v)
                for k, v in (s.world_layers or {}).items()
            },
            "obs_raw": None,
            "i_count": s.i_count,
        }
        if s.mode == "patrol":
            base["trajectory"] = [list(map(float, p)) for p in s.trajectory]
        return base

    def _build_env(self, params: dict):
        if self.loaded_config is None:
            raise RuntimeError("No scenario loaded")

        config = self.loaded_config.model_copy(deep=True)
        
        if "max_steps" in params:
            config.max_steps = params["max_steps"]
        
        config.obs_config.layers_count = 6
        static_layers = self.loaded_static_layers
        
        scenario_seed = None
        if self.loaded_scenario is not None:
            scenario_seed = self.loaded_scenario.runtime_context.get("seed", self.loaded_scenario.seed)
        
        use_random_spawn = config.agent_config.is_random_spawned

        def factory():
            env = GridForest.load(config)
            
            if "terrain" in static_layers:
                env.world_layers["terrain"] = static_layers["terrain"].copy()
                env.layers_backup["terrain"] = static_layers["terrain"].copy()
            if "passability" in static_layers:
                env.world_layers["passability"] = static_layers["passability"].copy()
                env.layers_backup["passability"] = static_layers["passability"].copy()
            if "value" in static_layers:
                env.world_layers["value"] = static_layers["value"].copy()
                env.layers_backup["value"] = static_layers["value"].copy()
            
            env.train_state = self.training_state
            
            if use_random_spawn:
                env.reset()  
            else:
                env.reset(seed=scenario_seed) 
            
            return env
        
        return make_vec_env(factory, n_envs=1)

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
        
        self.training_state.goal_pos = []
        self.training_state.i_count = 0
        
        if self.loaded_config and not self.loaded_config.agent_config.is_random_spawned:
            self.training_state.agent_pos = list(preview.get("agent_pos") or [])
        else:
            self.training_state.agent_pos = []
            
        self.training_state.trajectory = []
        self.training_state.new_episode = False
        self.training_state.running = False
        
        layers = {}
        terrain = scenario.get_layer_data("terrain")
        if terrain is not None:
            layers["terrain"] = np.asarray(terrain, dtype=np.float32).tolist()
        else:
            layers["terrain"] = preview.get("terrain_map")
        
        if "passability" in self.loaded_static_layers:
            layers["passability"] = self.loaded_static_layers["passability"].tolist()
        if "value" in self.loaded_static_layers:
            layers["value"] = self.loaded_static_layers["value"].tolist()
        
        self.training_state.world_layers = layers