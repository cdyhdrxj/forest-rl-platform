"""
GridForest — лесная среда, расширяющая GridWorld.

Добавляет три слоя:
  intruders   — {0, 1} наличие нарушителя
  passability — [0, 1] проходимость ячейки (μ)
  value       — [0, 1000] ценность леса (c)
"""
from __future__ import annotations

import math
import copy
import time
from typing import List, Optional

import numpy as np

from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.assets.envs.src import generate_intruder_schedule, sample_spawn_cell, get_valid_spawn_cells
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.intruders.controllable import Controllable
from services.patrol_planning.assets.intruders.poacher_simple import PoacherSimple
from services.patrol_planning.assets.intruders.models import WandererConfig
from services.patrol_planning.learning.metrics.idleness import IdlenessMetric
from services.patrol_planning.learning.metrics.catch_latency import calc_catch_latency


class GridForest(GridWorld):
    """Лесная сеточная среда с поддержкой проходимости и ценности клеток."""

    def __init__(
        self,
        agent: GridWorldAgent,
        obs_model,
        grid_world_size: int = 20,
        intruders: Optional[List] = None,
        max_steps: int = 50,
        random_spawn_position: bool = True,
        random_spawn_time: bool = True,
        tau_min: int = 0,
        tau_max: int = 0
    ) -> None:
        super().__init__(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=grid_world_size,
            intruders=intruders or [],
            max_steps=max_steps,
        )
        # Добавляем лесные слои поверх базовых
        self.world_layers["passability"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        self.world_layers["value"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        #Словарь со слоями, которые нужно сохранять в самом начале обучения и восстанавливать каждый сброс.
        self.layers_backup =  {}
        
        #Список ячеек, выбранных ботами для рубки
        self.poacher_targets = []
        self.intruder_exit_count = 0
        
        #Создаём расписание
        self.intruder_schedule = []
        
        #Обнуляем список с нарушителями, будем их добавлять постепенно:
        self.intruders = []
        self.remember_intruder_schedule: bool = False
        
        #Появление нарушителей (сохраняем для восстановления)
        self.intruder_schedule_start = []
        self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
        self.tau_min = tau_min
        self.tau_max = tau_max
        
        #Флаги
        #Если верно, то будет брать k нарушителя для k появления
        self.spawn_with_index = len(self.intruder_schedule) == len(self.intruders_start)
        
        self.random_spawn_position = random_spawn_position #Случайное появление нарушителей
        self.random_spawn_time = random_spawn_time #Случайный момент появления нарушителей
        
        
        #Модули для оценки патрулирования
        self.idleness = IdlenessMetric(self)
        
    def step(self, action):
        obs_reward = 0.0
        reward = 0

        # 1. действие агента
        reward += self.agent.step(self, action)

        # 2. СПАВН нарушителя (перенесено вверх)
        t_key = self.train_state.step
        if t_key in self.intruder_schedule:

            index: int = self.intruder_schedule[t_key][0]
            intruder = copy.deepcopy(self.intruders_start[index])

            if self.random_spawn_position:
                self.intruder_schedule[t_key][1] = sample_spawn_cell(self, 0.5)
            else:
                pos: tuple = (intruder.x, intruder.y)
                valid_cells = get_valid_spawn_cells(self, 0.5)

                if pos not in valid_cells:
                    self.intruder_schedule[t_key][1] = sample_spawn_cell(self, 0.5)

            pos = self.intruder_schedule[t_key][1]

            intruder.x = pos[0]
            intruder.y = pos[1]
            intruder.spawn_time = self.train_state.step

            self.intruders.append(intruder)


        terminated = False
        truncated = False

        # 3. теперь строим observation
        observation = self.obs.build_observation(self.world_layers, self.agent)

        # дальше всё как было
        
        #Собираем информацию о посещениях ячеек
        self.idleness.update(observation=observation,
                             agent_pos=(self.agent.x, self.agent.y),
                             step=self.train_state.step)
        
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
            

        info = {"intruders_left" : len(self.intruder_schedule_start) - self.intruder_exit_count}
        
        #Обновляем рендер если включено
        if self.renderer is not None:
            self.renderer.live.update(self.renderer.render())
            time.sleep(self.render_time_sleep)
        
        #Записываем слои в состояние обучение
        self.train_state.world_layers = self.world_layers
           
            
        #Завершаем эпизод если все нарушители вышли/были пойманы из леса
        if self.intruder_exit_count == len(self.intruder_schedule_start):
            terminated = True
        
        
        
        self.train_state.step += 1
        #Проверяем превышение по шагам
        if self.train_state.step >= self.max_steps:
            truncated = True
        
        #Обновляем train_state
        super().update_train_state(truncated, terminated, reward, observation)
        
            
        return observation, reward, terminated, truncated, info

    def generate_forest(
        self,
        seed: Optional[int] = None,
        passability_low: float = 0.0,
        passability_high: float = 1.0,
        impassable_prob: float = 0.15,
        max_value: float = 1000.0,
        value_density: float = 0.7,
    ) -> None:
        """
        Случайно генерирует карту леса.

        Алгоритм:
          1. Для каждой клетки с вероятностью impassable_prob μ = 0,
             иначе μ ~ Uniform(passability_low, passability_high).
          2. Для клеток с μ > 0: с вероятностью value_density
             назначается c ~ Uniform(0, max_value), иначе c = 0.
          3. Для клеток с μ = 0: c = 0 (принудительно).

        Args:
            seed: Зерно генератора для воспроизводимости.
            passability_low: Минимальное значение проходимости (μ > 0).
            passability_high: Максимальное значение проходимости.
            impassable_prob: Вероятность того, что ячейка непроходима (μ = 0).
            max_value: Максимальная ценность ячейки.
            value_density: Доля проходимых клеток, имеющих ценность > 0.
        """
        rng = np.random.default_rng(seed)
        n = self.grid_world_size

        # --- Проходимость ---
        is_impassable = rng.random((n, n)) < impassable_prob
        passability = rng.uniform(passability_low, passability_high, (n, n)).astype(
            np.float32
        )
        passability[is_impassable] = 0.0
        self.world_layers["passability"] = passability

        # --- Ценность ---
        value = np.zeros((n, n), dtype=np.float32)
        passable_mask = passability > 0.0
        has_value_mask = rng.random((n, n)) < value_density
        # Только проходимые клетки могут иметь ценность
        assign_value = passable_mask & has_value_mask
        value[assign_value] = rng.uniform(0.0, max_value, assign_value.sum()).astype(
            np.float32
        )
        self.world_layers["value"] = value


    def reset(self, seed=None, options=None):
        """Сбрасывает среду, сохраняя лесные слои (если уже сгенерированы)."""
        
        #Сброс модулей для оценок патрулирования
        # print('IDLENESS_METRIC:', self.idleness.calculate_metric(self.train_state.step))
        # print('CATCH_LATENCY:', calc_catch_latency(self.train_state))
        # print('TOTAL_DAMAGE:', self.train_state.total_damage)
        
        
        self.idleness.reset()
        
        #Сбрасываем счётчики
        self.train_state.reset_counters()
        

        # Кешируем лесные слои до вызова super().reset(), если сохранения не было
        if not self.layers_backup:

            if self.world_layers.get("passability") is not None:
                self.layers_backup["passability"] = (
                    self.world_layers["passability"].copy()
                )

            if self.world_layers.get("value") is not None:
                self.layers_backup["value"] = (
                    self.world_layers["value"].copy()
                )

        # Получаем сохранённую информацию 
        passability_backup = (
            self.layers_backup["passability"].copy()
            if self.layers_backup.get("passability") is not None
            else None
        )

        value_backup = (
            self.layers_backup["value"].copy()
            if self.layers_backup.get("value") is not None
            else None
        )

        # reset родителя
        _observation, _info = super().reset(seed=seed, options=options)

        # Восстанавливаем слои без ссылок
        if passability_backup is not None:
            self.world_layers["passability"] = passability_backup.copy()
        else:
            self.world_layers["passability"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        if value_backup is not None:
            self.world_layers["value"] = value_backup.copy()
        else:
            self.world_layers["value"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        observation = self.obs.build_observation(self.world_layers, self.agent)
        info = {}
        
        # Убираем нарушителей и их спавн (они спавняться по событиям)
        self.intruders = []
        self.intruder_exit_count = 0
        
        #Сбрасываем цели
        self.poacher_targets = []

        #Сохраняется ли расписание для всех эпизодов
        if self.remember_intruder_schedule:
            #Если пусто => генерируем новове
            if not self.intruder_schedule_start:
                self.intruder_schedule_start = generate_intruder_schedule(self.intruders_start, self.max_steps,
                                                                tau_min=self.tau_min, tau_max=self.tau_max, random = self.random_spawn_time)
            #берём старое
            self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
        else:
            #генерируем новое
            self.intruder_schedule_start = generate_intruder_schedule(self.intruders_start, self.max_steps,
                                                                tau_min=self.tau_min, tau_max=self.tau_max, random = self.random_spawn_time)
            self.intruder_schedule = copy.deepcopy(self.intruder_schedule_start)
            
        return observation, info
    @staticmethod
    def load(config: "GridForestConfig") -> "GridForest":
        """
        Создаёт настроенный экземпляр GridForest из GridForestConfig.

        Автоматически вызывает generate_forest() с параметрами из конфига.

        Args:
            config: GridForestConfig

        Returns:
            GridForest: готовый экземпляр среды с картой
        """
        # Импорт здесь, чтобы избежать циклических зависимостей
        from services.patrol_planning.assets.envs.models import GridForestConfig
        from services.patrol_planning.assets.intruders.models import (
            WandererConfig, ControllableConfig, PoacherConfig,
        )

        if not isinstance(config, GridForestConfig):
            raise ValueError(
                f"Ожидался GridForestConfig, получено: {type(config)}"
            )

        # Агент
        agent = GridWorldAgent.load(config.agent_config)

        # Модель наблюдения
        obs_model = ObservationBox.load(config.obs_config)

        # ПОДДЕРЖИВАЕМ ТОЛЬКО PoacherSimple
        intruders = []
        for intruder_config in config.intruder_config:
            match type(intruder_config).__name__:
                # case "WandererConfig":
                #     intruders.append(Wanderer.load(intruder_config))
                # case "ControllableConfig":
                #     intruders.append(Controllable.load(intruder_config))
                # case "PoacherConfig":
                #     intruders.append(Poacher.load(intruder_config))
                case 'PoacherSimpleConfig':
                    intruders.append(PoacherSimple.load(intruder_config))
                case _:
                    raise ValueError(
                        f"Неподдерживаемый тип нарушителя: {type(intruder_config).__name__}"
                    )

        env = GridForest(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=config.grid_size,
            intruders=intruders,
            max_steps=config.max_steps,
            random_spawn_position=config.random_spawn_position,
            random_spawn_time=config.random_spawn_time,
            tau_min = config.tau_min,
            tau_max = config.tau_max
            
        )
        
        #Генерировать расписание для нарушителей

        # Генерируем карту сразу при создании
        env.generate_forest(
            seed=config.map_seed,
            passability_low=config.passability_low,
            passability_high=config.passability_high,
            impassable_prob=config.impassable_prob,
            max_value=config.max_value,
            value_density=config.value_density,
            
        )
        
        env.reset()

        return env
