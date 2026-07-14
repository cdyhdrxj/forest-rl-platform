from __future__ import annotations
import numpy as np
from enum import IntEnum
from services.patrol_planning.assets.intruders.intruder import GridWorldIntruder
from services.patrol_planning.assets.intruders.models import PoacherAltConfig
from services.patrol_planning.assets.rewards.events import CatchEvent, DamageEvent, IntruderExitEvent

from services.patrol_planning.assets.intruders.src.poacher import target2path, get_border_positions


class Actions(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4


class PoacherAltState(IntEnum):
    WAITING  = -1
    MOVING   = 0
    FELLING  = 1
    EXITING  = 2


class PoacherAlt(GridWorldIntruder):
    """Браконьер: выбирает цель случайно из N ближайших ценных клеток на всей карте.

    При n_targets=1 всегда идёт к ближайшей ценной клетке (детерминировано).
    """

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward: float = 1.0,
                 m_plan: float = 1000.0,
                 m_tool_power: float = 100.0,
                 n_targets: int = 1,
                 incoming_moment: int = 0,
                 manual_spawn: bool = False,
                 use_idleness_targeting: bool = False,
                 use_passability_routing: bool = False):
        super().__init__(y, x, is_random_spawned, catch_reward, manual_spawn)
        self.route: list = []
        self.target: tuple = (-1, -1)
        self.m_tool_power = m_tool_power
        self.m_plan = m_plan
        self.n_targets = n_targets
        self.m_damage: float = 0.0
        self.incoming_moment = incoming_moment
        self.use_idleness_targeting = use_idleness_targeting
        self.use_passability_routing = use_passability_routing
        self.active_state: PoacherAltState = PoacherAltState.MOVING

    def get_symbol(self):
        return 'P'

    # ------------------------------------------------------------------
    # Target management
    # ------------------------------------------------------------------

    def _target_valid(self, env) -> bool:
        x, y = self.target
        if x == -1:
            return False
        value = env.world_layers['value']
        passability = env.world_layers.get('passability')
        if value[x][y] <= 0:
            return False
        if passability is not None and passability[x][y] == 0:
            return False
        return True

    def _set_target(self, env, new_target: tuple):
        if self.target in env.poacher_targets:
            env.poacher_targets.remove(self.target)
        self.target = new_target
        env.poacher_targets.append(self.target)

    def _clear_target(self, env):
        if self.target in env.poacher_targets:
            env.poacher_targets.remove(self.target)
        self.target = (-1, -1)

    def _acquire_target(self, env, max_fallback: int = 10) -> bool:
        """Перебирает кандидатов, строит A* для каждого, берёт первую достижимую цель.

        Из N ближайших выбирает случайный (поведение n_targets).
        Если все N недостижимы — продолжает перебор по дистанции (до max_fallback доп. попыток).
        Возвращает True если цель найдена и self.target / self.route установлены.
        """
        value = env.world_layers['value']
        passability = env.world_layers.get('passability')

        mask = np.asarray(value) > 0
        if passability is not None:
            mask &= np.asarray(passability) > 0

        candidates = [tuple(c) for c in np.argwhere(mask)]
        if not candidates:
            return False

        blocked = set(map(tuple, env.poacher_targets))
        candidates = [c for c in candidates if c not in blocked]
        if not candidates:
            return False

        if self.use_idleness_targeting:
            idleness = env.world_layers.get('idleness')
            if idleness is not None:
                # score = value × idleness: ценная + давно не посещённая = лучший кандидат
                candidates.sort(
                    key=lambda c: float(value[c[0]][c[1]]) * float(idleness[c[0]][c[1]]),
                    reverse=True,
                )
            else:
                candidates.sort(key=lambda c: abs(c[0] - self.x) + abs(c[1] - self.y))
            pool = candidates[:self.n_targets]
            # из топ-N берём ближайшую (детерминированно)
            pool_order = sorted(pool, key=lambda c: abs(c[0] - self.x) + abs(c[1] - self.y))
        else:
            # Из N ближайших — случайный порядок (исходное поведение)
            candidates.sort(key=lambda pos: abs(pos[0] - self.x) + abs(pos[1] - self.y))
            pool = candidates[:self.n_targets]
            rng = getattr(env, 'np_random', None)
            if rng is not None:
                pool_order = [pool[int(k)] for k in rng.permutation(len(pool))]
            else:
                pool_order = [pool[k] for k in np.random.permutation(len(pool))]

        # Остальные — по порядку дистанции / скора (fallback)
        rest = candidates[self.n_targets: self.n_targets + max_fallback]

        for candidate in pool_order + rest:
            if candidate == (self.x, self.y):
                self._set_target(env, candidate)
                self.route = []
                return True
            route = self._build_route(env, candidate)
            if route:
                self._set_target(env, candidate)
                self.route = route
                return True

        return False

    # ------------------------------------------------------------------
    # Pathfinding helpers
    # ------------------------------------------------------------------

    def _build_route(self, env, goal: tuple) -> list:
        """A* до goal. Возвращает список клеток без стартовой.

        Возвращает [] если цель в данный момент занята другим нарушителем или недостижима.
        """
        if env.world_layers['intruders'][goal[0]][goal[1]] == 1:
            return []
        result = target2path(env, (self.x, self.y), goal,
                             cost_by_passability=self.use_passability_routing)
        if result is None or result[0] is None:
            return []
        path, _ = result
        return path[1:] if len(path) > 1 else []

    def _move_one_step(self, env) -> bool:
        """Делает один шаг по self.route.

        Возвращает True если шаг выполнен, False при коллизии (позиция откатывается, маршрут сбрасывается).
        """
        i = env.world_layers['intruders']
        next_cell = self.route[0]
        action = self.path_to_actions([[self.x, self.y], next_cell])[0]
        backup = (self.x, self.y)

        if action == Actions.UP:
            self.x -= 1
        elif action == Actions.DOWN:
            self.x += 1
        elif action == Actions.LEFT:
            self.y -= 1
        elif action == Actions.RIGHT:
            self.y += 1

        if i[self.x][self.y] == 1:
            self.x, self.y = backup
            self.route = []
            return False

        self.route.pop(0)
        return True

    # ------------------------------------------------------------------
    # Main step
    # ------------------------------------------------------------------

    def step(self, env) -> float:
        delta_damage = 0.0

        if self.active_state == PoacherAltState.WAITING:
            env.world_layers['intruders'][self.x][self.y] = 0
            return 0.0

        match self.active_state:
            case PoacherAltState.MOVING:
                self._step_moving(env)

            case PoacherAltState.FELLING:
                delta_damage = self._do_fell(env)

            case PoacherAltState.EXITING:
                done = self._step_exiting(env)
                if done:
                    return 0.0

        agent = env.agent
        if agent.x == self.x and agent.y == self.y:
            env.step_events.append(CatchEvent(
                intruder_id=id(self),
                m_damage=self.m_damage,
                m_plan=self.m_plan,
            ))
            self.kill(env)
            return 0.0

        if delta_damage > 0:
            env.step_events.append(DamageEvent(delta=delta_damage))
        self.m_damage += delta_damage
        return -delta_damage

    # ------------------------------------------------------------------
    # State handlers
    # ------------------------------------------------------------------

    def _step_moving(self, env):
        i = env.world_layers['intruders']
        i[self.x][self.y] = 0

        if not self.route:
            # Инвалидируем устаревшую цель
            if not self._target_valid(env):
                self._clear_target(env)

            if self.target == (-1, -1):
                # Нет цели — ищем достижимую с нуля
                if not self._acquire_target(env):
                    self.active_state = PoacherAltState.EXITING
                    i[self.x][self.y] = 1
                    return
            else:
                # Цель валидна, но маршрут пуст (сброшен коллизией) — перестраиваем
                if (self.x, self.y) == self.target:
                    self.active_state = PoacherAltState.FELLING
                    i[self.x][self.y] = 1
                    return
                self.route = self._build_route(env, self.target)
                if not self.route:
                    # Цель заблокирована другим нарушителем или стала недостижима
                    self._clear_target(env)
                    if not self._acquire_target(env):
                        self.active_state = PoacherAltState.EXITING
                        i[self.x][self.y] = 1
                        return

            # _acquire_target мог выбрать цель совпадающую с текущей позицией
            if (self.x, self.y) == self.target:
                self.active_state = PoacherAltState.FELLING
                i[self.x][self.y] = 1
                return

        moved = self._move_one_step(env)

        # Переходим в FELLING только если шаг реально выполнен и мы на цели
        if moved and not self.route and (self.x, self.y) == self.target:
            self.active_state = PoacherAltState.FELLING

        self.x = np.clip(self.x, 0, env.grid_world_size - 1)
        self.y = np.clip(self.y, 0, env.grid_world_size - 1)
        i[self.x][self.y] = 1

    def _do_fell(self, env) -> float:
        if self.m_damage >= self.m_plan:
            self.active_state = PoacherAltState.EXITING
            return 0.0

        val = env.world_layers['value'][self.x][self.y]

        if val <= 0:
            # Клетка вырублена — ищем новую цель
            self._clear_target(env)
            self.route = []
            self.active_state = PoacherAltState.MOVING
            return 0.0

        delta = min(self.m_tool_power, val)
        env.world_layers['value'][self.x][self.y] -= delta
        return delta

    def _step_exiting(self, env) -> bool:
        """Движение к ближайшей валидной граничной клетке (passability >= mu_min).

        Выход разрешён только через граничную клетку с достаточной проходимостью.
        Возвращает True если поачер вышел с карты.
        """
        i = env.world_layers['intruders']
        i[self.x][self.y] = 0

        mu_min: float = getattr(env, 'mu_min', 0.5)
        u = env.world_layers['passability']
        rows, cols = len(u), len(u[0])

        def _on_valid_border(x, y) -> bool:
            on_edge = (x == 0 or x == rows - 1 or y == 0 or y == cols - 1)
            return on_edge and u[x][y] >= mu_min

        if not self.route:
            # Уже на валидной граничной клетке — выходим немедленно
            if _on_valid_border(self.x, self.y):
                env.step_events.append(IntruderExitEvent(intruder_id=id(self)))
                self.kill(env)
                return True

            # Ищем ближайшую валидную граничную клетку
            border = get_border_positions(rows, cols)
            valid_exits = [(x, y) for (x, y) in border if u[x][y] >= mu_min]

            best_cost = float('inf')
            best_route: list = []
            for target in valid_exits:
                result = target2path(env, (self.x, self.y), target, pass_mltply=20)
                if result is None:
                    continue
                path, cost = result
                if path is not None and cost < best_cost:
                    best_cost = cost
                    best_route = path[1:] if len(path) > 1 else []

            if not best_route:
                # Нет доступного выхода — стоим
                i[self.x][self.y] = 1
                return False

            self.route = best_route

        moved = self._move_one_step(env)

        self.x = np.clip(self.x, 0, env.grid_world_size - 1)
        self.y = np.clip(self.y, 0, env.grid_world_size - 1)
        i[self.x][self.y] = 1

        # Выход разрешён только если:
        # 1. Шаг реально выполнен (не коллизия)
        # 2. Маршрут исчерпан
        # 3. Поачер на валидной граничной клетке
        if moved and not self.route and _on_valid_border(self.x, self.y):
            env.step_events.append(IntruderExitEvent(intruder_id=id(self)))
            self.kill(env)
            return True

        return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def kill(self, env):
        env.world_layers['intruders'][self.x][self.y] = 0
        self.death_time = env.train_state.step
        env.train_state.total_damage += self.m_damage
        env.train_state.catch_latency.append(self.death_time - self.spawn_time)
        self._clear_target(env)
        env.intruders.remove(self)
        env.intruder_exit_count += 1

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def path_to_actions(path):
        actions = []
        for i in range(1, len(path)):
            x0, y0 = path[i - 1]
            x1, y1 = path[i]
            if x1 < x0:
                actions.append(Actions.UP)
            elif x1 > x0:
                actions.append(Actions.DOWN)
            elif y1 < y0:
                actions.append(Actions.LEFT)
            elif y1 > y0:
                actions.append(Actions.RIGHT)
            else:
                actions.append(Actions.STAY)
        return actions

    @staticmethod
    def load(config: PoacherAltConfig) -> PoacherAlt:
        return PoacherAlt(
            y=config.pos[1],
            x=config.pos[0],
            is_random_spawned=config.is_random_spawned,
            catch_reward=config.catch_reward,
            m_plan=config.m_plan,
            m_tool_power=config.m_tool_power,
            n_targets=config.n_targets,
            incoming_moment=config.incoming_moment,
            manual_spawn=config.manual_spawn,
            use_idleness_targeting=config.use_idleness_targeting,
            use_passability_routing=config.use_passability_routing,
        )
