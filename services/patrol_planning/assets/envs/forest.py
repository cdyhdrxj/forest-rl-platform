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
from typing import List, Optional

import numpy as np

from services.patrol_planning.assets.envs.environment import GridWorld
from services.patrol_planning.assets.agents.agent import GridWorldAgent
from services.patrol_planning.assets.observations.obs_box import ObservationBox
from services.patrol_planning.assets.intruders.wanderer import Wanderer
from services.patrol_planning.assets.intruders.controllable import Controllable
from services.patrol_planning.assets.intruders.poacher_lite import Poacher
from services.patrol_planning.assets.intruders.models import WandererConfig


class GridForest(GridWorld):
    """Лесная сеточная среда с поддержкой проходимости и ценности клеток."""

    def __init__(
        self,
        agent: GridWorldAgent,
        obs_model,
        grid_world_size: int = 20,
        intruders: Optional[List] = None,
        max_steps: int = 50,
    ) -> None:
        super().__init__(
            agent=agent,
            obs_model=obs_model,
            grid_world_size=grid_world_size,
            intruders=intruders or [],
            max_steps=max_steps,
        )
        # Добавляем лесные слои поверх базовых
        self.word_layers["passability"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        self.word_layers["value"] = np.zeros(
            (grid_world_size, grid_world_size), dtype=np.float32
        )
        #Словарь со слоями, которые нужно сохранять в самом начале обучения и восстанавливать каждый сброс.
        self.layers_backup =  {}

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
        self.word_layers["passability"] = passability

        # --- Ценность ---
        value = np.zeros((n, n), dtype=np.float32)
        passable_mask = passability > 0.0
        has_value_mask = rng.random((n, n)) < value_density
        # Только проходимые клетки могут иметь ценность
        assign_value = passable_mask & has_value_mask
        value[assign_value] = rng.uniform(0.0, max_value, assign_value.sum()).astype(
            np.float32
        )
        self.word_layers["value"] = value

    # ------------------------------------------------------------------ #
    #  Reset                                                               #
    # ------------------------------------------------------------------ #

    def reset(self, seed=None, options=None):
        """Сбрасывает среду, сохраняя лесные слои (если уже сгенерированы)."""

        # Кешируем лесные слои до вызова super().reset(), если сохранения не было
        if not self.layers_backup:

            if self.word_layers.get("passability") is not None:
                self.layers_backup["passability"] = (
                    self.word_layers["passability"].copy()
                )

            if self.word_layers.get("value") is not None:
                self.layers_backup["value"] = (
                    self.word_layers["value"].copy()
                )

        # Получаем сохранённую информацию (копии!)
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
            self.word_layers["passability"] = passability_backup.copy()
        else:
            self.word_layers["passability"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        if value_backup is not None:
            self.word_layers["value"] = value_backup.copy()
        else:
            self.word_layers["value"] = np.zeros(
                (self.grid_world_size, self.grid_world_size),
                dtype=np.float32
            )

        observation = self.obs.build_observation(self.word_layers, self.agent)
        info = {}

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

        # Нарушители
        intruders = []
        for intruder_config in config.intruder_config:
            match type(intruder_config).__name__:
                case "WandererConfig":
                    intruders.append(Wanderer.load(intruder_config))
                case "ControllableConfig":
                    intruders.append(Controllable.load(intruder_config))
                case "PoacherConfig":
                    intruders.append(Poacher.load(intruder_config))
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
        )

        # Генерируем карту сразу при создании
        env.generate_forest(
            seed=config.map_seed,
            passability_low=config.passability_low,
            passability_high=config.passability_high,
            impassable_prob=config.impassable_prob,
            max_value=config.max_value,
            value_density=config.value_density,
        )

        return env
