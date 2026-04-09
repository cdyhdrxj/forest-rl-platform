import sys
import os
import json

# Абсолютный путь до корня проекта (где лежит environment, observations и т.д.)
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..")
)

# Добавляем в sys.path, если ещё нет
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


import random
from apps.api.sb3.sb3_trainer import SB3Trainer
from stable_baselines3.common.env_util import make_vec_env

from services.patrol_planning.assets.envs.models import GridForestConfig
from services.patrol_planning.service.models import GridWorldTrainState
from services.patrol_planning.service.callback import GridWorldCallback
from services.patrol_planning.assets.envs.forest import GridForest

class GridWorldService(SB3Trainer):
    """Сервис обучения агента в среде GridWorld"""

    def __init__(self):
        self.env: GridForest = None
        self.model = None
        self.training_state: GridWorldTrainState = self._make_state()

    def start(self, params: dict) -> None:
        self.training_state["mode"] = params.get("mode", "patrol")
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
            "running": s.running,
            "episode": s.episode,
            "step": s.step,
            "total_reward": s.total_reward,
            "total_damage": s.total_damage,
            "last_episode_reward": s.last_episode_reward,
            "new_episode": s.new_episode,
            "agent_pos": s.agent_pos,
            "goal_pos": s.goal_pos,
            
            "word_layers": s.world_layers,
            "obs_raw": s.obs_raw,
            "i_count": s.i_count,
        }
        if s.mode == "patrol":
            base["trajectory"] = s.trajectory

        return base

    def _build_env(self, params: dict) -> GridForest:
        """Создание среды с параметрами от фронта"""
        #В словаре по ключу grid_forest_config должен быть передан model_dump GridForestConfig
        #Либо сделать params тоже pydantic моделью и просто вложить GridForestConfig
        config = GridForestConfig.model_validate(params['grid_forest_config'])
        env = GridForest.load(config)
        
        #Указываем ссылку на GridWorldTrainState, чтобы среда туда писала каждый step состояние
        env.train_state = self.training_state
        
        #Векторизация среды
        vec_env = make_vec_env(lambda: env, n_envs=1)
        return vec_env

    def _make_callback(self) -> GridWorldCallback:
        return GridWorldCallback(self.training_state)

    def _reset_counters(self) -> None:
        """Сброс счётчиков и буферов между запусками"""
        self.training_state.reset_counters()

    @staticmethod
    def _make_state() -> GridWorldTrainState:
        return GridWorldTrainState()