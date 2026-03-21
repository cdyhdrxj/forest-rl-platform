from __future__ import annotations
from abc import ABC, abstractmethod

from services.patrol_planning.src.pp_types import AgentActions
from enum import IntEnum
from services.patrol_planning.assets.agents.models import AgentConfig
import numpy as np

class GridWorldAgent:
    """Базовый класс для агентов сеточного мира"""
    
    #Действия агента
    ACTIONS: IntEnum = AgentActions

    def __init__(self, y, x, is_random_spawned: bool = False):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.is_random_spawned = is_random_spawned
        
    def step(self, env: GridWorld, input_action):
        """
        Логика управления агентом. 
        Args:
            input_action: ввод
        """
        
        if input_action == AgentActions.UP:
            self.x -= 1
        elif input_action == AgentActions.DOWN: 
            self.x += 1
        elif input_action == AgentActions.LEFT:
            self.y -= 1
        elif input_action == AgentActions.RIGHT:
            self.y += 1
        elif input_action == AgentActions.STAY:
            pass

        # границы карты
        self.x = np.clip(self.x, 0, env.grid_world_size - 1)
        self.y = np.clip(self.y, 0, env.grid_world_size - 1)        
        
    
    def get_symbol(self):
        """
        Возвращает обозначение нарушителя в среде
        """
        return "A"
    
    def reset(self, env):
        """
        Сбросить агента к начальному состоянию
        """

        #Случайный спавн
        if self.is_random_spawned:

            max_attempts = 100

            for _ in range(max_attempts):

                x = env.np_random.integers(0, env.grid_world_size)
                y = env.np_random.integers(0, env.grid_world_size)

                # проверяем что там нет нарушителя
                if env.word_layers["intruders"][x, y] == 0:
                    self.x = x
                    self.y = y
                    return

            raise RuntimeError("Не удалось найти свободную клетку для спавна агента")
        
        #Заданная точка
        else:
            self.x = self.start_x
            self.y = self.start_y
            
    @staticmethod
    def load(config: AgentConfig) -> GridWorldAgent:
        """
        Создает экземпляр GridWorldAgent на основе конфигурации.

        Args:
            config: Конфигурация агента

        Returns:
            Экземпляр GridWorldAgent
        """
        return GridWorldAgent(
            y=config.pos[1],
            x=config.pos[0],
            is_random_spawned=config.is_random_spawned,
        )
