from __future__ import annotations
import gymnasium as gym
from gymnasium import spaces
import numpy as np
from .obs import Observation

from services.patrol_planning.assets.agents.agent import GridWorldAgent

class ObservationBox(Observation):
    """Custom observation handler for the forest patrol environment."""

    def __init__(self, obs_size=10, cell_max_value=10, layers_count: int  = 2):
        super().__init__(obs_size, cell_max_value)
        # внутреннее описание пространства для RL
        
        self.layers_count = layers_count
        
        self.space = spaces.Box(
            low=0,
            high=1.0,
            shape=self.get_obs_shape(),
            dtype=np.float32
        )


    def build_observation(self, layers: dict, agent: GridWorldAgent):
        """
        Построить локальное наблюдение вокруг агента.

        layers: dict[str, np.ndarray] — словарь слоёв карты
        agent_pos: (x, y) — позиция агента
        """
        
        x = agent.x
        y = agent.y
        half = self.obs_size // 2 #расстояние от агента до края окна

        # предполагаем что все слои одинакового размера
        sample_layer = next(iter(layers.values()))
        size_x, size_y = sample_layer.shape

        # границы окна
        x_min = max(0, x - half)
        x_max = min(size_x, x + half + 1)
        y_min = max(0, y - half)
        y_max = min(size_y, y + half + 1)

        # padding
        pad_x1 = max(0, half - x)
        pad_x2 = max(0, (x + half + 1) - size_x)
        pad_y1 = max(0, half - y)
        pad_y2 = max(0, (y + half + 1) - size_y)

        obs_layers = []

        for layer in layers.values():

            obs = layer[x_min:x_max, y_min:y_max]

            obs = np.pad(
                obs,
                ((pad_x1, pad_x2), (pad_y1, pad_y2)),
                constant_values=0
            )

            obs_layers.append(obs)

        # (channels, obs_size, obs_size)
        return np.stack(obs_layers)
    
    def get_obs_shape(self):
        """
        Получить shape
        """

        #Создаём двумерный слой размером с наблюдение
        layer = np.zeros((self.obs_size, self.obs_size))
        
        #Формируем входные данные для функции
        layers = {f"layer_{i}": layer.copy() for i in range(self.layers_count)}
        
        obs = self.build_observation(layers, GridWorldAgent(0,0))
        return obs.shape
        