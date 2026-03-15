from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import List
from services.patrol_planning.src.pp_types import AgentActions

import copy
import time

#Сеточный мир
class GridWorld(gym.Env):
    """Сеточный мир"""

    def __init__(self, agent: GridWorldAgent, obs_model: Observation, grid_world_size = 20, intruders: List[GridWorldIntruder] = [], max_steps: int = 50):

        self.grid_world_size = grid_world_size
        
        #Слои
        self.word_layers = {  
            "terrain": np.zeros((grid_world_size,grid_world_size), dtype=np.float32),
            "intruders": np.zeros((grid_world_size,grid_world_size), dtype=np.float32)
        }
        #Агент
        self.agent = agent
        
        #Нарушители
        self.intruders_start = copy.deepcopy(intruders)
        self.intruders = copy.deepcopy(intruders)
        
        #Переопределяем параметр класса
        self.action_space = spaces.Discrete(len(AgentActions))

        #Переопределяем параметр класса
        self.obs = obs_model
        self.observation_space = self.obs.space
        
        #Длина эпизода (в шагах)
        self.max_steps = max_steps
        self.cur_step = 0
        
        #Передаётся вручную
        self.renderer = None
        self.render_time_sleep = 0.0
        
    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        #Сброс сеточного мира
        #TODO
        self.word_layers = {  
            "terrain": np.zeros((self.grid_world_size,self.grid_world_size)),
            "intruders": np.zeros((self.grid_world_size,self.grid_world_size))
        }
        
        #Сброс агента
        self.agent.reset(self)
        
        #Сброс нарушителей
        self.intruders = copy.deepcopy(self.intruders_start)
        for i in self.intruders:
            #Сбрасываем чтобы учесть случайное появление 
            i.reset(self)

        observation = self.obs.build_observation(self.word_layers, self.agent)

        info = {}

        return observation, info

    def step(self, action):

        #Обработка действия агента
        self.agent.step(self, action)

        reward = 0
        terminated = False
        truncated = False
        
        #Обновляем нарушителей
        for i in self.intruders:
            reward += i.step(self)
        
        #Проверяем пойманы ли все нарушители?
        if len(self.intruders) == 0:
            #завершаем эпизод
            terminated = True
            
        #Проверяем превышение по шагам
        self.cur_step += 1
        if self.cur_step >= self.max_steps:
            truncated = True
        
        observation = self.obs.build_observation(self.word_layers, self.agent)

        info = {"intruders_left" : len(self.intruders)}
        
        #Обновляем рендер если включено
        if self.renderer is not None:
            self.renderer.live.update(self.renderer.render())
            time.sleep(self.render_time_sleep)
            
                    #Конвертируем в формат для CNN
        return observation, reward, terminated, truncated, info
    