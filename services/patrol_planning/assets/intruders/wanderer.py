from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from enum import IntEnum
from .intruder import GridWorldIntruder

class Actions(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4

class Wanderer(GridWorldIntruder):
    """Класс нарушителей-бродяг для сеточного мира"""

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward = 1):
        super().__init__(y, x, is_random_spawned, catch_reward)

    def get_symbol(self):
            return '&'
        
    def step(self, env: GridWorld):
        
        #Удаляем свою старую позицию из мира
        env.word_layers["intruders"][self.x][self.y] = 0
        
        #Выбирает случайное действие и реализовывает его
        action = Actions(env.np_random.integers(len(Actions)))
        
        if action == Actions.UP:
            self.x -= 1
        elif action == Actions.DOWN: 
            self.x += 1
        elif action == Actions.LEFT:
            self.y -= 1
        elif action == Actions.RIGHT:
            self.y += 1
        elif action == Actions.STAY:
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
        
