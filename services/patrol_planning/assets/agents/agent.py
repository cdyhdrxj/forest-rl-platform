from __future__ import annotations
from abc import ABC, abstractmethod

from services.patrol_planning.src.pp_types import AgentActions
from enum import IntEnum
from services.patrol_planning.assets.agents.models import AgentConfig
from services.patrol_planning.assets.rewards.events import MoveEvent, BlockedMoveEvent, StayEvent
import numpy as np

class GridWorldAgent:
    """Базовый класс для агентов сеточного мира"""
    
    #Действия агента
    ACTIONS: IntEnum = AgentActions

    def __init__(self, y, x, is_random_spawned: bool = False, m_block = 1.0, m_out = 1.0, m_stay = 0.001, spawn_min_passability: float = 0.0):
        self.start_x = x
        self.start_y = y
        self.x = x
        self.y = y
        self.is_random_spawned = is_random_spawned
        self.spawn_min_passability = spawn_min_passability
        self.m_block = m_block
        self.m_out = m_out
        self.m_stay = m_stay
        
    def step(self, env: GridWorld, input_action) -> float:
        """Шаг агента: применяет действие, пишет событие в env.step_events.

        Возвращает float-награду для обратной совместимости с GridWorld.step().
        GridForest.step() игнорирует возвращаемое значение и использует события.
        """
        last_pos = [self.x, self.y]

        if input_action == AgentActions.UP:
            self.x -= 1
        elif input_action == AgentActions.DOWN:
            self.x += 1
        elif input_action == AgentActions.LEFT:
            self.y -= 1
        elif input_action == AgentActions.RIGHT:
            self.y += 1

        # Выход за границу карты
        if self.x < 0 or self.x >= env.grid_world_size or self.y < 0 or self.y >= env.grid_world_size:
            self.x, self.y = last_pos[0], last_pos[1]
            env.step_events.append(BlockedMoveEvent(reason="out_of_bounds"))
            return -self.m_out

        # Простой
        if input_action == AgentActions.STAY:
            env.step_events.append(StayEvent())
            return -self.m_stay

        # Столкновение с непроходимой клеткой (только GridForest)
        passability = env.world_layers.get("passability")
        if passability is not None and passability[self.x, self.y] == 0:
            self.x, self.y = last_pos[0], last_pos[1]
            env.step_events.append(BlockedMoveEvent(reason="impassable"))
            return -self.m_block

        # Успешное перемещение
        mu_from = float(passability[last_pos[0], last_pos[1]]) if passability is not None else 1.0
        mu_to = float(passability[self.x, self.y]) if passability is not None else 1.0
        env.step_events.append(MoveEvent(mu_from=mu_from, mu_to=mu_to))
        return 0.0
        
    
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
                if env.world_layers["intruders"][x][y] == 0:
                    if type(env).__name__ == 'GridForest':
                        mu = env.world_layers["passability"][x][y]
                        if mu > 0 and mu >= self.spawn_min_passability:
                            self.x = x
                            self.y = y
                            return
                    if type(env).__name__ != 'GridForest':
                        self.x = x
                        self.y = y
                        return

            # Детерминированный перебор всех ячеек как запасной вариант
            is_forest = type(env).__name__ == 'GridForest'
            all_cells = [(x, y)
                         for x in range(env.grid_world_size)
                         for y in range(env.grid_world_size)]
            env.np_random.shuffle(all_cells)
            for x, y in all_cells:
                if env.world_layers["intruders"][x][y] == 0:
                    if is_forest:
                        mu = env.world_layers["passability"][x][y]
                        if mu > 0 and mu >= self.spawn_min_passability:
                            self.x, self.y = x, y
                            return
                    if not is_forest:
                        self.x, self.y = x, y
                        return

            raise RuntimeError(
                f"GridWorldAgent: нет свободных проходимых ячеек для спавна агента (grid={env.grid_world_size})"
            )
        
        #Заданная точка
        else:
            self.x = self.start_x
            self.y = self.start_y
            
            if env.world_layers["intruders"][self.start_x][self.start_y] == 0 or \
                type(env).__name__ == 'GridForest' and env.world_layers["passability"][self.start_x][self.start_y] != 0:
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
            spawn_min_passability=config.spawn_min_passability,
        )
