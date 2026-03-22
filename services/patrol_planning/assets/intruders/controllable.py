from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from enum import IntEnum
from services.patrol_planning.assets.intruders.intruder import GridWorldIntruder
from services.patrol_planning.src.pp_types import InputActions
from services.patrol_planning.assets.intruders.models import IntruderConfig
from typing import Type



class Controllable(GridWorldIntruder):
    """Класс управляемых нарушителей для сеточного мира"""

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward = 1):
        super().__init__(y, x, is_random_spawned, catch_reward)
        
        self.input_action = InputActions.STAY

    def get_symbol(self):
            return '&'
        
    def step(self, env: GridWorld):
        
        #Удаляем свою старую позицию из мира
        env.word_layers["intruders"][self.x][self.y] = 0
        
        #input_action нужно обновлять внешними механизмами
        action = self.input_action
        
        if action == InputActions.UP:
            self.x -= 1
        elif action == InputActions.DOWN: 
            self.x += 1
        elif action == InputActions.LEFT:
            self.y -= 1
        elif action == InputActions.RIGHT:
            self.y += 1
        elif action == InputActions.STAY:
            pass

        # границы карты
        self.x = np.clip(self.x, 0, env.grid_world_size - 1)
        self.y = np.clip(self.y, 0, env.grid_world_size - 1)
        
        #Проверяем не поймал ли агент
        agent = env.agent
        
        if agent.x == self.x and agent.y == self.y:
            env.intruders.remove(self) #удаляем себя т.к агент нейтрализовал
            
            return self.catch_reward #Возвращаем награду за поимку
        
        #Иначе переходим в новую позицию
        env.word_layers["intruders"][self.x][self.y] = 1

        return 0

    @staticmethod
    def load(config: IntruderConfig) -> Controllable:
        """
        Создает экземпляр Controllable на основе конфигурации.

        Args:
            config: Конфигурация нарушителя

        Returns:
            Экземпляр Controllable
        """
        return Controllable(
            y=config.pos[1],
            x=config.pos[0],
            is_random_spawned=config.is_random_spawned,
            catch_reward=config.catch_reward
        )
