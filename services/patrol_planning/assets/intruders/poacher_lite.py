from __future__ import annotations
import math
from enum import IntEnum
from typing import List, Optional, Tuple
import numpy as np

from services.patrol_planning.assets.intruders.intruder import GridWorldIntruder
from services.patrol_planning.assets.intruders.models import PoacherConfig
from services.patrol_planning.assets.intruders.src.poacher import (
    cell_passable,
    pick_initial_target,
    find_nearest_valuable,
    find_exit_cell,
    bfs,
)

class PoacherState(IntEnum):
    WAITING  = -1   # ещё не появился (incoming=True)
    MOVING   = 0
    FELLING  = 1
    EXITING  = 2


class Poacher(GridWorldIntruder):
    """
    Нарушитель-браконьер.

    Логика:
    1. Первый выбор цели — случайная ценная клетка
    2. Затем выбирается ближайшая достижимая ценная клетка
    3. После выполнения плана — выход с карты

    Параметры задержки появления (incoming=True):
        incoming_step     – шаг появления нарушителя.
                            -1 (по умолчанию) → выбирается случайно из
                            [incoming_patience, env.max_steps - incoming_patience]
                            в первом вызове step().
        incoming_patience – отступ от краёв интервала при случайном выборе шага.
    """

    def __init__(
        self,
        y: int,
        x: int,
        m_plan: float = 100.0,
        felling_intensity: float = 100.0,
        m_defence: float = 1.5,
        is_random_spawned: bool = False,
        catch_reward: float = 1.0,
        # --- новые параметры задержки ---
        incoming: bool = False,
        incoming_step: int = -1,
        incoming_patience: int = 5,
    ) -> None:

        super().__init__(
            y,
            x,
            is_random_spawned=is_random_spawned,
            catch_reward=catch_reward,
        )

        # параметры нарушителя
        self.m_plan = m_plan
        self.felling_intensity = felling_intensity
        self.m_defence = m_defence

        # накопленный ущерб
        self.m_damage = 0.0

        # --- параметры задержки ---
        self.incoming = incoming
        self.incoming_step = incoming_step
        self.incoming_patience = incoming_patience

        # шаг появления (разрешается в первом step, если incoming_step == -1)
        self._spawn_step: int = incoming_step
        # счётчик шагов среды
        self._step_count: int = 0
        # виден ли нарушитель уже на карте
        self._active: bool = not incoming

        # состояние
        self.state = PoacherState.WAITING if incoming else PoacherState.MOVING

        # цель и путь
        self.target: Optional[Tuple[int, int]] = None
        self._path: List[Tuple[int, int]] = []

        # рубка
        self._felling_steps_left = 0
        self._started_felling = False

        # флаг выхода
        self._exited = False

    def reset(self, env) -> None:
        """Сброс нарушителя к начальному состоянию."""

        self._step_count = 0
        self._exited = False
        self.m_damage = 0.0
        self.target = None
        self._path = []
        self._felling_steps_left = 0
        self._started_felling = False

        if self.incoming:
            self._active = False
            self.state = PoacherState.WAITING
            # _spawn_step будет разрешён в первом step() если == -1
            self._spawn_step = self.incoming_step
            # не ставим нарушителя на карту
        else:
            self._active = True
            self.state = PoacherState.MOVING
            # стандартный спавн из базового класса
            super().reset(env)
            
            
    def step(self, env) -> float:
        reward = 0.0
        delta_damage = 0.0

        self._step_count += 1

        # --- Проверяем, появление ---
        if self.state == PoacherState.WAITING:
            # разрешаем случайный шаг при первом вызове
            if self._spawn_step == -1:
                rng = getattr(env, "np_random", np.random.default_rng())
                low  = self.incoming_patience
                high = env.max_steps - self.incoming_patience
                self._spawn_step = int(rng.integers(low, max(low + 1, high + 1)))

            if self._step_count >= self._spawn_step:
                spawned = self._spawn_on_border(env)
                if spawned:
                    self._active = True
                    self.state = PoacherState.MOVING
                else:
                    # нет свободной клетки — пробуем на следующем шаге
                    self._spawn_step += 1
            return 0.0  # пока не появился, никакого эффекта

        # очистка старой позиции
        env.word_layers["intruders"][self.x][self.y] = 0

        # поведение
        if self.state == PoacherState.MOVING:
            self._do_move(env)

        elif self.state == PoacherState.FELLING:
            delta = self._do_fell(env)
            delta_damage = delta if delta else 0.0

        elif self.state == PoacherState.EXITING:
            self._do_exit(env)

        # проверка выхода
        if self._exited:
            if self in env.intruders:
                env.intruders.remove(self)
            return 0.0

        # проверка поимки
        agent = env.agent
        if (self.x, self.y) == (agent.x, agent.y):
            reward = float(self.compute_catch_reward())
            if self in env.intruders:
                env.intruders.remove(self)
            return reward - delta_damage

        # установка новой позиции
        env.word_layers["intruders"][self.x][self.y] = 1

        return delta_damage * -1.0

    @staticmethod
    def load(config: PoacherConfig) -> "Poacher":
        """
        Создаёт экземпляр Poacher из конфигурации.

        Args:
            config: PoacherConfig

        Returns:
            Poacher
        """
        return Poacher(
            y=config.pos[1],
            x=config.pos[0],
            m_plan=config.m_plan,
            is_random_spawned=config.is_random_spawned,
            catch_reward=config.catch_reward,
            incoming=config.incoming,
            incoming_step=config.incoming_step,
            incoming_patience=config.incoming_patience,
            felling_intensity=config.felling_intensity,
            m_defence=config.m_defence,
        )
        
        

    def get_symbol(self) -> str:
        return "P"

    def compute_catch_reward(self) -> float:
        prevented = max(0.0, self.m_defence * (self.m_plan - self.m_damage))
        return self.catch_reward + self.m_damage + prevented


    def _spawn_on_border(self, env) -> bool:
        """
        Выбирает клетку на границе с максимальной проходимостью
        (без других нарушителей) и перемещает нарушителя туда.
        Возвращает True если успешно.
        """
        #Окно, расширяющее выбор
        window = 0.08
        n = env.grid_world_size
        passability = env.word_layers.get("passability")
        intruders   = env.word_layers["intruders"]

        border = (
            [(x, 0)   for x in range(n)] +
            [(x, n-1) for x in range(n)] +
            [(0, y)   for y in range(1, n-1)] +
            [(n-1, y) for y in range(1, n-1)]
        )

        # фильтруем: нет нарушителей
        candidates = [(bx, by) for bx, by in border if intruders[bx][by] == 0]

        if not candidates:
            return False

        if passability is not None:
            # находим максимальную проходимость среди кандидатов
            max_pass = max(float(passability[bx][by]) for bx, by in candidates)
            candidates = [
                (bx, by) for bx, by in candidates
                if float(passability[bx][by]) >= max_pass - window
            ]

        rng = getattr(env, "np_random", np.random.default_rng())
        idx = int(rng.integers(len(candidates)))
        bx, by = candidates[idx]

        self.x, self.y = bx, by
        env.word_layers["intruders"][bx][by] = 1
        return True


    def _do_move(self, env) -> None:

        if self.target is None or not cell_passable(env, *self.target):
            if not self._started_felling:
                #Если нарушитель приходит с краю, то будет брать ближайшее к себе, чтобы не попасться
                # if self.incoming:
                #     self.target = self._choose_next_target(env)
                # else:
                #     self.target = pick_initial_target(env) # TODO Объединить с find_nearest_valuable
                #Случайным образом выбираем начальную
                self.target = pick_initial_target(env)
            else:
                self.target = find_nearest_valuable(env, self.x, self.y)

            self._path = []

        if self.target is None:
            self.state = PoacherState.EXITING
            return

        if not self._path:
            self._path = bfs(env, (self.x, self.y), self.target)[1:]

        if not self._path:
            self.target = None
            return

        nx, ny = self._path.pop(0)

        if not cell_passable(env, nx, ny):
            self._path = []
            return

        self.x, self.y = nx, ny

        if (self.x, self.y) == self.target:
            if env.word_layers["value"][self.x][self.y] > 0:
                self._start_felling(env)
            else:
                self.target = None


    def _start_felling(self, env) -> None:
        val = env.word_layers["value"][self.x][self.y]
        self._felling_steps_left = math.ceil(val / self.felling_intensity)
        self.state = PoacherState.FELLING
        self._started_felling = True

    def _do_fell(self, env) -> None:

        if self.m_damage >= self.m_plan:
            self.state = PoacherState.EXITING
            return None

        val = env.word_layers["value"][self.x][self.y]

        if val <= 0:
            self._choose_next_target(env)
            return None

        delta = min(self.felling_intensity, val)
        env.word_layers["value"][self.x][self.y] -= delta
        self.m_damage += delta
        self._felling_steps_left -= 1

        if self._felling_steps_left <= 0:
            env.word_layers["value"][self.x][self.y] = 0.0
            self._choose_next_target(env)

        return delta

    def _choose_next_target(self, env) -> None:

        for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nx, ny = self.x + dx, self.y + dy
            if (cell_passable(env, nx, ny) and
                    env.word_layers["value"][nx][ny] > 0):
                self.target = (nx, ny)
                self._path = []
                self.state = PoacherState.MOVING
                return

        self.target = find_nearest_valuable(env, self.x, self.y)
        self._path = []

        if self.target:
            self.state = PoacherState.MOVING
        else:
            self.state = PoacherState.EXITING


    def _do_exit(self, env) -> None:

        n = env.grid_world_size

        if self.x in (0, n - 1) or self.y in (0, n - 1):
            self._exited = True
            return

        if not self._path:
            self.target = find_exit_cell(env, self.x, self.y)
            if self.target:
                self._path = bfs(env, (self.x, self.y), self.target)[1:]

        if self._path:
            nx, ny = self._path.pop(0)
            if cell_passable(env, nx, ny):
                self.x, self.y = nx, ny
            else:
                self._path = []
