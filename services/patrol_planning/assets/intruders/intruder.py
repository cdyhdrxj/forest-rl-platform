from __future__ import annotations
from abc import ABC, abstractmethod

class GridWorldIntruder:
    """Класс нарушителей для сеточного мира"""

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward = 1):
        #X и Y тут поменяны наоборот потому что в numpy x~rows (Y) а y~columns (X)
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.catch_reward = catch_reward
        self.is_random_spawned = is_random_spawned
        
    
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

        if self.is_random_spawned:

            max_attempts = 100

            for _ in range(max_attempts):

                x = env.np_random.integers(0, env.grid_world_size)
                y = env.np_random.integers(0, env.grid_world_size)

                # проверяем:
                # 1. нет другого нарушителя
                # 2. нет агента
                if (
                    env.word_layers["intruders"][x, y] == 0
                    and not (x == env.agent.x and y == env.agent.y)
                ):
                    self.x = x
                    self.y = y

                    env.word_layers["intruders"][x, y] = 1
                    return

            raise RuntimeError("Не удалось найти свободную клетку для спавна нарушителя")

        else:
            # проверка чтобы не заспавниться на агенте
            if self.start_x == env.agent.x and self.start_y == env.agent.y:
                raise RuntimeError("Нарушитель не может заспавниться на агенте")

            self.x = self.start_x
            self.y = self.start_y
            env.word_layers["intruders"][self.x, self.y] = 1


      