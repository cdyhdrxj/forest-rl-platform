"""Базовый класс для всех наблюдений в patrol_planning."""
from __future__ import annotations
from abc import ABC, abstractmethod
import numpy as np

from gymnasium.spaces.space import Space
from services.patrol_planning.assets.observations.models import  ObservationConfig

class Observation(ABC):
    """Базовый абстрактный класс для наблюдений."""

    def __init__(self, obs_size: int):
        """
        Инициализация базового observation.

        Args:
            obs_size: размер наблюдения 
            cell_max_value: максимальное значение в ячейке
        """
        self.obs_size = obs_size
        # self.cell_max_value = cell_max_value
        
        ## gymnasium.spaces.space import Space
        self.space: Space

    @abstractmethod
    def build_observation(self, grid_world: np.ndarray, agent: GridWorldAgent):
        """
        Построить наблюдение вокруг агента.

        Args:
            grid_world: полная карта сеточного мира
            agent_pos: позиция агента (x, y) в сеточном мире

        Returns:
            np.ndarray: построенное наблюдение
        """
        pass

    @staticmethod
    @abstractmethod
    def load(config: ObservationConfig) -> Observation:
        """
        Создать экземпляр наблюдения из конфигурации.

        Args:
            config: конфигурация наблюдения

        Returns:
            Observation: настроенный экземпляр наблюдения
        """
        pass
