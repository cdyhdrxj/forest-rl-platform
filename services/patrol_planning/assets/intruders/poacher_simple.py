from __future__ import annotations
import numpy as np
from abc import ABC, abstractmethod
from enum import IntEnum
from services.patrol_planning.assets.intruders.intruder import GridWorldIntruder
from services.patrol_planning.assets.intruders.models import IntruderConfig, PoacherSimpleConfig
from typing import Type

from services.patrol_planning.assets.intruders.src.poacher import target2path, get_neighbors_radius_1, get_border_positions


class Actions(IntEnum):
    UP = 0
    DOWN = 1
    LEFT = 2
    RIGHT = 3
    STAY = 4
    
class PoacherState(IntEnum):
    WAITING  = -1   # ещё не появился (incoming=True)
    MOVING   = 0
    FELLING  = 1
    EXITING  = 2
    SEARCHING = 3

#Пока что может оказаться с одной клетке с другим нарушителем

class PoacherSimple(GridWorldIntruder):
    """Класс браконьеров для сеточного мира"""

    def __init__(self, y, x, is_random_spawned: bool = False, catch_reward=1,
                 m_plan: float = 1000.0,
                    m_tool_power: float = 100,
                    search_patience: int = 5,
                    incoming_moment: int = 0):
        super().__init__(y, x, is_random_spawned, catch_reward)
        self.route = []
        self.target: tuple = (-1, -1)
        self.m_tool_power = m_tool_power
        self.m_plan = m_plan
        
        self.m_damage = 0
        self.search_patience = search_patience
        
        #Состояние нарушителя
        self.active_state: PoacherState = PoacherState.SEARCHING
        self.incoming_moment = incoming_moment
        #Ищем цель для рубки
        self.s_count: int = 0
        self.max_target: tuple = (-1,-1)
        self.exiting: bool = False
        

    def get_symbol(self):
        return 'P'

    def step(self, env: GridWorld):
        delta_damage = 0
        if self.active_state == PoacherState.WAITING:
            i = env.world_layers['intruders'][self.x][self.y] = 0
            return 0 
        # print('ACTIVE_ST', self.active_state)
        # print('target', self.target, self.max_target)
        
        match self.active_state:
            
            #ИЩЕМ ЦЕЛЬ ПОКА НЕ НАЙДЁМ ЛУЧШЕ ИЛИ НЕ КОНЧИТСЯ ТЕРПЕНИЕ
            case PoacherState.SEARCHING:
                v = env.world_layers['value']
                p = env.world_layers['passability']
                positions = get_neighbors_radius_1((self.x, self.y), len(v), len(v[0]))

                # фильтруем только проходимые клетки
                valid_positions = [pos for pos in positions if p[pos[0]][pos[1]] != 0 and not pos in env.poacher_targets]

                if valid_positions:
                    # выбираем клетку с максимальным значением среди проходимых
                    max_pos = max(valid_positions, key=lambda pos: v[pos[0]][pos[1]])
                else:
                    raise Exception("Нарушителю некуда двигаться, все клетки заняты")
                
                #Проверяем лучше ли он существующего?
                if self.max_target[0] != -1 and \
                    v[max_pos[0]][max_pos[1]] > v[self.max_target[0]][self.max_target[1]] and (
                        self.s_count < self.search_patience):
                    self.s_count += 1
                    self.max_target = max_pos
                #Если цели не было, ставим что нашли
                elif self.max_target[0] == -1:
                    self.max_target = max_pos
                    
                #Если лучше чем было уже нет, то начинаем рубку
                else:
                    self.s_count = self.search_patience
                    self.active_state = PoacherState.FELLING

                
                #Если цель есть, удаляем
                if self.target in env.poacher_targets:
                    env.poacher_targets.remove(self.target)
                
                #Обновляем цель и добавляем в список исключений
                self.target = self.max_target
                env.poacher_targets.append(self.target)
                
                                
                # Если маршрута нет или он пустой, строим новый к цели                
                if (not self.route or len(self.route) == 0) and self.target:
                    self.route, _ = target2path(env, (self.x, self.y), self.target)
                    self.active_state = PoacherState.MOVING
                    
            #ИДЁМ К ЦЕЛИ ПРИ ПОМОЩИ A* и стоимости = манхеттенского расстояния + (1-проходимость)* 10  
            case PoacherState.MOVING:
                # Удаляем свою старую позицию из мира
                i = env.world_layers["intruders"]
                i[self.x][self.y] = 0
                
                v = env.world_layers['value'] 
                
                # Двигаемся по маршруту
                if self.route and len(self.route) > 0:
                    # Берем следующую клетку маршрута
                    next_cell = self.route.pop(0)  # pop(0) — извлекаем первую координату
                    # Преобразуем в действие
                    action = self.path_to_actions([[self.x, self.y], next_cell])[0]

                    #Сохраняем старую позицию
                    pos_backup = (self.x, self.y)
                    
                    # Выполняем действие
                    if action == Actions.UP:
                        self.x -= 1
                    elif action == Actions.DOWN:
                        self.x += 1
                    elif action == Actions.LEFT:
                        self.y -= 1
                    elif action == Actions.RIGHT:
                        self.y += 1
                    elif action == Actions.STAY:
                        pass
                    
                    #Если кто-то в той клетке в которую идём - отменяем переход, перестраиваем маршрут
                    if i[self.x][self.y] == 1:
                        self.x = pos_backup[0]
                        self.y = pos_backup[1]
                        
                        #Возвращаемся в режим поиска и делаем перестраивание маршрута
                        self.active_state = PoacherState.SEARCHING
                        self.route = []
                    
                    
                else:
                    # Если маршрута нет — просто остаёмся
                    action = Actions.STAY
                    
                    #Если мы выхоим, и пришли в цель
                    if self.exiting:
                        self.kill(env)
                        return 0
                    
                    #Если устали искать, то рубим
                    if self.s_count >= self.search_patience and v[self.target[0]][self.target[1]]:
                        self.active_state = PoacherState.FELLING
                        # Тут надо проверить Если целевая ячейка пуста то сбрасываем терпение и начинаем поиск 
                    else:
                        #Иначе продолжаем поиск
                        self.active_state = PoacherState.SEARCHING

                # Границы карты
                self.x = np.clip(self.x, 0, env.grid_world_size - 1)
                self.y = np.clip(self.y, 0, env.grid_world_size - 1)
                
                # Иначе обновляем позицию на слое
                env.world_layers["intruders"][self.x][self.y] = 1
            
            #РУБКА
            case PoacherState.FELLING:
                delta_damage =  self._do_fell(env)
                
            #ИДЁМ К ВЫХОДУ
            case PoacherState.EXITING:
                # Берём края
                u = env.world_layers["passability"]
                rows, cols = len(u), len(u[0])
                border = get_border_positions(rows, cols)

                routes = []

                # считаем маршрут до каждой граничной клетки
                for target in border:
                    result = target2path(env, (self.x, self.y), target, pass_mltply=20)

                    if result is None:
                        continue

                    path, cost = result

                    if path is not None:
                        routes.append((cost, path))

                # если есть хотя бы один путь
                if routes:
                    # сортируем по минимальной стоимости
                    routes.sort(key=lambda x: x[0])

                    best_cost, best_route = routes[0]

                    self.route = best_route
                    self.active_state = PoacherState.MOVING                    
                    self.exiting = True
                else:
                    # выхода нет — остаёмся
                    self.active_state = PoacherState.STAY
                
                
            
        # Проверяем, не поймал ли агент
        agent = env.agent
        if agent.x == self.x and agent.y == self.y:
            self.kill(env)
            return self.compute_catch_reward(env)  # награда за поимку

        # # Иначе обновляем позицию на слое
        # env.world_layers["intruders"][self.x][self.y] = 1
        
        self.m_damage += delta_damage
        return -delta_damage
    
    def kill(self, env):
        #Обновляем метаданные
        self.death_time = env.train_state.step
        
        #Обновляем данные в train_state
        env.train_state.total_damage += self.m_damage
        env.train_state.catch_latency.append(self.death_time - self.spawn_time)
        
        #Убираем из списка активных нарушителей в среде
        env.intruders.remove(self) 
        env.intruder_exit_count += 1
    
    #Награда за поимку 
    def compute_catch_reward(self, env) -> float:
        
        prevented = max(0.0, env.intruder_detection_reward * (self.m_plan - self.m_damage))
        return self.catch_reward + self.m_damage + prevented

    def _do_fell(self, env) -> None:

        if self.m_damage >= self.m_plan:
            self.active_state = PoacherState.EXITING
            return 0

        val = env.world_layers["value"][self.x][self.y]

        if val <= 0:
            self.active_state = PoacherState.SEARCHING
            #Сбрасываем попытки поиска
            self.s_count = 0
            return 0

        delta = min(self.m_tool_power, val)
        env.world_layers["value"][self.x][self.y] -= delta
        
        return delta

    # Преобразовать маршрут в действия
    @staticmethod
    def path_to_actions(path):
        """
        path: список координат [(x0,y0), (x1,y1), ...]
        return: список действий Actions
        """
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
                actions.append(Actions.STAY)  # если координаты не изменились

        return actions

    @staticmethod
    def load(config: PoacherSimpleConfig) -> PoacherSimple:
        """
        Создает экземпляр PoacherSimple на основе конфигурации PoacherSimpleConfig.

        Args:
            config: Конфигурация нарушителя

        Returns:
            Экземпляр PoacherSimple
        """
        return PoacherSimple(
            y=config.pos[1],
            x=config.pos[0],
            is_random_spawned=config.is_random_spawned,
            catch_reward=config.catch_reward,
            m_plan=config.m_plan,
            m_tool_power=config.m_tool_power,
            search_patience=config.search_patience,
            incoming_moment=config.incoming_moment)

