from __future__ import annotations

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import List, Type

import copy
import time

from services.patrol_planning.assets.envs.models import GridWorldConfig
from services.patrol_planning.service.models import GridWorldTrainState
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.patrol_planning.assets.intruders.controllable import Controllable
from services.patrol_planning.assets.intruders.poacher_simple import PoacherSimple
from services.patrol_planning.service.models import GridWorldTrainState
# TRAJECTORY_MAX_LEN = 200

#Сеточный мир
class GridWorld(gym.Env):
    """Сеточный мир"""

    def __init__(self, agent: GridWorldAgent, obs_model: Observation,
                 grid_world_size = 20, intruders: List[GridWorldIntruder] = [], max_steps: int = 50,
                 intruder_detection_reward = 1, intruder_interception_reward = 1):

        self.grid_world_size = grid_world_size
        
        #Слои
        self.world_layers = {  
            "terrain": np.zeros((grid_world_size,grid_world_size), dtype=np.float32),
            "intruders": np.zeros((grid_world_size,grid_world_size), dtype=np.float32),
            "rows": np.tile(np.arange(grid_world_size, dtype=np.float32).reshape(-1, 1), (1, grid_world_size)),
            "cols": np.tile(np.arange(grid_world_size, dtype=np.float32).reshape(1, -1), (grid_world_size, 1))
        }
        #Агент
        self.agent = agent
        
        #Нарушители
        self.intruders_start = copy.deepcopy(intruders) #Кешируем чтобы потом восстанавливать при reset
        self.intruders = copy.deepcopy(intruders)
        
        #Переопределяем параметр класса (#TODO Должен получать из агента!)
        self.action_space = spaces.Discrete(len(agent.ACTIONS))

        #Переопределяем параметр класса
        self.obs = obs_model
        self.observation_space = self.obs.space
        
        #Длина эпизода (в шагах)
        self.max_steps = max_steps
        
        #Передаётся вручную (снаружи)
        self.renderer = None
        self.render_time_sleep = 0.0
        self.train_state: GridWorldTrainState | None = None #В эту pydantic модель каждый шаг пишет среда
        
        #Награды за нарушителей (множители)
        self.intruder_detection_reward = intruder_detection_reward  #Попадание в область наблюдения
        self.intruder_interception_reward = intruder_interception_reward #Перехват нарушителя, множитель к тому ущербу который нарушитель не успел нанести
        
        #Если не задана структура сохранения данных обучения, создаём её вручную. Если класс используется внутри сервиса, то сервис перезапишет на свою модель.
        if not self.train_state:
            self.train_state = GridWorldTrainState()
        
    def reset(self, seed=None, options=None):

        super().reset(seed=seed)

        #Сброс сеточного мира
        #TODO
        # self.world_layers = {  
        #     "terrain": np.zeros((self.grid_world_size,self.grid_world_size)),
        #     "intruders": np.zeros((self.grid_world_size,self.grid_world_size))
        # }
        #Сбрасываем только известные слои, чтобы не удалить слои дочерних классов
        # self.world_layers["terrain"] = np.zeros((self.grid_world_size,self.grid_world_size))
        self.world_layers["intruders"] = np.zeros((self.grid_world_size,self.grid_world_size))

        #Сброс агента
        self.agent.reset(self)
        
        #Сброс нарушителей
        self.intruders = copy.deepcopy(self.intruders_start)
        for i in self.intruders:
            #Сбрасываем чтобы учесть случайное появление 
            i.reset(self)

        observation = self.obs.build_observation(self.world_layers, self.agent)

        info = {}

        return observation, info

    def step(self, action):
        obs_reward = 0.0
        
        reward = 0 #Награда за этот шаг
        
        #Обработка действия агента
        reward += self.agent.step(self, action)

        
        terminated = False
        truncated = False
        
        observation = self.obs.build_observation(self.world_layers, self.agent)
        
        #Получаем слой с нарушителями (1 слой начиная с 0)
        intruders_layer = observation[1]
        
        #Даём награду за попадание в область видимости
        for row in intruders_layer:
            for e in row:
                if e == 1:
                    reward += obs_reward * self.intruder_detection_reward
        
        #Обновляем нарушителей
        for i in self.intruders:
            reward += i.step(self)
            
        
        #Проверяем пойманы ли все нарушители?
        if len(self.intruders) == 0:
            #завершаем эпизод
            terminated = True
            
        #Проверяем превышение по шагам
        self.train_state.step += 1
        if self.train_state.step >= self.max_steps:
            truncated = True
        
        

        info = {"intruders_left" : len(self.intruders)}
        
        #Обновляем рендер если включено
        if self.renderer is not None:
            self.renderer.live.update(self.renderer.render())
            time.sleep(self.render_time_sleep)
            
        #Обновляем train_state
        self.update_train_state(truncated, terminated, reward, observation)
           
        return observation, reward, terminated, truncated, info
    
    def update_train_state(self, truncated,
                           terminated, reward, obs):
        #Обновляем train_state если включено
        if self.train_state:
            #Позиция агента
            self.train_state.agent_pos = [[self.agent.x, self.agent.y]]
            #Маршрут
            self.train_state.trajectory.append([self.agent.x, self.agent.y])
            #Награда
            self.train_state.total_reward += reward
            #Наблюдение
            self.train_state.obs_raw = obs
            
            
            #Позиции нарушителей
            goal_pos = []
            for i in self.intruders:
                goal_pos.append([i.x, i.y])
            #Позиции
            self.train_state.goal_pos = goal_pos.copy()
            
            #Осталось нарушителей
            self.train_state.i_count = len(self.intruders)
            
            #Шаг
            self.train_state.new_episode = truncated or terminated
            
        

    @staticmethod
    def load(config: GridWorldConfig) -> 'GridWorld':
        """
        Создает настроенный экземпляр GridWorld на основе конфигурации.

        Args:
            config: Конфигурация GridWorldConfig

        Returns:
            GridWorld: Настроенный экземпляр среды

        """
        # Проверка типа модели
        if not isinstance(config, GridWorldConfig):
            raise ValueError(f"Ожидался GridWorldConfig, получено: {type(config)}")

        # Создаем агента из конфигурации
        agent = GridWorldAgent.load(config.agent_config)

        # Создаем модель наблюдения из конфигурации
        match type(config.obs_config).__name__:
            case 'ObsBoxConfig':
                obs_model = ObservationBox.load(config.obs_config)
            case _:
                raise ValueError(f"Неподдерживаемый тип конфига наблюдения: {type(config.obs_config).__name__}")

        # Создаем нарушителей из конфигураций
        intruders = []
        for intruder_config in config.intruder_config: 
            match type(intruder_config).__name__:
                case 'WandererConfig':
                    # По умолчанию создаем Wanderer, но можно добавить логику для определения типа
                    intruders.append(Wanderer.load(intruder_config))
                case 'ControllableConfig':
                    # По умолчанию создаем Wanderer, но можно добавить логику для определения типа
                    intruders.append(Controllable.load(intruder_config))
                case 'PoacherSimpleConfig':
                    intruders.append(PoacherSimple.load(intruder_config))
                case _:
                    raise ValueError(f"Неподдерживаемый тип конфига нарушителя: {type(intruder_config).__name__}")

        # Создаем и возвращаем настроенный экземпляр GridWorld
        return GridWorld(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=config.grid_size,  # По умолчанию, можно сделать конфигурируемым
            intruders=intruders,
            max_steps=config.max_steps,
            intruder_detection_reward=config.intruder_detection_reward,
            intruder_interception_reward=config.intruder_interception_reward
        )
    