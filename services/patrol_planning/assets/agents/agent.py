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

    def __init__(self, y, x, is_random_spawned: bool = False, m_block = 1.0, m_out = 1.0, m_stay = 0.001):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.is_random_spawned = is_random_spawned
        self.m_block = m_block
        self.m_out = m_out
        self.m_stay = m_stay
        
    def step(self, env: GridWorld, input_action):
        """
        Логика управления агентом. 
        Args:
            input_action: ввод
        """
        
        reward = 0.0 #Награда за действия агента
        last_pos = [self.x, self.y]
        
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

        #Проверка выхода за границу карты
        if  self.x < 0 or self.x >= env.grid_world_size or self.y < 0 or  self.y >= env.grid_world_size:
            reward -= self.m_out #Назначаем штраф за некорректное поведение
            # границы карты (ограничиваем)
            #Восстанавливаем корретную позицию
            self.x = last_pos[0]
            self.y = last_pos[1]
        
        #Проверка простоя
        if input_action == AgentActions.STAY:
            reward -= self.m_stay #Назначаем штраф за простой. (лучше очень маленькое значение)
        
        #Проверка столкновения
        if type(env).__name__ == 'GridForest':
            passability = env.word_layers["passability"]
            if passability[self.x, self.y] == 0:
                reward -= self.m_block #штрафуем за столкновение с препятствием
                #Восстанавливаем корретную позицию
                self.x = last_pos[0]
                self.y = last_pos[1]
        
        
        return reward      
        
    
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

                # проверяем что там нет нарушителя и это не препятствие
                if env.word_layers["intruders"][x][y] == 0:
                    if type(env).__name__ == 'GridForest' and env.word_layers["passability"][x][y] != 0:
                        self.x = x
                        self.y = y
                        return
                    if type(env).__name__ != 'GridForest':
                        self.x = x
                        self.y = y


            raise RuntimeError("Не удалось найти свободную клетку для спавна агента")
        
        #Заданная точка
        else:
            self.x = self.start_x
            self.y = self.start_y
            
            if env.word_layers["intruders"][self.start_x][self.start_y] == 0 or \
                type(env).__name__ == 'GridForest' and env.word_layers["passability"][self.start_x][self.start_y] != 0:
                pass
            else:
                raise RuntimeError("Попытка разместить агента в непроходимой клетке! Проверьте позицию!")
            
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
    def compute_catch_reward(self) -> float:
        prevented = max(0.0, self.m_defence * (self.m_plan - self.m_damage))
        return self.catch_reward + self.m_damage + prevented
