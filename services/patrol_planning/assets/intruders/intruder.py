from __future__ import annotations
import warnings
from abc import ABC, abstractmethod
from services.patrol_planning.assets.intruders.models import IntruderConfig
from typing import Type

class GridWorldIntruder:
    """Класс нарушителей для сеточного мира"""

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward=1,
                 manual_spawn: bool = False):
        #X и Y тут поменяны наоборот потому что в numpy x~rows (Y) а y~columns (X)
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.catch_reward = catch_reward
        self.is_random_spawned = is_random_spawned
        self.manual_spawn = manual_spawn
        self.spawn_failed: bool = False

        #Метаданные
        self.spawn_time: int = -1
        self.death_time: int = -1
        
    
    @abstractmethod
    def step(self, env: GridWorld):
        """
        Логика поведения нарушителя.
        Обновляет его состояние и состояние сеточного мира,
        на каждом шаге, должна так же содержить проверку поимки
        и вознаграждение за поимку

        Args:
            env: экземпляр среды сеточного мира
        """
        pass
    
    @abstractmethod
    def get_symbol(self):
        """
        Возвращает обозначение нарушителя в среде
        """
        pass
    
    def reset(self, env):
        """

        Сбросить нарушителя к начальному состоянию
        """
        self.spawn_failed = False

        if self.is_random_spawned:

            max_attempts = 100

            for _ in range(max_attempts):

                x = env.np_random.integers(0, env.grid_world_size)
                y = env.np_random.integers(0, env.grid_world_size)

                # проверяем:
                # 1. нет другого нарушителя
                # 2. нет агента
                if (
                    env.world_layers["intruders"][x, y] == 0
                    and not (x == env.agent.x and y == env.agent.y)
                ):
                    self.x = x
                    self.y = y

                    env.world_layers["intruders"][x, y] = 1
                    return

            # Детерминированный перебор всех ячеек как запасной вариант
            for x in range(env.grid_world_size):
                for y in range(env.grid_world_size):
                    if (env.world_layers["intruders"][x, y] == 0
                            and not (x == env.agent.x and y == env.agent.y)):
                        self.x, self.y = x, y
                        env.world_layers["intruders"][x, y] = 1
                        return

            warnings.warn(
                "GridWorldIntruder: не удалось найти свободную клетку для спавна, пропуск размещения"
            )
            self.x, self.y = -1, -1
            self.spawn_failed = True

        else:
            # проверка чтобы не заспавниться на агенте
            if self.start_x == env.agent.x and self.start_y == env.agent.y:
                warnings.warn(
                    f"GridWorldIntruder: позиция ({self.start_x},{self.start_y}) занята агентом, пропуск размещения"
                )
                self.x, self.y = -1, -1
                self.spawn_failed = True
                return

            self.x = self.start_x
            self.y = self.start_y
            env.world_layers["intruders"][self.x, self.y] = 1

    @staticmethod
    def load(config: IntruderConfig) -> GridWorldIntruder:
        """
        Создает экземпляр GridWorldIntruder на основе конфигурации.

        Args:
            config: Конфигурация нарушителя

        Returns:
            Экземпляр GridWorldIntruder
        """
        return GridWorldIntruder(
            y=config.pos[1],
            x=config.pos[0],
            is_random_spawned=config.is_random_spawned,
            catch_reward=config.catch_reward,
            manual_spawn=config.manual_spawn,
        )
      